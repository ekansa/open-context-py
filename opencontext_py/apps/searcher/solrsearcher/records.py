import json
import geojson
from django.conf import settings
from geojson import Feature, Point, Polygon, GeometryCollection, FeatureCollection
from opencontext_py.libs.rootpath import RootPath
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.apps.entities.entity.models import Entity
from opencontext_py.apps.indexer.solrdocument import SolrDocument
from opencontext_py.apps.ocitems.assertions.models import Assertion
from opencontext_py.apps.ocitems.mediafiles.models import Mediafile


class JsonLDrecords():
    """ methods to make JSON-LD for records returned
        in a solr search; i.e. items in (response.docs)

        This makes GeoJSON-LD features for items with
        geo data.

        TO DO: add JSON-LD for non spatial items
    """

    def __init__(self):
        rp = RootPath()
        self.base_url = rp.get_baseurl()
        self.geojson_recs = []
        self.non_geo_recs = []
        self.total_found = False
        self.rec_start = False
        self.recursive_count = 0
        self.min_date = False
        self.max_date = False

    def make_records_from_solr(self, solr_json):
        """ makes geojson-ld point records from a solr response """
        #first do lots of checks to make sure the solr-json is OK
        if isinstance(solr_json, dict):
            try:
                self.total_found = solr_json['response']['numFound']
            except KeyError:
                self.total_found = False
            try:
                self.rec_start = solr_json['response']['start']
            except KeyError:
                self.rec_start = False
            try:
                solr_recs = solr_json['response']['docs']
            except KeyError:
                solr_recs = False
            if isinstance(solr_recs, list):
                self.process_solr_recs(solr_recs)

    def process_solr_recs(self, solr_recs):
        """ processes the solr_json to
             make GeoJSON records
        """
        i = self.rec_start + 1
        for solr_rec in solr_recs:
            record = LastUpdatedOrderedDict()
            record['id'] = '#record-' + str(i) + '-of-' + str(self.total_found)
            label = 'Record ' + str(i) + ' of ' + str(self.total_found)
            local_url = False
            id_val = self.get_key_val('slug_type_uri_label', solr_rec)
            if id_val is not None:
                id_parts = self.parse_solr_value_parts(id_val)
                if id_parts is not False:
                    label = id_parts['label']
                    record['rdfs:isDefinedBy'] = self.make_url_from_val_string(id_parts['uri'], True)
                    record['label'] = label
                    local_url = self.make_url_from_val_string(id_parts['uri'], False)
            geo_strings = self.get_key_val('discovery_geolocation', solr_rec)
            if geo_strings is not None:
                # add the point geometry
                geo_coords_str = geo_strings[0].split(' ')
                geo_coords = []
                for geo_coord_str in  geo_coords_str:
                    geo_coords.append(float(geo_coord_str))
                geometry = LastUpdatedOrderedDict()
                geometry['id'] = '#geo-rec-geom-' + str(i) + '-of-' + str(self.total_found)
                geometry['type'] = 'Point'
                geometry['coordinates'] = geo_coords
                record['type'] = 'Feature'
                record['category'] = 'oc-api:geo-record'
                record['geometry'] = geometry
                # check for time information
                when = False
                if 'form_use_life_chrono_earliest' in solr_rec \
                   and 'form_use_life_chrono_latest' in solr_rec:
                    early_list = solr_rec['form_use_life_chrono_earliest']
                    late_list = solr_rec['form_use_life_chrono_latest']
                    when = LastUpdatedOrderedDict()
                    when['id'] = '#event-rec-when-' + str(i) + '-of-' + str(self.total_found)
                    when['type'] = 'oc-gen:formation-use-life'
                    if self.min_date is not False \
                       and self.max_date is not False:
                        early_list.sort()
                        for early in early_list:
                            if early >= self.min_date:
                                when['start'] = early
                                break
                        late_list.sort(reverse=True)
                        for late in late_list:
                            if late <= self.max_date:
                                when['stop'] = max(late_list)
                                break
                    if 'start' not in when:
                        when['start'] = min(early_list)
                    if 'stop' not in when:
                        when['stop'] = max(late_list)
                    record['when'] = when
                # start adding GeoJSON properties
                properties = LastUpdatedOrderedDict()
                properties['id'] = '#rec-' + str(i) + '-of-' + str(self.total_found)
                properties['feature type'] = 'item record'
                properties['uri'] = record['rdfs:isDefinedBy']
                properties['href'] = local_url
                # add context information, if present
                self.recursive_count = 0
                projects = self.extract_hierarchy(solr_rec,
                                                  SolrDocument.ROOT_PROJECT_SOLR,
                                                  '___project_id',
                                                  [])
                if len(projects) > 0:
                    properties['project label'] = projects[-1]['label']
                    properties['project href'] = self.make_url_from_val_string(projects[-1]['uri'],
                                                                               False)
                self.recursive_count = 0
                contexts = self.extract_hierarchy(solr_rec,
                                                  SolrDocument.ROOT_CONTEXT_SOLR,
                                                  '___context_id',
                                                  [])
                if len(contexts) > 0:
                    properties['context label'] = self.make_context_path_label(contexts)
                    properties['context href'] = self. make_context_uri(contexts)
                properties['label'] = label
                if isinstance(when, dict):
                    properties['early bce/ce'] = when['start']
                    properties['late bce/ce'] = when['stop']
                # get category information
                self.recursive_count = 0
                cat_hierarchy = self.get_category_hierarchy(solr_rec)
                if len(cat_hierarchy) > 0:
                    properties['item category'] = cat_hierarchy[-1]['label']
                thumbnail = self.get_thumbnail(solr_rec)
                if isinstance(thumbnail, dict):
                    properties['thumbnail'] = thumbnail['src']
                record['properties'] = properties
                # add to list of geospatial records
                self.geojson_recs.append(record)
            else:
                # case when the record is not GeoSpatial in nature
                self.non_geo_recs.append(record)

    def get_thumbnail(self, solr_rec):
        """ get media record and thumbnail, if it exists """
        output = False
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
                    output = {'uuid': muuid,
                              'src': thumb[0].file_uri}
        return output

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
                                                   '___pred_id',
                                                   [])
        return cat_hierarchy

    def extract_hierarchy(self,
                          solr_rec,
                          facet_field_key,
                          facet_suffix,
                          hierarchy=[]):
        """ extracts a hierarchy from a solr_record.
            The output is a list starting with the most
            general parent of the hiearchy,
            then going to the most specific

            This is a recursive function and
            default / starts with the root
            of the hiearchy as the facet_field_key
        """
        if facet_field_key in solr_rec and self.recursive_count < 20:
            self.recursive_count += 1
            path_item_val = solr_rec[facet_field_key][0]
            parsed_path_item = self.parse_solr_value_parts(path_item_val)
            if isinstance(parsed_path_item, dict):
                hierarchy.append(parsed_path_item)
                new_facet_field = parsed_path_item['slug'].replace('-', '_')
                new_facet_field += facet_suffix
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

    def make_context_uri(self, contexts):
        """ makes a URI for a context """
        context_uri = False
        if len(contexts) > 0:
            context_uri = self.make_url_from_val_string(contexts[-1]['uri'],
                                                        False)
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
