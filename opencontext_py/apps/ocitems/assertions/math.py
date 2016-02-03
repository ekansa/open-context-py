from django.db import models
from django.db.models import Max, Min, Count, Avg
from opencontext_py.apps.entities.uri.models import URImanagement
from opencontext_py.apps.ocitems.assertions.models import Assertion
from opencontext_py.apps.ldata.linkannotations.equivalence import LinkEquivalence
from opencontext_py.apps.ldata.linkannotations.recursion import LinkRecursion


class MathAssertions():
    """
    This class has useful methods for math on assertion data
    """

    def __init__(self):
        self.predicate_uuids = []

    def get_numeric_range_via_ldata(self, object_uri):
        """ gets predicates linked to an object_uri """
        lequiv = LinkEquivalence()
        predicate_uuids = lequiv.get_from_object(object_uri)
        return self.get_numeric_range(predicate_uuids)

    def get_date_range_via_ldata(self, object_uri):
        """ gets predicates linked to an object_uri """
        lequiv = LinkEquivalence()
        predicate_uuids = lequiv.get_from_object(object_uri)
        return self.get_date_range(predicate_uuids)

    def get_numeric_range(self, predicate_uuids, children_ok=True):
        if not isinstance(predicate_uuids, list):
            predicate_uuids = [str(predicate_uuids)]
        sum_ass = Assertion.objects\
                           .filter(predicate_uuid__in=predicate_uuids)\
                           .aggregate(Min('data_num'),
                                      Max('data_num'),
                                      Count('hash_id'),
                                      Avg('data_num'))
        output = {}
        output['avg'] = sum_ass['data_num__avg']
        output['min'] = sum_ass['data_num__min']
        output['max'] = sum_ass['data_num__max']
        output['count'] = sum_ass['hash_id__count']
        if output['count'] == 0 and children_ok:
            output = self.get_numeric_range_from_children(predicate_uuids)
        return output

    def get_numeric_range_from_children(self, predicate_uuids):
        """ gets numeric range from a list of predicates
            OR their children
        """
        if not isinstance(predicate_uuids, list):
            predicate_uuids = [str(predicate_uuids)]
        all_preds = []
        for predicate_uuid in predicate_uuids:
            all_preds.append(predicate_uuid)
            lr = LinkRecursion()
            children = lr.get_entity_children(predicate_uuid)
            for child_uuid_key in children:
                if child_uuid_key not in all_preds:
                    all_preds.append(child_uuid_key)
        # now get the summary, but don't allow recursive looking at children
        output = self.get_numeric_range(all_preds, False)
        return output

    def get_date_range(self, predicate_uuids):
        if not isinstance(predicate_uuids, list):
            predicate_uuids = [str(predicate_uuids)]
        sum_ass = Assertion.objects\
                           .filter(predicate_uuid__in=predicate_uuids)\
                           .aggregate(Min('data_date'),
                                      Max('data_date'),
                                      Count('hash_id'))
        output = {}
        output['min'] = sum_ass['data_date__min']
        output['max'] = sum_ass['data_date__max']
        output['count'] = sum_ass['hash_id__count']
        return output

