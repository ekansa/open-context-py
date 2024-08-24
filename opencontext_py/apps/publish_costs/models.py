import datetime
import hashlib
import uuid as GenUUID

from django.conf import settings

from unidecode import unidecode


from django.db import models

from django.db.models import JSONField
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone


class PublishEstimate(models.Model):
    '''
    Model to record publication cost estimates. Data will be visible
    only to administrative users, but no personally identifiable data will be kept here
    so this should not be considered sensitive.
    '''
    uuid = models.UUIDField(primary_key=True, editable=True)
    session_id = models.TextField()
    hash_id = models.TextField()
    estimated_cost = models.FloatField(null=True)
    input_json = JSONField(default=dict)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    meta_json = JSONField(default=dict)


    def make_hash_id(
        self,
        session_id,
        input_json=None,
    ):
        """Makes a hash_id for an assertion"""
        hash_obj = hashlib.sha1()
        concat_list = [
            str(session_id),
            str(input_json),
        ]
        concat_string = " ".join(concat_list)
        hash_obj.update(concat_string.encode('utf-8'))
        return hash_obj.hexdigest()


    def __str__(self):
        out = (
            f'{self.uuid}: cost {self.estimated_cost} [{self.session_id}] '
            f'-> {self.updated}'
        )
        return out


    def save(self, *args, **kwargs):
        """
        Saves with validation checks.
        """
        if not self.uuid:
            self.uuid = GenUUID.uuid4()
        if not self.hash_id:
            self.hash_id = self.make_hash_id(self.session_id, self.input_json)
        super(PublishEstimate, self).save(*args, **kwargs)


    class Meta:
        db_table = 'oc_publish_estimates'
        unique_together = (
            (
                "session_id",
                "hash_id",
            ),
        )
        ordering = ["updated", "session_id",]