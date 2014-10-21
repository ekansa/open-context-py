import uuid as GenUUID
from django.conf import settings
from django.db import models
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.apps.ocitems.assertions.models import Assertion
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.ocitems.predicates.models import Predicate
from opencontext_py.apps.ocitems.predicates.manage import PredicateManage
from opencontext_py.apps.entities.entity.models import Entity
from opencontext_py.apps.imports.fields.models import ImportField
from opencontext_py.apps.imports.fieldannotations.models import ImportFieldAnnotation
from opencontext_py.apps.imports.records.models import ImportCell
from opencontext_py.apps.imports.records.process import ProcessCells
from opencontext_py.apps.imports.fieldannotations.general import ProcessGeneral


# Processes to generate subjects items for an import
class ProcessLinks():

    def __init__(self, source_id):
        self.source_id = source_id
        pg = ProcessGeneral(source_id)
        pg.get_source()
        self.project_uuid = pg.project_uuid
        self.start_row = 1
        self.batch_size = 250
        self.end_row = self.batch_size
        self.example_size = 5


class CandidateLink():

    def __init__(self):
        self.project_uuid = False
        self.source_id = False
        self.obs_node = False
        self.obs_num = 0
        self.label = False
        self.class_uri = 'link'  # defualt for linking predicates
        self.uuid = False  # final, uuid for the item
        self.data_type = 'id'  # default for linking enitities
        self.sort = 0  # default is not sorted
        self.imp_cell_obj = False  # ImportCell object
        self.evenif_blank = False  # Mint a new item even if the record is blank
        self.import_rows = False  # if a list, then changes to uuids are saved for all rows in this list

    def make_reconcile_link_pred(self,
                                 label):
        """ makes a new linking relationship or
            reconciles with existing relations
        """
        pm = PredicateManage()
        pm.project_uuid = self.project_uuid
        pm.source_id = self.source_id
        pm.data_type = self.data_type
        pm.sort = self.sort
        pm.get_make_predicate(label,
                              self.class_uri,
                              self.data_type)
        self.uuid = pm.predicate.uuid
