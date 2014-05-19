from django.db import models


# Predicate stores a predicate (decriptive property or linking relation)
# that is contributed by open context data contributors
class Predicate(models.Model):
    uuid = models.CharField(max_length=50, primary_key=True)
    project_uuid = models.CharField(max_length=50, db_index=True)
    source_id = models.CharField(max_length=50, db_index=True)
    archaeoml_type = models.CharField(max_length=50)
    data_type = models.CharField(max_length=50)
    sort = models.DecimalField(max_digits=8, decimal_places=3)
    label = models.CharField(max_length=200)
    created = models.DateTimeField()
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'oc_predicates'
        ordering = ['sort']
