from django.conf import settings


class SolrResponseTypes():
    """ methods to customize
        the types of results returned
        from solr searches
    """
    DEFAULT_RESPONSES = ['context',
                         'metadata',
                         'chrono-facet',
                         'facet',
                         'geo-facet',
                         'geo-record',
                         'nongeo-record']

    ALL_RESPONSES = ['context',
                     'metadata',
                     'facet',
                     'chrono-facet',
                     'geo-facet',
                     'geo-feature',
                     'geo-project',
                     'geo-record',
                     'uuid',
                     'uri',
                     'uri-meta',
                     'solr']

    def __init__(self, request_dict={}):
        self.responses = self.DEFAULT_RESPONSES
        self.request_dict = request_dict
        self.set_responses()

    def set_responses(self):
        """ makes geojson-ld point records from a solr response """
        #first do lots of checks to make sure the solr-json is OK
        if isinstance(self.request_dict, dict):
            if 'response' in self.request_dict:
                if isinstance(self.request_dict['response'], list):
                    resp = self.request_dict['response'][0]
                elif isinstance(self.request_dict['response'], str):
                    resp = self.request_dict['response']
                if ',' in resp:
                    resps = resp.split(',')
                else:
                    resps = [resp]
                use_resps = []
                for check_r in resps:
                    if check_r in self.ALL_RESPONSES:
                        # this is a legitimate response type
                        # we can use it
                        use_resps.append(check_r)
                if len(use_resps) == 0:
                    # no legitimate response types
                    # found, so use the defaults
                    use_resps = self.DEFAULT_RESPONSES
                else:
                    self.responses = use_resps
