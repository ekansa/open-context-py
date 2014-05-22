import geojson
from geojson import Feature, Point, Polygon, GeometryCollection, FeatureCollection
from collections import OrderedDict
from django.conf import settings
from django.db import models
from opencontext_py.libs.globalmaptiles import GlobalMercator
from opencontext_py.apps.ocitems.manifest.models import Manifest as Manifest
from opencontext_py.apps.ocitems.assertions.models import Assertion, Containment
from opencontext_py.apps.ocitems.predicates.models import Predicate
from opencontext_py.apps.ocitems.strings.models import OCstring
from opencontext_py.apps.ldata.linkannotations.models import LinkAnnotation
from opencontext_py.apps.ldata.linkentities.models import LinkEntity


# OCitem is a very general class for all Open Context items.
# This class is used to make a JSON-LD output from data returned from the database via other apps
class OCitem():
    PREDICATES_DCTERMS_PUBLISHED = 'dc-terms:published'
    PREDICATES_DCTERMS_CREATOR = 'dc-terms:creator'
    PREDICATES_DCTERMS_CONTRIBUTOR = 'dc-terms:contributor'
    PREDICATES_DCTERMS_ISPARTOF = 'dc-terms:isPartOf'
    PREDICATES_OCGEN_HASCONTEXTPATH = 'oc-gen:has-context-path'
    PREDICATES_OCGEN_HASPATHITEMS = 'oc-gen:has-path-items'
    PREDICATES_OCGEN_HASCONTENTS = 'oc-gen:has-contents'
    PREDICATES_OCGEN_CONTAINS = 'oc-gen:contains'
    PREDICATES_OCGEN_HASOBS = 'oc-gen:has-obs'
    PREDICATES_OCGEN_SOURCEID = 'oc-gen:sourceID'
    PREDICATES_OCGEN_OBSTATUS = 'oc-gen:obsStatus'
    PREDICATES_OCGEN_HASGEOREFSOURCE = 'oc-gen:has-geo-ref-source'
    PREDICATES_OCGEN_HASCHRONOREFSOURCE = 'oc-gen:has-chrono-ref-source'

    def __init__(self):
        self.uuid = False
        self.slug = False
        self.label = False
        self.item_type = False
        self.published = False
        self.manifest = False
        self.assertions = False
        self.contexts = False
        self.contents = False
        self.geo = False
        self.chrono = False

    def get_item(self, actUUID):
        """
        gets data for an item
        """
        self.uuid = actUUID
        self.get_manifest()
        self.get_assertions()
        self.get_parent_contexts()
        self.get_contained()
        self.get_geochrono_metadata()
        self.construct_json_ld()
        return self

    def get_manifest(self):
        """
        gets basic metadata about the item from the Manifest app
        """
        self.manifest = Manifest.objects.get(uuid=self.uuid)
        self.slug = self.manifest.slug
        self.label = self.manifest.label
        self.project_uuid = self.manifest.project_uuid
        self.item_type = self.manifest.item_type
        self.published = self.manifest.published
        return self.manifest

    def get_assertions(self):
        """
        gets item descriptions and linking relations for the item from the Assertion app
        """
        act_contain = Containment()
        self.assertions = Assertion.objects.filter(uuid=self.uuid) \
                                           .exclude(predicate_uuid=Assertion.PREDICATES_CONTAINS)
        return self.assertions

    def get_parent_contexts(self):
        """
        gets item parent context
        """
        act_contain = Containment()
        self.contexts = act_contain.get_parents_by_child_uuid(self.uuid)
        if(self.item_type == 'subjects'):
            # get item geospatial and chronological metadata if subject item
            # will do it differently if not a subject item
            subject_list = act_contain.contexts_list
            subject_list.insert(0, self.uuid)
            self.geo = act_contain.get_geochron_from_subject_list(subject_list, 'geo')
            self.chrono = act_contain.get_geochron_from_subject_list(subject_list, 'chrono')
        return self.contexts

    def get_geochrono_metadata(self):
        """
        gets item geo and chronological metadata
        """
        if(self.geo is False and self.chrono is False):
            act_contain = Containment()
            self.geo = act_contain.get_related_geochron(self.uuid, self.item_type, 'geo')
            self.chrono = act_contain.get_related_geochron(self.uuid, self.item_type, 'chrono')
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

    def construct_json_ld(self):
        """
        creates JSON-LD documents for an item
        currently, it's just here to make some initial JSON while we learn python
        """
        item_con = ItemConstruction()
        json_ld = item_con.intialize_json_ld(self.assertions)
        json_ld['id'] = item_con.make_oc_uri(self.uuid, self.item_type)
        json_ld['label'] = self.label
        json_ld['@type'] = [{'id': self.manifest.class_uri}]
        if(len(self.contexts) > 0):
            #adds parent contents, with different treenodes
            act_context = LastUpdatedOrderedDict()
            for tree_node, r_parents in self.contexts.items():
                act_context = LastUpdatedOrderedDict()
                # change the parent node to context not contents
                tree_node = tree_node.replace('contents', 'context')
                act_context['id'] = tree_node
                 # now reverse the list of parent contexts, so top most parent context is first, followed by children contexts
                parents = r_parents[::-1]
                for parent_uuid in parents:
                    act_context = item_con.add_json_predicate_list_ocitem(act_context,
                                                                          self.PREDICATES_OCGEN_HASPATHITEMS,
                                                                          parent_uuid, 'subjects')
            json_ld[self.PREDICATES_OCGEN_HASCONTEXTPATH] = act_context
        if(len(self.contents) > 0):
            #adds child contents, with different treenodes
            for tree_node, children in self.contents.items():
                act_children = LastUpdatedOrderedDict()
                act_children['id'] = tree_node
                for child_uuid in children:
                    act_children = item_con.add_json_predicate_list_ocitem(act_children,
                                                                           self.PREDICATES_OCGEN_CONTAINS,
                                                                           child_uuid, 'subjects')
            json_ld[self.PREDICATES_OCGEN_HASCONTENTS] = act_children
        # add predicate - object (descriptions) to the item
        json_ld = item_con.add_descriptive_assertions(json_ld, self.assertions)
        json_ld = item_con.add_spacetime_metadata(json_ld,
                                                  self.uuid,
                                                  self.item_type,
                                                  self.geo,
                                                  self.chrono)
        json_ld[self.PREDICATES_DCTERMS_PUBLISHED] = self.published.date().isoformat()
        json_ld = item_con.add_json_predicate_list_ocitem(json_ld,
                                                          self.PREDICATES_DCTERMS_ISPARTOF,
                                                          self.project_uuid, 'projects')
        item_con.add_item_labels = False
        if(self.item_type in settings.SLUG_TYPES):
            json_ld = item_con.add_json_predicate_list_ocitem(json_ld,
                                                              'owl:sameAs',
                                                              self.slug, self.item_type)
        # add linked data annotations
        json_ld = item_con.add_linked_data_graph(json_ld)
        self.json_ld = json_ld
        item_con.__del__()
        return self.json_ld


