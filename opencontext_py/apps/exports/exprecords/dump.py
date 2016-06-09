import csv
import os
import codecs
from django.conf import settings
from django.http import HttpResponse
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.apps.exports.expfields.models import ExpField
from opencontext_py.apps.exports.exprecords.models import ExpCell
from opencontext_py.apps.exports.exprecords.uuidlist import UUIDsRowsExportTable, ExportTableDump


class CSVdump():
    """ Methods for dumping a csv data to a file

from opencontext_py.apps.exports.exprecords.dump import CSVdump
dump = CSVdump()
dump.dump('b5f81371-35db-4644-b353-3f5648eeb222', 'b5f81371-35db-4644-b353-3f5648eeb222.csv')

from opencontext_py.apps.exports.exprecords.dump import CSVdump
dump = CSVdump()
dump.dump('ea16a444-9876-4fe7-8ffb-389b54a7e3a0', 'ea16a444-9876-4fe7-8ffb-389b54a7e3a0.csv')    

    """

    def __init__(self):
        self.root_export_dir = settings.STATIC_EXPORTS_ROOT
        self.table_export_dir = False  # directory to export files into
        self.table_id = False
        self.dir_filename = False
        self.field_name_row = []
        self.field_count = 0
        self.max_row_number = 0
        self.DEFAULT_DIRECTORY = 'exports'

    def dump(self, table_id, filename, excel=False):
        """ Dumps an export table to a CSV output file """
        self.table_id = table_id
        directory = self.prep_directory()
        self.dir_filename = os.path.join(directory,
                                         filename)
        self.get_table_fields()
        self.get_max_row_number()
        output = False
        if self.field_count < 2:
            raise Exception('Crap! incomplete record of fields!')
        else:
            written_rows = 0
            # f = open(self.dir_filename, 'w', newline='', encoding='utf-8')
            f = codecs.open(self.dir_filename, 'w', encoding='utf-8')
            writer = csv.writer(f, dialect=csv.excel, quoting=csv.QUOTE_ALL)
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

    def web_dump(self, table_id):
        """ writes a csv file for a Web dump instead of a file save """
        self.table_id = table_id
        self.get_table_fields()
        self.get_max_row_number()
        filename = 'oc-table-' + table_id + '.csv'
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="'+ filename + '"'
        writer = csv.writer(response, dialect='excel', quoting=csv.QUOTE_ALL)
        writer.writerow(self.field_name_row)  # write the field labels in first row
        cells = ExportTableDump(self.table_id).cells
        written_rows = 0
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
        return response

    def compose_write_row(self, writer, act_row_dict):
        """ Takes the row_dict, fills in blank cells,
            and writes to the CSV file
        """
        field_index = 1
        row = []
        while field_index <= self.field_count:
            if field_index in act_row_dict:
                # escaped_cell = '"' + act_row_dict[field_index] + '"'
                escaped_cell = act_row_dict[field_index]
                row.append(escaped_cell)
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

    def prep_directory(self):
        """ Prepares a directory to receive export files """
        output = False
        if self.table_export_dir is not False:
            full_dir = self.root_export_dir + '/' + self.table_export_dir
            full_dir.replace('//', '/')
            if not os.path.exists(full_dir):
                os.makedirs(full_dir)
        else:
            full_dir = self.root_export_dir
        output = full_dir
        if output[-1] != '/':
            output += '/'
        print('Prepared directory: ' + str(output))
        return output
