import reversion  # version control object
import hashlib
import collections
from jsonfield import JSONField  # json field for complex objects
from django.db import models
from opencontext_py.apps.ldata.linkentities.models import LinkEntityGeneration


# This class stores linked data annotations made on the data contributed to open context
@reversion.register  # records in this model under version control
class LinkAnnotation(models.Model):
    # predicates indicating that a subject has an object that is a broader, more general class or property
    # used for establising hierarchy relations among oc-predicates and oc-types
    # these relations are needed for look ups in the faceted search
    PREDS_SBJ_IS_SUB_OF_OBJ = ['skos:broader',
                               'skos:broaderTransitive',
                               'skos:broadMatch',
                               'rdfs:subClassOf',
                               'rdfs:subPropertyOf']

    # predicates indicating that a subject has an object that is narrower (a subclass)
    PREDS_SBJ_IS_SUPER_OF_OBJ = ['skos:narrower',
                                 'skos:narrowerTransitive',
                                 'skos:narrowMatch']

    # predicates indicting that a subject is the same or very similar to an object
    PREDS_SBJ_EQUIV_OBJ = ['owl:sameAs',
                           'skos:closeMatch',
                           'skos:exactMatch']

    hash_id = models.CharField(max_length=50, primary_key=True)
    sort = models.DecimalField(max_digits=8, decimal_places=3)
    subject = models.CharField(max_length=200, db_index=True)
    subject_type = models.CharField(max_length=50)
    project_uuid = models.CharField(max_length=50)
    source_id = models.CharField(max_length=200)  # longer than the normal 50 for URI-identifed vocabs
    predicate_uri = models.CharField(max_length=200, db_index=True)
    object_uri = models.CharField(max_length=200, db_index=True)
    obj_extra = JSONField(default={},
                          load_kwargs={'object_pairs_hook': collections.OrderedDict},
                          blank=True)
    creator_uuid = models.CharField(max_length=50)
    updated = models.DateTimeField(auto_now=True)

    def make_hash_id(self):
        """
        creates a hash-id to insure unique combinations of project_uuids and contexts
        """
        hash_obj = hashlib.sha1()
        concat_string = str(self.subject) + " " + str(self.predicate_uri) + " " + str(self.object_uri)
        hash_obj.update(concat_string.encode('utf-8'))
        return hash_obj.hexdigest()

    def clean_uris(self):
        """
        cleans URIs to keep them consistent and empty of 'cruft'
        """
        le_gen = LinkEntityGeneration()
        self.subject = le_gen.make_clean_uri(self.subject)
        self.predicate_uri = le_gen.make_clean_uri(self.predicate_uri)
        self.object_uri = le_gen.make_clean_uri(self.object_uri)

    def save(self, *args, **kwargs):
        """
        creates the hash-id on saving to insure a unique assertion
        """
        self.clean_uris()
        self.hash_id = self.make_hash_id()
        super(LinkAnnotation, self).save(*args, **kwargs)

    class Meta:
        db_table = 'link_annotations'
        unique_together = ('subject', 'predicate_uri', 'object_uri')
        ordering = ['subject', 'sort']
