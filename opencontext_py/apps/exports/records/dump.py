import csv
import os
from django.conf import settings
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.apps.exports.fields.models import ExpField
from opencontext_py.apps.exports.records.models import ExpCell
from opencontext_py.apps.exports.records.uuidlist import UUIDsRowsExportTable, ExportTableDump


class CSVdump():
    """ Methods for dumping a csv data to a file """

    def __init__(self):
        self.table_id = False
        self.filename = False
        self.field_name_row = []
        self.field_count = 0
        self.max_row_number = 0
        self.DEFAULT_DIRECTORY = 'exports'

    def dump(self, table_id, filename, excel=False):
        """ Dumps an export table to a CSV output file """
        self.table_id = table_id
        self.filename = os.path.join(settings.STATIC_ROOT,
                                     self.DEFAULT_DIRECTORY,
                                     filename)
        self.get_table_fields()
        self.get_max_row_number()
        output = False
        if self.field_count < 2:
            raise Exception('Crap! incomplete record of fields!')
        else:
            written_rows = 0
            f = open(self.filename, 'w', newline='', encoding='utf-8')
            writer = csv.writer(f)
            writer.writerow(self.field_name_row)  # write the field labels in first row
            cells = ExportTableDump(self.table_id).cells
            last_row_num = 1
            act_row_dict = LastUpdatedOrderedDict()
            for cell in cells:
                if cell['row_num'] > last_row_num:
                    # we've advanced to the next row, time to write the
                    # active row to the csv file
                    ok = self.compose_write_row(writer, act_row_dict)
                    if ok:
                        written_rows += 1
                    act_row_dict = None
                    act_row_dict = LastUpdatedOrderedDict()
                    last_row_num = cell['row_num']
                act_row_dict[cell['field_num']] = cell['record']
            # now right the last row
            ok = self.compose_write_row(writer, act_row_dict)
            f.closed
            if ok:
                written_rows += 1
            if written_rows == self.max_row_number:
                output = True
        return output

    def compose_write_row(self, writer, act_row_dict):
        """ Takes the row_dict, fills in blank cells,
            and writes to the CSV file
        """
        field_index = 1
        row = []
        while field_index <= self.field_count:
            if field_index in act_row_dict:
                row.append(act_row_dict[field_index])
            else:
                row.append('')  # no value for this cell, add blank record
            field_index += 1
        if len(row) == self.field_count:
            writer.writerow(row)  # write row
            output = True
        else:
            output = False
            raise Exception('Row has cell count of: '\
                            + str(len(row))\
                            + ' expecting: '\
                            + str(self.field_count))
        return output

    def get_max_row_number(self):
        """ Gets the maximum row numbre for the table
        """
        self.max_row_number = ExpCell.objects\
                                     .values_list('row_num', flat=True)\
                                     .order_by('-row_num')\
                                     .filter(table_id=self.table_id)[0]
        return self.max_row_number

    def get_table_fields(self):
        """ Gets a list of the table field names """
        self.field_name_row = []
        exfields = ExpField.objects\
                           .filter(table_id=self.table_id)\
                           .order_by('field_num')
        check_num = 1
        for exfield in exfields:
            self.field_count = exfield.field_num
            self.field_name_row.append(exfield.label)
            if exfield.field_num != check_num:
                raise Exception('Expected field_num'\
                                + str(check_num)\
                                + ' but got: '\
                                + str(exfield.field_num))
            check_num += 1
