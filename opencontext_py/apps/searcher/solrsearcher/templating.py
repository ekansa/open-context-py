from django.conf import settings
from opencontext_py.libs.rootpath import RootPath


class SearchTemplate():
    """ methods use Open Context JSON-LD
        search results and turn them into a
        user interface
    """

    def __init__(self, json_ld):
        if isinstance(json_ld, dict):
            self.json_ld = json_ld
            self.ok = True
        else:
            self.ok = False
        self.total_count = 0
        self.start_num = 0
        self.end_num = 0
        self.items_per_page = 0
        self.filters = []
        self.num_facets = []
        self.date_facets = []
        self.facets = []
        self.records = []
        self.nav_items = settings.NAV_ITEMS

    def process_json_ld(self):
        """ processes JSON-LD to make a view """
        if self.ok:
            if 'totalResults' in self.json_ld:
                self.total_count = self.json_ld['totalResults']
            if 'itemsPerPage' in self.json_ld:
                self.items_per_page = self.json_ld['itemsPerPage']
            if 'startIndex' in self.json_ld:
                self.start_num = self.json_ld['startIndex'] + 1
                self.end_num = self.json_ld['startIndex'] + self.items_per_page
                if self.end_num > self.total_count:
                    self.end_num = self.total_count
            if 'oc-api:has-facets' in self.json_ld:
                dom_id_prefix = 'f-'
                i = 0
                first_facet_field = True
                for json_facet in self.json_ld['oc-api:has-facets']:
                    i += 1
                    ff = FacetField()
                    ff.facet_field_index = i
                    first_facet_field = False
                    ff.dom_id_prefix = dom_id_prefix + str(i)
                    ff.parse_json_facet(json_facet)
                    if ff.id is not False:
                        self.facets.append(ff)
            if 'features' in self.json_ld:
                for feature in self.json_ld['features']:
                    if 'category' in feature:
                        if feature['category'] == 'oc-api:geo-record':
                            rr = ResultRecord()
                            rr.parse_json_record(feature)

    def get_path_in_dict(self, key_path_list, dict_obj, default=False):
        """ get part of a dictionary object by a list of keys """
        act_dict_obj = dict_obj
        for key in key_path_list:
            if isinstance(act_dict_obj, dict): 
                if key in act_dict_obj:
                    act_dict_obj = act_dict_obj[key]
                    output = act_dict_obj
                else:
                    output = default
                    break
            else:
                output = default
                break
        return output


class ResultRecord():
    """ Object for a result record
    """
    def __init__(self):
        self.dom_id_prefix = False
        self.id = False
        self.label = False
        self.item_type = False
        self.context = False
        self.project = False
        self.href = False
        self.category = False
        self.thumbnail = False

    def parse_json_record(self, json_rec):
        """ parses json for a
            geo-json feature of the record
        """
        pass


class FacetField():
    """ Object for
        facet fields of different sorts
    """
    def __init__(self):
        self.facet_field_index = 0
        self.dom_id_prefix = False
        self.id = False
        self.defined_by = False
        self.label = False
        self.type = False
        self.option_types = []
        self.id_options = []
        self.numeric_options = []
        self.date_options = []
        self.string_options = []

    def parse_json_facet(self, json_facet):
        """ parses the json data to set
            values to the attributes of this
            object
        """
        if 'id' in json_facet:
            self.id = json_facet['id']
            self.id = self.id.replace('#', '')
        if 'label' in json_facet:
            self.label = json_facet['label']
        if 'rdfs:isDefinedBy' in json_facet:
            if 'http://' in json_facet['rdfs:isDefinedBy'] \
               or 'https://' in json_facet['rdfs:isDefinedBy']:
                self.defined_by = json_facet['rdfs:isDefinedBy']
        if 'type' in json_facet:
            raw_type = json_facet['type']
            if '-context' in raw_type:
                self.type = 'Context'
            elif '-project' in raw_type:
                self.type = 'Project'
            elif '-item-type' in raw_type:
                self.type = 'Open Context Type'
            elif '-prop' in raw_type:
                self.type = 'Description'
            else:
                self.type = 'Description'
            if self.label == '':
                self.label = self.type
        i = 0
        if 'oc-api:has-id-options' in json_facet:
            for json_option in json_facet['oc-api:has-id-options']:
                i += 1
                fo = FacetOption()
                fo.dom_id_prefix = self.dom_id_prefix + '-' + str(i)
                fo.parse_json_option(json_option)
                if fo.id is not False:
                    self.id_options.append(fo)
        if 'oc-api:has-numeric-options' in json_facet:
            for json_option in json_facet['oc-api:has-numeric-options']:
                i += 1
                fo = FacetOption()
                fo.dom_id_prefix = self.dom_id_prefix + '-' + str(i)
                fo.parse_json_option(json_option)
                if fo.id is not False:
                    self.numeric_options.append(fo)
        if 'oc-api:has-date-options' in json_facet:
            for json_option in json_facet['oc-api:has-date-options']:
                i += 1
                fo = FacetOption()
                fo.dom_id_prefix = self.dom_id_prefix + '-' + str(i)
                fo.parse_json_option(json_option)
                if fo.id is not False:
                    self.date_options.append(fo)
        if 'oc-api:has-string-options' in json_facet:
            for json_option in json_facet['oc-api:has-string-options']:
                i += 1
                fo = FacetOption()
                fo.dom_id_prefix = self.dom_id_prefix + '-' + str(i)
                fo.parse_json_option(json_option)
                if fo.id is not False:
                    self.string_options.append(fo)
        if len(self.id_options) > 0:
            self.option_types.append('id')
        if len(self.numeric_options) > 0:
            self.option_types.append('numeric')
        if len(self.date_options) > 0:
            self.option_types.append('date')
        if len(self.string_options) > 0:
            self.option_types.append('string')


class FacetOption():
    """ Object for
        facet options
    """
    def __init__(self):
        self.dom_id_prefix = False
        self.dom_id = False
        self.id = False
        self.json = False
        self.defined_by = False
        self.label = False
        self.count = 0
        self.slug = False

    def parse_json_option(self, json_option):
        """ parses json option to populate
            this object
        """
        if 'id' in json_option:
            self.id = json_option['id']
        if 'json' in json_option:
            self.json = json_option['json']
        if 'label' in json_option:
            self.label = json_option['label']
        if 'count' in json_option:
            self.count = json_option['count']
        if 'slug' in json_option:
            self.slug = json_option['slug']
        if 'rdfs:isDefinedBy' in json_option:
            if 'http://' in json_option['rdfs:isDefinedBy'] \
               or 'https://' in json_option['rdfs:isDefinedBy']:
                rp = RootPath()
                self.defined_by = rp.convert_local_url(json_option['rdfs:isDefinedBy'])
        self.dom_id = self.dom_id_prefix + '---' + str(self.slug)
