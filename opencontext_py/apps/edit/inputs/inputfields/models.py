from datetime import datetime
from django.utils import timezone
from django.db import models


# Stores information about fields for a data entry form
class InputField(models.Model):

    # required fields for creating items in open context
    PREDICATES_OC = {'subjects': ['oc-gen:label',
                                  'oc-gen:class_uri',
                                  'oc-gen:contained-in'],
                     'media': ['oc-gen:label'],
                     'documents': ['oc-gen:label'],
                     'persons': ['oc-gen:label']}

    PREDICATE_ITEMS = {'oc-gen:label': {'label': 'Item Label',
                                        'data_type': 'xsd:string',
                                        'note': 'Main identifying label for an item.',
                                        'validation': {}},
                       'oc-gen:class_uri': {'label': 'Item Category',
                                            'data_type': 'id',
                                            'note': 'General type/classification',
                                            'validation': {'values': ['*'],
                                                           'search': {
                                                           'url': '/entities/hierarchy-children/oc-gen%3Asubjects'
                                                                      }}
                                            },
                       'oc-gen:contained-in': {'label': 'Contained within',
                                               'data_type': 'id',
                                               'note': 'Context of where the item was discovered.',
                                               'validation': {'values': ['*'],
                                                              'search': {
                                                              'url': '/entities/look-up/subjects'}
                                                                }}}

    uuid = models.CharField(max_length=50, primary_key=True)  # uuid for the InputField itself
    project_uuid = models.CharField(max_length=50, db_index=True)
    profile_uuid = models.CharField(max_length=50, db_index=True)  # uuid for the input profile
    fgroup_uuid = models.CharField(max_length=50, db_index=True)  # uuid for the input field_group
    row_num = models.IntegerField()  # row column number for placing field
    col_num = models.IntegerField()  # column number for placing the field
    sort = models.IntegerField()  # sort value a field in a given cell
    predicate_uuid = models.CharField(max_length=50, db_index=True)  # the predicate UUID associated with this field
    label = models.CharField(max_length=200)  # label for data entry form
    note = models.TextField()  # note for instructions in data entry
    validation = models.TextField()  # JSON with settings to facilitate data entry
    created = models.DateTimeField()
    updated = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        """
        saves a manifest item with a good slug
        """
        if self.created is None:
            self.created = datetime.now()
        super(InputField, self).save(*args, **kwargs)

    class Meta:
        db_table = 'crt_fields'
        ordering = ['profile_uuid',
                    'fgroup_uuid',
                    'row_num',
                    'col_num',
                    'sort',
                    'label']
