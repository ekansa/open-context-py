import pytest

import os
import logging
import random

from opencontext_py.apps.all_items import configs

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
from opencontext_py.tests.regression.etl.importer.df_datasources import (
    TEST_SOURCE_ID,
    TEST_SOURCE_UUID,
    TEST_FILE,
    SUBJECTS_FIELDS_ATTRIBUTE_DICTS,
    get_or_load_test_data_dataframe,
    update_fields_attributes,
)


logger = logging.getLogger("tests-regression-logger")


@pytest.mark.django_db
def test_load_ds_source():
    """Tests the creation of a ds_source object from a CSV file."""
    ds_source = get_or_load_test_data_dataframe(TEST_SOURCE_ID, TEST_FILE)
    cleanup_etl_test_entities()
    assert ds_source.field_count > 0
    assert ds_source.row_count > 0
    

@pytest.mark.django_db
def test_set_ds_fields_subjects():
    """Tests the creation of a ds_source object from a CSV file."""
    ds_source = get_or_load_test_data_dataframe(TEST_SOURCE_ID, TEST_FILE)
    update_fields_attributes(
        ds_source, 
        list_attribute_dicts=SUBJECTS_FIELDS_ATTRIBUTE_DICTS,
    )
    for attrib_dict in SUBJECTS_FIELDS_ATTRIBUTE_DICTS:
        ds_field = DataSourceField.objects.filter(
            data_source=ds_source,
            label=attrib_dict['label']
        ).first()
        assert ds_field.item_type == 'subjects'
    cleanup_etl_test_entities()