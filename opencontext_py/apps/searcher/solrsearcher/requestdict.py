import json
from django.conf import settings
from opencontext_py.libs.rootpath import RootPath
from opencontext_py.libs.general import LastUpdatedOrderedDict


class RequestDict():

    def __init__(self):
        pass

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
                new_request[key] = request.GET.getlist(key)
        return new_request 
