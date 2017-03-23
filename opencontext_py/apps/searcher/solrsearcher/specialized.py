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
        query['q'] = 'text:' + trinomial
        if 'hl.q' not in query:
            query['hl.q'] = ''
        query['hl.q'] += 'text:' + trinomial
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

    def process_reconcile(self,
                          reconcile,
                          query):
        """ Processes a request to reconcile
            linked data with biological taxonomies
        """
        """
        if isinstance(reconcile, list):
            qm = QueryMaker()
            prequery = query
            prequery.pop('facet.field', None)
            prequery['facet.field'] = []
            prequery['facet.field'].append(SolrDocument.ROOT_PROJECT_SOLR)
            if prequery['q'] == '*:*':
                prequery['q'] = ''
            prequery['q.op'] = 'AND'
            for recon_term in reconcile:
                escaped_terms = qm.prep_string_search_term(recon_term)
                prequery['q'] += ' '.join(escaped_terms)
            solr = self.solr_connect()
            response = self.solr.search(**prequery)  # execute solr query
            solr_json = response.raw_content
            if isinstance(solr_json, dict):
                if 'facet_counts' in solr_json:
                    if 'facet_fields' in solr_json['facet_counts']:
                        ffields = solr_json['facet_fields']
                        if SolrDocument.ROOT_PROJECT_SOLR in ffields:
                            projfacets = ffields[SolrDocument.ROOT_PROJECT_SOLR]    
            subquery = {}
            subquery['rows'] = 0
            subquery['q'] = '*:*'
            subquery['q.op'] = 'AND'
            subquery['fq'] = []
            subquery['fq'].append('item_type:types')
            subquery['facet'] = 'true'
            subquery['facet.mincount'] = 1
            subquery['facet.field'] = []
            subquery['facet.field'].append('skos_closematch___pred_id')
            for recon_term in reconcile:
                escaped_terms = qm.prep_string_search_term(recon_term)    
                act_filter_a = 'skos_closematch___pred_id:' + ' '.join(escaped_terms)
                act_filter_b = 'slug_type_uri_label:' + ' '.join(escaped_terms)
                act_filter = '((' + act_filter_a + ') OR (' + act_filter_b + '))'
                subquery['fq'].append(act_filter)
            solr = self.solr_connect()
            response = self.solr.search(**stats_query)  # execute solr query
            solr_json = response.raw_content
            if isinstance(solr_json, dict):
                if 'facet_counts' in solr_json:
                    if 'facet_fields' in solr_json['facet_counts']:
                        ffields = solr_json['facet_fields']
                        if 'skos_closematch___pred_id' in ffields:
                            
                if 'fq' not in query:
                    query['fq'] = []
                # nuke the facet fields to only get the item we want
                query.pop('facet.field', None)
                query['facet.field'] = []
                if isinstance(reconcile, list):
                    for recon_item in reconcile:
                        query['fq'].append('ld___pred_id_fq:biol-term-hastaxonomy')
                        query['fq'].append('item_type:subjects')
                        taxon_field = 'obj_all___biol_term_hastaxonomy___pred_id'
                        if taxon_field not in query['facet.field']: 
                            query['facet.field'].append(taxon_field)
        """
        return query
    
    def solr_connect(self):
        """ connects to solr """
        return SolrConnection(False).connection