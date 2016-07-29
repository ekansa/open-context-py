import reversion
from datetime import datetime
from django.utils import timezone
from django.db import models


# Stores information about fields for a data entry form
@reversion.register
class InputField(models.Model):

    # required fields for creating items in open context
    PREDICATES_OC = {
        'subjects': [
            'oc-gen:label',
            'oc-gen:class_uri',
            'oc-gen:contained-in'
        ],
        'media': [
            'oc-gen:label',
            'oc-gen:subjects-link'
        ],
        'documents': [
            'oc-gen:label',
            'oc-gen:subjects-link',
            'oc-gen:content'
        ],
        'persons': [
            'oc-gen:label']
    }

    PREDICATE_ITEMS = {
        'oc-gen:label': {
            'label': 'Item Label',
            'data_type': 'xsd:string',
            'note': 'Main identifying label for an item.',
            'validation': {}},
        'oc-gen:class_uri': {
            'label': 'Item Category',
            'data_type': 'id',
            'note': 'General type/classification',
            'validation': {
                'search': {
                    'search_type': 'hierarchy',
                    'ent_type': 'uri'
                }
            }
        },
        'oc-gen:content': {
            'label': 'Text Content',
            'data_type': 'xsd:string',
            'note': 'Body of text representing the content of the item (HTML is ok).',
            'validation': {}},
        'oc-gen:contained-in': {
            'label': 'Contained within',
            'data_type': 'id',
            'note': 'Context of where the item was discovered.',
            'validation': {
                'search': {
                    'search_type': 'look-up',
                    'ent_type': 'subjects'
                }
            }
        },
        'oc-gen:subjects-link': {
            'label': 'Linked Subject',
            'data_type': 'id',
            'note': 'Linked / associated subject (location or object).',
            'validation': {
                'search': {
                    'search_type': 'look-up',
                    'ent_type': 'subjects'
                }
            }
        }
    }

    uuid = models.CharField(max_length=50, primary_key=True)  # uuid for the InputField itself
    project_uuid = models.CharField(max_length=50, db_index=True)
    profile_uuid = models.CharField(max_length=50, db_index=True)  # uuid for the input profile
    fgroup_uuid = models.CharField(max_length=50, db_index=True)  # uuid for the input field_group
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
                    'sort',
                    'label']
