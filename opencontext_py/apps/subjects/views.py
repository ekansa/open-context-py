from django.http import HttpResponse
from opencontext_py.apps.subjects.models import Subject
import json


# A subject is a generic item that is the subbject of observations
# A subject is the main type of record in open context for analytic data
# The main dependency for this app is for OCitems, which are used to generate
# Every type of item in Open Context, including subjects
def index(request):
    return HttpResponse("Hello, world. You're at the subjects index.")


def htmlView(request, uuid):
    try:
        actItem = Subject.objects.get(uuid=uuid)
        return HttpResponse("Hello, world. You're at the subjects htmlView of " + str(uuid))
    except Subject.DoesNotExist:
        raise Http404


def jsonView(request, uuid):
    try:
        actItem = Subject.objects.get(uuid=uuid)
        actItem.getItem()
        jsonOutput = json.dumps(actItem.ocitem.jsonLD, indent=4, sort_keys=True)
        return HttpResponse(jsonOutput, mimetype='application/json')
    except Subject.DoesNotExist:
        raise Http404
