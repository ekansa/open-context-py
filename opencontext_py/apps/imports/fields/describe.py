from django.db import models
from opencontext_py.apps.imports.fields.models import ImportField


# Methods to describe import fields
class ImportFieldDescribe():

    def __init__(self, source_id):
        self.source_id = source_id
        self.field_num_list = []

    def update_field_type(self, field_type, field_num):
        """ Updates field_types for a comma-seperated list of field_nums """
        self.get_field_num_list(field_num)
        ImportField.objects\
                   .filter(field_num__in=self.field_num_list)\
                   .update(field_type=field_type)

    def update_field_data_type(self, field_data_type, field_num):
        """ Updates field_data_type for a comma-seperated list of field_nums """
        self.get_field_num_list(field_num)
        ImportField.objects\
                   .filter(field_num__in=self.field_num_list)\
                   .update(field_data_type=field_data_type)

    def update_field_label(self, label, field_num):
        """ Updates field_data_type for a comma-seperated list of field_nums """
        self.get_field_num_list(field_num)
        label = label.strip()
        ImportField.objects\
                   .filter(field_num__in=self.field_num_list)\
                   .update(label=label)

    def update_field_value_prefix(self, value_prefix, field_num):
        """ Updates field_prefix for a comma-seperated list of field_nums """
        self.get_field_num_list(field_num)
        value_prefix = value_prefix.lstrip()
        ImportField.objects\
                   .filter(field_num__in=self.field_num_list)\
                   .update(value_prefix=value_prefix)

    def update_field_value_cat(self, field_value_cat, field_num):
        """ Updates the field value category,
            which is a more fine-grain classification
            for entities to import
            for a comma-seperated list of field_nums """
        self.get_field_num_list(field_num)
        ImportField.objects\
                   .filter(field_num__in=self.field_num_list)\
                   .update(field_value_cat=field_value_cat)

    def get_field_num_list(self, field_num):
        """ Makes a list of field nums, splitting on commas as needed"""
        if ',' in field_num:
            self.field_num_list = field_num.split(',')
        else:
            self.field_num_list = [field_num]
        return self.field_num_list

