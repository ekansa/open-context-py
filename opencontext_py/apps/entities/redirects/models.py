import re
import reversion  # version control object
from django.db import models
from unidecode import unidecode
from django.template.defaultfilters import slugify


# This class stores linked data annotations made on the data contributed to open context
@reversion.register  # records in this model under version control
class RedirectMapping(models.Model):

    DEFAULT_HTTP_CODE = 301  # default to a permanent redirect

    url = models.CharField(max_length=400, primary_key=True)
    redirect = models.CharField(max_length=400, db_index=True)
    http_code = models.IntegerField()
    note = models.TextField(blank=True)
    updated = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        """
        creates the hash-id on saving to insure a unique assertion
        """
        if self.http_code is None:
            self.http_code = self.DEFAULT_HTTP_CODE
        if self.url == self.redirect:
            # problem!
            raise CircularRedirect
        super(RedirectMapping, self).save(*args, **kwargs)

    class Meta:
        db_table = 'oc_redirects'
