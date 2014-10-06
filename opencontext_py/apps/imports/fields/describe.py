from django.db import models
from opencontext_py.apps.imports.fields.models import ImportField


# Methods to describe import fields
class ImportFieldDescribe():

    def __init__(self, source_id):
        self.source_id = source_id
        self.field_num_list = []

    def updated_field_type(self, field_type, field_num):
        """ Updates field_types for a comma-seperated list of field_nums """
        if ',' in field_num:
            self.field_num_list = field_num.split(',')
        else:
            self.field_num_list = [field_num]
        ImportField.objects\
                   .filter(field_num__in=self.field_num_list)\
                   .update(field_type=field_type)

