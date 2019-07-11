import pytest
import random
from django.conf import settings
from opencontext_py.settings import DATABASES
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.ocitems.assertions.models import Assertion

# How many UUIDs should be sampled in each group project,
# item_type, class, etc.
MAX_TEST_UUIDS_IN_GROUP = 5

@pytest.fixture(scope="module")
def django_db_setup():
    # Sets up the test database to use the default Open Context database
    # imported from opencontext_py.settings
    settings.DATABASES['default'] = DATABASES['default']


@pytest.fixture
def random_sample_items(db):
    """Gets a random sample of items, from different projects, item_types, and classes"""
    # NOTE: This iterates through each project, item_types, and class_uri
    # to randomly select representative uuids for testing. Because it selects
    # uuids from such wide variety of sources and types, it helps in testing
    # the full diversity of items published by Open Context.
    MAX_TEST_UUIDS_IN_GROUP = 5
    test_args = []
    combos = set(
        Manifest.objects.all().values_list(
            'project_uuid',
            'item_type',
            'class_uri',
        ).distinct()
    )
    combos = sorted(list(combos))
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


@pytest.fixture
def random_sample_items_by_predicate(db):
    """Gets a random sample of items, from different projects and use of different predicates"""
    # NOTE: I haven't actually tested this function yet. This is still in development.
    test_args = []
    all_test_uuids = set()
    combos = set(
        Manifest.objects.filter(
            item_type='predicates'
        ).values_list(
            'project_uuid',
            'uuid',
        ).distinct()
    )
    combos = sorted(list(combos))
    for project_uuid, predicate_uuid in combos:
        example_qs = Assertion.objects.filter(
            project_uuid=project_uuid,
            predicate_uuid=predicate_uuid
        )
        all_uuids = example_qs.values_list('uuid', flat=True)
        num_uuids = len(all_uuids)
        # Make a list of 10 or fewer items, selected at random
        # to test for this project, item_type and class.
        if num_uuids <= MAX_TEST_UUIDS_IN_GROUP:
            batch_uuids = all_uuids
        else:
            batch_uuids = []
            for i in range(0, MAX_TEST_UUIDS_IN_GROUP):
                rand_index = random.randint(0,(num_uuids - 1))
                batch_uuids.append(all_uuids[rand_index])
        # Use batch uuids are only going to be new, not repeats of uuids already
        # in the set of all_test_uuids. The list use_batch_uuids may be empty
        # if all the uuids in the batch_uuids list are already present in the
        # all_test_uuids set.
        use_batch_uuids = [uuid for uuid in batch_uuids if not uuid in all_test_uuids]
        for uuid in use_batch_uuids:
            # Add the uuid to the set of all_test_uuids so we don't repeat.
            all_test_uuids.add(uuid)
            # add to the set of test args.
            test_args.append((project_uuid, predicate_uuid, uuid,))
    return test_args



