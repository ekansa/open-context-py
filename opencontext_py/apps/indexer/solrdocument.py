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
        self._process_project()
        self._process_category()
        self._process_context_path()
        self._process_predicates()
        self._process_geo()
        self._process_chrono()

    def _process_predicate_values(self, predicate_slug, predicate_type):
        # First generate the solr field name
        solr_field_name = self._convert_slug_to_solr(
            predicate_slug +
            self._get_predicate_field_name_suffix(
                predicate_type)
            )
        # Then get the predicate values
        if(solr_field_name not in self.fields):
            self.fields[solr_field_name] = []
        pred_key = 'oc-pred:' + predicate_slug
        for obs_list in self.oc_item.json_ld['oc-gen:has-obs']:
            if pred_key in obs_list:
                pred_values = obs_list[pred_key]
                for val in pred_values:
                    if predicate_type == '@id':
                        act_solr_field = solr_field_name
                        parents = LinkRecursion().get_jsonldish_entity_parents(val['id'])
                        for parent in parents:
                            if(act_solr_field not in self.fields):
                                self.fields[act_solr_field] = []
                            act_solr_val = self._convert_values_to_json(
                                parent['slug'],
                                parent['label']
                                )
                            self.fields['text'] += ' ' + parent['label'] + ' '
                            self.fields[act_solr_field].append(act_solr_val)
                            # print('\n ID field: ' + act_solr_field + ' Val: ' + act_solr_val)
                            act_solr_field = self._convert_slug_to_solr(parent['slug']) + '___' + solr_field_name
                        self.fields['text'] += ' \n'
                    elif predicate_type in [
                        'xsd:integer', 'xsd:double', 'xsd:boolean', 'xsd:date'
                            ]:
                        self.fields[solr_field_name].append(val)
                    elif predicate_type == 'xsd:string':
                        self.fields['text'] += val['xsd:string'] + ' \n'
                        self.fields[solr_field_name].append(val['xsd:string'])
                    else:
                        raise Exception("Error: Could not get predicate value")

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
                    if(solr_field_name not in self.fields):
                        self.fields[solr_field_name] = []
                    # Add slug and label as json values
                    self.fields[solr_field_name].append(
                        self._convert_values_to_json(
                            parent['slug'],
                            parent['label']
                            )
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
        self.fields['item_type'] = self.oc_item.item_type
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

    def _process_project(self):
        """ Finds the project that this item is part of. If not part of a project,
        make the project slug the same as the item's own slug.
        """ 
        if 'dc-terms:isPartOf' in self.oc_item.json_ld:
            for proj in self.oc_item.json_ld['dc-terms:isPartOf']:
                if('projects' in proj['id']):
                    self.fields['project_slug'] = self._convert_values_to_json(proj['slug'],
                                                                               proj['label'])
                    break
        elif(self.oc_item.item_type == 'projects'):
            self.fields['project_slug'] = self._convert_values_to_json(self.oc_item.json_ld['slug'],
                                                                       self.oc_item.json_ld['label'])

    def _process_geo(self):
        """ Finds geospatial point coordinates in GeoJSON features for indexing.
        Only 1 location of a given location type is allowed.
        """
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
        """ Finds chronological / date ranges in GeoJSON features for indexing.
        More than 1 date range per item is OK.
        """
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

    def _process_category(self):
        """ Finds category / type data ('class_uri' n the manifest table)
        For indexing as a type of predicate
        """
        if 'category' in self.oc_item.json_ld:
            for cat in self.oc_item.json_ld['category']:
                # get the parent entities of the current category
                parents = LinkRecursion().get_jsonldish_entity_parents(cat)
                item_type_found = False
                act_predicate_field = False
                for index, parent in enumerate(parents):
                    # we're ignoring the 'slug' from the LinkRecursion parents, since it's not
                    ptype = predicate_uuid = parent['id'].split('/')[-1]  # gets the last part of the URI
                    prefix_ptype = 'oc-gen-' + ptype
                    if(item_type_found is False):
                        if(ptype == self.oc_item.item_type):
                            item_type_found = True
                    if(act_predicate_field is not False):
                        solr_val = self._convert_values_to_json(prefix_ptype,
                                                                parent['label'])
                        if(act_predicate_field not in self.fields):
                            self.fields[act_predicate_field] = []
                        self.fields[act_predicate_field].append(solr_val)
                    if(item_type_found):
                        act_predicate_field = self._convert_slug_to_solr(prefix_ptype) + '___pred_id'
