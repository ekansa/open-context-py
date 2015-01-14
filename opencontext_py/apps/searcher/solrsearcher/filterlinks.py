from django.utils.http import urlquote
from django.conf import settings
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.apps.entities.entity.models import Entity
from opencontext_py.apps.indexer.solrdocument import SolrDocument


class FilterLinks():

    SOLR_FIELD_PARAM_MAPPINGS = \
        {'___project_id': 'proj',
         '___context_id': 'path',
         '___pred_': 'prop'}

    def __init__(self):
        self.base_search_link = '/sets/'
        self.base_request = False
        self.testing = True

    def make_request_urls(self, new_request):
        """ makes request urls from the new request object """
        output = {}
        output['html'] = self.make_request_url(new_request)
        output['json'] = self.make_request_url(new_request, '.json')
        output['atom'] = self.make_request_url(new_request, '.atom')
        return output

    def make_request_url(self, new_request, doc_format=''):
        """ makes request urls from the new request object
            default doc_format is '' (HTML)
        """
        url = settings.CANONICAL_HOST + self.base_search_link
        if self.testing:
            url = 'http://127.0.0.1:8000' + self.base_search_link
        if 'path' in new_request:
            if new_request['path'] is not None \
               and new_request['path'] is not False:
                url += urlquote(new_request['path'])
        new_request.pop('path', None)
        url += doc_format
        param_sep = '?'
        for param, param_vals in new_request.items():
            for val in param_vals:
                url += param_sep + param + '=' + urlquote(val)
                param_sep = '&'
        return url

    def add_to_new_request_by_solr_field(self,
                                         new_request,
                                         solr_facet_key,
                                         new_value):
        """ uses the solr_facet_key to determine the
           request parameter
        """
        param = self.get_param_from_solr_facet_key(solr_facet_key)
        slugs = self.parse_slugs_in_solr_facet_key(solr_facet_key)
        if slugs is not False:
            add_to_value = ' '.join(slugs)
            # print('Add-to-value' + add_to_value)
        else:
            add_to_value = None
        new_request = self.add_to_new_request(new_request,
                                              param,
                                              new_value,
                                              add_to_value)
        return new_request

    def add_to_new_request(self,
                           new_request,
                           param,
                           new_value,
                           add_to_value=None):
        """ adds to the new request object a parameter and value """
        if param not in new_request:
            if param == 'path':
                new_request[param] = new_value
            else:
                new_request[param] = [new_value]
        else:
            if param == 'path':
                if add_to_value is not None:
                    new_request['path'] += '/'.new_value
                else:
                    new_request['path'] = new_value
            else:
                if add_to_value is not None:
                    new_list = []
                    old_found = False
                    for old_val in new_request[param]:
                        # print('Old val:' + old_val + ' add to:' + add_to_value)
                        if old_val == add_to_value:
                            old_found = True
                            new_list_val = old_val + ' ' + new_value
                        else:
                            new_list_val = old_val
                        new_list.append(new_list_val)
                    new_request[param] = new_list
                    if old_found is False:
                        new_request[param].append(new_value)
                else:
                    new_request[param].append(new_value)
        return new_request

    def get_param_from_solr_facet_key(self, solr_facet_key):
        """" returns the public parameter from the solr_facet_key """
        output = solr_facet_key
        for solr_field_part_key, param in self.SOLR_FIELD_PARAM_MAPPINGS.items():
            if solr_field_part_key in solr_facet_key:
                output = param
                break
        return output

    def parse_slugs_in_solr_facet_key(self, solr_facet_key):
        """ returns a list of slugs encoded in a solr_facet_key
            the solr field has these slugs in reverse order
        """
        no_slug_field_list = [SolrDocument.ROOT_CONTEXT_SOLR,
                              SolrDocument.ROOT_PROJECT_SOLR,
                              SolrDocument.ROOT_LINK_DATA_SOLR,
                              SolrDocument.ROOT_PREDICATE_SOLR]
        if solr_facet_key in no_slug_field_list:
            slugs = False
        else:
            raw_slugs = []
            facet_key_list = solr_facet_key.split('___')
            list_len = len(facet_key_list)
            i = 0
            for list_item in facet_key_list:
                i += 1
                if i < list_len:
                    # last item is the suffix for the field type
                    # also replace '_' with '-' to get a slug
                    raw_slugs.append(list_item.replace('_', '-'))
            slugs = raw_slugs[::-1]
        return slugs

    def prep_base_request_obj(self, request_dict):
        """ prepares a base request object from the old request object
            to use to create new requests
        """
        self.base_request = request_dict
        return self.base_request

    def get_request_param(self, param, default, as_list=False):
        """ get a string or list to use in queries from either
            the request object or the internal_request object
            so we have flexibility in doing searches without
            having to go through HTTP
        """
        output = False
        if self.request is not False:
            if as_list:
                output = self.request.GET.getlist(param)
            else:
                output = self.request.GET.get(param, default=default)
        elif self.internal_request is not False:
            if as_list:
                if param in self.internal_request:
                    param_obj = self.internal_request[param]
                    if isinstance(param_obj, list):
                        output = param_obj
                    else:
                        output = [param_obj]
            else:
                if param in self.internal_request:
                    output = self.internal_request[param]
                else:
                    output = default
        else:
            output = False
        return output 
