import json
from django.conf import settings
from django.http import HttpResponse, Http404
from django.shortcuts import redirect

from django.template import loader
from opencontext_py.libs.rootpath import RootPath
from opencontext_py.libs.requestnegotiation import RequestNegotiation
from opencontext_py.apps.all_items.representations import item
from opencontext_py.apps.all_items.representations.template_prep import (
    prepare_for_item_dict_solr_and_html_template,
    prepare_for_item_dict_html_template
)
from opencontext_py.apps.all_items.representations.schema_org import (
    make_schema_org_json_ld
)
from opencontext_py.apps.all_items.representations import citation
from opencontext_py.apps.all_items.legacy_all import update_old_id

from opencontext_py.apps.indexer.solrdocument_new_schema import SolrDocumentNS

from opencontext_py.apps.all_items.editorial.api import get_man_obj_by_any_id

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
    item_obj = get_man_obj_by_any_id(ok_uuid)
    if item_obj:
        return item_obj.uuid, True
    item_obj = get_man_obj_by_any_id(uuid)
    if item_obj:
        return item_obj.uuid, True
    return None, False


@never_cache
def test_json(request, uuid):
    """ API for searching Open Context """
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
        _, rep_dict = item.make_representation_dict(subject_id=ok_uuid)
    
    json_output = json.dumps(
        rep_dict,
        indent=4,
        ensure_ascii=False
    )
    return HttpResponse(
        json_output,
        content_type="application/json; charset=utf8"
    )


def make_solr_doc_in_html(request, ok_uuid):
    """Make a Solr Doc JSON in HTML for debugging"""
    man_obj, rep_dict = item.make_representation_dict(
        subject_id=ok_uuid,
        for_solr=True,
    )
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
def test_html(request, uuid, full_media=False):
    """HTML representation for searching Open Context """
    ok_uuid, do_redirect = evaluate_update_id(uuid)
    if not ok_uuid:
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
    rp = RootPath()
    context = {
        'NAV_ITEMS': settings.NAV_ITEMS,
        'BASE_URL': rp.get_baseurl(),
        'PAGE_TITLE': f'Open Context: {rep_dict["label"]}',
        'SCHEMA_ORG_JSON_LD': json.dumps(
            schema_org_meta,
            indent=4,
            ensure_ascii=False
        ),
        'MAPBOX_PUBLIC_ACCESS_TOKEN': settings.MAPBOX_PUBLIC_ACCESS_TOKEN,
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
        'item': item_dict,
        'item_json': json_output,
        'full_media': full_media,
        # for debugging.
        'show_json': request.GET.get('json', False),
        # Consent to view human remains defaults to False if not actually set.
        'human_remains_ok': request.session.get('human_remains_ok', False),
    }
    template = loader.get_template('bootstrap_vue/item/item.html')
    response = HttpResponse(template.render(context, request))
    patch_vary_headers(response, ['accept', 'Accept', 'content-type'])
    return response


@never_cache
def test_html_full(request, uuid):
    """HTML Media Full representation for searching Open Context """
    # NOTE: There is NO templating here, this is strictly so we can 
    # use the Django debugger to optimize queries
    return test_html(request, uuid, full_media=True)


def subjects_html(request, uuid):
    """HTML Subjects Item representation Open Context """
    ok_uuid, do_redirect = evaluate_update_id(uuid)
    if not ok_uuid:
        raise Http404 
    if do_redirect:
        return make_redirect_url(request, 'subjects', ok_uuid, extension='')
    return test_html(request, ok_uuid)

def subjects_json(request, uuid):
    """JSON Subjects Item representation Open Context """
    ok_uuid, do_redirect = evaluate_update_id(uuid)
    if not ok_uuid:
        raise Http404 
    if do_redirect:
        return make_redirect_url(request, 'subjects', ok_uuid, extension='.json')
    return test_json(request, ok_uuid)



def media_html(request, uuid):
    """HTML Media Item representation Open Context """
    ok_uuid, do_redirect = evaluate_update_id(uuid)
    if not ok_uuid:
        raise Http404 
    if do_redirect:
        return make_redirect_url(request, 'media', ok_uuid, extension='')
    return test_html(request, ok_uuid)

