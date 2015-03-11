import re
import json
import geojson
import django.utils.http as http
from django.conf import settings
from geojson import Feature, Point, Polygon, GeometryCollection, FeatureCollection
from urllib.parse import urlparse, parse_qs
from django.utils.http import urlquote, quote_plus, urlquote_plus
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.libs.chronotiles import ChronoTile
from opencontext_py.libs.globalmaptiles import GlobalMercator
from opencontext_py.apps.entities.entity.models import Entity
from opencontext_py.apps.searcher.solrsearcher.filterlinks import FilterLinks
from opencontext_py.apps.searcher.solrsearcher.querymaker import QueryMaker


class ActiveFilters():

    """ Methods to show search / query filters in use """

    def __init__(self):
        self.entities = {}  # entities already dereferenced
        self.hierarchy_delim = '---'

    def add_filters_json(self, request_dict):
        """ adds JSON describing search filters """
        fl = FilterLinks()
        filters = []
        string_fields = []  # so we have an interface for string searches
        i = 0
        for param_key, param_vals in request_dict.items():
            if param_key == 'path':
                if param_vals is not False and param_vals is not None:
                    i += 1
                    f_entity = self.get_entity(param_vals, True)
                    label = http.urlunquote_plus(param_vals)
                    act_filter = LastUpdatedOrderedDict()
                    act_filter['id'] = '#filter-' + str(i)
                    act_filter['oc-api:filter'] = 'Context'
                    act_filter['label'] = label.replace('||', ' OR ')
                    if f_entity is not False:
                        act_filter['rdfs:isDefinedBy'] = f_entity.uri
                    # generate a request dict without the context filter
                    rem_request = fl.make_request_sub(request_dict,
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
                    if self.hierarchy_delim in param_val:
                        all_vals = param_val.split(self.hierarchy_delim)
                    else:
                        all_vals = [param_val]
                    if param_key == 'proj':
                        # projects, only care about the last item in the parameter value
                        act_filter['oc-api:filter'] = 'Project'
                        label_dict = self.make_filter_label_dict(all_vals[-1])
                        act_filter['label'] = label_dict['label']
                        if len(label_dict['entities']) == 1:
                            act_filter['rdfs:isDefinedBy'] = label_dict['entities'][0].uri
                    elif param_key == 'prop':
                        # prop, the first item is the filter-label
                        # the last is the filter
                        act_filter['label'] = False
                        if len(all_vals) < 2:
                            act_filter['oc-api:filter'] = 'Description'
                        else:
                            filt_dict = self.make_filter_label_dict(all_vals[0])
                            act_filter['oc-api:filter'] = filt_dict['label']
                            if filt_dict['data-type'] == 'string':
                                act_filter['label'] = 'Search Term: \'' + all_vals[-1] + '\''
                        if act_filter['label'] is False:
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
                    elif param_key == 'q':
                        act_filter['oc-api:filter'] = 'General Keyword Search'
                        act_filter['label'] = 'Search Term: \'' + all_vals[0] + '\''
                    elif param_key == 'form-chronotile':
                        act_filter['oc-api:filter'] = 'Time of formation, use, or life'
                        chrono = ChronoTile()
                        dates = chrono.decode_path_dates(all_vals[0])
                        if isinstance(dates, dict):
                            act_filter['label'] = 'Time range: ' + str(dates['earliest_bce'])
                            act_filter['label'] += ' to ' + str(dates['latest_bce'])
                    elif param_key == 'disc-geotile':
                        act_filter['oc-api:filter'] = 'Location of discovery or observation'
                        geotile = GlobalMercator()
                        coordinates = geotile.quadtree_to_lat_lon(all_vals[0])
                        if coordinates is not False:
                            act_filter['label'] = 'In the region bounded by: '
                            act_filter['label'] += str(round(coordinates[0], 3))
                            act_filter['label'] += ', ' + str(round(coordinates[1], 3))
                            act_filter['label'] += ' (SW) and ' + str(round(coordinates[2], 3))
                            act_filter['label'] += ', ' + str(round(coordinates[3], 3))
                            act_filter['label'] += ' (NE)'
                    elif param_key == 'images':
                        act_filter['oc-api:filter'] = 'Has related media'
                        act_filter['label'] = 'Linked to images'
                    elif param_key == 'other-media':
                        act_filter['oc-api:filter'] = 'Has related media'
                        act_filter['label'] = 'Linked to media (other than images)'
                    elif param_key == 'documents':
                        act_filter['oc-api:filter'] = 'Has related media'
                        act_filter['label'] = 'Linked to documents'
                    elif param_key == 'dc-subject':
                        act_filter['oc-api:filter'] = 'Has subject metadata'
                        label_dict = self.make_filter_label_dict(all_vals[-1])
                        if len(label_dict['label']) > 0:
                            act_filter['label'] = label_dict['label']
                        elif 'tdar' in all_vals[-1]:
                            act_filter['label'] = 'tDAR defined metadata record(s)'
                        if len(label_dict['entities']) == 1:
                            act_filter['rdfs:isDefinedBy'] = label_dict['entities'][0].uri
                            if label_dict['entities'][0].vocabulary is not False:
                                act_filter['label'] += ' in ' + label_dict['entities'][0].vocabulary
                    elif param_key == 'dc-spatial':
                        act_filter['oc-api:filter'] = 'Has spatial metadata'
                        label_dict = self.make_filter_label_dict(all_vals[-1])
                        if len(label_dict['label']) > 0:
                            act_filter['label'] = label_dict['label']
                        if len(label_dict['entities']) == 1:
                            act_filter['rdfs:isDefinedBy'] = label_dict['entities'][0].uri
                            if label_dict['entities'][0].vocabulary is not False:
                                act_filter['label'] += ' in ' + label_dict['entities'][0].vocabulary
                    elif param_key == 'dc-coverage':
                        act_filter['oc-api:filter'] = 'Has coverage / period metadata'
                        label_dict = self.make_filter_label_dict(all_vals[-1])
                        if len(label_dict['label']) > 0:
                            act_filter['label'] = label_dict['label']
                        if len(label_dict['entities']) == 1:
                            act_filter['rdfs:isDefinedBy'] = label_dict['entities'][0].uri
                            if label_dict['entities'][0].vocabulary is not False:
                                act_filter['label'] += ' in ' + label_dict['entities'][0].vocabulary
                    rem_request = fl.make_request_sub(request_dict,
                                                      param_key,
                                                      param_val)
                    act_filter['oc-api:remove'] = fl.make_request_url(rem_request)
                    act_filter['oc-api:remove-json'] = fl.make_request_url(rem_request, '.json')
                    filters.append(act_filter)
        return filters

    def make_filter_label_dict(self, act_val):
        """ returns a dictionary object
            with a label and set of entities (in cases of OR
            searchs)
        """
        output = {'label': False,
                  'data-type': 'id',
                  'slug': False,
                  'entities': []}
        labels = []
        if '||' in act_val:
            vals = act_val.split('||')
        else:
            vals = [act_val]
        for val in vals:
            f_entity = self.get_entity(val)
            if f_entity is not False:
                qm = QueryMaker()
                # get the solr field data type
                ent_solr_data_type = qm.get_solr_field_type(f_entity.data_type)
                if ent_solr_data_type is not False \
                   and ent_solr_data_type != 'id':
                    output['data-type'] = ent_solr_data_type
                labels.append(f_entity.label)
                output['entities'].append(f_entity)
        output['label'] = ' OR '.join(labels)
        output['slug'] = '-or-'.join(vals)
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
                output = entity
        return output
