import json
from django.http import HttpResponse, Http404
from opencontext_py.apps.ocitems.ocitem.models import OCitem
from opencontext_py.apps.ocitems.ocitem.templating import TemplateItem
from opencontext_py.apps.edit.items.model import ItemEdit
from django.template import RequestContext, loader
from django.views.decorators.csrf import ensure_csrf_cookie


# These views handle requests for interacting with the version history
def index(request):
    return HttpResponse("Hello, world. You're at the versioning index.")

