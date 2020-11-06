import pytest

import os
import logging
import random

from opencontext_py.apps.all_items import configs
from opencontext_py.apps.all_items.models import (
    AllManifest,
    AllAssertion,
)

from opencontext_py.apps.etl.importer.models import (
    DataSource,
    DataSourceField,
    DataSourceRecord,
    DataSourceAnnotation,
)

from opencontext_py.apps.etl.importer.transforms import predicates_types_variables as etl_p_t_v

from opencontext_py.tests.regression.etl.project_setup import (
    TEST_PROJECT_UUID,
    setup_etl_test_project_with_clean_state,
    cleanup_etl_test_entities,
)
from opencontext_py.tests.regression.etl.importer.df_datasources import (
    TEST_SOURCE_ID,
    TEST_SOURCE_UUID,
    TEST_FILE,
    get_or_load_test_data_dataframe,
    update_fields_attributes,
    setup_preds_types_vars_vals_fields_annotations,
)


logger = logging.getLogger("tests-regression-logger")


# The following list tests the expected creation of manifest objects
# with item_type predicates and item_type types and the expected context
# relations for these.
EXPECTED_PREDICATES_TYPES_RELATIONS = [
    # NOTE: The tuples are as follows
    # (parent_label (predicate), child_label (type), ),
    ('Construction Technique', 'Foraged iron',),
    ('Construction Technique', 'Excavated',),
    ('Geology', 'Volcanic',),
    ('Geology', 'Mithril veins',),
    ('Site Type', 'Tower',),
    ('Site Type', 'Dungeon',),
]

@pytest.mark.django_db
def test_predicates_types_reconciliation():
    """Tests ETL of predicates and types items and their expected context"""
    ds_source = get_or_load_test_data_dataframe(TEST_SOURCE_ID, TEST_FILE)
    setup_preds_types_vars_vals_fields_annotations(ds_source)
    _ = etl_p_t_v.reconcile_predicates_types_variables(ds_source)
    for parent_label, child_label in EXPECTED_PREDICATES_TYPES_RELATIONS:
        man_p = AllManifest.objects.filter(
            project=ds_source.project,
            item_type='predicates',
            label=parent_label,
            data_type='id',
        ).first()
        man_ch = AllManifest.objects.filter(
            project=ds_source.project,
            item_type='types',
            label=child_label,
            data_type='id',
        ).first()
        assert man_p is not None
        assert man_ch is not None
        logger.info(
            f'Check {man_p.label} -> is predicate context for -> {man_ch.label}'
        )
        # Check the exected context relationship exists.
        assert man_ch.context.uuid == man_p.uuid
    cleanup_etl_test_entities()