import re
import datetime
from django.conf import settings
from opencontext_py.apps.entities.entity.models import Entity
from opencontext_py.apps.ldata.linkannotations.recursion import LinkRecursion
from opencontext_py.apps.indexer.solrdocument import SolrDocument
from opencontext_py.apps.searcher.solrsearcher.querymaker import QueryMaker


class SpecialSearches():
    """ Methods to compose specialized searches
        on specific datasets in Open Context.
        These methods have dependencies on data in Open Context.
    """

    def __init__(self):
        pass

    def process_geo_projects(self, query):
        """ requests pivot facets for projects
            so as to make enriched GeoJSON for
            project facets
        """
        proj_field = SolrDocument.ROOT_PROJECT_SOLR
        query['facet.pivot.mincount'] = 1
        if 'facet.pivot' not in query:
            query['facet.pivot'] = []
        query['facet.pivot'].append(proj_field + ',discovery_geotile')
        query['facet.pivot'].append(proj_field + ',form_use_life_chrono_tile')
        return query
    
    def process_linked_dinaa(self, query):
        """ processes a request for DINAA sites that
            are cross referenced with tDAR or other
            online collections
        """
        rel_query_term = '((dc_terms_subject___pred_id:tdar*)'
        rel_query_term += ' OR (dc_terms_isreferencedby___pred_id:*))'
        if 'fq' not in query:
            query['fq'] = []
        query['fq'].append(rel_query_term)
        proj_field = SolrDocument.ROOT_PROJECT_SOLR
        proj_query = proj_field + ':52-digital-index-of-north-american-archaeology-dinaa*'
        query['fq'].append(proj_query)
        if 'facet.field' not in query:
            query['facet.field'] = []
        query['facet.field'].append('dc_terms_isreferencedby___pred_id')
        return query

    def process_trinonial_reconcile(self,
                                    trinomial,
                                    query):
        """ Processes a request to reconcile
            Smithsonian trinomials against
            DINAA data
        """
        if 'fq' not in query:
            query['fq'] = []
        query['hl'] = 'true'
        query['hl.fl'] = 'text'
        if 'hl.q' not in query:
            query['hl.q'] = ''
        query['hl.q'] += trinomial
        # first make sure we're searching in the DINAA project dataset
        proj_field = SolrDocument.ROOT_PROJECT_SOLR
        proj_query = proj_field + ':52-digital-index-of-north-american-archaeology-dinaa*'
        query['fq'].append(proj_query)
        # these are the fields that have trinomials to search
        trinomial_fields = ['52-smithsonian-trinomial-identifier',
                            '52-sortable-trinomial',
                            '52-variant-trinomial-expressions']
        tri_queries = []
        for tri_field in trinomial_fields:
            tri_field = tri_field.replace('-', '_')
            tri_field += '___pred_string'
            tri_query = '(' + tri_field + ':' + trinomial + ')'
            tri_queries.append(tri_query)
        all_tri_query = ' OR '.join(tri_queries)
        query['fq'].append(all_tri_query)
        return query

