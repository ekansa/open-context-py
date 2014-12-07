import uuid as GenUUID
import datetime
from django.db import models
from django.db.models import Q
from opencontext_py.apps.imports.fields.models import ImportField
from opencontext_py.apps.imports.records.models import ImportCell
from opencontext_py.apps.imports.fields.create import ImportFields
from opencontext_py.apps.imports.refine.api import RefineAPI


# Imports records, doing the appropriate lookups for uuids
class ImportRecords():

    def __init__(self):
        self.source_id = False
        self.obsolete_source_id = False
        self.project_uuid = False
        self.related_fields = {}
        self.do_batch = True

    def save_refine_records(self,
                            refine_project,
                            start=False):
        """ Loads a schema from refine, saves it in the database """
        row_num = 0
        r_api = RefineAPI(refine_project)
        self.source_id = r_api.source_id
        if self.do_batch:
            # get a batch of data
            r_api.get_data_batch_to_model(start)
        else:
            # get all the data at once from Refine (not in batches)
            r_api.get_data_to_model()
        if len(r_api.data) > 0:
            print('Records to import: ' + str(len(r_api.data)))
            bulk_list = []
            for record in r_api.data:
                row_num = record['row_num']
                for field_num, cell_value in record['cells'].items():
                    imp_cell = ImportCell()
                    imp_cell.source_id = self.source_id
                    imp_cell.project_uuid = self.project_uuid
                    imp_cell.row_num = row_num
                    imp_cell.field_num = int(float(field_num))
                    imp_cell.rec_hash = ImportCell().make_rec_hash(self.project_uuid,
                                                                   str(cell_value))
                    imp_cell.fl_uuid = False
                    imp_cell.l_uuid = False
                    imp_cell.cell_ok = True  # default to Import OK
                    imp_cell.record = str(cell_value)
                    # imp_cell.save()
                    bulk_list.append(imp_cell)
            ImportCell.objects.bulk_create(bulk_list)
            bulk_list = None
            print('Done with: ' + str(row_num))
        return row_num
