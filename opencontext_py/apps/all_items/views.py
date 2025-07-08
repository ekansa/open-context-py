import json
from django.conf import settings

from django.contrib import messages
from django.http import HttpResponse, Http404
from django.shortcuts import redirect

from django.db.models.functions import Length

from django.template import loader
from opencontext_py.libs.rootpath import RootPath
from opencontext_py.libs.requestnegotiation import RequestNegotiation

from opencontext_py.apps.all_items import configs
from opencontext_py.apps.all_items.permissions import get_request_user_permissions
from opencontext_py.apps.all_items.representations import item
from opencontext_py.apps.all_items.representations.rep_utils import get_hero_banner_url
from opencontext_py.apps.all_items.representations.template_prep import (
    prepare_for_item_dict_solr_and_html_template,
    prepare_for_item_dict_html_template,
)
from opencontext_py.apps.all_items.representations.schema_org import (
    make_schema_org_json_ld
)
from opencontext_py.apps.all_items.representations import citation
from opencontext_py.apps.all_items.legacy_all import update_old_id

from opencontext_py.apps.indexer.solrdocument_new_schema import SolrDocumentNS

from opencontext_py.apps.all_items.editorial.api import get_man_obj_by_any_id

from opencontext_py.apps.all_items.models import (
    AllManifest,
    AllIdentifier,
)

from opencontext_py.apps.searcher.new_solrsearcher import db_entities

from opencontext_py.apps.web_metadata.social import make_social_media_metadata

from django.views.decorators.cache import never_cache
from django.utils.cache import patch_vary_headers




def make_redirect_url(request, path, ok_uuid, extension=''):
    request = RequestNegotiation().anonymize_request(request)
    rp = RootPath()
    base_url = rp.get_baseurl()
    new_url = f'{base_url}/{path}/{ok_uuid}{extension}'
    return redirect(new_url, permanent=True)


def evaluate_update_id(uuid):
    """Evaluates and, if needed, updates a UUID"""
    _, ok_uuid = update_old_id(uuid)
    if ok_uuid == uuid:
        return uuid, False
    # reduce long query lookups by checking to see if
    # we have a manifest object cached by item_key
    item_key_dict = db_entities.get_cache_item_key_dict()
    item_obj = get_man_obj_by_any_id(
        identifier=ok_uuid,
        item_key_dict=item_key_dict,
    )
    if item_obj:
        return item_obj.uuid, True
    item_obj = get_man_obj_by_any_id(
        identifier=uuid,
        item_key_dict=item_key_dict,
    )
    if item_obj:
        return item_obj.uuid, True
    return None, False


def get_suffix_backoff_suggest_obj(unmatched_id):
    """Get a manifest object for a suggested (semantic) parent
    resource to provide a more informative 404 error.
    """
    suggest_obj = None
    if not unmatched_id:
        return None
    item_key_dict = db_entities.get_cache_item_key_dict()
    unmatched_id = str(unmatched_id)
    id_suffix = ''
    root_suggest_obj = None
    for id_delim in ['/', '_']:
        if root_suggest_obj:
            continue
        if not id_delim in unmatched_id:
            continue
        split_id = unmatched_id.split(id_delim)
        check_id = split_id[0].strip()
        id_suffix = split_id[-1].strip()
        print(f'check_id: {check_id}  id_suffix: {id_suffix}')
        root_suggest_obj = get_man_obj_by_any_id(
            identifier=check_id,
            item_key_dict=item_key_dict,
        )
    if not root_suggest_obj:
        return None
    print(f'Found suggested item {root_suggest_obj.label} [{root_suggest_obj.uuid}]')
    if root_suggest_obj.item_type != 'projects':
        # we have suggested object, but it is not a project.
        return root_suggest_obj
    # Make a big OR search for ID strings that start with the
    # ID suffix and are used for items in the root_suggest_obj
    # project
    proj_ark_id_qs = AllIdentifier.objects.filter(
        item=root_suggest_obj,
        scheme='ark',
    )
    query_ids = []
    for proj_ark_id_obj in proj_ark_id_qs:
        for i in range(1, len(id_suffix) + 1):
            act_suffix = id_suffix[:i]
            id_start = f'{proj_ark_id_obj.id}/{act_suffix}'
            query_ids.append(id_start)
            # Add a lower case version, if not present already
            lc_id_start = f'{proj_ark_id_obj.id}/{act_suffix.lower()}'
            if lc_id_start in query_ids:
                continue
            query_ids.append(lc_id_start)
    # Do the query, looking up ARKs for items in this project
    # where the id_suffix from the request may start with characters
    # that match a known ARK id.
    id_obj = AllIdentifier.objects.filter(
        item__project=root_suggest_obj,
        scheme='ark',
    ).filter(
        id__in=query_ids,
    ).annotate(
        id_len=Length('id')
    ).order_by(
        '-id_len'
    ).first()
    if not id_obj:
        # We didn't find a more specific item, via "backing off" characters in the
        # requested identifier suffix. So just return the
        # root_suggest_obj (for the project)
        return root_suggest_obj
    return id_obj.item


