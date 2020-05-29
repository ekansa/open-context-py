import copy
import json
import logging

from django.conf import settings


from opencontext_py.libs.globalmaptiles import GlobalMercator
from opencontext_py.libs.validategeojson import ValidateGeoJson

from opencontext_py.libs.isoyears import ISOyears
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.libs.memorycache import MemoryCache
from opencontext_py.libs.rootpath import RootPath

from opencontext_py.apps.ocitems.geospace.models import Geospace
from opencontext_py.apps.ocitems.subjects.models import Subject

from opencontext_py.apps.indexer.solrdocumentnew import SolrDocumentNew as SolrDocument

from opencontext_py.apps.searcher.new_solrsearcher import configs
from opencontext_py.apps.searcher.new_solrsearcher.searchlinks import SearchLinks
from opencontext_py.apps.searcher.new_solrsearcher import utilities


logger = logging.getLogger(__name__)


# Skip if the geospatial tile is for "Null Island" (0 Lat, 0 Lon) 
# because this is for bad data.
NULL_ISLAND_TILE_ROOT = '211111'

# ---------------------------------------------------------------------
# Methods to generate results for geospatial facets
# ---------------------------------------------------------------------

class ResultFacetsGeo():

    """ Methods to prepare result facets for geospatial """

    def __init__(self, 
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
        self.max_depth = SolrDocument.MAX_GEOTILE_ZOOM
        self.min_depth = SolrDocument.MAX_GEOTILE_ZOOM
        self.default_tile_feature_type = 'Polygon'
        self.valid_tile_feature_types = ['Polygon', 'Point',]
        self.default_aggregation_depth = 10
        self.default_max_tile_count = 500
        self.min_tile_depth = 5
        self.min_date = None
        self.max_date = None


    def _make_valid_options_tile_tuples(self, options_tuples):
        """Makes a list of valid tile_dicts from a list of options_tuples"""
        valid_tile_tuples = []
        for tile, count in options_tuples:
            if tile.startswith(NULL_ISLAND_TILE_ROOT):
                # Skip, because the tile is almost certainly reflecting
                # bad data.
                logger.warn('Found {} bad geotile records'.format(count))
                # So skip.
                continue
            # Parse the tile to get the lon, lat list.
            gm = GlobalMercator()
            geo_coords = gm.quadtree_to_geojson_poly_coords(tile)
            if not isinstance(geo_coords, list):
                # Not a valid data for some awful reason.
                logger.warn(
                    'Found bad {} geotile with {} records'.format(
                        tile, 
                        count,
                    )
                )
                continue
            valid_tile_tuples.append(
                (tile, count,)
            )
        return valid_tile_tuples


    def _distance_determine_aggregation_depth(self, valid_tile_tuples):
        """Uses distance between to recalibrate aggregation depth in tiles"""
        if len(valid_tile_tuples) < 2:
            return self.default_aggregation_depth

        lons = []
        lats = []
        gm = GlobalMercator()
        for tile, _ in valid_tile_tuples:
            geo_coords = gm.quadtree_to_geojson_lon_lat(tile)
            # Remember geojson ordering of the coordinates (lon, lat)
            lons.append(geo_coords[0])
            lats.append(geo_coords[1])
        
        max_distance = gm.distance_on_unit_sphere(
            min(lats), 
            min(lons), 
            max(lats), 
            max(lons),
        )
        # Converts the maximum distance between points into a zoom level
        # appropriate for tile aggregation. Seems to work well.
        return gm.ZoomForPixelSize(max_distance) + 3


    def _get_tile_aggregation_depth(self, valid_tile_tuples):
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
            # The chronology aggregation depth is not set, so
            # return the 
            dist_deep = self._distance_determine_aggregation_depth(
                valid_tile_tuples
            )
            
            valid_tiles = [tile for tile, _ in valid_tile_tuples]
            all_agg_depth = utilities.get_aggregation_depth_to_group_paths(
                max_groups=4,
                paths=valid_tiles,
                max_depth=self.max_depth,
            )
            all_agg_depth += self.min_tile_depth

            # Choose the less deep aggregation depth determined from
            # these two methods.
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
        when['id'] = '#event-{}'.format(id_suffix)
        when['type'] = 'oc-gen:formation-use-life'
        # convert numeric to GeoJSON-LD ISO 8601
        when['start'] = ISOyears().make_iso_from_float(
            self.min_date
        )
        when['stop'] = ISOyears().make_iso_from_float(
            self.max_date
        )
        option['when'] = when
        return option


    def make_geotile_facet_options(self, solr_json):
        """Makes geographic tile facets from a solr_json response""" 
        geotile_path_keys = (
            configs.FACETS_SOLR_ROOT_PATH_KEYS 
            + ['discovery_geotile']
        )
        geotile_val_count_list = utilities.get_dict_path_value(
            geotile_path_keys,
            solr_json,
            default=[]
        )
        if not len(geotile_val_count_list):
            return None
        
        # Make the list of tile, count tuples.
        options_tuples = utilities.get_facet_value_count_tuples(
            geotile_val_count_list
        )
        if not len(options_tuples):
            return None
        
        valid_tile_tuples = self._make_valid_options_tile_tuples(
            options_tuples
        )
        if not len(valid_tile_tuples):
            # None of the chronological tiles are valid
            # given the query requirements.
            return None

        # Determine the aggregation depth needed to group geotiles
        # together into a reasonable number of options.
        self._get_tile_aggregation_depth(valid_tile_tuples)

        # Determine the min tile depth. We need to return this to 
        # the client so the client knows not to over-zoom.
        tile_lens = [len(tile) for tile, _ in valid_tile_tuples]
        self.min_depth = min(tile_lens)

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

        aggregate_tiles = {}
        for tile, count in valid_tile_tuples:
            # Now aggregate the tiles.
            trim_tile_key = tile[:self.default_aggregation_depth]
            if trim_tile_key not in aggregate_tiles:
                # Make the aggregate tile with a count
                # of zero
                aggregate_tiles[trim_tile_key] = 0

            aggregate_tiles[trim_tile_key] += count

        options = []
        for tile, count in aggregate_tiles.items():
            sl = SearchLinks(
                request_dict=copy.deepcopy(self.request_dict),
                base_search_url=self.base_search_url
            )
            # Remove non search related params.
            sl.remove_non_query_params()

            # Update the request dict for this facet option.
            sl.replace_param_value(
                'disc-geotile',
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
            geometry['id'] = '#geo-disc-tile-geom-{}'.format(tile)
            geometry['type'] = feature_type
            geometry['coordinates'] = geo_coords
            option['geometry'] = geometry

            properties = LastUpdatedOrderedDict()
            properties['id'] = '#geo-disc-tile-{}'.format(tile)
            properties['href'] = option['id']
            properties['label'] = 'Discovery region ({})'.format(
                (len(options) + 1)
            )
            properties['feature-type'] = 'discovery region (facet)'
            properties['count'] = count
            properties['early bce/ce'] = self.min_date
            properties['late bce/ce'] = self.max_date
            option['properties'] = properties

            options.append(option)

        return options


    def _make_cache_geospace_obj_dict(self, uuids):
        """Make a dict of geospace objects keyed by uuid"""
        m_cache = MemoryCache()
        uuids_for_qs = []
        uuid_geo_dict = {}
        for uuid in uuids:
            cache_key = m_cache.make_cache_key(
                prefix='geospace-obj',
                identifier=uuid
            )
            geo_obj = m_cache.get_cache_object(
                cache_key
            )
            if geo_obj is None:
                uuids_for_qs.append(uuid)
            else:
                uuid_geo_dict[uuid] = geo_obj
        
        if not len(uuids_for_qs):
            # Found them all from the cache!
            # Return without touching the database.
            return uuid_geo_dict
        
        # Lookup the remaining geospace objects from a
        # database query. We order by uuid then reverse
        # of feature_id so that the lowest feature id is the
        # thing that actually gets cached.
        geospace_qs = Geospace.objects.filter(
            uuid__in=uuids_for_qs,
        ).exclude(
            ftype__in=['Point', 'point']
        ).order_by('uuid', '-feature_id')
        for geo_obj in geospace_qs:
            cache_key = m_cache.make_cache_key(
                prefix='geospace-obj',
                identifier=str(geo_obj.uuid)
            )
            m_cache.save_cache_object(
                cache_key, geo_obj
            )
            uuid_geo_dict[geo_obj.uuid] = geo_obj
        
        return uuid_geo_dict
    

    def _get_cache_contexts_dict(self, uuids):
        """Make a dictionary that associates uuids to context paths"""
        m_cache = MemoryCache()
        uuids_for_qs = []
        uuid_context_dict = {}
        for uuid in uuids:
            cache_key = m_cache.make_cache_key(
                prefix='context-path',
                identifier=uuid
            )
            context_path = m_cache.get_cache_object(
                cache_key
            )
            if context_path is None:
                uuids_for_qs.append(uuid)
            else:
                uuid_context_dict[uuid] = context_path
        
        if not len(uuids_for_qs):
            # Found them all from the cache!
            # Return without touching the database.
            return uuid_context_dict
        
        # Lookup the remaining geospace objects from a
        # database query. We order by uuid then reverse
        # of feature_id so that the lowest feature id is the
        # thing that actually gets cached.
        subject_qs = Subject.objects.filter(
            uuid__in=uuids_for_qs,
        )
        for sub_obj in subject_qs:
            cache_key = m_cache.make_cache_key(
                prefix='context-path',
                identifier=str(sub_obj.uuid)
            )
            m_cache.save_cache_object(
                cache_key, 
                sub_obj.context
            )
            uuid_context_dict[sub_obj.uuid] = sub_obj.context
        
        return uuid_context_dict


    def make_geo_contained_in_facet_options(self, solr_json):
        """Gets geospace item query set from a list of options tuples"""
        geosource_path_keys = (
            configs.FACETS_SOLR_ROOT_PATH_KEYS 
            + ['disc_geosource']
        )
        geosource_val_count_list = utilities.get_dict_path_value(
            geosource_path_keys,
            solr_json,
            default=[]
        )
        if not len(geosource_val_count_list):
            return None
        
        # Make the list of tile, count tuples.
        options_tuples = utilities.get_facet_value_count_tuples(
            geosource_val_count_list
        )
        if not len(options_tuples):
            return None

        uuids = []
        parsed_solr_entities = {}
        uuid_geo_dict = {}
        for solr_entity_str, count in options_tuples:
            parsed_entity = utilities.parse_solr_encoded_entity_str(
                solr_entity_str,
                base_url=self.base_url
            )
            if not parsed_entity:
                logger.warn(
                    'Cannot parse entity from {}'.format(solr_entity_str)
                )
                continue
            if not '/' in parsed_entity['uri']:
                logger.warn(
                    'Invalid uri from {}'.format(solr_entity_str)
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
        uuid_geo_dict = self._make_cache_geospace_obj_dict(uuids)

        # Make a dict of context paths, keyed by uuid. This will also
        # hit the database in only 1 query, for all context paths not
        # already present in the cache.
        uuid_context_dict = self._get_cache_contexts_dict(uuids)
        
        # Now make the final 
        geo_options = []
        for solr_entity_str, count in options_tuples:
            if solr_entity_str not in parsed_solr_entities:
                # This solr_entity_str did not validate to extract a UUID.
                continue
            parsed_entity = parsed_solr_entities[solr_entity_str]
            uuid = parsed_entity['uuid']
            geo_obj = uuid_geo_dict.get(uuid)
            if  geo_obj is None:
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
            geometry = LastUpdatedOrderedDict()
            geometry['id'] = '#geo-in-geom-{}'.format(uuid)
            geometry['type'] =  geo_obj.ftype
            coord_obj = json.loads(geo_obj.coordinates)
            v_geojson = ValidateGeoJson()
            coord_obj = v_geojson.fix_geometry_rings_dir(
                geo_obj.ftype,
                coord_obj
            )
            geometry['coordinates'] = coord_obj
            option['geometry'] = geometry


            properties = LastUpdatedOrderedDict()
            properties['id'] = '#geo-in-props-{}'.format(uuid)
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


