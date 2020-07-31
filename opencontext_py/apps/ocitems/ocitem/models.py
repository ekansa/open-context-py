import time
import json
import geojson
import copy
import hashlib
from geojson import Feature, Point, Polygon, MultiPolygon, GeometryCollection, FeatureCollection
from geojson import MultiPoint, MultiLineString, LineString
from collections import OrderedDict
from django.conf import settings
from django.db import models
from django.db.models import Q
from django.core.cache import caches
from opencontext_py.libs.rootpath import RootPath
from opencontext_py.libs.languages import Languages
from opencontext_py.libs.isoyears import ISOyears
from opencontext_py.libs.general import LastUpdatedOrderedDict, DCterms
from opencontext_py.libs.globalmaptiles import GlobalMercator
from opencontext_py.libs.memorycache import MemoryCache
from opencontext_py.apps.entities.uri.models import URImanagement
from opencontext_py.apps.entities.entity.models import Entity
from opencontext_py.apps.contexts.models import ItemContext
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.ocitems.assertions.models import Assertion
from opencontext_py.apps.ocitems.assertions.containment import Containment
from opencontext_py.apps.ocitems.obsmetadata.models import ObsMetadata
from opencontext_py.apps.ocitems.predicates.models import Predicate
from opencontext_py.apps.ocitems.octypes.models import OCtype
from opencontext_py.apps.ocitems.strings.models import OCstring
from opencontext_py.apps.ocitems.mediafiles.models import Mediafile
from opencontext_py.apps.ocitems.documents.models import OCdocument
from opencontext_py.apps.ocitems.persons.models import Person
from opencontext_py.apps.ocitems.projects.models import Project
from opencontext_py.apps.ocitems.projects.metadata import ProjectRels, ProjectMeta
from opencontext_py.apps.ocitems.identifiers.models import StableIdentifer
from opencontext_py.apps.ldata.linkannotations.models import LinkAnnotation
from opencontext_py.apps.ldata.linkannotations.authorship import Authorship
from opencontext_py.apps.ldata.linkannotations.licensing import Licensing