def get_suffix_backoff_suggest_message(unmatched_id):
    """Get string suggestion message for a suggested (semantic) parent
    resource to provide a more informative 404 error.
    """
    suggest_obj = get_suffix_backoff_suggest_obj(unmatched_id)
    if not suggest_obj:
        return None
    message = 'The resource you requested could not be found. However, the '
    if suggest_obj.item_type == 'projects':
        message += 'Open Context project '
    else:
        message += 'resource '
    message += f'<strong><em>"<a href="https://{suggest_obj.uri}">{suggest_obj.label}</a>"</em></strong> '
    message += 'likely provides related information that may help you find what you need.'
    # print(f'Message for 404: {message}')
    return message


@never_cache
def all_items_json(request, uuid, man_obj=None):
    """ API for searching Open Context """
    if man_obj:
        ok_uuid = man_obj.uuid
        do_redirect = False
    else:
        ok_uuid, do_redirect = evaluate_update_id(uuid)
    if not ok_uuid:
        raise Http404
    if do_redirect:
        return make_redirect_url(request, 'all-items', ok_uuid, extension='.json')
    if request.GET.get('solr') == 'prep':
        # with added stuff for Solr
        man_obj, rep_dict = item.make_representation_dict(
            subject_id=ok_uuid,
            for_solr=True,
        )
        if not man_obj or not rep_dict:
            raise Http404
        rep_dict = prepare_for_item_dict_solr_and_html_template(
            man_obj,
            rep_dict
        )
        rep_dict['for_solr_assert_objs'] = len(
            rep_dict.get('for_solr_assert_objs', [])
        )
    elif request.GET.get('solr') == 'solr':
        # with added stuff for Solr
        man_obj, rep_dict = item.make_representation_dict(
            subject_id=ok_uuid,
            for_solr=True,
        )
        if not man_obj or not rep_dict:
            raise Http404
        rep_dict = prepare_for_item_dict_solr_and_html_template(
            man_obj,
            rep_dict
        )
        solrdoc = SolrDocumentNS(
            uuid=man_obj.uuid,
            man_obj=man_obj,
            rep_dict=rep_dict,
        )
        solrdoc.make_solr_doc()
        rep_dict = solrdoc.fields
    else:
        # default, simple JSON-LD
        man_obj, rep_dict = item.make_representation_dict(subject_id=ok_uuid)
    if not man_obj or not rep_dict:
        raise Http404
    allow_view, allow_edit = get_request_user_permissions(request, man_obj)
    if not allow_view:
        for rem_key in ['oc-gen:has-obs', 'oc-gen:has-files']:
            if not rem_key in rep_dict:
                continue
            rep_dict.pop(rem_key)

    json_output = json.dumps(
        rep_dict,
        indent=4,
        ensure_ascii=False
    )
    return HttpResponse(
        json_output,
        content_type="application/json; charset=utf8"
    )


def make_solr_doc_in_html(request, uuid):
    """Make a Solr Doc JSON in HTML for debugging"""
    ok_uuid, do_redirect = evaluate_update_id(uuid)
    if not ok_uuid:
        raise Http404
    if do_redirect:
        return make_redirect_url(request, 'all-items-solr', ok_uuid)
    man_obj, rep_dict = item.make_representation_dict(
        subject_id=ok_uuid,
        for_solr=True,
    )
    if not man_obj or not rep_dict:
        raise Http404
    rep_dict = prepare_for_item_dict_solr_and_html_template(
        man_obj,
        rep_dict
    )
    solrdoc = SolrDocumentNS(
        uuid=man_obj.uuid,
        man_obj=man_obj,
        rep_dict=rep_dict,
    )
    solrdoc.make_solr_doc()
    rp = RootPath()
    context = {
        'NAV_ITEMS': settings.NAV_ITEMS,
        'CANONICAL_URI': f'https://{man_obj.uri}',
        'BASE_URL': rp.get_baseurl(),
        'PAGE_TITLE': f'Solr Doc: {man_obj.label}',
        'solr_json': json.dumps(
            solrdoc.fields,
            indent=4,
            ensure_ascii=False
        ),
    }
    template = loader.get_template('bootstrap_vue/item/item_solr.html')
    response = HttpResponse(template.render(context, request))
    patch_vary_headers(response, ['accept', 'Accept', 'content-type'])
    return response


