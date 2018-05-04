import time
import json
from collections import OrderedDict
from django.conf import settings
from django.db import models
from django.db.models import Q
from opencontext_py.libs.rootpath import RootPath
from opencontext_py.libs.languages import Languages
from opencontext_py.libs.isoyears import ISOyears
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.apps.entities.uri.models import URImanagement
from opencontext_py.apps.ocitems.ocitem.caching import ItemGenerationCache
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.entities.entity.models import Entity


# ItemJsonLD is used to make JSON-LD output for OC-Items
class PartsJsonLD():
    
    ITEM_TYPE_CLASS_LIST = [
        'subjects',
        'media',
        'persons'
    ]
    
    ITEM_TYPE_MANIFEST_LIST = [
        'subjects'
        'documents',
        'projects',
        'tables'
    ]
    
    # item types to dereference in the project context / vocabulary
    ITEM_TYPE_PROJ_VOCAB_LIST = [
        'predicates',
        'types',
        'persons'
    ]

    def __init__(self):
        self.item_gen_cache = ItemGenerationCache()
        rp = RootPath()
        self.base_url = rp.get_baseurl()
        self.class_uri_list = []  # uris of item classes used in this item
        self.manifest_obj_dict = {}  # manifest objects, in a dict with uuid as key
        self.proj_context_json_ld = {}  # general project context JSON-LD, with @graph of predicates, types
        self.stable_id_predicate = False  # predicate to use to add a stable ID to an entity
        self.stable_id_prefix_limit = False  # limit adding stable ID to the following URI prefix
        self.predicate_uri_as_stable_id = False  # add the predicate full URI as a stable id with the stable_id_predicate
        
    def addto_predicate_list(self,
                             act_dict,
                             act_pred_key,
                             object_id,
                             item_type,
                             do_slug_uri=False,
                             add_hash_id=False):
        """
        creates a list for an predicate (act_pred_key) of the json_ld dictionary object if it doesn't exist
        adds a list item of a dictionary object for item that's an object of the predicate
        """
        # first get the identifiers for objects that
        # may already be listed with this predicate. This prevents duplication
        object_ids = []
        if act_pred_key in act_dict:
            for obj in act_dict[act_pred_key]:
                if 'id' in obj:
                    object_ids.append(obj['id'])
                elif '@id' in obj:
                    object_ids.append(obj['@id'])
        else:
            act_dict[act_pred_key] = []
        new_object_item = None
        ent = self.get_object_item_entity(object_id, item_type)
        if ent is not False:
            new_object_item = LastUpdatedOrderedDict()
            if add_hash_id is not False:
                new_object_item['hash_id'] = add_hash_id
            if do_slug_uri:
                # make the item's ID based on a slug for an item
                new_object_item['id'] = URImanagement.make_oc_uri(object_id, item_type)
            else:
                # normal URI
                new_object_item['id'] = ent.uri
            new_object_item['slug'] = ent.slug
            if isinstance(ent.label, str):
                new_object_item['label'] = ent.label
            else:
                new_object_item['label'] = 'No record of label'
            if isinstance(ent.thumbnail_uri, str):
                new_object_item['oc-gen:thumbnail-uri'] = ent.thumbnail_uri
            if isinstance(ent.content, str) and ent.content != ent.label:
                new_object_item['rdfs:comment'] = ent.content
            if isinstance(ent.class_uri, str) and item_type in self.ITEM_TYPE_CLASS_LIST:
                new_object_item['type'] = ent.class_uri
                if ent.class_uri not in self.class_uri_list:
                    self.class_uri_list.append(ent.class_uri)  # list of unique open context item classes
            if isinstance(self.predicate_uri_as_stable_id, str) and item_type == 'predicates':
                # we need to add a the full uri to make this predicate
                new_object_item[self.predicate_uri_as_stable_id] = URImanagement.make_oc_uri(ent.uuid, item_type)
            if hasattr(ent, 'stable_id_uris'):
                if ent.stable_id_uris is not False \
                   and isinstance(self.stable_id_predicate, str):
                    if len(ent.stable_id_uris) > 0:
                        #  add a stable identifier URI using the appropriate predicate.
                        #  just adds the first such identifier
                        if isinstance(self.stable_id_prefix_limit, str):
                            for stable_id_uri in ent.stable_id_uris:
                                if self.stable_id_prefix_limit in stable_id_uri:
                                    # we have a stable ID of the correct prefix
                                    new_object_item[self.stable_id_predicate] = stable_id_uri
                                    break
                        else:
                            new_object_item[self.stable_id_predicate] = ent.stable_id_uris[0]
        elif act_pred_key == 'oc-gen:hasIcon':
            new_object_item = {'id': object_id}
        # OK now check to see if the new object is already listed with the predicate
        if new_object_item  is not None:
            if new_object_item['id'] not in object_ids:
                # only add it if it does not exist yet
                act_dict[act_pred_key].append(new_object_item)
        return act_dict 
    
    
    def get_object_item_entity(self, object_id, item_type):
        """ makes new object item json ld,
            1st: check to see if this is in the self.manifest_obj_dict,
                 if so, it means we've got an item that doesn't need
                 multiple queries
            2nd: if not in the self.manifest_obj_dict, look up the
                 entity with the ItemGenerationCache() class
        """
        ent = False
        if item_type in self.ITEM_TYPE_MANIFEST_LIST:
            if object_id in self.manifest_obj_dict:
                ent = self.manifest_obj_dict[object_id]
        elif item_type in self.ITEM_TYPE_PROJ_VOCAB_LIST:
            # look in the project vocabulary for an entity
            ent = self.get_vocabulary_entity_from_proj_context(object_id,
                                                               item_type)
        if ent is False:
            # we don't have an entity, so attempt to dereference and
            # get it via the ItemGenerationCache entity lookup
            igen_cache = ItemGenerationCache()
            ent = igen_cache.get_entity(object_id)  # returns False if not found
        return ent
    
    def get_json_ld_predicate_slug_uri(self, object_id, return_entity=False):
        """ gets a slug uri in the form of 'oc-pred:<slug>'. """
        ent = self.get_object_item_entity(object_id,
                                          'predicates')
        if ent is not False:
            make_slug_uri = True
            if hasattr(ent, 'slug_uri'):
                if isinstance(ent.slug_uri, str):
                    slug_uri = ent.slug_uri
                    make_slug_uri = False
            if make_slug_uri:
                if isinstance(ent.uuid, str):
                    # the entity has a uuid, so it's an open context predicate
                    # from a project
                    if isinstance(ent.slug, str):
                        slug_uri = 'oc-pred:' + ent.slug
                    else:
                        slug_uri = 'oc-pred:' + ent.uuid
                elif ':' in object_id:
                    # probably a prefixed URI so just leave it.
                    slug_uri = object_id
                else:
                    # default to the entity URI. This seems to be a linked data entity
                    slug_uri = ent.uri
        elif ':' in object_id:
                # probably a prefixed URI so just leave it.
                slug_uri = object_id
        else:
            # not found. something is wrong!
            slug_uri = None
        # sometimes useful to get the found predicate entity object,
        # not just the slug_uri
        if return_entity:
            output = {
                'ent': ent,
                'slug_uri': slug_uri
            }
        else:
            output = slug_uri
        return output
    
    def get_vocabulary_entity_from_proj_context(self, object_id, item_type):
        """ get a predicate or type from the project_context """
        # id_keys are used to look for identifiers in json_ld items that can be
        # used to reference object_ids
        ent = False
        id_keys = [
            '@id',
            'id',
            'uuid',
            'slug',
            'owl:sameAs'
        ]
        # print('try to look for ' + object_id + ' ' + item_type)
        # print('proj_context: ' + str(self.proj_context_json_ld))
        if isinstance(self.proj_context_json_ld, dict) \
           and item_type in self.ITEM_TYPE_PROJ_VOCAB_LIST:
            if '@graph' in self.proj_context_json_ld:
                vocab = self.proj_context_json_ld['@graph']
            else:
                vocab = []
                for key, item in self.proj_context_json_ld:
                    if key != '@context':
                        vocab.append(item)
            for item in vocab:
                id_match = False
                for id_key in id_keys:
                    id_match = False
                    if id_key in item:
                        if object_id == item[id_key]:
                            # the object id matches an identifer
                            id_match = True
                            break
                if id_match:
                    # print('found this: ' + str(item))
                    ent = Entity()
                    ent.item_json_ld = item
                    ent.slug_uri = None
                    if 'id' in item:
                        ent.uri = item['id']
                    elif '@id' in item:
                        ent.uri = item['@id']
                    elif 'owl:sameAs' in item:
                        ent.uri = item['owl:sameAs']
                    if isinstance(ent.uri, str):
                        # identify the item_type by looking at the URI
                        for act_type in self.ITEM_TYPE_PROJ_VOCAB_LIST:
                            if ('/' + act_type + '/') in ent.uri:
                                ent.item_type = act_type
                    if 'uuid' in item:
                        ent.uuid = item['uuid']
                    if 'slug' in item:
                        ent.slug = item['slug']
                        if ent.item_type == 'predicates':
                            # make a predicate slug URI
                            ent.slug_uri = 'oc-pred:' + ent.slug
                    if 'label' in item:
                        ent.label = item['label']
                    break
        return ent
    
    def get_manifest_objects_from_uuids(self, query_uuids):
        """ gets manifest objects from a list of uuids
            that are in the ITEM_TYPE_MANIFEST_LIST
        """
        if not isinstance(query_uuids, list):
            query_uuids = [query_uuids]
        if len(query_uuids) > 0:
            # go and retrieve all of these manifest objects
            act_man_objs = Manifest.objects.filter(uuid__in=query_uuids,
                                                   item_type__in=self.ITEM_TYPE_MANIFEST_LIST)
            for act_man_obj in act_man_objs:
                uuid = act_man_obj.uuid
                # now add some attributes expected for entites
                act_man_obj.uri = URImanagement.make_oc_uri(uuid, act_man_obj.item_type)
                act_man_obj.slug_uri = None
                act_man_obj.thumbnail_uri = None
                act_man_obj.content = None
                act_man_obj.item_json_ld = None
                self.manifest_obj_dict[uuid] = act_man_obj

