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


# List of tuples for testing expected failures of annotations
# between fields where 1 or more are not of item_type = 'subjects'
BAD_FIELD_ITEM_TYPE_ANNOTATIONS = [
    ('Site', configs.PREDICATE_CONTAINS_UUID, 'Site Type',),
    ('Measure', configs.PREDICATE_CONTAINS_UUID, 'Site',),
]


@pytest.mark.django_db
def test_bad_subjects_annotations():
    """Tests expected containment annotation errors between non-subjects fields"""
    ds_source = get_or_load_test_data_dataframe(TEST_SOURCE_ID, TEST_FILE)
    update_fields_attributes(
        ds_source, 
        list_attribute_dicts=SUBJECTS_FIELDS_ATTRIBUTE_DICTS,
    )
    for sub_field_label, predicate_id, obj_field_label in BAD_FIELD_ITEM_TYPE_ANNOTATIONS:
        sub_field = DataSourceField.objects.filter(
            data_source=ds_source,
            label=sub_field_label
        ).first()
        obj_field = DataSourceField.objects.filter(
            data_source=ds_source,
            label=obj_field_label
        ).first()
        dsa = DataSourceAnnotation()
        dsa.data_source = ds_source
        dsa.subject_field = sub_field
        dsa.predicate_id = predicate_id
        dsa.object_field = obj_field
        with pytest.raises(Exception) as excinfo:   
            dsa.save()
        assert 'must be item_type="subjects"' in str(excinfo.value)