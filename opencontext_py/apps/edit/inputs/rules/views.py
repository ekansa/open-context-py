from django.http import HttpResponse
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.libs.requestnegotiation import RequestNegotiation
from opencontext_py.apps.contexts.models import ItemContext
from opencontext_py.apps.contexts.models import SearchContext


def index(request, spatial_context=None):
    return HttpResponse("Hello, world. You're at the sets index.")
