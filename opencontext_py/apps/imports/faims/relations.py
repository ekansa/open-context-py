import os
import codecs
import uuid as GenUUID
import re
import datetime
import json
from dateutil.parser import parse
from lxml import etree
from django.db import models
from django.conf import settings
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.ocitems.subjects.generation import SubjectGeneration
from opencontext_py.apps.ocitems.assertions.models import Assertion
from opencontext_py.apps.ocitems.predicates.manage import PredicateManagement
from opencontext_py.apps.imports.faims.files import FileManage


class RelationsImport():
    """ Loads relns.xml files for import
    
        Note: the configuration file 'oc-relations-types.json'
        needs to be edited in a text editor to indicate
        equivalent predicates already in Open Context,
        especially the "oc-gen:contains" predicate.

from opencontext_py.apps.imports.faims.relations import RelationsImport
faims_rels = RelationsImport()
faims_rels.gen_config('faims-survey')

    """

    def __init__(self):
        self.tree = None
        self.project_uuid = False
        self.source_id = False
        self.relation_types = LastUpdatedOrderedDict()
        self.entities = LastUpdatedOrderedDict()
        self.oc_config_relation_types = 'oc-relation-types'
        self.oc_config_entities = 'oc-entities'
        self.reconcile_key = 'faims_id'
        self.fm = FileManage()

    def gen_config(self, act_dir, filename='relns.xml'):
        """ processes the relns file """
        self.tree = self.fm.load_xml_file(act_dir, filename)
        if self.tree is not False:
            self.load_or_classify_relation_types(act_dir)
            
    def load_or_classify_relation_types(self, act_dir):
        """ loads or classifies attributes in a tree """
        key = self.oc_config_relation_types
        json_obj = self.fm.get_dict_from_file(key, act_dir)
        if json_obj is None:
            # need to read the XML and make the classifications from scratch
            self.classify_xml_tree_relation_types()
            self.fm.save_serialized_json(key,
                                         act_dir,
                                         self.relation_types)
        else:
            # we have JSON with relations
            self.relation_types = json_obj

    def classify_xml_tree_relation_types(self):
        """ gets xml relation types """
        if self.tree is not False:
            rel_counts = {}
            rel_types = self.tree.xpath('/relationships/relationshipType')
            for rel_type in rel_types:
                faims_id = rel_type.get('relntypeid')
                relations =  rel_type.xpath('relationship')
                relation_count = len(relations)
                rel_counts[faims_id] = relation_count
                rel_type_obj = LastUpdatedOrderedDict()
                rel_type_obj['id'] = faims_id
                rel_type_obj['label'] = rel_type.get('relntypename')
                rel_type_obj['oc-equiv'] = None
                rel_type_obj['order'] = None
                rel_type_obj['predicate_uuid'] = None
                rel_type_obj['data_type'] = 'id'
                rel_type_obj['predicate_type'] = 'link'
                rel_type_obj['count'] = relation_count
                self.relation_types[faims_id] = rel_type_obj
            s = [(faims_id, rel_counts[faims_id]) for faims_id in sorted(rel_counts,
                                                                         key=rel_counts.get)]
            i = 0
            for faims_id, count in s:
                i += 1
                self.relation_types[faims_id]['order'] = i
    
    def db_save_reconcile_predicates(self, act_dir):
        """ saves predicates to the
            Open Context database, and / or reconciles these
            items with previously saved items from the same project
        """
        key = self.oc_config_relation_types
        json_obj = self.fm.get_dict_from_file(key, act_dir)
        if json_obj is None:
            print('Need to 1st generate a oc-relation-types.json from the relns.xml!')
            ok = False
        else:
            # we have JSON with dictionary for the attributes
            ok = True
            self.relation_types = json_obj
            for faims_id_pred, rel_dict in json_obj.items():
                if not isinstance(rel_dict['oc-equiv'], str):
                    # No equivalence, so reconcile the relation as a new predicate
                    sup_dict = LastUpdatedOrderedDict()
                    sup_dict[self.reconcile_key] = faims_id_pred
                    pm = PredicateManagement()
                    pm.project_uuid = self.project_uuid
                    pm.source_id = self.source_id
                    pm.sup_dict = sup_dict
                    pm.sup_reconcile_key = self.reconcile_key
                    pm.sup_reconcile_value = faims_id_pred
                    pred_obj = pm.get_make_predicate(rel_dict['label'],
                                                     rel_dict['predicate_type'],
                                                     rel_dict['data_type'])
                    if pred_obj is not False:
                        # we reconciled the predicate!
                        self.relation_types[faims_id_pred]['predicate_uuid'] = str(pred_obj.uuid)
            # now save the results
            self.fm.save_serialized_json(key,
                                         act_dir,
                                         self.relation_types)
    
    def db_faims_relations_import(self, act_dir, filename='relns.xml'):
        """ adds relationships to FAIMS entities that map to
            Open Context containment relationships
        """
        if self.tree is None:
            # we have not imported the XML yet
            self.tree = self.fm.load_xml_file(act_dir, filename)
        if len(self.entities) < 1:
            self.entities = self.fm.get_dict_from_file(self.oc_config_entities,
                                                       act_dir)
        if len(self.relation_types) < 1:
            self.relation_types = self.fm.get_dict_from_file(self.oc_config_relation_types,
                                                             act_dir)
        if self.tree is not False and self.entities is not None and self.relation_types is not None:
            # we've loaded the data we need!
            print('Have all data needed to make relations')
            rel_types = self.tree.xpath('/relationships/relationshipType')
            sort_num = 1
            for rel_type in rel_types:
                sort_num += 1  # so non containment observations have different sorting
                faims_id = rel_type.get('relntypeid')
                if faims_id in self.relation_types:
                    # we found a configuration record for the current relationship type
                    rel_dict = self.relation_types[faims_id]
                    if isinstance(rel_dict['oc-equiv'], str)\
                       or isinstance(rel_dict['predicate_uuid'], str):
                        # we've got a reconciled predicate, so it's worth going through
                        # the relations XML
                        relations =  rel_type.xpath('relationship') 
                        for xml_rel in relations:
                            from_id = xml_rel.xpath('fromuuid')[0].text
                            to_id = xml_rel.xpath('touuid')[0].text
                            if from_id in self.entities and to_id in self.entities:
                                # we have a record for both the from and the to FAIMS-item-ids
                                subject_ent = self.entities[from_id]
                                object_ent = self.entities[to_id]
                                contain_pred = Assertion.PREDICATES_CONTAINS
                                if rel_dict['oc-equiv'] == contain_pred \
                                   or rel_dict['predicate_uuid'] == contain_pred:
                                    # we are making a new containment relationship
                                    # the subject is the parent, the object is the child
                                    self.add_change_containment_assertion(subject_ent['uuid'],
                                                                          object_ent['uuid'])
                                else:
                                    # we have a different kind of relationship to add, defined by
                                    # the previously reconciled predicate_uuid
                                    new_ass = Assertion()
                                    new_ass.uuid = subject_ent['uuid']
                                    new_ass.subject_type = subject_ent['item_type']
                                    new_ass.project_uuid = self.project_uuid
                                    new_ass.source_id = self.source_id
                                    new_ass.obs_node = '#obs-' + str(1)
                                    new_ass.obs_num = 1
                                    new_ass.sort = sort_num
                                    new_ass.visibility = 1
                                    new_ass.predicate_uuid = rel_dict['predicate_uuid']
                                    new_ass.object_type = object_ent['item_type']
                                    new_ass.object_uuid = object_ent['uuid']
                                    try:
                                        new_ass.save()
                                    except:
                                        # we probably already have this assertion
                                        pass
    
    def add_change_containment_assertion(self, parent_uuid, child_uuid):
        """ adds or changes a containment assertion """
        contain_pred = Assertion.PREDICATES_CONTAINS
        del_old = Assertion.objects\
                           .filter(predicate_uuid=contain_pred,
                                   object_uuid=child_uuid)\
                           .delete()
        new_ass = Assertion()
        new_ass.uuid = parent_uuid
        new_ass.subject_type = 'subjects'
        new_ass.project_uuid = self.project_uuid
        new_ass.source_id = self.source_id
        new_ass.obs_node = '#contents-' + str(1)
        new_ass.obs_num = 1
        new_ass.sort = 1
        new_ass.visibility = 1
        new_ass.predicate_uuid = contain_pred
        new_ass.object_type = 'subjects'
        new_ass.object_uuid = child_uuid
        new_ass.save()
        # now alter the subject item, regenerating its path
        # for new containment
        sg = SubjectGeneration()
        sg.generate_save_context_path_from_uuid(child_uuid,
                                                True)
            