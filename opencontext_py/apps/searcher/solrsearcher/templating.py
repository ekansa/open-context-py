import datetime
from django.utils.html import strip_tags
from urllib.parse import urlparse, parse_qs, urlunparse
from django.http import QueryDict
from django.conf import settings
from opencontext_py.libs.rootpath import RootPath
from opencontext_py.apps.entities.uri.models import URImanagement
from opencontext_py.apps.searcher.solrsearcher.querymaker import QueryMaker
from opencontext_py.apps.searcher.solrsearcher.filterlinks import FilterLinks


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
        self.paging = {}
        self.num_facets = []
        self.date_facets = []
        self.facets = []
        self.geo_records = []
        self.text_search = []
        self.active_sort = {}
        self.sort_options = []
        self.nav_items = settings.NAV_ITEMS

    def process_json_ld(self):
        """ processes JSON-LD to make a view """
        if self.ok:
            self.set_sorting()  # sorting in the templating
            self.set_paging()  # adds to the paging dict
            self.set_text_search()  # adds text search fields
            if 'totalResults' in self.json_ld:
                self.total_count = self.json_ld['totalResults']
            if 'itemsPerPage' in self.json_ld:
                self.items_per_page = self.json_ld['itemsPerPage']
            if 'startIndex' in self.json_ld:
                self.start_num = self.json_ld['startIndex'] + 1
                self.end_num = self.json_ld['startIndex'] + self.items_per_page
                if self.end_num > self.total_count:
                    self.end_num = self.total_count
            if 'oc-api:active-filters' in self.json_ld:
                for json_filter in self.json_ld['oc-api:active-filters']:
                    s_filter = SearchFilter()
                    s_filter.parse_json_filter(json_filter)
                    self.filters.append(s_filter)
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
                            geor = ResultRecord()
                            geor.parse_json_record(feature)
                            self.geo_records.append(geor)
            if 'oc-api:has-results' in self.json_ld:
                for json_rec in self.json_ld['oc-api:has-results']:
                    rr = ResultRecord()
                    rr.parse_json_record(json_rec)
                    self.geo_records.append(rr)

    def set_sorting(self):
        """ set links for sorting records """
        if 'oc-api:active-sorting' in self.json_ld:
            act_sorts = self.json_ld['oc-api:active-sorting']
            if len(act_sorts) > 0:
                self.active_sort['label'] = act_sorts[0]['label']
                self.active_sort['order'] = act_sorts[0]['oc-api:sort-order']
        if 'oc-api:has-sorting' in self.json_ld:
            for sort_opt in self.json_ld['oc-api:has-sorting']:
                # do this so we can use the template without a prefix
                sort_opt['order'] = sort_opt['oc-api:sort-order']
                self.sort_options.append(sort_opt)

    def replace_query_param(self, url, attr, val):
        """ replace a query parameter in a url """
        (scheme, netloc, path, params, query, fragment) = urlparse(url)
        query_dict = QueryDict(query).copy()
        query_dict[attr] = val
        if val is False:
            query_dict.pop(attr)
        query = query_dict.urlencode()
        return urlunparse((scheme, netloc, path, params, query, fragment))

    def set_paging(self):
        """ sets the paging for these results """
        pages = ['first',
                 'previous',
                 'next',
                 'last']
        for page in pages:
            if page in self.json_ld:
                self.paging[page] = self.json_ld[page]
            else:
                self.paging[page] = False

    def set_text_search(self):
        """ sets the text search URL """
        if 'oc-api:has-text-search' in self.json_ld:
            for t_opt in self.json_ld['oc-api:has-text-search']:
                ts = TextSearch()
                ts.parse_json_record(t_opt)
                if ts.id is not False:
                    self.text_search.append(ts)

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


class SearchFilter():
    """ Object for an active search filter """

    def __init__(self):
        self.filter_label = False
        self.filter_value = False
        self.remove_href = False

    def parse_json_filter(self, json_filter):
        """ parses a json filter record
            to populate object attributes
        """
        if 'oc-api:filter' in json_filter:
            self.filter_label = json_filter['oc-api:filter']
        if 'label' in json_filter:
            self.filter_value = json_filter['label']
        if 'oc-api:remove' in json_filter:
            self.remove_href = json_filter['oc-api:remove']


