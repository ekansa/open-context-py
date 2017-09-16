from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.apps.ocitems.octypes.models import OCtype
from opencontext_py.apps.ldata.arachne.api import ArachneAPI
from opencontext_py.apps.entities.uri.models import URImanagement
from opencontext_py.apps.entities.entity.models import Entity


class TypeSupplement():
    """ Class for adding related, supplemental information about types
    """
    RELATES_PREDICATES = [
        'rdfs:seeAlso',
        'skos:example',
        'skos:note'
    ]

    def __init__(self, item_json):
        self.item_json = item_json

    def type_german_mappings(self, keyword):
        """ translates to related german for searches """
        keyword = keyword.lower()
        mappings = {'bucchero': 'etruskischer bucchero'}
        if keyword in mappings:
            keyword = mappings[keyword]
        return keyword

    def get_arachne_comparanda(self):
        """ get a type item including lots of useful related data
        """
        label = self.item_json['label']
        # keyword = self.type_german_mappings(label)
        arachne_search_url = self.check_arachne_relation()
        if isinstance(arachne_search_url, str):
            # print('search url: ' + arachne_search_url)
            a_api = ArachneAPI()
            a_api.get_results_from_search_url(arachne_search_url)
            if a_api.results is not False:
                editorial_pred = LastUpdatedOrderedDict()
                editorial_pred['owl:sameAs'] = 'http://www.w3.org/2004/02/skos/core#editorialNote'
                editorial_pred['slug'] = 'skos-editorialnote'
                editorial_pred['label'] = 'Arachne comparative material'
                editorial_pred['oc-gen:predType'] = 'variable'
                editorial_pred['type'] = 'xsd:string'
                example_pred = LastUpdatedOrderedDict()
                example_pred['owl:sameAs'] = 'http://www.w3.org/2004/02/skos/core#example'
                example_pred['slug'] = 'skos-example'
                example_pred['label'] = 'Comparanda in Arachne'
                example_pred['oc-gen:predType'] = 'link'
                example_pred['type'] = '@id'
                self.item_json['@context'][2]['skos:editorialNote'] = editorial_pred
                self.item_json['@context'][2]['skos:example'] = example_pred
                self.add_arachne_observation(a_api)
        return self.item_json

    def add_arachne_observation(self, a_api):
        """ Adds an observation for Arachne comparanda """
        if 'oc-gen:has-obs' not in self.item_json:
            self.item_json['oc-gen:has-obs'] = []
        arachne_obs = LastUpdatedOrderedDict()
        arachne_obs['id'] = '#obs-' + str(len(self.item_json['oc-gen:has-obs']) + 1)
        arachne_obs['oc-gen:sourceID'] = a_api.DEFAULT_API_BASE_URL
        arachne_obs['oc-gen:obsStatus'] = 'active'
        arachne_obs['type'] = 'oc-gen:observations'
        editorial = LastUpdatedOrderedDict()
        editorial['id'] = '#string-arachne-editorial'
        note = ''
        note += '<p>Arachne has: <strong>' + str(a_api.result_count) + '</strong> related item(s) with images</p>'
        note += '<p>Browse these comparanda: '
        note += '[<a href="' + a_api.arachne_html_url + '" target="_blank">Link to Arachne search results</a>]</p>'
        note += '<p><small>Open Context editors identified materials in Arachne likley to be relevant for comparison to this type.'
        note += ' <a href="http://arachne.uni-koeln.de/" target="_blank">Arachne</a> is the central object database of the German Archaeological Institute (DAI)'
        note += ' and the Archaeological Institute of the University of Cologne.</small></p>'
        editorial['xsd:string'] = note
        arachne_obs['skos:editorialNote'] = []
        arachne_obs['skos:editorialNote'].append(editorial)
        arachne_obs['skos:example'] = a_api.results
        self.item_json['oc-gen:has-obs'].append(arachne_obs)
    
    def check_arachne_relation(self):
        """ checks to see if the type is related to an arachne search """
        arachne_search_url = None
        for rel_pred in self.RELATES_PREDICATES:
            if rel_pred in self.item_json:
                if isinstance(self.item_json[rel_pred], list):
                    for item in self.item_json[rel_pred]:
                        if 'id' in item:
                            if ArachneAPI.ARACHNE_SEARCH in item['id']:
                                # we have a link to something in arachne search
                                arachne_search_url = item['id']
                                break
        return arachne_search_url
