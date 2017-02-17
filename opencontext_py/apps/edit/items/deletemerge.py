from django.conf import settings
from django.db import models
from django.db.models import Q
from opencontext_py.apps.entities.uri.models import URImanagement
from opencontext_py.apps.ldata.linkentities.models import LinkEntity
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.ocitems.assertions.models import Assertion
from opencontext_py.apps.ocitems.assertions.containment import Containment
from opencontext_py.apps.ldata.linkannotations.models import LinkAnnotation
from opencontext_py.apps.ocitems.subjects.generation import SubjectGeneration
from opencontext_py.apps.ocitems.subjects.models import Subject
from opencontext_py.apps.ocitems.predicates.models import Predicate
from opencontext_py.apps.ocitems.octypes.models import OCtype
from opencontext_py.apps.ocitems.mediafiles.models import Mediafile
from opencontext_py.apps.ocitems.documents.models import OCdocument
from opencontext_py.apps.ocitems.persons.models import Person
from opencontext_py.apps.ocitems.geospace.models import Geospace


# This class is used to delete or merge entities
class DeleteMerge():
    """ methods to delete and merge entities, including
        subjects entities

from opencontext_py.apps.edit.items.deletemerge import DeleteMerge
dm = DeleteMerge()
delete_uuid = 'f6d5304c-bf4e-467d-b3c1-afd7a0d88e10'
merge_into_uuid = '2A1B75E6-8C79-49B9-873A-A2E006669691'
dm.merge_by_uuid(delete_uuid, merge_into_uuid)

    """


    def __init__(self):
        self.source_id = None
        self.delete_uuid = False
        self.delete_manifest_obj = False
        self.delete_prefix_uri = False
        self.delete_uri = False
        self.delete_children = False
        self.merge_into_uuid = False
        self.merge_manifest_obj = False
        self.merge_prefix_uri = False
        self.merge_uri = False
        self.merge_children = False

    def merge_by_uuid(self, delete_uuid, merge_into_uuid):
        """ Merges an item. The delete_uuid will be destroyed, but all of it's associated
            data will be merged into the 'merge_into_uuid' which will be retained.
            Returns a dictionary about what happened
        """
        self.delete_uuid = delete_uuid
        self.merge_into_uuid = merge_into_uuid
        ok_delete = self.prep_delete_uuid(delete_uuid)
        ok_merge = self.prep_merge_uuid(merge_into_uuid)
        output = {}
        output['done'] = False
        if ok_delete and ok_merge and delete_uuid != merge_into_uuid:
            output['assertions'] = self.alter_assertions(delete_uuid, merge_into_uuid)
            output['annotations'] = self.alter_annotations(delete_uuid, merge_into_uuid)
            output['geospace'] = self.alter_geospace(delete_uuid, merge_into_uuid)
            self.delete_self_containment(merge_into_uuid)
            # changes oc_subjects path information to reflect new reality
            sg = SubjectGeneration()
            sg.generate_save_context_path_from_uuid(merge_into_uuid,
                                                    True)
            output['message'] = 'Merged item. Deleted - '
            output['message'] += self.delete_manifest_obj.label + '(' + delete_uuid + ')'
            output['message'] = ', merged into - '
            output['message'] += self.merge_manifest_obj.label + '(' + merge_into_uuid + ')'
            self.delete_manifest_obj.delete()  # deletes object from the manifest
            self.delete_type_records(delete_uuid, self.delete_manifest_obj.item_type)
            output['done'] = True
        return output

    def delete_type_records(self, uuid, item_type):
        """ Deletes records of data specific to models of different types
            For now, we're not deleting strings, since they may be used
            on one or more types.
        """
        output = True
        if item_type == 'subjects':
            Subject.objects.filter(uuid=uuid).delete()
        elif item_type == 'media':
            Mediafile.objects.filter(uuid=uuid).delete()
        elif item_type == 'documents':
            OCdocument.objects.filter(uuid=uuid).delete()
        elif item_type == 'persons':
            Person.objects.filter(uuid=uuid).delete()
        elif item_type == 'predicates':
            Predicate.objects.filter(uuid=uuid).delete()
        elif item_type == 'types':
            OCtype.objects.filter(uuid=uuid).delete()
        else:
            output = False
        return output

    def prep_delete_uuid(self, delete_uuid):
        """ Prepares some information needed to delete a uuid
        """
        ok_delete = False
        delete_obj = self.get_manifest(delete_uuid)
        if delete_obj is not False:
            ok_delete = True
            self.delete_manifest_obj = delete_obj
            self.delete_uri = URImanagement.make_oc_uri(delete_uuid,
                                                        delete_obj.item_type)
            self.delete_prefix_uri = URImanagement.prefix_common_uri(self.delete_uri)
        return ok_delete

    def prep_merge_uuid(self, merge_into_uuid):
        """ Prepares some information needed to delete a uuid
        """
        ok_merge = False
        merge_obj = self.get_manifest(merge_into_uuid)
        if merge_obj is not False:
            ok_merge = True
            self.merge_manifest_obj = merge_obj
            self.merge_uri = URImanagement.make_oc_uri(merge_into_uuid,
                                                       merge_obj.item_type)
            self.merge_prefix_uri = URImanagement.prefix_common_uri(self.merge_uri)
        return ok_merge

    def alter_assertions(self, delete_uuid, merge_into_uuid=False):
        """
        alters the assertions table to change uuids to a new uuid
        or delete them entirely
        """
        output = {}
        output['subjects'] = self.alter_assertions_by_role('subjects',
                                                           delete_uuid,
                                                           merge_into_uuid)
        output['predicates'] = self.alter_assertions_by_role('predicates',
                                                             delete_uuid,
                                                             merge_into_uuid)
        output['objects'] = self.alter_assertions_by_role('objects',
                                                          delete_uuid,
                                                          merge_into_uuid)
        return output
    
    def alter_geospace(self, delete_uuid, merge_into_uuid=False):
        """
        alters the geospace data to change uuids to a new uuid
        or delete them entirely
        """
        old_geos = Geospace.objects\
                           .filter(uuid=delete_uuid)
        for old_geo in old_geos:
            if merge_into_uuid is not False:
                new_geo = old_geo
                new_geo.uuid = merge_into_uuid
                Geospace.objects\
                        .filter(hash_id=old_geo.hash_id)\
                        .delete()
                new_geo.save()
            else:
                Geospace.objects\
                        .filter(uuid=delete_uuid,
                                hash_id=old_geo.hash_id)\
                        .delete()

    def alter_annotations(self, delete_uuid, merge_into_uuid=False):
        """
        alters the link annotations table to change uuids to a new uuid
        or delete them entirely
        """
        output = {}
        output['subjects'] = self.alter_annotations_by_role('subjects',
                                                            delete_uuid,
                                                            merge_into_uuid)
        output['predicates'] = self.alter_annotations_by_role('predicates',
                                                              delete_uuid,
                                                              merge_into_uuid)
        output['objects'] = self.alter_annotations_by_role('objects',
                                                           delete_uuid,
                                                           merge_into_uuid)
        return output

    def alter_assertions_by_role(self,
                                 role,
                                 delete_uuid,
                                 merge_into_uuid=False,
                                 only_predicate_uuid=False):
        """
        alters the assertions table to change uuids to a new uuid
        or delete them entirely

        if only_predicate_uuid is not false, then limit changes to a given predicate
        """
        change_count = 0
        if role == 'subjects':
            if only_predicate_uuid is False:
                old_assertions = Assertion.objects\
                                          .filter(uuid=delete_uuid)
            else:
                old_assertions = Assertion.objects\
                                          .filter(uuid=delete_uuid,
                                                  predicate_uuid=only_predicate_uuid)
        elif role == 'predicates':
            old_assertions = Assertion.objects\
                                      .filter(predicate_uuid=delete_uuid)
        elif role == 'objects':
            if only_predicate_uuid is False:
                old_assertions = Assertion.objects\
                                          .filter(object_uuid=delete_uuid)
            else:
                old_assertions = Assertion.objects\
                                          .filter(predicate_uuid=only_predicate_uuid,
                                                  object_uuid=delete_uuid)
        else:
            old_assertions = []
        for bad_ass in old_assertions:
            if merge_into_uuid is not False:
                # the assertion needs to get modified to use the new
                # uuid
                new_ass = bad_ass
                if role == 'subjects':
                    new_ass.uuid = merge_into_uuid
                elif role == 'predicates':
                    new_ass.predicate_uuid = merge_into_uuid
                elif role == 'objects':
                    new_ass.object_uuid = merge_into_uuid
                Assertion.objects\
                         .filter(hash_id=bad_ass.hash_id).delete()
                new_ass.save()
            else:
                Assertion.objects\
                         .filter(hash_id=bad_ass.hash_id).delete()
            change_count += 1
        return change_count

    def delete_self_containment(self, uuid):
        old_assertions = Assertion.objects\
                                  .filter(uuid=uuid,
                                          predicate_uuid=Assertion.PREDICATES_CONTAINS,
                                          object_uuid=uuid)\
                                  .delete()

    def alter_annotations_by_role(self,
                                  role,
                                  delete_uuid,
                                  merge_into_uuid=False):
        """
        alters the links_annotations table to change uuids to a new uuid
        or delete them entirely
        """
        change_count = 0
        if role == 'subjects':
            old_annotations = LinkAnnotation.objects\
                                            .filter(Q(subject=delete_uuid)
                                                    | Q(subject=self.delete_uri)
                                                    | Q(subject=self.delete_prefix_uri))
        elif role == 'predicates':
            old_annotations = LinkAnnotation.objects\
                                            .filter(Q(predicate_uri=delete_uuid)
                                                    | Q(predicate_uri=self.delete_uri)
                                                    | Q(predicate_uri=self.delete_prefix_uri))
        elif role == 'objects':
            old_annotations = LinkAnnotation.objects\
                                            .filter(Q(object_uri=delete_uuid)
                                                    | Q(object_uri=self.delete_uri)
                                                    | Q(object_uri=self.delete_prefix_uri))
        else:
            old_annotations = []
        for bad_anno in old_annotations:
            if merge_into_uuid is not False and self.merge_uri is not False:
                # the assertion needs to get modified to use the new
                # uuid
                new_anno = bad_anno
                if isinstance(self.source_id, str):
                    new_anno.source_id = self.source_id
                if role == 'subjects':
                    new_anno.subject = merge_into_uuid
                elif role == 'predicates':
                    new_anno.predicate_uri = self.merge_uri
                elif role == 'objects':
                    new_anno.object_uri = self.merge_uri
                new_anno.save()
            LinkAnnotation.objects\
                          .filter(hash_id=bad_ass.hash_id).delete()
            change_count += 1
        return change_count

    def get_manifest(self, act_identifier, try_slug=False):
        """
        gets basic metadata about the item from the Manifest app
        """
        man_obj = False
        if(try_slug):
            try:
                man_obj = Manifest.objects.get(Q(uuid=act_identifier) | Q(slug=act_identifier))
            except Manifest.DoesNotExist:
                man_obj = False
        else:
            try:
                man_obj = Manifest.objects.get(uuid=act_identifier)
            except Manifest.DoesNotExist:
                man_obj = False
        return man_obj
