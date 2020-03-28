import datetime
from django.utils.html import strip_tags
from django.http import QueryDict
from django.conf import settings
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.libs.rootpath import RootPath
from opencontext_py.libs.globalmaptiles import GlobalMercator
from opencontext_py.apps.entities.uri.models import URImanagement
from opencontext_py.apps.searcher.solrsearcher.querymaker import QueryMaker
from opencontext_py.apps.searcher.solrsearcher.filterlinks import FilterLinks


class FacetSearchTemplate():
    """ methods to transform raw JSON-LD faceted
        search facets and add some organization
        to make it easier to navigate
    """
    SUB_HEADING_DEFAULT = 'Other Attributes'
    SUB_HEADINGS = [
        'N. American Site (DINAA)',
        'Standard Biological',
        'Standard Cultural (CIDOC-CRM)',
        'Cross-References',
        'Library of Congress (LoC)',
        'Getty Art and Architecture Thesaurus',
        'British Museum Terms',
        'Geonames (Gazetteer)',
        'Pleiades (Ancient Places Gazetteer)',
        'Levantine Ceramics Wares',
        'Wikipedia Topics',
        '(Deprecated) Biological',
        SUB_HEADING_DEFAULT,
    ]
    SUB_HEADING_URI_MAPS = {
        'http://purl.obolibrary.org/obo/FOODON_00001303': 'Standard Biological',
        'http://purl.org/NET/biol/ns#term_hasTaxonomy': '(Deprecated) Biological',
        'http://purl.org/dc/terms/references': 'Cross-References',
        'http://purl.org/dc/terms/isReferencedBy': 'Cross-References',
    }
    SUB_HEADING_URI_PREFIX_MAPS = {
        'opencontext.org/vocabularies/dinaa/': 'N. American Site (DINAA)',
        'opencontext.org/vocabularies/open-context-zooarch/': 'Standard Biological',
        'erlangen-crm.org/': 'Standard Cultural (CIDOC-CRM)',
        'id.loc.gov/authorities/subjects/': 'Library of Congress (LoC)',
        'wikipedia.org/': 'Wikipedia Topics',
        'geonames.org/': 'Geonames (Gazetteer)',
        'pleiades.stoa.org/': 'Pleiades (Ancient Places Gazetteer)',
        'collection.britishmuseum.org': 'British Museum Terms',
        'vocab.getty.edu/aat/': 'Getty Art and Architecture Thesaurus',
        'levantineceramics.org/wares/': 'Levantine Ceramics Wares' 
    }
    HIDE_URI_MAPS = [
        'http://purl.org/NET/biol/ns#term_hasTaxonomy',
        'http://www.w3.org/2004/02/skos/core#closeMatch',
        'http://purl.org/dc/terms/subject',
        'http://www.wikidata.org/wiki/Q247204',
        'http://www.w3.org/2004/02/skos/core#related',
        'http://purl.org/dc/terms/isPartOf',
        'http://purl.org/dc/terms/hasPart'
    ]
    HIDE_URI_PREFIX_MAPS = [
               
    ]

    def __init__(self, json_ld):
        self.total_count = 0
        self.num_facets = []
        self.date_facets = []
        self.facets = []
        # is the item_type_limit is in effect?
        self.item_type_limited = False

    def process_json_ld(self):
        """ processes JSON-LD to make a view """
        if 'oc-api:has-facets' in self.json_ld:
            dom_id_prefix = 'f-'
            i = 0
            first_facet_field = True
            for json_facet in self.json_ld['oc-api:has-facets']:
                i += 1
                ff = FacetField()
                ff.item_type_limited = self.item_type_limited
                ff.facet_field_index = i
                first_facet_field = False
                ff.dom_id_prefix = dom_id_prefix + str(i)
                ff.parse_json_facet(json_facet)
                if ff.id is not False:
                    self.facets.append(ff)

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
        # is the item_type_limit is in effect?
        self.item_type_limited = False
        self.fg_id_options = LastUpdatedOrderedDict()
        self.fg_num_options = LastUpdatedOrderedDict()
        self.fg_date_options = LastUpdatedOrderedDict()
        self.fg_string_options = LastUpdatedOrderedDict()
        self.group_labels = []
        self.id_options = []
        self.numeric_options = []
        self.date_options = []
        self.string_options = []
        self.option_types = []
        self.show_group_labels = False
        # now add groups as keys, with list values
        # for each type of faceted search option
        for group_label in FacetSearchTemplate.SUB_HEADINGS:
            if group_label not in self.fg_id_options:
                self.fg_id_options[group_label] = []
            if group_label not in self.fg_num_options:
                self.fg_num_options[group_label] = []
            if group_label not in self.fg_date_options:
                self.fg_date_options[group_label] = []
            if group_label not in self.fg_string_options:
                self.fg_string_options[group_label] = []

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
                fo.item_type_limited = self.item_type_limited
                fo.dom_id_prefix = self.dom_id_prefix + '-' + str(i)
                fo.parse_json_option(json_option)
                if fo.id is not False and fo.show:
                    self.id_options.append(fo)
                    if fo.group_label in self.fg_id_options:
                        # only add if we can match keys OK
                        self.fg_id_options[fo.group_label].append(fo)
                        if fo.group_label not in self.group_labels:
                            self.group_labels.append(fo.group_label)
                    else:
                        self.fg_id_options[FacetSearchTemplate.SUB_HEADING_DEFAULT]\
                            .append(fo)
        elif 'oc-api:has-rel-media-options' in json_facet:
            for json_option in json_facet['oc-api:has-rel-media-options']:
                i += 1
                fo = FacetOption()
                fo.item_type_limited = self.item_type_limited
                fo.dom_id_prefix = self.dom_id_prefix + '-' + str(i)
                fo.parse_json_option(json_option)
                if fo.id is not False and fo.show:
                    self.id_options.append(fo)
                    self.fg_id_options[fo.group_label].append(fo)
                    if fo.group_label not in self.group_labels:
                        self.group_labels.append(fo.group_label)
        if 'oc-api:has-numeric-options' in json_facet:
            for json_option in json_facet['oc-api:has-numeric-options']:
                i += 1
                fo = FacetOption()
                fo.item_type_limited = self.item_type_limited
                fo.dom_id_prefix = self.dom_id_prefix + '-' + str(i)
                fo.parse_json_option(json_option)
                if fo.id is not False and fo.show:
                    self.numeric_options.append(fo)
                    self.fg_num_options[fo.group_label].append(fo)
                    if fo.group_label not in self.group_labels:
                        self.group_labels.append(fo.group_label)
        if 'oc-api:has-date-options' in json_facet:
            for json_option in json_facet['oc-api:has-date-options']:
                i += 1
                fo = FacetOption()
                fo.item_type_limited = self.item_type_limited
                fo.dom_id_prefix = self.dom_id_prefix + '-' + str(i)
                fo.parse_json_option(json_option)
                if fo.id is not False and fo.show:
                    self.date_options.append(fo)
                    self.fg_date_options[fo.group_label].append(fo)
                    if fo.group_label not in self.group_labels:
                        self.group_labels.append(fo.group_label)
        if 'oc-api:has-string-options' in json_facet:
            for json_option in json_facet['oc-api:has-string-options']:
                i += 1
                fo = FacetOption()
                fo.item_type_limited = self.item_type_limited
                fo.dom_id_prefix = self.dom_id_prefix + '-' + str(i)
                fo.parse_json_option(json_option)
                if fo.id is not False and fo.show:
                    self.string_options.append(fo)
                    self.fg_string_options[fo.group_label].append(fo)
                    if fo.group_label not in self.group_labels:
                        self.group_labels.append(fo.group_label)
        if len(self.id_options) > 0:
            self.option_types.append('id')
        if len(self.numeric_options) > 0:
            self.option_types.append('numeric')
        if len(self.date_options) > 0:
            self.option_types.append('date')
        if len(self.string_options) > 0:
            self.option_types.append('string')
        if len(self.group_labels) > 1:
            self.show_group_labels = True

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
        self.group_label = FacetSearchTemplate.SUB_HEADING_DEFAULT
        self.show = True
        # is the item_type_limit is in effect?
        self.item_type_limited = False

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
                # assign this to a subheading
                self.set_sub_heading(json_option['rdfs:isDefinedBy'])
                rp = RootPath()
                self.defined_by = rp.convert_local_url(json_option['rdfs:isDefinedBy'])
        self.dom_id = self.dom_id_prefix + '---' + str(self.slug)
        # check to see if we should show this, based in if this is a related property
        # and if self.item_type_limited is False
        self.check_show_related_options()
    
    def set_sub_heading(self, defined_by_uri):
        """ checkes a 'rdfs:isDefinedBy' to assign the
            facet option into a group, if it is in a
            uri-> sub headding group mappings
        """
        # make a list of uri, so we can check the https or http
        # variants of the "defined_by_uri"
        def_list = [defined_by_uri]
        if defined_by_uri[0:8] == 'https://':
            alt_uri = 'http://' + defined_by_uri[8:]
            def_list.append(alt_uri)
        elif defined_by_uri[0:7] == 'http://':
            alt_uri = 'https://' + defined_by_uri[7:]
            def_list.append(alt_uri)
        for def_uri in def_list:
            if self.group_label == FacetSearchTemplate.SUB_HEADING_DEFAULT:
                for uri, sub_heading in FacetSearchTemplate.SUB_HEADING_URI_MAPS.items():
                    if uri == def_uri:
                        # exact match of the def_uri and the uri with a sub-heading
                        self.group_label = sub_heading
                        break
            if self.group_label == FacetSearchTemplate.SUB_HEADING_DEFAULT:
                for prefix, sub_heading in FacetSearchTemplate.SUB_HEADING_URI_PREFIX_MAPS.items():
                    if prefix in def_uri:
                        # in-exact match of the def_uri and the uri-prefix for with a sub-heading 
                        self.group_label = sub_heading
                        break
            if self.show:
                for uri in FacetSearchTemplate.HIDE_URI_MAPS:
                    if uri == def_uri:
                        # an exact match with URIs that need to be hidden
                        self.show = False
                for prefix in FacetSearchTemplate.HIDE_URI_PREFIX_MAPS:
                    if prefix in def_uri:
                        # a non-exact match with URIs that need to be hidden
                        self.show = False

    def check_show_related_options(self):
        """ checks if related options should be shown.
            It the self.item_type_limited is True, then
            we are filtering for item_type, so it is OK
            to show related options. Otherwise, it would
            be confusing to the user, so we should hide
            the facet optio
        """
        if self.item_type_limited is False and isinstance(self.slug, str):
            if 'rel--' == self.slug[0:5]:
                # this is a related property, so confusing
                # to show in the faceted search list if the user
                # hasn't first limited the search by item_type
                self.show = False
