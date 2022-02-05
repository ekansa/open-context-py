from opencontext_py.apps.ocitems.assertions.models import Assertion
from opencontext_py.apps.ocitems.octypes.models import OCtype
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.ocitems.predicates.models import Predicate


class AssertionObservations():
    """ Class for managing groupings of
    assertions into different observations.

from opencontext_py.apps.ocitems.obsmetadata.models import ObsMetadata
from opencontext_py.apps.ocitems.assertions.observations import AssertionObservations
last_obs = ObsMetadata.objects.all().order_by('id').last()
ometa = ObsMetadata()
ometa.id = last_obs.id + 1
ometa.source_id = 'ref:2164606804233'
ometa.project_uuid = '0db006e9-7d27-47b9-aea8-7b0019a7e81a'
ometa.obs_num = 6
ometa.label = 'Other Taxa and Descriptions'
ometa.obs_type = 'oc-gen:primary'
ometa.note = 'Other Taxa and Description'
ometa.save()
class_uri = 'oc-gen:cat-sample'
aos = AssertionObservations()
aos.change_obs_num_by_source_id(ometa.obs_num, ometa.source_id, class_uri)


class_uris = [
'oc-gen:cat-object',
'oc-gen:cat-arch-element',
'oc-gen:cat-glass',
'oc-gen:cat-pottery',
'oc-gen:cat-coin']
for class_uri in class_uris:
    aos = AssertionObservations()
    aos.change_obs_num_by_source_id(ometa.obs_num, ometa.source_id, class_uri)


from opencontext_py.apps.ocitems.assertions.observations import AssertionObservations


    """
    def __init__(self):
        self.errors = []

    def change_obs_num_by_source_id(self, obs_num, source_id, class_uri=None):
        """ Changes observation numbers or assertions by a source_id,
            with an optional class_uri to further limit.
        """
        change_cnt = 0
        uuids_ok = {}
        old_assertions = Assertion.objects\
                                  .filter(source_id=source_id)\
                                  .exclude(obs_num=obs_num)\
                                  .iterator()
        for old_ass in old_assertions:
            if class_uri is None:
                change_ok = True
            else:
                if old_ass.uuid not in uuids_ok:
                    man_check = Manifest.objects\
                                        .filter(uuid=old_ass.uuid,
                                                class_uri=class_uri)[:1]
                    if len(man_check) > 0:
                        change_ok = True
                    else:
                        change_ok = False
                    uuids_ok[old_ass.uuid] = change_ok
                else:
                    change_ok = uuids_ok[old_ass.uuid]
            if change_ok:
                # ok to make the change!
                new_ass = old_ass
                new_ass.obs_num = obs_num
                new_ass.obs_node = '#obs-' + str(obs_num)
                Assertion.objects\
                         .get(hash_id=old_ass.hash_id)\
                         .delete()
                new_ass.save()
                change_cnt += 1
                print('Assertions changed: ' + str(change_cnt))
