import time
import datetime
from dateutil.parser import parse
import uuid as GenUUID
from lxml import etree
import lxml.html
from django.db import models
from django.db.models import Q
from django.db.models import Count
from django.conf import settings
from django.core.cache import caches
from opencontext_py.libs.languages import Languages
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.apps.entities.uri.models import URImanagement
from opencontext_py.apps.entities.entity.models import Entity
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.ocitems.assertions.models import Assertion
from opencontext_py.apps.ocitems.predicates.models import Predicate
from opencontext_py.apps.ocitems.octypes.models import OCtype
from opencontext_py.apps.ocitems.strings.models import OCstring
from opencontext_py.apps.ocitems.strings.manage import StringManagement
from opencontext_py.apps.ocitems.subjects.generation import SubjectGeneration
from opencontext_py.apps.ldata.linkentities.models import LinkEntityGeneration
from opencontext_py.apps.edit.items.itembasic import ItemBasicEdit
from opencontext_py.apps.edit.versioning.deletion import DeletionRevision
from opencontext_py.apps.ocitems.editorials.models import Editorial
from opencontext_py.apps.ocitems.editorials.manage import EditorialAction
from opencontext_py.apps.edit.items.deletemerge import DeleteMerge
from opencontext_py.apps.ldata.linkannotations.manage import LinkAnnoManagement
from opencontext_py.apps.ldata.linkannotations.recursion import LinkRecursion


