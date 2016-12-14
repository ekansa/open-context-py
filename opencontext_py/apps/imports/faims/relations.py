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
        self.oc_config_relation_types = 'oc-relation-types'
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
            rel_types = self.tree.xpath('/relationships/relationshipType')
            for rel_type in rel_types:
                faims_id = rel_type.get('relntypeid')
                rel_type_obj = LastUpdatedOrderedDict()
                rel_type_obj['id'] = faims_id
                rel_type_obj['label'] = rel_type.get('relntypename')
                rel_type_obj['oc-equiv'] = None
                rel_type_obj['order'] = None
                rel_type_obj['predicate_uuid'] = None
                rel_type_obj['data_type'] = 'id'
                rel_type_obj['predicate_type'] = 'link'
                self.relation_types[faims_id] = rel_type_obj
    
    def db_save_reconcile_predicates(self, act_dir):
        """ saves predicates and type items to the
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