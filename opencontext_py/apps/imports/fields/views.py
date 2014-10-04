import json
from django.http import HttpResponse, Http404
from opencontext_py.apps.imports.fields.templating import ImportProfile
from django.template import RequestContext, loader


# A subject is a generic item that is the subbject of observations
# A subject is the main type of record in open context for analytic data
# The main dependency for this app is for OCitems, which are used to generate
# Every type of item in Open Context, including subjects
def index(request):
    return HttpResponse("Hello, world. You're at the imports fields index.")


def field_types(request, source_id):
    ip = ImportProfile(source_id)
    if ip.project_uuid is not False:
        ip.get_fields()
        template = loader.get_template('imports/fieldtypes.html')
        context = RequestContext(request,
                                 {'ip': ip})
        return HttpResponse(template.render(context))
    else:
        raise Http404


def field_classify(request):
    ip = ImportProfile()
    if ip.project_uuid is not False:
        ip.get_fields()
        context = RequestContext(request,
                                 {'ip': ip})
        return HttpResponse(template.render(context))
    else:
        raise Http404
