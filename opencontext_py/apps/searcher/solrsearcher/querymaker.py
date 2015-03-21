import re
import datetime
import itertools
import django.utils.http as http
from django.http import Http404
from opencontext_py.apps.entities.entity.models import Entity
from opencontext_py.apps.ldata.linkannotations.recursion import LinkRecursion
from opencontext_py.apps.ocitems.assertions.containment import Containment
from opencontext_py.apps.indexer.solrdocument import SolrDocument
from opencontext_py.apps.ocitems.assertions.math import MathAssertions
from opencontext_py.apps.ldata.linkannotations.equivalence import LinkEquivalence
from opencontext_py.apps.entities.uri.models import URImanagement


class QueryMaker():

    # main item-types mapped to their slugs to get solr-facet field prefix
    TYPE_MAPPINGS = {'subjects': 'oc-gen-subjects',
                     'media': 'oc-gen-media',
                     'documents': 'oc-gen-documents',
                     'persons': 'oc-gen-persons',
                     'projects': 'oc-gen-projects',
                     'types': 'oc-gen-types',
                     'predicates': 'oc-gen-predicates'}

    TYPE_URIS = {'subjects': 'oc-gen:subjects',
                 'media': 'oc-gen:media',
                 'documents': 'oc-gen:documents',
                 'persons': 'oc-gen:persons',
                 'projects': 'oc-gen:projects',
                 'types': 'oc-gen:types',
                 'predicates': 'oc-gen:predicates'}

    def __init__(self):
        self.error = False
        self.entities = {}  # keep looked up entities to save future database lookups
        self.histogram_groups = 10

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
        entity = Entity()
        valid_context_slugs = []
        context_list = list(contexts)
        for context in context_list:
            # Remove the '+' characters to match values in the database
            context = http.urlunquote_plus(context)
            # Verify that the contexts are valid
            found = entity.context_dereference(context)
            if found:
                valid_context_slugs.append(entity.slug)
                self.entities[context] = entity  # store entitty for later use
        return valid_context_slugs

    def _get_parent_slug(self, slug):
        '''
        Takes a slug and returns the slug of its parent. Returns 'root' if
        a slug has no parent.
        '''
        parent_slug = Containment().get_parent_slug_by_slug(slug)
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
                entity = Entity()
                found = entity.dereference(proj_slug)
                if found:
                    # fq_path_term = fq_field + ':' + self.make_solr_value_from_entity(entity)
                    # the below is a bit of a hack. We should have a query field
                    # as with ___pred_ to query just the slug. But this works for now
                    self.entities[proj_slug] = entity
                    proj_slug = entity.slug
                    fq_path_term = fq_field + ':' + proj_slug + '*'
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

    def process_dc_term(self, dc_param, dc_terms, add_facet=False):
        # TODO docstring
        query_dict = {'fq': [],
                      'facet.field': []}
        fq_terms = []
        if dc_param == 'dc-subject':
            fq_field = 'dc_terms_subject___pred_id'
        elif dc_param == 'dc-coverage':
            fq_field = 'dc_terms_coverage___pred_id'
        elif dc_param == 'dc-spatial':
            fq_field = 'dc_terms_spatial___pred_id'
        if fq_field not in query_dict['facet.field'] and add_facet:
            query_dict['facet.field'].append(fq_field)
        for raw_dc_term in dc_terms:
            if '||' in raw_dc_term:
                use_dc_terms = raw_dc_term.split('||')
            else:
                use_dc_terms = [raw_dc_term]
            fq_path_terms = []
            for dc_term in use_dc_terms:
                entity = Entity()
                found = entity.dereference(dc_term)
                if found:
                    # fq_path_term = fq_field + ':' + self.make_solr_value_from_entity(entity)
                    # the below is a bit of a hack. We should have a query field
                    # as with ___pred_ to query just the slug. But this works for now
                    self.entities[entity.slug] = entity
                    fq_path_term = fq_field + '_fq:' + entity.slug
                else:
                    fq_path_term = fq_field + ':' + dc_term
                fq_path_terms.append(fq_path_term)
            final_path_term = ' AND '.join(fq_path_terms)
            final_path_term = '(' + final_path_term + ')'
            fq_terms.append(final_path_term)
        fq_final = ' OR '.join(fq_terms)
        fq_final = '(' + fq_final + ')'
        query_dict['fq'].append(fq_final)
        return query_dict

    def process_prop(self, props):
        """ processes 'prop' (property) parameters
            property parameters are tricky because they
            can come in hierarchies
            that's why there's some complexity to this
        """
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
                l_prop_entity = False
                pred_prop_entity = False
                require_id_field = False
                if act_field_data_type == 'id':
                    entity = Entity()
                    found = entity.dereference(prop_slug)
                    if found is False:
                        found = entity.dereference(prop_slug, prop_slug)
                    if found:
                        self.entities[prop_slug] = entity  # store entitty for later use
                        last_field_label = entity.label
                        prop_slug = entity.slug
                        if entity.item_type == 'uri' and 'oc-gen' not in prop_slug:
                            if entity.entity_type == 'property':
                                pred_prop_entity = True
                                predicate_solr_slug = prop_slug.replace('-', '_')
                                l_prop_entity = True
                                lr = LinkRecursion()
                                lr.get_entity_children(entity.uri)
                                if len(lr.child_entities) > 1:
                                    # ok, this field has children. require it
                                    # to be treated as an ID field
                                    require_id_field = True
                        else:
                            if entity.item_type == 'predicates':
                                pred_prop_entity = True
                                predicate_solr_slug = prop_slug.replace('-', '_')
                                lr = LinkRecursion()
                                lr.get_entity_children(entity.uri)
                                if len(lr.child_entities) > 1:
                                    # ok, this field has children. require it
                                    # to be treated as an ID field
                                    require_id_field = True
                        if i == 0:
                            if 'oc-gen' in prop_slug:
                                act_field_fq = self.get_parent_item_type_facet_field(entity.uri)
                                lr = LinkRecursion()
                                parents = lr.get_jsonldish_entity_parents(entity.uri)
                                if len(parents) > 1:
                                    p_slug = parents[-2]['slug']
                                    act_field_fq = p_slug.replace('-', '_') + '___pred_id'
                            elif entity.item_type == 'uri':
                                act_field_fq = SolrDocument.ROOT_LINK_DATA_SOLR
                            else:
                                act_field_fq = SolrDocument.ROOT_PREDICATE_SOLR
                        # ---------------------------------------------------
                        # THIS PART BUILDS THE FACET-QUERY
                        # fq_path_term = fq_field + ':' + self.make_solr_value_from_entity(entity)
                        # the below is a bit of a hack. We should have a query field
                        # as with ___pred_ to query just the slug. But this works for now
                        fq_field = act_field_fq + '_fq'
                        if path_list_len == 2 and act_field_data_type == 'id':
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
                            lequiv = LinkEquivalence()
                            dtypes = lequiv.get_data_types_from_object(entity.uri)
                            if isinstance(dtypes, list):
                                # set te data type and the act-field
                                if prop_slug in self.entities:
                                    # pass
                                    self.entities[prop_slug].data_type = dtypes[0]  # store entitty for later use
                                act_field_data_type = self.get_solr_field_type(dtypes[0])
                        if predicate_solr_slug is False or pred_prop_entity:
                            act_field_fq = field_parts['prefix'] + '___pred_' + field_parts['suffix']
                            # get a facet on this field
                            if act_field_data_type != 'string':
                                query_dict['facet.field'].append(field_parts['prefix'] + '___pred_' + field_parts['suffix'])
                        else:
                            if act_field_data_type == 'id':
                                act_field_fq = 'obj_all___' + predicate_solr_slug \
                                               + '___pred_' + field_parts['suffix']
                                # get a facet on this field
                                if predicate_solr_slug != field_parts['prefix']:
                                    query_dict['facet.field'].append(field_parts['prefix'] \
                                                                     + '___' \
                                                                     + predicate_solr_slug \
                                                                     + '___pred_' + field_parts['suffix'])
                                else:
                                    query_dict['facet.field'].append(field_parts['prefix'] \
                                                                     + '___pred_' \
                                                                     + field_parts['suffix'])
                            else:
                                act_field_fq = predicate_solr_slug + '___pred_' + field_parts['suffix']
                        # -------------------------------------------
                        if act_field_data_type == 'numeric':
                            # print('Numeric field: ' + act_field)
                            act_field_fq = field_parts['prefix'] + '___pred_numeric'
                            query_dict = self.add_math_facet_ranges(query_dict,
                                                                    act_field_fq,
                                                                    entity)
                        elif act_field_data_type == 'date':
                            # print('Date field: ' + act_field)
                            act_field_fq = field_parts['prefix'] + '___pred_date'
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
        parents = LinkRecursion().get_jsonldish_entity_parents(category_uri)
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
        parents = LinkRecursion().get_jsonldish_entity_parents(entity_uri)
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
