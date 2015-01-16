from django.conf import settings
from django.db import models
from django.db.models import Q
from opencontext_py.apps.entities.uri.models import URImanagement
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.ocitems.assertions.models import Assertion
from opencontext_py.apps.ldata.linkannotations.models import LinkAnnotation
from opencontext_py.apps.ocitems.predicates.models import Predicate
from opencontext_py.apps.ocitems.octypes.models import OCtype


# This class is used to delete or merge entities
class PredicateMerge():

    def __init__(self):
        self.project_uuid = False

    def merge_identical_predicates(self, project_uuid):
        """ Merges identical predicates in a project """
        pass

    def get_identical_predicates(self, project_uuid):
        """ Merges identical predicates in a project """
        self.project_uuid = project_uuid
        checked_uuids = []
        matched_predicates = {}
        pred_mans = Manifest.objects\
                            .filter(item_type='predicates',
                                    project_uuid=project_uuid)
        for pred_man in pred_mans:
            if pred_man.uuid not in checked_uuids:
                checked_uuids.append(pred_man.uuid)
                matched_predicates[pred_man.uuid] = {'same': []}
                pred_obj = self.get_predicate(pred_man.uuid)
                if pred_obj is not False:
                    identical_pmans = Manifest.objects\
                                              .filter(item_type='predicates',
                                                      project_uuid=project_uuid,
                                                      label=pred_man.label,
                                                      class_uri=pred_man.class_uri)\
                                              .exclude(uuid=pred_man.uuid)
                    for ident_man in identical_pmans:
                        ident_pred_obj = self.get_predicate(ident_man.uuid)
                        if ident_pred_obj is not False:
                            if ident_pred_obj.uuid != pred_obj.uuid and\
                               ident_pred_obj.data_type == pred_obj.data_type:
                                matched_predicates[pred_man.uuid]['same'].append(ident_pred_obj.uuid)
                                checked_uuids.append(ident_pred_obj.uuid)
        return matched_predicates

    def get_predicate(self, uuid):
        """ gets a predicate object or False """
        pred_obj = False
        try:
            pred_obj = Predicate.objects.get(uuid=uuid)
        except Predicate.DoesNotExist:
            print('No predicate record for: ' + uuid)
            pred_obj = False
        return pred_obj

    def get_manifest(self, act_identifier, try_slug=False):
        """
        gets basic metadata about the item from the Manifest app
        """
        man_obj = False
        if(try_slug):
            try:
                man_obj = Manifest.objects.get(Q(uuid=act_identifier) | Q(slug=act_identifier))
            except Manifest.DoesNotExist:
                man_obj = False
        else:
            try:
                man_obj = Manifest.objects.get(uuid=act_identifier)
            except Manifest.DoesNotExist:
                man_obj = False
        return man_obj