@never_cache
def all_items_html(
    request,
    uuid,
    full_media=False,
    template_file='item.html',
    man_obj=None
):
    """HTML representation for searching Open Context """
    if man_obj:
        ok_uuid = man_obj.uuid
        do_redirect = False
    else:
        ok_uuid, do_redirect = evaluate_update_id(uuid)
    if not ok_uuid:
        message = get_suffix_backoff_suggest_message(unmatched_id=uuid)
        if message:
            messages.error(request, message)
        raise Http404
    if do_redirect:
        return make_redirect_url(request, 'all-items', ok_uuid, extension='')
    if request.GET.get('solr') == 'solr':
        # with added stuff for Solr
        return make_solr_doc_in_html(request, ok_uuid)

    man_obj, rep_dict = item.make_representation_dict(
        subject_id=ok_uuid,
        for_solr_or_html=True,
    )
    if not man_obj or not rep_dict:
        raise Http404
    allow_view, allow_edit = get_request_user_permissions(request, man_obj)
    if not allow_view:
        for rem_key in ['oc-gen:has-obs', 'oc-gen:has-files']:
            if not rem_key in rep_dict:
                continue
            rep_dict.pop(rem_key)
    item_dict = prepare_for_item_dict_html_template(man_obj, rep_dict)
    json_output = json.dumps(
        item_dict,
        indent=4,
        ensure_ascii=False
    )
    schema_org_meta = make_schema_org_json_ld(rep_dict)
    geo_json = None
    if rep_dict.get('features'):
        geo_json = json.dumps(
            {
                'type': 'FeatureCollection',
                'features': rep_dict.get('features'),
            },
            indent=4,
            ensure_ascii=False
        )
    # Get the edit status for the specific item, and if it
    # does not exist, get it for the parent project.
    edit_status = man_obj.meta_json.get(
        'edit_status',
        man_obj.project.meta_json.get('edit_status')
    )
    canonical_uri = f'https://{man_obj.uri}'
    if man_obj.item_class and str(man_obj.item_class.uuid) == configs.CLASS_OC_IMAGE_MEDIA and rep_dict.get('media_iiif'):
        # Use the media full url for as the canonical uri for this item.
        canonical_uri = f'https://{man_obj.uri}/full'
    query_context_path = man_obj.meta_json.get('query_context_path', '')
    query_context_path = query_context_path.replace(' ', '+')
    rp = RootPath()
    context = {
        'NAV_ITEMS': settings.NAV_ITEMS,
        'HREF': rep_dict['href'],
        'CANONICAL_URI': canonical_uri,
        'BASE_URL': rp.get_baseurl(),
        'PAGE_TITLE': f'Open Context: {rep_dict["label"]}',
        'SOCIAL_MEDIA_META': make_social_media_metadata(
            canonical_uri=canonical_uri,
            man_obj=man_obj,
            rep_dict=rep_dict,
        ),
        'SCHEMA_ORG_JSON_LD': json.dumps(
            schema_org_meta,
            indent=4,
            ensure_ascii=False
        ),
        'MAPBOX_PUBLIC_ACCESS_TOKEN': settings.MAPBOX_PUBLIC_ACCESS_TOKEN,
        'HERO_BANNER_URL': get_hero_banner_url(man_obj),
        'GEO_JSON': geo_json,
        # Expected order of related item_types
        'order_of_related_item_types': [
            'subjects',
            'media',
            'documents',
            'tables',
            'persons',
            'subjects_children'
        ],
        'citation':citation.make_citation_dict(rep_dict),
        'man_obj': man_obj,
        'edit_status': edit_status,
        'query_context_path': query_context_path,
        'item': item_dict,
        'item_json': json_output,
        'full_media': full_media,
        'attribute_group': request.GET.get('attribute-group', None),
        # for debugging.
        'show_json': request.GET.get('json', False),
        # Consent to view human remains defaults to False if not actually set.
        'human_remains_ok': request.session.get('human_remains_ok', False),
        'allow_view': allow_view,
        'is_parent_proj_oc': (str(man_obj.project.uuid) == configs.OPEN_CONTEXT_PROJ_UUID),
    }
    template = loader.get_template(f'bootstrap_vue/item/{template_file}')
    response = HttpResponse(template.render(context, request))
    patch_vary_headers(response, ['accept', 'Accept', 'content-type'])
    return response


