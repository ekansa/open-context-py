import copy
import pytest
import logging
import random
from opencontext_py.apps.entities.entity.models import Entity
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.ldata.linkentities.models import LinkEntity

logger = logging.getLogger("tests-regression-logger")


@pytest.mark.django_db
def do_manifest_items_search_tests(
    project_uuid, 
    item_type, 
    class_uri, 
    uuid
):
    """Actually tests random combinations of args on manifest
       entity searches
    """
    man = Manifest.objects.get(uuid=uuid)

    # The qstring is meant for filter on partial string matches, so
    # make a list of different strings to filter on based on
    # different attributes of the manifest object. 
    qstring_opts = [
        man.slug,
        man.slug[:5],
        man.uuid,
        man.uuid[:5],
        man.label,
        man.label[:5]
    ]

    all_args = {
        'qstring': random.choice(qstring_opts),
        'project_uuid': project_uuid,
        'item_type': item_type,
        'class_uri': class_uri,
        'label': man.label,
    }
    # The entity.search results are a list of dicts with slightly
    # different keys than the arguments used in the search. 
    # Below is a mapping between args (keys) and result
    # item keys.
    key_mappings = {
        'project_uuid': 'partOf_id',
        'item_type': 'type',
    }
    # Randomly generate different argument dicts that
    # use only certain keys and values of the all_args dict
    # above.
    keys = list(all_args.keys())
    args_list = [all_args]
    for num_sample in range(2, len(keys)):
        sample_keys = random.sample(keys, num_sample)
        new_args = {}
        for key in sample_keys:
            new_args[key] = all_args[key]
            if key == 'qstring':
                # Selects a random query string option.
                new_args[key] = random.choice(qstring_opts)
        if not 'qstring' in new_args:
            # The qstring is required, so make sure that
            # it is always at least an empty string.
            new_args['qstring'] = ''
        args_list.append(new_args)
    for args in args_list:
        ent = Entity()
        # Get the search results using the args.
        results = ent.search(**args)
        # Now test to make sure that the search results have the
        # expected values based on the search filtering criteria
        # passed by args.
        for key, value in args.items():
            if key == 'qstring' or not value:
                # Don't check qstring or an empty / missing value.
                continue
            check = key_mappings.get(key, key)
            for result in results:
                assert result[check] == value


def test_random_manifest_items_search(random_sample_items):
    """Tests search of manifest entities with randomly selected
    arguments on project_uuid, item_type, class_uri, etc.
    """
    # Get a random sublist of the bigger sampled items list.
    num_tests = 20
    sub_list_random_items = random.sample(random_sample_items, num_tests)
    i = 0
    for project_uuid, item_type, class_uri, uuid in sub_list_random_items:
        i += 1
        logger.info(
            'Test {}/{}: project_uuid="{}", item_type="{}", class_uri="{}", uuid="{}"'.format(
               i, num_tests, project_uuid, item_type, class_uri, uuid)
        )
        do_manifest_items_search_tests(
            project_uuid, 
            item_type, 
            class_uri, 
            uuid
        )
        