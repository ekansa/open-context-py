import json
from django.http import HttpResponse, Http404
from opencontext_py.apps.imports.fields.templating import ImportProfile
from opencontext_py.apps.imports.fields.describe import ImportFieldDescribe
from opencontext_py.apps.imports.fieldannotations.models import ImportFieldAnnotation
from opencontext_py.apps.imports.fieldannotations.subjects import ProcessSubjects
from opencontext_py.apps.imports.fieldannotations.descriptions import ProcessDescriptions
from opencontext_py.apps.imports.fieldannotations.links import ProcessLinks
from opencontext_py.apps.ocitems.assertions.models import Assertion
from django.template import RequestContext, loader
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.cache import cache_control
from django.views.decorators.cache import never_cache


# These views display an HTML form for classifying import fields,
# and handles AJAX requests / responses to change classifications
def index(request):
    return HttpResponse("Hello, world. You're at the imports fields annotations index.")


@cache_control(no_cache=True)
@never_cache
def view(request, source_id):
    """ Returns JSON data for an identifier in its hierarchy """
    if not request.user.is_superuser:
        return HttpResponse('Unauthorized', status=401)
    else:
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


@cache_control(no_cache=True)
@never_cache
def subjects_hierarchy_examples(request, source_id):
    """ Returns JSON data with examples of the subjects hierarchy """
    if not request.user.is_superuser:
        return HttpResponse('Unauthorized', status=401)
    else:
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


@cache_control(no_cache=True)
@never_cache
def described_examples(request, source_id):
    """ Returns JSON data with examples of described entites """
    if not request.user.is_superuser:
        return HttpResponse('Unauthorized', status=401)
    else:
        pd = ProcessDescriptions(source_id)
        if pd.project_uuid is not False:
            example_list = pd.get_description_examples()
            json_output = json.dumps(example_list,
                                     indent=4,
                                     ensure_ascii=False)
            return HttpResponse(json_output,
                                content_type='application/json; charset=utf8')
        else:
            raise Http404


@cache_control(no_cache=True)
@never_cache
def linked_examples(request, source_id):
    """ Returns JSON data with examples of described entites """
    if not request.user.is_superuser:
        return HttpResponse('Unauthorized', status=401)
    else:
        pl = ProcessLinks(source_id)
        if pl.project_uuid is not False:
            example_list = pl.get_link_examples()
            json_output = json.dumps(example_list,
                                     indent=4,
                                     ensure_ascii=False)
            return HttpResponse(json_output,
                                content_type='application/json; charset=utf8')
        else:
            raise Http404


@cache_control(no_cache=True)
def delete(request, source_id, annotation_id):
    """ Returns JSON data for an identifier in its hierarchy """
    if not request.user.is_superuser:
        return HttpResponse('Unauthorized', status=401)
    else:
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


@cache_control(no_cache=True)
def create(request, source_id):
    """ Classifies one or more fields with posted data """
    if not request.user.is_superuser:
        return HttpResponse('Unauthorized', status=401)
    else:
        if request.method == 'POST':
            ip = ImportProfile(source_id)
            if ip.project_uuid is not False:
                predicate_field_num = None
                ifd = ImportFieldDescribe(source_id)
                ifd.project_uuid = ip.project_uuid
                if 'predicate_field_num' in request.POST:
                    try:
                        predicate_field_num =  int(float(request.POST['predicate_field_num']))
                    except:
                        predicate_field_num = None
                if request.POST['predicate'] == Assertion.PREDICATES_CONTAINS:
                    ifd.update_field_contains(request.POST['field_num'],
                                              request.POST['object_field_num'])
                elif request.POST['predicate'] == ImportFieldAnnotation.PRED_CONTAINED_IN:
                    ifd.update_field_containedin_entity(request.POST['field_num'],
                                                        request.POST['object_uuid'])
                elif request.POST['predicate'] == ImportFieldAnnotation.PRED_DRAFT_CONTAINS:
                    ifd.update_field_contains(request.POST['field_num'],
                                              request.POST['object_field_num'],
                                              ImportFieldAnnotation.PRED_DRAFT_CONTAINS)
                elif request.POST['predicate'] == ImportFieldAnnotation.PRED_MEDIA_PART_OF:
                    ifd.update_field_media_part_of_entity(request.POST['field_num'],
                                                          request.POST['object_field_num'])
                elif request.POST['predicate'] == ImportFieldAnnotation.PRED_DOC_Text:
                    ifd.update_field_document_text_entity(request.POST['field_num'],
                                                          request.POST['object_field_num'])
                elif request.POST['predicate'] == Assertion.PREDICATES_LINK:
                    if 'object_field_num' in request.POST:
                        ifd.update_field_links(request.POST['field_num'],
                                               request.POST['object_field_num'])
                elif request.POST['predicate'] == ImportFieldAnnotation.PRED_DESCRIBES:
                    if 'object_field_num' in request.POST:
                        ifd.update_description(request.POST['field_num'],
                                               request.POST['object_field_num'])
                elif request.POST['predicate'] == ImportFieldAnnotation.PRED_VALUE_OF:
                    if 'object_field_num' in request.POST:
                        ifd.update_variable_value(request.POST['field_num'],
                                                  request.POST['object_field_num'])
                elif request.POST['predicate'] == ImportFieldAnnotation.PRED_OBS_NUM:
                    if 'object_field_num' in request.POST:
                        ifd.update_obs_num(request.POST['field_num'],
                                           request.POST['object_field_num'])
                else:
                    if predicate_field_num is None:
                        # we don't have a field chosen for a predicate relationship
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
                    else:
                        # we do have a field chosen where its values determine the predicate relationship
                        ifd.update_field_predicate_infield(request.POST['field_num'],
                                                           request.POST['object_field_num'],
                                                           predicate_field_num)
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
