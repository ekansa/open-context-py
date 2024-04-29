import logging
import pandas as pd

from opencontext_py.apps.searcher.new_solrsearcher import configs
from opencontext_py.apps.searcher.new_solrsearcher import utilities


def make_df_of_solr_facets(solr_json, path_keys_list=configs.FACETS_SOLR_ROOT_PATH_KEYS):
    """Make a Pandas Dataframe with a matrix of facet_fields, facet_values, and facet_counts
    
    :param dict solr_json: A dictionary derived from the raw solr query request response
    :param list path_keys_list: List of keys to identify the facet fields
        and their facet values and counts
    
    returns DataFrame df
    """
    all_facets_dict = utilities.get_dict_path_value(
        path_keys_list,
        solr_json,
        default={}
    )
    rows = []
    for facet_key, solr_facet_value_count_list in all_facets_dict.items():
        if not solr_facet_value_count_list or not isinstance(solr_facet_value_count_list, list):
            continue
        for i in range(0, len(solr_facet_value_count_list), 2):
            facet_value = solr_facet_value_count_list[i]
            facet_count = solr_facet_value_count_list[(i + 1)]
            row = {'facet_field_key': facet_key, 'facet_value': facet_value, 'facet_count': facet_count}
            rows.append(row)
    df = pd.DataFrame(data=rows)
    return df
