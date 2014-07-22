import datetime
import json
from opencontext_py.apps.ocitems.ocitem.models import OCitem
from opencontext_py.apps.ldata.linkannotations.models import LinkRecursion
from opencontext_py.apps.entities.entity.models import Entity
from opencontext_py.libs.chronotiles import ChronoTile
from opencontext_py.libs.globalmaptiles import GlobalMercator


class SolrDocument:
    '''
    Defines the Solr Document objects that the crawler will crawl. Solr
    fields are stored in a Solr Document's "fields" property.
    '''

    def __init__(self, uuid):
        '''
        Using our Python JSON-LD and other info provided in OCitem,
        build up dictionary of solr fields to index.
        '''
        # First get core data structures
        self.oc_item = OCitem().get_item(uuid)
        self.context_path = self._get_context_path()
        # Store values here
        self.fields = {}
        self.fields['text'] = ''  # Start of full-text field
        # Start processing and adding values...
        self._process_core_solr_fields()
        self._process_context_path()
        self._process_predicates()
        self._process_geo()
        self._process_chrono()

    def _process_predicate_values(self, parent_slug, predicate_type):
        # First generate the solr field name
        solr_field_name = self._convert_slug_to_solr(
            parent_slug +
            self._get_predicate_field_name_suffix(
                predicate_type)
            )
        # Then get the predicate values
        self.fields[solr_field_name] = \
            self._get_predicate_values(
                parent_slug,
                predicate_type
            )

    def _get_predicate_field_name_suffix(self, predicate_type):
        '''
        Defines whether our dynamic solr fields names for
        predicates end with ___pred_id, ___pred_numeric, etc.
        '''
        if predicate_type == '@id':
            return '___pred_id'
        elif predicate_type in ['xsd:integer', 'xsd:double', 'xsd:boolean']:
            return '___pred_numeric'
        elif predicate_type == 'xsd:string':
            return '___pred_string'
        elif predicate_type == 'xsd:date':
            return '___pred_date'
        else:
            raise Exception("Error: Unknown predicate type")

    def _get_predicate_values(self, predicate_slug, predicate_type):
        obs_key = 'oc-pred:' + predicate_slug
        for obs_list in self.oc_item.json_ld['oc-gen:has-obs']:
            if obs_key in obs_list:
                if predicate_type == '@id':
                    self.fields['text'] += obs_list[obs_key][0]['label'] + ' \n'
                    return self._convert_values_to_json(
                        obs_list[obs_key][0]['slug'],
                        obs_list[obs_key][0]['label']
                        )
                elif predicate_type in [
                    'xsd:integer', 'xsd:double', 'xsd:boolean'
                        ]:
                    if len(obs_list[obs_key]) == 1:
                        return obs_list[obs_key][0]
                    else:
                        return obs_list[obs_key]
                elif predicate_type == 'xsd:date':
                    self.fields['text'] += obs_list[obs_key][0] + ' \n'
                    return obs_list[obs_key][0] + 'T00:00:00Z'
                elif predicate_type == 'xsd:string':
                    self.fields['text'] += obs_list[obs_key][0]['xsd:string'] + ' \n'
                    return obs_list[obs_key][0]['xsd:string']
                else:
                    raise Exception("Error: Could not get predicate value")

    def _process_predicates(self):
        # Get list of predicates
        predicates = (item for item in self.oc_item.json_ld[
            '@context'].items() if item[0].startswith('oc-pred:'))
        # We need a list for "root___pred_id" because it is multi-valued
        self.fields['root___pred_id'] = []
        for predicate in predicates:
            # We need the predicate's uuid to get its parents
            predicate_uuid = predicate[1]['owl:sameAs'].split('/')[-1]
            predicate_type = predicate[1]['type']
            parents = LinkRecursion(
                ).get_jsonldish_entity_parents(predicate_uuid)
            # Process parents
            for index, parent in enumerate(parents):
                # add the label of the variable to the text field
                self.fields['text'] += ' ' + parent['label'] + ' '
                # Treat the first parent in a special way
                if index == 0:
                    self.fields['root___pred_id'].append(
                        self._convert_values_to_json(
                            parent['slug'],
                            parent['label']
                            )
                        )
                    # If it's the only item, process its predicate values
                    if len(parents) == 1:
                        self._process_predicate_values(
                            parent['slug'],
                            predicate_type
                        )
                else:
                    # Process additional items
                    # Create solr field name using parent slug
                    solr_field_name = \
                        parents[index - 1]['slug'] + '___pred_id'
                    solr_field_name = self._convert_slug_to_solr(
                        solr_field_name
                        )
                    # Add slug and label as json values
                    self.fields[solr_field_name] = \
                        self._convert_values_to_json(
                            parent['slug'],
                            parent['label']
                            )
                    # If this is the last item, process the predicate values
                    if index == len(parents) - 1:
                        self._process_predicate_values(
                            parent['slug'],
                            predicate_type
                            )

    def _get_context_path(self):
        if 'oc-gen:has-context-path' in self.oc_item.json_ld:
            try:
                return self.oc_item.json_ld[
                    'oc-gen:has-context-path']['oc-gen:has-path-items']
            except KeyError:
                return None
        elif 'oc-gen:has-linked-context-path' in self.oc_item.json_ld:
            try:
                return self.oc_item.json_ld[
                    'oc-gen:has-linked-context-path']['oc-gen:has-path-items']
            except KeyError:
                return None
        else:
            return None

    def _convert_slug_to_solr(self, slug):
        return slug.replace('-', '_')

    def _convert_values_to_json(self, key, value):
        json_values = {}
        json_values[key] = value
        return json.dumps(json_values, ensure_ascii=False)

    def _process_core_solr_fields(self):
        self.fields['uuid'] = self.oc_item.uuid
        self.fields['project_uuid'] = self.oc_item.project_uuid
        ent = Entity()
        found = ent.dereference(self.oc_item.project_uuid)
        if(found):
            self.fields['project_slug'] = self._convert_values_to_json(ent.slug,
                                                                       ent.label)
        self.fields['published'] = self.oc_item.published.strftime(
            '%Y-%m-%dT%H:%M:%SZ'
            )   # verify
        self.fields['updated'] = datetime.datetime.utcnow().strftime(  # verify
            '%Y-%m-%dT%H:%M:%SZ')
        self.fields['image_media_count'] = 0  # fix
        self.fields['other_binary_media_count'] = 0  # fix
        self.fields['sort_score'] = 0  # fix
        self.fields['interest_score'] = 0  # fix
        self.fields['document_count'] = 0  # fix
        self.fields['slug_label'] = self._convert_values_to_json(self.oc_item.json_ld['slug'],
                                                                 self.oc_item.json_ld['label'])
        self.fields['text'] += self.oc_item.json_ld['label'] + ' \n'

    def _process_context_path(self):
        if self.context_path is not None:
            for index, context in enumerate(self.context_path):
                # treat the root in its own special way
                if index == 0:
                        self.fields['root___context_id'] = \
                            self._convert_values_to_json(
                                self.context_path[0]['slug'],
                                self.context_path[0]['label']
                                )
                else:
                # for others, get the parent slug and generate a
                # dynamic field name
                    solr_field_name = \
                        self.context_path[index - 1]['slug'] + '___context_id'
                    # replace dashes with underscores because solr requires it
                    solr_field_name = self._convert_slug_to_solr(
                        solr_field_name
                        )
                    # add field name and values as json
                    self.fields[solr_field_name] = \
                        self._convert_values_to_json(
                            self.context_path[index]['slug'],
                            self.context_path[index]['label']
                            )

    def _process_geo(self):
        if 'features' in self.oc_item.json_ld:
            discovery_done = False
            for feature in self.oc_item.json_ld['features']:
                ftype = False
                loc_type = False
                coords = False
                try:
                    ftype = feature['geometry']['type']
                except KeyError:
                    ftype = False
                try:
                    loc_type = feature['properties']['type']
                except KeyError:
                    loc_type = False
                try:
                    zoom = feature['properties']['location-precision']
                except KeyError:
                    zoom = 20
                if(ftype == 'Point'
                   and loc_type == 'oc-gen:discovey-location'
                   and discovery_done is False):
                    try:
                        coords = feature['geometry']['coordinates']
                    except KeyError:
                        coords = False
                    if(coords is not False):
                        gm = GlobalMercator()
                        self.fields['discovery_geotile'] = gm.geojson_coords_to_quadtree(coords, zoom)
                        # indexing with coordinates seperated by a space is in lon-lat order, like GeoJSON
                        self.fields['discovery_geolocation'] = str(coords[0]) + ' ' + str(coords[1])
                        discovery_done = True  # so we don't repeat getting discovery locations
                if(discovery_done):
                    break

    def _process_chrono(self):
        if 'features' in self.oc_item.json_ld:
            for feature in self.oc_item.json_ld['features']:
                bad_time = False
                try:
                    start = feature['when']['start']
                except KeyError:
                    bad_time = True
                try:
                    stop = feature['when']['stop']
                except KeyError:
                    bad_time = True
                try:
                    when_type = feature['when']['type']
                except KeyError:
                    when_type = False
                if(when_type == 'oc-gen:formation-use-life' and bad_time is False):
                    ct = ChronoTile()
                    if('form_use_life_chrono_tile' not in self.fields):
                        self.fields['form_use_life_chrono_tile'] = []
                    if('form_use_life_chrono_earliest' not in self.fields):
                        self.fields['form_use_life_chrono_earliest'] = []
                    if('form_use_life_chrono_latest' not in self.fields):
                        self.fields['form_use_life_chrono_latest'] = []
                    self.fields['form_use_life_chrono_tile']\
                        .append(ct.encode_path_from_bce_ce(start, stop, '10M-'))
                    self.fields['form_use_life_chrono_earliest'].append(start)
                    self.fields['form_use_life_chrono_latest'].append(stop)
