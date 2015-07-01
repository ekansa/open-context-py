import time
import uuid as GenUUID
from lxml import etree
import lxml.html
from django.db import models
from django.db.models import Q
from opencontext_py.apps.entities.entity.models import Entity
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.ocitems.projects.permissions import ProjectPermissions
from opencontext_py.apps.ocitems.subjects.generation import SubjectGeneration
from opencontext_py.apps.ocitems.assertions.sorting import AssertionSorting
from opencontext_py.apps.ocitems.assertions.models import Assertion
from opencontext_py.apps.ocitems.predicates.models import Predicate
from opencontext_py.apps.ocitems.subjects.models import Subject
from opencontext_py.apps.ocitems.projects.models import Project
from opencontext_py.apps.ocitems.documents.models import OCdocument
from opencontext_py.apps.ocitems.persons.models import Person
from opencontext_py.apps.ocitems.mediafiles.models import Mediafile


class ItemLink():
    """ This class contains methods
        creating, editing, and deleting
        spatial context and linking relationships
    """

    def __init__(self,
                 project_uuid,
                 request=False):
        self.project_uuid = project_uuid
        self.oc_root_project = False
        self.request = request
        self.errors = {'params': False}
        self.response = {}
        try:
            self.project = Project.objects.get(uuid=project_uuid)
        except Project.DoesNotExist:
            self.project = False
        try:
            self.proj_manifest_obj = Manifest.objects.get(uuid=project_uuid)
        except Manifest.DoesNotExist:
            self.proj_manifest_obj = False
        if request is not False and self.project is not False:
            # check to make sure edit permissions OK
            pp = ProjectPermissions(project_uuid)
            self.edit_permitted = pp.edit_allowed(request)
        else:
            # default to no editting permissions
            self.edit_permitted = False
        if project_uuid == '0' \
           or project_uuid == ''  \
           or project_uuid == 'oc':
            self.oc_root_project = True
        else:
            self.oc_root_project = False

    def update_context_link(self,
                            child_uuid,
                            new_parent_uuid):
        """ updates a containment relationship so the child item
            gets a new parent item
        """
        output = False
        p_ass = Assertion.objects\
                         .filter(predicate_uuid=Assertion.PREDICATES_CONTAINS,
                                 object_uuid=child_uuid)
        for bad_ass in p_ass:
            new_ass = bad_ass
            new_ass.uuid = new_parent_uuid
            # now delete the assertion with the old parent
            Assertion.objects\
                     .filter(hash_id=bad_ass.hash_id).delete()
            # now try to save the new assertion with the new parent
            try:
                new_ass.save()
            except:
                # if there's a problem, we'll just assume its a duplicate somehow
                pass
        # update all of the context paths in the Subjects table
        sub_gen = SubjectGeneration()
        output = sub_gen.generate_save_context_path_from_uuid(object_uuid)
        return output

    def delete_specific_link(self,
                             subject_uuid,
                             predicate_uuid,
                             object_uuid):
        """ Deletes a linking assertion
            between two items
        """
        output = True
        Assertion.objects\
                 .filter(uuid=subject_uuid,
                         predicate_uuid=predicate_uuid,
                         object_uuid=object_uuid)\
                 .delete()
        if predicate_uuid == Assertion.PREDICATES_CONTAINS:
            # just changed a containment relationship
            # update all of the context paths in the Subjects table
            sub_gen = SubjectGeneration()
            output = sub_gen.generate_save_context_path_from_uuid(object_uuid)
        return output