class TextSearch():
    """ Object for text search fields """
    def __init__(self):
        self.id = False
        self.label = False
        self.href = False
        self.term = False
        self.temp = '{SearchTerm}'

    def parse_json_record(self, json_rec):
        """ parses a json record to make a text
            search object
        """
        if isinstance(json_rec, dict):
            if 'id' in json_rec:
                self.id = json_rec['id'].replace('#', '')
            if 'label' in json_rec:
                self.label = json_rec['label']
            if 'oc-api:search-term' in json_rec:
                if json_rec['oc-api:search-term'] is not None:
                    self.term = json_rec['oc-api:search-term']
            if 'oc-api:template' in json_rec:
                self.href = json_rec['oc-api:template']


class ResultRecord():
    """ Object for a result record
    """
    def __init__(self):
        self.uuid = False
        self.id = False
        self.label = False
        self.item_type = False
        self.context = False
        self.project = False
        self.href = False
        self.category = False
        self.early_bce_ce = False
        self.early_suffix = ''
        self.late_bce_ce = False
        self.late_suffix = ''
        self.published = False
        self.updated = False
        self.snippet = False
        self.thumbnail = False
        self.icon_thumbnail = False
        self.extra = False
        self.dc = False

    def parse_json_record(self, json_rec):
        """ parses json for a
            geo-json feature of the record
        """
        if 'properties' in json_rec:
            props = json_rec['properties']
        else:
            props = json_rec
        if isinstance(props, dict):
            if 'id' in props:
                self.id = props['id'].replace('#', '')
            if 'label' in props:
                self.label = props['label']
            if 'href' in props:
                self.href = props['href']
            if 'uri' in props:
                item_type_output = URImanagement.get_uuid_from_oc_uri(props['uri'], True)
                if isinstance(item_type_output, dict):
                    self.item_type = item_type_output['item_type']
                    self.uuid = item_type_output['uuid']
            if 'project label' in props:
                self.project = props['project label']
            if 'context label' in props:
                self.context = props['context label']
            if 'early bce/ce' in props:
                self.early_bce_ce = props['early bce/ce']
                if self.early_bce_ce < 0:
                    self.early_bce_ce = int(round(self.early_bce_ce * -1, 0))
                    self.early_suffix = 'BCE'
                else:
                    self.early_bce_ce = int(round(self.early_bce_ce, 0))
                    self.early_suffix = False
            if 'late bce/ce' in props:
                self.late_bce_ce = props['late bce/ce']
                if self.late_bce_ce < 0:
                    self.late_bce_ce = int(round(self.late_bce_ce * -1, 0))
                    self.late_suffix = 'BCE'
                else:
                    self.late_bce_ce = int(round(self.late_bce_ce, 0))
                    self.late_suffix = False
            if 'item category' in props:
                self.category = props['item category']
            if 'snippet' in props:
                self.snippet = props['snippet']
                self.snippet = self.snippet.replace('<em>', '[[[[mark]]]]')
                self.snippet = self.snippet.replace('</em>', '[[[[/mark]]]]')
                self.snippet = strip_tags(self.snippet)
                self.snippet = self.snippet.replace('</', '')
                self.snippet = self.snippet.replace('<', '')
                self.snippet = self.snippet.replace('>', '')
                self.snippet = self.snippet.replace('[[[[mark]]]]', '<mark>')
                self.snippet = self.snippet.replace('[[[[/mark]]]]', '</mark>')
            if 'thumbnail' in props:
                self.thumbnail = props['thumbnail']
                if '/icons/' in self.thumbnail or '-noun-' in self.thumbnail:
                    self.icon_thumbnail = True
            if 'published' in props:
                self.published = QueryMaker().make_human_readable_date(props['published'])
            if 'updated' in props:
                self.updated = QueryMaker().make_human_readable_date(props['updated'])


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
        elif 'oc-api:has-rel-media-options' in json_facet:
            for json_option in json_facet['oc-api:has-rel-media-options']:
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
