import pytest

import logging

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
    VALID_HIERARCHY_ANNOTATIONS,
    get_or_load_test_data_dataframe,
    update_fields_attributes,
    setup_valid_spatial_containment_annotations,
)


logger = logging.getLogger("tests-regression-logger")


# List of tuples for testing expected failures of annotations
# between fields where 1 or more are not of item_type = 'subjects'
BAD_FIELD_ITEM_TYPE_ANNOTATIONS = [
    ('Site', configs.PREDICATE_CONTAINS_UUID, 'Site Type',),
    ('Measure', configs.PREDICATE_CONTAINS_UUID, 'Site',),
    ('Lat', configs.PREDICATE_CONTAINS_UUID, 'Lon',),
]

# Lists tuples where the first element is the type of expected problem,
# and the second element is a list of tuples defining spatial hierarchy
# annotations between fields.
BAD_HIERARCHY_ANNOTATIONS = [
    (
        'Site already has parent field',
        [
            # Tuples as follows:
            # expect_error, subj field label, predicate_id, obj_field label
            (False, 'World Region', configs.PREDICATE_CONTAINS_UUID, 'Realm',),
            (False, 'Realm', configs.PREDICATE_CONTAINS_UUID, 'Region',),
            (False, 'Region', configs.PREDICATE_CONTAINS_UUID, 'Site',),
            # Site is already in Region, so it can't be in Realm.
            (True, 'Realm', configs.PREDICATE_CONTAINS_UUID, 'Site',),
        ],
    ),
    (
        'Circular hierarchy',
        [
            # Tuples as follows:
            # expect_error, subj field label, predicate_id, obj_field label
            (False, 'World Region', configs.PREDICATE_CONTAINS_UUID, 'Realm',),
            (False, 'Realm', configs.PREDICATE_CONTAINS_UUID, 'Region',),
            (False, 'Region', configs.PREDICATE_CONTAINS_UUID, 'Site',),
            # Site can't be a parent of one of it's parents.
            (True, 'Site', configs.PREDICATE_CONTAINS_UUID, 'Realm',),
        ],
    ),
]


EXPECTED_ROOT_FIELD = 'World Region'
EXPECTED_DEEPEST_FIELD = 'Site'

# The following list tests the expected creation of manifest objects
# with item_type subjects and the expected spatial hierarchy for 
# these items.
EXPECTED_PARENT_CHILD_RELATIONS = [
    # NOTE: The tuples are as follows
    # (parent_label, child_label, child_path_exclude),
    ('Middle Earth', 'Mordor', None),
    ('Middle Earth', 'Rohan', None),
    # NOTE: There's no "Realm" as a parent context for "Misty Mountains", so
    # we should make the Misty Mountains contained in Middle Earth, the next
    # level up. in the hierarchy
    ('Middle Earth', 'Misty Mountains', None),
    ('Mordor', 'Gorgoroth', None),
    ('Mordor', 'Nurn', None),
    ('Rohan', 'West-mark', None),
    ('Gorgoroth', 'Barad-dûr', None),
    # NOTE: This is the main 'Mt. Doom' (in Mordor, but we're also
    # importing another 'Mt. Doom' into the Misty Mountins to test
    # that our context-dependency for entity reconciliation work).
    ('Gorgoroth', 'Mt. Doom', 'Misty Mountains'),
    ('West-mark', 'Isengard', None),
    ('Misty Mountains', 'Moria', None),
    # NOTE: This is the tricky 2nd 'Mt. Doom' that is NOT expected
    # to be in Mordor.
    ('Misty Mountains', 'Mt. Doom', 'Mordor'),
]

@pytest.mark.django_db
def test_bad_spatial_containment_item_type_annotations():
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
        # Tests expected exception detecting that one or more of the
        # fields in this annotation are not of item_type = "subjects"
        with pytest.raises(Exception) as excinfo:   
            dsa.save()
        assert len(str(excinfo.value)) > 0
    cleanup_etl_test_entities()


