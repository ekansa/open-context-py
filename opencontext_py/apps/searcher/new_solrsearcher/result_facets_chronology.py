import copy

from django.conf import settings


from opencontext_py.libs.chronotiles import ChronoTile
from opencontext_py.libs.isoyears import ISOyears
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.libs.rootpath import RootPath

from opencontext_py.apps.searcher.new_solrsearcher import configs
from opencontext_py.apps.searcher.new_solrsearcher.searchlinks import SearchLinks
from opencontext_py.apps.searcher.new_solrsearcher import utilities

# ---------------------------------------------------------------------
# Methods to generate results for chronology facets
# ---------------------------------------------------------------------
class ResultFacetsChronology():

    """ Methods to prepare result facets for chronology """

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
        self.min_tile_depth = 12
        self.default_aggregation_depth = 16
        self.default_max_tile_count = 30
        self.max_depth = ChronoTile.MAX_TILE_DEPTH
        self.limiting_tile = None
        self.min_date = None  # bce / ce
        self.max_date = None  # bce / ce
        self.exclude_before = None  # bce / ce
        self.exclude_after = None # bce / ce


    def _set_client_earliest_latest_limits(self):
        """Sets earliest and latest date limits from the client"""
        form_start = utilities.get_request_param_value(
            self.request_dict, 
            param='form-start',
            default=None,
            as_list=False,
            solr_escape=False,
            require_float=True,
        ) 
        if form_start:
            self.exclude_before = form_start
        form_stop = utilities.get_request_param_value(
            self.request_dict, 
            param='form-stop',
            default=None,
            as_list=False,
            solr_escape=False,
            require_float=True,
        )
        if form_stop:
            self.exclude_after = form_stop
        form_tile = utilities.get_request_param_value(
            self.request_dict, 
            param='form-chronotile',
            default=None,
            as_list=False,
            solr_escape=False,
        )
        if form_tile:
            self.limiting_tile = form_tile


    def _make_valid_options_tile_dicts(self, options_tuples):
        """Makes a list of valid tile_dicts from a list of options_tuples"""
        valid_tile_dicts = []
        for tile, count in options_tuples:
            if (self.limiting_tile is not None
                and not tile.startswith(self.limiting_tile)):
                # We're looking only for tiles within a limiting
                # tile, and the current tile is not within that.
                # So skip.
                continue
            # Parse the tile to get date ranges.
            chrono_t = ChronoTile()
            tile_dict = chrono_t.decode_path_dates(tile)
            if not isinstance(tile_dict, dict):
                # Not a valid data for some awful reason.
                continue
            if (self.exclude_before is not None 
                and tile_dict['earliest_bce'] < self.exclude_before):
                # The date range is too early.
                continue
            if (self.exclude_after is not None 
                and tile_dict['latest_bce'] > self.exclude_after):
                # The date range is too late.
                continue
            if self.min_date is None:
                self.min_date = tile_dict['earliest_bce']
            if self.max_date is None:
                self.max_date = tile_dict['latest_bce']
            if self.min_date > tile_dict['earliest_bce']:
                self.min_date = tile_dict['earliest_bce']
            if self.max_date < tile_dict['latest_bce']:
                self.max_date = tile_dict['latest_bce']
            tile_dict['tile_key'] = tile
            tile_dict['count'] = count
            valid_tile_dicts.append(tile_dict)
        return valid_tile_dicts


    def _get_tile_aggregation_depth(self, valid_tile_dicts):
        """Set aggregation depth for grouping tile options"""
        deep = utilities.get_request_param_value(
            self.request_dict, 
            param='chronodeep',
            default=None,
            as_list=False,
            solr_escape=False,
            require_int=True,
        )
        if not deep:
            # The chronology aggregation depth is not set, so
            # return the 
            valid_tiles = [d['tile_key'] for d in valid_tile_dicts]
            deep = utilities.get_aggregation_depth_to_group_paths(
                max_groups=self.default_max_tile_count,
                paths=valid_tiles,
                max_depth=self.max_depth,
            )
        # Now put some limits on it.
        if deep < self.min_tile_depth:
            deep = self.min_tile_depth
        if deep > self.max_depth:
            deep = self.max_depth
        self.default_aggregation_depth = deep
        return deep 


    def make_chronology_facet_options(self, solr_json):
        """Makes chronology facets from a solr_json response""" 
        chrono_path_keys = (
            configs.FACETS_SOLR_ROOT_PATH_KEYS 
            + ['form_use_life_chrono_tile']
        )
        chrono_val_count_list = utilities.get_dict_path_value(
            chrono_path_keys,
            solr_json,
            default=[]
        )
        if not len(chrono_val_count_list):
            return None
        options_tuples = utilities.get_facet_value_count_tuples(
            chrono_val_count_list
        )
        if not len(options_tuples):
            return None
        
        # Check to see if the client included any request parameters
        # that limited the chronological range of the request.
        self._set_client_earliest_latest_limits()
        
        valid_tile_dicts = self._make_valid_options_tile_dicts(
            options_tuples
        )
        if not len(valid_tile_dicts):
            # None of the chronological tiles are valid
            # given the query requirements.
            return None

        # Determine the aggregation depth needed to group chronological
        # tiles together into a reasonable number of options.
        self._get_tile_aggregation_depth(valid_tile_dicts)

        aggregate_tiles = {}
        for tile_dict in valid_tile_dicts:
            # Now aggregate the tiles.
            trim_tile_key = tile_dict['tile_key'][:self.default_aggregation_depth]
            if trim_tile_key not in aggregate_tiles:
                # Make the aggregate tile dictionary
                # object.
                chrono_t = ChronoTile()
                agg_dict = chrono_t.decode_path_dates(trim_tile_key)
                if (self.min_date is not None 
                    and agg_dict['earliest_bce'] < self.min_date):
                    # The aggregated date range looks too early, so
                    # set it to the earliest allowed.
                    agg_dict['earliest_bce'] = self.min_date
                if (self.max_date is not None 
                    and agg_dict['latest_bce'] > self.max_date):
                    # The aggregated date range looks too late, so
                    # set it to the latest date range allowed.
                    agg_dict['latest_bce'] = self.max_date
                agg_dict['tile_key'] = trim_tile_key
                agg_dict['count'] = 0
                aggregate_tiles[trim_tile_key] = agg_dict

            aggregate_tiles[trim_tile_key]['count'] += tile_dict['count']


        agg_tile_list = [tile_dict for _, tile_dict in aggregate_tiles.items()]
        
        # Now sort by earliest bce, then reversed latest bce
        # this makes puts early dates with longest timespans first
        sorted_agg_tiles = sorted(
            agg_tile_list,
            key=lambda k: (k['earliest_bce'], -k['latest_bce'])
        )

        options = []
        for tile_dict in sorted_agg_tiles:
            sl = SearchLinks(
                request_dict=copy.deepcopy(self.request_dict),
                base_search_url=self.base_search_url
            )
            # Remove non search related params.
            sl.remove_non_query_params()

            # Update the request dict for this facet option.
            sl.replace_param_value(
                'form-chronotile',
                match_old_value=None,
                new_value=tile_dict['tile_key'],
            )
            sl.replace_param_value(
                'form-start',
                match_old_value=None,
                new_value=tile_dict['earliest_bce'],
            )
            sl.replace_param_value(
                'form-stop',
                match_old_value=None,
                new_value=tile_dict['latest_bce'],
            )  
            urls = sl.make_urls_from_request_dict()
            if urls['html'] == self.current_filters_url:
                # The new URL matches our current filter
                # url, so don't add this facet option.
                continue

            option = LastUpdatedOrderedDict()
            option['id'] = urls['html']
            option['json'] = urls['json']
            option['count'] = tile_dict['count']
            option['category'] = 'oc-api:chrono-facet'
            option['start'] = ISOyears().make_iso_from_float(
                tile_dict['earliest_bce']
            )
            option['stop'] = ISOyears().make_iso_from_float(
                tile_dict['latest_bce']
            )
            properties = LastUpdatedOrderedDict()
            properties['early bce/ce'] = tile_dict['earliest_bce']
            properties['late bce/ce'] = tile_dict['latest_bce']
            option['properties'] = properties
            options.append(option)

        return options
        


