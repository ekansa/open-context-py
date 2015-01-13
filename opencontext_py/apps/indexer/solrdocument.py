import datetime
import json
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.apps.ocitems.ocitem.models import OCitem
from opencontext_py.apps.ldata.linkannotations.recursion import LinkRecursion
from opencontext_py.apps.ocitems.projects.metadata import ProjectRels
from opencontext_py.libs.chronotiles import ChronoTile
from opencontext_py.libs.globalmaptiles import GlobalMercator
from opencontext_py.apps.entities.uri.models import URImanagement


class SolrDocument:
    '''
    Defines the Solr Document objects that the crawler will crawl. Solr
    fields are stored in a Solr Document's "fields" property.
    '''

    # the list below defines predicates used for semantic equivalence in indexing
    # linked data
    LD_EQUIVALENT_PREDICATES = ['skos:closeMatch',
                                'owl:sameAs',
                                'foaf:isPrimaryTopicOf']

    LD_IDENTIFIER_PREDICATES = ['owl:sameAs',
                                'foaf:isPrimaryTopicOf']

    PERSISTENT_ID_ROOTS = ['dx.doi.org',
                           'n2t.net/ark:/',
                           'orcid.org']

    ROOT_PREDICATE_SOLR = 'root___pred_id'
    ROOT_LINK_DATA_SOLR = 'ld___pred_id'
    ROOT_PROJECT_SOLR = 'proj___pred_id'

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
        self._process_category()
        self._process_context_path()
        self._process_predicates()
        self._process_geo()
        self._process_chrono()
        self._process_text_content()
        self._process_dc_terms()
        self._process_projects()
        self._process_persistent_ids()
        self._process_associated_linkedata()
        self._process_interest_score()

    def _process_predicate_values(self, predicate_slug, predicate_type):
        # First generate the solr field name
        solr_field_name = self._convert_slug_to_solr(
            predicate_slug +
            self._get_predicate_type_string(
                predicate_type, prefix='___pred_')
            )
        # Then get the predicate values
        if solr_field_name not in self.fields:
            self.fields[solr_field_name] = []
        if self.oc_item.item_type == 'media' \
                or self.oc_item.item_type == 'documents':
        # we want to make joins easier for these types of items
            make_join_ids = True
        else:
            make_join_ids = False
        predicate_key = 'oc-pred:' + predicate_slug
        for obs_list in self.oc_item.json_ld['oc-gen:has-obs']:
            if predicate_key in obs_list:
                predicate_values = obs_list[predicate_key]
                for value in predicate_values:
                    if predicate_type == '@id':
                        if make_join_ids and 'subjects' in value['id']:
                            # case where we want to make a join field to link
                            # associated subjects items with media or document
                            # items allows join relationships between
                            # 'join___pred_id' and 'uuid' solr fields.
                            if 'join___pred_id' not in self.fields:
                                self.fields['join___pred_id'] = []
                            # get subjects UUID from the URI
                            sub_uuid = URImanagement.get_uuid_from_oc_uri(
                                value['id']
                                )
                            # append to the solr field for joins
                            self.fields['join___pred_id'].append(sub_uuid)
                        if predicate_slug != 'link':
                            active_solr_field = solr_field_name
                            parents = LinkRecursion(
                                ).get_jsonldish_entity_parents(
                                value['id']
                                )
                            for parent in parents:
                                if active_solr_field not in self.fields:
                                    self.fields[active_solr_field] = []
                                active_solr_value = \
                                    self._concat_solr_string_value(
                                        parent['slug'],
                                        self._get_predicate_type_string(
                                            parent['type']),
                                        parent['id'],
                                        parent['label']
                                    )
                                self.fields['text'] += ' ' + \
                                    parent['label'] + ' '
                                self.fields[active_solr_field].append(
                                    active_solr_value
                                    )
                                active_solr_field = self._convert_slug_to_solr(
                                    parent['slug']) + '___' + solr_field_name
                        else:
                            # case of a linking relation, don't bother looking
                            # up hierarchies or recording as a solr field, but
                            # check for image, other media, and document counts
                            if 'media' in value['id'] \
                                    and 'image' in value['type']:
                                self.fields['image_media_count'] += 1
                            elif 'media' in value['id'] \
                                    and 'image' not in value['type']:
                                 # other types of media
                                self.fields['other_binary_media_count'] += 1
                            elif 'documents' in value['id']:
                                self.fields['document_count'] += 1
                            self.fields['text'] += value['label'] + ' '
                    elif predicate_type in [
                        'xsd:integer', 'xsd:double', 'xsd:boolean'
                            ]:
                        self.fields[solr_field_name].append(value)
                    elif predicate_type == 'xsd:date':
                        self.fields[solr_field_name].append(value +
                                                            'T00:00:00Z')
                    elif predicate_type == 'xsd:string':
                        self.fields['text'] += value['xsd:string'] + ' \n'
                        self.fields[solr_field_name].append(
                            value['xsd:string'])
                    else:
                        raise Exception("Error: Could not get predicate value")
                self.fields['text'] += ' \n'

    def _get_predicate_type_string(self, predicate_type,
                                   prefix=''):
        '''
        Defines whether our dynamic solr fields names for
        predicates end with ___pred_id, ___pred_numeric, etc.
        '''
        if predicate_type in ['@id', 'id']:
            return prefix + 'id'
        elif predicate_type in ['xsd:integer', 'xsd:double', 'xsd:boolean']:
            return prefix + 'numeric'
        elif predicate_type == 'xsd:string':
            return prefix + 'string'
        elif predicate_type == 'xsd:date':
            return prefix + 'date'
        else:
            raise Exception("Error: Unknown predicate type")

    def _process_predicates(self):
        # Get list of predicates
        predicates = (item for item in self.oc_item.json_ld[
            '@context'].items() if item[0].startswith('oc-pred:'))
        # We need a list for "root___pred_id" because it is multi-valued
        self.fields[self.ROOT_PREDICATE_SOLR] = []
        for predicate in predicates:
            # We need the predicate's uuid to get its parents
            predicate_uuid = predicate[1]['owl:sameAs'].split('/')[-1]
            predicate_type = predicate[1]['type']
            parents = LinkRecursion(
                ).get_jsonldish_entity_parents(predicate_uuid)
            # Process parents
            link_predicate = False  # link predicates get special treatment
            for index, parent in enumerate(parents):
                if parent['slug'] == 'link':
                    link_predicate = True
                else:
                # add the label of the variable to the text field
                    self.fields['text'] += ' ' + parent['label'] + ' '
                # Treat the first parent in a special way
                if index == 0:
                    if link_predicate is False:
                        self.fields[self.ROOT_PREDICATE_SOLR].append(
                            self._concat_solr_string_value(
                                parent['slug'],
                                self._get_predicate_type_string(
                                    parent['type']),
                                parent['id'],
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
                    if link_predicate is False:
                        if solr_field_name not in self.fields:
                            self.fields[solr_field_name] = []
                        # Add slug and label as json values
                        self.fields[solr_field_name].append(
                            self._concat_solr_string_value(
                                parent['slug'],
                                self._get_predicate_type_string(
                                    parent['type']),
                                parent['id'],
                                parent['label'])
                            )
                    # If this is the last item, process the predicate values
                    if index == len(parents) - 1:
                        self._process_predicate_values(
                            parent['slug'],
                            predicate_type)

    def _get_context_path(self):
        if 'oc-gen:has-context-path' in self.oc_item.json_ld:
            return self.oc_item.json_ld[
                'oc-gen:has-context-path'].get('oc-gen:has-path-items')
        elif 'oc-gen:has-linked-context-path' in self.oc_item.json_ld:
            return self.oc_item.json_ld[
                'oc-gen:has-linked-context-path'].get('oc-gen:has-path-items')
        else:
            return None

    def _convert_slug_to_solr(self, slug):
        return slug.replace('-', '_')

    def _concat_solr_string_value(self, slug, type, id, label):
        id_part = id
        if 'http://opencontext.org' in id:
            if '/vocabularies/' not in id:
                id_part = id.split('http://opencontext.org')[1]
        return slug + '___' + type + '___' + \
            id_part + '___' + label

    def _convert_values_to_json(self, slug, id_uri, label):
        json_values = LastUpdatedOrderedDict()
        json_values['slug'] = slug
        json_values['id'] = id_uri
        json_values['label'] = label
        return json.dumps(json_values, ensure_ascii=False)

    def _process_core_solr_fields(self):
        self.fields['uuid'] = self.oc_item.uuid
        self.fields['slug_type_uri_label'] = self.make_slug_type_uri_label()
        self.fields['project_uuid'] = self.oc_item.project_uuid
        self.fields['published'] = self.oc_item.published.strftime(
            '%Y-%m-%dT%H:%M:%SZ'
            )   # verify
        self.fields['updated'] = datetime.datetime.utcnow().strftime(  # verify
            '%Y-%m-%dT%H:%M:%SZ')
        # default, can add as image media links discovered
        self.fields['image_media_count'] = 0
        # default, can add as other media links discovered
        self.fields['other_binary_media_count'] = 0
        # default, can add as doc links discovered
        self.fields['document_count'] = 0
        self.fields['sort_score'] = 0  # fix
        #default, adds to interest score once other fields determined
        self.fields['interest_score'] = 0
        self.fields['item_type'] = self.oc_item.item_type
        if 'dc-terms:title' in self.oc_item.json_ld:
            self.fields['text'] += self.oc_item.json_ld['dc-terms:title'] + ' \n'
        else:
            self.fields['text'] += self.oc_item.json_ld['label'] + ' \n'

    def make_slug_type_uri_label(self):
        """ makes a slug_type_uri_label field for solr """
        parts = []
        parts.append(self.oc_item.json_ld['slug'])
        if self.oc_item.item_type == 'predicates':
            if self.oc_item.json_ld['oc-gen:data-type']:
                # Looks up the predicte type mapped to Solr types
                parts.append(self._get_predicate_type_string(self.oc_item\
                                                                 .json_ld['oc-gen:data-type']))
            else:
                # Defaults to ID
                parts.append('id')
        else:
            parts.append('id')
        parts.append('/' + self.oc_item.item_type + '/' + self.oc_item.uuid)
        parts.append(self.oc_item.json_ld['label'])
        return '___'.join(parts)

    def _process_context_path(self):
        if self.context_path is not None:
            for index, context in enumerate(self.context_path):
                # treat the root in its own special way
                if index == 0:
                        self.fields['root___context_id'] = \
                            self.context_path[0]['slug'] + '___id___' + \
                            self.context_path[0]['id'].split(
                                'http://opencontext.org')[1] + '___' + \
                            self.context_path[0]['label']
                else:
                # for others, get the parent slug and generate a
                # dynamic field name
                    solr_field_name = \
                        self.context_path[index - 1]['slug'] + '___context_id'
                    # replace dashes with underscores because solr requires it
                    solr_field_name = self._convert_slug_to_solr(
                        solr_field_name
                        )
                    # add field name and values
                    self.fields[solr_field_name] = \
                        self.context_path[index]['slug'] + '___id___' + \
                        self.context_path[index]['id'].split(
                            'http://opencontext.org')[1] + '___' + \
                        self.context_path[index]['label']

    def _process_projects(self):
        """
        Creates a hierarchy of projects in the same way as a hierarchy of predicates
        """
        act_solr_field = self.ROOT_PROJECT_SOLR
        proj_rel = ProjectRels()
        parents = proj_rel.get_jsonldish_parents(self.oc_item.project_uuid)
        for index, parent in enumerate(parents):
            solr_value = self._concat_solr_string_value(parent['slug'],
                                                        'id',
                                                        parent['id'],
                                                        parent['label'])
            if act_solr_field not in self.fields:
                self.fields[act_solr_field] = []
            self.fields[act_solr_field].append(solr_value)
            act_solr_field = \
                self._convert_slug_to_solr(parent['slug']) + act_solr_field

    def _process_dc_terms(self):
        """
        Finds the project that this item is part of. If not part of a
        project, make the project slug the same as the item's own slug.
        """
        if 'dc-terms:coverage' in self.oc_item.json_ld:
            fname = 'dc_terms_coverage___pred_id'
            self.fields[fname] = []
            for meta in self.oc_item.json_ld['dc-terms:coverage']:
                self.fields['text'] += meta['label'] + '\n'
                item = self._concat_solr_string_value(
                    meta['slug'],
                    'id',
                    meta['id'],
                    meta['label'])
                self.fields[fname].append(item)
        if 'dc-terms:subject' in self.oc_item.json_ld:
            fname = 'dc_terms_subject___pred_id'
            self.fields[fname] = []
            for meta in self.oc_item.json_ld['dc-terms:subject']:
                self.fields['text'] += meta['label'] + '\n'
                item = self._concat_solr_string_value(
                    meta['slug'],
                    'id',
                    meta['id'],
                    meta['label'])
                self.fields[fname].append(item)
        if 'dc-terms:spatial' in self.oc_item.json_ld:
            fname = 'dc_terms_spatial___pred_id'
            self.fields[fname] = []
            for meta in self.oc_item.json_ld['dc-terms:spatial']:
                self.fields['text'] += meta['label'] + '\n'
                item = self._concat_solr_string_value(
                    meta['slug'],
                    'id',
                    meta['id'],
                    meta['label'])
                self.fields[fname].append(item)

    def _process_geo(self):
        """
        Finds geospatial point coordinates in GeoJSON features for indexing.
        Only 1 location of a given location type is allowed.
        """
        self.geo_specified = False
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
                try:
                    ref_type = feature['properties']['reference-type']
                    if ref_type == 'specified':
                        self.geo_specified = True
                except KeyError:
                    ref_type = False
                if ftype == 'Point' \
                    and (loc_type == 'oc-gen:discovey-location'
                         or loc_type == 'oc-gen:geo-coverage')\
                        and discovery_done is False:
                    try:
                        coords = feature['geometry']['coordinates']
                    except KeyError:
                        coords = False
                    if coords is not False:
                        gm = GlobalMercator()
                        self.fields['discovery_geotile'] = \
                            gm.geojson_coords_to_quadtree(coords, zoom)
                        # indexing with coordinates seperated by a space is in
                        # lon-lat order, like GeoJSON
                        self.fields['discovery_geolocation'] = \
                            str(coords[0]) + ' ' + str(coords[1])
                        discovery_done = True  # so we don't repeat getting
                                               # discovery locations
                if discovery_done:
                    break

    def _process_chrono(self):
        """ Finds chronological / date ranges in GeoJSON features for indexing.
        More than 1 date range per item is OK.
        """
        self.chrono_specified = False
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
                try:
                    ref_type = feature['when']['reference-type']
                    if ref_type == 'specified':
                        self.chrono_specified = True
                except KeyError:
                    ref_type = False
                if when_type == 'oc-gen:formation-use-life' \
                        and bad_time is False:
                    chrono_tile = ChronoTile()
                    if 'form_use_life_chrono_tile' not in self.fields:
                        self.fields['form_use_life_chrono_tile'] = []
                    if 'form_use_life_chrono_earliest' not in self.fields:
                        self.fields['form_use_life_chrono_earliest'] = []
                    if 'form_use_life_chrono_latest' not in self.fields:
                        self.fields['form_use_life_chrono_latest'] = []
                    self.fields['form_use_life_chrono_tile'].append(
                        chrono_tile.encode_path_from_bce_ce(
                            start, stop, '10M-'
                            )
                        )
                    self.fields['form_use_life_chrono_earliest'].append(start)
                    self.fields['form_use_life_chrono_latest'].append(stop)

    def _process_category(self):
        """ Finds category / type data ('class_uri' n the manifest table)
        For indexing as a type of predicate
        """
        if 'category' in self.oc_item.json_ld:
            for category in self.oc_item.json_ld['category']:
                # get the parent entities of the current category
                parents = LinkRecursion(
                    ).get_jsonldish_entity_parents(category)
                item_type_found = False
                active_predicate_field = False
                for index, parent in enumerate(parents):
                    # We're ignoring the 'slug' from the LinkRecursion parents
                    # Gets the last part of the URI
                    ptype = parent['id'].split('/')[-1]
                    # prefix_ptype = 'oc-gen-' + ptype
                    # consistent with other uses of slugs for solr fields
                    prefix_ptype = parent['slug']
                    if item_type_found is False:
                        if ptype == self.oc_item.item_type:
                            item_type_found = True
                    if active_predicate_field is not False:
                        solr_value = self._concat_solr_string_value(
                            prefix_ptype,
                            'id',
                            parent['id'],
                            parent['label']
                            )
                        if active_predicate_field not in self.fields:
                            self.fields[active_predicate_field] = []
                        self.fields[active_predicate_field].append(solr_value)
                    if item_type_found:
                        active_predicate_field = self._convert_slug_to_solr(
                            prefix_ptype) + '___pred_id'

    def _process_text_content(self):
        """ Gets text content for indexing
        """
        text_predicates = ['dc-terms:description',
                           'description',
                           'dc-terms:abstract',
                           'rdfs:comment',
                           'rdf:HTML']
        for pred in text_predicates:
            if pred in self.oc_item.json_ld:
                self.fields['text'] += self.oc_item.json_ld[pred] + '\n'

    def _process_persistent_ids(self):
        """ Gets stable identifiers for indexing
        """
        for id_pred in self.LD_IDENTIFIER_PREDICATES:
            if id_pred in self.oc_item.json_ld:
                for id_entity in self.oc_item.json_ld[id_pred]:
                    id_id = self.get_entity_id(id_entity)
                    if id_id is not False:
                        for act_root in self.PERSISTENT_ID_ROOTS:
                            if act_root in id_id:
                                if 'persistent_uri' not in self.fields:
                                    self.fields['persistent_uri'] = []
                                self.fields['persistent_uri'].append(id_id)
                                self.fields['text'] += id_id + '\n'

    def _process_interest_score(self):
        """ Calculates the 'interest score' for sorting items with more
        documentation / description to a higher rank.
        """
        self.fields['interest_score'] = 0
        type_scores = {'subjects': 0,
                       'media': 5,
                       'documents': 5,
                       'persons': 2,
                       'types': 2,
                       'predicates': 2,
                       'projects': 50,
                       'vocabularies': 25,
                       'tables': 25}
        if self.oc_item.item_type in type_scores:
            self.fields['interest_score'] += type_scores[
                self.oc_item.item_type
                ]
        for field_key, value in self.fields.items():
            if '__pred_' in field_key:
                self.fields['interest_score'] += 1
        self.fields['interest_score'] += len(self.fields['text']) / 100
        self.fields['interest_score'] += self.fields['image_media_count'] * 4
        self.fields['interest_score'] += self.fields[
            'other_binary_media_count'] * 5
        self.fields['interest_score'] += self.fields['document_count'] * 4
        if self.geo_specified:
        # geo data specified, more interesting
            self.fields['interest_score'] += 5
        if self.chrono_specified:
        # chrono data specified, more interesting
            self.fields['interest_score'] += 5

    def _process_associated_linkedata(self):
        """ Finds linked data to add to index
        """
        if '@graph' in self.oc_item.json_ld:
            for entity in self.oc_item.json_ld['@graph']:
                entity_id = self.get_entity_id(entity)
                if 'oc-pred:' in entity_id:
                    # a predicate with linked data
                    pred_slug_id = entity_id
                    pred_datatype = self.get_predicate_datatype(pred_slug_id)
                    pres_solr_datatype = self._get_predicate_type_string(pred_datatype)
                    obs_values = self.get_linked_predicate_values(pred_slug_id)  # values for predicate in observations
                    for equiv_pred in self.LD_EQUIVALENT_PREDICATES:
                        if equiv_pred in entity:
                            # a semantic equivalence predicate exists for this oc-pred
                            for equiv_entity in entity[equiv_pred]:
                                equiv_id = self.get_entity_id(equiv_entity)
                                parents = LinkRecursion().get_jsonldish_entity_parents(equiv_id)
                                act_solr_field = self.ROOT_LINK_DATA_SOLR
                                last_index = len(parents) - 1
                                for index, parent in enumerate(parents):
                                    if index == last_index:
                                        # use the predicates solr-field type, which may be numeric, date, string, or ID
                                        act_solr_datatype = pres_solr_datatype
                                    else:
                                        # use an id field type, since this is in a hierarchy that contains children
                                        act_solr_datatype = 'id'
                                    solr_value = self._concat_solr_string_value(parent['slug'],
                                                                                act_solr_datatype,
                                                                                parent['id'],
                                                                                parent['label'])
                                    if act_solr_field not in self.fields:
                                        self.fields[act_solr_field] = []
                                    self.fields[act_solr_field].append(solr_value)
                                    last_linked_pred_label = parent['label']
                                    act_solr_field = \
                                        self._convert_slug_to_solr(parent['slug'])\
                                        + '___pred_' \
                                        + act_solr_datatype
                                # since we ended the loop above by creating a solr field, let's make sure it's added to the solrdoc
                                self.fields['text'] += last_linked_pred_label + ': \n'
                                act_pred_root_act_solr_field = act_solr_field
                                if act_pred_root_act_solr_field not in self.fields:
                                    self.fields[act_pred_root_act_solr_field] = []
                                # --------------------------------
                                # Now we handle the objects of this predicate!
                                # 1. obs_values come from the item's observations,
                                # 2. we treat literals differently than URI objects, since URI objects maybe in a hierarchy
                                # --------------------------------
                                if pred_datatype != '@id':
                                    # objects of this predicate are literals
                                    for obs_val in obs_values:
                                        if isinstance(obs_val, dict):
                                            if pred_datatype in obs_val:
                                                self.fields[act_pred_root_act_solr_field].append(obs_val[pred_datatype])
                                                self.fields['text'] += obs_val[pred_datatype] + '\n'
                                        else:
                                            self.fields[act_pred_root_act_solr_field].append(obs_val)
                                            self.fields['text'] += str(obs_val) + '\n'
                                else:
                                    # objects of this predicate IDed by URIs
                                    for obs_val in obs_values:
                                        # gets the id for the observation object
                                        obs_object_id = self.get_entity_id(obs_val)
                                        # gets linked data equivalents of the obs-object-id
                                        use_objects = self.get_equivalent_linked_data(obs_object_id)
                                        if use_objects is False:
                                            # no linked data equivalents found, so make a list w. 1 item
                                            use_objects = [{'id': obs_object_id}]
                                        for use_obj in use_objects:
                                            # make sure the active solr field is reset to be from
                                            # the last equivalent predicates. important if we're looping
                                            # through multiple use_objects
                                            act_solr_field = act_pred_root_act_solr_field
                                            # URI objects can be in hierarchies, look for these!
                                            object_id = self.get_entity_id(use_obj)
                                            parents = LinkRecursion().get_jsonldish_entity_parents(object_id)
                                            for index, parent in enumerate(parents):
                                                solr_value = self._concat_solr_string_value(parent['slug'],
                                                                                            'id',
                                                                                            parent['id'],
                                                                                            parent['label'])
                                                if act_solr_field not in self.fields:
                                                    self.fields[act_solr_field] = []
                                                self.fields[act_solr_field].append(solr_value)
                                                last_object_label = parent['label']
                                                act_solr_field = \
                                                    self._convert_slug_to_solr(parent['slug']) \
                                                    + '___' + act_solr_field
                                            self.fields['text'] += last_object_label + '\n'

    def get_linked_predicate_values(self, predicate_slug_id):
        """ Gets all the values usef with a certain predicate
        """
        output = False
        if 'oc-gen:has-obs' in self.oc_item.json_ld:
            for obs in self.oc_item.json_ld['oc-gen:has-obs']:
                obs_ok = True  # default, assume the observation is OK
                if 'oc-gen:obsStatus' in obs:
                    if obs['oc-gen:obsStatus'] != 'active':
                        # observation should be ignored for indexing
                        obs_ok = False
                if predicate_slug_id in obs and obs_ok:
                    if output is False:
                        output = []
                    output += obs[predicate_slug_id]
        return output

    def get_entity_linked_data(self, entity_id):
        """ Finds linked data to add to index
        """
        output = False
        if '@graph' in self.oc_item.json_ld:
            for entity in self.oc_item.json_ld['@graph']:
                act_entity_id = self.get_entity_id(entity) 
                if act_entity_id == entity_id:
                    output = entity
                    break
        return output

    def get_equivalent_linked_data(self, oc_id):
        """ Finds linked data asserted to be equivalent to the oc_id parameter """
        output = False
        entity = self.get_entity_linked_data(oc_id)
        if entity is not False:
            for equiv_pred in self.LD_EQUIVALENT_PREDICATES:
                if equiv_pred in entity:
                    if output is False:
                        output = []
                    output += entity[equiv_pred]  # adds list of equivalent entities
        return output

    def get_predicate_datatype(self, predicate_slug_id):
        """ Finds linked data to add to index
        """
        output = False
        if '@context' in self.oc_item.json_ld:
            for act_entity_id, entity in self.oc_item.json_ld['@context'].items():
                if act_entity_id == predicate_slug_id and 'type' in entity:
                    output = entity['type']
                    break
        return output

    def get_entity_id(self, entity_dict):
        """ Gets the ID from an entity dictionary obj """
        if 'id' in entity_dict:
            output = entity_dict['id']
        elif '@id' in entity_dict:
            output = entity_dict['@id']
        else:
            output = False
        return output
