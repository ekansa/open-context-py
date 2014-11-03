import json
from django.http import HttpResponse, Http404
from opencontext_py.apps.imports.fields.templating import ImportProfile
from opencontext_py.apps.imports.fields.describe import ImportFieldDescribe
from opencontext_py.apps.imports.fieldannotations.models import ImportFieldAnnotation
from opencontext_py.apps.imports.fieldannotations.subjects import ProcessSubjects
from opencontext_py.apps.ocitems.assertions.models import Assertion
from django.template import RequestContext, loader
from django.views.decorators.csrf import ensure_csrf_cookie


# These views display an HTML form for classifying import fields,
# and handles AJAX requests / responses to change classifications
def index(request):
    return HttpResponse("Hello, world. You're at the imports fields annotations index.")


def view(request, source_id):
    """ Returns JSON data for an identifier in its hierarchy """
    ip = ImportProfile(source_id)
    if ip.project_uuid is not False:
        ip.get_field_annotations()
        anno_list = ip.jsonify_field_annotations()
        json_output = json.dumps(anno_list,
                                 indent=4,
                                 ensure_ascii=False)
        return HttpResponse(json_output,
                            content_type='application/json; charset=utf8')
    else:
        raise Http404


def subjects_hierarchy_examples(request, source_id):
    """ Returns JSON data with examples of the subjects hierarchy """
    ps = ProcessSubjects(source_id)
    if ps.project_uuid is not False:
        cont_list = ps.get_contained_examples()
        json_output = json.dumps(cont_list,
                                 indent=4,
                                 ensure_ascii=False)
        return HttpResponse(json_output,
                            content_type='application/json; charset=utf8')
    else:
        raise Http404


def described_examples(request, source_id):
    """ Returns JSON data with examples of described entites """
    ps = ProcessSubjects(source_id)
    if ps.project_uuid is not False:
        cont_list = ps.get_contained_examples()
        json_output = json.dumps(cont_list,
                                 indent=4,
                                 ensure_ascii=False)
        return HttpResponse(json_output,
                            content_type='application/json; charset=utf8')
    else:
        raise Http404


def delete(request, source_id, annotation_id):
    """ Returns JSON data for an identifier in its hierarchy """
    if request.method == 'POST':
        ip = ImportProfile(source_id)
        if ip.project_uuid is not False:
            ifd = ImportFieldDescribe(source_id)
            ifd.delete_field_annotation(annotation_id)
            ip.get_field_annotations()
            anno_list = ip.jsonify_field_annotations()
            json_output = json.dumps(anno_list,
                                     indent=4,
                                     ensure_ascii=False)
            return HttpResponse(json_output,
                                content_type='application/json; charset=utf8')
        else:
            raise Http404
    else:
        return HttpResponseForbidden


def create(request, source_id):
    """ Classifies one or more fields with posted data """
    if request.method == 'POST':
        ip = ImportProfile(source_id)
        if ip.project_uuid is not False:
            ifd = ImportFieldDescribe(source_id)
            ifd.project_uuid = ip.project_uuid
            if request.POST['predicate'] == Assertion.PREDICATES_CONTAINS:
                ifd.update_field_contains(request.POST['field_num'],
                                          request.POST['object_field_num'])
            elif request.POST['predicate'] == ImportFieldAnnotation.PRED_CONTAINED_IN:
                ifd.update_field_containedin_entity(request.POST['field_num'],
                                                    request.POST['object_uuid'])
            elif request.POST['predicate'] == Assertion.PREDICATES_LINK:
                if 'object_field_num' in request.POST:
                    ifd.update_field_links(request.POST['field_num'],
                                           request.POST['object_field_num'])
            elif request.POST['predicate'] == ImportFieldAnnotation.PRED_DESCRIBES:
                if 'object_field_num' in request.POST:
                    ifd.update_desciption(request.POST['field_num'],
                                          request.POST['object_field_num'])
            elif request.POST['predicate'] == ImportFieldAnnotation.PRED_VALUE_OF:
                if 'object_field_num' in request.POST:
                    ifd.update_variable_value(request.POST['field_num'],
                                              request.POST['object_field_num'])
            else:
                if request.POST['predicate'] == '-1':
                    # the predicate is not yet reconciled
                    predicate_id = ifd.make_or_reconcile_link_predicate(request.POST['predicate_label'],
                                                                        ifd.project_uuid)
                else:
                    predicate_id = request.POST['predicate']
                ifd.update_field_custom_predicate(request.POST['field_num'],
                                                  request.POST['object_field_num'],
                                                  predicate_id,
                                                  request.POST['predicate_type'])
            ip.get_field_annotations()
            anno_list = ip.jsonify_field_annotations()
            json_output = json.dumps(anno_list,
                                     indent=4,
                                     ensure_ascii=False)
            return HttpResponse(json_output,
                                content_type='application/json; charset=utf8')
        else:
            raise Http404
    else:
        return HttpResponseForbidden
