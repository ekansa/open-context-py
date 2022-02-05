from django.http import HttpResponse
from opencontext_py.libs.general import LastUpdatedOrderedDict


def index(request, spatial_context=None):
    return HttpResponse("Hello, world. You're at the archive index.")
