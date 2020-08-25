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

tabs = [
    (
        [
            'ref:1830065845915',
        ],
        ['oc-gen:cat-sample'],
        'ae266373-dca1-4546-ad57-0db5384a8aad',
        'Data Table of Akvat Survey Observation Points'
    ),
]
ex_tabs = []
for source_ids, class_uris, table_id, label in tabs:
    extab_c = ExpTabCreate()
    extab_c.table_id = table_id
    extab_c.label = label
    extab_c.class_uris = class_uris
    extab_c.include_equiv_ld_literals = False
    extab_c.include_ld_source_values = False
    extab_c.project_uuids = ['02b55e8c-e9b1-49e5-8edf-0afeea10e2be']
    extab_c.source_ids = source_ids
    extab_c.create_table()
    ex_tabs.append(extab_c)


from opencontext_py.apps.exports.exptables.models import ExpTable
from opencontext_py.apps.exports.exprecords.models import ExpCell
from opencontext_py.apps.exports.expfields.models import ExpField
rem_tabs = ['3f315237-38d3-4131-a2b8-666ddec68d7c']
ExpTable.objects.filter(table_id__in=rem_tabs).delete()
ExpField.objects.filter(table_id__in=rem_tabs).delete()
ExpCell.objects.filter(table_id__in=rem_tabs).delete()



# New showing custom list of UUIDs and observation limits
from opencontext_py.apps.ocitems.assertions.models import Assertion

source_id = 'ref:2215688392416'
project_uuid = '01d79ce4-43fb-4eca-9119-0cd505b1972a'
uuids = Assertion.objects.filter(
    source_id=source_id,
    project_uuid=project_uuid,
).distinct('uuid').values_list('uuid', flat=True)


from opencontext_py.apps.exports.exptables.create import ExpTabCreate
extab_c = ExpTabCreate()
extab_c.table_id = '3f315237-38d3-4131-a2b8-666ddec68d7'
extab_c.uuid_list = uuids
extab_c.label = 'Data Table of Pınarbaşı Bird Remains Measurements'
extab_c.include_equiv_ld_literals = False
extab_c.include_ld_source_values = False
extab_c.numeric_fields_last = False
extab_c.project_uuids = [project_uuid]
extab_c.class_uris = ['oc-gen:cat-animal-bone']
extab_c.obs_limits = [2] # Limit to the assertions from obs 2
extab_c.first_add_predicate_uuids = [
    'f21cf62d-b25f-41ac-8f89-0b427d736ac6',
    '5c7ca9c1-af27-488d-9ca8-ee2fc5be7a48',
]
extab_c.last_add_predicate_uuids = [
    '32d26999-e6f0-4dff-885f-52f957aaa815',
]
extab_c.create_table()


from opencontext_py.apps.exports.exptables.create import ExpTabCreate
extab_c = ExpTabCreate()
extab_c.label = 'Data Table of Pınarbaşı Bird Remains Primary Descriptions'
extab_c.include_equiv_ld_literals = False
extab_c.include_ld_source_values = False
extab_c.numeric_fields_last = False
extab_c.project_uuids = [project_uuid]
extab_c.class_uris = ['oc-gen:cat-animal-bone']
extab_c.obs_limits = [1] # Limit to the assertions from obs 2
extab_c.first_add_predicate_uuids = [
    'f21cf62d-b25f-41ac-8f89-0b427d736ac6',
    '5c7ca9c1-af27-488d-9ca8-ee2fc5be7a48',
]
extab_c.last_add_predicate_uuids = [
    '32d26999-e6f0-4dff-885f-52f957aaa815',
]
extab_c.create_table()






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
        self.obs_limits = []
        self.numeric_fields_last = False
        self.first_add_predicate_uuids = [] # Add these predicates first
        self.last_add_predicate_uuids = [] # Add these predicates last

    def make_uuid_list_for_table(self):
        """ makes a uuid list for items in the table """
        if self.uuid_list:
            return self.uuid_list
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
            ctab.obs_limits = self.obs_limits
            ctab.numeric_fields_last = self.numeric_fields_last
            ctab.first_add_predicate_uuids = self.first_add_predicate_uuids
            ctab.last_add_predicate_uuids = self.last_add_predicate_uuids
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
