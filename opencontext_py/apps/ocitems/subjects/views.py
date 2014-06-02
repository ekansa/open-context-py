from django.http import HttpResponse, Http404
from opencontext_py.apps.ocitems.subjects.models import Subject
import json


# A subject is a generic item that is the subbject of observations
# A subject is the main type of record in open context for analytic data
# The main dependency for this app is for OCitems, which are used to generate
# Every type of item in Open Context, including subjects
def index(request):
    return HttpResponse("Hello, world. You're at the subjects index.")


def html_view(request, uuid):
    try:
        #actItem = Subject.objects.get(uuid=uuid)
        return HttpResponse("Hello, world. You're at the subjects htmlView of "
                            + str(uuid))
    except Subject.DoesNotExist:
        raise Http404


def json_view(request, uuid):
    try:
        act_item = Subject.objects.get(uuid=uuid)
        act_item.get_item()
        json_output = json.dumps(act_item.ocitem.json_ld,
                                 indent=4,
                                 ensure_ascii=False)
        return HttpResponse(json_output,
                            content_type='application/json; charset=utf8')
    except Subject.DoesNotExist:
        raise Http404
