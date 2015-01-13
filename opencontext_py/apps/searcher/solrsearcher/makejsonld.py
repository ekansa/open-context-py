from datetime import datetime
import time
from django.conf import settings
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.apps.entities.entity.models import Entity
from opencontext_py.apps.ocitems.assertions.containment import Containment
from opencontext_py.apps.indexer.solrdocument import SolrDocument
from opencontext_py.apps.ocitems.namespaces.models import ItemNamespaces


class MakeJsonLd():

    def __init__(self, request=False, spatial_context=None):
        self.request = request
        self.spatial_context = spatial_context
        self.id = False
        self.label = settings.CANONICAL_SITENAME + ' API'
        self.json_ld = LastUpdatedOrderedDict()
        item_ns = ItemNamespaces()
        context = item_ns.namespaces
        self.namespaces = context
        context['opensearch'] = 'http://a9.com/-/spec/opensearch/1.1/'
        context['oc-api'] = 'http://opencontext.org/vocabularies/oc-general/oc-api/'
        context['id'] = '@id'
        context['label'] = 'rdfs:label'
        context['uuid'] = 'dc-terms:identifier'
        context['slug'] = 'oc-gen:slug'
        context['type'] = '@type'
        context['category'] = {'@id': 'oc-gen:category', '@type': '@id'}
        context['Feature'] = 'geojson:Feature'
        context['FeatureCollection'] = 'geojson:FeatureCollection'
        context['GeometryCollection'] = 'geojson:GeometryCollection'
        context['Instant'] = 'http://www.w3.org/2006/time#Instant'
        context['Interval'] = 'http://www.w3.org/2006/time#Interval'
        context['LineString'] = 'geojson:LineString'
        context['MultiLineString'] = 'geojson:MultiLineString'
        context['MultiPoint'] = 'geojson:MultiPoint'
        context['MultiPolygon'] = 'geojson:MultiPolygon'
        context['Point'] = 'geojson:Point'
        context['Polygon'] = 'geojson:Polygon'
        context['bbox'] = {'@id': 'geojson:bbox', '@container': '@list'}
        context['circa'] = 'geojson:circa'
        context['coordinates'] = 'geojson:coordinates'
        context['datetime'] = 'http://www.w3.org/2006/time#inXSDDateTime'
        context['description'] = 'dc-terms:description'
        context['features'] = {'@id': 'geojson:features', '@container': '@set'}
        context['geometry'] = 'geojson:geometry'
        context['properties'] = 'geojson:properties'
        context['start'] = 'http://www.w3.org/2006/time#hasBeginning'
        context['stop'] = 'http://www.w3.org/2006/time#hasEnding'
        context['title'] = 'dc-terms:title'
        context['when'] = 'geojson:when'
        context['reference-type'] = {'@id': 'oc-gen:reference-type', '@type': '@id'}
        context['inferred'] = 'oc-gen:inferred'
        context['specified'] = 'oc-gen:specified'
        context['reference-uri'] = 'oc-gen:reference-uri'
        context['reference-label'] = 'oc-gen:reference-label'
        context['location-precision'] = 'oc-gen:location-precision'
        context['location-note'] = 'oc-gen:location-note'
        self.base_context = context

    def convert_solr_json(self, solr_json):
        """ Converst the solr jsont """
        self.json_ld['@context'] = self.base_context
        self.json_ld['id'] = self.make_id()
        self.json_ld['label'] = self.label
        self.json_ld['opensearch:totalResults'] = self.get_path_in_dict(['response',
                                                                         'numFound'],
                                                                        solr_json)
        self.json_ld['dcmi:modified'] = self.get_modified_datetime(solr_json)
        self.json_ld['dcmi:created'] = self.get_created_datetime(solr_json)
        self.make_facets(solr_json)
        # self.json_ld['request'] = self.request.GET
        # self.json_ld['solr'] = solr_json
        return self.json_ld

    def make_id(self):
        """ makes the ID for the document """
        if self.id is not False:
            output = self.id
        elif self.request is not False:
            output = settings.CANONICAL_HOST + self.request.get_full_path()
        else:
            output = False
        return output

    def get_modified_datetime(self, solr_json):
        """ Makes the last modified time in ISO 8601 format
            Solr already defaults to that format
        """
        modified = self.get_path_in_dict(['stats',
                                          'stats_fields',
                                          'updated',
                                          'max'],
                                         solr_json)
        if modified is False:
            modified = time.strftime('%Y-%m-%dT%H:%M:%S') + 'Z'
        return modified

    def get_created_datetime(self, solr_json):
        """ Makes the last modified time in ISO 8601 format
            Solr already defaults to that format
        """
        created = self.get_path_in_dict(['stats',
                                        'stats_fields',
                                        'published',
                                        'max'],
                                        solr_json)
        if created is False:
            created = time.strftime('%Y-%m-%dT%H:%M:%S') + 'Z'
        return created

    def make_facets(self, solr_json):
        """ Makes a list of facets """
        solr_facet_fields = self.get_path_in_dict(['facet_counts',
                                                  'facet_fields'],
                                                  solr_json)
        if solr_facet_fields is not False:
            json_ld_facets = []
            for solr_facet_key, solr_facet_values in solr_facet_fields.items():
                facet = self.get_facet_meta(solr_facet_key)
                facet['oc-api:has-facet-values'] = []
                count_raw_values = len(solr_facet_values)
                i = -1
                for solr_facet_value_key in solr_facet_values[::2]:
                    i += 2
                    solr_facet_count = solr_facet_values[i]
                    facet_val_obj = self.make_facet_value_obj(solr_facet_key,
                                                              solr_facet_value_key,
                                                              solr_facet_count)
                    facet['oc-api:has-facet-values'].append(facet_val_obj)
                json_ld_facets.append(facet)
            if len(json_ld_facets) > 0:
                self.json_ld['oc-api:has-facets'] = json_ld_facets

    def get_facet_meta(self, solr_facet_key):
        facet = LastUpdatedOrderedDict()
        if solr_facet_key == SolrDocument.ROOT_PROJECT_SOLR:
            facet['id'] = 'oc-api:facet-project'
            facet['label'] = 'Project'
            facet['data-type'] = 'id'
        elif solr_facet_key == SolrDocument.ROOT_LINK_DATA_SOLR:
            facet['id'] = 'oc-api:facet-ld'
            facet['label'] = 'Linked Data (Common Standards)'
            facet['data-type'] = 'id'
        elif solr_facet_key == SolrDocument.ROOT_PREDICATE_SOLR:
            facet['id'] = 'oc-api:facet-var'
            facet['label'] = 'Descriptive Properties (Project Defined)'
            facet['data-type'] = 'id'
        else:
            facet['id'] = ''
            facet['label'] = ''
            facet_key_list = solr_facet_key.split('___')
            fdtype_list = facet_key_list[1].split('_')
            slug = facet_key_list[0].replace('_', '-')
            entity = Entity()
            found = entity.dereference(slug)
            if found:
                facet['id'] = entity.uri
                facet['label'] = entity.label
            facet['data-type'] = fdtype_list[1]
        return facet

    def make_facet_value_obj(self,
                             solr_facet_key,
                             solr_facet_value_key,
                             solr_facet_count):
        """ Makes an last-ordered-dict for a facet """
        facet_key_list = solr_facet_value_key.split('___')
        output = LastUpdatedOrderedDict()
        if len(facet_key_list) == 4:
            if 'http://' in facet_key_list[2] or 'https://' in facet_key_list[2]:
                output['id'] = facet_key_list[2]
            else:
                output['id'] = settings.CANONICAL_HOST + facet_key_list[2]
            output['label'] = facet_key_list[3]
            output['count'] = solr_facet_count
            output['slug'] = facet_key_list[0]
            output['filter'] = 'to do'
        return output

    def get_path_in_dict(self, key_path_list, dict_obj, default=False):
        """ get part of a dictionary object by a list of keys """
        act_dict_obj = dict_obj
        for key in key_path_list:
            if key in act_dict_obj:
                act_dict_obj = act_dict_obj[key]
                output = act_dict_obj
            else:
                output = default
                break
        return output
