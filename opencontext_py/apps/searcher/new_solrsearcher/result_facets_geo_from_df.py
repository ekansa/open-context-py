import copy
import logging
import pandas as pd


from opencontext_py.libs.globalmaptiles import GlobalMercator

from opencontext_py.libs.isoyears import ISOyears
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.libs.rootpath import RootPath


from opencontext_py.apps.indexer import solrdocument_new_schema as SolrDoc

from opencontext_py.apps.searcher.new_solrsearcher import configs
from opencontext_py.apps.searcher.new_solrsearcher import event_utilities
from opencontext_py.apps.searcher.new_solrsearcher.searchlinks import SearchLinks
from opencontext_py.apps.searcher.new_solrsearcher import utilities


logger = logging.getLogger(__name__)


# Skip if the geospatial tile is for "Null Island" (0 Lat, 0 Lon) 
# because this is for bad data.
NULL_ISLAND_TILE_ROOT = '211111'

# ---------------------------------------------------------------------
# Methods to generate results for geospatial facets
# ---------------------------------------------------------------------


GEO_TILE_FACET_FIELDS = [
    f'{configs.ROOT_EVENT_CLASS}___geo_tile',
    f'{configs.ROOT_EVENT_CLASS}___lr_geo_tile',
]

GEO_SOURCE_FACET_FIELDS = [
    f'{configs.ROOT_EVENT_CLASS}___geo_source',
]

def get_tile_lon_lat_coordinates(tile):
    gm = GlobalMercator()
    geo_coords = gm.quadtree_to_geojson_lon_lat(tile)
    # remember coordinates are in lon, lat order!
    return geo_coords


