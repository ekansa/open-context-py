from django.db import models
from django.db.models import Q
from django.conf import settings
from opencontext_py.apps.imports.records.models import ImportCell


# Imports records, doing the appropriate lookups for uuids
class ProcessCells():

    def __init__(self, source_id, start_row):
        self.source_id = source_id
        self.start_row = start_row
        self.batch_size = settings.IMPORT_BATCH_SIZE
        self.end_row = self.start_row + self.batch_size

    def get_field_records(self,
                          field_num,
                          in_rows=False):
        """ Gets dict object of unique field records, dict has a
            list of row_nums where each unique record value appears """
        distinct_records = False
        field_cells = self.get_field_row_records(field_num,
                                                 in_rows)
        if len(field_cells) > 0:
            distinct_records = {}
            for cell in field_cells:
                # iterate through cells to get list of row_nums for each distinct value
                if cell.rec_hash not in distinct_records:
                    distinct_records[cell.rec_hash] = {}
                    distinct_records[cell.rec_hash]['rows'] = []
                    distinct_records[cell.rec_hash]['imp_cell_obj'] = cell
                distinct_records[cell.rec_hash]['rows'].append(cell.row_num)
        return distinct_records

    def get_field_records_by_fl_uuid(self,
                                     field_num,
                                     in_rows=False):
        """ gets a dict object of unique field records, as
           determined by the fl_uuid. This is useful
           for subjects entities that have been reconciled in
           hierarchy relationships
        """
        distinct_records = False
        field_cells = self.get_field_row_records(field_num,
                                                 in_rows)
        if len(field_cells) > 0:
            distinct_records = {}
            for cell in field_cells:
                # iterate through cells to get list of row_nums for each distinct value
                if cell.fl_uuid not in distinct_records:
                    distinct_records[cell.fl_uuid] = {}
                    distinct_records[cell.fl_uuid]['rows'] = []
                    distinct_records[cell.fl_uuid]['imp_cell_obj'] = cell
                distinct_records[cell.fl_uuid]['rows'].append(cell.row_num)
        return distinct_records

    def get_field_row_records(self,
                              field_num,
                              in_rows=False):
        """ Gets a list of import cells """
        field_cells = []
        if in_rows is False:
            field_cells = ImportCell.objects\
                                    .filter(source_id=self.source_id,
                                            field_num=field_num,
                                            row_num__gte=self.start_row,
                                            row_num__lt=self.end_row)
        else:
            field_cells = ImportCell.objects\
                                    .order_by()\
                                    .filter(source_id=self.source_id,
                                            field_num=field_num,
                                            row_num__in=in_rows)
        return field_cells
