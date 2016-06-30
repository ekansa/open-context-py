import uuid as GenUUID
from django.db import models
from django.conf import settings
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.apps.exports.exptables.models import ExpTable
from opencontext_py.apps.exports.exptables.manage import ExpManage
from opencontext_py.apps.exports.exprecords.create import Create
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.ocitems.subjects.models import Subject


# Creates export table
class ExpTabCreate():
    """

from opencontext_py.apps.exports.exptables.create import ExpTabCreate
extab_c = ExpTabCreate()
# extab_c.table_id = 'b5f81371-35db-4644-b353-3f5648eeb222'
extab_c.label = 'Data Table of Biometry for Dog "Burials" from Tell Gezer and Other Sites'
extab_c.include_equiv_ld_literals = False
extab_c.include_ld_source_values = False
extab_c.project_uuids = ['646b7034-07b7-4971-8d89-ebe37dda4cd2']
extab_c.class_uris = ['oc-gen:cat-animal-bone']
# extab_c.source_ids = ['ref:1910791260696']
extab_c.create_table()


from opencontext_py.apps.exports.exptables.models import ExpTable
from opencontext_py.apps.exports.exprecords.models import ExpCell
from opencontext_py.apps.exports.expfields.models import ExpField
rem_tabs = ['ea16a444-9876-4fe7-8ffb-389b54a7e3a0', 'b5f81371-35db-4644-b353-3f5648eeb222']
ExpTable.objects.filter(table_id__in=rem_tabs).delete()
ExpField.objects.filter(table_id__in=rem_tabs).delete()
ExpCell.objects.filter(table_id__in=rem_tabs).delete()

from opencontext_py.apps.exports.exptables.create import ExpTabCreate
extab_c = ExpTabCreate()
extab_c.table_id = 'ea16a444-9876-4fe7-8ffb-389b54a7e3a0'
extab_c.label = 'Cranial Specimen Data for European Aurochs and Domestic Cattle'
extab_c.include_equiv_ld_literals = False
extab_c.include_ld_source_values = False
extab_c.project_uuids = ['1816A043-92E2-471D-A23D-AAC58695D0D3']
extab_c.class_uris = ['oc-gen:cat-animal-bone']
extab_c.source_ids = ['ref:2288268357961']
extab_c.create_table()

from opencontext_py.apps.exports.exptables.create import ExpTabCreate
extab_c = ExpTabCreate()
extab_c.table_id = 'b5f81371-35db-4644-b353-3f5648eeb222'
extab_c.label = 'Postcranial Data for European Aurochs and Domestic Cattle'
extab_c.include_equiv_ld_literals = False
extab_c.include_ld_source_values = False
extab_c.project_uuids = ['1816A043-92E2-471D-A23D-AAC58695D0D3']
extab_c.class_uris = ['oc-gen:cat-animal-bone']
extab_c.source_ids = ['ref:1910791260696', 'ref:1569687538629']
extab_c.create_table()


    """

    def __init__(self):
        self.table_id = None
        self.label = None
        self.dates_bce_ce = True  # calendar dates in BCE/CE, if false BP
        self.include_equiv_ld = True  # include linked data related by EQUIV_PREDICATES
        self.include_equiv_ld_literals = True  # include linked data related by Equiv Predicates for literal objects
        self.include_ld_obj_uris = True  # include URIs to linked data objects
        self.include_ld_source_values = True  # include original values annoted as
                                              # equivalent to linked data
        self.boolean_multiple_ld_fields = False  # for multiple values of linked data
                                                 # (same predicate, multiple objects)
                                                 # make multiple fields if NOT False.
                                                 # When this value is NOT False, its
                                                 # string value indicates presence of
                                                 # a linked data object uri.
        self.include_original_fields = True  # include original field data
        self.source_field_label_suffix = ''
        self.project_uuids = []
        self.class_uris = []
        self.source_ids = []
        self.context_path = None
        self.uuid_list = []

    def make_uuid_list_for_table(self):
        """ makes a uuid list for items in the table """
        args = {}
        sub_args = {}
        args['class_uri__in'] = self.class_uris
        args['item_type'] = 'subjects'
        if len(self.project_uuids) > 0:
            args['project_uuid__in'] = self.project_uuids
            sub_args['project_uuid__in'] = self.project_uuids
        if len(self.source_ids) > 0:
            args['source_id__in'] = self.source_ids
        if isinstance(self.context_path, str):
            # limit the uuid_list by context path
            sub_args['context__startswith'] = self.context_path
            context_uuids = []
            subs = Subject.objects\
                          .filter(**sub_args)\
                          .iterator()
            for sub in subs:
                context_uuids.append(sub.uuid)
            if len(context_uuids) > 0:
                args['uuid__in'] = context_uuids
        # now get the uuids!
        man_items = Manifest.objects\
                            .filter(**args)\
                            .order_by('sort')\
                            .iterator()
        for man in man_items:
            self.uuid_list.append(man.uuid)
        return self.uuid_list

    def create_table(self):
        """ creates an export table """
        self.make_uuid_list_for_table()
        if len(self.uuid_list) > 0:
            if self.table_id is None:
                self.table_id = str(GenUUID.uuid4())
            ex_tab = ExpTable()
            ex_tab.table_id = self.table_id
            ex_tab.label = self.label
            ex_tab.field_count = 0
            ex_tab.row_count = 0
            ex_tab.save()
            ctab = Create()
            ctab.table_id = self.table_id
            ctab.include_equiv_ld = self.include_equiv_ld
            ctab.include_ld_source_values = self.include_ld_source_values
            ctab.include_original_fields = self.include_original_fields
            ctab.include_equiv_ld_literals = self.include_equiv_ld_literals
            ctab.boolean_multiple_ld_fields = self.boolean_multiple_ld_fields   # single field for LD fields
            ctab.source_field_label_suffix = self.source_field_label_suffix  # blank suffix for source data field names
            ctab.prep_default_fields()
            ctab.uuidlist = self.uuid_list
            ctab.process_uuid_list(self.uuid_list)
            ctab.get_predicate_uuids()  # now prepare to do item descriptions
            ctab.get_predicate_link_annotations()  # even if not showing linked data
            ctab.process_ld_predicates_values()  # only if exporting linked data
            ctab.save_ld_fields()  # only if exporting linked data
            ctab.save_source_fields()  # save source data, possibly limited by observations
            ctab.update_table_metadata()  # save a record of the table metadata
            # now save metadata for the table
            ex_man = ExpManage()
            ex_man.save_table_manifest_record(self.table_id)
            ex_man.generate_table_metadata(self.table_id, True)
            # all done!
