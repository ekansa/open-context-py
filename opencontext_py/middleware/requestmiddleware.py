import time
from django.conf import settings
from opencontext_py.apps.entities.httpmetrics.request import RequestHttpMetric


class RequestMiddleware(object):

    """ Methods to record HTTP requests and some information
        about clients making those requests

    """
    
    def __init__(self, get_response=None):
        self.start_time = None
        self.get_response = get_response
        self.content_type = 'text/html'
        self.uuid = False
        self.project_uuid = False
        self.item_type = False
        # One-time configuration and initialization.
    
    def process_request(self, request):
        self.start_time = time.time()
        request.start_time = self.start_time
        request.uuid = self.uuid
        request.project_uuid = self.project_uuid
        request.item_type = self.item_type
        request.content_type = 'text/html'  # default, unless changed elsewhere
    
    def process_response(self, request, response):
        r_metric = RequestHttpMetric(request)
        if hasattr(request, 'start_time'):
            r_metric.time_start = request.start_time
        else:
            r_metric.time_start = self.start_time
        if hasattr(request, 'content_type'):
            r_metric.mime_type = request.content_type
        else:
            r_metric.mime_type = self.content_type
        if hasattr(request, 'uuid'):
            r_metric.uuid = request.uuid
        if hasattr(request, 'project_uuid'):
            r_metric.project_uuid = request.project_uuid
        if hasattr(request, 'item_type'):
            r_metric.item_type = request.item_type
        r_metric.record()
        return response

    
    
    
 