import json
from urllib.parse import urlparse, parse_qs
from django.utils.http import urlquote, quote_plus, urlquote_plus
from django.conf import settings
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.apps.entities.entity.models import Entity
from opencontext_py.apps.indexer.solrdocument import SolrDocument
from django.utils.encoding import iri_to_uri


class FilterLinks():

    SOLR_FIELD_PARAM_MAPPINGS = \
        {'___project_id': 'proj',
         '___context_id': 'path',
         '___pred_': 'prop'}

    def __init__(self, request_dict=False):
        self.base_search_link = '/sets/'
        self.base_request = request_dict
        self.base_request_json = False
        self.base_r_full_path = False
        self.spatial_context = False
        self.testing = True

    def make_request_urls(self, new_rparams):
        """ makes request urls from the new request object """
        output = {}
        output['html'] = self.make_request_url(new_rparams)
        output['json'] = self.make_request_url(new_rparams, '.json')
        output['atom'] = self.make_request_url(new_rparams, '.atom')
        return output

    def make_request_url(self,
                         new_rparams,
                         doc_format=''):
        """ makes request urls from the new request object
            default doc_format is '' (HTML)
        """
        url = settings.CANONICAL_HOST + self.base_search_link
        if self.testing:
            url = 'http://127.0.0.1:8000' + self.base_search_link
        if 'path' in new_rparams:
            if new_rparams['path'] is not None \
               and new_rparams['path'] is not False:
                # context_path = iri_to_uri(new_rparams['path'])
                context_path = new_rparams['path']
                context_path = context_path.replace(' ', '+')
                url += context_path
        url += doc_format
        param_sep = '?'
        for param, param_vals in new_rparams.items():
            if param != 'path':
                for val in param_vals:
                    url += param_sep + param + '=' + quote_plus(val)
                    param_sep = '&'
        return url

    def add_to_request_by_solr_field(self,
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
        #print('New param: ' + param + ' new val: ' + new_value + ' len:' + str(self.base_request))
        new_rparams = self.add_to_request(param,
                                          new_value,
                                          add_to_value)
        return new_rparams

    def add_to_request(self,
                       param,
                       new_value,
                       add_to_value=None):
        """ adds to the new request object a parameter and value """
        if self.base_request_json is not False:
            # start of with JSON encoded base request parameters
            new_rparams = json.loads(self.base_request_json)
        elif self.base_r_full_path is not False:
            # start of with parsing a URL string
            new_rparams = self.make_base_params_from_url(self.base_r_full_path)
        elif self.base_request is not False:
            # start with a dictionary object of the base request
            # for some reason this often leads to memory errors
            new_rparams = self.base_request
        else:
            new_rparams = {}
        if param == 'path':
            entity = Entity()
            entity.get_context = True
            found = entity.dereference(new_value)
            if found:
                # convert the (slug) value into a context path
                new_value = entity.context
        if param not in new_rparams:
            if param == 'path':
                new_rparams[param] = new_value
            else:
                new_rparams[param] = [new_value]
        else:
            if param == 'path':
                new_rparams['path'] = new_value
            else:
                if add_to_value is not None:
                    new_list = []
                    old_found = False
                    for old_val in new_rparams[param]:
                        # print('Old val:' + old_val + ' add to:' + add_to_value)
                        if old_val == add_to_value:
                            old_found = True
                            new_list_val = old_val + ' ' + new_value
                        else:
                            new_list_val = old_val
                        new_list.append(new_list_val)
                    new_rparams[param] = new_list
                    if old_found is False:
                        new_rparams[param].append(new_value)
                else:
                    new_rparams[param].append(new_value)
        return new_rparams

    def make_base_params_from_url(self, request_url):
        """ makes the base parameters from the url """
        rparams = {}
        url_o = urlparse(request_url)
        rparams = parse_qs(url_o.query)
        if self.spatial_context is False:
            self.spatial_context = self.get_context_from_path(url_o.path)
        rparams['path'] = self.spatial_context
        return rparams

    def get_context_from_path(self, path):
        """ geths the spatial context from a request path """
        context = False
        if '.' in path:
            pathex = path.split('.')
            path = pathex[0]
        if '/' in path:
            pathex = path.split('/')
            print(str(pathex))
            if len(pathex) > 2:
                # remove the part that's the first slash
                pathex.pop(0)
                # remove the part that's for the url of search
                pathex.pop(0)
            context = '/'.join(pathex)
        return context

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
