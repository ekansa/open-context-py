import pytest

from opencontext_py.apps.all_items import configs
from opencontext_py.apps.all_items.models import (
    AllManifest,
    AllAssertion,
    AllHistory,
    AllResource,
    AllIdentifier,
    AllSpaceTime,
)

# ---------------------------------------------------------------------
# NOTE: This sets up database entities required for testing ETL
# functions. It also includes a function to delete database entities
# following test runs.
# ---------------------------------------------------------------------

TEST_PROJECT_SOURCE_ID = 'elt-project-setup-47263b0d1c4f'
TEST_PROJECT_UUID = 'f6721495-1841-423b-bf1d-9e2673fb8f49'

TEST_PROJECT_MANIFEST_DICT = {
    # ETL processes need a project
    'uuid': TEST_PROJECT_UUID,
    'publisher_id': configs.OPEN_CONTEXT_PUB_UUID,
    'project_id': configs.OPEN_CONTEXT_PROJ_UUID,
    'item_class_id': configs.DEFAULT_CLASS_UUID,
    'source_id': TEST_PROJECT_SOURCE_ID,
    'item_type': 'projects',
    'data_type': 'id',
    'slug': '1000-etl-testing-project-143db91adac4',
    'label': 'ETL Testing Project',
    'uri': f'opecontext.org/projects/{TEST_PROJECT_UUID}',
    'context_id': configs.OPEN_CONTEXT_PROJ_UUID,
    'meta_json': {
        'short_id': 10000,
    }
}


@pytest.mark.django_db
def setup_etl_test_project_manifest_obj():
    """Creates and gets a project manifest object for ETL tests"""
    project, _ = AllManifest.objects.get_or_create(
        uuid=TEST_PROJECT_UUID,
        defaults=TEST_PROJECT_MANIFEST_DICT
    )
    # Now make the context and project the same item, to
    # further limit impact of these tests.
    project.project_id = TEST_PROJECT_UUID
    project.context_id = TEST_PROJECT_UUID
    project.save()
    return project


@pytest.mark.django_db
def cleanup_etl_test_entities():
    """Deletes all the database records associated with the ETL test project"""
    project = setup_etl_test_project_manifest_obj()
    AllIdentifier.objects.filter(item__project=project).delete()
    AllHistory.objects.filter(item__project=project).delete()
    AllResource.objects.filter(item__project=project).delete()
    AllAssertion.objects.filter(project=project).delete()
    AllSpaceTime.objects.filter(item__project=project).delete()
    AllManifest.objects.filter(project=project).delete()


@pytest.mark.django_db
def setup_etl_test_project_with_clean_state():
    """Sets up an ETL test project and pre-deletes any leftover test records"""
    cleanup_etl_test_entities()
    return setup_etl_test_project_manifest_obj()