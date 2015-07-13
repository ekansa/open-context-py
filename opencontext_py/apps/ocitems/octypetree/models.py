import uuid as GenUUID
from django.conf import settings
from datetime import datetime, date, time
from django.db import models
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.ocitems.octypes.models import OCtype
from opencontext_py.apps.ocitems.octypes.manage import TypeManagement
from opencontext_py.apps.ldata.linkannotations.models import LinkAnnotation
from opencontext_py.apps.ldata.linkannotations.recursion import LinkRecursion
from opencontext_py.apps.entities.uri.models import URImanagement


class HierarchicTypes():
    """
    Special case of types where there's a hierarchy that needs to be represented
    """
    HIERARCHY_DELIM = '::'
    SOURCE_ID = 'HierarchicTypes'
    PRED_SBJ_IS_SUB_OF_OBJ = 'skos:broader'  # default predicate for subject item is subordinate to object item

    def __init__(self):
        self.source_id = self.SOURCE_ID
        self.p_for_superobjs = self.PRED_SBJ_IS_SUB_OF_OBJ

    def process_new_hierarchic_types(self, revision_date):
        """ Creates new oc_types for parent types (if not yet present)
            of types with hierachic features.
            Also creates the linked data annotations to indicate hierarchy
        """
        output = False
        new_hierarchic_list = self.get_new_hierarchic_types(revision_date)
        if(len(new_hierarchic_list) > 1):
            output = self.create_concept_parents(new_hierarchic_list)
        return output

    def get_new_hierarchic_types(self, revision_date):
        """ Gets a list of types items revised after a date with
            the default delimiter for hierachy, but no superior
            concept
        """
        rdate = datetime.strptime(revision_date, '%Y-%m-%d')
        new_hierarchic_list = []
        hi_types = Manifest.objects.filter(item_type='types',
                                           label__contains=self.HIERARCHY_DELIM,
                                           revised__gte=rdate)
        if(len(hi_types) > 0):
            for hi_type in hi_types:
                lr = LinkRecursion()
                lr.get_entity_parents(hi_type.uuid)
                if(len(lr.parent_entities) < 1):
                    # no superior parents found
                    new_hierarchic_list.append(hi_type)
        return new_hierarchic_list

    def create_concept_parents(self, new_hierachic_list):
        """ Creates new types for
        superior (more general) types from a list
        of types that have hiearchies implicit in their labels
        once the superior types are created,
        linked data annotations noting hierarchy are stored
        """
        parent_children_pairs = []
        for manifest in new_hierachic_list:
            try:
                oc_type = OCtype.objects.get(uuid=manifest.uuid)
            except OCtype.DoesNotExist:
                oc_type = False
            if(oc_type is not False):
                child_parts = manifest.label.split(self.HIERARCHY_DELIM)
                act_delim = ''
                act_new_label = ''
                current_parent = False
                for label_part in child_parts:
                    act_new_label = act_new_label + act_delim + label_part
                    act_delim = self.HIERARCHY_DELIM
                    type_manage = TypeManagement()
                    type_manage.project_uuid = oc_type.project_uuid
                    type_manage.source_id = self.source_id
                    ptype = type_manage.get_make_type_within_pred_uuid(oc_type.predicate_uuid,
                                                                       act_new_label)
                    if(current_parent is not False):
                        parent_child = {'parent': current_parent,
                                        'child': ptype.uuid}
                        parent_children_pairs.append(parent_child)
                    current_parent = ptype.uuid
                if(len(parent_children_pairs) > 0):
                    # now make some linked data annotations
                    for parent_child in parent_children_pairs:
                        if(parent_child['parent'] is not False):
                            new_la = LinkAnnotation()
                            new_la.subject = parent_child['child']
                            new_la.subject_type = 'types'
                            new_la.project_uuid = oc_type.project_uuid
                            new_la.source_id = self.source_id
                            new_la.predicate_uri = self.p_for_superobjs
                            new_la.object_uri = URImanagement.make_oc_uri(parent_child['parent'], 'types')
                            new_la.creator_uuid = ''
                            new_la.save()
        return parent_children_pairs
