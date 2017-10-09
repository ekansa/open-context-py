import json
from opencontext_py.libs.rootpath import RootPath
from django.http import HttpResponse, Http404, HttpResponseRedirect
from opencontext_py.apps.imports.sources.projects import ImportProjects
from opencontext_py.apps.imports.sources.models import ImportSource
from opencontext_py.apps.imports.sources.navtemplate import ImportNavigation
from opencontext_py.apps.imports.sources.create import ImportRefineSource
from opencontext_py.apps.imports.sources.finalize import FinalizeImport
from opencontext_py.apps.imports.fields.templating import ImportProfile
from opencontext_py.apps.imports.fields.describe import ImportFieldDescribe
from django.template import RequestContext, loader
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.cache import cache_control
from django.views.decorators.cache import never_cache


"""
-------------------------------------------------------------
BELOW HERE ARE VIEWS FOR ACCEPTING POST REQUESTS
THAT CREATE NEW PROJECTS, EDIT PROJECT NAMES,
AND IMPORT DATA TO A PROJECT FROM REFINE
-------------------------------------------------------------
"""


@cache_control(no_cache=True)
@never_cache
def create_project(request):
    """ Create a new project """
    if not request.user.is_superuser:
        return HttpResponse('Unauthorized', status=401)
    else:
        valid_post = False
        if request.method == 'POST':
            label = False
            short_des = False
            if 'label' in request.POST:
                label = request.POST['label']
            if 'short_des' in request.POST:
                short_des = request.POST['short_des']
            if label is not False and short_des is not False:
                valid_post = True
        if valid_post:
            ipr = ImportProjects()
            project_uuid = ipr.create_project(label,
                                              short_des)
            return HttpResponseRedirect('../../imports/project/' + str(project_uuid))
        else:
            return HttpResponseForbidden


@cache_control(no_cache=True)
@never_cache
def edit_project(request, project_uuid):
    """ Create a new project """
    if not request.user.is_superuser:
        return HttpResponse('Unauthorized', status=401)
    else:
        valid_post = False
        if request.method == 'POST':
            label = False
            short_des = False
            if 'label' in request.POST:
                label = request.POST['label']
            if 'short_des' in request.POST:
                short_des = request.POST['short_des']
            if label is not False and short_des is not False:
                valid_post = True
        if valid_post:
            ipr = ImportProjects()
            ok = ipr.edit_project(project_uuid,
                                  label,
                                  short_des)
            if ok:
                return HttpResponseRedirect('../../imports/project/' + project_uuid)
            else:
                raise Http404
        else:
            return HttpResponseForbidden


@cache_control(no_cache=True)
@never_cache
def project_import_refine(request, project_uuid):
    """ Imports data from refine to a project """
    if not request.user.is_superuser:
        return HttpResponse('Unauthorized', status=401)
    else:
        valid_post = False
        if request.method == 'POST':
            refine_project = False
            if 'refine_project' in request.POST:
                refine_project = request.POST['refine_project']
                valid_post = True
        if valid_post:
            ipr = ImportProjects()
            proj = ipr.get_project(project_uuid)
            if proj is not False:
                # the project actually exists
                irs = ImportRefineSource()
                result = irs.import_refine_to_project(refine_project,
                                                      project_uuid)
                json_output = json.dumps(result,
                                         indent=4,
                                         ensure_ascii=False)
                return HttpResponse(json_output,
                                    content_type='application/json; charset=utf8')
            else:
                raise Http404
        else:
            return HttpResponseForbidden

"""
from opencontext_py.apps.imports.sources.create import ImportRefineSource
refine_project = '2200545655556'
project_uuid = '3885b0b6-2ba8-4d19-b597-7f445367c5c0'
irs = ImportRefineSource()
irs.import_refine_to_project(refine_project, project_uuid)
"""


