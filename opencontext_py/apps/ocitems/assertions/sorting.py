from django.conf import settings
from django.db import models
from opencontext_py.apps.ocitems.assertions.models import Assertion
from opencontext_py.apps.ocitems.octypes.models import OCtype
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.ocitems.predicates.models import Predicate


class AssertionSorting():
    """ Class for managing data_types for predicates, make sure consistency in data types
        used for predicates across manifest, predicate, and assertions tables
    """
    def sort_ranked_types_for_project(self, project_uuid):
        """Changes sort order for assertions with ranked types in a project """
        act_preds = self.get_preds_with_ranked_types(project_uuid)
        for predicate_uuid in act_preds:
            print('Working on predicate: ' + predicate_uuid)
            self.re_rank_assertions_by_predicate(predicate_uuid)

    def re_rank_assertions_by_predicate(self, predicate_uuid):
        type_rankings = self.get_ranked_types_for_pred(predicate_uuid)
        max_type = max(type_rankings, key=type_rankings.get)
        default_missing_rank = float(type_rankings[max_type] + 1)
        print('Predicate: ' + predicate_uuid + ' has ' + str(len(type_rankings)) + ' ranked types.')
        act_assertions = Assertion.objects\
                                  .filter(predicate_uuid=predicate_uuid)\
                                  .order_by('uuid', 'sort')
        act_uuid = False
        print('Number of assertions to change: ' + str(len(act_assertions)))
        for act_ass in act_assertions:
            if act_ass.uuid != act_uuid:
                start_sort = round(act_ass.sort, 0)
                act_uuid = act_ass.uuid
            if act_ass.object_uuid in type_rankings:
                type_rank = type_rankings[act_ass.object_uuid]
            else:
                type_rank = default_missing_rank
            act_ass.sort = float(start_sort) + (type_rank / 1000)
            act_ass.save(force_update=True)

    def get_ranked_types_for_pred(self, predicate_uuid):
        """ Gets the ranked types used with a given predicate """
        type_rankings = {}
        ranked_types = OCtype.objects\
                             .filter(rank__gt=0,
                                     predicate_uuid=predicate_uuid)\
                             .order_by('rank')
        for r_type in ranked_types:
            type_rankings[r_type.uuid] = float(r_type.rank)
        return type_rankings

    def get_preds_with_ranked_types(self, project_uuid):
        """ Uses ranked types to sort muliple values of the same
        predicate and same subject (uuid) in the Assertions table
        """
        act_preds = []
        ranked_types = OCtype.objects\
                             .filter(rank__gt=0,
                                     project_uuid=project_uuid)\
                             .order_by('rank')
        for r_type in ranked_types:
            if r_type.predicate_uuid not in act_preds:
                act_preds.append(r_type.predicate_uuid)
        return act_preds
