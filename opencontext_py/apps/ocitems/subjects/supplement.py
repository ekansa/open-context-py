from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.apps.ocitems.ocitem.models import OCitem
from opencontext_py.apps.ldata.catallivingarchive.api import CatalLivingArchiveAPI


class SubjectSupplement():
    """ Class for adding related, supplemental information about types
    """

    def __init__(self, item_json):
        self.item_json = item_json

    def get_catal_related(self):
        """ Check to see if this item has related data
            in the Çatalhöyük Living Archive
        """
        label = self.item_json['label']
        category_list = []
        project_list = []
        if 'category' in self.item_json:
            category_list = self.item_json['category']
        if 'dc-terms:isPartOf' in self.item_json:
            project_list = self.item_json['dc-terms:isPartOf']
        catal_api = CatalLivingArchiveAPI()
        catal_api.check_relevance(category_list,
                                  project_list)
        if catal_api.relevant:
            catal_api.get_unit(label)
            if catal_api.has_data:
                editorial_pred = LastUpdatedOrderedDict()
                editorial_pred['owl:sameAs'] = 'http://www.w3.org/2004/02/skos/core#editorialNote'
                editorial_pred['slug'] = 'skos-editorialnote'
                editorial_pred['label'] = 'About Çatalhöyük Living Archive Data'
                editorial_pred['oc-gen:predType'] = 'variable'
                editorial_pred['type'] = 'xsd:string'
                props_pred = LastUpdatedOrderedDict()
                props_pred['owl:sameAs'] = 'http://www.w3.org/2004/02/skos/core#definition'
                props_pred['slug'] = 'skos-definition'
                props_pred['label'] = 'Çatalhöyük Living Archive: Unit Properties'
                props_pred['oc-gen:predType'] = 'variable'
                props_pred['type'] = 'xsd:string'
                finds_pred = LastUpdatedOrderedDict()
                finds_pred['owl:sameAs'] = 'http://www.w3.org/2004/02/skos/core#note'
                finds_pred['slug'] = 'skos-note'
                finds_pred['label'] = 'Çatalhöyük Living Archive: Unit Finds'
                finds_pred['oc-gen:predType'] = 'variable'
                finds_pred['type'] = 'xsd:string'
                self.item_json['@context'][2]['skos:editorialNote'] = editorial_pred
                if catal_api.props_count > 0:
                    self.item_json['@context'][2]['skos:definition'] = props_pred
                if catal_api.finds_count > 0:
                    self.item_json['@context'][2]['skos:note'] = finds_pred
                self.add_catal_observation(catal_api)
        return self.item_json

    def add_catal_observation(self, catal_api):
        """ Adds an observation for Catal API data """
        if 'oc-gen:has-obs' not in self.item_json:
            self.item_json['oc-gen:has-obs'] = []
        catal_obs = LastUpdatedOrderedDict()
        catal_obs['id'] = '#obs-' + str(len(self.item_json['oc-gen:has-obs']) + 1)
        catal_obs['oc-gen:sourceID'] = catal_api.BASE_HTML_URL
        catal_obs['oc-gen:obsStatus'] = 'active'
        catal_obs[OCitem.PREDICATES_OCGEN_OBSLABEL] = 'Çatalhöyük Living Archive Data'
        catal_obs['type'] = 'oc-gen:observations'
        if catal_api.props_count > 0:
            catal_obs['skos:definition'] = catal_api.properties
        if catal_api.finds_count > 0:
            catal_obs['skos:note'] = catal_api.finds
        editorial = LastUpdatedOrderedDict()
        editorial['id'] = '#string-catal-editorial'
        note = ''
        note += '<p>The Çatalhöyük Living Archive describes this unit with: </>'
        note += '<ul>'
        if catal_api.props_count > 0:
            note += '<li><strong>' + str(catal_api.props_count) + '</strong> descriptive properties</li>'
        if catal_api.finds_count > 0:
            note += '<li><strong>' + str(catal_api.finds_count) + '</strong> finds (other than animal bones)</li>'
        note += '</ul>'
        note += '<p><small>Open Context requested these current ("live") data through an external API. '
        note += 'The <a href="http://catalhoyuk.stanford.edu//" target="_blank">Çatalhöyük Living Archive</a> '
        note += 'has powerful analysis and visualization tools for use with the comprehensive '
        note += 'database documenting recent excavations at Çatalhöyük. '
        note += 'Stanford University sponsored and hosts this project.</small></p>'
        editorial['xsd:string'] = note
        catal_obs['skos:editorialNote'] = []
        catal_obs['skos:editorialNote'].append(editorial)
        self.item_json['oc-gen:has-obs'].append(catal_obs)
