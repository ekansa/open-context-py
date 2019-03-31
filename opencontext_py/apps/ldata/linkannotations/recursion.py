import hashlib
from django.core.cache import caches
from django.db import models
from django.db.models import Q

from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.libs.memorycache import MemoryCache

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
lr.get_jsonldish_entity_parents('oc-gen:cat-bio-subj-ecofact')
lr = LinkRecursion()
lr.get_jsonldish_entity_parents('oc-gen:cat-arch-element')
lr = LinkRecursion()
lr.get_jsonldish_entity_parents('http://eol.org/pages/7680')
lr = LinkRecursion()
lr.get_entity_children('http://eol.org/pages/4077', True)
    """
    def __init__(self):
        self.m_cache = MemoryCache()
        self.parent_entities = None
        self.child_entities = None
        # cache prefix for the json-ldish-parents
        self.jsonldish_p_prefix = 'json-ldish-parents-{}'
        # cache prefix for list of parents
        self.p_prefix = 'lr-parents'
        # cache prefix for children of an item
        self.children_prefix = 'lr-children-{}'
        # cache prefix for full tree of child items
        self.child_tree_prefix = 'lr-child-tree-{}'

    def get_jsonldish_entity_parents(self, identifier, add_original=True):
        """
        Gets parent concepts for a given URI or UUID identified entity
        returns a list of dictionary objects similar to JSON-LD expectations
        This is useful for faceted search

        If add_original is true, add the original UUID for the entity
        that's the childmost item, at the bottom of the hierarchy
        """
        cache_key = self.m_cache.make_cache_key(
            self.jsonldish_p_prefix.format(str(add_original)),
            identifier
        )
        obj = self.m_cache.get_cache_object(cache_key)
        if obj is not None:
            return obj
        # We don't have it cached, so get from the database.
        obj = self._get_jsonldish_entity_parents_db(
            identifier,
            add_original
        )
        if obj:
            self.m_cache.save_cache_object(cache_key, obj)
        return obj

    def _get_jsonldish_entity_parents_db(self, identifier, add_original=True):
        """
        Gets parent concepts for a given URI or UUID identified entity
        returns a list of dictionary objects similar to JSON-LD expectations
        This is useful for faceted search

        If add_original is true, add the original UUID for the entity
        that's the childmost item, at the bottom of the hierarchy
        """
        output = False
        if add_original:
            # add the original identifer to the list of parents, at lowest rank
            raw_parents = (
                [identifier] +
                self.get_entity_parents(identifier, [], 0)
            )
        else:
            raw_parents = self.get_entity_parents(
                identifier,
                [],
                0
            )
        if not len(raw_parents):
            # No parents. Returns false.
            return output
        # Make the output.
        # reverse the order of the list, to make top most concept
        # first
        output = []
        for par_id in raw_parents[::-1]:
            # print('par_id is: ' + par_id)
            ent = self.m_cache.get_entity(par_id)
            if not ent:
                continue
            p_item = LastUpdatedOrderedDict()
            p_item['id'] = ent.uri
            p_item['slug'] = ent.slug
            p_item['label'] = ent.label
            if ent.data_type is not False:
                p_item['type'] = ent.data_type
            else:
                p_item['type'] = '@id'
            p_item['ld_object_ok'] = ent.ld_object_ok
            output.append(p_item)
        return output
    
    def get_entity_parents(self, identifier, parent_list=None, loop_count=0):
        """
        Gets parent concepts for a given URI or UUID identified entity
        """
        if not parent_list:
            parent_list = []
        loop_count += 1
        parent_id = self._get_parent_id(identifier)
        # print('ID: {} has parent: {}'.format(identifier, parent_id))
        if parent_id:
            if parent_id not in parent_list:
                parent_list.append(parent_id)
                # print('Parent list is: ' + str(parent_list))
            if loop_count <= 50:
                parent_list = self.get_entity_parents(parent_id, parent_list, loop_count)
        else:
            # all done, save the parents
            self.parent_entities = parent_list
        return parent_list
    
    def _get_parent_id(self, identifier):
        """Get the parent id for the current identifier, or from the cache."""
        cache_key = self.m_cache.make_cache_key(self.p_prefix,
                                                identifier)
        obj = self.m_cache.get_cache_object(cache_key)
        if obj is not None:
            return obj
        else:
            obj = self._get_parent_id_db(identifier)
            if obj:
                self.m_cache.save_cache_object(cache_key, obj)
            return obj

    def _get_parent_id_db(self, identifier):
        """Get the parent id for the current identifier """
        parent_id = None
        lequiv = LinkEquivalence()
        identifiers = lequiv.get_identifier_list_variants(identifier)
        # print('identifiers: {}'.format(identifiers))
        p_for_superobjs = LinkAnnotation.PREDS_SBJ_IS_SUB_OF_OBJ
        preds_for_superobjs = lequiv.get_identifier_list_variants(p_for_superobjs)
        p_for_subobjs = LinkAnnotation.PREDS_SBJ_IS_SUPER_OF_OBJ
        preds_for_subobjs = lequiv.get_identifier_list_variants(p_for_subobjs)
        try:
            # look for superior items in the objects of the assertion
            # sorting by sort so we can privelage a certain hierarchy path
            superobjs_anno = LinkAnnotation.objects.filter(subject__in=identifiers,
                                                           predicate_uri__in=preds_for_superobjs)\
                                                   .exclude(object_uri__in=identifiers)\
                                                   .order_by('sort', 'object_uri')[:1]
            if len(superobjs_anno) < 1:
                superobjs_anno = False
        except LinkAnnotation.DoesNotExist:
            superobjs_anno = False
        if superobjs_anno:
            parent_id = superobjs_anno[0].object_uri
            # print('Subject {} is child of {}'.format(identifiers, parent_id))
            oc_uuid = URImanagement.get_uuid_from_oc_uri(parent_id)
            if oc_uuid:
                parent_id = oc_uuid
        try:
            """
            Now look for superior entities in the subject, not the object
            sorting by sort so we can privelage a certain hierarchy path
            """
            supersubj_anno = LinkAnnotation.objects.filter(object_uri__in=identifiers,
                                                           predicate_uri__in=preds_for_subobjs)\
                                                   .exclude(subject__in=identifiers)\
                                                   .order_by('sort', 'subject')[:1]
            if len(supersubj_anno) < 1:
                supersubj_anno = False
        except LinkAnnotation.DoesNotExist:
            supersubj_anno = False
        if supersubj_anno:
            parent_id = supersubj_anno[0].subject
            # print('Subject {} is parent of {}'.format(parent_id, identifiers))
            oc_uuid = URImanagement.get_uuid_from_oc_uri(parent_id)
            if oc_uuid:
                parent_id = oc_uuid
        return parent_id

    def get_entity_children(self, identifier, recursive=True):
        cache_key = self.m_cache.make_cache_key(self.children_prefix.format(str(recursive)),
                                                identifier)
        tree_cache_key = self.m_cache.make_cache_key(self.child_tree_prefix.format(str(recursive)),
                                                     identifier)
        obj = self.m_cache.get_cache_object(cache_key)
        tree_obj = self.m_cache.get_cache_object(tree_cache_key)
        if obj is not None and tree_obj is not None:
            # print('Hit child cache on {}'.format(identifier))
            self.child_entities = tree_obj  # the fill tree of child entities
            return obj
        else:
            obj = self._get_entity_children_db(identifier, recursive)
            if obj:
                # print('Hit child DB on {}'.format(identifier))
                self.m_cache.save_cache_object(cache_key, obj)
                self.m_cache.save_cache_object(tree_cache_key, self.child_entities)
            return obj
    
    def _get_entity_children_db(self, identifier, recursive=True):
        """
        Gets child concepts for a given URI or UUID identified entity
        """
        if not self.child_entities:
            self.child_entities = LastUpdatedOrderedDict()
        if identifier in self.child_entities and recursive:
            output = self.child_entities[identifier]
        else:
            act_children = []
            p_for_superobjs = LinkAnnotation.PREDS_SBJ_IS_SUB_OF_OBJ
            p_for_subobjs = LinkAnnotation.PREDS_SBJ_IS_SUPER_OF_OBJ
            lequiv = LinkEquivalence()
            identifiers = lequiv.get_identifier_list_variants(identifier)
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
            # print('found: ' + predicate_uuid)
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
        """ Gets an entity either from the cache or from
            database lookups. This is a wrapper for the
            MemoryCache().get_entity function.
        """
        return self.m_cache.get_entity(identifier)
    