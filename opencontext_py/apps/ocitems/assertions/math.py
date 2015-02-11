from django.db import models
from django.db.models import Max, Min, Count, Avg
from opencontext_py.apps.ocitems.assertions.models import Assertion
from opencontext_py.apps.ldata.linkannotations.equivalence import LinkEquivalence
from opencontext_py.apps.entities.uri.models import URImanagement


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

    def get_numeric_range(self, predicate_uuids):
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
        return output
