from django.db import models
from opencontext_py.apps.ldata.linkannotations.models import LinkAnnotation, LinkRecursion
from opencontext_py.apps.entities.uri.models import URImanagement


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


class MigrateHierarchy():
    def migrate(self):
        lh_list = LinkHierarchy.objects.all()
        for lh in lh_list:
            new_la = LinkAnnotation()
            new_la.subject = lh.child_uri
            new_la.subject_type = 'uri'
            new_la.project_uuid = '0'
            new_la.source_id = 'LinkHierarchy'
            new_la.predicate_uri = 'skos:broader'
            new_la.object_uri = lh.parent_uri
            new_la.creator_uuid = ''
            new_la.save()
