import hashlib
from django.db import models
from django.db.models import Q
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.apps.entities.uri.models import URImanagement
from opencontext_py.apps.entities.entity.models import Entity
from opencontext_py.apps.ldata.linkannotations.models import LinkAnnotation
from opencontext_py.apps.ldata.linkannotations.equivalence import LinkEquivalence
from opencontext_py.apps.ocitems.predicates.models import Predicate
from opencontext_py.apps.ocitems.octypes.models import OCtype


class LinkRecursion():
    """
    Does recursive look ups on link annotations, especially to find hierarchies

from opencontext_py.apps.ldata.linkannotations.recursion import LinkRecursion
lr = LinkRecursion()
lr.get_jsonldish_entity_parents('oc-gen:cat-site', False)

    """
    def __init__(self):
        self.parent_entities = []
        self.child_entities = LastUpdatedOrderedDict()
        self.loop_count = 0
        self.mem_cache_parents = {}
        self.mem_cache_entities = {}
        self.mem_cache_children = {}

    def get_jsonldish_entity_parents(self, identifier, add_original=True):
        """
        Gets parent concepts for a given URI or UUID identified entity
        returns a list of dictionary objects similar to JSON-LD expectations
        This is useful for faceted search

        If add_original is true, add the original UUID for the entity
        that's the childmost item, at the bottom of the hierarchy
        """
        output = False
        if identifier in self.mem_cache_parents and add_original:
            output = self.mem_cache_parents[identifier]
        else:
            raw_parents = self.get_entity_parents(identifier)
            if add_original:
                # add the original identifer to the list of parents, at lowest rank
                raw_parents.insert(0, identifier)
            if len(raw_parents) > 0:
                output = []
                # reverse the order of the list, to make top most concept
                # first
                parents = raw_parents[::-1]
                for par_id in parents:
                    if par_id in self.mem_cache_parents:
                        output = self.mem_cache_parents[par_id]
                    else:
                        ent = self.get_entity(par_id)
                        if ent is not False:
                            p_item = LastUpdatedOrderedDict()
                            p_item['id'] = ent.uri
                            p_item['slug'] = ent.slug
                            p_item['label'] = ent.label
                            if(ent.data_type is not False):
                                p_item['type'] = ent.data_type
                            else:
                                p_item['type'] = '@id'
                            p_item['ld_object_ok'] = ent.ld_object_ok
                            output.append(p_item)
                            self.mem_cache_parents[par_id] = output
        return output

    def get_entity_parents(self, identifier):
        """
        Gets parent concepts for a given URI or UUID identified entity
        """
        self.loop_count += 1
        lequiv = LinkEquivalence()
        identifiers = lequiv.get_identifier_list_variants(identifier)
        p_for_superobjs = LinkAnnotation.PREDS_SBJ_IS_SUB_OF_OBJ
        preds_for_superobjs = lequiv.get_identifier_list_variants(p_for_superobjs)
        p_for_subobjs = LinkAnnotation.PREDS_SBJ_IS_SUPER_OF_OBJ
        preds_for_subobjs = lequiv.get_identifier_list_variants(p_for_subobjs)
        try:
            # look for superior items in the objects of the assertion
            superobjs_anno = LinkAnnotation.objects.filter(subject__in=identifiers,
                                                           predicate_uri__in=preds_for_superobjs)\
                                                   .exclude(object_uri__in=identifiers)[:1]
            if(len(superobjs_anno) < 1):
                superobjs_anno = False
        except LinkAnnotation.DoesNotExist:
            superobjs_anno = False
        if(superobjs_anno is not False):
            parent_id = superobjs_anno[0].object_uri
            if(parent_id.count('/') > 1):
                oc_uuid = URImanagement.get_uuid_from_oc_uri(parent_id)
                if(oc_uuid is not False):
                    parent_id = oc_uuid
                if(parent_id not in self.parent_entities):
                    self.parent_entities.append(parent_id)
            if self.loop_count <= 50:
                self.parent_entities = self.get_entity_parents(parent_id)
        try:
            """
            Now look for superior entities in the subject, not the object
            """
            supersubj_anno = LinkAnnotation.objects.filter(object_uri__in=identifiers,
                                                           predicate_uri__in=preds_for_subobjs)\
                                                   .exclude(subject__in=identifiers)[:1]
            if(len(supersubj_anno) < 1):
                supersubj_anno = False
        except LinkAnnotation.DoesNotExist:
            supersubj_anno = False
        if supersubj_anno is not False:
            parent_id = supersubj_anno[0].subject
            if(parent_id.count('/') > 1):
                oc_uuid = URImanagement.get_uuid_from_oc_uri(parent_id)
                if(oc_uuid is not False):
                    parent_id = oc_uuid
                if(parent_id not in self.parent_entities):
                    self.parent_entities.append(parent_id)
            if self.loop_count <= 50:
                self.parent_entities = self.get_entity_parents(parent_id)
        return self.parent_entities

    def get_entity_children(self, identifier, recursive=True):
        """
        Gets child concepts for a given URI or UUID identified entity
        """
        if identifier in self.child_entities and recursive:
            output = self.child_entities[identifier]
        else:
            act_children = []
            p_for_superobjs = LinkAnnotation.PREDS_SBJ_IS_SUB_OF_OBJ
            p_for_subobjs = LinkAnnotation.PREDS_SBJ_IS_SUPER_OF_OBJ
            lequiv = LinkEquivalence()
            lequiv.mem_cache_entities = self.mem_cache_entities
            identifiers = lequiv.get_identifier_list_variants(identifier)
            # print(str(identifiers))
            self.mem_cache_entities = lequiv.mem_cache_entities
            try:
                # look for child items in the objects of the assertion
                subobjs_anno = LinkAnnotation.objects.filter(subject__in=identifiers,
                                                             predicate_uri__in=p_for_subobjs)
                if(len(subobjs_anno) < 1):
                    subobjs_anno = False
            except LinkAnnotation.DoesNotExist:
                subobjs_anno = False
            if subobjs_anno is not False:
                for sub_obj in subobjs_anno:
                    child_id = sub_obj.object_uri
                    act_children.append(child_id)
            try:
                """
                Now look for subordinate entities in the subject, not the object
                """
                subsubj_anno = LinkAnnotation.objects.filter(object_uri__in=identifiers,
                                                             predicate_uri__in=p_for_superobjs)
                if len(subsubj_anno) < 1:
                    subsubj_anno = False
            except LinkAnnotation.DoesNotExist:
                subsubj_anno = False
            if subsubj_anno is not False:
                for sub_sub in subsubj_anno:
                    child_id = sub_sub.subject
                    act_children.append(child_id)
            if len(act_children) > 0:
                identifier_children = []
                for child_id in act_children:
                    if child_id.count('/') > 1:
                        oc_uuid = URImanagement.get_uuid_from_oc_uri(child_id)
                        if oc_uuid is not False:
                            child_id = oc_uuid
                    identifier_children.append(child_id)
                    # recursively get the children of the child
                    if recursive:
                        self.get_entity_children(child_id, recursive)
                # same the list of children of the current identified item
                if identifier not in self.child_entities:
                    self.child_entities[identifier] = identifier_children
            else:
                # save a False for the current identified item. it has no children
                if identifier not in self.child_entities:
                    self.child_entities[identifier] = []
            output = self.child_entities[identifier]
        return output

    def get_pred_top_rank_types(self, predicate_uuid):
        """ gets the top ranked (not a subordinate) of any other
            type for a predicate
        """
        types = False
        try:
            pred_obj = Predicate.objects.get(uuid=predicate_uuid)
        except Predicate.DoesNotExist:
            pred_obj = False
        if pred_obj is not False:
            print('found: ' + predicate_uuid)
            if pred_obj.data_type == 'id':
                types = []
                id_list = []
                pred_types = OCtype.objects\
                                   .filter(predicate_uuid=predicate_uuid)
                for p_type in pred_types:
                    type_pars = self.get_jsonldish_entity_parents(p_type.uuid)
                    self.parent_entities = []
                    self.loop_count = 0
                    if type_pars[0]['id'] not in id_list:
                        # so the top parent is only listed once
                        id_list.append(type_pars[0]['id'])
                        types.append(type_pars[0])
        return types

    def get_entity(self, identifier):
        """ gets entities, but checkes first if they are in memory """
        output = False
        if identifier in self.mem_cache_entities:
            output = self.mem_cache_entities[identifier]
        else:
            ent = Entity()
            found = ent.dereference(identifier)
            if found:
                output = ent
                self.mem_cache_entities[identifier] = ent
        return output
