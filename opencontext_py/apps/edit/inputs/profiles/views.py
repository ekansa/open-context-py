import json
from django.http import HttpResponse, Http404
from opencontext_py.libs.rootpath import RootPath
from django.template import RequestContext, loader
from django.views.decorators.csrf import ensure_csrf_cookie
from opencontext_py.apps.edit.items.itembasic import ItemBasicEdit
from opencontext_py.apps.edit.inputs.projectinputs import ProjectInputs
from opencontext_py.apps.edit.inputs.profiles.models import InputProfile
from opencontext_py.apps.edit.inputs.profiles.manage import ManageInputProfile
from opencontext_py.apps.edit.inputs.profiles.templating import InputProfileTemplating
from opencontext_py.apps.edit.inputs.fieldgroups.models import InputFieldGroup


@ensure_csrf_cookie
def index(request):
    """nothing to do"""
    pass
