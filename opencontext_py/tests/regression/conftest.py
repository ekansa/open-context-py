import pytest
import random
from django.conf import settings
from opencontext_py.settings import DATABASES
from opencontext_py.apps.ocitems.manifest.models import Manifest


@pytest.fixture(scope="module")
def django_db_setup():
    # Sets up the test database to use the default Open Context database
    # imported from opencontext_py.settings
    settings.DATABASES['default'] = DATABASES['default']


@pytest.fixture
def random_sample_items(db):
    """Gets a random sample of items, from differernt projects, item_types, and classes"""
    MAX_TEST_UUIDS_IN_GROUP = 10
    test_args = []
    combos = set(
        Manifest.objects.all().values_list(
            'project_uuid',
            'item_type',
            'class_uri',
        ).distinct()
    )
    for project_uuid, item_type, class_uri in combos:
        example_qs = Manifest.objects.filter(
            project_uuid=project_uuid,
            item_type=item_type,
        )
        if class_uri:
            example_qs = example_qs.filter(class_uri=class_uri)
        all_uuids = example_qs.values_list('uuid', flat=True)
        num_uuids = len(all_uuids)
        # Make a list of 10 or fewer items, selected at random
        # to test for this project, item_type and class.
        if num_uuids <= MAX_TEST_UUIDS_IN_GROUP:
            test_uuids = all_uuids
        else:
            test_uuids = set()
            iterations = 0 # Another counter for saftety.
            while iterations <= 30 and len(test_uuids) <= MAX_TEST_UUIDS_IN_GROUP:
                iterations += 1
                rand_index = random.randint(0,(num_uuids - 1))
                test_uuids.add(all_uuids[rand_index])
            test_uuids = list(test_uuids)
        test_args += [(project_uuid, item_type, class_uri, uuid,) for uuid in test_uuids]
    return test_args