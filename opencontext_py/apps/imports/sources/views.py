import json
from django.http import HttpResponse, Http404, HttpResponseRedirect
from opencontext_py.apps.imports.sources.projects import ImportProjects
from opencontext_py.apps.imports.sources.models import ImportSource
from django.template import RequestContext, loader
from django.views.decorators.csrf import ensure_csrf_cookie


# These views display an HTML form for classifying import fields,
# and handles AJAX requests / responses to change classifications
@ensure_csrf_cookie
def index(request):
    """ Index for sources is going to be a list of projects """
    ipr = ImportProjects()
    projs = ipr.get_all_projects()
    template = loader.get_template('imports/projects.html')
    context = RequestContext(request,
                             {'projs': projs})
    return HttpResponse(template.render(context))


def create_project(request):
    """ Create a new project """
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
        """
            proj = ipr.get_project(project_uuid)
            template = loader.get_template('imports/project.html')
            context = RequestContext(request,
                                     {'proj': proj})
            return HttpResponse(template.render(context))
        """
        return HttpResponseRedirect('../../imports/project/' + project_uuid)
    else:
        return HttpResponseForbidden


def edit_project(request, project_uuid):
    """ Create a new project """
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
            """
            proj = ipr.get_project(project_uuid)
            template = loader.get_template('imports/project.html')
            context = RequestContext(request,
                                     {'proj': proj})
            return HttpResponse(template.render(context))
            """
            return HttpResponseRedirect('../../imports/project/' + project_uuid)
        else:
            raise Http404
    else:
        return HttpResponseForbidden


@ensure_csrf_cookie
def project(request, project_uuid):
    """ Show HTML form further classifying subject fields """
    ipr = ImportProjects()
    proj = ipr.get_project(project_uuid)
    if proj is not False:
        template = loader.get_template('imports/project.html')
        context = RequestContext(request,
                                 {'proj': proj})
        return HttpResponse(template.render(context))
    else:
        raise Http404
