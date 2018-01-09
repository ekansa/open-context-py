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


# ItemJsonLD is used to make JSON-LD output for OC-Items
class PartsJsonLD():
    
    ITEM_TYPE_CLASS_LIST = [
        'subjects',
        'media',
        'persons'
    ]

    def __init__(self):
        self.item_gen_cache = ItemGenerationCache()
        rp = RootPath()
        self.base_url = rp.get_baseurl()
        self.class_uri_list = []  # uris of item classes used in this item 
        
    def addto_predicate_list(self,
                             act_dict,
                             act_pred_key,
                             object_id,
                             item_type,
                             do_slug_uri=False,
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
        new_object_item = LastUpdatedOrderedDict()
        igen_cache = ItemGenerationCache()
        ent = igen_cache.get_entity(object_id)
        if ent is not False:
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
        elif act_pred_key == 'oc-gen:hasIcon':
            new_object_item = {'id': object_id}
        if new_object_item['id'] not in object_ids:
            # only add it if it does not exist yet
            act_dict[act_pred_key].append(new_object_item)
        return act_dict 
        