from django.db import models


# Chronology provides (eventually)topo-time modeling of time range information for an item
class Chronology(models.Model):
    uuid = models.CharField(max_length=50, primary_key=True)
    project_uuid = models.CharField(max_length=50, db_index=True)
    # lc means "least confidence", c means "confidence"
    start_lc = models.DecimalField(max_digits=19, decimal_places=5)
    start_c = models.DecimalField(max_digits=19, decimal_places=5)
    end_c = models.DecimalField(max_digits=19, decimal_places=5)
    end_lc = models.DecimalField(max_digits=19, decimal_places=5)
    updated = models.DateTimeField(auto_now=True)
    note = models.TextField()

    class Meta:
        db_table = 'oc_chronology'
