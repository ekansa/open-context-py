import re
import json
import geojson
import django.utils.http as http
from django.conf import settings
from geojson import Feature, Point, Polygon, GeometryCollection, FeatureCollection
from urllib.parse import urlparse, parse_qs
from django.utils.http import urlquote, quote_plus, urlquote_plus
from opencontext_py.libs.memorycache import MemoryCache
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.libs.chronotiles import ChronoTile
from opencontext_py.libs.globalmaptiles import GlobalMercator
from opencontext_py.apps.entities.entity.models import Entity
from opencontext_py.apps.searcher.solrsearcher.filterlinks import FilterLinks
from opencontext_py.apps.searcher.solrsearcher.querymaker import QueryMaker


class ActiveFilters():

    """ Methods to show search / query filters in use """
    TEXT_SEARCH_TITLE = 'Current Text Search Filter'

    IGNORE_PARAMS = ['geodeep',
                     'chronodeep',
                     'sort',
                     'rows',
                     'start']

    def __init__(self):
        self.m_cache = MemoryCache()  # memory caching object
        self.base_search_link = '/search/'
        self.hierarchy_delim = '---'

    def add_filters_json(self, request_dict):
        """ adds JSON describing search filters """
        fl = FilterLinks()
        fl.base_search_link = self.base_search_link
        filters = []
        string_fields = []  # so we have an interface for string searches
        i = 0
        for param_key, param_vals in request_dict.items():
            if param_key == 'path':
                if param_vals:
                    i += 1
                    f_entity = self.m_cache.get_entity(param_vals)
                    label = http.urlunquote_plus(param_vals)
                    act_filter = LastUpdatedOrderedDict()
                    act_filter['id'] = '#filter-' + str(i)
                    act_filter['oc-api:filter'] = 'Context'
                    act_filter['label'] = label.replace('||', ' OR ')
                    if f_entity:
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
                    remove_geodeep = False
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
                            act_filter['oc-api:filter-slug'] = all_vals[0]
                        else:
                            filt_dict = self.make_filter_label_dict(all_vals[0])
                            act_filter['oc-api:filter'] = filt_dict['label']
                            if 'slug' in filt_dict:
                                act_filter['oc-api:filter-slug'] = filt_dict['slug']
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
                        act_filter['oc-api:filter'] = self.TEXT_SEARCH_TITLE
                        act_filter['label'] = 'Search Term: \'' + all_vals[0] + '\''
                    elif param_key == 'id':
                        act_filter['oc-api:filter'] = 'Identifier Lookup'
                        act_filter['label'] = 'Identifier: \'' + all_vals[0] + '\''
                    elif param_key == 'form-chronotile':
                        act_filter['oc-api:filter'] = 'Time of formation, use, or life'
                        chrono = ChronoTile()
                        dates = chrono.decode_path_dates(all_vals[0])
                        if isinstance(dates, dict):
                            act_filter['label'] = 'Time range: ' + str(dates['earliest_bce'])
                            act_filter['label'] += ' to ' + str(dates['latest_bce'])
                    elif param_key == 'form-start':
                        act_filter['oc-api:filter'] = 'Earliest formation, use, or life date'
                        try:
                            val_date = int(float(all_vals[0]))
                        except:
                            val_date = False
                        if val_date is False:
                            act_filter['label'] = '[Invalid year]'
                        elif val_date < 0:
                            act_filter['label'] = str(val_date * -1) + ' BCE'
                        else:
                            act_filter['label'] = str(val_date) + ' CE'
                    elif param_key == 'form-stop':
                        act_filter['oc-api:filter'] = 'Latest formation, use, or life date'
                        try:
                            val_date = int(float(all_vals[0]))
                        except:
                            val_date = False
                        if val_date is False:
                            act_filter['label'] = '[Invalid year]'
                        elif val_date < 0:
                            act_filter['label'] = str(val_date * -1) + ' BCE'
                        else:
                            act_filter['label'] = str(val_date) + ' CE'
                    elif param_key == 'disc-geotile':
                        act_filter['oc-api:filter'] = 'Location of discovery or observation'
                        act_filter['label'] = self.make_geotile_filter_label(all_vals[0])
                        remove_geodeep = True
                    elif param_key == 'disc-bbox':
                        act_filter['oc-api:filter'] = 'Location of discovery or observation'
                        act_filter['label'] = self.make_bbox_filter_label(all_vals[0])
                        remove_geodeep = True
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
                        if 'tdar' == all_vals[-1] or 'tdar*' == all_vals[-1]:
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
                    elif param_key == 'dc-temporal':
                        act_filter['oc-api:filter'] = 'Has temporal coverage'
                        label_dict = self.make_filter_label_dict(all_vals[-1])
                        if len(label_dict['label']) > 0:
                            act_filter['label'] = label_dict['label']
                            if len(label_dict['entities']) == 1: 
                                if label_dict['entities'][0].entity_type == 'vocabulary':
                                    act_filter['label'] = 'Concepts defined by: ' + label_dict['label']
                            elif 'periodo' in all_vals[-1]:
                                act_filter['label'] = 'PeriodO defined concepts'
                        if len(label_dict['entities']) == 1:
                            act_filter['rdfs:isDefinedBy'] = label_dict['entities'][0].uri
                            if label_dict['entities'][0].vocabulary is not False\
                               and label_dict['entities'][0].vocabulary != label_dict['label']:
                                act_filter['label'] += ' in ' + label_dict['entities'][0].vocabulary
                    elif param_key == 'obj':
                        act_filter['oc-api:filter'] = 'Links (in some manner) to object'
                        label_dict = self.make_filter_label_dict(all_vals[-1])
                        if len(label_dict['label']) > 0:
                            act_filter['label'] = label_dict['label']
                        if len(label_dict['entities']) == 1:
                            act_filter['rdfs:isDefinedBy'] = label_dict['entities'][0].uri
                            if label_dict['entities'][0].vocabulary is not False:
                                act_filter['label'] += ' in ' + label_dict['entities'][0].vocabulary
                    elif param_key == 'dc-isReferencedBy':
                        act_filter['oc-api:filter'] = 'Is referenced by'
                        label_dict = self.make_filter_label_dict(all_vals[-1])
                        if len(label_dict['label']) > 0:
                            act_filter['label'] = label_dict['label']
                        if len(label_dict['entities']) == 1:
                            act_filter['rdfs:isDefinedBy'] = label_dict['entities'][0].uri
                            if label_dict['entities'][0].vocabulary is not False\
                               and label_dict['entities'][0].vocab_uri != label_dict['entities'][0].uri:
                                act_filter['label'] += ' in ' + label_dict['entities'][0].vocabulary
                    elif param_key == 'linked' and all_vals[-1] == 'dinaa-cross-ref':
                        act_filter['oc-api:filter'] = 'Has cross references'
                        act_filter['label'] = 'Links to, or with, DINAA curated site files'
                    else:
                        act_filter = False
                    if act_filter is not False:
                        rem_request = fl.make_request_sub(request_dict,
                                                          param_key,
                                                          param_val)
                        if 'geodeep' in rem_request and remove_geodeep:
                            rem_request.pop('geodeep', None)    
                        act_filter['oc-api:remove'] = fl.make_request_url(rem_request)
                        act_filter['oc-api:remove-json'] = fl.make_request_url(rem_request, '.json')
                        filters.append(act_filter)
        return filters

    def make_geotile_filter_label(self, raw_geotile):
        """ parses a raw bbox parameter value to make
            a filter label
        """
        output_list = []
        if '||' in raw_geotile:
            tile_list = raw_geotile.split('||')
        else:
            tile_list = [raw_geotile]
        for tile in tile_list:
            geotile = GlobalMercator()
            coordinates = geotile.quadtree_to_lat_lon(tile)
            if coordinates is not False:
                label = 'In the region bounded by: '
                label += str(round(coordinates[0], 3))
                label += ', ' + str(round(coordinates[1], 3))
                label += ' (SW) and ' + str(round(coordinates[2], 3))
                label += ', ' + str(round(coordinates[3], 3))
                label += ' (NE)'
                output_list.append(label)
            else:
                output_list.append('[Ignored invalid geospatial tile]')
        output = '; or '.join(output_list)
        return output

    def make_bbox_filter_label(self, raw_disc_bbox):
        """ parses a raw bbox parameter value to make
            a filter label
        """
        qm = QueryMaker()
        output_list = []
        if '||' in raw_disc_bbox:
            bbox_list = raw_disc_bbox.split('||')
        else:
            bbox_list = [raw_disc_bbox]
        for bbox in bbox_list:
            if ',' in bbox:
                bbox_coors = bbox.split(',')
                bbox_valid = qm.validate_bbox_coordiantes(bbox_coors)
                if bbox_valid:
                    label = 'In the bounding-box of: Latitude '
                    label += str(bbox_coors[1])
                    label += ', Longitude ' + str(bbox_coors[0])
                    label += ' (SW) and Latitude ' + str(bbox_coors[3])
                    label += ', Longitude ' + str(bbox_coors[2])
                    label += ' (NE)'
                    output_list.append(label)
                else:
                    output_list.append('[Ignored invalid bounding-box]')
            else:
                output_list.append('[Ignored invalid bounding-box]')
        output = '; or '.join(output_list)
        return output

    def make_filter_label_dict(self, act_val):
        """ returns a dictionary object
            with a label and set of entities (in cases of OR
            searchs)
        """
        related_suffix = ''
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
            qm = QueryMaker()
            db_val = qm.clean_related_slug(val)
            if val != db_val:
                related_suffix = ' (for related items)'
            f_entity = self.m_cache.get_entity(db_val)
            if f_entity:
                # get the solr field data type
                ent_solr_data_type = qm.get_solr_field_type(f_entity.data_type)
                if ent_solr_data_type is not False \
                   and ent_solr_data_type != 'id':
                    output['data-type'] = ent_solr_data_type
                labels.append(f_entity.label)
                output['entities'].append(f_entity)
            else:
                labels.append(val)
        output['label'] = (' OR '.join(labels)) + related_suffix
        output['slug'] = '-or-'.join(vals)
        return output