class LastUpdatedOrderedDict(OrderedDict):
    """
    Stores items in the order the keys were last added
    """
    def __setitem__(self, key, value):
        if key in self:
            del self[key]
        OrderedDict.__setitem__(self, key, value)


class ItemConstruction():
    """
    General purpose functions for building Open Context items
    """
    base_context = False
    add_item_labels = True
    add_media_thumnails = True
    add_subject_class = True
    add_linked_data_labels = True
    cannonical_uris = True
    predicates = {}
    obs_list = list()
    var_list = list()
    link_list = list()
    type_list = list()
    item_metadata = {}

    def __init__(self):
        self.add_item_labels = True
        self.add_linked_data_labels = True
        self.add_media_thumnails = True
        self.add_subject_class = True
        self.cannonical_uris = True
        self.obs_list = list()
        self.predicates = {}
        self.var_list = list()
        self.link_list = list()
        self.type_list = list()
        self.item_metadata = {}
        context = LastUpdatedOrderedDict()
        context['id'] = '@id'
        context['type'] = '@type'
        context['rdf'] = 'http://www.w3.org/1999/02/22-rdf-syntax-ns#'
        context['rdfs'] = 'http://www.w3.org/2000/01/rdf-schema#'
        context['label'] = 'rdfs:label'
        context['xsd'] = 'http://www.w3.org/2001/XMLSchema#'
        context['skos'] = 'http://www.w3.org/2004/02/skos/core#'
        context['owl'] = 'http://www.w3.org/2002/07/owl#'
        context['dc-terms'] = 'http://purl.org/dc/terms/'
        context['uuid'] = 'dc-terms:identifier'
        context['bibo'] = 'http://purl.org/ontology/bibo/'
        context['foaf'] = 'http://xmlns.com/foaf/0.1/'
        context['cidoc-crm'] = 'http://www.cidoc-crm.org/cidoc-crm/'
        context['oc-gen'] = 'http://opencontext.org/vocabularies/oc-general/'
        context['oc-pred'] = 'http://opencontext.org/predicates/'
        context['location-inferred-uri'] = 'oc-gen:geojson-location-inferred-uri'
        context['location-inferred-label'] = 'oc-gen:geojson-location-inferred-label'
        context['location-precision'] = 'oc-gen:geojson-location-precision'
        context['location-note'] = 'oc-gen:geojson-location-note'
        self.base_context = context

    def __del__(self):
        self.var_list = list()
        self.link_list = list()
        self.type_list = list()

    def intialize_json_ld(self, assertions):
        """
        creates a json_ld (ordered) dictionary with a context
        """
        json_ld = LastUpdatedOrderedDict()
        context = self.base_context
        raw_pred_list = list()
        pred_types = {}
        for assertion in assertions:
            if(assertion.obs_num not in self.obs_list):
                self.obs_list.append(assertion.obs_num)
            if(assertion.predicate_uuid not in raw_pred_list):
                raw_pred_list.append(assertion.predicate_uuid)
                if any(assertion.object_type in item_type for item_type in settings.ITEM_TYPES):
                    pred_types[assertion.predicate_uuid] = '@id'
                else:
                    pred_types[assertion.predicate_uuid] = assertion.object_type
        # prepares dictionary objects for each predicate
        for pred_uuid in raw_pred_list:
            pmeta = self.get_item_metadata(pred_uuid)
            if(pmeta is not False):
                p_data = LastUpdatedOrderedDict()
                p_data['owl:sameAs'] = self.make_oc_uri(pred_uuid, pmeta.item_type)
                p_data['label'] = pmeta.label
                p_data['slug'] = pmeta.slug
                p_data['uuid'] = pmeta.uuid
                # p_data['owl:sameAs'] = self.make_oc_uri(pmeta.slug, pmeta.item_type)
                p_data['oc-gen:predType'] = pmeta.class_uri
                p_data['@type'] = pred_types[pred_uuid]
                if(pmeta.class_uri == 'variable'):
                    self.var_list.append(p_data)
                elif(pmeta.class_uri == 'link'):
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
            del v_data['uuid']
            context[key] = v_data
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
            context[key] = l_data
            l += 1
        json_ld['@context'] = context
        return json_ld

    def add_descriptive_assertions(self, act_dict, assertions):
        """
        adds descriptive assertions (descriptive properties, non spatial containment links)
        to items
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
                            act_obs[OCitem.PREDICATES_OCGEN_OBSTATUS] = 'not active'
                        add_obs_def = False
                    if(assertion.predicate_uuid in self.predicates):
                        act_pred_key = self.predicates[assertion.predicate_uuid]
                        act_obs = self.add_predicate_value(act_obs, act_pred_key, assertion)
            observations.append(act_obs)
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
            if (assertion.object_type == 'xsd:string'):
                new_object_item = LastUpdatedOrderedDict()
                new_object_item['id'] = '#string-' + str(assertion.object_uuid)
                try:
                    string_item = OCstring.objects.get(uuid=assertion.object_uuid)
                    new_object_item[assertion.object_type] = string_item.content
                except OCstring.DoesNotExist:
                    new_object_item[assertion.object_type] = 'string content missing'
                act_list.append(new_object_item)
            elif (assertion.object_type == 'xsd:date'):
                act_list.append(assertion.data_date.date().isoformat())
            else:
                act_list.append(assertion.data_num)
            act_dict[act_pred_key] = act_list
            return act_dict

    def add_json_predicate_list_ocitem(self, act_dict, act_pred_key, object_id, item_type):
        """
        creates a list for an act_predicate of the json_ld dictionary object if it doesn't exist
        adds a list item of a dictionary object for a linked Open Context item
        """
        if act_pred_key in act_dict:
            act_list = act_dict[act_pred_key]
        else:
            act_list = []
        new_object_item = LastUpdatedOrderedDict()
        if(item_type != 'uri' and object_id[:7] != 'http://' and object_id[:8] != 'https://'):
            new_object_item['id'] = self.make_oc_uri(object_id, item_type)
            if self.add_item_labels:
                manifest_item = self.get_item_metadata(object_id)
                if(manifest_item is not False):
                    new_object_item['label'] = manifest_item.label
                else:
                    new_object_item['label'] = 'Item not in manifest'
            if(item_type in settings.SLUG_TYPES):
                new_object_item['owl:sameAs'] = self.make_oc_uri(manifest_item.slug, item_type)
        else:
            new_object_item['id'] = object_id
            if(self.add_linked_data_labels):
                try:
                    link_item = LinkEntity.objects.get(uri=object_id)
                    new_object_item['label'] = link_item.label
                except LinkEntity.DoesNotExist:
                    new_object_item['label'] = 'Label not known'
        act_list.append(new_object_item)
        act_dict[act_pred_key] = act_list
        return act_dict

    def add_linked_data_graph(self, act_dict):
        """
        adds graph of linked data annotations
        """
        graph_list = []
        #add linked data annotations for predicates
        for (predicate_uuid, slug) in self.predicates.items():
            graph_list = self.get_annotations_for_ocitem(graph_list, predicate_uuid, 'predicates', slug)
        #add linked data annotations for types
        for type_uuid in self.type_list:
            graph_list = self.get_annotations_for_ocitem(graph_list, type_uuid, 'types')
        if(len(graph_list) > 0):
            act_dict['@graph'] = graph_list
        return act_dict

    def get_annotations_for_ocitem(self, graph_list, subject_uuid, subject_type, slug=False):
        """
        adds linked data annotations to a given subject_uuid
        """
        la_count = 0
        try:
            link_annotations = LinkAnnotation.objects.filter(uuid=subject_uuid)
            la_count = len(link_annotations)
        except LinkAnnotation.DoesNotExist:
            la_count = 0
        if(la_count > 0):
            act_annotation = LastUpdatedOrderedDict()
            if(slug is not False):
                act_annotation['@id'] = self.make_oc_uri(slug, subject_type)
            else:
                act_annotation['@id'] = self.make_oc_uri(subject_uuid, subject_type)
            for link_anno in link_annotations:
                # shorten the predicate uri if it's namespace is defined in the context
                predicate_uri = self.shorten_context_namespace(link_anno.predicate_uri)
                act_annotation = self.add_json_predicate_list_ocitem(act_annotation,
                                                                     predicate_uri,
                                                                     link_anno.object_uri,
                                                                     'uri')
            graph_list.append(act_annotation)
        return graph_list

    def add_spacetime_metadata(self, act_dict, uuid, item_type, geo, chrono):
        """
        adds geospatial and chronological data
        """
        if(geo is not False):
            item_features = False
            geo_props = LastUpdatedOrderedDict()
            if(uuid != geo.uuid):
                geo_props['location-inferred-uri'] = self.make_oc_uri(geo.uuid, 'subjects')
                rel_meta = self.get_item_metadata(uuid)
                if(rel_meta is not False):
                    geo_props['location-inferred-label'] = rel_meta.label
            if(geo.specificity < 0):
                # case where we've got reduced precision geospatial data
                # geotile = quadtree.encode(geo.latitude, geo.longitude, abs(geo.specificity))
                geo_props['location-precision'] = abs(geo.specificity)
                geo_props['location-note'] = 'Location data has intentionally reduced spatial precision'
                gmt = GlobalMercator()
                geotile = gmt.lat_lon_to_quadtree(geo.latitude, geo.longitude, abs(geo.specificity))
                tile_bounds = gmt.quadtree_to_lat_lon(geotile)
                item_polygon = Polygon([[(tile_bounds[1], tile_bounds[0]),
                                         (tile_bounds[1], tile_bounds[2]),
                                         (tile_bounds[3], tile_bounds[2]),
                                         (tile_bounds[3], tile_bounds[0]),
                                         (tile_bounds[1], tile_bounds[0])
                                         ]])
                item_point = Point((float(geo.longitude), float(geo.latitude)))
                item_f_geocol = GeometryCollection([item_polygon, item_point])
                item_f_geocol.id = '#geo-' + geotile
                item_f_geocol.properties = geo_props
                item_features = [item_f_geocol]
            elif(len(geo.geo_json) > 1):
                # here we have geo_json expressed features and geometries to use
                #do something
            else:
                # case where the item only has a point for geo-spatial reference
                geo_props['location-note'] = 'Location data available with no intentional reduction in precision'
                item_point = Point((float(geo.longitude), float(geo.latitude)))
                item_f_point = Feature(geometry=item_point)
                item_f_point.id = '#geo-1'
                item_f_point.properties = geo_props
                item_features = [item_f_point]
            if(item_features is not False):
                if(len(item_features)>1):
                    # more than one feature, bundle them in a feature collection
                    item_fc = FeatureCollection(item_features)
                    act_dict.update(item_fc)
                else:
                    # only one feature, make a geo_json feature
                    act_dict.update(item_features[0])
        return act_dict

    def shorten_context_namespace(self, uri):
        """
        checks to see if a name space has been defined, and if so, use its prefix
        """
        context = self.base_context
        for prefix in context:
            namespace = str(context[prefix])
            if(uri.find(namespace) == 0):
                uri = uri.replace(namespace, (prefix + ":"))
                break
        return uri

    def make_oc_uri(self, uuid, item_type):
        """
        creates a URI for an item based on its uuid and its item_type
        """
        uri = False
        uuid = str(uuid)
        item_type = str(item_type)
        if(self.cannonical_uris):
            uri = settings.CANONICAL_HOST + "/" + item_type + "/" + uuid
        else:
            uri = "http://" + settings.HOSTNAME + "/" + item_type + "/" + uuid
        return uri

    def get_item_metadata(self, uuid):
        """
        gets metadata about an item from the manifest table
        """
        if(uuid in self.item_metadata):
            # check first to see if the manifest item is already in memory
            manifest_item = self.item_metadata[uuid]
        else:    
            manifest_item = False
            try:
                manifest_item = Manifest.objects.get(uuid=uuid)
                self.item_metadata[uuid] = manifest_item
            except Manifest.DoesNotExist:
                return False
        return maniifest_item
