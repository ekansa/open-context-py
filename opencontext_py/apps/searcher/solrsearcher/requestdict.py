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
                if self.security_ok is False:
                    break
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
