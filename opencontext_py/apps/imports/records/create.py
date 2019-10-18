import uuid as GenUUID
import datetime
import numpy as np
import pandas as pd
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
    
    def save_dataframe_records(
        self,
        source_id,
        df,
        do_valiate=True
    ):
        """ Loads a schema from refine, saves it in the database """
        self.source_id = source_id
        if df.empty:
            return None
        print('Importing {} records from: {}'.format(
                len(df.index),
                self.source_id
            )
        )

        cols = df.columns.tolist()
        for i, row in df.iterrows():
            row_num = i + 1
            bulk_list = []
            for field_num, col in enumerate(cols, 1):
                cell_value = row[col]
                if cell_value in [np.nan, None, 'nan']:
                    cell_value = ''
                cell_value = str(cell_value).strip()
                if cell_value == 'nan':
                     cell_value = ''
                imp_cell = ImportCell()
                imp_cell.source_id = self.source_id
                imp_cell.project_uuid = self.project_uuid
                imp_cell.row_num = row_num
                imp_cell.field_num = field_num
                imp_cell.rec_hash = ImportCell().make_rec_hash(
                    self.project_uuid,
                    cell_value
                )
                imp_cell.fl_uuid = False
                imp_cell.l_uuid = False
                imp_cell.cell_ok = True  # default to Import OK
                imp_cell.record = cell_value
                bulk_list.append(imp_cell)
            # Now bulk create the list of records in this row
            ImportCell.objects.bulk_create(bulk_list)
            bulk_list = None
        df_len = len(df.index)
        print('FINISHED import of {} records from: {}'.format(
                len(df.index),
                self.source_id
            )
        )
        if not do_valiate:
            return row_num
        for field_num, col in enumerate(cols, 1):
            rec_count = ImportCell.objects.filter(
                source_id=self.source_id,
                field_num=field_num
            ).count()
            print('Imported {} [{}]: {}, expected {}'.format(
                    col,
                    field_num,
                    rec_count,
                    df_len
                )
            )
            assert rec_count == df_len
        return row_num