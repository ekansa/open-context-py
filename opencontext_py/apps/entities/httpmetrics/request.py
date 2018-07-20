import time
import json
import hashlib
from django.conf import settings
from django.core.cache import caches
from django.contrib.gis.geoip2 import GeoIP2
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.apps.entities.httpmetrics.models import HttpMetric


class RequestHttpMetric():

    """ Methods to record HTTP requests and some information
        about clients making those requests

    """

    def __init__(self, request=None, request_dict_json=None):
        self.time_start = time.time()
        self.request = request
        self.uuid = False
        self.project_uuid = False
        self.item_type = False
        self.mime_type = 'text/html'  # default mime-type
        if isinstance(request_dict_json, str):
            self.request_dict = json.loads(request_dict_json)
        elif isinstance(request_dict_json, dict):
            self.request_dict = request_dict_json
        elif request is not None and request_dict_json is None:
            self.request_dict = self.make_request_obj_dict(request)
        else:
            self.request_dict = None
        self.latitude = 0
        self.longitude = 0
    
    def record(self):
        """ records the request to track general, non
            privacy defeating information about
            clients
        """
        output = None
        if self.request is not None:
            if self.request.user_agent.is_bot is False:
                # only capture this data for non bots
                if 'HTTP_REFERER' in self.request.META:
                    referer = self.request.META['HTTP_REFERER']
                else:
                    referer = 'None'
                if self.request.user_agent.is_mobile:
                    type = 'mobile'
                elif self.request.user_agent.is_tablet:
                    type = 'tablet'
                elif self.request.user_agent.is_pc:
                    type = 'pc'
                else:
                    type = 'other'
                self.get_geo_ip(self.request)
                httpm = HttpMetric()
                httpm.referer = referer
                httpm.path = self.request.get_full_path()
                httpm.mime_type = self.mime_type
                httpm.uuid = self.uuid
                httpm.project_uuid = self.project_uuid
                httpm.item_type = self.item_type
                httpm.params_json = self.request_dict
                httpm.latitude = round(self.latitude, 1)
                httpm.longitude = round(self.longitude, 1)
                httpm.type = type
                httpm.browser = self.request.user_agent.browser.family
                httpm.os = self.request.user_agent.os.family
                httpm.device = self.request.user_agent.device.family
                httpm.duration = time.time() - self.time_start  # length of time for request
                httpm.save()
                output = True
        return output
        
    def get_geo_ip(self, request):
        """ gets geospatial information about an IP address """
        geo_ip_obj = None
        ip = self.get_client_ip(request)
        if ip is not None:
            key = self.make_cache_key('request-ip', ip)
            geo_ip_obj = self.get_cache_object(key)
            if geo_ip_obj is None:
                # could not get the geo_ip_obj from the memory cache
                # so look it up from the GeoIP database
                geo_ip_obj = self.lookup_geo_up(ip)
                self.save_cache_object(key, geo_ip_obj)
            if isinstance(geo_ip_obj, dict):
                if 'latitude' in geo_ip_obj and \
                   'longitude' in geo_ip_obj:
                    self.latitude = geo_ip_obj['latitude']
                    self.longitude = geo_ip_obj['longitude'] 
        return geo_ip_obj

    def lookup_geo_up(self, ip):
        """looks up the geographic coordinates of an IP address """
        if isinstance(settings.GEOIP_PATH, str):
            try:
                g = GeoIP2()
                geo_ip_obj = g.city(ip)
            except:
                geo_ip_obj = None
        else:
            geo_ip_obj = None
        return geo_ip_obj

    def get_client_ip(self, request):
        """ get's the client IP address note! This never gets
            stored!!
        """
        try:
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                ip = x_forwarded_for.split(',')[0]
            else:
                ip = request.META.get('REMOTE_ADDR')
        except:
            ip = None
        return ip
    
    def make_request_obj_dict(self, request):
        """ makes a dictionary object from a request, so
            we can save parameters that may be passed
        """
        request_dict = LastUpdatedOrderedDict()
        if request is not None:
            for key, key_val in request.GET.items():
                request_dict[key] = request.GET.getlist(key)    
        return request_dict
    
    def make_cache_key(self, prefix, identifier):
        """ makes a valid OK cache key """
        hash_obj = hashlib.sha1()
        concat_string = str(prefix) + " " + str(identifier)
        hash_obj.update(concat_string.encode('utf-8'))
        return hash_obj.hexdigest()

    def get_cache_object(self, key):
        """ gets a cached reddis object """
        try:
            cache = caches['redis']
            obj = cache.get(key)
        except:
            obj = None
        return obj

    def save_cache_object(self, key, obj):
        """ saves a cached reddis object """
        try:
            cache = caches['redis']
            cache.set(key, obj)
            ok = True
        except:
            self.redis_ok = False
            ok = False
        return ok