class ItemDelete():
    """ This class contains methods
        for deleting items and previewing the concequences of deletion

from opencontext_py.apps.edit.items.itemdelete import ItemDelete
item_del = ItemDelete()


    """

    def __init__(self, manifest=None):
        self.manifest = manifest
        self.pred_object_uuids = None
        if self.manifest is not None:
            self.uuid = manifest.uuid
            self.project_uuid = manifest.project_uuid
            self.item_type = manifest.item_type
            if self.item_type == 'predicates':
                pred = None
                try:
                    pred = Predicate.objects.get(uuid=self.uuid)
                except:
                    pred = None
                if pred is not None:
                    if pred.data_type == 'id':
                        self.pred_object_uuids = []
                        rel_types = OCtype.objects\
                                          .filter(project_uuid=self.project_uuid,
                                                  predicate_uuid=self.uuid)
                        for rel_type in rel_types:
                            self.pred_object_uuids.append(rel_type.uuid)
        else:
            self.uuid = None
            self.project_uuid = None
            self.item_type = None
        self.user_id = 1
        self.user_specified_merge = False
        self.merge_into_uuid = None
        self.merge_manifest = None
        self.merge_retain_attributes = True
        self.editorial_uuid = None
        self.editorial_label = None
        self.editorial_note = None
        self.editorial_class_uri = None
        self.errors = []
        self.ok = True
        self.response = False
        self.uniquely_linking_types = [
            'subjects',
            'media',
            'documents'
        ]

    def delete_and_document(self, post_data):
        """ deletes an item, including assertions about it
            and document the deletion event so it can be
            rolled back (in theory)
        """
        output = {}
        merge_into_label = None
        ok = self.set_merge_into_uuid(post_data)
        if ok:
            self.set_editorial_metadata(post_data)
            self.editorial_uuid = str(GenUUID.uuid4())
            ed_act = EditorialAction()
            ed_act.editorial_uuid = self.editorial_uuid
            ed_act.editorial_project_uuid = self.project_uuid
            ed_act.editorial_user_id = self.user_id
            ed_act.editorial_class_uri = self.editorial_class_uri
            ed_act.editorial_label = self.editorial_label
            ed_act.editorial_note = self.editorial_note
            # save a copy of data, as a JSON serialization string
            # of the data to editorial event, the item itself,
            # relationships to the item, and attributes of the item
            if isinstance(self.pred_object_uuids, list):
                uuid_list = [self.uuid] + self.pred_object_uuids
                saved_query_sets = ed_act.save_editorial_and_pre_redaction_data(self.uuid)
            else:
                saved_query_sets = ed_act.save_editorial_and_pre_redaction_data(self.uuid)
            if isinstance(saved_query_sets, list):
                # success in saving the item's data, now alter hierarchies for the item
                # and deleted the data related ot the item. Deleted records can be restored later
                # from the JSON-serialization stored with this editorial action
                if self.merge_retain_attributes and \
                   isinstance(self.merge_into_uuid, str):
                    dm = DeleteMerge()
                    dm.source_id = self.editorial_uuid
                    dm.merge_by_uuid(self.uuid, self.merge_into_uuid)
                    # delete self containment
                    dm = DeleteMerge()
                    dm.delete_self_containment(self.uuid)
                else:
                    # not retaining an item's descrptive attributes
                    self.alter_hierarchies()
                # now delete the data related to the item
                ed_act.delete_query_set_model_objects(saved_query_sets)
            else:
                error_msg = 'Recovery data not saved, so item not deleted.'
                self.errors.append(error_msg)
                ok = False
        if isinstance(self.merge_into_uuid, str):
            merge_into_label = self.merge_manifest.label
            merge_into_type = self.merge_manifest.item_type
        else:
            merge_into_type = None
            merge_into_label = None
        # add a note about the outcome
        if len(self.errors) > 0:
            note = ' '.join(self.errors)
        else:
            note = 'Completed ' + self.editorial_label
        if ok:
            # deletion OK, so clear caches.
            self.clear_caches()
        output = {
            'action': 'delete-item',
            'ok': ok,
            'project_uuid': self.manifest.project_uuid,
            'user_specified_merge': self.user_specified_merge,
            'merge_into_uuid': self.merge_into_uuid,
            'merge_into_label': merge_into_label,
            'merge_into_type': merge_into_type,
            'editorial_uuid': self.editorial_uuid,
            'editorial_label': self.editorial_label,
            'change': {'note': note}
        }
        return output

    def set_merge_into_uuid(self, post_data):
        """ sets the merge_into_uuid if it is specified
            in the post_data
        """
        ok = True
        if 'merge_into_uuid' in post_data:
            # the merge_into_uuid is how the user specifies
            merge_into_uuid = post_data['merge_into_uuid'].strip()
            if len(merge_into_uuid) > 0:
                ok = self.check_set_merge_into_manifest(merge_into_uuid)
                if merge_into_uuid == self.uuid:
                    ok = False
                    error_msg = 'Cannot merge an item into itself.'
                    self.errors.append(error_msg)
                    self.merge_manifest = None
                if ok:
                    if self.merge_manifest.item_type == self.manifest.item_type:
                        #----------------------
                        # The case where the merge_into_uuid is VALID
                        # 1. not the same as self.uuid
                        # 2. has the same item_type as self.manifest
                        #----------------------
                        self.merge_into_uuid = merge_into_uuid
                        self.user_specified_merge = True
                    else:
                        error_msg = 'Cannot merge items of different types. '
                        error_msg += 'The item to be merged into needs to have a type: '
                        error_msg += self.manifest.item_type
                        self.errors.append(error_msg)
                        self.merge_manifest = None
                else:
                    error_msg = 'The item to be merged into (' + merge_into_uuid
                    error_msg += ') cannot be found.'
                    self.errors.append(error_msg)
            if 'merge_retain_attributes' in post_data:
                if isinstance(self.merge_into_uuid, str):
                    if post_data['merge_retain_attributes'] == 'false':     
                        # OK. When merging items, retain the descriptive
                        # attributes of the item being deleted and associate
                        # those attributes with the merge-into-uuid item
                        self.merge_retain_attributes = False
                    else:
                        # default for the conservative position of retaining
                        # descriptive attributes
                        self.merge_retain_attributes = True
        return ok

    def set_editorial_metadata(self, post_data):
        """ sets editorial metadata with data POSTed by a user,
            if the data is blank or missing, sets default metadata
        """
        self.editorial_class_uri = 'edit-deletion'
        if 'edit_class_uri' in post_data:
            if post_data['ed_class_uri'] in Editorial.EDITORIAL_TYPES:
                # editorial_class_uri recognized, so allow it
                self.editorial_class_uri = post_data['ed_class_uri']
        self.editorial_label = 'Delete: ' + self.manifest.label + ' '
        self.editorial_label += '(' + self.manifest.item_type + '/' + self.uuid + ')'
        if 'edit_label' in post_data:
            if len(post_data['edit_label'].strip()) > 1:
                self.editorial_label = post_data['edit_label'].strip()
        self.editorial_note = ''
        if 'edit_note' in post_data:
            if len(post_data['edit_note'].strip()) > 1:
                self.editorial_note = post_data['edit_note'].strip()

    def alter_hierarchies(self):
        """ alter hierarchic relations
            if the item to be deleted has
            children items
            either in spatial containment
            or in SKOS / OWL relations
        """
        if self.manifest.item_type == 'subjects':
            self.alter_spatial_hierarchy()
        self.alter_annotation_hiearchy()
    
    def alter_spatial_hierarchy(self):
        """ alters the spatial hieratchy
            if the item to be deleted has spatial
            children items
        """
        num_changed = 0
        sp_child_count = self.count_spatial_children()
        if sp_child_count > 0:
            # item has spatial containment children
            # get the current item's parent. By default, the item's children
            # will then get associated with the current item's parent,
            # unless the user specified a valid "merge_into_uuid"
            if self.merge_into_uuid is None:
                # OK the user did not specify a merge_into_uuid, so
                # add default to the parent of the item to be deleted as the new
                # parent of the item-to-be-deleted's children
                self.get_parent_merge_into_manifest_obj()
            if isinstance(self.merge_into_uuid, str):
                dm = DeleteMerge()
                dm.source_id = self.editorial_uuid  # so editorial uuid associated with change
                num_changed = dm.alter_assertions_by_role(
                                'subjects',
                                self.uuid,
                                self.merge_into_uuid,
                                Assertion.PREDICATES_CONTAINS)
                # now change the path information for the Subjects
                sg = SubjectGeneration()
                sg.generate_save_context_path_from_uuid(self.merge_into_uuid,
                                                        True)
                # now check to see it the item to be deleted links to any
                # subjects, media, or document items that would be orphaned
                count_orphans = self.count_and_alter_unqiue_rel_to_subject()
                if count_orphans > 0:
                    # we will orphan subjects, media, or documents with deletion
                    # so link the orphaned items to the new_parent_uuid
                    num_changed += self.count_and_alter_unqiue_rel_to_subject(self.merge_into_uuid)
                # delete self containment
                dm = DeleteMerge()
                dm.delete_self_containment(self.uuid)
        return num_changed
    
    def get_parent_merge_into_manifest_obj(self):
        """ gets the parent item as the
            merge_into_manigest object
        """
        ok = False
        if self.merge_into_uuid is None:
            # OK the user did not specify a merge_into_uuid, so
            # add default to the parent of the item to be deleted as the new
            # parent of the item-to-be-deleted's children
            p_ass = Assertion.objects\
                             .filter(object_uuid=self.uuid,
                                     predicate_uuid=Assertion.PREDICATES_CONTAINS)[:1]
            if len(p_ass) > 0:
                ok = self.check_set_merge_into_manifest(p_ass[0].uuid)
                if ok:
                    self.merge_into_uuid = p_ass[0].uuid
        return ok
    
    def check_set_merge_into_manifest(self, merge_into_uuid):
        """ checks to see if the merge into manifest uuid
            is OK. If it is OK, it sets the self.merge_manifest object
        """
        ok = False
        try:
            merge_manifest = Manifest.objects.get(uuid=merge_into_uuid)
        except Manifest.DoesNotExist:
            merge_manifest = False
        if merge_manifest is not False:
            self.merge_manifest = merge_manifest
            ok = True
        return ok
        
    def alter_annotation_hiearchy(self):
        """ alters hierarchic annotations
            expressed in SKOS or OWL
            relations
        """
        lr = LinkRecursion()
        parents = lr.get_jsonldish_entity_parents(self.uuid, False)
        if isinstance(parents, list):
            if len(parents) > 0:
                # the item has SKOS / OWL parents
                parent_id = parents[-1]['id']
                lam = LinkAnnoManagement()
                lam.source_id = self.editorial_uuid  # so editorial uuid associated with change
                lam.replace_hierarchy(self.uuid, parent_id)
    
    def check_delete_item(self):
        """ checks on the impact of deleting an item """
        output = {
            'spatial_children': None,
            'uniqely_linked_items': None,
            'predicate_uses': None,
            'type_uses': None,
            'label': self.manifest.label,
            'uuid': self.manifest.uuid,
            'item_type': self.manifest.item_type,
            'default_merge_uuid': None,
            'default_merge_label': None
        }
        if self.manifest.item_type in self.uniquely_linking_types:
            output['uniqely_linked_items'] = self.count_and_alter_unqiue_rel_to_subject()
            if self.manifest.item_type == 'subjects':
                output['spatial_children'] = self.count_spatial_children()
                if output['spatial_children'] > 0:
                    ok = self.get_parent_merge_into_manifest_obj()
                    if ok:
                        output['default_merge_uuid'] = self.merge_into_uuid
                        output['default_merge_label'] = self.merge_manifest.label
        elif self.manifest.item_type == 'predicates':
            output['predicate_uses'] = self.count_predicate_uses()
        elif self.manifest.item_type == 'types':
            output['type_uses'] = self.count_object_uses()
        return output
    
    def count_predicate_uses(self):
        """ counts numbers of distinct
            subjects used with a given predicate
        """
        sub_asses = Assertion.objects\
                             .filter(predicate_uuid=self.uuid)\
                             .distinct('uuid')\
                             .count()
        return sub_asses
    
    def count_object_uses(self):
        """ counts numbers of distinct
            subjects used with a given object
        """
        obj_asses = Assertion.objects\
                             .filter(object_uuid=self.uuid)\
                             .distinct('uuid')\
                             .count()
        return obj_asses

    def count_and_alter_unqiue_rel_to_subject(self, new_subject_uuid=None):
        """ gets a count of items related to the subject, and ONLY
            the subject,
            if the new_subject_uuid is a string, then this will
            also alter the relationships to a new subject so as
            not to loose linking relationships
        """
        sub_asses = Assertion.objects\
                             .filter(uuid=self.uuid,
                                     object_type__in=self.uniquely_linking_types)\
                             .exclude(predicate_uuid=Assertion.PREDICATES_CONTAINS)\
                             .distinct('object_uuid')\
                             .order_by('object_uuid')
        sub_only_count = 0
        for sub_ass in sub_asses:
            # The sub_asses list is a list of items linked (except for containment) to the
            # item to that may be deleted.
            # Below, the other_count checks to see if the linked item has links to
            # other items.
            other_count = Assertion.objects\
                                   .filter(object_uuid=sub_ass.object_uuid,
                                           subject_type__in=self.uniquely_linking_types)\
                                   .exclude(uuid=self.uuid)\
                                   .count()
            if other_count == 0:
                # if the self.uuid item is deleted, then some related items
                # will be left as orphans, without any linking relations
                # to subjects, media, or documents
                # this will likely cause data integrity problems
                sub_only_count += 1
                if isinstance(new_subject_uuid, str):
                    # because the_subject_uuid is a string, we
                    # need to alter this assertion so that the
                    # the object will not be orphaned
                    new_sub_ass = sub_ass
                    del_hash_id = sub_ass.hash_id
                    sub_ass.delete()
                    new_sub_ass.source_id = self.editorial_uuid
                    new_sub_ass.uuid = new_subject_uuid
                    Assertion.objects\
                             .filter(hash_id=del_hash_id).delete()
                    new_sub_ass.save()
        return sub_only_count

    def count_spatial_children(self):
        """ returns a count of children from spatial relations """
        child_count = Assertion.objects\
                               .filter(uuid=self.uuid,
                                       predicate_uuid=Assertion.PREDICATES_CONTAINS)\
                               .count()
        return child_count

    def clear_caches(self):
        """ clears all the caches """
        cache = caches['redis']
        cache.clear()
        cache = caches['default']
        cache.clear()