@pytest.mark.django_db
def test_bad_spatial_containment_heirarchies_annotations():
    """Tests expected containment annotation errors between non-subjects fields"""
    ds_source = get_or_load_test_data_dataframe(TEST_SOURCE_ID, TEST_FILE)
    update_fields_attributes(
        ds_source, 
        list_attribute_dicts=SUBJECTS_FIELDS_ATTRIBUTE_DICTS,
    )
    for expected_problem, anno_tups in BAD_HIERARCHY_ANNOTATIONS:
        # Clear any existing spatial containment annotations.
        DataSourceAnnotation.objects.filter(
            data_source=ds_source,
            predicate_id=configs.PREDICATE_CONTAINS_UUID
        ).delete()
        logger.info(f'Testing {expected_problem}')
        for expect_error, sub_field_label, predicate_id, obj_field_label in anno_tups:
            sub_field = DataSourceField.objects.filter(
                data_source=ds_source,
                label=sub_field_label
            ).first()
            obj_field = DataSourceField.objects.filter(
                data_source=ds_source,
                label=obj_field_label
            ).first()

            # Make the annotation.
            dsa = DataSourceAnnotation()
            dsa.data_source = ds_source
            dsa.subject_field = sub_field
            dsa.predicate_id = predicate_id
            dsa.object_field = obj_field

            if expect_error:
                # Tests expected exception detecting some problem with the
                # spatial containment hierarchy annotations.
                with pytest.raises(Exception) as excinfo:   
                    assert dsa.save()
                assert len(str(excinfo.value)) > 0
            else:
                # This is expected to be OK and not throw an exception.
                dsa.save()
                assert len(str(dsa.uuid)) > 0
    cleanup_etl_test_entities()


@pytest.mark.django_db
def test_identification_of_root_field():
    """Tests identification of the root (top of hierarchy) containment annotation"""
    ds_source = get_or_load_test_data_dataframe(TEST_SOURCE_ID, TEST_FILE)
    setup_valid_spatial_containment_annotations(ds_source, VALID_HIERARCHY_ANNOTATIONS)
    root_contain_anno_qs = etl_subjects.get_containment_root_annotations(ds_source)
    assert len(root_contain_anno_qs) == 1
    # Make sure the root field is properly identified in the root spatial
    # containment annotation.
    assert root_contain_anno_qs[0].subject_field.label == EXPECTED_ROOT_FIELD
    cleanup_etl_test_entities()


@pytest.mark.django_db
def test_containment_paths():
    """Tests generation of paths of fields in order of containment"""
    ds_source = get_or_load_test_data_dataframe(TEST_SOURCE_ID, TEST_FILE)
    setup_valid_spatial_containment_annotations(ds_source, VALID_HIERARCHY_ANNOTATIONS)
    all_containment_paths = etl_subjects.get_containment_fields_in_hierarchy(ds_source)
    for path in all_containment_paths:
        p_labels = [f.label for f in path]
        logger.info(f'Path: {str(p_labels)}')
        assert path[0].label == EXPECTED_ROOT_FIELD
        assert path[-1].label == EXPECTED_DEEPEST_FIELD
    cleanup_etl_test_entities()


@pytest.mark.django_db
def test_subjects_reconciliation():
    """Tests ETL of subjects items and their expected hierarchy"""
    ds_source = get_or_load_test_data_dataframe(TEST_SOURCE_ID, TEST_FILE)
    setup_valid_spatial_containment_annotations(ds_source, VALID_HIERARCHY_ANNOTATIONS)
    _ = etl_subjects.reconcile_item_type_subjects(ds_source)
    for parent_label, child_label, child_path_exclude in EXPECTED_PARENT_CHILD_RELATIONS:
        man_p = AllManifest.objects.filter(
            project=ds_source.project,
            item_type='subjects',
            label=parent_label
        ).first()
        man_ch_qs = AllManifest.objects.filter(
            project=ds_source.project,
            item_type='subjects',
            label=child_label
        )
        if child_path_exclude:
            # We want to exclude something from the path
            # when looking up the child entity.
            man_ch_qs = man_ch_qs.exclude(
                path__contains=child_path_exclude
            )
        man_ch = man_ch_qs.first()

        assert man_p is not None
        assert man_ch is not None
        logger.info(
            f'Check {man_p.label} -> contains -> {man_ch.label}'
        )
        # Check the exected context relationship exists.
        assert man_ch.context.uuid == man_p.uuid
        contain_assertion = AllAssertion.objects.filter(
            subject=man_p,
            predicate_id=configs.PREDICATE_CONTAINS_UUID,
            object=man_ch,
        ).first()
        # Check that the expected containment assertion
        # exists.
        assert contain_assertion is not None
    cleanup_etl_test_entities()