class ResultFacetsGeoFromDF():

    """ Methods to prepare result facets for geospatial """

    def __init__(
        self,          
        request_dict=None,
        current_filters_url=None, 
        base_search_url='/search/'
    ):
        rp = RootPath()
        self.base_url = rp.get_baseurl()
        self.base_search_url = base_search_url
        self.request_dict = copy.deepcopy(request_dict)
        if current_filters_url is None:
            current_filters_url = self.base_search_url
        self.current_filters_url = current_filters_url
        self.max_depth = SolrDoc.MAX_GEOTILE_ZOOM
        self.min_depth = SolrDoc.MIN_GEOTILE_ZOOM
        self.default_tile_feature_type = 'Polygon'
        self.valid_tile_feature_types = ['Polygon', 'Point',]
        self.default_aggregation_depth = 10
        self.default_max_tile_count = 500
        self.min_tile_depth = 5
        self.min_date = None
        self.max_date = None


    def get_valid_tiles_df(self, facets_df):
        """Makes a list of valid tile_dicts from a list of options_tuples"""
        valid_index = (
            facets_df['facet_field_key'].isin(GEO_TILE_FACET_FIELDS)
            & ~facets_df['facet_value'].str.startswith(NULL_ISLAND_TILE_ROOT, na=False)
        )
        tiles_df = facets_df[valid_index].copy()
        tiles_df['lon_lat'] = tiles_df['facet_value'].apply(
            get_tile_lon_lat_coordinates
        )
        tiles_df['lon'] = tiles_df['lon_lat'].str.get(1)
        tiles_df['lon'] = pd.to_numeric(tiles_df['lon'])
        tiles_df['lat'] = tiles_df['lon_lat'].str.get(1)
        tiles_df['lat'] = pd.to_numeric(tiles_df['lat'])
        tiles_df.drop(
            columns=['lon_lat'],
            inplace=True
        )
        return tiles_df


    def _distance_determine_aggregation_depth(self, tiles_df):
        """Uses distance between to recalibrate aggregation depth in tiles"""
        if len(tiles_df.index) < 2:
            return self.default_aggregation_depth
        
        gm = GlobalMercator()
        max_distance = gm.distance_on_unit_sphere(
            tiles_df['lat'].min(),
            tiles_df['lon'].min(), 
            tiles_df['lat'].max(),
            tiles_df['lon'].max(),
        )
        max_distance = int(max_distance)
        if max_distance < 1: max_distance = 1
        # Converts the maximum distance between points into a zoom level
        # appropriate for tile aggregation. Seems to work well.
        return gm.ZoomForPixelSize(max_distance) + 3

    
    def _get_tile_aggregation_depth(self, tiles_df):
        """Set aggregation depth for grouping tile options"""
        deep = utilities.get_request_param_value(
            self.request_dict, 
            param='geodeep',
            default=None,
            as_list=False,
            solr_escape=False,
            require_int=True,
        )
        if not deep:
            # The geospatial aggregation depth is not set, so
            # return the 
            dist_deep = self._distance_determine_aggregation_depth(
                tiles_df
            )
            
            all_agg_depth, _ = utilities.get_aggregation_depth_to_group_paths_from_tiles_df(
                max_groups=4,
                tiles_df=tiles_df,
                max_depth=self.max_depth,
                min_depth=1,
            )
            all_agg_depth += self.min_tile_depth

            # Choose the less deep aggregation depth determined from
            # these two methods.
            print(f'Computed geodeep options are: ' + str([dist_deep, all_agg_depth]))
            deep = min([dist_deep, all_agg_depth])
        # Now put some limits on it.
        if deep < self.min_tile_depth:
            deep = self.min_tile_depth
        if deep > self.max_depth:
            deep = self.max_depth
        self.default_aggregation_depth = deep
        return deep


    def _add_when_object_to_feature_option(self, id_suffix, option):
        """Adds a when object to a feature option"""
        # Add some general chronology information to the
            # geospatial tile. 
        if (self.min_date is None
            or self.max_date is None):
            return option

        when = LastUpdatedOrderedDict()
        when['id'] = f'#event-{id_suffix}'
        when['type'] = configs.DEFAULT_API_EVENT_ID
        # convert numeric to GeoJSON-LD ISO 8601
        when['start'] = ISOyears().make_iso_from_float(
            self.min_date
        )
        when['stop'] = ISOyears().make_iso_from_float(
            self.max_date
        )
        option['when'] = when
        return option


    def make_geotile_facet_options(self, tiles_df):
        """Makes geographic tile facets from a tiles_df dataframe"""

        if tiles_df is None:
            return None
        if len(tiles_df.index) == 0:
            return None

        # Determine the aggregation depth needed to group geotiles
        # together into a reasonable number of options.
        geodeep = self._get_tile_aggregation_depth(tiles_df)

        # Make the aggregate tile based on our geodeep
        tiles_df['agg_tile'] = tiles_df['facet_value'].str[:geodeep]

        # Determine the min tile depth. We need to return this to 
        # the client so the client knows not to over-zoom.
        self.min_depth = tiles_df['facet_value'].str.len().min()

        # Get the client's requested feature type for the geotile
        # facets.
        feature_type = utilities.get_request_param_value(
            self.request_dict, 
            param='geo-facet-type',
            default=self.default_tile_feature_type,
            as_list=False,
            solr_escape=False,
        )
        if feature_type not in self.valid_tile_feature_types:
            # If the requested feature type is not in the
            # valid list of feature types, just use the default.
            feature_type = self.default_tile_feature_type
        
        # Now aggregate the tiles together by summing all the facet counts
        # grouped into common agg_tiles
        grp_cols = [
            'agg_tile',
            'facet_count',
        ]
        df_g = tiles_df[grp_cols].groupby(['agg_tile'], as_index=False).sum()
        df_g.reset_index(drop=True, inplace=True)
        df_g.sort_values(
            by=['facet_count', 'agg_tile',], 
            ascending=[False, True],
            inplace=True,
        )
        options = []
        for _, row in df_g.iterrows():
            tile = row['agg_tile']
            count = row['facet_count']
            sl = SearchLinks(
                request_dict=copy.deepcopy(self.request_dict),
                base_search_url=self.base_search_url
            )
            # Remove non search related params.
            sl.remove_non_query_params()

            # Update the request dict for this facet option.
            sl.replace_param_value(
                'allevent-geotile',
                match_old_value=None,
                new_value=tile,
            )  
            urls = sl.make_urls_from_request_dict()
            if urls['html'] == self.current_filters_url:
                # The new URL matches our current filter
                # url, so don't add this facet option.
                continue

            option = LastUpdatedOrderedDict()
            option['id'] = urls['html']
            option['json'] = urls['json']
            option['count'] = count
            option['geodeep'] = geodeep
            option['type'] = 'Feature'
            option['category'] = 'oc-api:geo-facet'

            # Add some general chronology information to the
            # geospatial tile. 
            option = self._add_when_object_to_feature_option(
                tile,
                option,
            )
            
            gm = GlobalMercator()
            if feature_type == 'Polygon':
                # Get polygon coordinates (a list of lists)
                geo_coords = gm.quadtree_to_geojson_poly_coords(tile)
            elif feature_type == 'Point':
                # Get point coordinates (a list of lon,lat values)
                geo_coords = gm.quadtree_to_geojson_lon_lat(tile)
            else:
                # We shouldn't be here!
                continue
            
            # Add the geometry object to the facet option.
            geometry = LastUpdatedOrderedDict()
            geometry['id'] = f'#geo-all-geom-{tile}'
            geometry['type'] = feature_type
            geometry['coordinates'] = geo_coords
            option['geometry'] = geometry

            properties = LastUpdatedOrderedDict()
            properties['id'] = f'#geo-all-{tile}'
            properties['href'] = option['id']
            properties['label'] = f'Region ({(len(options) + 1)})'
            properties['feature-type'] = 'Geospace region (facet)'
            properties['count'] = count
            properties['early bce/ce'] = self.min_date
            properties['late bce/ce'] = self.max_date
            option['properties'] = properties

            options.append(option)

        return options
    

    def make_geo_contained_in_facet_options(self, facets_df):
        """Gets geospatial features with counts of contained objects"""
        
        valid_index = (
            facets_df['facet_field_key'].isin(GEO_SOURCE_FACET_FIELDS)
        )
        if not len(facets_df[valid_index].index):
            return None
        
        if False:
            # just in case we want to do this in a vectorized(?) way
            facets_df['parsed_entity'] = facets_df['facet_value'].apply(
                utilities.parse_solr_encoded_entity_str,
                base_url=self.base_url,
            )
        
        uuids = []
        parsed_solr_entities = {}
        uuid_geo_dict = {}
        for _, row in facets_df[valid_index].iterrows():
            solr_entity_str = row['facet_value']
            parsed_entity = utilities.parse_solr_encoded_entity_str(
                solr_entity_str=solr_entity_str,
                base_url=self.base_url
            )
            if not parsed_entity:
                logger.warn(
                    f'Cannot parse entity from {solr_entity_str}'
                )
                continue
            if not '/' in parsed_entity['uri']:
                logger.warn(
                    f'Invalid uri from {solr_entity_str}'
                )
                continue
            uri_parts = parsed_entity['uri'].split('/')
            uuid = uri_parts[-1]
            parsed_entity['uuid'] = uuid
            parsed_solr_entities[solr_entity_str] = parsed_entity
            uuids.append(uuid)
        
        # Make a dictionary of geospace objects keyed by uuid. This
        # will hit the database in one query to get all geospace
        # objects not present in the cache.
        uuid_geo_dict = event_utilities.make_cache_spacetime_obj_dict(uuids)

        # Make a dict of context paths, keyed by uuid. This will also
        # hit the database in only 1 query, for all context paths not
        # already present in the cache.
        uuid_context_dict = self._get_cache_contexts_dict(uuids)
        
        # Now make the final 
        geo_options = []
        for _, row in facets_df[valid_index].iterrows():
            solr_entity_str = row['facet_value']
            count = row['facet_count']
            if solr_entity_str not in parsed_solr_entities:
                # This solr_entity_str did not validate to extract a UUID.
                continue
            parsed_entity = parsed_solr_entities[solr_entity_str]
            uuid = parsed_entity['uuid']
            geo_obj = uuid_geo_dict.get(uuid)
            if  geo_obj is None or not geo_obj.geometry:
                logger.warn('No geospace object for {}'.format(uuid))
                continue

            context_path = uuid_context_dict.get(uuid)
            if context_path is None:
                logger.warn('No context path for {}'.format(uuid))
                continue
            
            sl = SearchLinks(
                request_dict=copy.deepcopy(self.request_dict),
                base_search_url=self.base_search_url
            )
            # Remove non search related params.
            sl.remove_non_query_params()

            # Update the request dict for this facet option.
            sl.replace_param_value(
                'path',
                match_old_value=None,
                new_value=context_path,
            )  
            urls = sl.make_urls_from_request_dict()

            # NOTE: We're not checking if the URLs are the same
            # as the current search URL, because part of the point
            # of listing these features is for visualization display
            # in the front end.

            option = LastUpdatedOrderedDict()

            # The fragment id in the URLs are so we don't have an
            # ID collision with context facets.
            option['id'] = urls['html'] + '#geo-in'
            option['json'] = urls['json'] + '#geo-in'

            option['count'] = count
            option['type'] = 'Feature'
            option['category'] = 'oc-api:geo-contained-in-feature'

            # Add some general chronology information to the
            # geospatial feature.
            option = self._add_when_object_to_feature_option(
                uuid,
                option,
            )

            # Add the geometry from the geo_obj coordinates. First
            # check to make sure they are OK with the the GeoJSON
            # right-hand rule.
            geometry = copy.deepcopy(geo_obj.geometry)
            geometry['id'] = f'#geo-in-geom-{uuid}'
            option['geometry'] = geometry


            properties = LastUpdatedOrderedDict()
            properties['id'] = f'#geo-in-props-{uuid}'
            properties['href'] = option['id']
            properties['item-href'] = parsed_entity['uri']
            properties['label'] = context_path
            properties['feature-type'] = 'containing-region'
            properties['count'] = count
            properties['early bce/ce'] = self.min_date
            properties['late bce/ce'] = self.max_date
            option['properties'] = properties
            
            geo_options.append(option)

        return geo_options