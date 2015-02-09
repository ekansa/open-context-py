import itertools
import django.utils.http as http
from django.http import Http404
from opencontext_py.apps.entities.entity.models import Entity
from opencontext_py.apps.ldata.linkannotations.recursion import LinkRecursion
from opencontext_py.apps.ocitems.assertions.containment import Containment
from opencontext_py.apps.indexer.solrdocument import SolrDocument


class QueryMaker():

    # main item-types mapped to their slugs to get solr-facet field prefix
    TYPE_MAPPINGS = {'subjects': 'oc-gen-subjects',
                     'media': 'oc-gen-media',
                     'documents': 'oc-gen-documents',
                     'persons': 'oc-gen-persons',
                     'projects': 'oc-gen-projects',
                     'types': 'oc-gen-types',
                     'predicates': 'oc-gen-predicates'}

    def __init__(self):
        self.error = False
        self.entities = {}  # keep looked up entities to save future database lookups

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

    def process_prop(self, props):
        # TODO docstring
        query_dict = {'fq': [],
                      'facet.field': []}
        fq_terms = []
        prop_path_lists = self.expand_hierarchy_options(props)
        for prop_path_list in prop_path_lists:
            i = 0
            path_list_len = len(prop_path_list)
            fq_path_terms = []
            act_field = SolrDocument.ROOT_PREDICATE_SOLR
            for prop_slug in prop_path_list:
                entity = Entity()
                found = entity.dereference(prop_slug)
                if found is False:
                    found = entity.dereference(prop_slug, prop_slug)
                if found:
                    self.entities[prop_slug] = entity  # store entitty for later use
                    prop_slug = entity.slug
                    if i == 0:
                        if entity.item_type != 'uri':
                            act_field = SolrDocument.ROOT_PREDICATE_SOLR
                        else:
                            act_field = False
                            if 'oc-gen' in prop_slug:
                                # get the root solr facet field for the item type
                                # associated with this category
                                act_field = self.get_parent_item_type_facet_field(entity.uri)
                            if act_field is False:
                                act_field = SolrDocument.ROOT_LINK_DATA_SOLR
                    # fq_path_term = fq_field + ':' + self.make_solr_value_from_entity(entity)
                    # the below is a bit of a hack. We should have a query field
                    # as with ___pred_ to query just the slug. But this works for now
                    fq_field = act_field + '_fq'
                    fq_path_term = fq_field + ':' + prop_slug
                    fq_path_terms.append(fq_path_term)
                    field_parts = self.make_prop_solr_field_parts(entity)
                    if i < 1:
                        act_field = field_parts['prefix'] + '___pred_' + field_parts['suffix']
                    else:
                        act_field = field_parts['prefix'] + '___' + act_field
                i += 1
                if i >= path_list_len and act_field not in query_dict['facet.field']:
                    query_dict['facet.field'].append(act_field)
            final_path_term = ' AND '.join(fq_path_terms)
            final_path_term = '(' + final_path_term + ')'
            fq_terms.append(final_path_term)
        fq_final = ' OR '.join(fq_terms)
        fq_final = '(' + fq_final + ')'
        query_dict['fq'].append(fq_final)
        return query_dict

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
