import json
from django.http import HttpResponse, Http404
from django.template import RequestContext, loader
from opencontext_py.apps.ocitems.ocitem.models import OCitem
from opencontext_py.apps.ocitems.ocitem.templating import TemplateItem
