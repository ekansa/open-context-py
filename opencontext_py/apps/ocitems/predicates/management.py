import uuid as GenUUID
import datetime
from django.db import models
from django.db.models import Q
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.ocitems.predicates.models import Predicate
from opencontext_py.apps.ocitems.octypes.management import TypeManagement


class PredicateManagement():
    """ Class for helping to create and edit data about predicates
    """

    def __init__(self):
        self.predicate = False
        self.manifest = False
        self.project_uuid = False
        self.source_id = False
        self.data_type = "xsd:string"
        self.sort = 0

    def get_make_predicate(self, predicate_label, predicate_type, data_type=False):
        """
        gets a predicate, filtered by label, predicate_type, and data_type
        """
        self.manifest = False
        self.predicate = False
        if(data_type is not False):
            self.data_type = data_type
        plist = Manifest.objects.filter(label=predicate_label,
                                        item_type='predicates',
                                        project_uuid=self.project_uuid,
                                        class_uri=predicate_type)
        for pitem in plist:
            if(self.manifest is False):
                if(data_type is not False):
                    try:  # try to find the predicate with a given data_type
                        self.predicate = Predicate.objects.get(uuid=pitem.uuid,
                                                               data_type=data_type)
                        self.manifest = pitem
                    except Predicate.DoesNotExist:
                        self.predicate = False
                        self.manifest = False
                else:
                    try:  # look for the predicate item
                        self.predicate = Predicate.objects.get(uuid=pitem.uuid)
                        self.manifest = pitem
                    except Predicate.DoesNotExist:
                        self.predicate = False
                        self.manifest = False
        if(self.manifest is False and self.predicate is False):
            uuid = GenUUID.uuid4()
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
            self.manifest = newman
        return self.predicate
