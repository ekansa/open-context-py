from django.conf import settings
from django.db import models
from opencontext_py.apps.imports.fields.models import ImportField
from opencontext_py.apps.imports.fieldannotations.models import ImportFieldAnnotation
from opencontext_py.apps.imports.records.models import ImportCell


# General methods for processing the import
class ProcessGeneral():

    def __init__(self, source_id):
        self.source_id = source_id
        self.project_uuid = False
        self.fields = False

    def get_source(self):
        """ gets the project_uuid from the source_id
        """
        output = False
        fields = ImportField.objects\
                            .filter(source_id=self.source_id)
        if len(fields) > 0:
            self.project_uuid = fields[0].project_uuid
            self.fields = fields
            output = True
        return output

    def check_blank_required(self,
                             field_num,
                             row_num):
        """ Checks to see if a given record
            needs to be used even if blank,
            because it has other data that references
            that blank record.
        """
        output = False
        check_fields = []
        anno_subjs = ImportFieldAnnotation.objects\
                                          .filter(source_id=self.source_id,
                                                  field_num=field_num,
                                                  object_field_num__gt=0)
        anno_objs = ImportFieldAnnotation.objects\
                                         .filter(source_id=self.source_id,
                                                 object_field_num=field_num,
                                                 field_num__gt=0)
        if len(anno_subjs) > 0:
            for anno_subj in anno_subjs:
                if anno_subj.object_field_num not in check_fields:
                    check_fields.append(anno_subj.object_field_num)
        if len(anno_objs) > 0:
            for anno_obj in anno_objs:
                if anno_obj.field_num not in check_fields:
                    check_fields.append(anno_obj.field_num)
        if len(check_fields) > 0:
            rel_cells = ImportCell.objects\
                                  .filter(source_id=self.source_id,
                                          field_num__in=check_fields,
                                          row_num__in=row_num)
            if len(rel_cells) > 0:
                for rel_cell in rel_cells:
                    if len(rel_cell.record) > 0:
                        # we found a related cell that has a non-blank
                        # value, so the output is true, this record
                        # does require creation / use of a blank entity
                        output = True
                        break
        return output
