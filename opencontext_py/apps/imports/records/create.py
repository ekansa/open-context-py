import uuid as GenUUID
import datetime
from django.db import models
from opencontext_py.apps.imports.fields.models import ImportField
from opencontext_py.apps.imports.records.models import ImportCell


# Imports records, doing the appropriate lookups for uuids
class ImportRecords():

    def __init__(self):
        self.source_id = False
        self.project_uuid = False

    def get_make_literal_uuid(self, record):
        """ Gets a uuid for a literal in an import table,
            where a literal has a unique uuid with a project's import records
        """
        l_uuid = self.get_literal_uuid(recod)
        if l_uuid is False:
            l_uuid = GenUUID.uuid4()
        return l_uuid

    def get_make_field_literal_uuid(self, field_num, record):
        """ Gets or makes a uuid for unique to the field and a project
        """
        fl_uuid = self.get_field_literal_uuid(field_num, record)
        if fl_uuid is False:
            fl_uuid = GenUUID.uuid4()
        return fl_uuid

    def get_field_literal_uuid(self, field_num, record):
        """ Gets a uuid for a literal of the same in a given field
            in a project
        """
        output = False
        rel_fields = self.get_related_fields(field_num)
        if len(rel_fields) > 0:
            filters = ''
            for rel_field in rel_fields:
                act_filter = '(imp_cell.source_id = \'' + rel_field.source_id + '\' '
                act_filter += 'AND imp_cell.field_num = \'' + rel_field.field_num + '\')'
                if filters == '':
                    filters = act_filter
                else:
                    filters += ' OR ' + act_filter
            check = ImportCell.objects\
                              .filter(project_uuid=self.project_uuid,
                                      record=record)\
                              .extra(where=[filters])[:1]
            if len(check) > 0:
                output = check[0].fl_uuid
        return output

    def get_field_uuid(self, field_num):
        """ Gets the f_uuid (field_uuid) associated with a field_num """
        output = False
        field_look = ImportField.objects\
                                .filter(source_id=self.source_id,
                                        field_num=field_num)[:1]
        if len(field_look) > 0:
            output = field_look[0].f_uuid
        return output

    def get_related_fields(self, field_num):
        """ Gets imp_field objects for fields that share the
            same f_uuid
        """
        field_uuid = self.get_field_uuid(field_num)
        rel_fields = ImportField.objects\
                                .filter(f_uuid=field_uuid)
        return rel_fields

    def get_literal_uuid(self, record):
        """ Gets a uuid for a literal in a project's import records """
        output = False
        check = ImportCell.objects\
                          .filter(project_uuid=self.project_uuid,
                                  record=record)[:1]
        if len(check) > 0:
            output = check[0].l_uuid
        return output
