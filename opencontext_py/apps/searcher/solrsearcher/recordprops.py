import json
from django.conf import settings
from opencontext_py.libs.rootpath import RootPath
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.apps.entities.entity.models import Entity
from opencontext_py.apps.entities.uri.models import URImanagement
from opencontext_py.apps.indexer.solrdocument import SolrDocument
from opencontext_py.apps.ocitems.assertions.models import Assertion
from opencontext_py.apps.ocitems.mediafiles.models import Mediafile
from opencontext_py.apps.searcher.solrsearcher.querymaker import QueryMaker


class RecordProperties():
    """ Methods to make properties for individual record items
        useful for making geospatial feature records or
        lists of items without geospatial data
    """

    def __init__(self, response_dict_json=False):
        self.uuid = False
        self.uri = False  # cannonical uri for the item
        self.href = False  # link to the item in the current deployment
        self.cite_uri = False  # stable / persistent uri
        self.label = False
        self.item_type = False
        self.project_href = False  # link to the project in current deployment
        self.project_uri = False  # cannonical uri for the project
        self.project_label = False 
        self.context_href = False  # link to parent context in current deployment
        self.context_uri = False  # link to parent context cannonical uri
        self.context_label = False
        self.category = False
        self.latitute = False
        self.longitude = False
        self.geojson = False
        self.early_date = False
        self.late_date = False
        self.thumbnail_href = False
        self.thumbnail_uri = False
        self.thumbnail_scr = False
        self.snippet = False
        self.cite_uri = False  # stable identifier as an HTTP uri
        self.base_url = settings.CANONICAL_HOST
        rp = RootPath()
        self.base_url = rp.get_baseurl()
        self.entities = {}
        if response_dict_json is not False:
            self.response_dict = json.loads(response_dict_json)
        else:
            self.response_dict = False
        self.highlighting = False
        self.recursive_count = 0
        self.min_date = False
        self.max_date = False

    def parse_solr_record(self, solr_rec):
        """ Parses a solr rec object """
        if isinstance(solr_rec, dict):
            self.get_item_basics(solr_rec)
            self.get_citation_uri(solr_rec)
            self.get_lat_lon(solr_rec)
            self.get_category(solr_rec)
            self.get_project(solr_rec)
            self.get_context(solr_rec)
            self.get_time(solr_rec)  # get time information, limiting date ranges to query constaints
            self.get_thumbnail(solr_rec)
            self.get_snippet(solr_rec)  # get snippet of highlighted text

    def get_item_basics(self, solr_rec):
        """ get basic metadata for an item """
        output = False
        if isinstance(solr_rec, dict):
            if 'uuid' in solr_rec:
                self.uuid = solr_rec['uuid']
            if 'slug_type_uri_label' in solr_rec:
                id_parts = self.parse_solr_value_parts(solr_rec['slug_type_uri_label'])
                if id_parts is not False:
                    output = True
                    self.uri = self.make_url_from_val_string(id_parts['uri'], True)
                    self.href = self.make_url_from_val_string(id_parts['uri'], False)
                    item_type_output = URImanagement.get_uuid_from_oc_uri(self.uri, True)
                    self.item_type = item_type_output['item_type']
                    self.label = id_parts['label']
        return output

    def get_snippet(self, solr_rec):
        """ get a text highlighting snippet """
        if isinstance(self.highlighting, dict):
            if self.uuid is False:
                if 'uuid' in solr_rec:
                    self.uuid = solr_rec['uuid']
            if self.uuid in self.highlighting:
                if 'text' in self.highlighting[self.uuid]:
                    text_list = self.highlighting[self.uuid]['text']
                    self.snippet = ' '.join(text_list)

    def get_citation_uri(self, solr_rec):
        """ gets the best citation / persistent uri for the item """
        if 'persistent_uri' in solr_rec:
            for p_uri in solr_rec['persistent_uri']:
                self.cite_uri = p_uri
                if 'dx.doi.org' in p_uri:
                    break # stop looking once we have a DOI, the best

    def get_lat_lon(self, solr_rec):
        """ gets latitute and longitude information """
        if 'discovery_geolocation' in solr_rec:
            geo_strings = solr_rec['discovery_geolocation']
            geo_coords_str = geo_strings[0].split(' ')
            self.latitude = float(geo_coords_str[1])
            self.longitude = float(geo_coords_str[0])  # geojson ording

    def get_category(self, solr_rec):
        """ Gets the most specific category for the item """
        self.recursive_count = 0
        cat_hierarchy = self.get_category_hierarchy(solr_rec)
        if len(cat_hierarchy) > 0:
            self.category = cat_hierarchy[-1]['label']

    def get_context(self, solr_rec):
        """ Get the most specific context parent for the record """
        self.recursive_count = 0
        contexts = self.extract_hierarchy(solr_rec,
                                          SolrDocument.ROOT_CONTEXT_SOLR,
                                          '___context',
                                          [])
        if len(contexts) > 0:
            self.context_label = self.make_context_path_label(contexts)
            self.context_uri = self. make_context_link(contexts, True)
            self.context_href = self. make_context_link(contexts, False)

    def get_project(self, solr_rec):
        """ Get the most specific project for the record """
        self.recursive_count = 0
        projects = self.extract_hierarchy(solr_rec,
                                          SolrDocument.ROOT_PROJECT_SOLR,
                                          '___project',
                                          [])
        if len(projects) > 0:
            self.project_label = projects[-1]['label']
            self.project_uri = self.make_url_from_val_string(projects[-1]['uri'],
                                                             True)
            self.project_href = self.make_url_from_val_string(projects[-1]['uri'],
                                                              False)

    def get_time(self, solr_rec):
        """ parses time information """
        early_list = False
        late_list = False
        if 'form_use_life_chrono_earliest' in solr_rec:
            early_list = solr_rec['form_use_life_chrono_earliest']
        if 'form_use_life_chrono_latest' in solr_rec:
            late_list = solr_rec['form_use_life_chrono_latest']
        if isinstance(early_list, list):
            date_list = early_list
        else:
            date_list = []
        if isinstance(late_list, list):
            date_list += late_list
        if len(date_list) > 0:
            min_max = self.get_list_min_max(date_list)
            self.early_date = min(min_max)
            self.late_date = max(min_max)

    def get_list_min_max(self, date_list):
        """ Returns the minimum and maximum dates
            from a date list, constrained by
            preset min and max dates
        """
        min_date = False
        max_date = False
        # print(str(date_list))
        if isinstance(date_list, list):
            date_list.sort()
            for date in date_list:
                if self.min_date is not False:
                    if date >= self.min_date \
                       and min_date is False:
                        min_date = date
                if self.max_date is not False:
                    if date <= self.max_date:
                        max_date = date
        if min_date is False:
            min_date = self.min_date
        if max_date is False:
            max_date = self.max_date
        return [min_date, max_date]

    def get_thumbnail(self, solr_rec):
        """ get media record and thumbnail, if it exists """
        if 'uuid' in solr_rec:
            uuid = solr_rec['uuid']
            media_item = Assertion.objects\
                                  .filter(uuid=uuid,
                                          object_type='media')[:1]
            if len(media_item) > 0:
                muuid = media_item[0].object_uuid
                thumb = Mediafile.objects\
                                 .filter(uuid=muuid,
                                         file_type='oc-gen:thumbnail')[:1]
                if len(thumb) > 0:
                    self.thumbnail_href = self.base_url + '/media/' + muuid
                    self.thumbnail_uri = settings.CANONICAL_HOST + '/media/' + muuid
                    self.thumbnail_scr = thumb[0].file_uri

    def get_category_hierarchy(self, solr_rec):
        """ gets the most specific category
            informtation about
            an item
        """
        cat_hierarchy = []
        if 'item_type' in solr_rec:
            item_type = solr_rec['item_type'][0]
            root_cat_field = 'oc_gen_' + item_type + '___pred_id'
            cat_hierarchy = self.extract_hierarchy(solr_rec,
                                                   root_cat_field,
                                                   '___pred',
                                                   [])
        return cat_hierarchy

    def extract_hierarchy(self,
                          solr_rec,
                          facet_field_key,
                          facet_suffix,
                          hierarchy=[],
                          pred_field=False):
        """ extracts a hierarchy from a solr_record.
            The output is a list starting with the most
            general parent of the hiearchy,
            then going to the most specific

            This is a recursive function and
            default / starts with the root
            of the hiearchy as the facet_field_key
        """
        alt_facet_field_key = facet_field_key
        if pred_field is not False:
            # do this to allow search of hiarchy in a named
            # predicate field
            f_parts = facet_field_key.split('___')
            if len(f_parts) == 2:
                alt_f_parts = [f_parts[0],
                               pred_field.replace('-', '_'),
                               f_parts[1]]
                alt_facet_field_key = '___'.join(alt_f_parts)
                print('Check: ' + facet_field_key + ', ' + alt_facet_field_key)
        if (facet_field_key in solr_rec or alt_facet_field_key in solr_rec)\
           and self.recursive_count < 20:
            self.recursive_count += 1
            if facet_field_key in solr_rec:
                path_item_val = solr_rec[facet_field_key][0]
            else:
                path_item_val = solr_rec[alt_facet_field_key][0]
            parsed_path_item = self.parse_solr_value_parts(path_item_val)
            if isinstance(parsed_path_item, dict):
                hierarchy.append(parsed_path_item)
                new_facet_field = parsed_path_item['slug'].replace('-', '_')
                new_facet_field += facet_suffix + '_' + parsed_path_item['data_type']
                # print('New hierarchy field: ' + new_facet_field)
                hierarchy = self.extract_hierarchy(solr_rec,
                                                   new_facet_field,
                                                   facet_suffix,
                                                   hierarchy)
        return hierarchy

    def make_context_path_label(self, contexts):
        """ Makes a '/' delimited context
            path for easy human readability
        """
        context_path = False
        if len(contexts) > 0:
            context_labels = []
            for context in contexts:
                context_labels.append(context['label'])
            context_path = '/'.join(context_labels)
        return context_path

    def make_context_link(self, contexts, cannonical=False):
        """ makes a URI for a context """
        context_uri = False
        if len(contexts) > 0:
            context_uri = self.make_url_from_val_string(contexts[-1]['uri'],
                                                        cannonical)
        return context_uri

    def make_url_from_val_string(self,
                                 partial_url,
                                 use_cannonical=True):
        """ parses a solr value if it has
            '___' delimiters, to get the URI part
            string.
            if it's already a URI part, it makes
            a URL
        """
        if use_cannonical:
            base_url = settings.CANONICAL_HOST
        else:
            base_url = self.base_url
        solr_parts = self.parse_solr_value_parts(partial_url)
        if isinstance(solr_parts, dict):
            partial_url = solr_parts['uri']
        if 'http://' not in partial_url \
           and 'https://' not in partial_url:
            url = base_url + partial_url
        else:
            url = partial_url
        return url

    def add_record_fields(self):
        """ adds fields to include in the GeoJSON properties """
        if 'rec-field' in self.response_dict:
            raw_rec_fields = self.response_dict['rec-field'][0]
            if ',' in raw_rec_fields:
                self.record_fields = raw_rec_fields.split(',')
            else:
                self.record_fields = [raw_rec_fields]
        else:
            self.record_fields = []
        return self.record_fields

    def parse_solr_value_parts(self, solr_value):
        """ parses a solr_value string into
            slug, solr-data-type, uri, and label
            parts
        """
        output = False
        if '___' in solr_value:
            solr_ex = solr_value.split('___')
            if len(solr_ex) == 4:
                output = {}
                output['slug'] = solr_ex[0]
                output['data_type'] = solr_ex[1]
                output['uri'] = solr_ex[2]
                output['label'] = solr_ex[3]
        return output

    def get_key_val(self, key, dict_obj):
        """ returns the value associated
            with a key, if the key exists
            else, none
        """
        output = None
        if isinstance(dict_obj, dict):
            if key in dict_obj:
                output = dict_obj[key]
        return output

    def get_entity(self, identifier, is_path=False):
        """ looks up an entity """
        output = False
        identifier = http.urlunquote_plus(identifier)
        if identifier in self.entities:
            # best case scenario, the entity is already looked up
            output = self.entities[identifier]
        else:
            found = False
            entity = Entity()
            if is_path:
                found = entity.context_dereference(identifier)
            else:
                found = entity.dereference(identifier)
                if found is False:
                    # case of linked data slugs
                    found = entity.dereference(identifier, identifier)
            if found:
                self.entities[identifier] = entity
                output = entity
        return output