@never_cache
def all_items_html_full(request, uuid):
    """HTML Media Full representation for searching Open Context """
    # NOTE: There is NO templating here, this is strictly so we can
    # use the Django debugger to optimize queries
    return all_items_html(request, uuid, full_media=True)


def subjects_html(request, uuid):
    """HTML Subjects Item representation Open Context """
    ok_uuid, do_redirect = evaluate_update_id(uuid)
    if not ok_uuid:
        message = get_suffix_backoff_suggest_message(unmatched_id=uuid)
        if message:
            messages.error(request, message)
        raise Http404
    if do_redirect:
        return make_redirect_url(request, 'subjects', ok_uuid, extension='')
    return all_items_html(request, ok_uuid)

def subjects_json(request, uuid):
    """JSON Subjects Item representation Open Context """
    ok_uuid, do_redirect = evaluate_update_id(uuid)
    if not ok_uuid:
        raise Http404
    if do_redirect:
        return make_redirect_url(request, 'subjects', ok_uuid, extension='.json')
    return all_items_json(request, ok_uuid)



def media_html(request, uuid):
    """HTML Media Item representation Open Context """
    ok_uuid, do_redirect = evaluate_update_id(uuid)
    if not ok_uuid:
        message = get_suffix_backoff_suggest_message(unmatched_id=uuid)
        if message:
            messages.error(request, message)
        raise Http404
    if do_redirect:
        return make_redirect_url(request, 'media', ok_uuid, extension='')
    return all_items_html(request, ok_uuid)

def media_full_html(request, uuid):
    """HTML Media full Item representation Open Context """
    ok_uuid, do_redirect = evaluate_update_id(uuid)
    if not ok_uuid:
        message = get_suffix_backoff_suggest_message(unmatched_id=uuid)
        if message:
            messages.error(request, message)
        raise Http404
    if do_redirect:
        ok_uuid = str(ok_uuid)
        return make_redirect_url(
            request,
            'media',
            f'{ok_uuid}/full',
            extension=''
        )
    return all_items_html(request, ok_uuid, full_media=True)

def media_json(request, uuid):
    """JSON Media Item representation Open Context """
    ok_uuid, do_redirect = evaluate_update_id(uuid)
    if not ok_uuid:
        raise Http404
    if do_redirect:
        return make_redirect_url(request, 'media', ok_uuid, extension='.json')
    return all_items_json(request, ok_uuid)



def documents_html(request, uuid):
    """HTML Documents Item representation Open Context """
    ok_uuid, do_redirect = evaluate_update_id(uuid)
    if not ok_uuid:
        message = get_suffix_backoff_suggest_message(unmatched_id=uuid)
        if message:
            messages.error(request, message)
        raise Http404
    if do_redirect:
        return make_redirect_url(request, 'documents', ok_uuid, extension='')
    return all_items_html(request, ok_uuid)

def documents_json(request, uuid):
    """JSON Media Item representation Open Context """
    ok_uuid, do_redirect = evaluate_update_id(uuid)
    if not ok_uuid:
        raise Http404
    if do_redirect:
        return make_redirect_url(request, 'documents', ok_uuid, extension='.json')
    return all_items_json(request, ok_uuid)


def projects_html(request, uuid):
    """HTML Projects Item representation Open Context """
    ok_uuid, do_redirect = evaluate_update_id(uuid)
    if not ok_uuid:
        message = get_suffix_backoff_suggest_message(unmatched_id=uuid)
        if message:
            messages.error(request, message)
        raise Http404
    if do_redirect:
        return make_redirect_url(request, 'projects', ok_uuid, extension='')
    return all_items_html(request, ok_uuid)

def projects_json(request, uuid):
    """JSON Projects Item representation Open Context """
    ok_uuid, do_redirect = evaluate_update_id(uuid)
    if not ok_uuid:
        raise Http404
    if do_redirect:
        return make_redirect_url(request, 'projects', ok_uuid, extension='.json')
    return all_items_json(request, ok_uuid)


