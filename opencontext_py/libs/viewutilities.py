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
    # Create lists of the various permutations
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
    parent_child_set = parent_child_slug.split('___')
    return parent_child_set[0].replace('-', '_') + '___context_id_fq:' + \
        parent_child_set[1]


def _process_spatial_context(spatial_context=None):
    context = {}

    if spatial_context:
        context_paths = _get_context_paths(spatial_context)
        context_slugs = _get_valid_context_slugs(context_paths)
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
        # If we cannot find a valid context, raise a 404
            if not fq_string:
                raise Http404

            context['fq'] = '(' + fq_string + ')'

        context['facet.field'] = facet_field

    else:
        context['fq'] = None
        context['facet.field'] = 'root___context_id'

    return context
