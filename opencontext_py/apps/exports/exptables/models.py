import collections
from datetime import datetime
from django.utils import timezone
from django.db import models
from jsonfield import JSONField


# Stores metadata about export tables
class ExpTable(models.Model):

    PREDICATE_DUMP = 'void:dataDump'

    table_id = models.CharField(max_length=50, primary_key=True)
    label = models.CharField(max_length=200, db_index=True)
    field_count = models.IntegerField()
    row_count = models.IntegerField()
    meta_json = JSONField(default={},
                          load_kwargs={'object_pairs_hook': collections.OrderedDict})
    short_des = models.CharField(max_length=200)
    abstract = models.TextField()
    created = models.DateTimeField()
    updated = models.DateTimeField(auto_now=True)
    sm_localized_json = JSONField(default={},
                                  load_kwargs={'object_pairs_hook': collections.OrderedDict},
                                  blank=True)
    lg_localized_json = JSONField(default={},
                                  load_kwargs={'object_pairs_hook': collections.OrderedDict},
                                  blank=True)

    def save(self, *args, **kwargs):
        """
        saves with created time if None
        """
        if self.created is None:
            self.created = datetime.now()
        super(ExpTable, self).save(*args, **kwargs)

    class Meta:
        db_table = 'exp_tables'