def persons_html(request, uuid):
    """HTML Persons Item representation Open Context """
    ok_uuid, do_redirect = evaluate_update_id(uuid)
    if not ok_uuid:
        message = get_suffix_backoff_suggest_message(unmatched_id=uuid)
        if message:
            messages.error(request, message)
        raise Http404
    if do_redirect:
        return make_redirect_url(request, 'persons', ok_uuid, extension='')
    return all_items_html(request, ok_uuid)

def persons_json(request, uuid):
    """JSON Persons Item representation Open Context """
    ok_uuid, do_redirect = evaluate_update_id(uuid)
    if not ok_uuid:
        raise Http404
    if do_redirect:
        return make_redirect_url(request, 'persons', ok_uuid, extension='.json')
    return all_items_json(request, ok_uuid)


def predicates_html(request, uuid):
    """HTML Predicates Item representation Open Context """
    ok_uuid, do_redirect = evaluate_update_id(uuid)
    if not ok_uuid:
        message = get_suffix_backoff_suggest_message(unmatched_id=uuid)
        if message:
            messages.error(request, message)
        raise Http404
    if do_redirect:
        return make_redirect_url(request, 'predicates', ok_uuid, extension='')
    return all_items_html(request, ok_uuid)

def predicates_json(request, uuid):
    """JSON Predicates Item representation Open Context """
    ok_uuid, do_redirect = evaluate_update_id(uuid)
    if not ok_uuid:
        raise Http404
    if do_redirect:
        return make_redirect_url(request, 'predicates', ok_uuid, extension='.json')
    return all_items_json(request, ok_uuid)


def types_html(request, uuid):
    """HTML Types Item representation Open Context """
    ok_uuid, do_redirect = evaluate_update_id(uuid)
    if not ok_uuid:
        message = get_suffix_backoff_suggest_message(unmatched_id=uuid)
        if message:
            messages.error(request, message)
        raise Http404
    if do_redirect:
        return make_redirect_url(request, 'types', ok_uuid, extension='')
    return all_items_html(request, ok_uuid)

def types_json(request, uuid):
    """JSON Types Item representation Open Context """
    ok_uuid, do_redirect = evaluate_update_id(uuid)
    if not ok_uuid:
        raise Http404
    if do_redirect:
        return make_redirect_url(request, 'types', ok_uuid, extension='.json')
    return all_items_json(request, ok_uuid)


def tables_html(request, uuid):
    """HTML Tables Item representation Open Context """
    ok_uuid, do_redirect = evaluate_update_id(uuid)
    if not ok_uuid:
        message = get_suffix_backoff_suggest_message(unmatched_id=uuid)
        if message:
            messages.error(request, message)
        raise Http404
    if do_redirect:
        return make_redirect_url(request, 'tables', ok_uuid, extension='')
    return all_items_html(request, ok_uuid, template_file='table.html')

def tables_json(request, uuid):
    """JSON Tables Item representation Open Context """
    ok_uuid, do_redirect = evaluate_update_id(uuid)
    if not ok_uuid:
        raise Http404
    if do_redirect:
        return make_redirect_url(request, 'tables', ok_uuid, extension='.json')
    return all_items_json(request, ok_uuid)

def tables_csv(request, uuid):
    """CSV Tables Item representation Open Context """
    ok_uuid, do_redirect = evaluate_update_id(uuid)
    if not ok_uuid:
        raise Http404
    if do_redirect:
        return make_redirect_url(request, 'tables', ok_uuid, extension='.csv')
    man_obj = AllManifest.objects.filter(uuid=ok_uuid).first()
    if not man_obj:
        raise Http404
    allow_view, _ = get_request_user_permissions(request, man_obj)
    if not allow_view:
        return 'Not allowed'
    csv_url = man_obj.table_full_csv_url
    if not csv_url:
        raise Http404
    return redirect(csv_url, permanent=False)


def vocabularies_html(request, identifier):
    uri = f'{settings.CANONICAL_BASE_URL}/vocabularies/{identifier}'
    uri = AllManifest().clean_uri(uri)
    man_obj = AllManifest.objects.filter(uri=uri).first()
    if not man_obj:
        raise Http404
    return all_items_html(request, man_obj.uuid, man_obj=man_obj)

def vocabularies_json(request, identifier):
    uri = f'{settings.CANONICAL_BASE_URL}/vocabularies/{identifier}'
    uri = AllManifest().clean_uri(uri)
    man_obj = AllManifest.objects.filter(uri=uri).first()
    if not man_obj:
        raise Http404
    return all_items_json(request, man_obj.uuid, man_obj=man_obj)