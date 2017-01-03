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


# STEP 1: DELETE PRIOR DATA
source_id = 'faims-survey'
project_uuid = '59ae0bd4-2dda-4428-b163-8ef0d579e2b9'
from opencontext_py.apps.imports.sources.unimport import UnImport
unimp = UnImport(source_id, project_uuid)
unimp.delete_ok = True
unimp.delete_all()

# STEP 2: SET UP CONFIG FILES
source_id = 'faims-survey'
project_uuid = '59ae0bd4-2dda-4428-b163-8ef0d579e2b9'
from opencontext_py.apps.imports.faims.main import FaimsImport
faims_imp = FaimsImport()
faims_imp.project_uuid = project_uuid
faims_imp.source_id = source_id
faims_imp.root_subject_label = 'Mordor'
faims_imp.gen_configs('faims-survey')

# STEP 3: EDIT CONFIG FILES


# STEP 4: SAVE RECONCILE PREDICATES, TYPES
source_id = 'faims-survey'
project_uuid = '59ae0bd4-2dda-4428-b163-8ef0d579e2b9'
from opencontext_py.apps.imports.faims.main import FaimsImport
faims_imp = FaimsImport()
faims_imp.project_uuid = project_uuid
faims_imp.source_id = source_id
faims_imp.save_reconcile_predicates_types('faims-survey')

     
# STEP 5: SAVE ENTITIES then DESCRIBE THEM
source_id = 'faims-survey'
project_uuid = '59ae0bd4-2dda-4428-b163-8ef0d579e2b9'
from opencontext_py.apps.imports.faims.main import FaimsImport
faims_imp = FaimsImport()
faims_imp.root_subject_label = 'Mordor'
faims_imp.project_uuid = project_uuid
faims_imp.source_id = source_id     
faims_imp.save_describe_entities('faims-survey')

# faims_imp.save_reconcile_preds_relations('faims-survey')
    """

    def __init__(self):
        self.project_uuid = False
        self.source_id = False
        self.oc_config_relation_types = 'oc-relation-types'
        self.oc_config_entity_types = 'oc-entity-types'
        self.oc_config_attributes = 'oc-attributes'
        self.oc_config_entities = 'oc-entities'
        self.root_subject_label = False
        self.root_subject_uuid = False
        self.root_subject_context = False
        self.root_subject_class = 'oc-gen:cat-site'
        self.root_subject_sup_id = 'auto-root'

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
    
    def save_reconcile_predicates_types(self, act_dir):
        """ saves and/or reconciles predicates for linking
            relations and descriptions, as well as controlled
            vocabulary concepts as oc_types.
            
            This step happens BEFORE entities get described
        """
        print('Save / reconcile entity types for description...')
        self.save_reconcile_entity_type_types(act_dir)
        print('Save / reconcile descriptive predicates and types...')
        self.save_reconcile_preds_types(act_dir)
        print('Save / reconcile linking predicates...')
        self.save_reconcile_preds_relations(act_dir)
    
    def save_reconcile_entity_type_types(self, act_dir):
        """ saves and/or reconciles a predicate for describing
            an items "entity_type", makes oc_types for each
            entity type used.
        """
        faims_ents = ArchEntsImport()
        faims_ents.project_uuid = self.project_uuid
        faims_ents.source_id = self.source_id
        faims_ents.oc_config_entity_types = self.oc_config_entity_types
        faims_ents.db_save_reconcile_entity_predicates_types(act_dir)
    
    def save_reconcile_preds_types(self, act_dir):
        """ saves and/or reconciles predicates for description
            as well as controlled vocabulary concepts as oc_types.
        """
        faims_attribs = AttributesImport()
        faims_attribs.oc_config_attributes = self.oc_config_attributes
        faims_attribs.project_uuid = self.project_uuid
        faims_attribs.source_id = self.source_id
        faims_attribs.db_save_reconcile_predicates_types(act_dir)
    
    def save_reconcile_preds_relations(self, act_dir):
        """ saves and/or reconciles predicates for linking relations
        """
        faims_rels = RelationsImport()
        faims_rels.oc_config_relation_types = self.oc_config_relation_types
        faims_rels.project_uuid = self.project_uuid
        faims_rels.source_id = self.source_id
        faims_rels.db_save_reconcile_predicates(act_dir)
    
    def save_describe_entities(self, act_dir):
        """ saves and/or reconciles predicates for linking
            relations and descriptions, as well as controlled
            vocabulary concepts as oc_types.
            
            This step happens BEFORE entities get described
        """
        print('Save subject entities...')
        self.save_subject_entities(act_dir)
        print('Save entity relationships...')
        self.save_entity_relations(act_dir)
        print('Save entity descriptions...')
        self.save_entity_descriptions(act_dir)
    
    def save_subject_entities(self, act_dir):
        """ saves the subject entities from archents.xml file
        
            this involves some complexity, because we don't
            have clear spatial containment for the items.

        """
        faims_ents = ArchEntsImport()
        faims_ents.project_uuid = self.project_uuid
        faims_ents.source_id = self.source_id
        faims_ents.oc_config_relation_types = self.oc_config_relation_types
        faims_ents.oc_config_entity_types = self.oc_config_entity_types
        faims_ents.oc_config_attributes = self.oc_config_attributes
        faims_ents.oc_config_entities = self.oc_config_entities
        faims_ents.root_subject_label = self.root_subject_label
        faims_ents.root_subject_uuid = self.root_subject_uuid
        faims_ents.root_subject_context = self.root_subject_context
        faims_ents.root_subject_class = self.root_subject_class
        faims_ents.root_subject_sup_id = self.root_subject_sup_id
        # first we make the initial subjects,
        # by default they get created as children of the root_subject_uuid
        # we move them later...
        faims_ents.db_initial_subjects_creation(act_dir)
    
    def save_entity_relations(self, act_dir):
        """ saves relationships between entities,
            this will change spatial hiearchies from the default
            to what FAIMS explicitly specifies. It also adds
            non-containment relations
        """
        faims_rels = RelationsImport()
        faims_rels.oc_config_relation_types = self.oc_config_relation_types
        faims_rels.oc_config_entities = self.oc_config_entities
        faims_rels.project_uuid = self.project_uuid
        faims_rels.source_id = self.source_id
        faims_rels.db_faims_relations_import(act_dir)
    
    def save_entity_descriptions(self, act_dir):
        """ saves the descriptions of subject entities from archents.xml file
        """
        faims_ents = ArchEntsImport()
        faims_ents.project_uuid = self.project_uuid
        faims_ents.source_id = self.source_id
        faims_ents.oc_config_entity_types = self.oc_config_entity_types
        faims_ents.oc_config_attributes = self.oc_config_attributes
        faims_ents.oc_config_entities = self.oc_config_entities
        faims_ents.root_subject_label = self.root_subject_label
        faims_ents.root_subject_uuid = self.root_subject_uuid
        faims_ents.root_subject_context = self.root_subject_context
        faims_ents.root_subject_class = self.root_subject_class
        faims_ents.root_subject_sup_id = self.root_subject_sup_id
        # first we make the initial subjects,
        # by default they get created as children of the root_subject_uuid
        # we move them later...
        faims_ents.db_save_entity_attributes(act_dir)
