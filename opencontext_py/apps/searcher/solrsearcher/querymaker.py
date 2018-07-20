import re
import datetime
import itertools
import django.utils.http as http
from django.http import Http404
from opencontext_py.libs.general import LastUpdatedOrderedDict, DCterms
from opencontext_py.libs.memorycache import MemoryCache
from opencontext_py.apps.entities.entity.models import Entity
from opencontext_py.apps.entities.uri.models import URImanagement
from opencontext_py.apps.indexer.solrdocument import SolrDocument
from opencontext_py.apps.ldata.linkannotations.recursion import LinkRecursion
from opencontext_py.apps.ldata.linkannotations.equivalence import LinkEquivalence
from opencontext_py.apps.ocitems.assertions.containment import Containment
from opencontext_py.apps.ocitems.assertions.math import MathAssertions
from opencontext_py.apps.searcher.solrsearcher.caching import SearchGenerationCache


class QueryMaker():

    # main item-types mapped to their slugs to get solr-facet field prefix
    TYPE_MAPPINGS = {'subjects': 'oc-gen-subjects',
                     'media': 'oc-gen-media',
                     'documents': 'oc-gen-documents',
                     'persons': 'oc-gen-persons',
                     'projects': 'oc-gen-projects',
                     'types': 'oc-gen-types',
                     'predicates': 'oc-gen-predicates',
                     'tables': 'oc-gen-tables'}

    TYPE_URIS = {'subjects': 'oc-gen:subjects',
                 'media': 'oc-gen:media',
                 'documents': 'oc-gen:documents',
                 'persons': 'oc-gen:persons',
                 'projects': 'oc-gen:projects',
                 'types': 'oc-gen:types',
                 'predicates': 'oc-gen:predicates',
                 'tables': 'oc-gen:tables'}

    def __init__(self):
        self.error = False
        self.histogram_groups = 10
        self.m_cache = MemoryCache() # memory caching object
        self.s_cache = SearchGenerationCache() # supplemental caching object, specific for searching

    def _get_context_paths(self, spatial_context):
        '''
        Takes a context path and returns an iterator with the list of possible
        contexts. Parses the list of boolean '||' (OR) and returns a list
        of contexts.

        For example:

        >>> _get_context_paths('Turkey/Domuztepe/I||II||Stray')

        ['Turkey/Domuztepe/I', 'Turkey/Domuztepe/II', 'Turkey/Domuztepe/Stray']

        '''
        # Split the context path by '/' and then by '||'
        context_lists = (value.split('||') for value in
                         spatial_context.split('/'))
        # Create a list of the various permutations
        context_tuple_list = list(itertools.product(*context_lists))
        # Turn the lists back into URIs
        return ('/'.join(value) for value in context_tuple_list)

    def _get_context_depth(self, spatial_context):
        '''
        Takes a context path and returns its depth as an interger. For
        example, the context '/Turkey/Domuztepe'
        would have a depth of 2.
        '''
        # Remove a possible trailing slash before calculating the depth
        return len(spatial_context.rstrip('/').split('/'))

    def _get_valid_context_slugs(self, contexts):
        '''
        Takes a list of contexts and, for valid contexts, returns a list of
        slugs
        '''
        valid_context_slugs = []
        context_list = list(contexts)
        for context in context_list:
            # Verify that the contexts are valid
            # find and save the enity to memory
            context = context.replace('+', ' ')
            context = context.replace('%20', ' ')
            # print('check: ' + context)
            entity = self.m_cache.get_entity_by_context(context)
            if entity:
                valid_context_slugs.append(entity.slug)
        # print('context-slugs: ' + str(valid_context_slugs))
        return valid_context_slugs

    def _get_parent_slug(self, slug):
        '''
        Takes a slug and returns the slug of its parent. Returns 'root' if
        a slug has no parent.
        '''
        cache_key = self.m_cache.make_cache_key('par-slug', slug)
        parent_slug = self.m_cache.get_cache_object(cache_key)
        if parent_slug is None:
            contain_obj = Containment()
            contain_obj.use_cache = False  # because it seems to introduce memory errors
            parent_slug = contain_obj.get_parent_slug_by_slug(slug)
            self.m_cache.save_cache_object(cache_key, parent_slug)
        if parent_slug:
            return parent_slug
        else:
            return 'root'

    def _prepare_filter_query(self, parent_child_slug):
        # TODO docstring
        parent_child_set = parent_child_slug.split('___')
        return parent_child_set[0].replace('-', '_') + '___context_id_fq:' + \
            parent_child_set[1]

    def expand_hierarchy_options(self,
                                 path_param_val,
                                 hier_delim='---',
                                 or_delim='||'):
        """ Exapands a hiearchic path string into a
            list of listed hierachically ordered items.
            This method also makes a new hiearchic ordered
            list if there is an 'or_delim'.
        """
        if isinstance(path_param_val, list):
            inital_path_list = path_param_val
        else:
            inital_path_list = [path_param_val]
        path_list = []
        for path_string in inital_path_list:
            raw_path_list = (value.split(or_delim) for value in
                             path_string.split(hier_delim))
            # Create a list of the various permutations
            path_tuple_list = list(itertools.product(*raw_path_list))
            for item in path_tuple_list:
                path_list.append(list(item))
        return path_list

    def get_solr_field_type(self, data_type, prefix=''):
        '''
        Defines whether our dynamic solr fields names for
        predicates end with ___pred_id, ___pred_numeric, etc.
        '''
        if data_type in ['@id', 'id', False]:
            return prefix + 'id'
        elif data_type in ['xsd:integer', 'xsd:double', 'xsd:boolean']:
            return prefix + 'numeric'
        elif data_type == 'xsd:string':
            return prefix + 'string'
        elif data_type == 'xsd:date':
            return prefix + 'date'
        else:
            raise Exception("Error: Unknown predicate type")

    def make_prop_solr_field_parts(self, entity):
        """ Makes a solr field for a property """
        output = {}
        output['prefix'] = entity.slug.replace('-', '_')
        output['suffix'] = self.get_solr_field_type(entity.data_type)
        return output

    def process_proj(self, proj_path):
        # TODO docstring
        query_dict = {'fq': [],
                      'facet.field': []}
        fq_terms = []
        project_path_lists = self.expand_hierarchy_options(proj_path)
        for proj_path_list in project_path_lists:
            i = 0
            path_list_len = len(proj_path_list)
            fq_field = SolrDocument.ROOT_PROJECT_SOLR
            fq_path_terms = []
            for proj_slug in proj_path_list:
                entity = self.m_cache.get_entity(proj_slug)
                if entity:
                    # fq_path_term = fq_field + ':' + self.make_solr_value_from_entity(entity)
                    # the below is a bit of a hack. We should have a query field
                    # as with ___pred_ to query just the slug. But this works for now
                    proj_slug = entity.slug
                    if len(proj_slug) > 56:
                        proj_slug = proj_slug[0:56]
                    fq_path_term = fq_field + ':' + proj_slug + '*'
                    if entity.par_proj_man_obj is not False and \
                       fq_field == SolrDocument.ROOT_PROJECT_SOLR:
                        # this entity has a parent object, so make sure to look for it as a child of
                        # that parent project
                        alt_fq_field = entity.par_proj_man_obj.slug.replace('-', '_') + '___project_id'
                        alt_fq_term = alt_fq_field + ':' + proj_slug + '*'
                        fq_path_term = ' (' + fq_path_term + ' OR ' + alt_fq_term + ' ) '
                else:
                    fq_path_term = fq_field + ':' + proj_slug
                fq_path_terms.append(fq_path_term)
                fq_field = proj_slug.replace('-', '_') + '___project_id'
                i += 1
                if i >= path_list_len and fq_field not in query_dict['facet.field']:
                    query_dict['facet.field'].append(fq_field)
            final_path_term = ' AND '.join(fq_path_terms)
            final_path_term = '(' + final_path_term + ')'
            fq_terms.append(final_path_term)
        fq_final = ' OR '.join(fq_terms)
        fq_final = '(' + fq_final + ')'
        query_dict['fq'].append(fq_final)
        return query_dict

    def process_ld_object(self, objects):
        # TODO docstring
        query_dict = {'fq': []}
        fq_terms = []
        if not isinstance(objects, list):
            objects = [objects]
        for raw_obj in objects:
            if '||' in raw_obj:
                or_objects = raw_obj.split('||')
            else:
                or_objects = [raw_obj]
            fq_or_terms = []
            for obj in or_objects:
                # find and save the entity to memory
                entity = self.m_cache.get_entity(obj)
                if entity:
                    fq_term = 'object_uri:' + self.escape_solr_arg(entity.uri)
                    fq_term += ' OR text:"' + self.escape_solr_arg(entity.uri) + '"'
                else:
                    fq_term = 'object_uri:' + obj
                fq_or_terms.append(fq_term)
            fq_all_ors = ' OR '.join(fq_or_terms)
            fq_all_ors = '(' + fq_all_ors + ')'
            fq_terms.append(fq_all_ors)
        fq_final = ' AND '.join(fq_terms)
        fq_final = '(' + fq_final + ')'
        query_dict['fq'].append(fq_final)
        return query_dict

    def process_dc_term(self, dc_param, dc_terms, add_facet=False):
        # TODO docstring
        query_dict = {'fq': [],
                      'facet.field': []}
        fq_terms = []
        if dc_param in DCterms.DC_META_FIELDS:
            fq_field = DCterms.DC_META_FIELDS[dc_param]
            if fq_field not in query_dict['facet.field'] and add_facet:
                query_dict['facet.field'].append(fq_field)
            add_to_fq = False
            for raw_dc_term in dc_terms:
                if '||' in raw_dc_term:
                    use_dc_terms = raw_dc_term.split('||')
                else:
                    use_dc_terms = [raw_dc_term]
                fq_path_terms = []
                for dc_term in use_dc_terms:
                    if len(dc_term) > 0:
                        add_to_fq = True
                        # check if entity exists, and or store in memory
                        entity = self.m_cache.get_entity(dc_term)
                        if entity:
                            # fq_path_term = fq_field + ':' + self.make_solr_value_from_entity(entity)
                            # the below is a bit of a hack. We should have a query field
                            # as with ___pred_ to query just the slug. But this works for now
                            fq_path_term = '(' + fq_field + '_fq:' + entity.slug + ')'
                            fq_path_term += ' OR (' + fq_field + ':' + entity.slug + '*)'
                            fq_path_term += ' OR (obj_all___' + fq_field + ':' + entity.slug + '___*)'
                            fq_path_term += '(' + fq_path_term + ')'
                            # print('vocab: ' + str(entity.vocabulary))
                            if entity.vocabulary == entity.label:
                                par_slug_part = entity.slug.replace('-', '_')
                                child_facet_field = par_slug_part + '___' + fq_field
                                print('adding: ' + child_facet_field)
                                query_dict['facet.field'].append(child_facet_field)
                            if dc_param == 'dc-temporal' \
                               and entity.entity_type == 'vocabulary' \
                               and 'periodo' in entity.slug:
                                # it's a temporal vocabulary from periodo
                                # so search for specific periods contained in
                                # the vocabulary
                                fq_path_term = '(' + fq_path_term +\
                                               ' OR ' + fq_path_term + '*)'
                        else:
                            if dc_term[-1] != '*':
                                dc_term += '*'
                            fq_path_term = fq_field + ':' + dc_term
                        fq_path_terms.append(fq_path_term)
                final_path_term = ' OR '.join(fq_path_terms)
                final_path_term = '(' + final_path_term + ')'
                fq_terms.append(final_path_term)
            fq_final = ' AND '.join(fq_terms)
            fq_final = '(' + fq_final + ')'
            if add_to_fq:
                query_dict['fq'].append(fq_final)
        return query_dict

    def get_related_slug_field_prefix(self, slug):
        """ gets the field prefix for a related property
            if it is present in the slug, 
            then return the solr_field prefix otherwise
            return a '' string
        """
        field_prefix = SolrDocument.RELATED_SOLR_FIELD_PREFIX
        prefix_len = len(field_prefix)
        slug_start = slug[:prefix_len]
        if slug_start == field_prefix:
            return field_prefix
        else:
            return ''

    def clean_related_slug(self, slug):
        """ removes the field_prefix for related slugs """
        field_prefix = SolrDocument.RELATED_SOLR_FIELD_PREFIX
        prefix_len = len(field_prefix)
        slug_start = slug[:prefix_len]
        if slug_start == field_prefix:
            slug = slug[prefix_len:]
        return slug

    def correct_solr_prefix_for_fq(self, solr_f_prefix, act_field_fq):
        """ makes sure the solr prefix is on the fq if needed """
        if solr_f_prefix != '':
            if solr_f_prefix not in act_field_fq:
                act_field_fq = solr_f_prefix + act_field_fq
        return act_field_fq

    def process_prop(self, props):
        """ processes 'prop' (property) parameters
            property parameters are tricky because they
            can come in hierarchies
            that's why there's some complexity to this
        """
        # is the property for the item itself, or for a related item?
        query_dict = {'fq': [],
                      'facet.field': [],
                      'stats.field': [],
                      'prequery-stats': [],
                      'facet.range': [],
                      'hl-queries': [],
                      'ranges': {}}
        fq_terms = []
        prop_path_lists = self.expand_hierarchy_options(props)
        for prop_path_list in prop_path_lists:
            i = 0
            path_list_len = len(prop_path_list)
            fq_path_terms = []
            act_field_fq = SolrDocument.ROOT_PREDICATE_SOLR
            act_field_data_type = 'id'
            last_field_label = False  # needed for full text highlighting
            predicate_solr_slug = False
            for prop_slug in prop_path_list:
                field_prefix = self.get_related_slug_field_prefix(prop_slug)
                solr_f_prefix = field_prefix.replace('-', '_')
                db_prop_slug = self.clean_related_slug(prop_slug)
                l_prop_entity = False
                pred_prop_entity = False
                require_id_field = False
                if act_field_data_type == 'id':
                    # check entity exists, and save to memory
                    entity = self.m_cache.get_entity(db_prop_slug)
                    if entity:
                        last_field_label = entity.label
                        prop_slug = field_prefix + entity.slug
                        if entity.item_type == 'uri' and not db_prop_slug.startswith('oc-gen'):
                            if entity.entity_type == 'property':
                                pred_prop_entity = True
                                predicate_solr_slug = prop_slug.replace('-', '_')
                                l_prop_entity = True
                                children = LinkRecursion().get_entity_children(entity.uri)
                                if len(children) > 0:
                                    # ok, this field has children. require it
                                    # to be treated as an ID field
                                    require_id_field = True
                        else:
                            if entity.item_type == 'predicates':
                                pred_prop_entity = True
                                predicate_solr_slug = prop_slug.replace('-', '_')
                                children = LinkRecursion().get_entity_children(entity.uri)
                                if len(children) > 0:
                                    # ok, this field has children. require it
                                    # to be treated as an ID field
                                    require_id_field = True
                        if i == 0:
                            if db_prop_slug.startswith('oc-gen'):
                                # for open context categories / types
                                act_field_fq = self.get_parent_item_type_facet_field(entity.uri)
                                lr = LinkRecursion()
                                parents = lr.get_jsonldish_entity_parents(entity.uri)
                                if len(parents) > 1:
                                    try:
                                        p_slug = parents[-2]['slug']
                                        act_field_fq = p_slug.replace('-', '_') + '___pred_id'
                                        act_field_fq = self.correct_solr_prefix_for_fq(solr_f_prefix, act_field_fq)
                                    except:
                                        pass
                                        print('Predicate Parent exception: '+ str(parents))
                            elif entity.item_type == 'uri':
                                act_field_fq = SolrDocument.ROOT_LINK_DATA_SOLR
                            elif entity.item_type == 'predicates':
                                temp_field_fq = self.get_parent_item_type_facet_field(entity.uri)
                                lr = LinkRecursion()
                                parents = lr.get_jsonldish_entity_parents(entity.uri)
                                if len(parents) > 1:
                                    try:
                                        p_slug = parents[-2]['slug']
                                        temp_field_fq = p_slug.replace('-', '_') + '___pred_id'
                                    except:
                                        print('Predicate Parent exception: '+ str(parents))
                                        temp_field_fq = False
                                if temp_field_fq is not False:
                                    act_field_fq = temp_field_fq
                                else:
                                    act_field_fq = SolrDocument.ROOT_PREDICATE_SOLR
                            else:
                                act_field_fq = SolrDocument.ROOT_PREDICATE_SOLR
                        # ---------------------------------------------------
                        # THIS PART BUILDS THE FACET-QUERY
                        # fq_path_term = fq_field + ':' + self.make_solr_value_from_entity(entity)
                        # the below is a bit of a hack. We should have a query field
                        # as with ___pred_ to query just the slug. But this works for now
                        fq_field = act_field_fq + '_fq'
                        if path_list_len >= 2 and act_field_data_type == 'id':
                            # could be an object deeper in the hierarchy, so allow the obj_all version
                            fq_path_term = '(' + fq_field + ':' + prop_slug
                            fq_path_term += ' OR obj_all___' + fq_field + ':' + prop_slug + ')'
                        else:
                            fq_path_term = fq_field + ':' + prop_slug
                        fq_path_terms.append(fq_path_term)
                        #---------------------------------------------------
                        #
                        #---------------------------------------------------
                        # THIS PART PREPARES FOR LOOPING OR FINAL FACET-FIELDS
                        #
                        # print('pred-solr-slug: ' + predicate_solr_slug)
                        field_parts = self.make_prop_solr_field_parts(entity)
                        act_field_data_type = field_parts['suffix']
                        if require_id_field:
                            act_field_data_type = 'id'
                            field_parts['suffix'] = 'id'
                        # check if the last or penultimate field has
                        # a different data-type (for linked-data)
                        if i >= (path_list_len - 2) \
                           and l_prop_entity:
                            dtypes = self.s_cache.get_dtypes(entity.uri)
                            if isinstance(dtypes, list):
                                # set the data type and the act-field
                                act_field_data_type = self.get_solr_field_type(dtypes[0])
                        if not predicate_solr_slug or pred_prop_entity:
                            act_field_fq = field_parts['prefix'] + '___pred_' + field_parts['suffix']
                            act_field_fq = self.correct_solr_prefix_for_fq(solr_f_prefix, act_field_fq)
                            # get a facet on this field
                            if act_field_data_type != 'string':
                                # adds a prefix for related properties
                                ffield = solr_f_prefix + field_parts['prefix'] + '___pred_' + field_parts['suffix']
                                if ffield not in query_dict['facet.field'] and \
                                   i >= (path_list_len - 1):
                                    query_dict['facet.field'].append(ffield)
                        else:
                            if act_field_data_type == 'id':
                                act_field_fq = 'obj_all___' + predicate_solr_slug \
                                               + '___pred_' + field_parts['suffix']
                                # get a facet on this field
                                if predicate_solr_slug != field_parts['prefix']:
                                    # the predicate_solr_slug is not the
                                    # prefix of the current field part, meaning
                                    # the field_parts[prefix] is the type, and
                                    # we want facets for the predicate -> type
                                    ffield = field_parts['prefix'] \
                                             + '___' \
                                             + predicate_solr_slug \
                                             + '___pred_' + field_parts['suffix']
                                else:
                                    # get facets for the predicate
                                    ffield = field_parts['prefix'] \
                                             + '___pred_' \
                                             + field_parts['suffix']
                                # adds a prefix, in case of a related property
                                ffield = solr_f_prefix + ffield
                                if ffield not in query_dict['facet.field'] \
                                   and i >= (path_list_len - 1):
                                    query_dict['facet.field'].append(ffield)
                            else:
                                act_field_fq = predicate_solr_slug + '___pred_' + field_parts['suffix']
                        # -------------------------------------------
                        if act_field_data_type == 'numeric':
                            # print('Numeric field: ' + act_field)
                            act_field_fq = field_parts['prefix'] + '___pred_numeric'
                            act_field_fq = self.correct_solr_prefix_for_fq(solr_f_prefix, act_field_fq)
                            query_dict = self.add_math_facet_ranges(query_dict,
                                                                    act_field_fq,
                                                                    entity)
                        elif act_field_data_type == 'date':
                            # print('Date field: ' + act_field)
                            act_field_fq = field_parts['prefix'] + '___pred_date'
                            act_field_fq = self.correct_solr_prefix_for_fq(solr_f_prefix, act_field_fq)
                            query_dict = self.add_date_facet_ranges(query_dict,
                                                                    act_field_fq,
                                                                    entity)
                        # print('Current data type (' + str(i) + '): ' + act_field_data_type)
                        # print('Current field (' + str(i) + '): ' + act_field_fq)
                    i += 1
                elif act_field_data_type == 'string':
                    # case for a text search
                    # last_field_label = False  # turn off using the field label for highlighting
                    string_terms = self.prep_string_search_term(prop_slug)
                    for escaped_term in string_terms:
                        search_term = act_field_fq + ':' + escaped_term
                        if last_field_label is False:
                            query_dict['hl-queries'].append(escaped_term)
                        else:
                            query_dict['hl-queries'].append(last_field_label + ' ' + escaped_term)
                        fq_path_terms.append(search_term)
                elif act_field_data_type == 'numeric':
                    # numeric search. assume it's well formed solr numeric request
                    search_term = act_field_fq + ':' + prop_slug
                    fq_path_terms.append(search_term)
                    # now limit the numeric ranges from query to the range facets
                    query_dict = self.add_math_facet_ranges(query_dict,
                                                            act_field_fq,
                                                            False,
                                                            prop_slug)
                elif act_field_data_type == 'date':
                    # date search. assume it's well formed solr request
                    search_term = act_field_fq + ':' + prop_slug
                    fq_path_terms.append(search_term)
                    # now limit the date ranges from query to the range facets
                    query_dict = self.add_date_facet_ranges(query_dict,
                                                            act_field_fq,
                                                            False,
                                                            prop_slug)
            final_path_term = ' AND '.join(fq_path_terms)
            final_path_term = '(' + final_path_term + ')'
            fq_terms.append(final_path_term)
        fq_final = ' OR '.join(fq_terms)
        fq_final = '(' + fq_final + ')'
        query_dict['fq'].append(fq_final)
        return query_dict

    def add_math_facet_ranges(self,
                              query_dict,
                              act_field,
                              entity=False,
                              solr_query=False):
        """ this does some math for facet
            ranges for numeric fields
        """
        ok = False
        groups = self.histogram_groups
        fstart = 'f.' + act_field + '.facet.range.start'
        fend = 'f.' + act_field + '.facet.range.end'
        fgap = 'f.' + act_field + '.facet.range.gap'
        findex = 'f.' + act_field + '.facet.sort'
        fother = 'f.' + act_field + '.facet.range.other'
        finclude = 'f.' + act_field + '.facet.range.include'
        if entity is not False:
            # this is a field with no value limits
            # we need to do a stats-prequery first
            query_dict['prequery-stats'].append(act_field)
        else:
            if solr_query is not False:
                vals = []
                # get the numbers out
                q_nums_strs = re.findall(r'[-+]?\d*\.\d+|\d+', solr_query)
                for q_num_str in q_nums_strs:
                    vals.append(float(q_num_str))
                vals.sort()
                if len(vals) > 1:
                    ok = True
                    min_val = vals[0]
                    max_val = vals[-1]
        if ok:
            if act_field not in query_dict['stats.field']:
                query_dict['stats.field'].append(act_field)
            if act_field not in query_dict['facet.range']:
                query_dict['facet.range'].append(act_field)
            query_dict['ranges'][fother] = 'all'
            query_dict['ranges'][finclude] = 'all'
            query_dict['ranges'][fstart] = min_val
            query_dict['ranges'][fend] = max_val
            query_dict['ranges'][fgap] = (max_val - min_val) / groups
            query_dict['ranges'][findex] = 'index'  # sort by index, not by count
        return query_dict

    def add_date_facet_ranges(self,
                              query_dict,
                              act_field,
                              entity=False,
                              solr_query=False):
        """ this does some math for facet
            ranges for numeric fields
        """
        ok = False
        groups = 4
        fstart = 'f.' + act_field + '.facet.range.start'
        fend = 'f.' + act_field + '.facet.range.end'
        fgap = 'f.' + act_field + '.facet.range.gap'
        findex = 'f.' + act_field + '.facet.sort'
        fother = 'f.' + act_field + '.facet.range.other'
        finclude = 'f.' + act_field + '.facet.range.include'
        if entity is not False:
            # this is a field with no value limits
            # we need to do a stats-prequery first
            query_dict['prequery-stats'].append(act_field)
        else:
            if solr_query is not False:
                q_dt_strs = re.findall(r'\d{4}-\d{2}-\d{2}[T:]\d{2}:\d{2}:\d{2}', solr_query)
                if len(q_dt_strs) < 2:
                    # try a less strict regular expression to get dates
                    q_dt_strs = re.findall(r'\d{4}-\d{2}-\d{2}', solr_query)
                if len(q_dt_strs) >= 2:
                    ok = True
                    vals = []
                    for q_dt_str in q_dt_strs:
                        vals.append(q_dt_str)
                    vals.sort()
                    min_val = vals[0]
                    max_val = vals[1]
        if ok:
            if act_field not in query_dict['stats.field']:
                query_dict['stats.field'].append(act_field)
            if act_field not in query_dict['facet.range']:
                query_dict['facet.range'].append(act_field)
            query_dict['ranges'][fother] = 'all'
            query_dict['ranges'][finclude] = 'all'
            query_dict['ranges'][fstart] = self.convert_date_to_solr_date(min_val)
            query_dict['ranges'][fend] = self.convert_date_to_solr_date(max_val)
            query_dict['ranges'][fgap] = self.get_date_difference_for_solr(min_val, max_val, groups)
            query_dict['ranges'][findex] = 'index'  # sort by index, not by count
        return query_dict

    def get_date_difference_for_solr(self, min_date, max_date, groups):
        """ Gets a solr date difference from two values """
        min_dt = self.date_convert(min_date)
        max_dt = self.date_convert(max_date)
        dif_dt = (max_dt - min_dt) / groups
        if dif_dt.days >= 366:
            solr_val = int(round((dif_dt.days / 365.25), 0))
            solr_dif = '+' + str(solr_val) + 'YEAR'
        elif dif_dt.days >= 31:
            solr_val = int(round((dif_dt.days / 30), 0))
            solr_dif = '+' + str(solr_val) + 'MONTH'
        elif dif_dt.days >= 1:
            solr_val = int(round(dif_dt.days, 0))
            solr_dif = '+' + str(solr_val) + 'DAY'
        elif (dif_dt.seconds // 3600) >= 1:
            solr_val = int(round((dif_dt.seconds // 3600), 0))
            solr_dif = '+' + str(solr_val) + 'HOUR'
        elif ((dif_dt.seconds % 3600) // 60) >= 1:
            solr_val = int(round(((dif_dt.seconds % 3600) // 60), 0))
            solr_dif = '+' + str(solr_val) + 'MINUTE'
        elif dif_dt.seconds >= 1:
            solr_val = int(round(dif_dt.seconds, 0))
            solr_dif = '+' + str(solr_val) + 'SECOND'
        else:
            solr_dif = '+1YEAR'
        return solr_dif

    def add_solr_gap_to_date(self, date_val, solr_gap):
        """ adds a solr gap to a date_val """
        solr_val = re.sub(r'[^\d.]', r'', solr_gap)
        solr_val = int(float(solr_val))
        dt = self.date_convert(date_val)
        if 'YEAR' in solr_gap:
            dt = dt + datetime.timedelta(days=int(round((solr_val * 365.25), 0)))
        elif 'MONTH' in solr_gap:
            dt = dt + datetime.timedelta(days=(solr_val * 30))
        elif 'DAY' in solr_gap:
            dt = dt + datetime.timedelta(days=solr_val)
        elif 'HOUR' in solr_gap:
            dt = dt + datetime.timedelta(hours=solr_val)
        elif 'MINUTE' in solr_gap:
            dt = dt + datetime.timedelta(minutes=solr_val)
        elif 'SECOND' in solr_gap:
            dt = dt + datetime.timedelta(seconds=solr_val)
        else:
            dt = dt
        return dt

    def convert_date_to_solr_date(self, date_val):
        """ Conversts a string for a date into
            a Solr formated datetime string
        """
        dt = self.date_convert(date_val)
        return dt.strftime('%Y-%m-%dT%H:%M:%SZ')

    def make_human_readable_date(self, date_val):
        """ Converts a date value into something
            easier to read
        """
        dt = self.date_convert(date_val)
        check_date = dt.strftime('%Y-%m-%d')
        check_dt = self.date_convert(date_val)
        if check_dt == dt:
            return check_date
        else:
            return dt.strftime('%Y-%m-%d:%H:%M:%S')

    def date_convert(self, date_val):
        """ converts to a python datetime if not already so """
        if isinstance(date_val, str):
            date_val = date_val.replace('Z', '')
            dt = datetime.datetime.strptime(date_val, '%Y-%m-%dT%H:%M:%S')
        else:
            dt = date_val
        return dt

    def get_parent_item_type_facet_field(self, category_uri):
        """ Gets the parent facet field for a given
            category_uri. This assumes the category_uri is an entity
            that exists in the database.
        """
        output = False;
        lr = LinkRecursion()
        parents = lr.get_jsonldish_entity_parents(category_uri)
        for par in parents:
            if par['slug'] in self.TYPE_MAPPINGS.values():
                # the parent exists in the Type Mappings
                output = par['slug'].replace('-', '_') + '___pred_id'
                break
        return output

    def get_parent_entity_facet_field(self, entity_uri):
        """ Gets the parent facet field for a given
            category_uri. This assumes the category_uri is an entity
            that exists in the database.
        """
        output = False;
        lr = LinkRecursion()
        parents = lr.get_jsonldish_entity_parents(entity_uri)
        if isinstance(parents, list):
            if len(parents) > 1:
                # get the penultimate field
                output = parents[-2]['slug'].replace('-', '_') + '___pred_id'
        return output

    def process_item_type(self, raw_item_type):
        # TODO docstring
        query_dict = {'fq': [],
                      'facet.field': []}
        fq_terms = []
        item_type_lists = self.expand_hierarchy_options(raw_item_type)
        for item_type_list in item_type_lists:
            i = 0
            path_list_len = len(item_type_list)
            fq_path_terms = []
            item_type = item_type_list[0]  # no hiearchy in this field, just the type
            fq_term = 'item_type:' + item_type
            fq_terms.append(fq_term)
            if item_type in self.TYPE_MAPPINGS:
                act_field = self.TYPE_MAPPINGS[item_type].replace('-', '_') + '___pred_id'
                query_dict['facet.field'].append(act_field)
        fq_final = ' OR '.join(fq_terms)
        fq_final = '(' + fq_final + ')'
        query_dict['fq'].append(fq_final)
        return query_dict

    def process_id(self, identifier):
        # check for identifier
        query_dict = {'fq': [],
                      'facet.field': []}
        fq_terms = []
        id_list = [identifier]
        id_list = self.make_http_https_options(id_list)
        for act_id in id_list:
            escape_id = self.escape_solr_arg(act_id)
            fq_terms.append('persistent_uri:' + escape_id)
            fq_terms.append('uuid:' + escape_id)
         # now make URIs in case we have a naked identifier
        prefix_removes = [
            'doi:',
            'orcid:',
            'http://dx.doi.org/',
            'https://dx.doi.org/',
            'http://doi.org/',
            'https://doi.org/'
        ]
        for prefix in prefix_removes:
            # strip ID prefixes, case insensitive
            re_gone = re.compile(re.escape(prefix), re.IGNORECASE)
            identifier = re_gone.sub('', identifier)
        uris = [
            'http://dx.doi.org/' + identifier,  # DOI (old)
            'http://doi.org/' + identifier,  # DOI (new)
            'http://n2t.net/' + identifier,  # ARK (CDL / Merritt)
            'http://orcid.org/' + identifier # Orcid (people)
        ]
        # now make https http varients of the URIs
        uris = self.make_http_https_options(uris)
        for uri in uris:
            # now make a DOI URI in case this is just a naked DOI
            escaped_uri = self.escape_solr_arg(uri)
            fq_terms.append('persistent_uri:' + escaped_uri)
        tcheck = URImanagement.get_uuid_from_oc_uri(identifier, True)
        if tcheck is not False:
            uuid = tcheck['uuid']
            fq_terms.append('uuid:' + uuid)
        fq_final = ' OR '.join(fq_terms)
        fq_final = '(' + fq_final + ')'
        query_dict['fq'].append(fq_final)
        # print(fq_final)
        return query_dict

    def process_form_use_life_chrono(self, raw_form_use_life_chrono):
        # creates facet query for form-use-life chronological tiles
        # supports or {'||') queries in the path also
        query_dict = {'fq': [],
                      'facet.field': []}
        fq_terms = []
        query_dict['facet.field'].append('form_use_life_chrono_tile')
        if '||' in raw_form_use_life_chrono:
            chrono_paths = raw_form_use_life_chrono.split('||')
        else:
            chrono_paths = [raw_form_use_life_chrono]
        for chrono_path in chrono_paths:
            i = 0
            if len(chrono_path) < 30:
                chrono_path += '*'
            fq_term = 'form_use_life_chrono_tile:' + chrono_path
            fq_terms.append(fq_term)
        fq_final = ' OR '.join(fq_terms)
        fq_final = '(' + fq_final + ')'
        query_dict['fq'].append(fq_final)
        return query_dict

    def process_form_date_chrono(self, form_use_life_date, date_type):
        # creates facet query for form-use-life dates
        # supports or {'||') queries in the path also
        query_dict = {'fq': [],
                      'facet.field': []}
        if date_type == 'start':
            qterm = '[' + str(form_use_life_date) + ' TO *]'
            fquery = 'form_use_life_chrono_earliest: ' + qterm
        else:
            qterm = '[* TO ' + str(form_use_life_date) + ']'
            fquery = 'form_use_life_chrono_latest: ' + qterm
        query_dict['fq'].append(fquery)
        return query_dict

    def process_discovery_geo(self, raw_disc_geo):
        # creates facet query for discovery geotiles
        # supports or {'||') queries in the path also
        query_dict = {'fq': [],
                      'facet.field': []}
        fq_terms = []
        query_dict['facet.field'].append('discovery_geotile')
        if '||' in raw_disc_geo:
            disc_geo_paths = raw_disc_geo.split('||')
        else:
            disc_geo_paths = [raw_disc_geo]
        for disc_path in disc_geo_paths:
            i = 0
            if len(disc_path) < 20:
                disc_path += '*'
            fq_term = 'discovery_geotile:' + disc_path
            fq_terms.append(fq_term)
        fq_final = ' OR '.join(fq_terms)
        fq_final = '(' + fq_final + ')'
        query_dict['fq'].append(fq_final)
        return query_dict

    def process_discovery_bbox(self, raw_disc_bbox):
        # creates facet query for bounding box searches
        # supports or {'||') queries
        query_dict = {'fq': []}
        fq_terms = []
        if '||' in raw_disc_bbox:
            bbox_list = raw_disc_bbox.split('||')
        else:
            bbox_list = [raw_disc_bbox]
        for bbox in bbox_list:
            if ',' in bbox:
                # comma seperated list of coordinates
                bbox_coors = bbox.split(',')
                bbox_valid = self.validate_bbox_coordiantes(bbox_coors)
                if bbox_valid:
                    # valid bounding box, now make a solr-query
                    # not how solr expacts latitude / longitude order, which
                    # is the revserse of geojson!
                    fq_term = 'discovery_geolocation:'
                    fq_term += '[' + str(bbox_coors[1]) + ',' + str(bbox_coors[0])
                    fq_term += ' TO ' + str(bbox_coors[3]) + ',' + str(bbox_coors[2])
                    fq_term += ']'
                    fq_terms.append(fq_term)
        if len(fq_terms) > 0:
            fq_final = ' OR '.join(fq_terms)
            fq_final = '(' + fq_final + ')'
            query_dict['fq'].append(fq_final)
        return query_dict

    def validate_bbox_coordiantes(self, bbox_coors):
        """ validates a set of bounding box coordinates """
        is_valid = False
        if len(bbox_coors) == 4:
            lower_left_valid = self.validate_geo_lon_lat(bbox_coors[0],
                                                         bbox_coors[1])
            top_right_valid = self.validate_geo_lon_lat(bbox_coors[2],
                                                        bbox_coors[3])
            # print('ok: ' + str(lower_left_valid) + ' ' + str(top_right_valid))
            if lower_left_valid and top_right_valid:
                if float(bbox_coors[0]) < float(bbox_coors[2]) and\
                   float(bbox_coors[1]) < float(bbox_coors[3]):
                    is_valid = True
        return is_valid

    def validate_geo_lon_lat(self, lon, lat):
        """ checks to see if a lon, lat pair
            are valid. Note the GeoJSON ordering
            of the coordinates
        """
        is_valid = False
        lon_valid = self.validate_geo_coordinate(lon, 'lon')
        lat_valid = self.validate_geo_coordinate(lat, 'lat')
        if lon_valid and lat_valid:
            is_valid = True
        return is_valid

    def validate_geo_coordinate(self, coordinate, coord_type):
        """ validates a geo-spatial coordinate """
        is_valid = False
        try:
            fl_coord = float(coordinate)
        except ValueError:
            fl_coord = False
        if fl_coord is not False:
            if 'lat' in coord_type:
                if fl_coord <= 90 and\
                   fl_coord >= -90:
                    is_valid = True
            elif 'lon' in coord_type:
                if fl_coord <= 180 and\
                   fl_coord >= -180:
                    is_valid = True
        return is_valid

    def make_solr_value_from_entity(self, entity, value_type='id'):
        """ makes a solr value as indexed in SolrDocument
            see _concat_solr_string_value
        """
        id_part = entity.uri
        if 'http://opencontext.org' in entity.uri:
            if '/vocabularies/' not in entity.uri:
                id_part = entity.uri.split('http://opencontext.org')[1]
        return entity.slug + '___' + value_type + '___' + \
            id_part + '___' + entity.label
        return output

    def _process_spatial_context(self, spatial_context=None):
        # TODO docstring
        context = {}
        if spatial_context:
            context_paths = self._get_context_paths(spatial_context)
            context_slugs = self._get_valid_context_slugs(context_paths)
            # print('Context slugs: ' + str(context_slugs))
            # If we cannot find a valid context, raise a 404
            if not context_slugs:
                raise Http404
            # Solr 'fq' parameters
            parent_child_slugs = []
            # Solr 'facet.field' parameters
            facet_field = []
            for slug in context_slugs:
                # fq parameters
                parent_child_slugs.append(self._get_parent_slug(slug) + '___' + slug)
                # facet.field parameters
                facet_field.append(slug.replace('-', '_') + '___context_id')
            # First, handle the most likely scenario of a single context
            if len(parent_child_slugs) == 1:
                context['fq'] = self._prepare_filter_query(parent_child_slugs[0])
            # Otherwise, combine multiple contexts into an OR filter
            else:
                fq_string = ' OR '.join(
                    (self._prepare_filter_query(slug_set) for slug_set
                        in parent_child_slugs)
                    )
                context['fq'] = '(' + fq_string + ')'
            context['facet.field'] = facet_field
        # No spatial context provided
        else:
            context['fq'] = None
            context['facet.field'] = ['root___context_id']
        return context

    def prep_string_search_term(self, raw_term):
        """ prepares a string search
            returns a list of search terms
            for AND queries
        """
        if '"' in raw_term:
            nq_term = raw_term.replace('"', ' ')  # get rid of quotes in the search term
            quoted_list = re.findall(r"\"(.*?)\"", raw_term)
            terms = []
            terms.append(self.escape_solr_arg(nq_term))
            for quote_item in quoted_list:
                quote_item = self.escape_solr_arg(quote_item)  # escape characters
                quote_item = '"' + quote_item + '"'  # put quotes back around it
                terms.append(quote_item)
        else:
            terms = []
            terms.append(self.escape_solr_arg(raw_term))
        return terms
    
    def make_http_https_options(self, terms):
        """ checks a list of terms for http:// or https://
            strings, if those exist, then add the alternative
            to the list
        """
        output_terms = terms
        if isinstance(terms, list):
            output_terms = []
            for term in terms:
                output_terms.append(term)
                if isinstance(term, str):
                    if 'http://' in term:
                        new_term = term.replace('http://', 'https://')
                    elif 'https://' in term:
                        new_term = term.replace('https://', 'http://')
                    else:
                        new_term = None
                    if new_term is not None:
                        output_terms.append(new_term)
        else:
            output_terms = terms
        return output_terms

    def escaped_seq(self, term):
        """ Yield the next string based on the
            next character (either this char
            or escaped version """
        escaperules = {'+': r'\+',
                       '-': r'\-',
                       '&': r'\&',
                       '|': r'\|',
                       '!': r'\!',
                       '(': r'\(',
                       ')': r'\)',
                       '{': r'\{',
                       '}': r'\}',
                       '[': r'\[',
                       ']': r'\]',
                       '^': r'\^',
                       '~': r'\~',
                       '*': r'\*',
                       '?': r'\?',
                       ':': r'\:',
                       '"': r'\"',
                       ';': r'\;',
                       ' ': r'\ '}
        for char in term:
            if char in escaperules.keys():
                yield escaperules[char]
            else:
                yield char

    def escape_solr_arg(self, term):
        """ Apply escaping to the passed in query terms
            escaping special characters like : , etc"""
        term = term.replace('\\', r'\\')   # escape \ first
        return "".join([next_str for next_str in self.escaped_seq(term)])