@cache_control(no_cache=True)
@never_cache
def import_finalize(request, source_id):
    """ Finalizes an import """
    if not request.user.is_superuser:
        return HttpResponse('Unauthorized', status=401)
    else:
        if request.method == 'POST':
            fi = FinalizeImport(source_id)
            if fi.project_uuid is not False:
                if 'reset_state' in request.POST:
                    fi.reset_state()
                    fi = FinalizeImport(source_id)
                output = fi.process_current_batch()
                json_output = json.dumps(output,
                                         indent=4,
                                         ensure_ascii=False)
                return HttpResponse(json_output,
                                    content_type='application/json; charset=utf8')
            else:
                raise Http404
        else:
            return HttpResponseForbidden

"""
-------------------------------------------------------------
BELOW HERE ARE VIEWS NAVIGATING PROJECTS FOR THE USER
TO CHOOSE TO ADD ADDITIONAL DATA FROM REFINE
-------------------------------------------------------------
"""


@ensure_csrf_cookie
@cache_control(no_cache=True)
@never_cache
def index(request):
    """ Index for sources is going to be a list of projects """
    if not request.user.is_superuser:
        return HttpResponse('Unauthorized', status=401)
    else:
        rp = RootPath()
        base_url = rp.get_baseurl()
        ipr = ImportProjects()
        projs = ipr.get_all_projects()
        imnav = ImportNavigation()
        proj = {}
        proj['nav'] = imnav.set_nav('index')
        template = loader.get_template('imports/projects.html')
        context = {
            'projs': projs,
            'proj': proj,
            'base_url': base_url,
            'user': request.user
        }
        return HttpResponse(template.render(context, request))


@ensure_csrf_cookie
@cache_control(no_cache=True)
@never_cache
def project(request, project_uuid):
    """ Show HTML form for importing sources to a project """
    if not request.user.is_superuser:
        return HttpResponse('Unauthorized', status=401)
    else:
        rp = RootPath()
        base_url = rp.get_baseurl()
        ipr = ImportProjects()
        proj = ipr.get_project(project_uuid)
        if proj is not False:
            imnav = ImportNavigation()
            proj['nav'] = imnav.set_nav('project',
                                        project_uuid,
                                        False)
            template = loader.get_template('imports/project.html')
            context = {
                'proj': proj,
                'base_url': base_url,
                'user': request.user
            }
            return HttpResponse(template.render(context, request))
        else:
            raise Http404

"""
-------------------------------------------------------------
BELOW HERE ARE VIEWS FOR THE IMPORT SCHEMA MAPPING / DESCRIPTION
INTERFACES.
-------------------------------------------------------------
"""


@ensure_csrf_cookie
@cache_control(no_cache=True)
@never_cache
def field_types(request, source_id):
    """ Show HTML form listing fields classified by field type """
    if not request.user.is_superuser:
        return HttpResponse('Unauthorized', status=401)
    else:
        rp = RootPath()
        base_url = rp.get_baseurl()
        ip = ImportProfile(source_id)
        if ip.project_uuid is not False:
            ip.get_fields()
            imnav = ImportNavigation()
            ip.nav = imnav.set_nav('field-types',
                                   ip.project_uuid,
                                   source_id)
            template = loader.get_template('imports/field-types.html')
            context = {
                'ip': ip,
                'base_url': base_url,
                'user': request.user
            }
            return HttpResponse(template.render(context, request))
        else:
            raise Http404


@ensure_csrf_cookie
@cache_control(no_cache=True)
@never_cache
def field_types_more(request, source_id):
    """ Show HTML form further classifying subject fields """
    if not request.user.is_superuser:
        return HttpResponse('Unauthorized', status=401)
    else:
        rp = RootPath()
        base_url = rp.get_baseurl()
        ip = ImportProfile(source_id)
        if ip.project_uuid is not False:
            ip.get_subject_type_fields()
            imnav = ImportNavigation()
            ip.nav = imnav.set_nav('field-types-more',
                                   ip.project_uuid,
                                   source_id)
            if len(ip.fields) > 0:
                template = loader.get_template('imports/field-types-more.html')
                context = {
                    'ip': ip,
                    'base_url': base_url,
                    'user': request.user
                }
                return HttpResponse(template.render(context, request))
            else:
                redirect = '../../imports/field-types/' + source_id
                return HttpResponseRedirect(redirect)
        else:
            raise Http404


