import copy



from opencontext_py.libs.utilities import chronotiles
from opencontext_py.libs.isoyears import ISOyears
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.libs.rootpath import RootPath


from opencontext_py.apps.searcher.new_solrsearcher import configs
from opencontext_py.apps.searcher.new_solrsearcher.searchlinks import SearchLinks
from opencontext_py.apps.searcher.new_solrsearcher import utilities

# ---------------------------------------------------------------------
# Methods to generate results for chronology facets
# ---------------------------------------------------------------------

CHRONO_TILE_FACET_FIELDS = [
    f'{configs.ROOT_EVENT_CLASS}___chrono_tile',
    f'{configs.ROOT_EVENT_CLASS}___lr_chrono_tile',
]


class ResultFacetsChronologyFromDF():

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
        self.min_tile_depth = configs.MIN_CHRONOTILE_ZOOM
        self.default_aggregation_depth = configs.DEFAULT_CHRONOTILE_ZOOM
        self.default_max_tile_count = 30
        self.max_depth = configs.MAX_CHRONOTILE_ZOOM
        self.limiting_tile = None
        self.min_date = None  # bce / ce
        self.max_date = None  # bce / ce
        self.exclude_before = None  # bce / ce
        self.exclude_after = None # bce / ce
    

    def _set_client_earliest_latest_limits(self):
        """Sets earliest and latest date limits from the client"""
        all_start = utilities.get_request_param_value(
            self.request_dict,
            param='allevent-start',
            default=None,
            as_list=False,
            solr_escape=False,
            require_float=True,
        )
        if all_start:
            self.exclude_before = all_start
        all_stop = utilities.get_request_param_value(
            self.request_dict,
            param='allevent-stop',
            default=None,
            as_list=False,
            solr_escape=False,
            require_float=True,
        )
        if all_stop:
            self.exclude_after = all_stop
        all_tile = utilities.get_request_param_value(
            self.request_dict,
            param='allevent-chronotile',
            default=None,
            as_list=False,
            solr_escape=False,
        )
        if all_tile:
            self.limiting_tile = all_tile


    def _make_earliest_latest_date_cols_from_col_value(
        self,
        df,
        value_col='facet_value',
    ):
        """Makes columns of earliest and latest dates bce from a chronotile column"""
        df['chrono_dict'] = df[value_col].apply(
            chronotiles.decode_path_dates
        )
        df['earliest_bce_ce'] = df['chrono_dict'].str.get('earliest_bce_ce')
        df['latest_bce_ce'] = df['chrono_dict'].str.get('latest_bce_ce')
        df.drop(
            columns=['chrono_dict'],
            inplace=True,
        )
        return df


    def get_valid_tiles_df(self, facets_df):
        """Makes a list of valid tile_dicts from a list of options_tuples"""
        self._set_client_earliest_latest_limits()
        valid_index = (
            facets_df['facet_field_key'].isin(CHRONO_TILE_FACET_FIELDS)
        )
        if self.limiting_tile is not None:
            valid_index &= facets_df['facet_value'].str.startswith(self.limiting_tile)
        tiles_df = facets_df[valid_index].copy()
        tiles_df = self._make_earliest_latest_date_cols_from_col_value(
            df=tiles_df,
            value_col='facet_value',
        )
        index = ~tiles_df['facet_value'].isnull()
        if self.exclude_before is not None:
            index &= tiles_df['earliest_bce_ce'] >= self.exclude_before
        if self.exclude_after is not None:
            index &= tiles_df['latest_bce_ce'] <= self.exclude_after
        return tiles_df[index]


    def _time_range_adjust_chronodeep(self, deep):
        """Adjust the chronodeep value by time range"""
        if self.min_date is None or self.max_date is None:
            return deep
        range =  self.max_date - self.min_date
        if range <= 2500:
            # Don't chronological deep for short time ranges.
            return deep
        deep_less = round(range / 160, 0)
        # print(f'Initial deep: {deep} less {deep_less}, range: {range}')
        if deep_less >= deep:
            return deep
        return int(deep - deep_less)


    def _get_tile_aggregation_depth(self, tiles_df):
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
            deep, _ = utilities.get_aggregation_depth_to_group_paths_from_tiles_df(
                max_groups=self.default_max_tile_count,
                tiles_df=tiles_df,
                max_depth=self.max_depth,
            )
            deep = self._time_range_adjust_chronodeep(deep)
        # Now put some limits on it.
        if deep < self.min_tile_depth:
            deep = self.min_tile_depth
        if deep > self.max_depth:
            deep = self.max_depth
        self.default_aggregation_depth = deep
        return deep


    def make_chronology_facet_options(self, tiles_df):
        """Makes chronology facets from a solr_json response"""
        if tiles_df is None:
            return None
        
        if not len(tiles_df.index):
            return None
        
        self.min_date = tiles_df['earliest_bce_ce'].min()
        self.max_date = tiles_df['latest_bce_ce'].max()
        
        # Determine the aggregation depth needed to group chronological
        # tiles together into a reasonable number of options.
        deep = self._get_tile_aggregation_depth(tiles_df)

        # Make the aggregate tile based on our aggregation depth
        tiles_df['agg_tile'] = tiles_df['facet_value'].str[:deep]
        # Now aggregate the tiles together by summing all the facet counts
        # grouped into common agg_tiles
        grp_cols = [
            'agg_tile',
            'facet_count',
        ]
        df_g = tiles_df[grp_cols].groupby(['agg_tile'], as_index=False).sum()
        df_g.reset_index(drop=True, inplace=True)
        df_g = self._make_earliest_latest_date_cols_from_col_value(
            df=df_g,
            value_col='agg_tile',
        )
        index = ~df_g['agg_tile'].isnull()
        if self.min_date:
            index &= df_g['earliest_bce_ce'] >= self.min_date
        if self.max_date:
            index &= df_g['latest_bce_ce'] <= self.max_date
        df_g = df_g[index]
        # Now sort by earliest bce, then reversed latest bce
        # this makes puts early dates with longest timespans first
        df_g.sort_values(
            by=['earliest_bce_ce', 'latest_bce_ce', 'facet_count',], 
            ascending=[True, False, False],
            inplace=True,
        )
        options = []
        for _, row in df_g.iterrows():
            sl = SearchLinks(
                request_dict=copy.deepcopy(self.request_dict),
                base_search_url=self.base_search_url
            )
            # Remove non search related params.
            sl.remove_non_query_params()

            # Update the request dict for this facet option.
            sl.replace_param_value(
                'allevent-chronotile',
                match_old_value=None,
                new_value=row['agg_tile'],
            )
            sl.replace_param_value(
                'allevent-start',
                match_old_value=None,
                new_value=row['earliest_bce_ce'],
            )
            sl.replace_param_value(
                'allevent-stop',
                match_old_value=None,
                new_value=row['latest_bce_ce'],
            )
            urls = sl.make_urls_from_request_dict()
            if urls['html'] == self.current_filters_url:
                # The new URL matches our current filter
                # url, so don't add this facet option.
                continue

            option = LastUpdatedOrderedDict()
            option['id'] = urls['html']
            option['json'] = urls['json']
            option['count'] = row['facet_count']
            option['category'] = configs.DEFAULT_API_EVENT_ID
            option['start'] = ISOyears().make_iso_from_float(
                row['earliest_bce_ce']
            )
            option['stop'] = ISOyears().make_iso_from_float(
                row['latest_bce_ce']
            )
            properties = LastUpdatedOrderedDict()
            properties['early bce/ce'] = row['earliest_bce_ce']
            properties['late bce/ce'] = row['latest_bce_ce']
            option['properties'] = properties
            options.append(option)

        return options
