import reversion  # version control object
from datetime import datetime
from django.utils import timezone
from django.db import models


# Predicate stores a predicate (decriptive property or linking relation)
# that is contributed by open context data contributors
@reversion.register  # records in this model under version control
class Predicate(models.Model):
    CLASS_TYPES = ['variable',
                   'link']
    DATA_TYPES_HUMAN = {'id': 'URI identified item',
                        'xsd:string': 'Alphanumeric text strings',
                        'xsd:double': 'Decimal values',
                        'xsd:integer': 'Integer values',
                        'xsd:boolean': 'Boolean (true/false) values',
                        'xsd:date': 'Calendar date or datetime values'}

    uuid = models.CharField(max_length=50, primary_key=True)
    project_uuid = models.CharField(max_length=50, db_index=True)
    source_id = models.CharField(max_length=50, db_index=True)
    data_type = models.CharField(max_length=50)
    sort = models.DecimalField(max_digits=8, decimal_places=3)
    created = models.DateTimeField()
    updated = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        """
        saves a manifest item with a good slug
        """
        if self.sort is None:
            self.sort = 0
        if self.created is None:
            self.created = timezone.now()
        super(Predicate, self).save(*args, **kwargs)

    class Meta:
        db_table = 'oc_predicates'
        ordering = ['sort']
