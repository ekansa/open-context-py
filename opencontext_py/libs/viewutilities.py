import itertools
import django.utils.http as http
from django.http import Http404
from opencontext_py.apps.entities.entity.models import Entity
from opencontext_py.apps.ocitems.assertions.containment import Containment


def _get_context_paths(spatial_context):
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


def _get_context_depth(spatial_context):
    '''
    Takes a context path and returns its depth as an interger. For
    example, the context '/Turkey/Domuztepe'
    would have a depth of 2.
    '''
    # Remove a possible trailing slash before calculating the depth
    return len(spatial_context.rstrip('/').split('/'))


def _get_valid_context_slugs(contexts):
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


def _get_parent_slug(slug):
    '''
    Takes a slug and returns the slug of its parent. Returns 'root' if
    a slug has no parent.
    '''
    parent_slug = Containment().get_parent_slug_by_slug(slug)
    if parent_slug:
        return parent_slug
    else:
        return 'root'


def _prepare_filter_query(parent_child_slug):
    # TODO docstring
    parent_child_set = parent_child_slug.split('___')
    return parent_child_set[0].replace('-', '_') + '___context_id_fq:' + \
        parent_child_set[1]


def _process_multi_select_prop(prop):
    prop_dict = {}
    # Modify the prop so each property is in its own list
    prop_list = [item.split('||') for item in prop]
    # Generate a list of the various permutations of multi-selected properties
    prop_tuple_list = list(itertools.product(*prop_list))
    # Turn the resulting list of tuples into a list of lists
    prop_list = [list(item) for item in prop_tuple_list]

    prop_facet_field_list = []
    prop_fq_list = []
    for prop in prop_list:
        value = prop.pop()
        if len(prop) == 0:
            if 'root___pred_id' not in prop_facet_field_list:
                prop_facet_field_list.append('root___pred_id')
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


def _process_single_select_prop(prop):
    prop_dict = {}
    # Get the value
    value = prop.pop()
    # A single property (e.g., ?prop=24--object-type)
    if len(prop) == 0:
        prop_dict['fq'] = 'root___pred_id_fq:' + value
        prop_dict['facet.field'] = 'root___pred_id'
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


def _process_spatial_context(spatial_context=None):
    # TODO docstring
    context = {}

    if spatial_context:
        context_paths = _get_context_paths(spatial_context)
        context_slugs = _get_valid_context_slugs(context_paths)

        # If we cannot find a valid context, raise a 404
        if not context_slugs:
            raise Http404

        # Solr 'fq' parameters
        parent_child_slugs = []
        # Solr 'facet.field' parameters
        facet_field = []

        for slug in context_slugs:
            # fq parameters
            parent_child_slugs.append(_get_parent_slug(slug) + '___' + slug)
            # facet.field parameters
            facet_field.append(slug.replace('-', '_') + '___context_id')

        # First, handle the most likely scenario of a single context
        if len(parent_child_slugs) == 1:
            context['fq'] = _prepare_filter_query(parent_child_slugs[0])

        # Otherwise, combine multiple contexts into an OR filter
        else:
            fq_string = ' OR '.join(
                [_prepare_filter_query(slug_set) for slug_set
                    in parent_child_slugs]
                )

            context['fq'] = '(' + fq_string + ')'

        context['facet.field'] = facet_field

    # No spatial context provided
    else:
        context['fq'] = None
        context['facet.field'] = 'root___context_id'

    return context
