import uuid as GenUUID
import datetime
from django.db import models
from opencontext_py.apps.ocitems.manifest.models import Manifest


# Predicate stores a predicate (decriptive property or linking relation)
# that is contributed by open context data contributors
class Predicate(models.Model):
    uuid = models.CharField(max_length=50, primary_key=True)
    project_uuid = models.CharField(max_length=50, db_index=True)
    source_id = models.CharField(max_length=50, db_index=True)
    data_type = models.CharField(max_length=50)
    sort = models.DecimalField(max_digits=8, decimal_places=3)
    created = models.DateTimeField()
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'oc_predicates'
        ordering = ['sort']


class PredicateManage():
    """ Class for helping to create and edit data about predicates
    """

    def __init__(self):
        self.predicate = False
        self.manifest = False
        self.project_uuid = False
        self.source_id = False
        self.data_type = "xsd:string"
        self.sort = 0

    def get_make_predicate(self, predicate_label, predicate_type):
        """
        gets a predicate, filtered by label, predicate_type, and data_type
        """
        try:
            self.manifest = Manifest.objects.get(label=predicate_label,
                                                 item_type='predicates',
                                                 project_uuid=self.project_uuid,
                                                 class_uri=predicate_type)
        except Manifest.DoesNotExist:
            self.manifest = False
        if(self.manifest is not False):
            try:
                self.predicate = Predicate.objects.get(uuid=self.manifest.uuid)
            except Predicate.DoesNotExist:
                self.predicate = False
        if(self.manifest is False):
            uuid = GenUUID.uuid1()
            newpred = Predicate()
            newpred.uuid = uuid
            newpred.project_uuid = self.project_uuid
            newpred.source_id = self.source_id
            newpred.data_type = self.data_type
            newpred.sort = self.sort
            newpred.created = datetime.datetime.now()
            newpred.save()
            self.predicate = newpred
            #now make a manifest record for the item
            newman = Manifest()
            newman.uuid = uuid
            newman.project_uuid = self.project_uuid
            newman.source_id = self.source_id
            newman.item_type = 'predicates'
            newman.repo = ''
            newman.class_uri = predicate_type
            newman.label = predicate_label
            newman.des_predicate_uuid = ''
            newman.views = 0
            newman.revised = datetime.datetime.now()
            newman.save()
        return self.predicate
