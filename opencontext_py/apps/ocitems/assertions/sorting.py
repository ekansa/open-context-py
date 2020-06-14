from django.conf import settings
from django.db import models
from opencontext_py.apps.ocitems.assertions.models import Assertion
from opencontext_py.apps.ocitems.octypes.models import OCtype
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.ocitems.predicates.models import Predicate


"""
# Example use.
from opencontext_py.apps.ocitems.assertions.sorting import AssertionSorting
asor = AssertionSorting()
asor.sort_ranked_manifest_for_project('project uuid')

"""


class AssertionSorting():
    """ Class for managing sorting for asseritions based on rankings of types
    and manifest entities.
    """
    TYPES_SORT_BY_MANIFEST = ['documents',
                              'media',
                              'subjects']

    def __init__(self):
        self.problems = []

    def sort_ranked_types_for_project(self, project_uuid):
        """Changes sort order for assertions with ranked types in a project """
        act_preds = self.get_preds_with_ranked_types(project_uuid)
        for predicate_uuid in act_preds:
            print('Working on predicate: ' + predicate_uuid)
            self.re_rank_assertions_by_predicate(predicate_uuid)

    def re_rank_assertions_by_predicate(self, predicate_uuid, filter_args=None):
        type_rankings = self.get_ranked_types_for_pred(predicate_uuid)
        if type_rankings:
            max_type = max(type_rankings, key=type_rankings.get)
            default_missing_rank = float(type_rankings[max_type] + 1)
        else:
            default_missing_rank = 0
        print('Predicate: ' + predicate_uuid + ' has ' + str(len(type_rankings)) + ' ranked types.')
        act_assertions = Assertion.objects\
                                  .filter(predicate_uuid=predicate_uuid)\
                                  .order_by('uuid', 'sort')
        if filter_args is not None:
            # Add additional optional filters.
            act_assertions = act_assertions.filter(**filter_args)
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
            act_ass.sort_save()
    
    def re_rank_assertions_by_source(self, project_uuid, source_id):
        """Re-ranks assertions to items impacted by an import of source_id"""
        pred_sources =  Assertion.objects.filter(
            source_id=source_id,
            object_uuid__isnull=False,
        ).exclude(
            object_uuid=''
        ).values_list(
            'predicate_uuid',
            flat=True
        ).distinct()
        
        for predicate_uuid in set(pred_sources):
            # Now query to get the UUIDs that have been
            # impacted by this source and predicate.
            uuids = Assertion.objects.filter(
                source_id=source_id,
                predicate_uuid=predicate_uuid
            ).values_list('uuid', flat=True).distinct()
            self.re_rank_manifest_assertions_by_predicate(
                predicate_uuid,
                project_uuid,
                subject_uuids=uuids
            )

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

    def sort_ranked_manifest_for_all(self):
        """Changes sort order for assertions with ranked manifiest items in ALL projects """
        projs = Manifest.objects\
                        .filter(item_type='projects')\
                        .values_list('uuid', flat=True)
        for project_uuid in projs:
            print('\n\n\n Working on project: ' + project_uuid)
            self.sort_ranked_manifest_for_project(project_uuid)

    def sort_ranked_manifest_for_project(self, project_uuid):
        """Changes sort order for assertions with ranked manifiest items in a project """
        act_preds = self.get_preds_with_ranked_manifest_objs(project_uuid)
        for predicate_uuid in act_preds:
            print('Working on predicate: ' + predicate_uuid)
            self.re_rank_manifest_assertions_by_predicate(predicate_uuid,
                                                          project_uuid)

    def re_rank_manifest_assertions_by_predicate(
        self,
        predicate_uuid,
        project_uuid,
        only_subject_uuid=None,
        subject_uuids=[]
    ):
        """ Reranks objects of assertions made using a given
        predicate for a given project by the order in the manifest
        table
        """
        change_count = 0
        if len(subject_uuids) == 0 and only_subject_uuid:
            subject_uuids.append(only_subject_uuid)
        elif len(subject_uuids) == 0 and not only_subject_uuid:
            subject_uuids = Assertion.objects\
                                     .values_list('uuid', flat=True)\
                                     .filter(project_uuid=project_uuid,
                                             predicate_uuid=predicate_uuid)\
                                     .distinct('uuid')\
                                     .iterator()
        for uuid in subject_uuids:
            print('Work - predicate: ' + predicate_uuid + ' - subject: ' + uuid)
            # get all assertions for this subject uuid and predicate_uuid
            presort_assertions = Assertion.objects\
                                          .filter(uuid=uuid,
                                                  predicate_uuid=predicate_uuid,
                                                  object_type__in=self.TYPES_SORT_BY_MANIFEST)\
                                          .order_by('sort')
            # make a list of objects to request from the manifest tab
            act_objects = []
            start_sort = False
            for pre_ass in presort_assertions:
                if start_sort is False:
                    start_sort = round(pre_ass.sort, 0)
                act_objects.append(pre_ass.object_uuid)
            # get sorted list of objects from the manifest tab
            sorted_objects = Manifest.objects\
                                     .values_list('uuid', flat=True)\
                                     .filter(uuid__in=act_objects)\
                                     .order_by('sort')
            # make a dictionary object for easy lookups of manifest sort rank
            manifest_rank = 0
            manifest_sort = {}
            for sorted_manifest_uuid in sorted_objects:
                manifest_rank += 1
                manifest_sort[sorted_manifest_uuid] = manifest_rank
            # iterate through assertions to save sort order
            for act_ass in presort_assertions:
                if act_ass.object_uuid in manifest_sort:
                    manifest_rank = manifest_sort[act_ass.object_uuid]
                else:
                    self.problems.append({'Error': 'Missing object',
                                          'uuid': uuid,
                                          'predicate_uuid': predicate_uuid,
                                          'object_uuid': act_ass.object_uuid,
                                          'object_type': act_ass.object_type})
                    manifest_rank = len(manifest_sort) + 1
                act_ass.sort = float(start_sort) + (manifest_rank / 1000)
                act_ass.sort_save()
                change_count += 1
        print('Predicate: ' + predicate_uuid
              + ', assertions changed:'
              + str(change_count))

    def get_preds_with_ranked_manifest_objs(self, project_uuid):
        """ Gets list of predicate_uuids used in a project
        from the assertions table where the predicates have objects
        of types that get sorted by the manifest
        """
        act_preds = Assertion.objects\
                             .values_list('predicate_uuid', flat=True)\
                             .filter(project_uuid=project_uuid,
                                     object_type__in=self.TYPES_SORT_BY_MANIFEST)\
                             .distinct('predicate_uuid')\
                             .order_by('predicate_uuid')
        return act_preds
