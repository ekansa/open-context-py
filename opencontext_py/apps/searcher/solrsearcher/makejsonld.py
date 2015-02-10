import time
import json
import django.utils.http as http
from datetime import datetime
from django.conf import settings
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.apps.entities.entity.models import Entity
from opencontext_py.apps.ocitems.assertions.containment import Containment
from opencontext_py.apps.indexer.solrdocument import SolrDocument
from opencontext_py.apps.ocitems.namespaces.models import ItemNamespaces
from opencontext_py.apps.searcher.solrsearcher.filterlinks import FilterLinks
from opencontext_py.apps.searcher.solrsearcher.querymaker import QueryMaker


class MakeJsonLd():

    def __init__(self, request_dict):
        self.request_dict = request_dict
        self.request_dict_json = json.dumps(request_dict,
                                            ensure_ascii=False,
                                            indent=4)
        self.request_full_path = False
        self.spatial_context = False
        self.id = False
        self.entities = {}
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

    def add_filters_json(self):
        """ adds JSON describing search filters """
        fl = FilterLinks()
        filters = []
        i = 0
        for param_key, param_vals in self.request_dict.items():
            if param_key == 'path':
                i += 1
                f_entity = self.get_filter_entity(param_vals, True)
                label = http.urlunquote_plus(param_vals)
                act_filter = LastUpdatedOrderedDict()
                act_filter['id'] = '#filter-' + str(i)
                act_filter['oc-api:filter'] = 'Context'
                act_filter['label'] = label.replace('||', ' OR ')
                if f_entity is not False:
                    act_filter['rdfs:isDefinedBy'] = f_entity.uri
                # generate a request dict without the context filter
                rem_request = fl.make_request_sub(self.request_dict,
                                                  param_key,
                                                  param_vals)
                act_filter['oc-api:remove'] = fl.make_request_url(rem_request)
                act_filter['oc-api:remove-json'] = fl.make_request_url(rem_request, '.json')
                filters.append(act_filter)
            else:
                for param_val in param_vals:
                    i += 1
                    act_filter = LastUpdatedOrderedDict()
                    act_filter['id'] = '#filter-' + str(i)
                    if ' ' in param_val:
                        all_vals = param_val.split(' ')
                    else:
                        all_vals = [param_val]
                    if param_key == 'proj':
                        # projects, only care about the last item in the parameter value
                        act_filter['oc-api:filter'] = 'Project'
                        label_dict = self.make_filter_label_dict(all_vals[-1])
                        act_filter['label'] = label_dict['label']
                    elif param_key == 'prop':
                        # prop, the first item is the filter-label
                        # the last is the filter
                        if len(all_vals) < 2:
                            act_filter['oc-api:filter'] = 'Description'
                        else:
                            filt_dict = self.make_filter_label_dict(all_vals[0])
                            act_filter['oc-api:filter'] = filt_dict['label']
                        label_dict = self.make_filter_label_dict(all_vals[-1])
                        act_filter['label'] = label_dict['label']
                    elif param_key == 'type':
                        act_filter['oc-api:filter'] = 'Open Context Type'
                        if all_vals[0] in QueryMaker.TYPE_MAPPINGS:
                            type_uri = QueryMaker.TYPE_MAPPINGS[all_vals[0]]
                            label_dict = self.make_filter_label_dict(type_uri)
                            act_filter['label'] = label_dict['label']
                        else:
                            act_filter['label'] = all_vals[0]
                    rem_request = fl.make_request_sub(self.request_dict,
                                                      param_key,
                                                      param_val)
                    act_filter['oc-api:remove'] = fl.make_request_url(rem_request)
                    act_filter['oc-api:remove-json'] = fl.make_request_url(rem_request, '.json')
                    filters.append(act_filter)
        self.json_ld['request'] = self.request_dict
        if len(filters) > 0:
            self.json_ld['oc-api:has-filters'] = filters

    def make_filter_label_dict(self, act_val):
        """ returns a dictionary object
            with a label and set of entities (in cases of OR
            searchs)
        """
        output = {'label': False,
                  'entities': []}
        labels = []
        if '||' in act_val:
            vals = act_val.split('||')
        else:
            vals = [act_val]
        for val in vals:
            f_entity = self.get_filter_entity(val)
            if f_entity is not False:
                labels.append(f_entity.label)
                output['entities'].append(f_entity)
        output['label'] = ' OR '.join(labels)
        return output

    def get_filter_entity(self, identifier, is_path=False):
        """ looks up an entity used in a filter """
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
                output = entity
        return output

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
        self.add_filters_json()
        self.make_facets(solr_json)
        if settings.DEBUG:
            # self.json_ld['request'] = self.request_dict
            self.json_ld['solr'] = solr_json
        return self.json_ld

    def make_id(self):
        """ makes the ID for the document """
        if self.id is not False:
            output = self.id
        elif self.request_full_path is not False:
            output = settings.CANONICAL_HOST + self.request_full_path
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
            pre_sort_facets = {}
            json_ld_facets = []
            for solr_facet_key, solr_facet_values in solr_facet_fields.items():
                facet = self.get_facet_meta(solr_facet_key)
                count_raw_values = len(solr_facet_values)
                id_options = []
                num_options = []
                date_options = []
                string_options = []
                i = -1
                for solr_facet_value_key in solr_facet_values[::2]:
                    i += 2
                    solr_facet_count = solr_facet_values[i]
                    facet_val_obj = self.make_facet_value_obj(solr_facet_key,
                                                              solr_facet_value_key,
                                                              solr_facet_count)
                    val_obj_data_type = facet_val_obj['data-type']
                    facet_val_obj.pop('data-type', None)
                    if val_obj_data_type == 'id':
                        id_options.append(facet_val_obj)
                    elif val_obj_data_type == 'numeric':
                        num_options.append(facet_val_obj)
                    elif val_obj_data_type == 'date':
                        date_options.append(facet_val_obj)
                    elif val_obj_data_type == 'string':
                        string_options.append(facet_val_obj)
                if len(id_options) > 0:
                    facet['oc-api:has-id-options'] = id_options
                if len(num_options) > 0:
                    facet['oc-api:has-numeric-options'] = num_options
                if len(date_options) > 0:
                    facet['oc-api:has-date-options'] = date_options
                if len(string_options) > 0:
                    facet['oc-api:has-text-options'] = string_options
                if count_raw_values > 0:
                    # check so facets without options are not presented
                    pre_sort_facets[facet['id']] = facet
            # now make a sorted list of facets
            json_ld_facets = self.make_sorted_facet_list(pre_sort_facets)
            if len(json_ld_facets) > 0:
                self.json_ld['oc-api:has-facets'] = json_ld_facets

    def make_sorted_facet_list(self, pre_sort_facets):
        """ makes a list of sorted facets based on 
            a dictionary oject of pre_sort_facets
        """
        json_ld_facets = []
        used_keys = []
        if 'prop' in self.request_dict:
            # first check for 'prop' related facets
            # these get promoted to the first positions in the list
            raw_plist = self.request_dict['prop']
            plist = raw_plist[::-1]  # reverse the list, so last props first
            qm = QueryMaker()
            for param_val in plist:
                param_paths = qm.expand_hierarchy_options(param_val)
                for id_key, facet in pre_sort_facets.items():
                    for param_slugs in param_paths:
                        last_slug = param_slugs[-1]
                        if last_slug in id_key \
                           and id_key not in used_keys:
                            # the facet id has the last slug id!
                            # so add to the ordered list of facets
                            json_ld_facets.append(facet)
                            used_keys.append(id_key)
        # now add facet for context
        for id_key, facet in pre_sort_facets.items():
            if '#facet-context' in id_key \
               and id_key not in used_keys:
                json_ld_facets.append(facet)
                used_keys.append(id_key)
        # now add facet for item-types
        if '#facet-item-type' in pre_sort_facets \
           and '#facet-item-type' not in used_keys:
                json_ld_facets.append(pre_sort_facets['#facet-item-type'])
                used_keys.append('#facet-item-type')
        # now add item categories
        for id_key, facet in pre_sort_facets.items():
            if '#facet-prop-oc-gen-' in id_key \
               and id_key not in used_keys:
                json_ld_facets.append(facet)
                used_keys.append(id_key)
        # now add facet for projects
        for id_key, facet in pre_sort_facets.items():
            if '#facet-project' in id_key \
               and id_key not in used_keys:
                json_ld_facets.append(facet)
                used_keys.append(id_key)
        # now add facet for root linked data
        if '#facet-prop-ld' in pre_sort_facets \
           and '#facet-prop-ld' not in used_keys:
                json_ld_facets.append(pre_sort_facets['#facet-prop-ld'])
                used_keys.append('#facet-prop-ld')
        # now add facet for root properties
        if '#facet-prop-var' in pre_sort_facets \
           and '#facet-prop-var' not in used_keys:
                json_ld_facets.append(pre_sort_facets['#facet-prop-var'])
                used_keys.append('#facet-prop-var')
        for id_key in used_keys:
            # delete all the used facets by key
            pre_sort_facets.pop(id_key, None)
        for id_key, facet in pre_sort_facets.items():
            # add remaining (unsorted) facets
            json_ld_facets.append(facet)
        return json_ld_facets

    def get_facet_meta(self, solr_facet_key):
        facet = LastUpdatedOrderedDict()
        # facet['solr'] = solr_facet_key
        if '___project_id' in solr_facet_key:
            id_prefix = '#facet-project'
            ftype = 'oc-api:facet-project'
        elif '___context_id' in solr_facet_key:
            id_prefix = '#facet-context'
            ftype = 'oc-api:facet-context'
        elif '___pred_' in solr_facet_key:
            id_prefix = '#facet-prop'
            ftype = 'oc-api:facet-prop'
        elif 'item_type' in solr_facet_key:
            id_prefix = '#facet-item-type'
            ftype = 'oc-api:item-type'
        if solr_facet_key == SolrDocument.ROOT_CONTEXT_SOLR:
            facet['id'] = id_prefix
            facet['rdfs:isDefinedBy'] = 'oc-api:facet-context'
            facet['label'] = 'Context'
            facet['data-type'] = 'id'
        if solr_facet_key == SolrDocument.ROOT_PROJECT_SOLR:
            facet['id'] = id_prefix
            facet['rdfs:isDefinedBy'] = 'oc-api:facet-project'
            facet['label'] = 'Project'
            facet['data-type'] = 'id'
        elif solr_facet_key == SolrDocument.ROOT_LINK_DATA_SOLR:
            facet['id'] = id_prefix + '-ld'
            facet['rdfs:isDefinedBy'] = 'oc-api:facet-prop-ld'
            facet['label'] = 'Linked Data (Common Standards)'
            facet['data-type'] = 'id'
        elif solr_facet_key == SolrDocument.ROOT_PREDICATE_SOLR:
            facet['id'] = id_prefix + '-var'
            facet['rdfs:isDefinedBy'] = 'oc-api:facet-prop-var'
            facet['label'] = 'Descriptive Properties (Project Defined)'
            facet['data-type'] = 'id'
        elif solr_facet_key == 'item_type':
            facet['id'] = id_prefix
            facet['rdfs:isDefinedBy'] = 'oc-api:facet-item-type'
            facet['label'] = 'Open Context Type'
            facet['data-type'] = 'id'
        else:
            # ------------------------
            # Facet is not at the root
            # ------------------------
            facet['id'] = id_prefix
            facet['label'] = ''
            facet_key_list = solr_facet_key.split('___')
            fdtype_list = facet_key_list[1].split('_')
            fsuffix_list = facet_key_list[-1].split('_')
            slug = facet_key_list[0].replace('_', '-')
            entity = Entity()
            found = entity.dereference(slug)
            if found is False:
                found = entity.dereference(slug, slug)
            if found:
                facet['id'] = id_prefix + '-' + entity.slug
                facet['rdfs:isDefinedBy'] = entity.uri
                facet['label'] = entity.label
            facet['data-type'] = fsuffix_list[-1]
        facet['type'] = ftype
        return facet

    def make_facet_value_obj(self,
                             solr_facet_key,
                             solr_facet_value_key,
                             solr_facet_count):
        """ Makes an last-ordered-dict for a facet """
        facet_key_list = solr_facet_value_key.split('___')
        if len(facet_key_list) == 4:
            # ----------------------------
            # Case where facet values are encoded as:
            # slug___data-type___/uri-item-type/uuid___label
            # ----------------------------
            fl = FilterLinks()
            fl.base_request_json = self.request_dict_json
            fl.base_r_full_path = self.request_full_path
            fl.spatial_context = self.spatial_context
            output = LastUpdatedOrderedDict()
            slug = facet_key_list[0]
            new_rparams = fl.add_to_request_by_solr_field(solr_facet_key,
                                                          slug)
            output['id'] = fl.make_request_url(new_rparams)
            output['json'] = fl.make_request_url(new_rparams, '.json')
            if 'http://' in facet_key_list[2] or 'https://' in facet_key_list[2]:
                output['rdfs:isDefinedBy'] = facet_key_list[2]
            else:
                output['rdfs:isDefinedBy'] = settings.CANONICAL_HOST + facet_key_list[2]
            output['label'] = facet_key_list[3]
            output['count'] = solr_facet_count
            output['slug'] = slug
            output['data-type'] = facet_key_list[1]
        else:
            # ----------------------------
            # Sepcilized cases of non-encoded facet values
            # ----------------------------
            output = LastUpdatedOrderedDict()
            output['id'] = solr_facet_value_key
            output['count'] = solr_facet_count
            output['data-type'] = 'id'
        return output

    def make_specialized_facet_value_obj(self,
                                         solr_facet_key,
                                         solr_facet_value_key,
                                         solr_facet_count,
                                         fl):
        """ makes a facet_value obj for specialzied solr faccets """
        fl = FilterLinks()
        fl.base_request_json = self.request_dict_json
        fl.base_r_full_path = self.request_full_path
        fl.spatial_context = self.spatial_context
        output = LastUpdatedOrderedDict()
        return output

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
