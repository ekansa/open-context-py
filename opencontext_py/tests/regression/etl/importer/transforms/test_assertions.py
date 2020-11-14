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

from opencontext_py.apps.etl.importer.transforms import subjects as etl_subjects
from opencontext_py.apps.etl.importer.transforms import predicates_types_variables as etl_p_t_v
from opencontext_py.apps.etl.importer.transforms import assertions as etl_asserts

from opencontext_py.apps.etl.importer import utilities as etl_utils

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
    setup_valid_spatial_containment_annotations,
    setup_preds_types_vars_vals_fields_annotations,
    setup_described_by_fields_annotations,
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

EXPECTED_ASSERTIONS_LITERALS = [
    ('Gorgoroth', None, 'Region Notes', 'xsd:string', 'It is a barren wasteland',),
    ('Gorgoroth', None, 'Region Notes', 'xsd:string', 'There is evil there that does not sleep',),
    ('Misty Mountains', None, 'Region Notes', 'xsd:string', 'Has deep roots',),
    ('Barad-dûr', None, 'Site Notes', 'xsd:string', 'Vast fortress',),
    ('Barad-dûr', None, 'Last Wikipedia Edit', 'xsd:date', '13 June 2020',),
    ('Barad-dûr', None, 'Orcs', 'xsd:integer', '255000',),
    # NOTE: This is to make sure the Mt. Doom in Mordor gets the correct Site Note
    ('Mt. Doom', 'Misty Mountains', 'Site Notes', 'xsd:string', 'Toasty',),
    # NOTE: This is the tricky 2nd 'Mt. Doom' that is NOT in Mordor.
    ('Mt. Doom', 'Mordor', 'Site Notes', 'xsd:string', 'A 2nd “Mt. Doom”',),
    ('Mt. Doom', 'Mordor', 'Last Wikipedia Edit [Note]', 'xsd:string', 'As if!',),
    ('Mt. Doom', 'Mordor', 'All [Note]', 'xsd:string', 'Fake',),
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


@pytest.mark.django_db
def test_descriptive_assertions():
    """Tests assertions made after all ETL and adding of literal values"""
    ds_source = get_or_load_test_data_dataframe(TEST_SOURCE_ID, TEST_FILE)
    setup_valid_spatial_containment_annotations(ds_source)
    setup_described_by_fields_annotations(ds_source)
    _ = etl_subjects.reconcile_item_type_subjects(ds_source)
    _ = etl_p_t_v.reconcile_predicates_types_variables(ds_source)
    etl_asserts.make_all_descriptive_assertions(ds_source, log_new_assertion=True)
    for subj_label, subj_path_exclude, pred_label, data_type, literal in EXPECTED_ASSERTIONS_LITERALS:
        object_val = etl_utils.validate_transform_data_type_value(
            literal, 
            data_type
        )
        man_subj_qs = AllManifest.objects.filter(
            project=ds_source.project,
            item_type='subjects',
            label=subj_label
        )
        if subj_path_exclude:
            # We want to exclude something from the path
            # when looking up the subject entity.
            man_subj_qs = man_subj_qs.exclude(
                path__contains=subj_path_exclude
            )
        man_subj = man_subj_qs.first()
        act_assert_qs = AllAssertion.objects.filter(
            project=ds_source.project,
            subject=man_subj,
            predicate__label=pred_label,
            predicate__data_type=data_type,
        )
        if data_type == 'xsd:string':
            act_assert_qs = act_assert_qs.filter(obj_string__startswith=object_val)
        elif data_type == 'xsd:integer':
            act_assert_qs = act_assert_qs.filter(obj_integer=object_val)
        elif data_type == 'xsd:date':
            act_assert_qs = act_assert_qs.filter(obj_datetime=object_val)
        logger.info(
            f'Check {man_subj.label} -> {pred_label} -> {object_val}'
        )
        # We should expect 1 and only 1 assertion to fit our expectations.
        assert len(act_assert_qs) == 1
    cleanup_etl_test_entities()