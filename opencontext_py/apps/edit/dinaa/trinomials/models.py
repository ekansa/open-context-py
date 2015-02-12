import hashlib
from django.db import models
from django.conf import settings
from datetime import datetime
from django.utils import timezone


# A model for Smithsonian Trinomials specific to the DINAA project
# This model is used strictly for DINAA data processing, and is
# not meant to be a permananent part of the Open Context project
class Trinomial(models.Model):

    uri = models.CharField(max_length=200, db_index=True)
    uuid = models.CharField(max_length=50, primary_key=True)
    label = models.CharField(max_length=200, db_index=True, null=True)
    project_label = models.CharField(max_length=200)
    trinomial = models.CharField(max_length=50, db_index=True, null=True)
    state = models.CharField(max_length=4, null=True)
    county = models.CharField(max_length=4, null=True)
    site = models.CharField(max_length=10, null=True)
    tdar_checked = models.DateTimeField(blank=True, null=True)

    def tdar_checked_save(self):
        """
        Updates with the last indexed time
        """
        self.tdar_checked = timezone.now()
        super(Trinomial, self).save(update_fields=['tdar_checked'])

    class Meta:
        db_table = 'dinaa_trinomials'
