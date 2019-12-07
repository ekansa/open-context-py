import copy
import logging
import time


from opencontext_py.apps.ocitems.subjects.models import Subject
from opencontext_py.apps.ocitems.manifest.models import Manifest

from opencontext_py.apps.searcher.new_solrsearcher.searchsolr import SearchSolr


# NOTE: This is for testing the speed of different solr
# queries. 
#
# Currently, this tests the speed of various filter queries in Solr.
# it seems to indicate that there is no real speed difference
# between a complete / perfect string pattern match and a string
# pattern match that ends with a wild card.

"""
Invoke with:

from opencontext_py.apps.searcher.new_solrsearcher.speedcheck import (
    make_context_query_list,
    check_solr_queries,
)
query_list = make_context_query_list()
check_solr_queries(query_list)

"""


logger = logging.getLogger(__name__)


BASE_SOLR_QUERY = {
    'facet': True,
    'facet.mincount': 1,
    'rows': 20,
    'start': 0,
    'debugQuery': True,
    'facet.field': [],
    'wt': 'json',
    'q': '*:*',
}


def make_context_query_list():
    """Makes a list of tuples for testing context queries"""
    # Gets all the "root" level subject items
    subs = Subject.objects.all().exclude(
        context__contains="/"
    )
    uuids = [s.uuid for s in subs]
    mans = Manifest.objects.filter(
        uuid__in=uuids, item_type='subjects'
    ).order_by('label')
    query_list = []
    for m in mans:
        # NOTE: qs is a list of different ways to query
        # for the spatial context entity "m" (a manifest object).
        qs = [
            'root___context_id:{}*'.format(m.slug),
            'root___context_id:{}___*'.format(m.slug),
            'root___context_id:{}___id___/subjects/{}___{}'.format(
                m.slug,
                m.uuid,
                m.label
            ),
            'root___context_id_fq:{}'.format(m.slug),
        ]
        query_list += [(q, {'fq':[q], 'facet.field':['root___context_id']},) for q in qs]
    return query_list


def check_solr_queries(query_list):
    """Checks on the speed of solr queries"""
    s_solr = SearchSolr()
    for note, query_part in query_list:
        # Below is a fancy new Python method to combine dicts.
        # This combines the standard, BASE_SOLR_QUERY dict with the
        # query_part that we want to evaluate for speediness.
        query = {**BASE_SOLR_QUERY, **query_part}
        start = time.time()
        # Now actually do the request to solr...
        resp = s_solr.query_solr(query)
        end = time.time()
        elapsed = end - start
        found = False
        if resp and 'response' in resp:
            found = resp['response']['numFound'] 
        print('{} found {} in {}'.format(
            note, found, elapsed)
        )