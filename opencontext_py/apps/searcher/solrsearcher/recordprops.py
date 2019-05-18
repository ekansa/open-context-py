import json
import lxml.html
from django.conf import settings
import django.utils.http as http
from django.utils.html import strip_tags
from opencontext_py.libs.rootpath import RootPath
from opencontext_py.libs.memorycache import MemoryCache
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.apps.entities.entity.models import Entity
from opencontext_py.apps.entities.uri.models import URImanagement
from opencontext_py.apps.indexer.solrdocument import SolrDocument
from opencontext_py.apps.ocitems.assertions.models import Assertion
from opencontext_py.apps.ocitems.mediafiles.models import Mediafile
from opencontext_py.apps.searcher.solrsearcher.caching import SearchGenerationCache
from opencontext_py.apps.searcher.solrsearcher.querymaker import QueryMaker
from opencontext_py.apps.ldata.linkannotations.recursion import LinkRecursion
from opencontext_py.apps.ldata.linkannotations.equivalence import LinkEquivalence


class RecordProperties():
    """ Methods to make properties for individual record items
        useful for making geospatial feature records or
        lists of items without geospatial data
    """
    ATTRIBUTE_DELIM = '; '  # delimiter for multiple attributes

    def __init__(self, request_dict_json=False):
        self.uuid = False
        self.uri = False  # cannonical uri for the item
        self.href = False  # link to the item in the current deployment
        self.cite_uri = False  # stable / persistent uri
        self.label = False
        self.item_type = False
        self.updated = False
        self.published = False
        self.project_href = False  # link to the project in current deployment
        self.project_uri = False  # cannonical uri for the project
        self.project_label = False 
        self.context_href = False  # link to parent context in current deployment
        self.context_uri = False  # link to parent context cannonical uri
        self.context_label = False
        self.category = False
        self.latitude = False
        self.longitude = False
        self.geojson = False
        self.early_date = False
        self.late_date = False
        self.human_remains_flagged = False  # flagged as relating to human remains
        self.thumbnail_href = False
        self.thumbnail_uri = False
        self.thumbnail_scr = False
        self.preview_scr = False
        self.fullfile_scr = False
        self.snippet = False
        self.cite_uri = False  # stable identifier as an HTTP uri
        self.other_attributes = False  # other attributes to the record
        # flatten list of an attribute values to single value
        self.flatten_rec_attributes = False
        # A list of (non-standard) attributes to include in a record
        self.rec_attributes = []
        self.attribute_hierarchies = {}
        self.base_url = settings.CANONICAL_HOST
        rp = RootPath()
        self.base_url = rp.get_baseurl()
        self.m_cache = MemoryCache()  # memory caching object
        self.s_cache = SearchGenerationCache() # supplemental caching object, specific for searching
        self.request_dict_json = request_dict_json
        if request_dict_json is not False:
            self.request_dict = json.loads(request_dict_json)
        else:
            self.request_dict = False
        self.highlighting = False
        self.recursive_count = 0
        self.min_date = False
        self.max_date = False
        self.thumbnail_data = {}
        self.media_file_data = {}
        self.string_attrib_data = {}

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
            self.get_media_files(solr_rec)
            self.get_snippet(solr_rec)  # get snippet of highlighted text
            self.get_attributes(solr_rec)  # get non-standard attributes
            self.get_string_attributes(solr_rec)  # get non-standard string attributes

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
            if 'updated' in solr_rec:
                self.updated = solr_rec['updated']
            if 'published' in solr_rec:
                self.published = solr_rec['published']
            if 'human_remains' in solr_rec:
                # is the record flagged as related to human remains ?human_remains
                if solr_rec['human_remains'] > 0:
                    self.human_remains_flagged = True
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
                    # some processing to remove fagments of HTML markup.
                    self.snippet = self.snippet.replace('<em>', '[[[[mark]]]]')
                    self.snippet = self.snippet.replace('</em>', '[[[[/mark]]]]')
                    try:
                        self.snippet = '<div>' + self.snippet + '</div>'
                        self.snippet = lxml.html.fromstring(self.snippet).text_content()
                        self.snippet = strip_tags(self.snippet)
                    except:
                        self.snippet = strip_tags(self.snippet)
                    self.snippet = self.snippet.replace('[[[[mark]]]]', '<em>')
                    self.snippet = self.snippet.replace('[[[[/mark]]]]', '</em>')

    def get_citation_uri(self, solr_rec):
        """ gets the best citation / persistent uri for the item """
        if 'persistent_uri' in solr_rec:
            for p_uri in solr_rec['persistent_uri']:
                self.cite_uri = p_uri
                if 'dx.doi.org' in p_uri:
                    break  # stop looking once we have a DOI, the best

    def get_lat_lon(self, solr_rec):
        """ gets latitute and longitude information """
        if 'discovery_geolocation' in solr_rec:
            geo_strings = solr_rec['discovery_geolocation']
            geo_coords_str = geo_strings.split(',')
            # NOT geojson ording, since solr uses lat/lon ordering
            self.latitude = float(geo_coords_str[0])
            self.longitude = float(geo_coords_str[1]) 

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
        """ get media record and thumbnai if it exists """
        if 'uuid' in solr_rec:
            uuid = solr_rec['uuid']
            if uuid in self.thumbnail_data:
                if self.thumbnail_data[uuid] is not False:
                    self.thumbnail_href = self.thumbnail_data[uuid]['href']
                    self.thumbnail_uri = self.thumbnail_data[uuid]['uri']
                    self.thumbnail_scr = self.thumbnail_data[uuid]['scr']
                    rp = RootPath()
                    self.thumbnail_scr = rp.convert_to_https(self.thumbnail_scr)
            else:
                # did not precache thumbnail data, get an indivitual record
                self.get_thumbnail_from_database(solr_rec)

    def get_media_files(self, solr_rec):
        """ get media record and thumbnai if it exists """
        if 'uuid' in solr_rec:
            uuid = solr_rec['uuid']
            if uuid in self.media_file_data:
                if self.media_file_data[uuid] is not False:
                    rp = RootPath()
                    for file_type, file_uri in self.media_file_data[uuid].items():
                        if file_type == 'oc-gen:thumbnail':
                            self.thumbnail_scr = rp.convert_to_https(file_uri)
                        elif file_type == 'oc-gen:preview':
                            self.preview_scr = rp.convert_to_https(file_uri)
                        elif file_type == 'oc-gen:fullfile':
                            self.fullfile_scr = rp.convert_to_https(file_uri)

    def get_thumbnail_from_database(self, solr_rec):
        """ get media record and thumbnail, if it exists """
        if 'uuid' in solr_rec:
            uuid = solr_rec['uuid']
            thumb = []
            if self.item_type != 'media':
                media_item = Assertion.objects\
                                      .filter(uuid=uuid,
                                              object_type='media')[:1]
                if len(media_item) > 0:
                    muuid = media_item[0].object_uuid
                    thumb = Mediafile.objects\
                                     .filter(uuid=muuid,
                                             file_type='oc-gen:thumbnail')[:1]
            else:
                # do this for media items
                muuid = uuid
                thumb = Mediafile.objects\
                                 .filter(uuid=uuid,
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

    """ The following seciton of code
        processes non-default attributes for records
    """
    def get_attributes(self, solr_rec):
        """ gets attributes for a record, based on the
            predicates requested in the search
            and optional predicates passed by a client
            with a GET request with parameter 'attributes'
        """
        qm = QueryMaker()
        solr_field_entities = {}
        for attribute in self.rec_attributes:
            entity = self.m_cache.get_entity(attribute)
            if entity:
                prop_slug = entity.slug
                # check to make sure we have the entity data type for linked fields
                if entity.data_type is False and entity.item_type == 'uri':
                    dtypes = self.s_cache.get_dtypes(entity.uri)
                    if isinstance(dtypes, list):
                        # set te data type and the act-field
                        # print('Found for ' + prop_slug + ' ' + dtypes[0])
                        entity.data_type = dtypes[0]
                field_parts = qm.make_prop_solr_field_parts(entity)
                solr_field = field_parts['prefix'] + '___pred_' + field_parts['suffix']
                # print('Found: ' + solr_field)
                # extract children of the solr_field so we know if
                # we have the most specific attributes, then we can get
                # values for the most specific attributes
                self.extract_attribute_children(solr_rec, solr_field)
        self.clean_attribute_hiearchies()
        if isinstance(self.attribute_hierarchies, dict):
            self.other_attributes = []
            for field_slug_key, values in self.attribute_hierarchies.items():
                entity = self.m_cache.get_entity(field_slug_key)
                if entity:
                    attribute_dict = LastUpdatedOrderedDict()
                    attribute_dict['property'] = entity.label
                    attribute_dict['values_list'] = []
                    attribute_dict['value'] = ''
                    string_val = False
                    delim = ''
                    for val in values:
                        if isinstance(val, str):
                            string_val = True
                            parsed_val = self.parse_solr_value_parts(val)
                            attribute_dict["values_list"].append(parsed_val['label'])
                            attribute_dict['value'] += delim + str(parsed_val['label'])
                        else:
                            attribute_dict["values_list"].append(val)
                            attribute_dict['value'] += delim + str(val)
                        delim = self.ATTRIBUTE_DELIM
                    if len(values) == 1 \
                       and string_val is False:
                        attribute_dict['value'] = values[0]
                    self.other_attributes.append(attribute_dict)

    def get_string_attributes(self, solr_rec):
        """ gets string attributes for a solr rec, from a previous database query
            needed because solr does not cache string field data
        """
        if isinstance(self.string_attrib_data, dict):
            # now add predicate attributes for string predicates, from the database
            if 'uuid' in solr_rec and 'data' in self.string_attrib_data:
                uuid = solr_rec['uuid']
                if uuid in self.string_attrib_data['data']:
                    item_data = self.string_attrib_data['data'][uuid]
                    for pred_uuid, values_list in item_data.items():
                        act_attribute = self.string_attrib_data['pred_ents'][pred_uuid]
                        act_attribute['values_list'] = values_list
                        act_attribute['value'] = self.ATTRIBUTE_DELIM.join(values_list)
                        self.other_attributes.append(act_attribute)

    def prevent_attribute_key_collision(self, item_prop_dict, prop_key):
        """ checks to make sure there's no collision between the prop_key
            and the dict that it will be added to
        """
        i = 2
        output_prop_key = prop_key
        while output_prop_key in item_prop_dict:
            output_prop_key = prop_key + '[' + str(i) + ']'
            i += 1
        return output_prop_key

    def clean_attribute_hiearchies(self):
        """ some post-processing to make sure
            we have clean attribute hierarchies
        """
        if isinstance(self.attribute_hierarchies, dict):
            # print('check: ' + str(self.attribute_hierarchies))
            temp_attribute_hierarchies = self.attribute_hierarchies
            clean_attribute_hiearchies = {}
            for solr_field_key, field_char in self.attribute_hierarchies.items():
                if field_char['most-specific']:
                    par_field_ex = solr_field_key.split('___')
                    # last two parts make the suffix, a pred-slug[-2] and a field type [-1]
                    pred_suffix = '___' + par_field_ex[-2] + '___' + par_field_ex[-1]
                    specific_ok = True
                    for val in field_char['values']:
                        if isinstance(val, str):
                            #  print('check:' + solr_field_key + ' val: ' + val)
                            parsed_val = self.parse_solr_value_parts(val)
                            check_field = parsed_val['slug'].replace('-', '_')
                            check_field += '___pred_' + parsed_val['data_type']
                            if check_field in temp_attribute_hierarchies:
                                # note a field is NOT at the most specific level
                                specific_ok = False
                            else:
                                # now check a version with the predicate as part of
                                # the solr field
                                check_field = parsed_val['slug'].replace('-', '_')
                                check_field += pred_suffix
                                if check_field in temp_attribute_hierarchies:
                                    # note a field is NOT at the most specific level
                                    specific_ok = False
                    if specific_ok:
                        # ok to add
                        # print('checked OK: ' + solr_field_key)
                        clean_attribute_hiearchies[solr_field_key] = field_char
            # now that we got rid of problem fields, lets sort these for consistent
            # rendering
            self.attribute_hierarchies = LastUpdatedOrderedDict()
            keys = LastUpdatedOrderedDict()
            # order of key types, we want id fields, followed by numeric then date
            key_types = ['___pred_id',
                         '___pred_numeric',
                         '___pred_date']
            for key_type in key_types:
                keys[key_type] = []
                for solr_field_key, field_char in clean_attribute_hiearchies.items():
                    if key_type in solr_field_key:
                        keys[key_type].append(solr_field_key)
                # sort alphabetically. Slugs useful, since they will cluster predicates
                # from similar vocabularies
                keys[key_type].sort()
                for key in keys[key_type]:
                    field_char = clean_attribute_hiearchies[key]
                    field_ex = key.split('___')
                    # the penultimate part is the predicate
                    field_slug = field_ex[-2].replace('_', '-')
                    if field_slug not in self.attribute_hierarchies:
                        self.attribute_hierarchies[field_slug] = []
                    for val in field_char['values']:
                        if val not in self.attribute_hierarchies[field_slug]:
                            self.attribute_hierarchies[field_slug].append(val)

    def extract_attribute_children(self,
                                   solr_rec,
                                   solr_field_key):
        """ extracts ALL children from the hiearchy of
            a solr_field_key
        """
        is_field = False
        if solr_field_key not in self.attribute_hierarchies:
            # so we don't look at the same thing twice!
            if solr_field_key in solr_rec:
                is_field = True
                field_char = {'most-specific': False,
                              'values': []}
                if '___pred_numeric' in solr_field_key \
                   or '___pred_numeric' in solr_field_key:
                    field_char['most-specific'] = True
                    field_char['values'] = solr_rec[solr_field_key]
                elif '___pred_id' in solr_field_key:
                    # make a suffix for the 
                    par_field_ex = solr_field_key.split('___')
                    # last two parts make the suffix, a pred-slug[-2] and a field type [-1]
                    pred_suffix = '___' + par_field_ex[-2] + '___' + par_field_ex[-1]
                    childless_children = []
                    for child_val in solr_rec[solr_field_key]:
                        # print('Child: ' + solr_field_key + ': ' + child_val)
                        parsed_path_item = self.parse_solr_value_parts(child_val)
                        new_field_prefix = parsed_path_item['slug'].replace('-', '_')
                        new_field_key = new_field_prefix + '___pred_' + parsed_path_item['data_type']
                        if parsed_path_item['data_type'] == 'id':
                            child_is_field = self.extract_attribute_children(solr_rec,
                                                                             new_field_key)
                            if child_is_field is False:
                                # now check an alternative combining the child
                                # slug with the predicate of the parent
                                new_field_key = new_field_prefix + pred_suffix
                                # print('check: ' + new_field_key)
                                child_is_field = self.extract_attribute_children(solr_rec,
                                                                                 new_field_key)
                                if child_is_field is False:
                                    childless_children.append(child_val)
                    if len(childless_children) > 0:
                        field_char['most-specific'] = True
                        field_char['values'] = childless_children
                else:
                    pass
                self.attribute_hierarchies[solr_field_key] = field_char
        return is_field

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

            This only follows a single path (not multiple paths)
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
                # print('Check: ' + facet_field_key + ', ' + alt_facet_field_key)
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
        if isinstance(solr_value, str):
            if '___' in solr_value:
                solr_ex = solr_value.split('___')
                if len(solr_ex) == 4:
                    output = {}
                    output['slug'] = solr_ex[0]
                    output['data_type'] = solr_ex[1]
                    output['uri'] = solr_ex[2]
                    output['label'] = solr_ex[3]
            else:
                output = solr_value
        else:
            output = solr_value
        return output

    def get_solr_record_uuid_type(self, solr_rec):
        """ get item uuid, label, and type from a solr_rec """
        output = False
        if not isinstance(solr_rec, dict):
            return output
        output = {'uuid': False,
                  'label': False,
                  'item_type': False}
        if 'uuid' in solr_rec:
            output['uuid'] = solr_rec['uuid']
        if 'slug_type_uri_label' in solr_rec:
            id_parts = self.parse_solr_value_parts(solr_rec['slug_type_uri_label'])
            if id_parts is not False:
                uri = self.make_url_from_val_string(id_parts['uri'], True)
                item_type_output = URImanagement.get_uuid_from_oc_uri(uri, True)
                if not item_type_output:
                    return output
                output['item_type'] = item_type_output['item_type']
                output['label'] = id_parts['label']
        return output

    def get_key_val(self, key, dict_obj):
        """ returns the value associated
            with a key, if the key exists
            else, none
        """
        if not isinstance(dict_obj, dict):
            return None
        return dict_obj.get(key)