@ensure_csrf_cookie
@cache_control(no_cache=True)
@never_cache
def field_entity_relations(request, source_id):
    """ Show HTML form to change relationships for entities
        to be created / or updated from an import table
    """
    if not request.user.is_superuser:
        return HttpResponse('Unauthorized', status=401)
    else:
        rp = RootPath()
        base_url = rp.get_baseurl()
        ip = ImportProfile(source_id)
        if ip.project_uuid is not False:
            ip.get_fields()
            if len(ip.fields) > 0:
                ip.get_field_annotations()
                ip.jsonify_field_annotations()
                imnav = ImportNavigation()
                ip.nav = imnav.set_nav('field-entity-relations',
                                       ip.project_uuid,
                                       source_id)
                template = loader.get_template('imports/field-entity-relations.html')
                context = {
                    'ip': ip,
                    'base_url': base_url,
                    'user': request.user
                }
                return HttpResponse(template.render(context, request))
            else:
                redirect = '../../imports/field-types/' + source_id
                return HttpResponseRedirect(redirect)
        else:
            raise Http404


@ensure_csrf_cookie
@cache_control(no_cache=True)
@never_cache
def field_complex_descriptions(request, source_id):
    """ Show HTML form to change group descriptive
        properties together into groups of
        complex descriptions
    """
    if not request.user.is_superuser:
        return HttpResponse('Unauthorized', status=401)
    else:
        rp = RootPath()
        base_url = rp.get_baseurl()
        ip = ImportProfile(source_id)
        if ip.project_uuid is not False:
            ip.get_fields()
            if len(ip.fields) > 0:
                ip.get_field_annotations()
                ip.jsonify_field_annotations()
                imnav = ImportNavigation()
                ip.nav = imnav.set_nav('field-entity-relations',
                                       ip.project_uuid,
                                       source_id)
                template = loader.get_template('imports/field-entity-relations.html')
                context = {
                    'ip': ip,
                    'base_url': base_url,
                    'user': request.user
                }
                return HttpResponse(template.render(context, request))
            else:
                redirect = '../../imports/field-types/' + source_id
                return HttpResponseRedirect(redirect)
        else:
            raise Http404


@ensure_csrf_cookie
@cache_control(no_cache=True)
@never_cache
def field_descriptions(request, source_id):
    """ Show HTML form to change relationships for entities
        to be created / or updated from an import table
    """
    if not request.user.is_superuser:
        return HttpResponse('Unauthorized', status=401)
    else:
        rp = RootPath()
        base_url = rp.get_baseurl()
        ip = ImportProfile(source_id)
        if ip.project_uuid is not False:
            ip.get_fields()
            imnav = ImportNavigation()
            ip.nav = imnav.set_nav('field-descriptions',
                                   ip.project_uuid,
                                   source_id)
            template = loader.get_template('imports/field-descriptions.html')
            context = {
                'ip': ip,
                'base_url': base_url,
                'user': request.user
            }
            return HttpResponse(template.render(context, request))
        else:
            raise Http404


@ensure_csrf_cookie
@cache_control(no_cache=True)
@never_cache
def finalize(request, source_id):
    """ Show HTML form to change relationships for entities
        to be created / or updated from an import table
    """
    if not request.user.is_superuser:
        return HttpResponse('Unauthorized', status=401)
    else:
        rp = RootPath()
        base_url = rp.get_baseurl()
        ip = ImportProfile(source_id)
        if ip.project_uuid is not False:
            ip.get_fields()
            imnav = ImportNavigation()
            ip.nav = imnav.set_nav('finalize',
                                   ip.project_uuid,
                                   source_id)
            template = loader.get_template('imports/finalize.html')
            context = {
                'ip': ip,
                'base_url': base_url,
                'user': request.user
            }
            return HttpResponse(template.render(context, request))
        else:
            raise Http404
