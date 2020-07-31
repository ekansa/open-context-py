import copy
import json
import logging
import re
import time
from datetime import datetime
from django.conf import settings
from mysolr.compat import urljoin, compat_args, parse_response

from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.libs.memorycache import MemoryCache
from opencontext_py.libs.solrconnection import SolrConnection

from opencontext_py.apps.searcher.new_solrsearcher import configs
from opencontext_py.apps.searcher.new_solrsearcher import utilities



def compose_stats_query(fq_list=[], stats_fields_list=[], q='*:*'):
    """Compose a stats query to get stats for solr fields for ranges"""
    query_dict = {}
    query_dict['debugQuery'] = 'false'
    query_dict['stats'] = 'true'
    query_dict['wt'] = 'json'
    query_dict['rows'] = 0
    query_dict['q'] = q
    query_dict['fq'] = fq_list
    query_dict['stats.field'] = stats_fields_list
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
            solr = SolrConnection(
                exit_on_error=False,
                solr_host=settings.SOLR_HOST_TEST,
                solr_port=settings.SOLR_PORT_TEST,
                solr_collection=settings.SOLR_COLLECTION_TEST
            ).connection
        else:
            # Connect to the default solr server
            solr = SolrConnection(False).connection

    response = solr.search(**stats_query)  # execute solr query
    solr_json = response.raw_content
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
        fstart = 'f.{}.facet.range.start'.format(solr_field_key)
        fend = 'f.{}.facet.range.end'.format(solr_field_key)
        fgap = 'f.{}.facet.range.gap'.format(solr_field_key)
        findex = 'f.{}.facet.range.sort'.format(solr_field_key)
        fother = 'f.{}.facet.range.other'.format(solr_field_key)
        finclude = 'f.{}.facet.range.include'.format(solr_field_key)
        query_dict[fother] = 'all'
        query_dict[finclude] = 'all'
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
            query_dict[fstart] = int(round(stats['min'], 0))
            query_dict[fend] = int(round(stats['max'], 0))
            query_dict[fgap] = int(round(((stats['max'] - stats['min']) / group_size), 0))
            if query_dict[fgap] > stats['mean']:
                query_dict[fgap] = int(round((stats['mean'] / 3), 0))
            if query_dict[fgap] < 1:
                query_dict[fgap] = 1
        else:
            query_dict[fstart] = stats['min']
            query_dict[fend] = stats['max']
            query_dict[fgap] = ((stats['max'] - stats['min']) / group_size)
            if query_dict[fgap] > stats['mean']:
                query_dict[fgap] = stats['mean'] / 3
            if query_dict[fgap] == 0:
                query_dict[fgap] = 0.001
    return query_dict