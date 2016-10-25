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
        request.time_start = time.time()
        request.content_type = 'text/html'  # default, unless changed elsewhere
        return request
    
    def process_response(self, request, response):
        r_metric = RequestHttpMetric(request)
        r_metric.time_start = request.time_start
        r_metric.mime_type = request.content_type
        r_metric.record()
        return response

    
    
    
 