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
        # One-time configuration and initialization.
    
    def process_request(self, request):
        self.start_time = time.time()
        request.content_type = 'text/html'  # default, unless changed elsewhere
    
    def process_response(self, request, response):
        r_metric = RequestHttpMetric(request)
        r_metric.time_start = self.start_time
        r_metric.mime_type = request.content_type
        r_metric.record()
        return response

    
    
    
 