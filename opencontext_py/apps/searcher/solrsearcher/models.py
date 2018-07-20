import time
import re
import json
import logging
from datetime import datetime
from django.conf import settings
from mysolr.compat import urljoin, compat_args, parse_response
from opencontext_py.libs.solrconnection import SolrConnection
from opencontext_py.libs.memorycache import MemoryCache
from opencontext_py.libs.general import LastUpdatedOrderedDict, DCterms
from opencontext_py.apps.indexer.solrdocument import SolrDocument
from opencontext_py.apps.searcher.solrsearcher.sorting import SortingOptions
from opencontext_py.apps.searcher.solrsearcher.querymaker import QueryMaker
from opencontext_py.apps.searcher.solrsearcher.specialized import SpecialSearches
from opencontext_py.apps.searcher.solrsearcher.statsquery import StatsQuery
from opencontext_py.apps.searcher.solrsearcher.projquery import ProjectsQuery

# This class is used to dereference URIs or prefixed URIs
# to get useful information about the entity
class SolrSearch():

    DEFAULT_FACET_FIELDS = [
        SolrDocument.ROOT_LINK_DATA_SOLR,
        SolrDocument.ROOT_PROJECT_SOLR,
        'image_media_count',
        'other_binary_media_count',
        'document_count'
    ]

    PROJECT_FACET_FIELDS = [
        # SolrDocument.ROOT_LINK_DATA_SOLR
        'dc_terms_subject___pred_id',
        'dc_terms_coverage___pred_id',
        'dc_terms_temporal___pred_id'
    ]

    # the number of rows to display by default for different item types
    ITEM_TYPE_ROWS = {'projects': 100}

    # the miniumum number of facets to display for different item types
    ITEM_TYPE_FACET_MIN = {'projects': 2}

    #facet fields for different item_types
    ITEM_TYPE_FACETFIELDS = {'projects': ['dc_terms_subject___pred_id',
                                          # 'dc_terms_temporal___pred_id',
                                          'dc_terms_spatial___pred_id',
                                          'dc_terms_coverage___pred_id'],
                             'subjects': ['oc_gen_subjects___pred_id']}

    ITEM_CAT_FIELDS = ['oc_gen_subjects___pred_id',
                       'oc_gen_media___pred_id',
                       'oc_gen_persons___pred_id']

    REL_CAT_FACET_FIELDS = ['rel__oc_gen_subjects___pred_id']
    GENERAL_STATS_FIELDS = ['updated',
                            'published']
    CHRONO_STATS_FIELDS =  ['form_use_life_chrono_earliest',
                            'form_use_life_chrono_latest']
    MEDIA_STATS_FIELDS = ['filesize___pred_numeric']

    def __init__(self):
        self.solr = False
        self.solr_connect()
        self.solr_response = False
        self.json_ld = False
        self.facet_fields = self.DEFAULT_FACET_FIELDS
        self.stats_fields = self.GENERAL_STATS_FIELDS
        self.rows = 20
        self.start = 0
        self.max_rows = 10000
        self.prequery_stats = []
        self.item_type_limit = False  # limit searches to a specific item type
        self.item_type_limited = False  # is an item_type_limit selected?
        self.do_context_paths = True  # make sure context paths are in the query
        self.is_bot = False
        self.do_bot_limit = False

    def solr_connect(self):
        """ connects to solr """
        self.solr = SolrConnection(False).connection

    def search_solr(self, request_dict_json):
        """searches solr to get raw solr search results"""
        # Start building solr query
        if self.item_type_limit == 'projects':
            self.facet_fields = self.PROJECT_FACET_FIELDS
        else:
            # add chronology stats fields, because its not just for projects
            self.stats_fields += self.CHRONO_STATS_FIELDS
        request_dict = json.loads(request_dict_json)
        query = self.compose_query(request_dict)
        if 'fq' in query:
            if isinstance(query['fq'], list):
                new_fq = []
                for old_fq in query['fq']:
                    if isinstance(old_fq, str):
                        new_fq.append(old_fq.replace('(())', ' '))
                query['fq'] = new_fq
        if self.do_bot_limit:
            # limit bots from requesting facets
            query['facet.field'] = []
            query['stats.field'] = []
        """
        try:
            response = self.solr.search(**query)
        except:
            # some hassels to handle project pivot queries
            response = KludgeSolrResponse()
            squery = response.build_request(query)
            url = urljoin(self.solr.base_url, 'select')
            http_response = self.solr.make_request.post(url,
                                                        data=squery,
                                                        timeout=240)
            response.raw_content = parse_response(http_response.content)
        """
        logger = logging.getLogger(__name__)
        # some hassels to handle project pivot queries
        response = KludgeSolrResponse()
        squery = response.build_request(query)
        url = urljoin(self.solr.base_url, 'select')
        try:
            http_response = self.solr.make_request.post(url,
                                                        data=squery,
                                                        timeout=240)
            response.raw_content = parse_response(http_response.content)
        except Exception as error:
            response = {}
            logger.error('[' + datetime.now().strftime('%x %X ') +
                         settings.TIME_ZONE + '] Error: ' + str(error)
                         + ' => Query: ' + str(squery))
        return response

    def compose_query(self, request_dict):
        """ composes the search query based on the request_dict """
        qm = QueryMaker()
        child_context_join = False # do a JOIN to include children in results
        query = {}
        query['facet'] = 'true'
        query['facet.mincount'] = 1
        query['rows'] = self.rows
        query['start'] = self.start
        query['debugQuery'] = 'false'
        query['fq'] = []
        query['facet.field'] = []
        query['facet.range'] = []
        query['stats'] = 'true'
        query['stats.field'] = self.stats_fields
        query['sort'] = SortingOptions.DEFAULT_SOLR_SORT
        s_param = self.get_request_param(request_dict,
                                         'sort',
                                         False,
                                         False)
        if s_param is not False:
            # add custom sorting
            sort_opts = SortingOptions()
            query['sort'] = sort_opts.make_solr_sort_param(s_param)
        # If the user does not provide a search term, search for everything
        query['q'] = '*:*'  # defaul search for all
        q_param = self.get_request_param(request_dict,
                                         'q',
                                         False,
                                         False)
        if q_param is not False:
            escaped_terms = qm.prep_string_search_term(q_param)
            query['q'] = 'text:' + ' '.join(escaped_terms)
            query['q.op'] = 'AND'
            query['hl'] = 'true'
            query['hl.fl'] = 'text'
            query['hl.q'] = 'text:' + ' '.join(escaped_terms)
        start = self.get_request_param(request_dict,
                                       'start',
                                       False,
                                       False)
        if start is not False:
            query['start'] = re.sub(r'[^\d]', r'', str(start))
        rows = self.get_request_param(request_dict,
                                      'rows',
                                      False,
                                      False)
        if rows is not False:
            rows = re.sub(r'[^\d]', r'', str(rows))
            rows = int(float(rows))
            if rows > self.max_rows:
                rows = self.max_rows
            elif rows < 0:
                rows = 0
            query['rows'] = rows
        # Spatial Context
        if 'path' in request_dict and self.do_context_paths:
            self.remove_from_default_facet_fields(SolrDocument.ROOT_CONTEXT_SOLR)
            print('context starts as: ' + str(request_dict['path']))
            context = qm._process_spatial_context(request_dict['path'])
            query['fq'].append(context['fq'])
            query['facet.field'] += context['facet.field']  # context facet fields, always a list
        # Properties and Linked Data
        props = self.get_request_param(request_dict,
                                       'prop',
                                       False,
                                       True)
        if props is not False:
            for act_prop in props:
                # process each prop independently.
                prop_query = qm.process_prop(act_prop)
                query['fq'] += prop_query['fq']
                query['facet.field'] += prop_query['facet.field']
                query['stats.field'] += prop_query['stats.field']
                query['facet.range'] += prop_query['facet.range']
                if 'ranges' in prop_query:
                    for key, value in prop_query['ranges'].items():
                        query[key] = value
                if 'hl-queries' in prop_query:
                    query['hl'] = 'true'
                    query['hl.fl'] = 'text'
                    # query['hl.snippets'] = 2
                    for q_term in prop_query['hl-queries']:
                        if 'hl.q' in query:
                            query['hl.q'] += ' OR (' + q_term + ')'
                        else:
                            query['hl.q'] = q_term
                if 'prequery-stats' in prop_query:
                    # we have fields that need a stats prequery
                    self.prequery_stats += prop_query['prequery-stats']
        # Project
        proj = self.get_request_param(request_dict,
                                      'proj',
                                      False)
        if proj is not False:
            # remove the facet field, since we're already filtering with it
            self.remove_from_default_facet_fields(SolrDocument.ROOT_PROJECT_SOLR)
            proj_query = qm.process_proj(proj)
            query['fq'] += proj_query['fq']
            query['facet.field'] += proj_query['facet.field']    
        # Dublin-Core terms
        dc_query_term_exists = False
        dc_terms_obj = DCterms()
        dc_params = dc_terms_obj.get_dc_params_list()
        for dc_param in dc_params:
            dc_terms = self.get_request_param(request_dict,
                                              dc_param,
                                              False,
                                              True)
            if dc_terms is not False:
                dc_query_term_exists = True
                dc_query = qm.process_dc_term(dc_param,
                                              dc_terms)
                query['fq'] += dc_query['fq']
                query['facet.field'] += dc_query['facet.field']
                if dc_param == 'dc-temporal':
                    child_context_join = False  # turn this off
        # item-types
        item_type = self.get_request_param(request_dict,
                                           'type',
                                           False,
                                           False)
        if item_type is not False:
            # remove the facet field, since we're already filtering with it
            self.remove_from_default_facet_fields('item_type')
            # indicate that the item_type_limit is in effect
            self.item_type_limited = True
            it_query = qm.process_item_type(item_type)
            query['fq'] += it_query['fq']
            query['facet.field'] += it_query['facet.field']
        """
        If a item_type_limit is set, then we're doing a specialized search
        that looks only for a certain item_type.
        """
        if self.item_type_limit is not False:
            # indicate that the item_type_limit is in effect
            self.item_type_limited = True
            query['fq'].append('item_type:' + self.item_type_limit)
            if self.item_type_limit in self.ITEM_TYPE_ROWS:
                query['rows'] = self.ITEM_TYPE_ROWS[self.item_type_limit]
            if self.item_type_limit in self.ITEM_TYPE_FACET_MIN:
                query['facet.mincount'] = self.ITEM_TYPE_FACET_MIN[self.item_type_limit]
                if dc_query_term_exists is True and query['facet.mincount'] > 1:
                    # we're already limiting by a DC terms search, so allow all
                    # search facets
                    query['facet.mincount'] = 1
            if self.item_type_limit in self.ITEM_TYPE_FACETFIELDS:
                for add_facet_field in self.ITEM_TYPE_FACETFIELDS[self.item_type_limit]:
                    if add_facet_field not in query['facet.field']:
                        # add facet field for this type of item
                        query['facet.field'].append(add_facet_field)
        else:
            cat_field_found = False
            for item_cat_field in self.ITEM_CAT_FIELDS:
                for facet_field in query['facet.field']:
                    if item_cat_field in facet_field:
                        cat_field_found = True
            if cat_field_found is False:
                query['facet.field'].append('item_type')
        """ CHRONOLOGY Form Use Life (form)
            queries
        """
        # now add form-use-life chronology
        form_chrono = self.get_request_param(request_dict,
                                             'form-chronotile',
                                             False,
                                             False)
        if form_chrono is not False:
            # query for form-use-live chronological tile
            form_chrono_query = qm.process_form_use_life_chrono(form_chrono)
            query['fq'] += form_chrono_query['fq']
            query['facet.field'] += form_chrono_query['facet.field']
            query['f.form_use_life_chrono_tile.facet.limit'] = -1
        else:
            # Add default form-use-life chronology
            query = self.add_root_form_use_life_chrono(query,
                                                       request_dict)
        form_start = self.get_request_param(request_dict,
                                            'form-start',
                                            False,
                                            False)
        if form_start is not False:
            # query for form-use-live start date
            form_start_query = qm.process_form_date_chrono(form_start,
                                                           'start')
            query['fq'] += form_start_query['fq']
        form_stop = self.get_request_param(request_dict,
                                           'form-stop',
                                           False,
                                           False)
        if form_stop is not False:
            # query for form-use-live stop date
            form_stop_query = qm.process_form_date_chrono(form_stop,
                                                          'stop')
            query['fq'] += form_stop_query['fq']
        """ Updated and Published Times
        """
        updated = self.get_request_param(request_dict,
                                         'updated',
                                         False,
                                         False)
        if updated is not False:
            # query for when the resource was updated
            query['fq'].append('updated:' + updated)
        published = self.get_request_param(request_dict,
                                           'published',
                                           False,
                                           False)
        if published is not False:
            # query for when the resource was published
            query['fq'].append('published:' + published)
        """
            query by uuid
            uri, or other identifier
        """
        uuid = self.get_request_param(request_dict,
                                      'uuid',
                                      False,
                                      False)
        if uuid is not False:
            query['fq'].append('uuid:' + uuid)
        identifier = self.get_request_param(request_dict,
                                            'id',
                                            False,
                                            False)
        if identifier is not False:
            id_query = qm.process_id(identifier)
            query['fq'] += id_query['fq']
        """ Linked media (images, documents, other)
            queries
        """
        # images
        images = self.get_request_param(request_dict,
                                        'images',
                                        False,
                                        False)
        if images is not False:
            query['fq'] += ['image_media_count:[1 TO *]']
        # other media (not images)
        other_media = self.get_request_param(request_dict,
                                             'other-media',
                                             False,
                                             False)
        if other_media is not False:
            query['fq'] += ['other_binary_media_count:[1 TO *]']
         # other media (not images)
        documents = self.get_request_param(request_dict,
                                           'documents',
                                           False,
                                           False)
        if documents is not False:
            query['fq'] += ['document_count:[1 TO *]']
        """ Geospatial (discovery location)
            queries
        """
        # now add discovery geo location
        disc_geo = self.get_request_param(request_dict,
                                          'disc-geotile',
                                          False,
                                          False)
        if disc_geo is not False:
            disc_geo_query = qm.process_discovery_geo(disc_geo)
            query['fq'] += disc_geo_query['fq']
            query['facet.field'] += disc_geo_query['facet.field']
            query['f.discovery_geotile.facet.limit'] = -1
        else:
            # Add default geofacet
            query = self.add_root_discovery_geo(query,
                                                request_dict)
        # geospatial bounding box query
        disc_bbox = self.get_request_param(request_dict,
                                           'disc-bbox',
                                           False,
                                           False)
        if disc_bbox is not False:
            disc_bbox_query = qm.process_discovery_bbox(disc_bbox)
            query['fq'] += disc_bbox_query['fq']
        # get items with a URI (or slug) indentified object
        obj = self.get_request_param(request_dict,
                                     'obj',
                                     False)
        if obj is not False:
            obj_query = qm.process_ld_object(obj)
            query['fq'] += obj_query['fq']
        """ -----------------------------------------
            Add default facet fields, used for most
            searches
            -----------------------------------------
        """
        query = self.add_default_facet_fields(query,
                                              request_dict)
        """ -----------------------------------------
            Additional, dataset specific specialized
            queries
            -----------------------------------------
        """
        # special queries (to simplify access to specific datasets)
        spsearch = SpecialSearches()
        response = self.get_request_param(request_dict,
                                          'response',
                                          False,
                                          False)
        if response is not False:
            if 'geo-project' in response:
                # request for special handling of project facets with
                # added geospatial and chronological metadata
                query = spsearch.process_geo_projects(query)
        linked = self.get_request_param(request_dict,
                                        'linked',
                                        False,
                                        False)
        if linked == 'dinaa-cross-ref':
            query = spsearch.process_linked_dinaa(query)
        trinomial = self.get_request_param(request_dict,
                                           'trinomial',
                                           False,
                                           False)
        if trinomial is not False:
            query = spsearch.process_trinonial_reconcile(trinomial,
                                                         query)
        reconcile = self.get_request_param(request_dict,
                                           'reconcile',
                                           False,
                                           True)
        if reconcile is not False:
            query = spsearch.process_reconcile(reconcile,
                                               query)
        if len(self.prequery_stats) > 0:
            #  we have fields that need a stats prequery
            statsq = StatsQuery()
            statsq.q = query['q']
            if 'q.op' in query:
                statsq.q_op = query['q.op']
            statsq.fq = query['fq']
            statsq.stats_fields = self.prequery_stats
            query = statsq.add_stats_ranges_from_solr(query)
        if child_context_join:
            all_fq = False
            for fq in query['fq']:
                if all_fq is False:
                    all_fq = '(' + fq + ')'
                else:
                    all_fq += ' AND (' + fq + ')'
            all_fq = '(' + all_fq + ')'
            joined_fq = '{!join from=slug_type_uri_label to=obj_all___context_id}' + all_fq 
            query['fq'] = all_fq + ' OR _query_:"' + joined_fq + '"'
        # now clean the stats fields to make sure we're not repeading ourselves
        if len(query['stats.field']) > 0:
            unique_stats_fields = []
            for stats_field in query['stats.field']:
                if stats_field not in unique_stats_fields:
                    unique_stats_fields.append(stats_field)
            query['stats.field'] = unique_stats_fields
        return query

    def remove_from_default_facet_fields(self, field):
        """ removes a field from the default facet fields """
        if isinstance(self.facet_fields, list):
            if field in self.facet_fields:
                self.facet_fields.remove(field)

    def add_default_facet_fields(self,
                                 query,
                                 request_dict):
        """ adds additional facet fields to query """
        if isinstance(self.facet_fields, list):
            for default_field in self.facet_fields:
                if default_field not in query['facet.field']:
                    query['facet.field'].append(default_field)
            if 'proj' in request_dict:
                if SolrDocument.ROOT_PREDICATE_SOLR not in query['facet.field']:
                    query['facet.field'].append(SolrDocument.ROOT_PREDICATE_SOLR)
                    # we need to request a disc_geosource to get polygon regions of contexts
                    query['facet.field'].append('disc_geosource')
                    query['f.disc_geosource.facet.limit'] = -1
            elif SolrDocument.ROOT_PROJECT_SOLR not in query['facet.field']:
                if self.item_type_limit != 'projects':
                    query['facet.field'].append(SolrDocument.ROOT_PROJECT_SOLR)
            if 'proj' not in request_dict and isinstance(self.item_type_limit, str):
                """ -----------------------------------------
                    In cases where no project parameter was chosen,
                    add project descriptive fields, by checking if
                    we have only 1 project in a result
                    -----------------------------------------
                """
                pq_obj = ProjectsQuery()
                single_project_ok = pq_obj.check_single_project(query)
                if single_project_ok:
                    if SolrDocument.ROOT_PREDICATE_SOLR not in query['facet.field']:
                        query['facet.field'].append(SolrDocument.ROOT_PREDICATE_SOLR)
                        # we need to request a disc_geosource to get polygon regions of contexts
                        query['facet.field'].append('disc_geosource')
                        query['f.disc_geosource.facet.limit'] = -1
        return query

    def add_root_discovery_geo(self,
                               query,
                               request_dict):
        """ add base discovery - geo """
        if 'disc-geotile' not in request_dict:
            query['facet.field'].append('discovery_geotile')
            query['f.discovery_geotile.facet.limit'] = -1
        return query

    def add_root_form_use_life_chrono(self,
                                      query,
                                      request_dict):
        """ adds facet field for the most commonly
            used chronology description, when the
            item was created / formed, used, and
            or lived:
            form_use_life_chrono_tile
        """
        if 'form-chronotile' not in request_dict:
            query['facet.field'].append('form_use_life_chrono_tile')
            query['f.form_use_life_chrono_tile.facet.limit'] = -1
        return query

    def get_request_param(self,
                          request_dict,
                          param,
                          default,
                          as_list=False,
                          solr_escape=False):
        """ get a string or list to use in queries from either
            the request object or the internal_request object
            so we have flexibility in doing searches without
            having to go through HTTP
        """
        if request_dict is not False:
            if as_list:
                if param in request_dict:
                    param_obj = request_dict[param]
                    if isinstance(param_obj, list):
                        output = param_obj
                    else:
                        if solr_escape:
                            param_obj = '"' + param_obj + '"'
                        output = [param_obj]
                else:
                    output = default
            else:
                if param in request_dict:
                    output = request_dict[param]
                    if isinstance(output, list):
                        output = output[0]
                    if solr_escape:
                        qm = QueryMaker()
                        if output[0] == '"' and output[-1] == '"':
                            output = qm.escape_solr_arg(output[1:-1])
                            output = '"' + output + '"'
                        else:
                            output = qm.escape_solr_arg(output)
                else:
                    output = default
        else:
            output = False
        return output

    def make_request_obj_dict(self, request, spatial_context):
        """ makes the Django request object into a dictionary obj """
        new_request = LastUpdatedOrderedDict()
        if spatial_context is not None:
            new_request['path'] = spatial_context
        else:
            new_request['path'] = False
        if request is not False:
            for key, key_val in request.GET.items():  # "for key in request.GET" works too.
                new_request[key] = request.GET.getlist(key)
        return new_request


class KludgeSolrResponse():
    """ A kludgy way around the lack of support for pivot facets
        in MySolr
    """
    def __init__(self):
        self.raw_content = False

    def build_request(self, query):
        """ Check solr query and put convenient format """
        assert 'q' in query
        compat_args(query)
        query['wt'] = 'json'
        return query
