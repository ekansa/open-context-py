import pytest

import os
import logging
import random

from opencontext_py.apps.all_items import configs
from opencontext_py.apps.all_items.legacy_all import update_old_id

from opencontext_py.apps.etl.importer.models import (
    DataSource,
    DataSourceField,
    DataSourceRecord,
    DataSourceAnnotation,
)
from opencontext_py.apps.etl.importer import df as etl_df

from opencontext_py.tests.regression.etl.project_setup import (
    TEST_PROJECT_UUID,
    setup_etl_test_project_with_clean_state,
    cleanup_etl_test_entities,
)


logger = logging.getLogger("tests-regression-logger")

# A data source ID that's unlikely to actually be used.
TEST_SOURCE_ID = '---etl-importer-test-pPsdH7iY---s77MbZKb'
_, TEST_SOURCE_UUID = update_old_id(TEST_SOURCE_ID)
TEST_FILE = 'test-middle-earth.csv'


# Attribute dicts for subjects fields
SUBJECTS_FIELDS_ATTRIBUTE_DICTS = [
    {
        'label': 'World Region',
        'item_type': 'subjects',
        'item_class_id': configs.CLASS_OC_REGION_UUID,
        'data_type': 'id',
        'context_id': configs.DEFAULT_SUBJECTS_OCEANIA_UUID,
    },
    {
        'label': 'Realm',
        'item_type': 'subjects',
        'item_class_id': configs.CLASS_OC_REGION_UUID,
        'data_type': 'id',
    },
    {
        'label': 'Region',
        'item_type': 'subjects',
        'item_class_id': configs.CLASS_OC_REGION_UUID,
        'data_type': 'id',
    },
    {
        'label': 'Site',
        'item_type': 'subjects',
        'item_class_id': configs.CLASS_OC_REGION_UUID,
        'data_type': 'id',
    },
]



def get_test_file_path(test_file):
    """Gets the path to a test file"""
    current_path = os.path.dirname(os.path.realpath(__file__))
    return os.path.join(current_path, 'data', test_file)


@pytest.mark.django_db
def get_or_load_test_data_dataframe(source_id, test_file):
    """Gets a datasource object or creates one from a CSV file"""
    ds_source = DataSource.objects.filter(
        project_id=TEST_PROJECT_UUID,
        source_id=source_id,
    ).first()
    if ds_source:
        return ds_source

    # We don't have a data source object for this test file,
    # so load it.
    project = setup_etl_test_project_with_clean_state()
    test_file = get_test_file_path(test_file)
    logger.info(f'Test file path: {test_file}')
    df = etl_df.df_str_cols_load_csv(test_file)
    ds_source = etl_df.load_df_for_etl(
        df, 
        project, 
        prelim_source_id=source_id, 
        data_source_label="Middle Earth Sites Test Data", 
        source_exists="replace",
    )
    return ds_source


@pytest.mark.django_db
def update_fields_attributes(ds_source, list_attribute_dicts):
    """Updates data source fields attributes"""
    # We assume we'll be matching on column label
    # for this.
    for attrib_dict in list_attribute_dicts:
        ds_field = DataSourceField.objects.filter(
            data_source=ds_source,
            label=attrib_dict['label']
        ).update(**attrib_dict)
