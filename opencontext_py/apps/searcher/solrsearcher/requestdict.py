import json
from django.conf import settings
from opencontext_py.libs.rootpath import RootPath
from opencontext_py.libs.general import LastUpdatedOrderedDict


class RequestDict():

    def __init__(self):
        self.security_ok = True  # False if a security threat detected in the request

    def make_request_dict_json(self, request, spatial_context):
        """ makes a JSON object of the request object
            to help deal with memory problems
        """
        request_dict = self.make_request_obj_dict(request, spatial_context)
        json_string = json.dumps(request_dict,
                                 ensure_ascii=False, indent=4)
        return json_string

    def make_request_obj_dict(self, request, spatial_context):
        """ makes the Django request object into a dictionary obj """
        new_request = LastUpdatedOrderedDict()
        if spatial_context is not None:
            new_request['path'] = spatial_context
        else:
            new_request['path'] = False
        if request is not False:
            for key, key_val in request.GET.items():  # "for key in request.GET" works too.
                if key != 'callback':
                    # so JSON-P callbacks not in the request
                    self.security_check(request, key)  # check for SQL injections
                    new_request[key] = request.GET.getlist(key)
                    new_request = self.dinaa_period_kludge(key, new_request)
                if self.security_ok is False:
                    break
        return new_request

    def dinaa_period_kludge(self, key, new_request):
        """ makes sure we dive a bit into the period hiearchy for
            requests to a DINAA period
        """
        if key == 'prop':
            new_prop_list = []
            for prop_list_item in new_request[key]:
                if 'dinaa-00001' in prop_list_item \
                   and 'dinaa-00001---dinaa-00002' not in prop_list_item:
                    prop_list_item = prop_list_item.replace('dinaa-00001', 'dinaa-00001---dinaa-00002')
                new_prop_list.append(prop_list_item)
            new_request[key] = new_prop_list
        return new_request

    def security_check(self, request, key):
        """ simple check for SQL injection attack,
            these are evil doers at work, no need
            even to pass this on to solr
        """
        evil_list = ['union select ',
                     'char(',
                     'delete from',
                     'truncate table',
                     'drop table',
                     '&#',
                     '/*']
        for param_val in request.GET.getlist(key):
            val = param_val.lower()
            for evil in evil_list:
                if evil in val:
                    self.security_ok = False
        return self.security_ok