# OCitem is a very general class for all Open Context items.
# This class is used to make a JSON-LD output from data returned from the database via other apps
class OCitem():
    PREDICATES_DCTERMS_PUBLISHED = 'dc-terms:issued'
    PREDICATES_DCTERMS_MODIFIED = 'dc-terms:modified'
    PREDICATES_DCTERMS_CREATOR = 'dc-terms:creator'
    PREDICATES_DCTERMS_CONTRIBUTOR = 'dc-terms:contributor'
    PREDICATES_DCTERMS_ISPARTOF = 'dc-terms:isPartOf'
    PREDICATES_DCTERMS_TITLE = 'dc-terms:title'
    PREDICATES_OCGEN_PREDICATETYPE = 'oc-gen:predType'
    PREDICATES_OCGEN_HASCONTEXTPATH = 'oc-gen:has-context-path'
    PREDICATES_OCGEN_HASLINKEDCONTEXTPATH = 'oc-gen:has-linked-context-path'
    PREDICATES_OCGEN_HASPATHITEMS = 'oc-gen:has-path-items'
    PREDICATES_OCGEN_HASCONTENTS = 'oc-gen:has-contents'
    PREDICATES_OCGEN_CONTAINS = 'oc-gen:contains'
    PREDICATES_OCGEN_HASOBS = 'oc-gen:has-obs'
    PREDICATES_OCGEN_SOURCEID = 'oc-gen:sourceID'
    PREDICATES_OCGEN_OBSTATUS = 'oc-gen:obsStatus'
    PREDICATES_OCGEN_OBSLABEL = 'label'
    PREDICATES_OCGEN_OBSNOTE = 'oc-gen:obsNote'
    PREDICATES_FOAF_PRIMARYTOPICOF = 'foaf:isPrimaryTopicOf'

    def __init__(self):
        self.time_start = time.time()
        self.json_ld = False
        self.uuid = False
        self.slug = False
        self.label = False
        self.item_type = False
        self.published = False
        self.modified = False
        self.manifest = False
        self.assertions = False
        self.contexts = False
        self.linked_contexts = False
        self.contents = False
        self.geo_meta = False
        self.event_meta = False
        self.temporal_meta = False
        self.stable_ids = False
        self.media = False
        self.document = False
        self.person = False
        self.project = False
        self.sub_projects = False
        self.vocabulary = False
        self.table = False
        self.predicate = False
        self.octype = False
        self.hero_images = False
        self.assertion_hashes = False
        dc_terms_obj = DCterms()
        self.DC_META_PREDS = dc_terms_obj.get_dc_terms_list()
        self.cache_entities = True

    def get_item(self, act_identifier, try_slug=False):
        """
        gets data for an item
        """
        self.get_manifest(act_identifier, try_slug)
        if(self.manifest is not False):
            self.get_assertions()
            self.get_parent_contexts()
            self.get_contained()
            self.get_geoevent_metadata()
            self.get_stable_ids()
            self.get_item_type_info()
            self.get_link_anotations()
            self.get_project_hero_images()
            self.construct_json_ld()
        return self

    def get_manifest(self, act_identifier, try_slug=False):
        """
        gets basic metadata about the item from the Manifest app
        """
        if(try_slug):
            try:
                self.manifest = Manifest.objects.get(Q(uuid=act_identifier) | Q(slug=act_identifier))
            except Manifest.DoesNotExist:
                self.manifest = False
        else:
            try:
                self.manifest = Manifest.objects.get(uuid=act_identifier)
            except Manifest.DoesNotExist:
                self.manifest = False
        if(self.manifest is not False):
            self.uuid = self.manifest.uuid
            self.slug = self.manifest.slug
            self.label = self.manifest.label
            self.project_uuid = self.manifest.project_uuid
            self.item_type = self.manifest.item_type
            self.published = self.manifest.published
            self.modified = self.manifest.revised
        return self.manifest

    def get_assertions(self):
        """
        gets item descriptions and linking relations for the item from the Assertion app
        """
        act_contain = Containment()
        self.assertions = Assertion.objects.filter(uuid=self.uuid) \
                                           .exclude(predicate_uuid=Assertion.PREDICATES_CONTAINS)\
                                           .exclude(visibility__lt=1)\
                                           .order_by('obs_num', 'sort')
        return self.assertions

    def get_parent_contexts(self):
        """
        gets item parent context
        """
        parents = False
        act_contain = Containment()
        if(self.item_type == 'subjects'):
            # get item geospatial and chronological metadata if subject item
            # will do it differently if not a subject item
            parents = act_contain.get_parents_by_child_uuid(self.uuid)
            self.contexts = parents
            # prepare a list of contexts (including the current item) to check for
            # geospatial and event / chronology metadata
            subject_list = act_contain.contexts_list
            subject_list.insert(0, self.uuid)
            self.geo_meta = act_contain.get_geochron_from_subject_list(subject_list, 'geo')
            self.temporal_meta = act_contain.get_geochron_from_subject_list(subject_list, 'temporal')
            self.event_meta = act_contain.get_geochron_from_subject_list(subject_list, 'event')
        else:
            parents = act_contain.get_related_context(self.uuid)
            self.linked_contexts = parents
        return parents

    def get_geoevent_metadata(self):
        """
        gets item geo and chronological metadata
        """
        if self.geo_meta is False and self.item_type == 'projects':
            # get project metadata objects directly
            pm = ProjectMeta()
            self.geo_meta = pm.get_project_geo_from_db(self.uuid)
        if self.geo_meta is False\
           or self.event_meta is False\
           or self.temporal_meta is False:
            act_contain = Containment()
            if self.geo_meta is False:
                self.geo_meta = act_contain.get_related_geochron(self.uuid,
                                                                 self.item_type,
                                                                 'geo')
            if self.temporal_meta is False:
                self.temporal_meta = act_contain.get_related_geochron(self.uuid,
                                                                      self.item_type,
                                                                      'temporal')
                if self.temporal_meta is False:
                    # now look in the project for temporal metadata
                    self.temporal_meta = act_contain.get_temporal_from_project(self.project_uuid)
            if self.event_meta is False:
                self.event_meta = act_contain.get_related_geochron(self.uuid,
                                                                   self.item_type,
                                                                   'event')
            return True
        else:
            return False

    def get_contained(self):
        """
        gets item containment children
        """
        act_contain = Containment()
        self.contents = act_contain.get_children_by_parent_uuid(self.uuid)
        return self.contents

    def get_stable_ids(self):
        self.stable_ids = StableIdentifer.objects.filter(uuid=self.uuid)

    def get_item_type_info(self):
        """
        gets information specific to different item types
        """
        if self.item_type == 'media':
            self.media = Mediafile.objects.filter(uuid=self.uuid)
        elif self.item_type == 'documents':
            try:
                self.document = OCdocument.objects.get(uuid=self.uuid)
            except Document.DoesNotExist:
                self.document = False
        elif self.item_type == 'persons':
            try:
                self.person = Person.objects.get(uuid=self.uuid)
            except Person.DoesNotExist:
                self.person = False
        elif self.item_type == 'projects':
            try:
                self.project = Project.objects.get(uuid=self.uuid)
            except Project.DoesNotExist:
                self.project = False
            pr = ProjectRels()
            pm = ProjectMeta()
            if self.project is not False:
                if isinstance(self.project.meta_json, dict):
                    if Project.META_KEY_GEO_SPECIFICITY in self.project.meta_json:
                        # the project has some default geographic specificity noted
                        # use this value when making geo_meta
                        pm.project_specificity = self.project.meta_json[Project.META_KEY_GEO_SPECIFICITY]
            self.sub_projects = pr.get_sub_projects(self.uuid)
            if self.geo_meta is False:
                pm.print_progress = True
                pm.make_geo_meta(self.uuid, self.sub_projects)
                self.geo_meta = pm.geo_objs
        elif self.item_type == 'predicates':
            try:
                self.predicate = Predicate.objects.get(uuid=self.uuid)
            except Predicate.DoesNotExist:
                self.predicate = False
        elif self.item_type == 'types':
            try:
                self.octype = OCtype.objects.get(uuid=self.uuid)
            except OCtype.DoesNotExist:
                self.octype = False

    def add_predicate_datatype(self, json_ld):
        """ Adds a rdfs:range to predicate items to indicate
            data types
        """
        if self.predicate is not False:
            json_ld['oc-gen:data-type'] = self.predicate.data_type
            p_range = LastUpdatedOrderedDict()
            p_range['id'] = self.predicate.data_type
            if self.predicate.data_type == 'id':
                p_range['id'] = 'http://opencontext.org/vocabularies/oc-general/items'
                p_range['label'] = 'URI identified items'
            elif self.predicate.data_type == 'xsd:string':
                p_range['label'] = 'Alphanumeric text strings'
            elif self.predicate.data_type == 'xsd:double':
                p_range['label'] = 'Decimal values'
            elif self.predicate.data_type == 'xsd:integer':
                p_range['label'] = 'Integer values'
            elif self.predicate.data_type == 'xsd:date':
                p_range['label'] = 'Calendar / date values'
            json_ld['rdfs:range'] = [p_range]
            if self.assertion_hashes:
                # add a default sort order, for edit view JSON
                json_ld['oc-gen:default-sort-order'] = float(self.predicate.sort)
        return json_ld

    def add_related_predicate(self,
                              item_con,
                              json_ld):
        """ Adds a skos:related to the predicate used with this type """
        output = False
        if self.octype is not False:
            rel_predicate = LastUpdatedOrderedDict()
            uri = URImanagement.make_oc_uri(self.octype.predicate_uuid,
                                            'predicates')
            rel_predicate['id'] = URImanagement.prefix_common_uri(uri)
            rel_predicate['owl:sameAs'] = uri
            rel_predicate['slug'] = False
            rel_predicate['label'] = False
            if self.cache_entities:
                icc = itemConstructionCache()
                entity_item = icc.get_entity_w_thumbnail(self.octype.predicate_uuid)
                if entity_item is not False:
                    found = True
                    ent = entity_item
                else:
                    found = False
            else:
                ent = Entity()
                found = ent.dereference(self.octype.predicate_uuid)
            if found:
                rel_predicate['id'] = 'oc-pred:' + str(ent.slug)
                rel_predicate['slug'] = ent.slug
                rel_predicate['label'] = ent.label
                item_con.predicates[self.octype.predicate_uuid] = rel_predicate['id']
            if 'skos:related' not in json_ld:
                json_ld['skos:related'] = []
            json_ld['skos:related'].append(rel_predicate)
            output = {'item_con': item_con,
                      'json_ld': json_ld}
        return output

    def get_link_anotations(self):
        self.link_annotations = LinkAnnotation.objects\
                                              .filter(subject=self.uuid)\
                                              .order_by('predicate_uri', 'sort')

    def get_project_hero_images(self):
        """ gets hero images if a project """
        if self.item_type == 'projects':
            self.hero_images = Mediafile.objects\
                                        .filter(uuid=self.uuid,
                                                file_type='oc-gen:hero')
            if len(self.hero_images) < 1:
                # check for hero images belonging to the parent project
                self.hero_images = Mediafile.objects\
                                            .filter(uuid=self.project_uuid,
                                                    file_type='oc-gen:hero')

    def construct_json_ld(self):
        """
        creates JSON-LD documents for an item
        currently, it's just here to make some initial JSON while we learn python
        """
        lang_obj = Languages()
        item_con = ItemConstruction()
        item_con.uuid = self.uuid
        item_con.project_uuid = self.project_uuid
        item_con.item_type = self.item_type
        item_con.cache_entities = self.cache_entities
        if self.assertion_hashes:
            # case to show hashs of observation values, useful for editing
            item_con.assertion_hashes = self.assertion_hashes
        json_ld = item_con.intialize_json_ld(self.assertions)
        json_ld['id'] = URImanagement.make_oc_uri(self.uuid, self.item_type)
        json_ld['uuid'] = self.uuid
        json_ld['slug'] = self.slug
        json_ld['label'] = self.label
        if isinstance(self.manifest.localized_json, dict):
            if len(self.manifest.localized_json) > 0:
                json_ld['skos:altLabel'] = self.manifest.localized_json
        if(len(self.manifest.class_uri) > 0):
            json_ld['category'] = [self.manifest.class_uri]
            item_con.class_type_list.append(self.manifest.class_uri)
        if self.person is not False:
            # add foaf properties for people / organizations
            json_ld['foaf:name'] = self.person.combined_name
            if len(self.person.given_name) > 0:
                json_ld['foaf:givenName'] = self.person.given_name
            if len(self.person.surname) > 0:
                json_ld['foaf:familyName'] = self.person.surname
            if len(self.person.initials) > 0:
                json_ld['foaf:nick'] = self.person.initials
            if self.assertion_hashes and len(self.person.mid_init) >0:
                json_ld['oc-gen:mid_init'] = self.person.mid_init
        # add related type data
        rel_pred = self.add_related_predicate(item_con,
                                              json_ld)
        if rel_pred is not False:
            item_con = rel_pred['item_con']
            json_ld = rel_pred['json_ld']
        # add predicate type data
        json_ld = self.add_predicate_datatype(json_ld)
        # add context data
        json_ld = item_con.add_contexts(json_ld,
                                        self.PREDICATES_OCGEN_HASCONTEXTPATH,
                                        self.contexts)
        # add linked contexts (context inferred from linking relations)
        json_ld = item_con.add_contexts(json_ld,
                                        self.PREDICATES_OCGEN_HASLINKEDCONTEXTPATH,
                                        self.linked_contexts)
        if(len(self.contents) > 0):
            #adds child contents, with different treenodes
            for tree_node, children in self.contents.items():
                act_children = LastUpdatedOrderedDict()
                act_children['id'] = tree_node
                act_children['type'] = 'oc-gen:contents'
                for child_uuid in children:
                    act_children = item_con.add_json_predicate_list_ocitem(act_children,
                                                                           self.PREDICATES_OCGEN_CONTAINS,
                                                                           child_uuid, 'subjects')
            json_ld[self.PREDICATES_OCGEN_HASCONTENTS] = act_children
        # add predicate - object (descriptions) to the item
        json_ld = item_con.add_direct_assertions(json_ld)
        json_ld = item_con.add_descriptive_assertions(json_ld, self.assertions)
        json_ld = item_con.add_spacetime_metadata(json_ld,
                                                  self.uuid,
                                                  self.item_type,
                                                  self.geo_meta,
                                                  self.event_meta)
        if self.media is not False:
            json_ld = item_con.add_media_json(json_ld, self.media)
        if self.document is not False:
            json_ld = item_con.add_document_json(json_ld, self.document)
        json_ld = item_con.add_dc_title(json_ld)  # adds dublin core title information, useful for indexing
        if self.published is not None and self.published is not False:
            json_ld[self.PREDICATES_DCTERMS_PUBLISHED] = self.published.date().isoformat()
        if self.modified is not None and self.modified is not False:
            json_ld[self.PREDICATES_DCTERMS_MODIFIED] = self.modified.date().isoformat()
        if(self.uuid != self.project_uuid):
            json_ld = item_con.add_json_predicate_list_ocitem(json_ld,
                                                              self.PREDICATES_DCTERMS_ISPARTOF,
                                                              self.project_uuid, 'projects')
        if self.project is not False:
            json_ld['description'] = lang_obj.make_json_ld_value_obj(self.project.short_des,
                                                                     self.project.sm_localized_json)
            json_ld['dc-terms:abstract'] = lang_obj.make_json_ld_value_obj(self.project.content,
                                                                           self.project.lg_localized_json)
            json_ld = item_con.add_editorial_status(json_ld, self.project.edit_status)
            json_ld = item_con.add_project_hero_images(json_ld, self.hero_images)
        # add dublin-core descriptive metadata predicates
        for dc_meta in self.DC_META_PREDS:
            if dc_meta not in json_ld:
                json_ld[dc_meta] = []  # add it here to make sure it's before the @graph
        json_ld = item_con.add_license(json_ld)
        # now add dublin-core descriptive metadata
        # add the stable ids needed for citation
        json_ld = item_con.add_stable_ids(json_ld, self.item_type, self.stable_ids)
        # add a slug identifier if the item_type allows slugs
        item_con.add_item_labels = False
        if(self.item_type in settings.SLUG_TYPES):
            json_ld = item_con.add_json_predicate_list_ocitem(json_ld,
                                                              'owl:sameAs',
                                                              self.slug,
                                                              self.item_type,
                                                              True)
        # add linked data annotations, inferred authorship metadata
        json_ld = item_con.add_inferred_authorship_linked_data_graph(json_ld)
        json_ld = item_con.add_link_annotations(json_ld, self.link_annotations)
        if self.sub_projects is not False:
            for sub_proj in self.sub_projects:
                json_ld = item_con.add_json_predicate_list_ocitem(json_ld,
                                                                  'dc-terms:hasPart',
                                                                  sub_proj.uuid,
                                                                  'projects')
        if settings.DEBUG:
            json_ld['time'] = time.time() - self.time_start
        # last add inferred temporal metadata if it exists
        json_ld = item_con.add_json_temporal(json_ld, self.temporal_meta)
        # now get rid of unused dc-terms metadata
        for dc_meta in self.DC_META_PREDS:
            if len(json_ld[dc_meta]) < 1:
                json_ld.pop(dc_meta, None)  # get rid of not used dc-meta predicate
        self.json_ld = json_ld
        item_con.__del__()
        return self.json_ld


