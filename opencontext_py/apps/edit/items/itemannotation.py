import time
import uuid as GenUUID
from django.db import models
from django.db.models import Q
from django.core.cache import caches
from opencontext_py.apps.entities.entity.models import Entity
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.ocitems.projects.permissions import ProjectPermissions
from opencontext_py.apps.ldata.linkannotations.models import LinkAnnotation
from opencontext_py.apps.ldata.linkannotations.equivalence import LinkEquivalence
from opencontext_py.apps.ldata.linkentities.models import LinkEntity
from opencontext_py.apps.ocitems.identifiers.models import StableIdentifer
from opencontext_py.apps.edit.versioning.deletion import DeletionRevision


# Help organize the code, with a class to make editing items easier
class ItemAnnotation():
    """ This class contains methods
        for editing item annotations
    """

    def __init__(self,
                 uuid,
                 request=False):
        self.hash_id = False
        self.creator_uuid = False
        self.super_user = False
        self.uuid = uuid
        self.request = request
        self.errors = {'uuid': False,
                       'params': False}
        self.response = {}
        self.orcid_ok = None
        try:
            self.manifest = Manifest.objects.get(uuid=uuid)
        except Manifest.DoesNotExist:
            self.manifest = False
            self.errors['uuid'] = 'Item ' + uuid + ' not in manifest'
        if request is not False and self.manifest is not False:
            # check to make sure edit permissions OK
            pp = ProjectPermissions(self.manifest.project_uuid)
            self.edit_permitted = pp.edit_allowed(request)
        else:
            # default to no editting permissions
            self.edit_permitted = False

    def add_item_annotation(self, post_data):
        """ Adds a linked data annotation to an item
        """
        note = ''
        ok_predicates = ['dc-terms:creator',
                         'dc-terms:contributor',
                         'dc-terms:subject',
                         'dc-terms:coverage',
                         'dc-terms:temporal',
                         'dc-terms:references',
                         'dc-terms:isReferencedBy',
                         'dc-terms:license',
                         'skos:closeMatch',
                         'skos:exactMatch',
                         'owl:sameAs',
                         'skos:broader',
                         'skos:related',
                         'skos:example',
                         'rdfs:isDefinedBy',
                         'http://www.w3.org/2000/01/rdf-schema#range']
        ok = True
        predicate_uri = self.request_param_val(post_data,
                                               'predicate_uri')
        object_uri = self.request_param_val(post_data,
                                            'object_uri')
        if predicate_uri is not False \
           and object_uri is not False:
            p_entity = Entity()
            found_p = p_entity.dereference(predicate_uri)
            if found_p is False \
               and predicate_uri in ok_predicates:
                found_p = True
            o_entity = Entity()
            found_o = o_entity.dereference(object_uri)
            if found_p and found_o:
                lequiv = LinkEquivalence()
                pred_list = lequiv.get_identifier_list_variants(predicate_uri)
                obj_list = lequiv.get_identifier_list_variants(object_uri)
                la_exist = LinkAnnotation.objects\
                                         .filter(subject=self.uuid,
                                                 predicate_uri__in=pred_list,
                                                 object_uri__in=obj_list)[:1]
                if len(la_exist) < 1:
                    # we don't have an annotation like this yet
                    object_uri = o_entity.uri
                    new_la = LinkAnnotation()
                    new_la.subject = self.manifest.uuid
                    new_la.subject_type = self.manifest.item_type
                    new_la.project_uuid = self.manifest.project_uuid
                    new_la.source_id = self.request_param_val(post_data,
                                                              'source_id',
                                                              'manual-web-form',
                                                              False)
                    new_la.sort = self.request_param_val(post_data,
                                                         'sort',
                                                         0,
                                                         False)
                    new_la.predicate_uri = predicate_uri
                    new_la.object_uri = object_uri
                    new_la.creator_uuid = self.creator_uuid
                    new_la.save()
                    # now clear the cache a change was made
                    self.clear_caches()
                else:
                    ok = False
                    note = 'This annotation already exists.'
            else:
                ok = False
                note = 'Missing a predicate or object entity'
        else:
            note = self.errors['params']
            ok = False
        self.response = {'action': 'add-item-annotation',
                         'ok': ok,
                         'change': {'note': note}}
        return self.response

    def delete_annotation(self, post_data):
        """ Adds a linked data annotation to an item
        """
        note = ''
        if 'hash_id' in post_data:
            hash_id = post_data['hash_id']
            la_exist = LinkAnnotation.objects\
                                     .filter(hash_id=hash_id)\
                                     .delete()
            self.hash_id = hash_id
            ok = True
            note = 'annotation deleteted'
            # now clear the cache a change was made
            self.clear_caches()
        else:
            ok = False
            note = 'Missing a annotation hash-id.'
            self.errors['params'] = note
        self.response = {'action': 'delete-annotation',
                         'ok': ok,
                         'change': {'note': note}}
        return self.response

    def sort_change_annotation(self, post_data):
        """ Adds a linked data annotation to an item
        """
        note = ''
        ok = True
        if 'hash_id' in post_data \
           and 'sort_change' in post_data:
            hash_id = post_data['hash_id']
            sort_change = 0
            try:
                sort_change = int(float(post_data['sort_change']))
            except:
                sort_change = 0
                ok = False
                note += 'Error, sort_change needs to be an integer value. '
            if sort_change != 0:
                try:
                    la_act = LinkAnnotation.objects\
                                           .get(hash_id=hash_id)
                except LinkAnnotation.DoesNotExist:
                    la_act = False
                    ok = False
                    note += 'Cannot find annotation to re-sort. '
                if la_act is not False:
                    # now get the related annotations to re-sort
                    le = LinkEquivalence()
                    subject_list = le.get_identifier_list_variants(la_act.subject)
                    if self.manifest.uuid not in subject_list:
                        subject_list.append(self.manifest.uuid)
                    pred_list = le.get_identifier_list_variants(la_act.predicate_uri)
                    rel_annos = LinkAnnotation.objects\
                                              .filter(subject__in=subject_list,
                                                      predicate_uri__in=pred_list)
                    pseudo_sort = 0 # used to make a sort value if none was given
                    i = -1
                    current_hash_index = False
                    for rel_anno in rel_annos:
                        pseudo_sort += 1
                        i += 1
                        if rel_anno.sort is None \
                           or rel_anno.sort == 0:
                            rel_anno.sort = pseudo_sort
                            rel_anno.save()
                        if rel_anno.hash_id == hash_id:
                            current_hash_index = i
                    if current_hash_index is not False:
                        item_b_index = current_hash_index + sort_change
                        if item_b_index >=0 and item_b_index < len(rel_annos):
                            anno_a = rel_annos[current_hash_index]
                            anno_b = rel_annos[item_b_index]
                            new_sort_anno_b = anno_a.sort
                            new_sort_anno_a = anno_b.sort
                            if new_sort_anno_a == new_sort_anno_b:
                                # so we don't have exactly the same values
                                new_sort_anno_a += sort_change
                            anno_a.sort = new_sort_anno_a
                            anno_a.save()
                            anno_b.sort = new_sort_anno_b
                            anno_b.save()
                            ok = True
                            note += 'Annotation successfully resorted. '
                            # now clear the cache a change was made
                            self.clear_caches()
                            # now fix it so we will always have unique sorts.
                            used_sorts = []
                            rel_annos = LinkAnnotation.objects\
                                                      .filter(subject__in=subject_list,
                                                              predicate_uri__in=pred_list)
                            for act_anno in rel_annos:
                                if act_anno.sort not in used_sorts:
                                    used_sorts.append(act_anno.sort)
                                else:
                                    act_anno.sort += 1
                                    used_sorts.append(act_anno.sort)
                                    act_anno.save()
                        else:
                            ok = False
                            note += 'Cannot change sorting, as at limit of the list of objects.'
                            note += ' Current_hash_index: ' + str(current_hash_index)
                            note += ' Exchange with index: ' + str(item_b_index)
                    else:
                        ok = False
                        note += 'A truly bizzare something happened. '
        else:
            ok = False
            note = 'Missing a annotation hash-id or sorting parameter "sort_change". '
            self.errors['params'] = note
        self.response = {'action': 'edit-annotation',
                         'ok': ok,
                         'change': {'note': note}}
        return self.response

    def check_orcid_ok(self, post_data):
        """ checks to see if it's OK to add ORCID
            stable identifiers
        """
        if self.orcid_ok is None:
            # we haven't checked yet
            orcid_ok = False
            if self.manifest.item_type == 'persons':
                id_type = self.request_param_val(post_data,
                                                 'stable_type')
                stable_id = self.request_param_val(post_data,
                                                   'stable_id')
                if stable_id is not False:
                    # check the actual identifier to see if it's an ORCID
                    id_type_prefixes = StableIdentifer.ID_TYPE_PREFIXES
                    if id_type_prefixes['orcid'] in stable_id:
                        id_type = 'orcid'
                if id_type == 'orcid':
                    orcid_ok = True
            self.orcid_ok = orcid_ok
        return self.orcid_ok

    def add_item_stable_id(self, post_data):
        """ adds a stable identifier to an item """
        ok = False
        note = ''
        orcid_ok = self.check_orcid_ok(post_data)
        stable_id = self.request_param_val(post_data,
                                           'stable_id')
        stable_type = self.request_param_val(post_data,
                                             'stable_type')
        stable_id = stable_id.strip()
        # now update the stable_type based on what's in the stable_id
        stable_type = StableIdentifer().type_uri_check(stable_type,
                                                       stable_id)
        if stable_type == 'orcid' and orcid_ok is not True:
            # problem adding an ORCID to this type of item
            stable_type = False
            note = 'Cannot add an ORCID to this item.'
        if stable_id is not False \
           and stable_type is not False:
            ok = True
            try:
                new_stable = StableIdentifer()
                new_stable.stable_id = stable_id
                new_stable.stable_type = stable_type
                new_stable.uuid = self.manifest.uuid
                new_stable.project_uuid = self.manifest.project_uuid
                new_stable.item_type = self.manifest.item_type
                new_stable.save()
            except:
                ok = False
                note = 'Identifier already in use'
        else:
            note = 'Problems with the ID request'
        if ok:
            # now clear the cache a change was made
            self.clear_caches()
        self.response = {'action': 'add-item-stable-id',
                         'ok': ok,
                         'change': {'note': note}}
        return self.response

    def delete_item_stable_id(self, post_data):
        """ deletes a stable identifier from an item """
        orcid_ok = self.check_orcid_ok(post_data)
        stable_id = self.request_param_val(post_data,
                                           'stable_id')
        if stable_id is not False:
            ok = True
            stable_id_list = [stable_id]
            for id_type, prefix in StableIdentifer.ID_TYPE_PREFIXES.items():
                id_variant = stable_id.replace(prefix, '')
                if id_variant not in stable_id_list:
                    # just in case the stable_id is a given as a URI
                    # delete multiple varients of it
                    stable_id_list.append(id_variant)
            drev = DeletionRevision()
            drev.project_uuid = self.manifest.project_uuid
            drev.uuid = self.manifest.uuid
            drev.item_type = self.manifest.item_type
            drev.user_id = self.creator_uuid
            rev_label = 'Updated ' + self.manifest.label
            rev_label += ', removed stable ID: ' + stable_id
            del_ids = StableIdentifer.objects\
                                     .filter(uuid=self.manifest.uuid,
                                             stable_id__in=stable_id_list)
            for del_id in del_ids:
                drev.identifier_keys.append(del_id.hash_id)
                del_id.delete()
            drev.save_delete_revision(rev_label, '')
            note = 'Deleteted: ' + stable_id + ' from ' + self.manifest.uuid
        else:
            note = 'Need to indicate what stable_id to delete'
        if ok:
            # now clear the cache a change was made
            self.clear_caches()
        self.response = {'action': 'delete-item-stable-id',
                         'ok': ok,
                         'change': {'note': note}}
        return self.response

    def request_param_val(self,
                          data,
                          param,
                          default=False,
                          note_error=True):
        """ Gets the value for paramater in a dict (data, if parameter
            does not exist, it returns a default value
        """
        if isinstance(data, dict):
            if param in data:
                output = data[param]
            else:
                output = default
                if note_error:
                    if self.error['params'] is False:    
                        self.error['params'] = 'Missing paramater: ' + param
                    else:
                        self.error['params'] += '; Missing paramater: ' + param
        else:
            output = default
        return output

    def clear_caches(self):
        """ clears all the caches """
        cache = caches['redis']
        cache.clear()
        cache = caches['default']
        cache.clear()
