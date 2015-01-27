import itertools
import django.utils.http as http
from django.http import Http404
from opencontext_py.apps.entities.entity.models import Entity
from opencontext_py.apps.ocitems.assertions.containment import Containment
from opencontext_py.apps.indexer.solrdocument import SolrDocument


class QueryMaker():

    def __init__(self):
        self.error = False

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

    def _process_prop_list(self, prop_list):
        # TODO docstring
        props = (prop.split(' ') for prop in prop_list)
        prop_dict_list = []
        for prop in props:
            # If multi-select
            if any('||' in property for property in prop):
                prop_dict_list.append(self._process_multi_select_prop(prop))
            else:
                # Otherwise, single-select
                prop_dict_list.append(self._process_single_select_prop(prop))
        return prop_dict_list

    def expand_hierarchy_options(self,
                                 path_param_val,
                                 hier_delim=' ',
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

    def _process_multi_select_prop(self, prop):
        # TODO docstring
        prop_dict = {}
        # Modify the prop so each property is in its own list
        prop_list = (item.split('||') for item in prop)
        # Generate a list of the various permutations of multi-selected properties
        prop_tuple_list = list(itertools.product(*prop_list))
        # Turn the resulting list of tuples into a list of lists
        prop_list = (list(item) for item in prop_tuple_list)
        prop_facet_field_list = []
        prop_fq_list = []
        for prop in prop_list:
            value = prop.pop()
            entity = Entity()
            found = entity.dereference(value)
            if len(prop) == 0:
                if found:
                    field_parts = self.make_prop_solr_field_parts(entity)
                    prop_facet_field_list.append(field_parts['prefix'] + '___pred_' + field_parts['suffix'])
                prop_fq_list.append('root___pred_id_fq:' + value)
            else:
                facet_field = ''
                for property in range(len(prop)):
                    facet_field += prop.pop().replace('-', '_') + '___'
                    facet_field += 'pred_id'
                    if facet_field not in prop_facet_field_list:
                        prop_facet_field_list.append(facet_field)
                    fq = facet_field + '_fq:' + value
                    prop_fq_list.append(fq)
        prop_dict['facet.field'] = prop_facet_field_list
        # Create fq string of multi-selected OR props
        prop_fq_string = ' OR '.join(fq for fq in prop_fq_list)
        prop_fq_string = '(' + prop_fq_string + ')'
        prop_dict['fq'] = prop_fq_string
        return prop_dict

    def get_solr_field_type(self, data_type, prefix=''):
        '''
        Defines whether our dynamic solr fields names for
        predicates end with ___pred_id, ___pred_numeric, etc.
        '''
        if data_type in ['@id', 'id']:
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

    def _process_single_select_prop(self, prop):
        # TODO docstring
        prop_dict = {}
        # Get the value
        value = prop.pop()
        entity = Entity()
        found = entity.dereference(value)
        # A single property (e.g., ?prop=24--object-type)
        if len(prop) == 0:
            prop_dict['fq'] = 'root___pred_id_fq:' + value
            if found:
                field_parts = self.make_prop_solr_field_parts(entity)
                prop_dict['facet.field'] = field_parts['prefix'] + '___pred_' + field_parts['suffix']
            else:
                prop_dict['facet.field'] = SolrDocument.ROOT_PREDICATE_SOLR
        # Multiple properties
        else:
            facet_field = ''
            for property in range(len(prop)):
                facet_field += prop.pop().replace('-', '_') + '___'
            facet_field += 'pred_id'
            prop_dict['facet.field'] = facet_field
            fq = facet_field + '_fq:' + value
            prop_dict['fq'] = fq
        return prop_dict

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