class ItemConstruction():
    """
    General purpose functions for building Open Context items
    """

    # predicates not for use in observations
    NO_OBS_ASSERTION_PREDS = [
        'skos:note'
    ]

    # Biological Taxonomy Requirements. This dict
    # configures how two different 
    PREDICATES_BIO_TAXONOMIES = {
        # NOTE: eol URIs and this predicate URI 
        # are to be deprecated.
        'http://purl.org/NET/biol/ns#term_hasTaxonomy': {
            'includes': ['eol.org'],
            'excludes': ['#gbif-sub'],
        },
        # NOTE: this predicate URI and GBIF uris
        # are preferred. However, 'sheep/goat' will remain
        # a EOL uri, but with a #gbif-sub suffix to it.
        'http://purl.obolibrary.org/obo/FOODON_00001303': {
            'includes': ['gbif.org', '#gbif-sub'],
            'excludes': [],
        },
    }

    def __init__(self):
        self.uuid = False
        self.project_uuid = False
        self.item_type = False
        self.assertion_hashes = False
        self.add_item_labels = True
        self.add_linked_data_labels = True
        self.add_media_thumnails = True
        self.add_subject_class = True
        self.cannonical_uris = True
        self.direct_assertions = list()  # assertions not in an observation
        self.obs_list = list()
        self.predicates = LastUpdatedOrderedDict()
        self.var_list = list()
        self.link_list = list()
        self.type_list = list()
        self.pred_strings = {}  # for tracking string values for preds with linked data
        self.class_type_list = list()
        self.dc_contrib_preds = list()
        self.dc_creator_preds = list()
        self.graph_links = list()
        self.entity_metadata = {}
        self.thumbnails = {}
        self.parent_list = list()
        self.cache_entities = False

    def __del__(self):
        self.var_list = list()
        self.link_list = list()
        self.type_list = list()

    def intialize_json_ld(self, assertions):
        """
        creates a json_ld (ordered) dictionary with a context
        """
        json_ld = LastUpdatedOrderedDict()
        # context object, a list with:
        # 1: a URI to the general item context
        # 2: a dict of 'local context' predicates (variables, links)
        context = []
        item_context_obj = ItemContext()
        context.append(item_context_obj.id)  # add the URI for the general item context
        context.append(item_context_obj.geo_json_context)  # add the URI for GeoJSON context
        local_context = LastUpdatedOrderedDict()  # make an object for the local context
        raw_pred_list = list()
        pred_types = {}
        for assertion in assertions:
            if assertion.predicate_uuid in self.NO_OBS_ASSERTION_PREDS:
                # these predicates describe the item, but not in an observation
                self.direct_assertions.append(assertion)
            else:
                # these predicates are used inside observations
                if assertion.obs_num not in self.obs_list:
                    self.obs_list.append(assertion.obs_num)
                if assertion.predicate_uuid not in raw_pred_list:
                    raw_pred_list.append(assertion.predicate_uuid)
                    if any(assertion.object_type in item_type for item_type in settings.ITEM_TYPES):
                        pred_types[assertion.predicate_uuid] = '@id'
                    else:
                        pred_types[assertion.predicate_uuid] = assertion.object_type
        # prepares dictionary objects for each predicate
        for pred_uuid in raw_pred_list:
            pmeta = self.get_entity_metadata(pred_uuid)
            if pmeta is not False:
                p_data = LastUpdatedOrderedDict()
                p_data['owl:sameAs'] = pmeta.uri
                p_data['label'] = str(pmeta.label)
                p_data['slug'] = str(pmeta.slug)
                p_data['uuid'] = str(pmeta.uuid)
                p_data[OCitem.PREDICATES_OCGEN_PREDICATETYPE] = str(pmeta.class_uri)
                p_data['type'] = pred_types[pred_uuid]
                if pmeta.class_uri == 'variable':
                    self.var_list.append(p_data)
                elif pmeta.class_uri == 'link':
                    self.link_list.append(p_data)
                else:
                    self.link_list.append(p_data)
        # adds variable predicates to the item context
        v = 1
        for v_data in self.var_list:
            if(v_data['slug'] is None):
                key = 'var-' + str(v)
            else:
                key = 'oc-pred:' + v_data['slug']
            self.predicates[v_data['uuid']] = key
            if v_data['type'] == 'xsd:string':
                self.pred_strings[key] = []  # to keep track of linked data for strings
            del v_data['uuid']
            local_context[key] = v_data
            v += 1
        # adds link predicates to the item context
        l = 1
        for l_data in self.link_list:
            if(l_data['slug'] is None):
                key = 'link-' + str(l)
            else:
                key = 'oc-pred:' + l_data['slug']
            self.predicates[l_data['uuid']] = key
            del l_data['uuid']
            local_context[key] = l_data
            l += 1
        # last handling to proccess general notes
        if Assertion.PREDICATES_NOTE in raw_pred_list:
            self.predicates[Assertion.PREDICATES_NOTE] = Assertion.PREDICATES_NOTE
            self.pred_strings[Assertion.PREDICATES_NOTE] = []
        context.append(local_context)  # add the local context to the context list
        json_ld['@context'] = context
        return json_ld

    def add_direct_assertions(self, act_dict):
        """
        adds assertions that describe the item, but are not
        part of an observation
        """
        for assertion in self.direct_assertions:
            content = None
            if any(assertion.object_type in item_type for item_type in settings.ITEM_TYPES):
                entity = self.get_entity_metadata(self.object_uuid)
                if entity is not False:
                    content = entity.uri
            else:
                if assertion.object_type == 'xsd:string':
                    try:
                        string_item = OCstring.objects.get(uuid=assertion.object_uuid)
                        lang_obj = Languages()
                        content = lang_obj.make_json_ld_value_obj(string_item.content,
                                                                  string_item.localized_json)
                    except OCstring.DoesNotExist:
                        content = 'string content missing'
                elif (assertion.object_type == 'xsd:date'):
                    content = assertion.data_date.date().isoformat()
                else:
                    content = assertion.data_num
            act_dict[assertion.predicate_uuid] = content
        return act_dict

    def add_descriptive_assertions(self, act_dict, assertions):
        """
        adds descriptive assertions (descriptive properties, non spatial containment links)
        to items, as parts of Observations
        """
        observations = list()
        for act_obs_num in self.obs_list:
            add_obs_def = True
            act_obs = LastUpdatedOrderedDict()
            for assertion in assertions:
                if(assertion.obs_num == act_obs_num):
                    if(add_obs_def):
                        if(assertion.obs_node[:1] == '#'):
                            act_obs['id'] = str(assertion.obs_node)
                        else:
                            act_obs['id'] = "#" + str(assertion.obs_node)
                        act_obs[OCitem.PREDICATES_OCGEN_SOURCEID] = assertion.source_id
                        if(act_obs_num >= 0 and act_obs_num != 100):
                            act_obs[OCitem.PREDICATES_OCGEN_OBSTATUS] = 'active'
                        else:
                            act_obs[OCitem.PREDICATES_OCGEN_OBSTATUS] = 'deprecated'
                        try:
                            obs_meta = ObsMetadata.objects.get(source_id=assertion.source_id,
                                                               obs_num=assertion.obs_num)
                        except ObsMetadata.DoesNotExist:
                            obs_meta = False
                        if(obs_meta is not False):
                            act_obs[OCitem.PREDICATES_OCGEN_OBSLABEL] = obs_meta.label
                            if(len(obs_meta.note) > 0):
                                act_obs[OCitem.PREDICATES_OCGEN_OBSNOTE] = obs_meta.note
                        add_obs_def = False
                        act_obs['type'] = 'oc-gen:observations'
                    if assertion.predicate_uuid in self.predicates:
                        act_pred_key = self.predicates[assertion.predicate_uuid]
                        if self.assertion_hashes:
                            # when we need to have hash identifiers on assertions
                            act_obs = self.add_predicate_value_hash_id(act_obs, act_pred_key, assertion)
                        else:
                            # default case, no has identifiers.
                            act_obs = self.add_predicate_value(act_obs, act_pred_key, assertion)
            observations.append(act_obs)
        if(len(observations) > 0):
            act_dict[OCitem.PREDICATES_OCGEN_HASOBS] = observations
        return act_dict

    def add_predicate_value(self, act_dict, act_pred_key, assertion):
        """
        creates an object value for a predicate assertion
        """
        if any(assertion.object_type in item_type for item_type in settings.ITEM_TYPES):
            if(assertion.object_uuid not in self.type_list):
                self.type_list.append(assertion.object_uuid)
            return self.add_json_predicate_list_ocitem(act_dict, act_pred_key,
                                                       assertion.object_uuid,
                                                       assertion.object_type)
        else:
            if act_pred_key in act_dict:
                act_list = act_dict[act_pred_key]
            else:
                act_list = []
            if assertion.object_type == 'xsd:string' \
               and act_pred_key in self.pred_strings:
                new_object_item = LastUpdatedOrderedDict()
                if assertion.object_uuid not in self.pred_strings[act_pred_key]:
                    self.pred_strings[act_pred_key].append(assertion.object_uuid)  # for linked data
                new_object_item['id'] = '#string-' + str(assertion.object_uuid)
                try:
                    string_item = OCstring.objects.get(uuid=assertion.object_uuid)
                    lang_obj = Languages()
                    new_object_item[assertion.object_type] = lang_obj.make_json_ld_value_obj(string_item.content,
                                                                                             string_item.localized_json)
                except OCstring.DoesNotExist:
                    new_object_item[assertion.object_type] = 'string content missing'
                act_list.append(new_object_item)
            elif (assertion.object_type == 'xsd:date'):
                act_list.append(assertion.data_date.date().isoformat())
            else:
                act_list.append(assertion.data_num)
            act_dict[act_pred_key] = act_list
            return act_dict

    def add_predicate_value_hash_id(self, act_dict, act_pred_key, assertion):
        """
        creates an object value for a predicate assertion
        """
        if any(assertion.object_type in item_type for item_type in settings.ITEM_TYPES):
            if(assertion.object_uuid not in self.type_list):
                self.type_list.append(assertion.object_uuid)
            return self.add_json_predicate_list_ocitem(act_dict, act_pred_key,
                                                       assertion.object_uuid,
                                                       assertion.object_type,
                                                       False,
                                                       assertion.hash_id)
        else:
            if act_pred_key in act_dict:
                act_list = act_dict[act_pred_key]
            else:
                act_list = []
            new_object_item = LastUpdatedOrderedDict()
            new_object_item['hash_id'] = assertion.hash_id
            if (assertion.object_type == 'xsd:string'):
                if assertion.object_uuid not in self.pred_strings[act_pred_key]:
                    self.pred_strings[act_pred_key].append(assertion.object_uuid)  # for linked data
                new_object_item['id'] = '#string-' + str(assertion.object_uuid)
                try:
                    string_item = OCstring.objects.get(uuid=assertion.object_uuid)
                    lang_obj = Languages()
                    new_object_item[assertion.object_type] = lang_obj.make_json_ld_value_obj(string_item.content,
                                                                                             string_item.localized_json)
                except OCstring.DoesNotExist:
                    new_object_item[assertion.object_type] = 'string content missing'
            elif (assertion.object_type == 'xsd:date'):
                new_object_item['literal'] = assertion.data_date.date().isoformat()
            else:
                new_object_item['literal'] = assertion.data_num
            act_list.append(new_object_item)
            act_dict[act_pred_key] = act_list
            return act_dict

    def add_contexts(self, act_dict, act_pred_key, raw_contexts):
        """ adds context information, if present """
        if(raw_contexts is not False):
            if(len(raw_contexts) > 0):
                #adds parent contents, with different treenodes
                first_node = True;
                act_context = LastUpdatedOrderedDict()
                for tree_node, r_parents in raw_contexts.items():
                    act_context = LastUpdatedOrderedDict()
                    # change the parent node to context not contents
                    tree_node = tree_node.replace('contents', 'context')
                    act_context['id'] = tree_node
                    act_context['type'] = 'oc-gen:contexts'
                    # now reverse the list of parent contexts, so top most parent context is first,
                    # followed by children contexts
                    parents = r_parents[::-1]
                    for parent_uuid in parents:
                        act_context = self.add_json_predicate_list_ocitem(act_context,
                                                                          OCitem.PREDICATES_OCGEN_HASPATHITEMS,
                                                                          parent_uuid, 'subjects')
                    act_dict[act_pred_key] = act_context
                    if first_node:
                        # set aside a list of parent labels to use for making a dc-term:title
                        first_node = False
                        if OCitem.PREDICATES_OCGEN_HASPATHITEMS in act_context:
                            for parent_obj in act_context[OCitem.PREDICATES_OCGEN_HASPATHITEMS]:
                                self.parent_list.append(parent_obj['label'])
        return act_dict

    def add_stable_ids(self, act_dict, item_type, stable_ids):
        """
        adds stable identifier information to an item's JSON-LD dictionary object
        """
        if(stable_ids is not False):
            if(len(stable_ids) > 0):
                stable_id_list = []
                for stable_id in stable_ids:
                    if(stable_id.stable_type in settings.STABLE_ID_URI_PREFIXES):
                        uri = settings.STABLE_ID_URI_PREFIXES[stable_id.stable_type] + str(stable_id.stable_id)
                        id_dict = {'id': uri}
                        stable_id_list.append(id_dict)
                if item_type == 'persons' and len(stable_id_list) > 0:
                    # persons with ORCID ids use the foaf:primarytopic predicate to link to ORCID
                    primary_topic_list = []
                    same_as_list = []
                    for id_dict in stable_id_list:
                        if 'http://orcid.org' in id_dict['id']:
                            primary_topic_list.append(id_dict)
                        else:
                            same_as_list.append(id_dict)
                    stable_id_list = same_as_list  # other types of identifiers use as owl:sameAs
                    if len(primary_topic_list) > 0:
                        act_dict[OCitem.PREDICATES_FOAF_PRIMARYTOPICOF] = primary_topic_list
                if len(stable_id_list) > 0:
                    act_dict['owl:sameAs'] = stable_id_list
        return act_dict

    def add_dc_title(self, act_dict, title=False):
        """
        adds a dublin core title key and value
        """
        if title is False and 'label' in act_dict:
            title = act_dict['label']
            if len(self.parent_list) > 0:
                parents = '/'.join(self.parent_list)
                title += ' from ' + parents
        if title is not False:
            act_dict[OCitem.PREDICATES_DCTERMS_TITLE] = title
        return act_dict

    def biological_taxonomy_validation(self, act_pred, object_uri):
        """For biological taxa linked data, checks if an object_uri
        is OK for a predicate
        """
        # NOTE: This is needed because we're deprecating EOL
        # URIs in favor of GBIF, but want to maintain 
        # backward compatibility
        # print('checking: {}'.format(act_pred))
        if not act_pred in self.PREDICATES_BIO_TAXONOMIES:
            # Not a predicate for biological taxa, default
            # to valid
            return True
        check_dict = self.PREDICATES_BIO_TAXONOMIES[act_pred]
        for exclude in check_dict['excludes']:
            if exclude in object_uri:
                return False
        for include in check_dict['includes']:
            if include in object_uri:
                return True
        return False

    def add_link_annotations(self, act_dict, link_annotations):
        """
        adds stable identifier information to an item's JSON-LD dictionary object
        """
        if len(link_annotations) < 1:
            return act_dict
        
        for la in link_annotations:
            tcheck = URImanagement.get_uuid_from_oc_uri(
                la.object_uri, 
                True
            )
            if not tcheck:
                item_type = False
            else:
                item_type = tcheck['item_type']
            act_pred = URImanagement.prefix_common_uri(la.predicate_uri)
            act_dict = self.add_json_predicate_list_ocitem(
                act_dict,
                act_pred,
                la.object_uri,
                item_type
            )
        return act_dict

    def add_editorial_status(self, act_dict, edit_status):
        """
        adds editorial status information to the resource
        """
        oc_status = 'oc-gen:edit-level-' + str(edit_status)
        act_dict = self.add_json_predicate_list_ocitem(act_dict, 'bibo:status', oc_status, False)
        if edit_status == 0:
            act_dict = self.add_json_predicate_list_ocitem(act_dict, 'bibo:status', 'bibo:status/forthcoming', False)
        elif edit_status >= 1 and edit_status <= 2:
            act_dict = self.add_json_predicate_list_ocitem(act_dict, 'bibo:status', 'bibo:status/nonPeerReviewed', False)
        else:
            act_dict = self.add_json_predicate_list_ocitem(act_dict, 'bibo:status', 'bibo:status/peerReviewed', False)
        return act_dict

    def add_json_predicate_list_ocitem(self, act_dict, act_pred_key,
                                       object_id, item_type, do_slug_uri=False,
                                       add_hash_id=False):
        """
        creates a list for an act_predicate of the json_ld dictionary object if it doesn't exist
        adds a list item of a dictionary object for a linked Open Context item
        """
        object_ids = []
        if act_pred_key in act_dict:
            for obj in act_dict[act_pred_key]:
                if 'id' in obj:
                    object_ids.append(obj['id'])
                elif '@id' in obj:
                    object_ids.append(obj['@id'])
        else:
            act_dict[act_pred_key] = []
        
        if do_slug_uri:
            new_object_item = LastUpdatedOrderedDict()
            new_object_item['id'] = URImanagement.make_oc_uri(object_id, item_type)
            act_dict[act_pred_key].append(new_object_item)
            return act_dict
        if act_pred_key == 'oc-gen:hasIcon':
            act_dict[act_pred_key].append({'id': object_id})
            return act_dict
        
        ent = self.get_entity_metadata(object_id)
        if not ent:
            return act_dict

        new_object_item = LastUpdatedOrderedDict()
        if add_hash_id is not False:
            new_object_item['hash_id'] = add_hash_id
        
        if not self.biological_taxonomy_validation(
            act_pred_key, ent.uri):
            # We have a act_pred and object_uri combination
            # that is not valid. So skip.
            return act_dict

        new_object_item['id'] = ent.uri
        new_object_item['slug'] = ent.slug
        if(ent.label is not False):
            new_object_item['label'] = ent.label
        else:
            new_object_item['label'] = 'No record of label'
        if(ent.thumbnail_uri is not False):
            new_object_item['oc-gen:thumbnail-uri'] = ent.thumbnail_uri
        if(ent.content is not False and ent.content != ent.label):
            new_object_item['rdfs:comment'] = ent.content
        if((ent.class_uri is not False) and
            (item_type == 'subjects'
                or item_type == 'media'
                or item_type == 'persons')):
            new_object_item['type'] = ent.class_uri
            if(ent.class_uri not in self.class_type_list):
                self.class_type_list.append(ent.class_uri)  # list of unique open context item classes
        if new_object_item['id'] not in object_ids:
            act_dict[act_pred_key].append(new_object_item)
        return act_dict

    def add_inferred_authorship_linked_data_graph(self, act_dict):
        """
        First gets linked data annotating entities in the item, this can include
        Dublin Core contributor and Creator annotions.
        Dublin Core contributor and Creator annotions are handled differently, since
        they are more special and used for citation. They are used to create
        predicate relations indicating authorship for an item.
        """
        # gets linked data for predicates and types
        self.prepare_linked_data_graph()
        # adds DC-contributors and Creators as inferred from annotations to predicates used on item
        act_dict = self.add_inferred_dc_authorship(act_dict)
        if(len(self.graph_links) > 0):
            act_dict['@graph'] = self.graph_links
        return act_dict

    def prepare_linked_data_graph(self):
        """
        prepare a list of graph_links describing linked data annotations
        """
        graph_list = []
        # add linked data annotations for predicates
        for predicate_uuid, slug in self.predicates.items():
            g_start = len(graph_list)
            graph_list = self.get_annotations_for_ocitem(graph_list, predicate_uuid, 'predicates', slug)
            g_next = len(graph_list)
            if g_next > g_start and slug in self.pred_strings:
                # only check for LD annotations if the current predicate has an annotation
                for string_uuid in self.pred_strings[slug]:
                    graph_list = self.get_annotations_for_ocitem(graph_list, string_uuid, 'xsd:string')
        # add linked data annotations for types
        for type_uuid in self.type_list:
            graph_list = self.get_annotations_for_ocitem(graph_list, type_uuid, 'types')
        # add lined data annotations for item oc-gen:classes (present in 'type' keys)
        for class_uri in self.class_type_list:
            graph_list = self.get_annotations_for_oc_gen_class(graph_list, class_uri)
        self.graph_links += graph_list
        return self.graph_links

    def add_inferred_dc_authorship(self, act_dict):
        """
        Adds authorship info via inference.
        If some predicates had DC contributor or DC creator annotations, get their objects
        to use in adding authorship information for the item
        """
        contribs = False
        creators = False
        icc = itemConstructionCache()
        cache_key = icc.make_cache_key('proj-auth-', str(self.project_uuid))
        auth = None
        if self.cache_entities:
            auth = icc.get_cache_object(cache_key)
        if auth is None:
            auth = Authorship()
            auth.get_project_authors(self.project_uuid)
            if self.cache_entities:
                icc.save_cache_object(cache_key, auth)
        proj_creators = []
        proj_creators_ids = []
        for proj_creator in auth.creators:
            new_object_item = LastUpdatedOrderedDict()
            ent = self.get_entity_metadata(proj_creator)
            if ent is not False:
                new_object_item['id'] = ent.uri
                new_object_item['slug'] = ent.slug
                new_object_item['label'] = ent.label
                if ent.class_uri is not False:
                    new_object_item['type'] = ent.class_uri
                if ent.uri not in proj_creators_ids:
                    # no duplicate IDs
                    proj_creators_ids.append(ent.uri)
                    proj_creators.append(new_object_item)
        proj_contribs = []
        proj_contribs_ids = []
        for proj_contrib in auth.contributors:
            new_object_item = LastUpdatedOrderedDict()
            ent = self.get_entity_metadata(proj_contrib)
            if ent is not False:
                new_object_item['id'] = ent.uri
                new_object_item['slug'] = ent.slug
                new_object_item['label'] = ent.label
                if ent.class_uri is not False:
                    new_object_item['type'] = ent.class_uri
                if ent.uri not in proj_contribs_ids:
                    # no duplicate IDs
                    proj_contribs_ids.append(ent.uri)
                    proj_contribs.append(new_object_item)
        if(len(self.dc_contrib_preds) > 0 or len(self.dc_creator_preds) > 0):
            contribs = self.get_dc_authorship(act_dict, self.dc_contrib_preds)
            creators = self.get_dc_authorship(act_dict, self.dc_creator_preds)
        if creators is False and contribs is False:
            # missing both item creators and contributors
            if len(proj_contribs) > 0:
                contribs = proj_contribs
        if creators is False:
            creators = proj_creators
        else:
            proj_creators_ids = []
            for proj_creator in proj_creators:
                if 'id' in proj_creator:
                    uri = proj_creator['id']
                elif '@id' in proj_creator:
                    uri = proj_creator['id']
                if uri not in proj_creators_ids:
                    # no duplicate IDs
                    proj_creators_ids.append(uri)
                    creators.append(proj_creator)
        if contribs is not False:
            if('dc-terms:contributor' in act_dict):
                act_dict['dc-terms:contributor'] = self.add_unique_entity_lists(act_dict['dc-terms:contributor'],
                                                                                contribs)
            else:
                act_dict['dc-terms:contributor'] = contribs
        if creators is not False:
            if('dc-terms:creator' in act_dict):
                act_dict['dc-terms:creator'] = self.add_unique_entity_lists(act_dict['dc-terms:creator'],
                                                                            creators)
            else:
                act_dict['dc-terms:creator'] = creators
        return act_dict

    def add_license(self, act_dict):
        """ Adds license information """
        item_license = None
        icc = itemConstructionCache()
        cache_key = icc.make_cache_key('proj-lic-',
                                       str(self.uuid) + ' ' + str(self.project_uuid))
        if self.cache_entities:
            item_license = icc.get_cache_object(cache_key)
        if item_license is None:
            lic = Licensing()
            item_license = lic.get_license(self.uuid,
                                           self.project_uuid)
            if self.cache_entities:
                icc.save_cache_object(cache_key, item_license)
        if item_license is not False:
            new_object_item = LastUpdatedOrderedDict()
            new_object_item['id'] = item_license
            ent = self.get_entity_metadata(item_license)
            if ent is not False:
                new_object_item['slug'] = ent.slug
                new_object_item['label'] = ent.label
            act_dict['dc-terms:license'] = [new_object_item]
        else:
            print('crap, no license')
        return act_dict

    def add_json_temporal(self, act_dict, temporal_meta):
        """ adds temporal metadata predicate """
        if temporal_meta is not False:
            if 'dc-terms:temporal' not in act_dict:
                act_dict['dc-terms:temporal'] = []
            if len(act_dict['dc-terms:temporal']) < 1:
                # only add if we don't already have temproal metadata
                # and if we have temporal annotations form a parent item
                i = 0
                for temporal in temporal_meta:
                    new_object_item = LastUpdatedOrderedDict()
                    new_object_item['id'] = temporal.object_uri
                    ent = self.get_entity_metadata(temporal.object_uri)
                    if ent is not False:
                        subject_uri = URImanagement.make_oc_uri(temporal.subject,
                                                                temporal.subject_type,
                                                                self.cannonical_uris)
                        new_object_item['slug'] = ent.slug
                        new_object_item['label'] = ent.label
                        if 'id' in act_dict\
                           and subject_uri is not False:
                            if act_dict['id'] != subject_uri:
                                # we have an infered temporal relation
                                """
                                Commenting out this stuff, because it is overly
                                pedantic. It's easier just to treat this assertion
                                directly to the period, rather than some fragment
                                identifier.

                                if people complain, we will uncomment this code.
                                i += 1
                                new_object_item['id'] = '#period-' + str(i)
                                new_object_item['rdfs:isDefinedBy'] = temporal.object_uri
                                new_object_item['slug'] = ent.slug
                                new_object_item['label'] = ent.label
                                """
                                new_object_item['reference-type'] = 'inferred'
                                new_object_item['reference-uri'] = subject_uri
                                rel_meta = self.get_entity_metadata(subject_uri)
                                if rel_meta is not False:
                                    new_object_item['reference-label'] = rel_meta.label
                        act_dict['dc-terms:temporal'].append(new_object_item)
        return act_dict

    def add_unique_entity_lists(self, existing_list, to_add_list):
        """
        Adds entities (uniquely) to an existing list from another entity list
        """
        existing_ids = []
        if(len(existing_list) > 0):
            for existing_item in existing_list:
                if('id' in existing_item):
                    existing_ids.append(existing_item['id'])
                elif('@id' in existing_item):
                    existing_ids.append(existing_item['@id'])
        if(len(to_add_list) > 0):
            for to_add_item in to_add_list:
                act_id = False
                if('id' in to_add_item):
                    act_id = to_add_item['id']
                elif('@id' in to_add_item):
                    act_id = to_add_item['@id']
                if(act_id not in existing_ids):
                    #only unique items, as identified by the id
                    existing_list.append(to_add_item)
                    existing_ids.append(act_id)
        return existing_list

    def get_dc_authorship(self, act_dict, author_predicates):
        """
        Looks through observations to find objects of author predicates
        """
        authors = False
        if(len(author_predicates) > 0):
            authors = []
            author_ids = []
            if(OCitem.PREDICATES_OCGEN_HASOBS in act_dict):
                observations = act_dict[OCitem.PREDICATES_OCGEN_HASOBS]
                for obs in observations:
                    for pred_key, pred_objs in obs.items():
                        if pred_key in author_predicates:
                            # the current predicate is a used for authorship
                            authors = self.add_unique_entity_lists(authors, obs[pred_key])
                            # print('Author pred: ' + pred_key + ': ' + str(authors))
            if(len(authors) < 1):
                authors = False
        return authors

    def get_annotations_for_ocitem(self, graph_list, subject_uuid, subject_type, prefix_slug=False):
        """
        adds linked data annotations to a given subject_uuid
        """
        la_count = 0
        link_annotations = None
        icc = itemConstructionCache()
        cache_key = icc.make_cache_key('linkanno-', subject_uuid)
        if self.cache_entities:
            link_annotations = icc.get_cache_object(cache_key)
            if link_annotations is not None:
                la_count = len(link_annotations)
        if link_annotations is None:
            try:
                link_annotations = LinkAnnotation.objects.filter(subject=subject_uuid)
                la_count = len(link_annotations)
            except LinkAnnotation.DoesNotExist:
                la_count = 0
                link_annotations = []
            if self.cache_entities:
                icc.save_cache_object(cache_key, link_annotations)
        if la_count > 0:
            added_annotation_count = 0
            act_annotation = LastUpdatedOrderedDict()
            if(prefix_slug is not False):
                act_annotation['@id'] = prefix_slug
            elif subject_type == 'xsd:string':
                act_annotation['@id'] = '#string-' + subject_uuid  # for string annotations
            else:
                act_annotation['@id'] = URImanagement.make_oc_uri(subject_uuid, subject_type, self.cannonical_uris)
            for link_anno in link_annotations:
                # shorten the predicate uri if it's namespace is defined in the context
                add_annotation = True
                predicate_uri = URImanagement.prefix_common_uri(link_anno.predicate_uri)
                object_prefix_uri = URImanagement.prefix_common_uri(link_anno.object_uri)
                if(predicate_uri == 'skos:closeMatch' or predicate_uri == 'owl:sameAs'):
                    if(object_prefix_uri == 'dc-terms:contributor'):
                        self.dc_contrib_preds.append(act_annotation['@id'])
                        add_annotation = False
                    elif(object_prefix_uri == 'dc-terms:creator'):
                        self.dc_creator_preds.append(act_annotation['@id'])
                        add_annotation = False
                if(add_annotation):
                    added_annotation_count += 1
                    act_annotation = self.add_json_predicate_list_ocitem(act_annotation,
                                                                         predicate_uri,
                                                                         link_anno.object_uri,
                                                                         'uri')
            if(added_annotation_count > 0):
                graph_list.append(act_annotation)
        return graph_list

    def get_annotations_for_oc_gen_class(self, graph_list, class_uri):
        """
        adds linked data annotations to a given subject_uuid
        """
        la_count = 0
        alt_identifier = URImanagement.convert_prefix_to_full_uri(class_uri)
        link_annotations = None
        icc = itemConstructionCache()
        cache_key = icc.make_cache_key('linkanno-', (
                                       str(class_uri) +
                                       ' '+ str(alt_identifier)))
        if self.cache_entities:
            link_annotations = icc.get_cache_object(cache_key)
            if link_annotations is not None:
                la_count = len(link_annotations)
        if link_annotations is None:
            try:
                link_annotations = LinkAnnotation.objects.filter(Q(subject=class_uri) |
                                                                 Q(subject=alt_identifier))
                la_count = len(link_annotations)
            except LinkAnnotation.DoesNotExist:
                la_count = 0
                link_annotations = []
            if self.cache_entities:
                icc.save_cache_object(cache_key, link_annotations)
        if la_count > 0:
            act_annotation = LastUpdatedOrderedDict()
            act_annotation['@id'] = class_uri
            ent = self.get_entity_metadata(class_uri)
            if ent:
                act_annotation['label'] = ent.label
            for link_anno in link_annotations:
                # shorten the predicate uri if it's namespace is defined in the context
                predicate_uri = URImanagement.prefix_common_uri(link_anno.predicate_uri)
                object_uri_found = False
                if isinstance(link_anno.object_uri, str):
                    if len(link_anno.object_uri) > 0:
                        object_uri_found = True
                        object_prefix_uri = URImanagement.prefix_common_uri(link_anno.object_uri)
                        act_annotation = self.add_json_predicate_list_ocitem(act_annotation,
                                                                             predicate_uri,
                                                                             link_anno.object_uri,
                                                                             'uri')
            graph_list.append(act_annotation)
        return graph_list

    def add_spacetime_metadata(self, act_dict, uuid, item_type, geo_meta, event_meta):
        """
        adds geospatial and event data that links time and space information
        """
        features_dict = False  # dict of all features to be added
        feature_events = False  # mappings between features and time periods
        if geo_meta is not False:
            features_dict = LastUpdatedOrderedDict()
            feature_events = LastUpdatedOrderedDict()
            for geo in geo_meta:
                geo_id = geo.feature_id
                geo_node = '#geo-' + str(geo_id)  # the node id for database rec of the feature
                geo_node_geom = '#geo-geom-' + str(geo_id)
                geo_node_props = '#geo-props-' + str(geo_id)
                geo_node_derived = '#geo-derived-' + str(geo_id)  # node id for a derived feature
                geo_node_derived_geom = '#geo-derived-geom-' + str(geo_id)
                geo_node_derived_props = '#geo-derived-props-' + str(geo_id)
                feature_events[geo_node] = []
                geo_props = LastUpdatedOrderedDict()
                geo_props['href'] = URImanagement.make_oc_uri(uuid, item_type, self.cannonical_uris)
                geo_props['type'] = geo.meta_type
                if len(geo.note) > 0:
                    geo_props['note'] = geo.note
                if uuid != geo.uuid:
                    geo_props['reference-type'] = 'inferred'
                    geo_props['reference-uri'] = URImanagement.make_oc_uri(geo.uuid, 'subjects', self.cannonical_uris)
                    rel_meta = self.get_entity_metadata(geo.uuid)
                    if rel_meta is not False:
                        geo_props['reference-label'] = rel_meta.label
                        geo_props['reference-slug'] = rel_meta.slug
                else:
                    geo_props['reference-type'] = 'specified'
                    if self.assertion_hashes:
                        geo_props['hash_id'] = geo.hash_id
                        geo_props['feature_id'] = geo.feature_id
                if geo.specificity < 0 and self.item_type != 'projects':
                    # case where we've got reduced precision geospatial data
                    # geotile = quadtree.encode(geo.latitude, geo.longitude, abs(geo.specificity))
                    geo_props['location-precision'] = abs(geo.specificity)
                    geo_props['location-precision-note'] = 'Location data approximated as a security precaution.'
                    gmt = GlobalMercator()
                    geotile = gmt.lat_lon_to_quadtree(geo.latitude, geo.longitude, abs(geo.specificity))
                    tile_bounds = gmt.quadtree_to_lat_lon(geotile)
                    item_polygon = Polygon([[(tile_bounds[1], tile_bounds[0]),
                                             (tile_bounds[1], tile_bounds[2]),
                                             (tile_bounds[3], tile_bounds[2]),
                                             (tile_bounds[3], tile_bounds[0]),
                                             (tile_bounds[1], tile_bounds[0])
                                             ]])
                    item_f_poly = Feature(geometry=item_polygon)
                    item_f_poly.id = geo_node_derived
                    item_f_poly.geometry.id = geo_node_derived_geom
                    item_f_poly.properties.update(geo_props)
                    item_f_poly.properties['location-note'] = 'This region defines the '\
                                                              'approximate location for this item.'
                    item_f_poly.properties['id'] = geo_node_derived_props
                    features_dict[geo_node_derived] = item_f_poly
                    item_point = Point((float(geo.longitude), float(geo.latitude)))
                    item_f_point = Feature(geometry=item_point)
                    item_f_point.id = geo_node
                    item_f_point.geometry.id = geo_node_geom
                    item_f_point.properties.update(geo_props)
                    item_f_point.properties['location-note'] = 'This point defines the center of the '\
                                                               'region approximating the location for this item.'
                    item_f_point.properties['id'] = geo_node_props
                    features_dict[geo_node] = item_f_point
                elif len(geo.coordinates) > 1:
                    # here we have geo_json expressed features and geometries to use
                    if geo.specificity < 0:
                        geo_props['location-precision-note'] = 'Location data approximated as a security precaution.'
                    elif geo.specificity > 0:
                        geo_props['location-precision-note'] = 'Location data has uncertainty.'
                    else:
                        geo_props['location-precision-note'] = 'Location data available with no '\
                                                               'intentional reduction in precision.'
                    item_point = Point((float(geo.longitude), float(geo.latitude)))
                    item_f_point = Feature(geometry=item_point)
                    item_f_point.properties.update(geo_props)
                    if uuid == geo.uuid:
                        #the item itself has the polygon as it's feature
                        item_db = Point((float(geo.longitude), float(geo.latitude)))
                        if(geo.ftype == 'Polygon'):
                            coord_obj = json.loads(geo.coordinates)
                            item_db = Polygon(coord_obj)
                        elif(geo.ftype == 'MultiPolygon'):
                            coord_obj = json.loads(geo.coordinates)
                            item_db = MultiPolygon(coord_obj)
                        elif(geo.ftype == 'MultiLineString'):
                            coord_obj = json.loads(geo.coordinates)
                            item_db = MultiLineString(coord_obj)
                        item_f_db = Feature(geometry=item_db)
                        item_f_db.id = geo_node
                        item_f_db.geometry.id = geo_node_geom
                        item_f_db.properties.update(geo_props)
                        item_f_db.properties['id'] = geo_node_props
                        features_dict[geo_node] = item_f_db
                        item_f_point.id = geo_node_derived
                        item_f_point.geometry.id = geo_node_derived_geom
                        item_f_point.properties['location-region-note'] = 'This point represents the center of the '\
                                                                          'region defining the location of this item.'
                        item_f_point.properties['id'] = geo_node_derived_props
                        features_dict[geo_node_derived] = item_f_point
                    else:
                        #the item is contained within another item with a polygon or multipolygon feature
                        item_f_point.id = geo_node
                        item_f_point.geometry.id = geo_node_geom
                        item_f_point.properties['id'] = geo_node_props
                        item_f_point.properties['contained-in-region'] = True
                        item_f_point.properties['location-region-note'] = 'This point represents the center of the '\
                                                                          'region containing this item.'
                        features_dict[geo_node] = item_f_point
                else:
                    # case where the item only has a point for geo-spatial reference
                    geo_props['location-note'] = 'Location data available with no intentional reduction in precision.'
                    item_point = Point((float(geo.longitude), float(geo.latitude)))
                    item_f_point = Feature(geometry=item_point)
                    item_f_point.id = geo_node
                    item_f_point.geometry.id = geo_node_geom
                    item_f_point.properties.update(geo_props)
                    item_f_point.properties['id'] = geo_node_props
                    features_dict[geo_node] = item_f_point
            if event_meta is not False:
                # events provide chrological information, tied to geo features
                # sometimes there are more than 1 time period for each geo feature
                # in such cases, we duplicate geo features and add the different time event
                # information to the new features
                for event in event_meta:
                    rel_feature_num = 1  # default to the first geospatial feature for where the event happened
                    rel_feature_node = False
                    if event.feature_id > 0:
                        rel_feature_num = event.feature_id
                    if rel_feature_num >= 1:
                        rel_feature_node = '#geo-' + str(rel_feature_num)
                    act_event_obj = LastUpdatedOrderedDict()
                    act_event_obj = self.add_when_json(act_event_obj, uuid, item_type, event)
                    if rel_feature_node is not False and feature_events is not False:
                        feature_events[rel_feature_node].append(act_event_obj)
            if features_dict is not False :
                if feature_events is not False:
                    for node_key, event_list in feature_events.items():
                        # update the feature with the first event "when" information
                        if len(event_list) > 0:
                            features_dict[node_key].update(event_list[0])
                            event_i = 1
                            for event in event_list:
                                if(event_i <= 1):
                                    # add the time info to the feature
                                    old_feature = features_dict[node_key]
                                    old_geo_id = old_feature.geometry['id']
                                    old_prop_id = old_feature.properties['id']
                                    features_dict[node_key].update(event)
                                else:
                                    act_feature = copy.deepcopy(old_feature)
                                    # now add new node ids for the new features created to for the event
                                    new_node = node_key + '-event-' + str(event_i)
                                    act_feature.id = new_node
                                    act_feature.geometry['id'] = old_geo_id + '-event-' + str(event_i)
                                    act_feature.properties['id'] = old_prop_id + '-event-' + str(event_i)
                                    act_feature.update(event)  # add the time info to the new feature
                                    features_dict[new_node] = act_feature
                                    del(act_feature)
                                event_i += 1
                feature_keys = list(features_dict.keys())
                if len(feature_keys) < 1:
                    del features_dict[feature_keys[0]]['id']  # remove the conflicting id
                    # only 1 feature, so item is not a feature collection
                    act_dict.update(features_dict[feature_keys[0]])
                else:
                    feature_list = []  # multiple features, so item has a feature collection
                    for node_key, feature in features_dict.items():
                        feature_list.append(feature)
                    item_fc = FeatureCollection(feature_list)
                    act_dict.update(item_fc)
        return act_dict

    def add_when_json(self, act_dict, uuid, item_type, event):
        """
        adds when (time interval or instant) data
        """
        when = LastUpdatedOrderedDict()
        when['id'] = '#event-when-' + str(event.event_id)
        when['type'] = event.when_type
        when['type'] = event.meta_type
        if(event.earliest != event.start):
            # when['earliest'] = int(event.earliest)
            pass
        when['start'] = ISOyears().make_iso_from_float(event.start)
        when['stop'] = ISOyears().make_iso_from_float(event.stop)
        if(event.latest != event.stop):
            # when['latest'] = int(event.latest)
            pass
        if(event.uuid != uuid):
            when['reference-type'] = 'inferred'
            when['reference-uri'] = URImanagement.make_oc_uri(event.uuid, 'subjects', self.cannonical_uris)
            rel_meta = self.get_entity_metadata(event.uuid)
            if(rel_meta is not False):
                when['reference-label'] = rel_meta.label
        else:
            when['reference-type'] = 'specified'
            if self.assertion_hashes:
                when['hash_id'] = event.hash_id
        act_dict['when'] = when
        return act_dict

    def add_media_json(self, act_dict, media):
        """
        adds media files
        """
        if media is not False:
            media_list = []
            thumb_missing = True
            pdf_doc = False
            for media_item in media:
                list_item = LastUpdatedOrderedDict()
                list_item['id'] = media_item.file_uri
                list_item['type'] = media_item.file_type
                if media_item.file_type == 'oc-gen:thumbnail':
                    thumb_missing = False
                list_item['dc-terms:hasFormat'] = media_item.mime_type_uri
                if 'application/pdf' in media_item.mime_type_uri:
                    pdf_doc = True
                list_item['dcat:size'] = float(media_item.filesize)
                if self.assertion_hashes:
                    if hasattr(media_item, 'hash_id'):
                        list_item['hash_id'] = media_item.hash_id
                    else:
                        list_item['hash_id'] = media_item.id
                media_list.append(list_item)
            if thumb_missing and pdf_doc:
                # we have a PDF with a default thumbnail
                list_item = LastUpdatedOrderedDict()
                list_item['id'] = Mediafile.PDF_DEFAULT_THUMBNAIL
                list_item['type'] = 'oc-gen:thumbnail'
                media_list.append(list_item)
            act_dict['oc-gen:has-files'] = media_list
        return act_dict

    def add_document_json(self, act_dict, document):
        """
        adds document content
        """
        if(document is not False):
            lan_obj = Languages()
            act_dict['rdf:HTML'] = lan_obj.make_json_ld_value_obj(document.content,
                                                                  document.localized_json)
        return act_dict

    def add_project_hero_images(self, act_dict, hero_list):
        """
        adds hero pictures for a project,
        uses the "foaf:depiction" predicate
        """
        if hero_list is not False:
            media_list = []
            for media_item in hero_list:
                list_item = LastUpdatedOrderedDict()
                list_item['id'] = media_item.file_uri
                list_item['type'] = media_item.file_type
                list_item['dc-terms:hasFormat'] = media_item.mime_type_uri
                list_item['dcat:size'] = float(media_item.filesize)
                if self.assertion_hashes:
                    if hasattr(media_item, 'hash_id'):
                        list_item['hash_id'] = media_item.hash_id
                    else:
                        list_item['hash_id'] = media_item.id
                media_list.append(list_item)
            act_dict['foaf:depiction'] = media_list
        return act_dict

    def get_entity_metadata(self, identifier):
        """
        gets metadata about an item from a look-up to the entity class
        """
        entity_item = False
        if identifier in self.entity_metadata:
            # check first to see if the manifest item is already in memory
            entity_item = self.entity_metadata[identifier]
        else:
            if self.cache_entities:
                icc = itemConstructionCache()
                entity_item = icc.get_entity_w_thumbnail(identifier)
                if entity_item is not False:
                    self.entity_metadata[identifier] = entity_item
            else:
                ent = Entity()
                ent.get_thumbnail = True
                found = ent.dereference(identifier)
                if found:
                    entity_item = ent
                    self.entity_metadata[identifier] = entity_item
        if entity_item is not False:
            if entity_item.slug == 'oc-gen-has-note':
                entity_item.class_uri = 'variable'
        return entity_item

    def make_dict_template_safe(self, node):
        """ Makes a JSON-LD structured dict object into a dict object safe for
            use with templates, meaning no funny characters in the keys. Probably a
            temporary hack
        """
        template_safe_dict = LastUpdatedOrderedDict()
        for key, item in node.items():
            safe_key = key.replace(':', '___')
            safe_key = safe_key.replace('@', 'at__')
            if isinstance(item, dict):
                template_safe_dict[safe_key] = self.make_dict_template_safe(item)
            elif isinstance(item, list):
                new_list = []
                for list_item in item:
                    if isinstance(list_item, dict):
                        new_item = self.make_dict_template_safe(list_item)
                        new_list.append(new_item)
                    else:
                        new_list.append(list_item)
                template_safe_dict[safe_key] = new_list
            else:
                template_safe_dict[safe_key] = item
        return template_safe_dict


class itemConstructionCache():
    """
    methods for using the Reddis cache to
    streamline making item JSON-LD
    """

    def __init__(self):
        self.redis_ok = True
        self.print_caching = False

    def get_entity_w_thumbnail(self, identifier):
        """ gets an entity with thumbnail (useful for item json) """
        m_cache = MemoryCache()
        return m_cache.get_entity(identifier)
    
    def make_cache_key(self, prefix, identifier):
        """ makes a valid OK cache key """
        m_cache = MemoryCache()
        return m_cache.make_cache_key(prefix, identifier)

    def make_memory_cache_key(self, prefix, identifier):
        """ makes a valid OK cache key """
        m_cache = MemoryCache()
        return m_cache.make_cache_key(prefix, identifier)

    def get_cache_object(self, key):
        """ gets a cached reddis object """
        m_cache = MemoryCache()
        return m_cache.get_cache_object(key)

    def save_cache_object(self, key, obj):
        """ saves a cached reddis object """
        m_cache = MemoryCache()
        return m_cache.save_cache_object(key, obj)