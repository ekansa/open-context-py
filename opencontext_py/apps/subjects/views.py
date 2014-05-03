from django.http import HttpResponse
from opencontext_py.apps.subjects.models import Subject

def index(request):
    return HttpResponse("Hello, world. You're at the subjects index.")

def htmlView(request, uuid):
    return HttpResponse("Hello, world. You're at the subjects htmlView of " + str(uuid))

def jsonView(request, uuid):
    try:
        actItem = Subject.objects.get(uuid=uuid)
        return HttpResponse("Hello, world. You're at the subjects jsonView of " + str(uuid))
    except Subject.DoesNotExist:
        raise Http404