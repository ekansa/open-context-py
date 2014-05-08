from django.db import models


# This class stores linked data hierarchies, useful for facetet search expansion
class LinkHierarchy(models.Model):
    hash_id = models.CharField(max_length=50, primary_key=True)
    parent_uri = models.CharField(max_length=200, db_index=True)
    child_uri = models.CharField(max_length=200, db_index=True)
    vocab_uri = models.CharField(max_length=200)
    tree = models.CharField(max_length=50)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'link_hierarchies'
