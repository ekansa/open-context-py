from django.conf import settings
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.contexts.models import (
    GeneralContext,
    ItemContext,
    SearchContext
)
from opencontext_py.apps.contexts.projectcontext import ProjectContext


"""    

from opencontext_py.apps.contexts.manage import cache_projects_contexts
cache_projects_contexts(True)  # Refrech cache of all project contexts

import requests
from opencontext_py.apps.contexts.manage import consolidate_contexts
url = 'http://127.0.0.1:8000/items/D5D2BD55-55A2-445F-9258-37A36AAC343E.json'
r = requests.get(url)
contexts = consolidate_contexts(r.json())


"""

# Returns a Context dict object for standard contexts widely used in
# Open Context. Note. This does NOT require access to the public Web.
STANDARD_CONTEXTS = {
    ItemContext.DOI: {'@context': ItemContext().context},
    ItemContext.URL: {'@context': ItemContext().context},
    SearchContext.DOI: {'@context': SearchContext().context},
    SearchContext.URL: {'@context': SearchContext().context},
    GeneralContext.GEO_JSON_CONTEXT_URI: GeneralContext().geo_json_dict()
}


def cache_projects_contexts(refresh_cache=False):
    """Caches contexts for all projects"""
    projs_man_objs = Manifest.objects\
                             .filter(item_type='projects')
    for proj_man_obj in projs_man_objs:
        proj_context = ProjectContext()
        proj_context.refresh_cache = refresh_cache
        proj_context.dereference_uuid_or_slug(proj_man_obj.uuid)
        if isinstance(proj_context.uuid, str):
            json_ld = proj_context.make_context_and_vocab_json_ld()

def get_project_id_in_uri(uri):
    """ Gets the ID part of a URI """
    uri_ex = uri.split('/')
    id = uri_ex[-1]
    if '.' in id:
        id = id.split('.')[0]
    return id

def get_context_by_uri(uri):
    """Gets a context dict from a URI or from the cache."""
    if uri in STANDARD_CONTEXTS:
        return STANDARD_CONTEXTS[uri]
    if '/contexts/project-vocabs/' in uri:
        project_id = get_project_id_in_uri(uri)
        proj_context = ProjectContext()
        proj_context.dereference_uuid_or_slug(project_id)
        if proj_context.manifest:
            # Return the context object
            return proj_context.make_context_and_vocab_json_ld()
    return None

def consolidate_contexts(json_ld):
    """Consolidates contexts into one large context to reduce
       HTTP retrievals of different context files."""
    if not isinstance(json_ld, dict) or not '@context' in json_ld:
        return None
    if not isinstance(json_ld['@context'], list):
        # The context is (probably) a dictionary object, so it is already
        # consolidated.
        return json_ld['@context']
    all_context = {}
    for context_uri in json_ld['@context']:
        context_dict = get_context_by_uri(context_uri)
        if not isinstance(context_dict, dict):
            # Something went wrong, it's not a dictionary object
            continue
        if not '@context' in context_dict:
            # Still something wrong, we're missing a @context key
            continue
        for key, vals in context_dict['@context'].items():
            all_context[key] = vals
    return all_context
    
