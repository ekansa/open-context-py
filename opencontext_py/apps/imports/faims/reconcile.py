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


class FaimsReconcile():
    """ Reconciling FAIMS data with the Open Context database
            
    """

    def __init__(self):
        self.project_uuid = False
        self.source_id = False
        self.oc_config_relation_types = 'oc-relation-types'
        self.oc_config_entity_types = 'oc-entity-types'
        self.oc_config_attributes = 'oc-attributes'
        self.oc_config_types = 'oc-types'

    def gen_configs(self, act_dir):
        """ read xml files, generate JSON configuration files  """
        self.gen_config_rels(act_dir)
        self.gen_config_archents(act_dir)
        self.gen_config_attributes(act_dir)
    
    def gen_config_rels(self, act_dir):
        """ make a relations config file """
        faims_rels = RelationsImport()
        faims_rels.oc_config_relation_types = self.oc_config_relation_types
        faims_rels.gen_config(act_dir)
    
    def gen_config_archents(self, act_dir):
        """ make configurations from the arch ents file """
        faims_ents = ArchEntsImport()
        faims_ents.oc_config_entity_types = self.oc_config_relation_types
        faims_ents.oc_config_attributes = self.oc_config_attributes
        faims_ents.gen_config(act_dir)
    
    def gen_config_attributes(self, act_dir):
        """ make configurations from the attributes file """
        faims_attribs = AttributesImport()
        faims_attribs.oc_config_attributes = self.oc_config_attributes
        faims_attribs.oc_config_types = self.oc_config_types
        faims_attribs.gen_config(act_dir)
        