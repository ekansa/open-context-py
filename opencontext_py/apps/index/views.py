from django.http import HttpResponse, Http404
from django.conf import settings
from django.template import RequestContext, loader


# These views provide forms for editing items
def index(request):
    """ Displays the HTML for the project homepage """
    template = loader.get_template('index/view.html')
    context = RequestContext(request,
                             {'nav_items': settings.NAV_ITEMS})
    return HttpResponse(template.render(context))

