import time
import collections
import hashlib
from datetime import datetime
from django.conf import settings
from django.utils import timezone
from django.db import models
from jsonfield import JSONField

class HttpMetric(models.Model):
    """ stores information about clients using Open Context
        limits precision of geospatial data so as to reduce
        privacy risks. Stores no IP addresses!
    """

    client_id = models.CharField(max_length=50, db_index=True)
    referer = models.CharField(max_length=255, db_index=True)
    path = models.CharField(max_length=255, db_index=True)
    mime_type = type = models.CharField(max_length=100)
    uuid = models.CharField(max_length=50, db_index=True)
    project_uuid = models.CharField(max_length=50, db_index=True)
    item_type = models.CharField(max_length=50)
    params_json = JSONField(default={},
                            load_kwargs={'object_pairs_hook': collections.OrderedDict},
                            blank=True)
    # limit precision here so as to reduce privacy risks
    latitude = models.DecimalField(max_digits=10, decimal_places=2)
    longitude = models.DecimalField(max_digits=10, decimal_places=2)
    # some client info
    type = models.CharField(max_length=50, db_index=True) # 'pc', 'tablet', 'mobile'
    browser = models.CharField(max_length=200)
    os = models.CharField(max_length=200)
    device = models.CharField(max_length=200)
    duration = models.DecimalField(max_digits=20, decimal_places=5)
    updated = models.DateTimeField(auto_now=True)

    def make_client_id(self):
        """
        creates a client_id which is a not that unique combination
        of geo data, client data, and rough time. It's not meant to be
        hugely unique so as to limit privacy risks, but it should
        give rough guestimates about what a clients do with the site
        """
        hash_obj = hashlib.sha1()
        parts_list = [
            str(self.type),
            str(self.browser),
            str(self.os),
            str(self.device),
            str(self.latitude),
            str(self.longitude),
            time.strftime('%Y-%m-%dT%H') 
        ]
        concat_string = ' '.join(parts_list)
        hash_obj.update(concat_string.encode('utf-8'))
        return hash_obj.hexdigest()

    def save(self, *args, **kwargs):
        """
        saves with created time if None
        """
        if not isinstance(self.client_id, str):
            self.client_id = self.make_client_id()
        elif len(self.client_id) < 10:
            self.client_id = self.make_client_id()
        super(HttpMetric, self).save(*args, **kwargs)

    class Meta:
        db_table = 'link_metrics'