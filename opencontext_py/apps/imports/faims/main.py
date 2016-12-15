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
from opencontext_py.apps.ocitems.geospace.models import Geospace
from opencontext_py.apps.ocitems.events.models import Event
from opencontext_py.apps.imports.fields.datatypeclass import DescriptionDataType
from opencontext_py.apps.imports.faims.files import FileManage
from opencontext_py.apps.imports.faims.archents import ArchEntsImport
from opencontext_py.apps.imports.faims.relations import RelationsImport
from opencontext_py.apps.imports.faims.attributes import AttributesImport
from opencontext_py.apps.imports.sources.models import ImportSource
from opencontext_py.apps.imports.sources.unimport import UnImport


class FaimsImport():
    """ Loads FAIMS xml files in the proper order for import
        (1) First generates oc_config_* files that store
            configurations in JSON. These configurations can be
            edited to customize how the import will be processed.
            Configuration files need to be generated in the proper
            order, starting with relation types, then entity types,
            then attributes.
        (2) Once configurations are created, the entities will be
            imported if they have a proper spatial containment
            path.

from opencontext_py.apps.imports.faims.main import FaimsImport
faims_imp = FaimsImport()
faims_imp.gen_configs('faims-test')

from opencontext_py.apps.imports.sources.unimport import UnImport
unimp = UnImport('faims-test', 'faims-test')
unimp.delete_ok = True
unimp.delete_all()

from opencontext_py.apps.imports.faims.main import FaimsImport
faims_imp = FaimsImport()
faims_imp.project_uuid = 'faims-test'
faims_imp.source_id = 'faims-test'
faims_imp.gen_configs('faims-test')
faims_imp.save_reconcile_preds_types('faims-test')

            
    """

    def __init__(self):
        self.project_uuid = False
        self.source_id = False
        self.oc_config_relation_types = 'oc-relation-types'
        self.oc_config_entity_types = 'oc-entity-types'
        self.oc_config_attributes = 'oc-attributes'
        self.oc_config_entities = 'oc-entities'

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
        faims_ents.oc_config_relation_types = self.oc_config_relation_types
        faims_ents.oc_config_entity_types = self.oc_config_entity_types
        faims_ents.oc_config_attributes = self.oc_config_attributes
        faims_ents.gen_config(act_dir)
    
    def gen_config_attributes(self, act_dir):
        """ make configurations from the attributes file """
        faims_attribs = AttributesImport()
        faims_attribs.oc_config_attributes = self.oc_config_attributes
        faims_attribs.gen_config(act_dir)
    
    def save_reconcile_preds_types(self, act_dir):
        """ make configurations from the attributes file """
        faims_attribs = AttributesImport()
        faims_attribs.oc_config_attributes = self.oc_config_attributes
        faims_attribs.project_uuid = self.project_uuid
        faims_attribs.source_id = self.source_id
        faims_attribs.db_save_reconcile_predicates_types(act_dir)
    
    def save_reconcile_preds_relations(self, act_dir):
        """ make configurations from the attributes file """
        faims_rels = RelationsImport()
        faims_rels.oc_config_relation_types = self.oc_config_relation_types
        faims_rels.project_uuid = self.project_uuid
        faims_rels.source_id = self.source_id
        faims_rels.db_save_reconcile_predicates(act_dir)
    
    
    
    
    def prep_importer_sources(self, act_dir, source_suffix=''):
        """ make an importer source object in preparation for running an import """
        self.source_id = 'faims:' + act_dir + source_suffix
        imp_s = ImportSource()
        imp_s.source_id = self.source_id
        imp_s.project_uuid = self.project_uuid
        imp_s.label = 'FAIMS import from "' + act_dir + '"'
        imp_s.field_count = 0
        imp_s.row_count = 0
        imp_s.source_type = 'faims'
        imp_s.is_current = True
        imp_s.imp_status = 'loading'
        imp_s.save()
    