def media_full_html(request, uuid):
    """HTML Media full Item representation Open Context """
    ok_uuid, do_redirect = evaluate_update_id(uuid)
    if not ok_uuid:
        raise Http404 
    if do_redirect:
        ok_uuid = str(ok_uuid)
        return make_redirect_url(
            request, 
            'media', 
            f'{ok_uuid}/full', 
            extension=''
        )
    return test_html(request, ok_uuid, full_media=True)

def media_json(request, uuid):
    """JSON Media Item representation Open Context """
    ok_uuid, do_redirect = evaluate_update_id(uuid)
    if not ok_uuid:
        raise Http404 
    if do_redirect:
        return make_redirect_url(request, 'media', ok_uuid, extension='.json')
    return test_json(request, ok_uuid)



def documents_html(request, uuid):
    """HTML Documents Item representation Open Context """
    ok_uuid, do_redirect = evaluate_update_id(uuid)
    if not ok_uuid:
        raise Http404 
    if do_redirect:
        return make_redirect_url(request, 'documents', ok_uuid, extension='')
    return test_html(request, ok_uuid)

def documents_json(request, uuid):
    """JSON Media Item representation Open Context """
    ok_uuid, do_redirect = evaluate_update_id(uuid)
    if not ok_uuid:
        raise Http404 
    if do_redirect:
        return make_redirect_url(request, 'documents', ok_uuid, extension='.json')
    return test_json(request, ok_uuid)


def projects_html(request, uuid):
    """HTML Projects Item representation Open Context """
    ok_uuid, do_redirect = evaluate_update_id(uuid)
    if not ok_uuid:
        raise Http404 
    if do_redirect:
        return make_redirect_url(request, 'projects', ok_uuid, extension='')
    return test_html(request, ok_uuid)

def projects_json(request, uuid):
    """JSON Projects Item representation Open Context """
    ok_uuid, do_redirect = evaluate_update_id(uuid)
    if not ok_uuid:
        raise Http404 
    if do_redirect:
        return make_redirect_url(request, 'projects', ok_uuid, extension='.json')
    return test_json(request, ok_uuid)


def persons_html(request, uuid):
    """HTML Persons Item representation Open Context """
    ok_uuid, do_redirect = evaluate_update_id(uuid)
    if not ok_uuid:
        raise Http404 
    if do_redirect:
        return make_redirect_url(request, 'persons', ok_uuid, extension='')
    return test_html(request, ok_uuid)

def persons_json(request, uuid):
    """JSON Persons Item representation Open Context """
    ok_uuid, do_redirect = evaluate_update_id(uuid)
    if not ok_uuid:
        raise Http404 
    if do_redirect:
        return make_redirect_url(request, 'persons', ok_uuid, extension='.json')
    return test_json(request, ok_uuid)


def predicates_html(request, uuid):
    """HTML Predicates Item representation Open Context """
    ok_uuid, do_redirect = evaluate_update_id(uuid)
    if not ok_uuid:
        raise Http404 
    if do_redirect:
        return make_redirect_url(request, 'predicates', ok_uuid, extension='')
    return test_html(request, ok_uuid)

def predicates_json(request, uuid):
    """JSON Predicates Item representation Open Context """
    ok_uuid, do_redirect = evaluate_update_id(uuid)
    if not ok_uuid:
        raise Http404 
    if do_redirect:
        return make_redirect_url(request, 'predicates', ok_uuid, extension='.json')
    return test_json(request, ok_uuid)


def types_html(request, uuid):
    """HTML Types Item representation Open Context """
    ok_uuid, do_redirect = evaluate_update_id(uuid)
    if not ok_uuid:
        raise Http404 
    if do_redirect:
        return make_redirect_url(request, 'types', ok_uuid, extension='')
    return test_html(request, ok_uuid)

def types_json(request, uuid):
    """JSON Types Item representation Open Context """
    ok_uuid, do_redirect = evaluate_update_id(uuid)
    if not ok_uuid:
        raise Http404 
    if do_redirect:
        return make_redirect_url(request, 'types', ok_uuid, extension='.json')
    return test_json(request, ok_uuid)