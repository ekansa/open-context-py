import time
import json
import geojson
import copy
from geojson import Feature, Point, Polygon, MultiPolygon, GeometryCollection, FeatureCollection
from geojson import MultiPoint, MultiLineString, LineString
from collections import OrderedDict
from django.conf import settings
from django.db import models
from django.db.models import Q
from opencontext_py.libs.rootpath import RootPath
from opencontext_py.libs.languages import Languages
from opencontext_py.libs.isoyears import ISOyears
from opencontext_py.libs.general import LastUpdatedOrderedDict, DCterms
from opencontext_py.libs.globalmaptiles import GlobalMercator
from opencontext_py.apps.entities.uri.models import URImanagement
from opencontext_py.apps.ocitems.ocitem.itemkeys import ItemKeys
from opencontext_py.apps.ocitems.ocitem.caching import ItemGenerationCache
from opencontext_py.apps.ocitems.ocitem.partsjsonld import PartsJsonLD
from opencontext_py.apps.ocitems.assertions.models import Assertion
from opencontext_py.apps.ocitems.assertions.containment import Containment
from opencontext_py.apps.ocitems.projects.models import Project
from opencontext_py.apps.ocitems.projects.metadata import ProjectMeta


class ItemSpatialTemporal():
    """ Methods for adding spatial context, containment, and spatial temporal
        data to an Open Context Item JSON-LD object
    """

    def __init__(self):
        self.project_uuid = None
        self.manifest = None
        dc_terms_obj = DCterms()
        self.DC_META_PREDS = dc_terms_obj.get_dc_terms_list()
        self.item_gen_cache = ItemGenerationCache()
        rp = RootPath()
        self.base_url = rp.get_baseurl()
        self.contexts = False
        self.linked_contexts = False
        self.geo_meta = False  # 
        self.temporal_meta = False
        self.event_meta = False
        self.contents = False
        self.assertion_hashes = False
        self.cannonical_uris = True
        self.class_uri_list = []  # uris of item classes used in this item
        self.parent_context_list = []  # list of parent context labels, used for making a dc-terms:Title
    
    def get_spatial_temporal_context(self):
        """ gets the item spatial context """
        act_contain = Containment()
        if self.manifest.item_type == 'subjects':
            # get item geospatial and chronological metadata if subject item
            # will do it differently if not a subject item
            parents = act_contain.get_parents_by_child_uuid(self.manifest.uuid)
            self.contexts = parents
            # prepare a list of contexts (including the current item) to check for
            # geospatial and event / chronology metadata
            subject_list = act_contain.contexts_list
            subject_list.insert(0, self.manifest.uuid)
            self.geo_meta = act_contain.get_geochron_from_subject_list(subject_list, 'geo')
            self.temporal_meta = act_contain.get_geochron_from_subject_list(subject_list, 'temporal')
            self.event_meta = act_contain.get_geochron_from_subject_list(subject_list, 'event')
            # now get any children items, contained in this "subjects" item 
            act_contain = Containment()
            self.contents = act_contain.get_children_by_parent_uuid(self.manifest.uuid)
        else:
            parents = act_contain.get_related_context(self.manifest.uuid)
            self.contexts = False
            self.linked_contexts = parents
            if self.manifest.item_type == 'projects':
                # get project metadata objects directly
                pm = ProjectMeta()
                project = self.item_gen_cache.get_project_model_object(self.manifest.uuid)
                sub_projects = self.item_gen_cache.get_project_subprojects(self.manifest.uuid)
                if project is not None:
                    if isinstance(project.meta_json, dict):
                        if Project.META_KEY_GEO_SPECIFICITY in project.meta_json:
                            # the project has some default geographic specificity noted
                            # use this value when making geo_meta
                            pm.project_specificity = project.meta_json[Project.META_KEY_GEO_SPECIFICITY]
                self.geo_meta = pm.get_project_geo_from_db(self.manifest.uuid)
                if self.geo_meta is False:
                    # make geospatial metadata for the project, and sub-projects if they exist
                    pm.make_geo_meta(self.manifest.uuid, sub_projects)
                    self.geo_meta = pm.geo_objs
            act_contain = Containment()
            if self.geo_meta is False:
                self.geo_meta = act_contain.get_related_geochron(self.manifest.uuid,
                                                                 self.manifest.item_type,
                                                                 'geo')
            if self.temporal_meta is False:
                self.temporal_meta = act_contain.get_related_geochron(self.manifest.uuid,
                                                                      self.manifest.item_type,
                                                                      'temporal')
                if self.temporal_meta is False:
                    # now look in the project for temporal metadata
                    self.temporal_meta = act_contain.get_temporal_from_project(self.manifest.project_uuid)
            if self.event_meta is False:
                self.event_meta = act_contain.get_related_geochron(self.manifest.uuid,
                                                                   self.manifest.item_type,
                                                                   'event')
    
    def add_json_ld_geojson_contexts(self, json_ld):
        """ adds context information if present """
        act_context = None
        if isinstance(self.contexts, dict):
            if len(self.contexts) > 0:
                # add spatial context, direct parents of a given subject item
                context_predicate = ItemKeys.PREDICATES_OCGEN_HASCONTEXTPATH
                act_context = self.make_spatial_context_json_ld(self.contexts)
        elif isinstance(self.linked_contexts, dict):
            if len(self.linked_contexts) > 0:
                # add related spatial contexts (related to a linked subject)
                context_predicate = ItemKeys.PREDICATES_OCGEN_HASLINKEDCONTEXTPATH
                act_context = self.make_spatial_context_json_ld(self.linked_contexts)
        # first make the GeoJSON part of the JSON-LD
        json_ld = self.add_geojson(json_ld)
        # now add the spatial context part (open context specific)
        if act_context is not None:
            json_ld[context_predicate] = act_context
        return json_ld
    
    def add_contents_json_ld(self, json_ld):
        """ adds subject items contained in the current item """
        if isinstance(self.contents, dict):
            if len(self.contents) > 0:
                # make a list of all the UUIDs for children items
                act_children_uuids = []
                for tree_node, children in self.contents.items():
                    for child_uuid in children:
                        if child_uuid not in act_children_uuids:
                            act_children_uuids.append(child_uuid)
                # adds child contents, with different treenodes
                parts_json_ld = PartsJsonLD()
                # get manifest objects for all the children items, for use in making JSON_LD
                parts_json_ld.get_manifest_objects_from_uuids(act_children_uuids)
                parts_json_ld.class_uri_list += self.class_uri_list
                for tree_node, children in self.contents.items():
                    act_children = LastUpdatedOrderedDict()
                    act_children['id'] = tree_node
                    act_children['type'] = 'oc-gen:contents'
                    for child_uuid in children:
                        act_children = parts_json_ld.addto_predicate_list(act_children,
                                                                          ItemKeys.PREDICATES_OCGEN_CONTAINS,
                                                                          child_uuid,
                                                                          'subjects')
                        self.class_uri_list += parts_json_ld.class_uri_list
                json_ld[ItemKeys.PREDICATES_OCGEN_HASCONTENTS] = act_children
        return json_ld
    
    def add_geojson(self, json_ld):
        """
        adds geospatial and event data that links time and space information
        """
        uuid = self.manifest.uuid
        item_type = self.manifest.item_type
        geo_meta = self.geo_meta
        event_meta = self.event_meta
        features_dict = False  # dict of all features to be added
        feature_events = False  # mappings between features and time periods
        if geo_meta is not False:
            # print('here!' + str(geo_meta))
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
                    geo_props['reference-uri'] = URImanagement.make_oc_uri(geo.uuid,
                                                                           'subjects',
                                                                           self.cannonical_uris)
                    
                    rel_meta = self.item_gen_cache.get_entity(geo.uuid)
                    if rel_meta is not False:
                        geo_props['reference-label'] = rel_meta.label
                        geo_props['reference-slug'] = rel_meta.slug
                else:
                    geo_props['reference-label'] = self.manifest.label
                    geo_props['reference-type'] = 'specified'
                    if self.assertion_hashes:
                        geo_props['hash_id'] = geo.hash_id
                        geo_props['feature_id'] = geo.feature_id
                if geo.specificity < 0 and self.manifest.item_type != 'projects':
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
                        if geo.ftype == 'Polygon':
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
                                if event_i <= 1:
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
                    json_ld.update(features_dict[feature_keys[0]])
                else:
                    feature_list = []  # multiple features, so item has a feature collection
                    for node_key, feature in features_dict.items():
                        feature_list.append(feature)
                    item_fc = FeatureCollection(feature_list)
                    json_ld.update(item_fc)
        return json_ld

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
        if event.latest != event.stop:
            # when['latest'] = int(event.latest)
            pass
        if event.uuid != uuid:
            # we're inheriting / inferring event metadata from a parent context
            when['reference-type'] = 'inferred'
            when['reference-uri'] = URImanagement.make_oc_uri(event.uuid, 'subjects', self.cannonical_uris)
            rel_meta = self.item_gen_cache.get_entity(event.uuid)
            if rel_meta is not False:
                when['reference-label'] = rel_meta.label
        else:
            # metadata is specified for this specific item
            when['reference-type'] = 'specified'
            when['reference-label'] = self.manifest.label
            if self.assertion_hashes:
                when['hash_id'] = event.hash_id
        act_dict['when'] = when
        return act_dict
    
    def make_spatial_context_json_ld(self, raw_contexts):
        """ adds context information, if present """
        #adds parent contents, with different treenodes
        first_node = True
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
            parts_json_ld = PartsJsonLD()
            parts_json_ld.class_uri_list += self.class_uri_list
            if len(parents) > 3:
                # lots of parents, so probably not worth trying to use the cache.
                # makes more sense look these all up in the manifest in 1 query
                # get manifest objects for all the parent items, for use in making JSON_LD
                parts_json_ld.get_manifest_objects_from_uuids(parents)
            for parent_uuid in parents:
                act_context = parts_json_ld.addto_predicate_list(act_context,
                                                                 ItemKeys.PREDICATES_OCGEN_HASPATHITEMS,
                                                                 parent_uuid,
                                                                 'subjects')
                self.class_uri_list += parts_json_ld.class_uri_list
            if first_node:
                # set aside a list of parent labels to use for making a dc-term:title
                first_node = False
                if ItemKeys.PREDICATES_OCGEN_HASPATHITEMS in act_context:
                    for parent_obj in act_context[ItemKeys.PREDICATES_OCGEN_HASPATHITEMS]:
                        self.parent_context_list.append(parent_obj['label'])
        return act_context