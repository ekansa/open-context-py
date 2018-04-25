import datetime
import json
from django.conf import settings
from opencontext_py.libs.languages import Languages
from django.utils.encoding import force_text
from opencontext_py.libs.isoyears import ISOyears
from opencontext_py.libs.general import LastUpdatedOrderedDict, DCterms
from opencontext_py.libs.rootpath import RootPath
from opencontext_py.apps.ocitems.ocitem.models import OCitem
from opencontext_py.apps.entities.entity.models import Entity
from opencontext_py.apps.ldata.linkannotations.recursion import LinkRecursion
from opencontext_py.apps.ldata.linkannotations.equivalence import LinkEquivalence
from opencontext_py.apps.ocitems.projects.metadata import ProjectRels
from opencontext_py.apps.ocitems.queries.geochrono import GeoChronoQueries
from opencontext_py.libs.chronotiles import ChronoTile
from opencontext_py.libs.globalmaptiles import GlobalMercator
from opencontext_py.apps.entities.uri.models import URImanagement


class SolrDocument:
    '''
    Defines the Solr Document objects that the crawler will crawl. Solr
    fields are stored in a Solr Document's "fields" property.

from opencontext_py.apps.indexer.solrdocument import SolrDocument
uuid = '182646e0-15cb-49f0-a180-84fa35709959'
sd_obj = SolrDocument(uuid)
sd_obj.process_item()
sd_a = sd_obj.fields
sd_a['text']
sd_a['discovery_geotile']
sd_a['form_use_life_chrono_earliest']
uuid = 'f266d43c-cdea-465c-9135-8c39b7ba6cd9'
sd_obj = SolrDocument(uuid)
sd_obj.process_item()
sd_b = sd_obj.fields
    '''

    # the list below defines predicates used for semantic equivalence in indexing
    # linked data
    LD_EQUIVALENT_PREDICATES = ['skos:closeMatch',
                                'skos:exactMatch',
                                'owl:sameAs',
                                'foaf:isPrimaryTopicOf']

    LD_IDENTIFIER_PREDICATES = ['owl:sameAs',
                                'foaf:isPrimaryTopicOf']

    LD_DIRECT_PREDICATES = ['http://nomisma.org/ontology#hasTypeSeriesItem',
                            'nmo:hasTypeSeriesItem',
                            'http://erlangen-crm.org/current/P2_has_type',
                            'cidoc-crm:P2_has_type']

    PERSISTENT_ID_ROOTS = ['doi.org',
                           'n2t.net/ark:/',
                           'orcid.org']

    ALL_CONTEXT_SOLR = 'obj_all___context_id'
    ROOT_CONTEXT_SOLR = 'root___context_id'
    ROOT_PREDICATE_SOLR = 'root___pred_id'
    ROOT_LINK_DATA_SOLR = 'ld___pred_id'
    ROOT_PROJECT_SOLR = 'root___project_id'
    FILE_SIZE_SOLR = 'filesize___pred_numeric'
    FILE_MIMETYPE_SOLR = 'mimetype___pred_id'
    RELATED_SOLR_FIELD_PREFIX = 'rel--'
    
    MISSING_PREDICATE_TYPES = [
        False,
        None,
        '',
        'None',
        'False'
    ]

    def __init__(self, uuid):
        '''
        Using our Python JSON-LD and other info provided in OCitem,
        build up dictionary of solr fields to index.
        '''
        # prefix for related solr_documents
        self.field_prefix = ''
        # do_related means that we're making solr fields for
        # a related item (a subject linked to a media resource)
        # this makes only some solr fields
        self.do_related = False
        self.max_file_size = 0
        # First get core data structures
        self.oc_item = OCitem().get_item(uuid)
        self.manifest = self.oc_item.manifest
        self.context_path = self._get_context_path()
        # Store values here
        self.fields = {}
        self.fields['text'] = ''  # Start of full-text field
        self.fields['human_remains'] = 0  # default, item is not about human remains.
        self.geo_specified = False
        self.chrono_specified = False
        self.max_geo_zoom = 30  # we can lower this if we want to force low precision on mapping

    def process_item(self):
        # Start processing and adding values...
        if self.do_related is False:
            self.field_prefix = ''
            self._process_core_solr_fields()
            self._process_category()
            self._process_context_path()
            self._process_predicates()
            self._process_geo()
            self._process_chrono()
            self._process_text_content()
            self._process_dc_terms()
            self._process_dc_authorship()
            self._process_projects()
            self._process_persistent_ids()
            self._process_associated_linkedata()
            self.process_equivalent_linked_data()
            self.process_direct_linked_data()
            self.process_media_fields()
            self._process_interest_score()
            self.process_related_subjects_for_media()
            self.ensure_text_ok()
        else:
            # making a solr-document that is related
            # to a primary solr-document
            # field_prefix differentiates solr fields from a
            # related item from solr fields describing the primary item
            self.field_prefix = self.RELATED_SOLR_FIELD_PREFIX
            self._process_category()
            self._process_predicates()
            self._process_text_content()
            self._process_associated_linkedata()

    def ensure_text_ok(self):
        """ makes sure the text is solr escaped """
        self.fields['text'] = force_text(self.fields['text'],
                                         encoding='utf-8',
                                         strings_only=False,
                                         errors='surrogateescape')

    def _process_predicate_values(self, predicate_slug, predicate_type):
        # First generate the solr field name
        thumbnail_uri = None
        iiif_json_uri = None
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
                    if solr_field_name not in self.fields:
                        self.fields[solr_field_name] = []
                    if predicate_type in predicate_type in self.MISSING_PREDICATE_TYPES:
                        # if missing a predicate type index as a string
                        predicate_type = 'xsd:string'
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
                            act_solr_field = solr_field_name
                            parents = LinkRecursion(
                                ).get_jsonldish_entity_parents(
                                value['id']
                                )
                            all_obj_solr_field = 'obj_all___' + act_solr_field
                            for parent in parents:
                                act_solr_value = \
                                    self._concat_solr_string_value(
                                        parent['slug'],
                                        self._get_predicate_type_string(
                                            parent['type']),
                                        parent['id'],
                                        parent['label']
                                    )
                                act_slug = parent['slug']
                                self.fields['text'] += ' ' + \
                                    str(parent['label']) + ' '
                                # add the solr id field value and fq field slug
                                self.add_id_field_fq_field_values(act_solr_field,
                                                                  act_solr_value,
                                                                  act_slug)
                                # so all items in the hiearchy are present in the
                                # and can be queried, even if you don't know the parent
                                self.add_id_field_fq_field_values(all_obj_solr_field,
                                                                  act_solr_value,
                                                                  act_slug)
                                # make the next solr field for the next iteration through the loop
                                act_solr_field = self._convert_slug_to_solr(
                                    parent['slug']) + '___' + solr_field_name
                        else:
                            # case of a linking relation, don't bother looking
                            # up hierarchies or recording as a solr field, but
                            # check for image, other media, and document counts
                            if self.do_related is False:
                                # only do this if not solr-doc related to media
                                if 'media' in value['id'] \
                                        and 'image' in value['type']:
                                    self.fields['image_media_count'] += 1
                                elif 'media' in value['id'] \
                                        and 'image' not in value['type']:
                                     # other types of media
                                    self.fields['other_binary_media_count'] += 1
                                elif 'documents' in value['id']:
                                    self.fields['document_count'] += 1
                                if 'oc-gen:thumbnail-uri' in value and thumbnail_uri is None:
                                    # we only do this once, get the first thumbnail to store as a thumbail in solr
                                    thumbnail_uri = value['oc-gen:thumbnail-uri']
                                    self.fields['thumbnail_uri'] = thumbnail_uri
                                if 'oc-gen:iiif-json-uri' in value and iiif_json_uri is None:
                                    # we only do this once, get the first iiif-json in solr
                                    iiif_json_uri = value['oc-gen:iiif-json-uri']
                                    self.fields['iiif_json_uri'] = iiif_json_uri
                            self.fields['text'] += str(value['label']) + ' '
                    elif predicate_type in [
                        'xsd:integer', 'xsd:double', 'xsd:boolean'
                            ]:
                        self.fields[solr_field_name].append(value)
                    elif predicate_type == 'xsd:date':
                        self.fields[solr_field_name].append(value +
                                                            'T00:00:00Z')
                    elif predicate_type == 'xsd:string':
                        if isinstance(value, dict):
                            if 'xsd:string' in value:
                                # only do this if we see the string key
                                lang_obj = Languages()
                                act_str = lang_obj.get_all_value_str(value['xsd:string'])
                                self.fields['text'] += str(act_str) + ' \n'
                                self.fields[solr_field_name].append(act_str)
                        else:
                            self.fields['text'] += str(value) + ' \n'
                            self.fields[solr_field_name].append(str(value))
                    else:
                        raise Exception("Error: Could not get predicate value")
                self.fields['text'] += ' \n'

    def add_id_field_fq_field_values(self, solr_id_field, concat_val, slug):
        """ adds values for an id field, and the complementary
            slug value for the related _fq field
        """
        if isinstance(solr_id_field, str):
            # add the main solr id field if not present,
            # then append the concat_val
            if isinstance(concat_val, str):
                if solr_id_field not in self.fields:
                    self.fields[solr_id_field] = []
                if len(concat_val) > 0 and concat_val not in self.fields[solr_id_field]:
                    # only add it if we don't already have it
                    self.fields[solr_id_field].append(concat_val)
            # add the solr id field's _fq field if not present,
            # then append the slug value
            solr_id_field_fq = solr_id_field + '_fq'
            if isinstance(slug, str):
                if len(slug) > 0:
                    if solr_id_field_fq not in self.fields:
                        self.fields[solr_id_field_fq] = []
                    # add the field prefix if needed
                    slug = self.field_prefix + slug
                    if slug not in self.fields[solr_id_field_fq]:
                        # only add it if we don't already have it
                        self.fields[solr_id_field_fq].append(slug)

    def _get_predicate_type_string(self, predicate_type,
                                   prefix=''):
        '''
        Defines whether our dynamic solr fields names for
        predicates end with ___pred_id, ___pred_numeric, etc.
        '''
        if predicate_type in ['@id', 'id', 'types', False]:
            return prefix + 'id'
        elif predicate_type in ['xsd:integer', 'xsd:double', 'xsd:boolean']:
            return prefix + 'numeric'
        elif predicate_type == 'xsd:string':
            return prefix + 'string'
        elif predicate_type == 'xsd:date':
            return prefix + 'date'
        elif predicate_type in self.MISSING_PREDICATE_TYPES:
            return prefix + 'string'
        else:
            raise Exception("Error: Unknown predicate type: " + str(predicate_type))

    def _process_predicates(self):
        # Get list of predicates
        predicates = (item for item in self.oc_item.json_ld[
            '@context'][2].items() if item[0].startswith('oc-pred:'))
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
                    self.fields['text'] += ' ' + str(parent['label']) + ' '
                # Treat the first parent in a special way
                if index == 0:
                    if link_predicate is False:
                        act_solr_value = self._concat_solr_string_value(
                            parent['slug'],
                            self._get_predicate_type_string(parent['type']),
                            parent['id'],
                            parent['label']
                        )
                        act_slug = parent['slug']
                        self.add_id_field_fq_field_values(self.ROOT_PREDICATE_SOLR,
                                                          act_solr_value,
                                                          act_slug)
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
                        act_solr_value = self._concat_solr_string_value(
                            parent['slug'],
                            self._get_predicate_type_string(parent['type']),
                            parent['id'],
                            parent['label']
                        )
                        act_slug = parent['slug']
                        self.add_id_field_fq_field_values(solr_field_name,
                                                          act_solr_value,
                                                          act_slug)
                    # If this is the last item, process the predicate values
                    if index == len(parents) - 1:
                        self._process_predicate_values(
                            parent['slug'],
                            predicate_type)

    def _get_context_path(self):
        output = None
        context = False
        if 'oc-gen:has-context-path' in self.oc_item.json_ld:
            context = self.oc_item.json_ld['oc-gen:has-context-path']
        elif 'oc-gen:has-linked-context-path' in self.oc_item.json_ld:
            context = self.oc_item.json_ld['oc-gen:has-linked-context-path']
        if context is not False:
            output = context['oc-gen:has-path-items']
        return output

    def _convert_slug_to_solr(self, slug):
        slug = self.field_prefix + slug
        return slug.replace('-', '_')

    def _concat_solr_string_value(self, slug, type, id, label):
        id_part = id
        if 'http://opencontext.org' in id:
            if '/vocabularies/' not in id:
                id_part = id.split('http://opencontext.org')[1]
        slug = self.field_prefix + slug
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
        if self.oc_item.published is not None:
            self.fields['published'] = self.oc_item.published.strftime(
                '%Y-%m-%dT%H:%M:%SZ'
                ) # verify
        else:
            self.fields['published'] = datetime.date(2007, 1, 1).strftime(
                '%Y-%m-%dT%H:%M:%SZ') # verify
        self.fields['updated'] = datetime.datetime.utcnow().strftime(  # verify
            '%Y-%m-%dT%H:%M:%SZ')
        # default, can add as image media links discovered
        self.fields['image_media_count'] = 0
        # default, can add as other media links discovered
        self.fields['other_binary_media_count'] = 0
        # default, can add as doc links discovered
        self.fields['document_count'] = 0
        self.fields['sort_score'] = float('.' + self.manifest.sort.replace('-', ''))
        #default, adds to interest score once other fields determined
        self.fields['interest_score'] = 0
        self.fields['item_type'] = self.oc_item.item_type
        if 'dc-terms:title' in self.oc_item.json_ld:
            self.fields['text'] += self.oc_item.json_ld['dc-terms:title'] + ' \n'
        else:
            self.fields['text'] += str(self.oc_item.json_ld['label']) + ' \n'
        if 'skos:altLabel' in self.oc_item.json_ld:
            # get the multilingual skos altLabels for this item
            lang_obj = Languages()
            self.fields['text'] += lang_obj.get_all_value_str(self.oc_item.json_ld['skos:altLabel'])

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
                act_solr_value = \
                    self._concat_solr_string_value(
                        self.context_path[index]['slug'],
                        'id',
                        self.context_path[index]['id'].split('http://opencontext.org')[1],
                        self.context_path[index]['label'])
                act_slug = self.context_path[index]['slug']
                self.add_id_field_fq_field_values(self.ALL_CONTEXT_SOLR,
                                                  act_solr_value,
                                                  act_slug)
                if index == 0:
                    self.add_id_field_fq_field_values(self.ROOT_CONTEXT_SOLR,
                                                      act_solr_value,
                                                      act_slug)
                else:
                    # for others, get the parent slug and generate a
                    # dynamic field name
                    solr_field_name = \
                        self.context_path[index - 1]['slug'] + '___context_id'
                    # replace dashes with underscores because solr requires it
                    act_solr_field = self._convert_slug_to_solr(
                        solr_field_name
                        )
                    # add field name and values
                    self.add_id_field_fq_field_values(act_solr_field,
                                                      act_solr_value,
                                                      act_slug)

    def _process_projects(self):
        """
        Creates a hierarchy of projects in the same way as a hierarchy of predicates
        """
        solr_field_name = self.ROOT_PROJECT_SOLR
        proj_rel = ProjectRels()
        parents = proj_rel.get_jsonldish_parents(self.oc_item.project_uuid)
        for index, parent in enumerate(parents):
            act_solr_value = self._concat_solr_string_value(parent['slug'],
                                                            'id',
                                                            parent['id'],
                                                            parent['label'])
            act_slug = parent['slug']
            self.add_id_field_fq_field_values(solr_field_name,
                                              act_solr_value,
                                              act_slug)
            # make the new solr_field_name for the next iteration of the loop
            solr_field_name = \
                self._convert_slug_to_solr(parent['slug'])\
                + '___project_id'

    
    def _process_dc_terms(self):
        """
        Finds dublin-core metadata about an item (other than authorship)
        """
        thumbnail_uri = None
        iiif_json_uri = None
        for dc_predicate, fname in DCterms.DC_META_PREDICATES.items():
            if dc_predicate in self.oc_item.json_ld:
                self.fields[fname] = []
                for meta in self.oc_item.json_ld[dc_predicate]:
                    if not ('http://' in meta['id']\
                       or 'https://' in meta['id'])\
                       and 'rdfs:isDefinedBy' in meta:
                        # special case for inferred relationship
                        meta['id'] = meta['rdfs:isDefinedBy']
                    if 'label' in meta and 'id' in meta:
                        self.fields['text'] += str(meta['label']) + '\n'
                        self.fields['text'] += meta['id'] + '\n'
                    if dc_predicate == 'foaf:depection':
                        if 'type' in meta:
                            if meta['type'] == 'oc-gen:hero' and thumbnail_uri is None:
                                # we only do this once, get the first hero to store as a thumbail in solr
                                thumbnail_uri = meta['id']
                                self.fields['thumbnail_uri'] = thumbnail_uri
                        if 'oc-gen:iiif-json-uri' in meta and iiif_json_uri is None:
                            # we only do this once, get the first iiif-json in solr
                            iiif_json_uri = meta['oc-gen:iiif-json-uri']
                            self.fields['iiif_json_uri'] = iiif_json_uri
                    elif 'opencontext.org/tables/' not in meta['id'] and 'label' in meta:
                        # do not index table references in this way
                        """
                        item = self._concat_solr_string_value(
                            meta['slug'],
                            'id',
                            meta['id'],
                            meta['label'])
                        self.fields[fname].append(item)
                        self.process_object_uri(meta['id'])
                        """
                        self.process_ld_predicate_objects(dc_predicate,
                                                          '@id',
                                                          [meta])

    def _process_dc_authorship(self):
        """
        Finds dublin-core authorship metadata about an item
        """
        for dc_predicate, solr_field_name in DCterms.DC_AUTHOR_PREDICATES.items():
            if dc_predicate in self.oc_item.json_ld:
                for meta in self.oc_item.json_ld[dc_predicate]:
                    if not ('http://' in meta['id']\
                       or 'https://' in meta['id'])\
                       and 'rdfs:isDefinedBy' in meta:
                        # special case for inferred relationship
                        meta['id'] = meta['rdfs:isDefinedBy']
                    if 'label' in meta and 'id' in meta and 'slug' in meta:
                        self.fields['text'] += str(meta['label']) + '\n'
                        self.fields['text'] += meta['id'] + '\n'
                        act_solr_value = self._concat_solr_string_value(
                            meta['slug'],
                            'id',
                            meta['id'],
                            meta['label'])
                        act_slug = meta['slug']
                        self.add_id_field_fq_field_values(solr_field_name,
                                                          act_solr_value,
                                                          act_slug)
                        self.process_object_uri(meta['id'])

    def _process_geo(self):
        """
        Finds geospatial point coordinates in GeoJSON features for indexing.
        Only 1 location of a given location type is allowed.
        """
        if self.oc_item.item_type in ['types', 'predicates']:
            # get geospatial data inferred from the project
            self.geo_specified = False
            gcq = GeoChronoQueries()
            geo_meta = gcq.get_project_geo_meta(self.oc_item.project_uuid)
            if isinstance(geo_meta, list):
                if len(geo_meta) > 0:
                    geo = geo_meta[0]
                    gm = GlobalMercator()
                    lat_ok = gm.validate_geo_coordinate(geo.latitude, 'lat')
                    lon_ok = gm.validate_geo_coordinate(geo.longitude, 'lon')
                    if lat_ok and lon_ok:
                        self.geo_specified = True
                        coords = str(geo.latitude) + ',' + str(geo.longitude)
                        if geo.specificity < 0:
                            zoom = geo.specificity * -1
                        elif geo.specificity > 0:
                            zoom = geo.specificity
                        else:
                            zoom = False
                        gm = GlobalMercator()
                        tile = gm.lat_lon_to_quadtree(geo.latitude,
                                                      geo.longitude,
                                                      zoom)
                        if len(tile) > (zoom - 2):
                            self.fields['discovery_geotile'] = tile
                        self.fields['discovery_geolocation'] = coords
        else:
            # get the geospatial data from the geojson feature
            self.process_geo_from_json()

    def process_geo_from_json(self):
        """ abstraction for just getting the geo-coodinates from JSON,
            enables use of project GeoJSON for indexing 'types' and 'predicates'
            items
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
                try:
                    # is this contained in a parent polygon?
                    contained_in_region = feature['properties']['contained-in-region']
                except KeyError:
                    contained_in_region = False
                if self.geo_specified:
                    if loc_type in ['oc-gen:discovey-location', 'oc-gen:geo-coverage'] \
                       and ftype != 'Point' and 'slug_type_uri_label' in self.fields:
                        # we have a specified location for a region (not a point)
                        self.fields['disc_geosource'] = self.fields['slug_type_uri_label']
                elif loc_type in ['oc-gen:discovey-location', 'oc-gen:geo-coverage'] \
                     and contained_in_region:
                    # we've got an infered location, check to see if
                    # we have a location contained in a region (polygon feature)
                    in_region_dict = {}
                    try:
                        in_region_dict['label'] = feature['properties']['reference-label']
                    except KeyError:
                        in_region_dict['label'] = None
                    try:
                        in_region_dict['uri'] = feature['properties']['reference-uri']
                    except KeyError:
                        in_region_dict['uri'] = None
                    try:
                        in_region_dict['slug'] = feature['properties']['reference-slug']
                    except KeyError:
                        in_region_dict['slug'] = None
                    if isinstance(in_region_dict['label'], str) \
                       and isinstance(in_region_dict['uri'], str)\
                       and isinstance(in_region_dict['slug'], str):
                        # ok we have the data needed to make a reference to a polygon discovery
                        # region for that's the inferred location for this item
                        self.fields['disc_geosource'] = self._concat_solr_string_value(in_region_dict['slug'],
                                                                                       'id',
                                                                                       in_region_dict['uri'],
                                                                                       in_region_dict['label'])
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
                        if zoom > self.max_geo_zoom:
                            zoom = self.max_geo_zoom
                        tile = gm.geojson_coords_to_quadtree(coords, zoom)
                        if len(tile) > (zoom - 2):
                            self.fields['discovery_geotile'] = \
                                gm.geojson_coords_to_quadtree(coords, zoom)
                            # indexing with coordinates seperated by a space is in
                            # lat-lon order, the reverse of GeoJSON because
                            # solr spatial fields expect a lat-lon order
                            lat_ok = gm.validate_geo_coordinate(coords[1], 'lat')
                            lon_ok = gm.validate_geo_coordinate(coords[0], 'lon')
                        else:
                            lat_ok = False
                            lon_ok = False
                        if lat_ok and lon_ok:
                            self.fields['discovery_geolocation'] = \
                                str(coords[1]) + ',' + str(coords[0])
                        else:
                            print('Geo problem in: ' + self.oc_item.uuid + ' ' + str(coords[0]) + ' ' + str(coords[1]))
                        discovery_done = True  # so we don't repeat getting
                                               # discovery locations

    def validate_geo_coordinate(self, coordinate, coord_type):
        """ validates a geo-spatial coordinate """
        is_valid = False
        try:
            fl_coord = float(coordinate)
        except ValueError:
            fl_coord = False
        if fl_coord is not False:
            if 'lat' in coord_type:
                if fl_coord <= 90 and\
                   fl_coord >= -90:
                    is_valid = True
            elif 'lon' in coord_type:
                if fl_coord <= 180 and\
                   fl_coord >= -180:
                    is_valid = True
        return is_valid

    def _process_chrono(self):
        """ Finds chronological / date ranges in GeoJSON features for indexing.
        More than 1 date range per item is OK.
        """
        if self.oc_item.item_type in ['types', 'predicates']:
            # get geospatial data inferred from the project
            self.geo_specified = False
            gcq = GeoChronoQueries()
            if self.oc_item.item_type  == 'types':
                # get a date range dict, using a method for types
                date_range = gcq.get_type_date_range(self.oc_item.uuid,
                                                     self.oc_item.project_uuid)
            else:
                # get a date range dict, using the method for the project
                date_range = gcq.get_project_date_range(self.oc_item.project_uuid)
            if isinstance(date_range, dict):
                # we have date information we can index!!
                self.chrono_specified = True
                chrono_tile = ChronoTile()
                if 'form_use_life_chrono_tile' not in self.fields:
                    self.fields['form_use_life_chrono_tile'] = []
                if 'form_use_life_chrono_earliest' not in self.fields:
                        self.fields['form_use_life_chrono_earliest'] = []
                if 'form_use_life_chrono_latest' not in self.fields:
                    self.fields['form_use_life_chrono_latest'] = []
                self.fields['form_use_life_chrono_tile'].append(
                        chrono_tile.encode_path_from_bce_ce(
                            date_range['start'], date_range['stop'], '10M-'
                            )
                        )
                self.fields['form_use_life_chrono_earliest'].append(date_range['start'])
                self.fields['form_use_life_chrono_latest'].append(date_range['stop'])
        else:
            # look for the chronological information in the GeoJSON
            self.process_chrono_from_json()
            chrono_tile = ChronoTile()
        
    def process_chrono_from_json(self):
        """ Finds chronological / date ranges in GeoJSON features for indexing.
            More than 1 date range per item is OK.
        """
        self.chrono_specified = False
        if 'features' in self.oc_item.json_ld:
            for feature in self.oc_item.json_ld['features']:
                bad_time = False
                try:
                    # time is in ISO 8601 time
                    iso_start = feature['when']['start']
                except KeyError:
                    bad_time = True
                try:
                    # time is in ISO 8601 time
                    iso_stop = feature['when']['stop']
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
                    # convert GeoJSON-LD ISO 8601 to numeric
                    start = ISOyears().make_float_from_iso(iso_start)
                    stop = ISOyears().make_float_from_iso(iso_stop)
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
    
    def process_chrono_from_rel_events(self):
        """ get chronological metadata for 'predicate' and 'type' items
        
        """
        pass

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
                        act_solr_value = self._concat_solr_string_value(
                            prefix_ptype,
                            'id',
                            parent['id'],
                            parent['label']
                        )
                        self.add_id_field_fq_field_values(active_predicate_field,
                                                          act_solr_value,
                                                          prefix_ptype)
                    if item_type_found:
                        active_predicate_field = self._convert_slug_to_solr(
                                prefix_ptype) + '___pred_id'

    def _process_text_content(self):
        """ Gets text content for indexing
        """
        for pred in settings.TEXT_CONTENT_PREDICATES:
            if pred in self.oc_item.json_ld:
                lang_obj = Languages()
                self.fields['text'] += lang_obj.get_all_value_str(self.oc_item.json_ld[pred]) + '\n'

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
                                self.process_object_uri(id_id)
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
        if self.max_file_size > 0:
            self.fields['interest_score'] += self.max_file_size / 10000

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
                                self.process_ld_predicate_objects(equiv_id, pred_datatype, obs_values)

    def process_ld_predicate_objects(self, predicate_uri, pred_datatype, obs_values):
        """ processes a LD predicate uri and the associated objects for that URI
        """
        pres_solr_datatype = self._get_predicate_type_string(pred_datatype)
        parents = LinkRecursion().get_jsonldish_entity_parents(predicate_uri)
        act_solr_field = self.ROOT_LINK_DATA_SOLR
        last_index = len(parents) - 1
        for index, parent in enumerate(parents):
            if index == last_index:
                # use the predicates solr-field type, which may be numeric, date, string, or ID
                act_solr_datatype = pres_solr_datatype
            else:
                # use an id field type, since this is in a hierarchy that contains children
                act_solr_datatype = 'id'
            act_solr_value = self._concat_solr_string_value(parent['slug'],
                                                            act_solr_datatype,
                                                            parent['id'],
                                                            parent['label'])
            act_slug = parent['slug']
            self.add_id_field_fq_field_values(act_solr_field,
                                              act_solr_value,
                                              act_slug)
            last_linked_pred_label = parent['label']
            last_linked_pred_uri = parent['id']
            act_solr_field = \
                self._convert_slug_to_solr(parent['slug'])\
                + '___pred_' \
                + act_solr_datatype
        # since we ended the loop above by creating a solr field, let's make sure it's added to the solrdoc
        self.fields['text'] += last_linked_pred_label + ': \n'
        act_pred_root_act_solr_field = act_solr_field
        # --------------------------------
        # Now we handle the objects of this predicate!
        # 1. obs_values come from the item's observations,
        # 2. we treat literals differently than URI objects, since URI objects maybe in a hierarchy
        # --------------------------------
        if pred_datatype != '@id' and isinstance(obs_values, list):
            # objects of this predicate are literals
            if act_pred_root_act_solr_field not in self.fields:
                self.fields[act_pred_root_act_solr_field] = []
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
            if isinstance(obs_values, list):
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
                        last_object_uri = False
                        last_object_label = ''
                        act_solr_field = act_pred_root_act_solr_field
                        #-------------------------------
                        # Now make a solr field for ALL the objects (parents, childred)
                        # using this predicate
                        all_obj_solr_field = 'obj_all___' + act_pred_root_act_solr_field
                        # URI objects can be in hierarchies, look for these!
                        object_id = self.get_entity_id(use_obj)
                        parents = LinkRecursion().get_jsonldish_entity_parents(object_id)
                        for index, parent in enumerate(parents):
                            act_slug = parent['slug']
                            act_solr_value = self._concat_solr_string_value(parent['slug'],
                                                                            'id',
                                                                            parent['id'],
                                                                            parent['label'])
                            act_slug = parent['slug']
                            last_object_uri = parent['id']
                            if parent['ld_object_ok']:
                                # only add this if it's OK for linked data use
                                # in presenting a facet
                                self.add_id_field_fq_field_values(act_solr_field,
                                                                  act_solr_value,
                                                                  act_slug)
                            #-------------------------------
                            # This way, you don't need to know a parent to search
                            # for a child. Since facets aren't made with this,
                            # it's OK for on-linked-data-ok objects to be used
                            #-------------------------------
                            self.add_id_field_fq_field_values(all_obj_solr_field,
                                                              act_solr_value,
                                                              act_slug)
                            if parent['id'] not in self.fields['text']:
                                self.fields['text'] += parent['id'] + ' '
                                self.fields['text'] += str(parent['label']) + '\n'
                            # now make the next act_solr_field for the next iteration of the loop
                            act_solr_field = \
                                self._convert_slug_to_solr(parent['slug']) \
                                + '___' + act_pred_root_act_solr_field
                        if last_object_uri is not False:
                            self.process_object_uri(last_object_uri)

    def process_equivalent_linked_data(self):
        """ Types are useful for entity reconciliation
            this checks for linked data associated
            with a type
        """
        for equiv_uri in self.LD_EQUIVALENT_PREDICATES:
            if equiv_uri in self.oc_item.json_ld \
               and 'foaf' not in equiv_uri:
                # for now, default to a close match
                solr_field_name = 'skos_closematch___pred_id'
                all_solr_field_name = 'obj_all___skos_closematch___pred_id'
                for entity in self.oc_item.json_ld[equiv_uri]:
                    if ('http://' in entity['id'] \
                       or 'https://' in entity['id']):
                        # only do this if this is NOT an open context URI
                        if 'label' in entity:
                            self.fields['text'] += str(entity['label']) + '\n'
                        self.fields['text'] += entity['id'] + '\n'
                        if 'label' in entity and 'slug' in entity:
                            # first make sure we've got the skos:closeMatch predicated added to the root
                            # linked data solr field
                            act_solr_value = self._concat_solr_string_value(
                                    'skos-closematch',
                                    'id',
                                    'http://www.w3.org/2004/02/skos/core#closeMatch',
                                    'Close Match'
                            )
                            act_slug = 'skos-closematch'
                            self.add_id_field_fq_field_values(self.ROOT_LINK_DATA_SOLR,
                                                              act_solr_value,
                                                              act_slug)
                            # now add the object item for that field
                            act_solr_value = self._concat_solr_string_value(
                                entity['slug'],
                                'id',
                                entity['id'],
                                entity['label']
                            )
                            act_slug = entity['slug']
                            self.add_id_field_fq_field_values(solr_field_name,
                                                              act_solr_value,
                                                              act_slug)
                            # add the all_solr_field name values
                            self.add_id_field_fq_field_values(all_solr_field_name,
                                                              act_solr_value,
                                                              act_slug)
                            # add to the general list of object entities
                            self.process_object_uri(entity['id'])
                            if self.oc_item.item_type == 'types' \
                               or self.oc_item.item_type == 'predicates':
                                # we to make the hierarchy of broader concepts indexed for
                                # keyword searches.
                                parents = LinkRecursion().get_jsonldish_entity_parents(entity['id'])
                                if len(parents) > 1:
                                    for parent in parents[0:-1]:
                                        self.fields['text'] += ' Broader concept: ' + \
                                            str(parent['label']) + ' '
                                        self.fields['text'] += ' ' + \
                                            str(parent['id']) + '\n'
        if 'skos:related' in self.oc_item.json_ld:
            solr_field_name = 'skos_related___pred_id'
            all_solr_field_name = 'obj_all___skos_related___pred_id'
            # first make sure we've got the skos:related predicated added to the root
            # linked data solr field
            act_solr_value = self._concat_solr_string_value(
                'skos-related',
                'id',
                'http://www.w3.org/2004/02/skos/core#related',
                'Related')
            act_slug = 'skos-related'
            self.add_id_field_fq_field_values(self.ROOT_LINK_DATA_SOLR,
                                              act_solr_value,
                                              act_slug)
            for entity in self.oc_item.json_ld['skos:related']:
                if 'http://' in entity['id'] \
                   or 'https://' in entity['id']:
                    self.fields['text'] += str(entity['label']) + '\n'
                    self.fields['text'] += entity['id'] + '\n'
                    act_solr_value = self._concat_solr_string_value(
                        entity['slug'],
                        'id',
                        entity['id'],
                        entity['label']
                    )
                    act_slug = entity['slug']
                    self.add_id_field_fq_field_values(solr_field_name,
                                                      act_solr_value,
                                                      act_slug)
                    # add the all_solr_field name values
                    self.add_id_field_fq_field_values(all_solr_field_name,
                                                      act_solr_value,
                                                      act_slug)
                    self.process_object_uri(entity['id'])
                elif 'oc-pred:' in entity['id'] \
                    and 'owl:sameAs' in entity:
                    pred_uuid = URImanagement.get_uuid_from_oc_uri(
                                entity['owl:sameAs']
                                )
                    if isinstance(pred_uuid, str) \
                       and isinstance(entity['slug'], str):
                        self.fields['text'] += str(entity['label']) + '\n'
                        self.fields['text'] += entity['id'] + '\n'
                        act_solr_value = self._concat_solr_string_value(
                            entity['slug'],
                            'id',
                            '/predicates/' + pred_uuid,
                            entity['label']
                        )
                        act_slug = entity['slug']
                        self.add_id_field_fq_field_values(solr_field_name,
                                                          act_solr_value,
                                                          act_slug)
                        # add the all_solr_field name values
                        self.add_id_field_fq_field_values(all_solr_field_name,
                                                          act_solr_value,
                                                          act_slug)

    def process_direct_linked_data(self):
        """ Sometimes items have linked data directly asserted
            (not via equivalence to predicates, types)
        """
        for pred_uri in self.LD_DIRECT_PREDICATES:
            if pred_uri in self.oc_item.json_ld:
                obs_values = self.oc_item.json_ld[pred_uri]
                pred_ent = Entity()
                found = pred_ent.dereference(pred_uri)
                if found:
                    # the predicate URI is found!
                    pred_slug_id = pred_ent.slug
                    pred_datatype = '@id'
                    self.process_ld_predicate_objects(pred_ent.uri, pred_datatype, obs_values)

    def process_object_uri(self, object_uri):
        """ Projecesses object URIs.
            Useful to have a simple field that
            records all the linked data objects
            related to a subject (the documented
            indexed by solr)
            Also checks the vocabular for the object
            we we can index on that.
        """
        do_object_uri = True  # set this to False for time being
        if do_object_uri:
            if 'object_uri' not in self.fields:
                self.fields['object_uri'] = []
            self.fields['object_uri'].append(object_uri)

    def get_linked_predicate_values(self, predicate_slug_id):
        """ Gets all the values used with a certain predicate
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
            for act_entity_id, entity in self.oc_item.json_ld['@context'][2].items():
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

    def process_media_fields(self):
        """ adds a property for media file size """
        if self.oc_item.item_type == 'media':
            self.fields[self.FILE_MIMETYPE_SOLR] = []
            self.fields[self.FILE_SIZE_SOLR] = []
            if 'oc-gen:has-files' in self.oc_item.json_ld:
                thumbnail_uri = None
                iiif_json_uri = None
                for file_item in self.oc_item.json_ld['oc-gen:has-files']:
                    if 'type' in file_item and 'dc-terms:hasFormat' in file_item:
                        if file_item['type'] == 'oc-gen:fullfile':
                            self.fields[self.FILE_MIMETYPE_SOLR].append(file_item['dc-terms:hasFormat'])
                        elif file_item['type'] == 'oc-gen:thumbnail' and thumbnail_uri is None:
                            thumbnail_uri = file_item['id']
                            self.fields['thumbnail_uri'] = thumbnail_uri
                        elif file_item['type'] == 'oc-gen:iiif' and iiif_json_uri is None:
                            iiif_json_uri = file_item['id']
                            self.fields['iiif_json_uri'] = iiif_json_uri
                    if 'dcat:size' in file_item:
                        size = float(file_item['dcat:size'])
                        if size > self.max_file_size:
                            self.max_file_size = size
            if self.max_file_size > 0:
                self.fields[self.FILE_SIZE_SOLR].append(self.max_file_size)

    def process_related_subjects_for_media(self):
        """ add some fields from subjects for media items """
        if self.oc_item.item_type == 'media':
            rel_uuids = []
            # get the related subject from a context path
            if isinstance(self.context_path, list):
                if len(self.context_path) > 0:
                    last_context = self.context_path[-1]
                    rel_uri = self.get_entity_id(last_context)
                    if rel_uri is not False:
                        if '/subjects/' in rel_uri:
                            rel_uri_ex = rel_uri.split('/')
                            rel_uuid = rel_uri_ex[-1]
                            if rel_uuid not in rel_uuids:
                                rel_uuids.append(rel_uuid)
            # now get other associated subjects
            if 'oc-gen:has-obs' in self.oc_item.json_ld:
                for obs in self.oc_item.json_ld['oc-gen:has-obs']:
                    for pred_key, val_obj in obs.items():
                        if isinstance(val_obj, list):
                            for val in val_obj:
                                if isinstance(val, dict):
                                    rel_uri = self.get_entity_id(val)
                                    if rel_uri is not False:
                                        if '/subjects/' in rel_uri:
                                            rel_uri_ex = rel_uri.split('/')
                                            rel_uuid = rel_uri_ex[-1]
                                            if rel_uuid not in rel_uuids:
                                                rel_uuids.append(rel_uuid)
            for rel_uuid in rel_uuids:
                sd_obj = SolrDocument(rel_uuid)
                sd_obj.do_related = True
                if sd_obj.oc_item.item_type == 'subjects':
                    sd_obj.process_item()
                    rel_solr = sd_obj.fields
                    for field_key, vals in rel_solr.items():
                        if field_key not in self.fields:
                            if isinstance(vals, str):
                                self.fields[field_key] = ''
                            elif isinstance(vals, list):
                                self.fields[field_key] = []
                        if isinstance(vals, str):
                            self.fields[field_key] += '\n ' + vals
                        elif isinstance(vals, list):
                            for val in vals:
                                if val not in self.fields[field_key]:
                                    self.fields[field_key].append(val)
