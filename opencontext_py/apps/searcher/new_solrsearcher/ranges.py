
from opencontext_py.libs.solrclient import SolrClient

from opencontext_py.apps.searcher.new_solrsearcher import configs
from opencontext_py.apps.searcher.new_solrsearcher import utilities



def compose_stats_query(fq_list=[], stats_fields_list=[], facet_fields=[], q='*:*'):
    """Compose a stats query to get stats for solr fields for ranges

    :param list fq_list: List of facet-query terms
    :param list stats_fields_list: List of fields for stats
    :param list facet_fields: List of fields to get facet counts
    :param str q: The solr q query condition
    """
    query_dict = {}
    query_dict['debugQuery'] = 'false'
    query_dict['stats'] = 'true'
    query_dict['wt'] = 'json'
    query_dict['rows'] = 0
    query_dict['q'] = q
    query_dict['fq'] = fq_list
    query_dict['stats.field'] = stats_fields_list
    if facet_fields:
        query_dict['facet'] = 'true'
        query_dict['facet.mincount'] = 1
        query_dict['facet.field'] = facet_fields
    return query_dict


def stats_ranges_query_dict_via_solr(
    stats_query,
    default_group_size=20,
    solr=None,
    return_pre_query_response=False):
    """ Makes stats range facet query dict by processing a solr query
    """
    if not solr:
        # Connect to solr.
        if configs.USE_TEST_SOLR_CONNECTION:
            # Connect to the testing solr server
            solr = SolrClient(use_test_solr=True).solr
        else:
            # Connect to the default solr server
            solr =  SolrClient().solr

    results = solr.search(**stats_query)
    solr_json = results.raw_response
    if not isinstance(solr_json, dict):
        return None

    if not 'stats' in solr_json:
        return None

    if not 'stats_fields' in solr_json['stats']:
        return None

    query_dict = {}
    if return_pre_query_response:
        # This is for testing purposes.
        query_dict['pre-query-response'] = solr_json
    query_dict['facet.range'] = []
    query_dict['stats.field'] = []
    for solr_field_key, stats in solr_json['stats']['stats_fields'].items():
        group_size = default_group_size
        if not stats or not stats.get('count'):
            continue
        if solr_field_key not in query_dict['facet.range']:
            query_dict['facet.range'].append(solr_field_key)
        if solr_field_key not in query_dict['stats.field']:
            query_dict['stats.field'].append(solr_field_key)
        fstart = f'f.{solr_field_key}.facet.range.start'
        fend = f'f.{solr_field_key}.facet.range.end'
        fgap = f'f.{solr_field_key}.facet.range.gap'
        findex = f'f.{solr_field_key}.facet.range.sort'
        fother = f'f.{solr_field_key}.facet.range.other'
        finclude = f'f.{solr_field_key}.facet.range.include'
        fmin = f'f.{solr_field_key}.facet.mincount'
        query_dict[fother] = 'all'
        query_dict[finclude] = 'lower'
        query_dict[findex] = 'index'  # sort by index, not by count
        if (stats['count'] / group_size) < 3:
            group_size = 4
        if solr_field_key.endswith('___pred_date'):
            query_dict[fstart] = utilities.convert_date_to_solr_date(
                stats['min']
            )
            query_dict[fend] = utilities.convert_date_to_solr_date(
                stats['max']
            )
            query_dict[fgap] = utilities.get_date_difference_for_solr(
                stats['min'],
                stats['max'],
                group_size
            )
        elif solr_field_key.endswith('___pred_int'):
            min_val =  int(round(stats['min'], 0))
            max_val = int(round(stats['max'], 0)) + 1
            gap = int(round(((stats['max'] - stats['min']) / group_size), 0))
            if gap > stats['mean']:
                gap = int(round((stats['mean'] / 3), 0))
            if gap < 1:
                gap = 1
            query_dict[fmin] = 0
            query_dict[fstart] = min_val
            query_dict[fend] = max_val
            query_dict[fgap] = gap
        else:
            gap =  ((stats['max'] - stats['min']) / group_size)
            if gap > stats['mean']:
                gap = stats['mean'] / 3
            if gap < 0:
                gap = gap * -1
            if gap == 0:
                gap = 0.001
            if ((stats['max'] - stats['min']) / gap) > 75:
                gap =  ((stats['max'] - stats['min']) / group_size)
            min_val = stats['min']
            max_val = stats['max'] + (gap / 10)
            query_dict[fmin] = 0
            query_dict[fstart] = min_val
            query_dict[fend] = max_val
            query_dict[fgap] = gap
    return query_dict