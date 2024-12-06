import copy
import hashlib
import os
from operator import sub
import re

import numpy as np
import pandas as pd

from django.core.cache import caches
from django.db.models import Q

from opencontext_py.apps.all_items.models import (
    AllManifest,
    AllAssertion,
)
from opencontext_py.apps.all_items.legacy_all import update_old_id

from opencontext_py.apps.etl.importer.models import (
    DataSource,
    DataSourceField,
    DataSourceAnnotation,
    DataSourceRecord,
)

from opencontext_py.apps.etl.importer import df as etl_df
from opencontext_py.apps.etl.importer.transforms import finalize_all

from opencontext_py.apps.all_items import configs

from opencontext_py.apps.all_items.editorial.api import get_man_obj_by_any_id

from opencontext_py.apps.etl.kobo import db_lookups
from opencontext_py.apps.etl.kobo import pc_configs


DB_LOAD_RESULT_A_COL = 'OC_DB_LOAD_OK'
DB_LOAD_RESULT_B_COL = 'OC_DB_LOAD_B_OK'
DEFAULT_OBS_NUM = 1



def get_or_create_manifest_obj(
    item_type,
    item_label,
    item_class_obj,
    source_id,
    item_uuid=None,
    item_any_id=None,
    context=None,
    reconcile_project_ids=None,
    item_data_type='id',
    field_num=None,
    meta_json=None,
):
    """Gets or creates a manifest entity after reconciliation"""
    num_matching = 0
    if item_uuid:
        man_obj = AllManifest.objects.filter(
            uuid=item_uuid
        ).first()
        if man_obj:
            num_matching = 1
    else:
        man_obj, num_matching = db_lookups.db_reconcile_manifest_obj(
            item_label=item_label,
            item_type=item_type,
            item_class_obj=item_class_obj,
            item_any_id=item_any_id,
            context=context,
            reconcile_project_ids=reconcile_project_ids,
            item_data_type=item_data_type,
            meta_json=meta_json,
        )

    if num_matching > 1:
        print(f'Found {num_matching}, too many possible matches for {item_label} ')
        return None, False

    if man_obj:
        # We have an existing manifest object, so
        # don't make it again.
        return man_obj, False

    # Make a new Manifest item
    man_dict = {
        'publisher_id': configs.OPEN_CONTEXT_PUB_UUID,
        'project_id': pc_configs.PROJECT_UUID,
        'source_id': source_id,
        'item_type': item_type,
        'data_type': item_data_type,
        'label': item_label,
        'context': context,
    }
    if item_uuid:
        man_dict['uuid'] = item_uuid
    if item_class_obj:
        man_dict['item_class'] = item_class_obj
    if item_type == 'predicates' and field_num:
        man_dict['meta_json'] = {
            'sort': field_num,
        }
    try:
        man_obj = AllManifest(**man_dict)
        man_obj.save()
        made_new = True
    except Exception as e:
        man_obj = None
        made_new = False
        print(f'Failed to make new manifest item: {str(man_dict)}')
        print(str(e))
        raise(ValueError(f'{str(man_dict)}'))
    if not man_obj:
        return man_obj, made_new
    print(f'---> Created {man_obj.label} ({man_obj.uuid}) in context {man_obj.context.label} ({man_obj.context.uuid})')
    return man_obj, made_new


# ---------------------------------------------------------------------
# CONTEXT (item_type: subjects) RELATED FUNCTIONS
# ---------------------------------------------------------------------
def load_subject_and_containment(
    source_id,
    parent_uuid,
    child_label,
    child_uuid,
    child_item_class_slug,
):
    """Loads a subject item and containment relation into the database"""
    item_class_obj = db_lookups.cache_get_man_obj_by_any_id(child_item_class_slug)
    if not item_class_obj:
        print(
            f'Cannot find item_class {child_item_class_slug} '
        )
        # Skip the rest.
        return False
    parent_man_obj = db_lookups.cache_get_man_obj_by_any_id(parent_uuid)
    if parent_man_obj is None:
        print(
            f'Cannot find parent_uuid {parent_uuid} '
            f'for {child_label} ({child_uuid})'
        )
        # Skip the rest.
        return False
    # OK to continue
    man_obj, made_new = get_or_create_manifest_obj(
        item_type='subjects',
        item_label=child_label,
        item_class_obj=item_class_obj,
        item_uuid=child_uuid,
        source_id=source_id,
        context=parent_man_obj,
    )
    if not man_obj:
        # We failed to make or reconcile the item.
        return False
    if not made_new:
        # This item already exists.
        return True
    # Now make the containment assertion
    assert_dict = {
        'project_id': pc_configs.PROJECT_UUID,
        'publisher_id': configs.OPEN_CONTEXT_PUB_UUID,
        'source_id': source_id,
        'subject': parent_man_obj,
        'predicate_id': configs.PREDICATE_CONTAINS_UUID,
        'object':man_obj,
    }
    assert_uuid = AllAssertion().primary_key_create(
        subject_id=assert_dict['subject'].uuid,
        predicate_id=assert_dict['predicate_id'],
        object_id=assert_dict['object'].uuid,
    )
    assert_dict['uuid'] = assert_uuid
    assert_obj = AllAssertion(**assert_dict)
    try:
        assert_obj.save()
    except Exception as e:
        print(str(e))
        return False
    return True


def load_subjects_parent_child_cols_df(
    subjects_df,
    parent_child_col_tup,
    source_id=pc_configs.SOURCE_ID_SUBJECTS,
    extra_filter_index=None,
):
    if not set(parent_child_col_tup).issubset(subjects_df.columns.tolist()):
        print(f'Missing required import columns {str(parent_child_col_tup)}')
        return subjects_df
    parent_context_col, child_label_col, child_uuid_col, child_class_slug_col = parent_child_col_tup
    indx = (
        ~subjects_df[parent_context_col].isnull()
        & ~subjects_df[child_label_col].isnull()
        & ~subjects_df[child_uuid_col].isnull()
        & ~subjects_df[child_class_slug_col].isnull()
    )
    if extra_filter_index is not None:
        indx &= extra_filter_index
    if subjects_df[indx].empty:
        print(f'No data to import columns {str(parent_child_col_tup)}')
        return subjects_df
    child_result_col = child_label_col.replace('_name', '_import')
    subjects_df[child_result_col] = np.nan
    grp_cols = list(parent_child_col_tup)
    df_g = subjects_df[indx][grp_cols].groupby(grp_cols, as_index=False).first()
    df_g.reset_index(drop=True, inplace=True)
    print(f'Reconcile containment in {parent_child_col_tup}')
    # Clear the cache to make sure we get fresh lookups for items.
    cache = caches['redis']
    cache.clear()
    for _, row in df_g.iterrows():
        ok = load_subject_and_containment(
            source_id=source_id,
            parent_uuid=str(row[parent_context_col]),
            child_label=str(row[child_label_col]),
            child_uuid=str(row[child_uuid_col]),
            child_item_class_slug=str(row[child_class_slug_col]),
        )
        act_indx = (
            (subjects_df[parent_context_col] == row[parent_context_col])
            & (subjects_df[child_uuid_col] == row[child_uuid_col])
        )
        subjects_df.loc[act_indx, child_result_col] = ok
    return subjects_df


def load_catalog_no_locus(
    subjects_df,
    source_id=pc_configs.SOURCE_ID_SUBJECTS,
):
    """Loads catalog subjects not contained in a locus"""
    req_cols = [
        'unit_uuid',
        'locus_name',
        'locus_uuid',
        'trench_year',
        'catalog_name',
        'catalog_uuid',
        'catalog_item_class_slug',
    ]
    if not set(req_cols).issubset(subjects_df.columns.tolist()):
        print(f'Missing required import columns {str(req_cols)}')
        return subjects_df
    no_loci_indx = (
        (
            (subjects_df['locus_name'] == 'Locus -1')
            | (subjects_df['trench_year'] < 1995)
        )
        & subjects_df['locus_uuid'].isnull()
    )
    parent_child_col_tup = (
        'unit_uuid',
        'catalog_name',
        'catalog_uuid',
        'catalog_item_class_slug',
    )
    return load_subjects_parent_child_cols_df(
        subjects_df,
        parent_child_col_tup,
        source_id=source_id,
        extra_filter_index=no_loci_indx,
    )


def load_subjects_dataframe(
    subjects_df,
    source_id=pc_configs.SOURCE_ID_SUBJECTS,
):
    """Loads the subjects dataframe"""
    if subjects_df is None or subjects_df.empty:
        return subjects_df
    for parent_child_col_tup in pc_configs.SUBJECTS_IMPORT_TREE_COL_TUPS:
        subjects_df = load_subjects_parent_child_cols_df(
            subjects_df,
            parent_child_col_tup,
            source_id=source_id,
        )
    # Load catalog items that are not contained in a locus.
    subjects_df = load_catalog_no_locus(
        subjects_df,
        source_id=source_id,
    )
    return subjects_df



# ---------------------------------------------------------------------
# ATTRIBUTES RELATED FUNCTIONS
# Attributes are loaded into the importer that normally gets data from
# via the user interface. The following functions load data from a
# dataframe with attributes, sets up the field types and relationships,
# assigns UUIDs where feasible, and imports the data into Open Context.
# The main expectation is that entities receiving attributes have been
# already created.
# ---------------------------------------------------------------------
def record_original_field_names(ds_source):
    ds_field_qs = DataSourceField.objects.filter(
        data_source=ds_source,
    ).filter(
        Q(ref_orig_name__isnull=True)
        |Q(ref_orig_name__exact='')
    )
    for ds_field in ds_field_qs:
        ds_field.ref_orig_name = ds_field.label
        if ds_field.label != 'subject_label':
            ds_field.item_type = None
            ds_field.data_type = None
            ds_field.context = None
        ds_field.save()


def import_from_ds_source(ds_source):
    # finalize_all.delete_data_source_reconciled_associations(ds_source)
    finalize_all.delete_imported_from_datasource(ds_source)
    for _, stage_label, func, _, updates_df in finalize_all.PROCESS_STAGES:
        if func is None:
            continue
        print(f'Working on import stage: {stage_label}')
        if not updates_df:
            func_output = func(ds_source)
            print(f'Made {func_output} annotations')
            continue
        df = etl_df.db_make_dataframe_from_etl_data_source(
            ds_source,
            include_uuid_cols=True,
            include_error_cols=True,
            use_column_labels=False,
        )
        func_output = func(ds_source, df=df)


def prep_subject_uuid_field(ds_source, sub_field):
    uuid_field = DataSourceField.objects.filter(
        data_source=ds_source,
        label='subject_uuid'
    ).first()
    if not uuid_field:
        return None
    uuid_field.item_type = 'uuid'
    uuid_field.save()
    des_exists = DataSourceAnnotation.objects.filter(
        data_source=ds_source,
        object_field=uuid_field,
        predicate_id=configs.PREDICATE_OC_ETL_DESCRIBED_BY,
    ).first()
    if des_exists:
        return uuid_field
    dsa = DataSourceAnnotation()
    dsa.data_source = ds_source
    dsa.subject_field = sub_field
    dsa.predicate_id = configs.PREDICATE_OC_ETL_DESCRIBED_BY
    dsa.object_field = uuid_field
    dsa.save()
    return uuid_field


def add_event_field_for_geometry(dsa, ds_source):
    if dsa.object_field.item_type != 'geometry':
        return None
    event_field = DataSourceField.objects.filter(
        data_source=ds_source,
        item_type='events'
    ).first()
    if not event_field:
        return None
    dsa.event_field = event_field
    dsa.save()


def prepare_ds_source_attribute_cols(
    form_type, 
    ds_source,
    attribute_configs=pc_configs.DF_ATTRIBUTE_CONFIGS,
):
    """Assigns attributes to the columns for a data source"""
    # Make sure we have the original field names recorded
    # properly.
    print(f'Configuring {form_type} fields for {ds_source.source_id}')
    record_original_field_names(ds_source)
    if ds_source.source_id.endswith('-files'):
        # make sure the sub_field has a field type of media.
        _ = DataSourceField.objects.filter(
            data_source=ds_source,
            label='subject_label',
        ).update(
            **pc_configs.MEDIA_IMAGE_FIELD_ARGS
        )
    sub_field = DataSourceField.objects.filter(
        data_source=ds_source,
        label='subject_label'
    ).first()
    if not sub_field:
        return None
    uuid_field = prep_subject_uuid_field(ds_source, sub_field)
    if not uuid_field:
        return None
    for config in attribute_configs:
        if not form_type in config.get('form_type', []):
            continue
        dsf_qs = DataSourceField.objects.filter(
            data_source=ds_source,
        )
        q_term = (
            Q(ref_orig_name=config['source_col'])
        )
        if config['match_type'] == 'startswith':
            q_term |= Q(ref_orig_name__startswith=config['source_col'])
        elif config['match_type'] == 'endswith':
            q_term |= Q(ref_orig_name__endswith=config['source_col'])

        dsf_qs = dsf_qs.filter(q_term)
        if dsf_qs.count() < 1:
            print(f"Cannot find source_col {config['source_col']}")
            continue
        for obj_field in dsf_qs:
            for attrib_key, val in config['field_args'].items():
                setattr(obj_field, attrib_key, val)
            obj_field.save()
            print(f"Updated column: {obj_field.label} ({obj_field.field_num})")
            if obj_field.label == 'subject_label':
                continue
            pred_rel = 'described by'
            predicate_id = configs.PREDICATE_OC_ETL_DESCRIBED_BY
            if obj_field.label.startswith('MEDIA_URL_'):
                pred_rel = 'has media resource url'
                predicate_id = configs.PREDICATE_OC_ETL_MEDIA_HAS_FILES
            if predicate_id == configs.PREDICATE_OC_ETL_DESCRIBED_BY:
                if not obj_field.item_type in DataSourceAnnotation.DESCRIBED_BY_OK_OBJECT_TYPES:
                    # This has to be OK for a description relation
                    continue
            des_exists = DataSourceAnnotation.objects.filter(
                data_source=ds_source,
                object_field=obj_field,
                predicate_id=predicate_id,
            ).first()
            if des_exists:
                continue
            print(f'Make {pred_rel} relation for: {obj_field.label}')
            dsa = DataSourceAnnotation()
            dsa.data_source = ds_source
            dsa.subject_field = sub_field
            dsa.predicate_id = predicate_id
            dsa.object_field = obj_field
            dsa.save()
            # For the locus geo case, where there's a geometry and event_field
            # defined. Make sure the datasource annotation has the event field given.
            add_event_field_for_geometry(dsa, ds_source)


def load_trench_books_and_attributes(
    form_type='trench book',
    source_id=pc_configs.SOURCE_ID_TB_ATTRIB,
    attrib_csv_path=pc_configs.TB_ATTRIB_CSV_PATH,
):
    """Loads/creates trenchbook items and attributes"""
    project = AllManifest.objects.get(uuid=pc_configs.PROJECT_UUID)
    ds_source = etl_df.load_csv_for_etl(
        project=project,
        file_path=attrib_csv_path,
        data_source_label=source_id,
        prelim_source_id=source_id,
        source_exists="replace"
    )
    prepare_ds_source_attribute_cols(form_type, ds_source)
    print(f'Prepared ds_source {ds_source.__dict__}')
    import_from_ds_source(ds_source)
    return ds_source


def load_media_files_and_attributes(
    form_type='media',
    source_id=pc_configs.SOURCE_ID_MEDIA_FILES,
    attrib_csv_path=pc_configs.MEDIA_ALL_KOBO_REFS_CSV_PATH,
):
    """Loads/creates media items, associate resource files and attributes"""
    project = AllManifest.objects.get(uuid=pc_configs.PROJECT_UUID)
    ds_source = etl_df.load_csv_for_etl(
        project=project,
        file_path=attrib_csv_path,
        data_source_label=source_id,
        prelim_source_id=source_id,
        source_exists="replace"
    )
    prepare_ds_source_attribute_cols(form_type, ds_source)
    print(f'Prepared ds_source {ds_source.__dict__}')
    import_from_ds_source(ds_source)
    return ds_source


def add_node_fields_for_locus_grid(ds_source):
    """Adds observation, event, and attribute-group node fields to the locus grid import"""
    project = AllManifest.objects.get(uuid=pc_configs.PROJECT_UUID)
    predicate_field_anno_qs = DataSourceAnnotation.objects.filter(
        data_source=ds_source,
        subject_field__item_type='subjects',
        object_field__item_type='predicates',
    )
    obs_field = DataSourceField.objects.filter(
        data_source=ds_source,
        item_type='observations',
    ).first()
    event_field = DataSourceField.objects.filter(
        data_source=ds_source,
        item_type='events'
    ).first()
    attrib_group_field = DataSourceField.objects.filter(
        data_source=ds_source,
        item_type='attribute-groups'
    ).first()
    for dsa in predicate_field_anno_qs:
        if obs_field is not None:
            obs_field.context = project
            obs_field.save()
            dsa.observation = None
            dsa.observation_field = obs_field
        if event_field is not None:
            event_field.context = project
            event_field.save()
            dsa.event = None
            dsa.event_field = event_field
        if attrib_group_field is not None:
            attrib_group_field.context = project
            attrib_group_field.save()
            dsa.attribute_group = None
            dsa.attribute_group_field = attrib_group_field
        dsa.save()
    

def load_locus_grid_attributes(
    form_type='locus',
    source_id=pc_configs.SOURCE_ID_LOCUS_GRID,
    attrib_csv_path=pc_configs.LOCUS_GRID_CSV_PATH,
):
    """Loads/creates media items, associate resource files and attributes"""
    project = AllManifest.objects.get(uuid=pc_configs.PROJECT_UUID)
    ds_source = etl_df.load_csv_for_etl(
        project=project,
        file_path=attrib_csv_path,
        data_source_label=source_id,
        prelim_source_id=source_id,
        source_exists="replace"
    )
    prepare_ds_source_attribute_cols(
        form_type, 
        ds_source,
        attribute_configs=pc_configs.LOCUS_GRID_ATTRIBUTE_CONFIGS,
    )
    add_node_fields_for_locus_grid(ds_source)
    print(f'Prepared ds_source {ds_source.__dict__}')
    import_from_ds_source(ds_source)
    return ds_source



def load_general_subjects_attributes(
    configs=pc_configs.GENERAL_ATTRIB_SOURCE_FILE_LIST
):
    """Loads subjects (locations, objects) attributes"""
    # NOTE: This does NOT create any new subjects items, it only
    # adds attribute descriptions for those items already created.
    project = AllManifest.objects.get(uuid=pc_configs.PROJECT_UUID)
    for form_type, source_id, attrib_csv_path in configs:
        ds_source = etl_df.load_csv_for_etl(
            project=project,
            file_path=attrib_csv_path,
            data_source_label=source_id,
            prelim_source_id=source_id,
            source_exists="replace"
        )
        if not ds_source:
            print(f'No data source for {form_type}, {source_id}, {attrib_csv_path}')
            continue
        prepare_ds_source_attribute_cols(form_type, ds_source)
        print(f'Prepared ds_source {ds_source.__dict__}')
        import_from_ds_source(ds_source)
        print(f'Added attributes from {ds_source.source_id} ({ds_source.uuid})')


# ---------------------------------------------------------------------
# LINKS RELATED FUNCTIONS
# Link assertions between named entities are structured as a set of
# subject -> predicate (link relation) -> object relationships.
# They are loaded from dataframes that store already reconciled IDs
# for subject and object items. The predicates of the linking relationships
# are human readable strings that get matched against the
# pc_configs.LINK_REL_PRED_MAPPINGS config.
# That config provides an identifier for the human readable linking
# relation and a UUID plus an option UUID for the inverse relationship.
#
# The main expectation is that entities receiving links have been
# already created.
# ---------------------------------------------------------------------

def make_link_assertion(source_id, subject_obj, object_obj, predicate_obj):
    """Makes a link subject, predicate, object assertion. """
    if not subject_obj or not object_obj or not predicate_obj:
        # We require these things to actually exist.
        return False
    assert_obj = AllAssertion.objects.filter(
        subject=subject_obj,
        predicate=predicate_obj,
        object=object_obj,
    ).first()
    if assert_obj:
        return assert_obj
    assert_dict = {
        'project_id': pc_configs.PROJECT_UUID,
        'publisher_id': configs.OPEN_CONTEXT_PUB_UUID,
        'source_id': source_id,
        'subject': subject_obj,
        'predicate': predicate_obj,
        'object': object_obj,
    }
    assert_uuid = AllAssertion().primary_key_create(
        subject_id=assert_dict['subject'].uuid,
        predicate_id=assert_dict['predicate'].uuid,
        object_id=assert_dict['object'].uuid,
    )
    assert_dict['uuid'] = assert_uuid
    assert_obj = AllAssertion(**assert_dict)
    try:
        assert_obj.save()
    except Exception as e:
        print(str(e))
        return None
    return assert_obj


def make_link_assertion_and_inverse(
    source_id,
    subject_obj,
    object_obj,
    predicate_obj,
    inv_predicate_obj
):
    """Make a link assertion and inverse if applicable"""
    inv_assert_obj = None
    assert_obj = make_link_assertion(
        source_id=source_id,
        subject_obj=subject_obj,
        object_obj=object_obj,
        predicate_obj=predicate_obj,
    )
    if inv_predicate_obj:
        # Make the inverse relationship now
        inv_assert_obj = make_link_assertion(
            source_id=source_id,
            subject_obj=object_obj,
            object_obj=subject_obj,
            predicate_obj=inv_predicate_obj
        )
    return assert_obj, inv_assert_obj


def get_manifest_obj_from_dict_or_db(uuid, man_uuid_dict):
    """Gets a manifest object from the man_uuid_dict or the database"""
    if not uuid:
        return None, man_uuid_dict
    uuid = uuid.strip()
    if man_uuid_dict.get(uuid):
        return man_uuid_dict.get(uuid), man_uuid_dict
    man_obj = AllManifest.objects.filter(uuid=uuid).first()
    man_uuid_dict[uuid] = man_obj
    return man_obj, man_uuid_dict


def sort_page_order():
    a_qs = AllAssertion.objects.filter(
        subject__item_type__in=['subjects', 'documents',],
        source_id__in=pc_configs.ALL_SOURCE_IDS,
        predicate__label__in=['Has part', 'Has Related Trench Book Entry',],
        object__item_type='documents',
    ).order_by('subject_id', 'object__label')
    last_subject_uuid = None
    i = 0
    for ass in a_qs:
        if ass.subject.uuid != last_subject_uuid:
            i = 0
        last_subject_uuid = ass.subject.uuid
        i += 0.001
        ass.sort = ass.sort + i
        ass.save()


def make_link_assertions_from_link_csv(source_id, links_csv_path):
    """Makes link assertions from a link csv file"""
    df = pd.read_csv(links_csv_path)
    cols = ['subject_uuid', pc_configs.LINK_RELATION_TYPE_COL, 'object_uuid']
    if not set(cols).issubset(set(df.columns.tolist())):
        print(f'File {links_csv_path} missing required columns {cols}')
        return None
    act_index = (
        ~df['subject_uuid'].isnull()
        & ~df[pc_configs.LINK_RELATION_TYPE_COL].isnull()
        & ~df['object_uuid'].isnull()
    )
    if df[act_index].empty:
        print(f'File {links_csv_path} lacks valid linking assertion data')
        return None
    n = AllAssertion.objects.filter(
        project_id=pc_configs.PROJECT_UUID,
        source_id=source_id,
    ).delete()
    print(f'Deleted {n} linking assertions already existing for source_id {source_id}')
    df_g = df[act_index][cols].groupby(cols, as_index=False).first()
    man_uuid_dict = {}
    for _, row in df_g.iterrows():
        rel = row[pc_configs.LINK_RELATION_TYPE_COL]
        pred_uuid, inv_pred_uuid = pc_configs.LINK_REL_PRED_MAPPINGS.get(
            rel,
            (None, None,)
        )
        if not pred_uuid:
            print('-'*50)
            print(f'PROBLEM! Relation {rel} has no configuration!')
            print('-'*50)
            continue
        subject_obj, man_uuid_dict = get_manifest_obj_from_dict_or_db(
            uuid=str(row['subject_uuid']),
            man_uuid_dict=man_uuid_dict
        )
        object_obj, man_uuid_dict = get_manifest_obj_from_dict_or_db(
            uuid=str(row['object_uuid']),
            man_uuid_dict=man_uuid_dict
        )
        predicate_obj, man_uuid_dict = get_manifest_obj_from_dict_or_db(
            uuid=pred_uuid,
            man_uuid_dict=man_uuid_dict
        )
        inv_predicate_obj, man_uuid_dict = get_manifest_obj_from_dict_or_db(
            uuid=inv_pred_uuid,
            man_uuid_dict=man_uuid_dict
        )
        assert_obj, inv_assert_obj = make_link_assertion_and_inverse(
            source_id,
            subject_obj,
            object_obj,
            predicate_obj,
            inv_predicate_obj
        )
        print(f'Link: {assert_obj}')
        print(f'Inverse Link: {inv_assert_obj}')


def make_all_link_assertion(
    configs=pc_configs.ALL_LINK_SOURCE_FILE_LIST
):
    """Makes all link assertions based on extracted, transformed data in CSV files"""
    for source_id, links_csv_path in configs:
        if not os.path.exists(links_csv_path):
            continue
        make_link_assertions_from_link_csv(source_id, links_csv_path)


def fix_trench_book_main_links():
    trench_df = pd.read_csv(pc_configs.TRENCH_CSV_PATH)
    unit_to_tb_link_pred = AllManifest.objects.get(uuid='f20e9e2e-246f-4421-b1dd-e31e8b58805c')
    tb_to_unit_link_pred = AllManifest.objects.get(uuid=configs.PREDICATE_LINK_UUID)
    tb_to_page_link_pred = AllManifest.objects.get(uuid='bd384f1f-fb29-4a9d-7aca-d8f6b4af0af9')
    page_to_tb_link_pred = AllManifest.objects.get(uuid='0bb889f9-54dd-4f70-5b63-f5d82425f0db')
    for unit_uuid in trench_df['uuid'].unique().tolist():
        unit_obj = AllManifest.objects.filter(uuid=unit_uuid).first()
        if not unit_obj:
            continue
        tb_obj = AllManifest.objects.filter(
            label__startswith='Trench Book',
            label__endswith=unit_obj.label,
            item_type='documents',
        ).first()
        if not tb_obj:
            continue
        make_link_assertion_and_inverse(
            source_id=f'{pc_configs.SOURCE_ID_TB_LINKS}-main-tb',
            subject_obj=unit_obj,
            object_obj=tb_obj,
            predicate_obj=unit_to_tb_link_pred,
            inv_predicate_obj=tb_to_unit_link_pred,
        )
        page_to_tb_links_qs = AllAssertion.objects.filter(
            subject__item_type='documents',
            predicate=tb_to_unit_link_pred,
            object=unit_obj,
        ).exclude(
            subject=tb_obj,
        )
        for ass in page_to_tb_links_qs:
            page_obj = ass.subject
            make_link_assertion_and_inverse(
                source_id=f'{pc_configs.SOURCE_ID_TB_LINKS}-main-tb',
                subject_obj=tb_obj,
                object_obj=page_obj,
                predicate_obj=tb_to_page_link_pred,
                inv_predicate_obj=page_to_tb_link_pred,
            )


def add_trench_book_media_main_links():
    """Add links to image media that lack links to subjects items """
    link_pred_obj = AllManifest.objects.get(uuid=configs.PREDICATE_LINK_UUID)
    media_qs = AllManifest.objects.filter(
        source_id__startswith=pc_configs.SOURCE_ID_PREFIX,
        item_type='media',
    )
    for media_obj in media_qs:
        sub_assert_obj = AllAssertion.objects.filter(
            subject__item_type='subjects',
            object=media_obj
        ).first()
        if sub_assert_obj:
            continue
        doc_assert_obj = AllAssertion.objects.filter(
            subject__item_type='documents',
            object=media_obj
        ).first()
        if not doc_assert_obj:
            # We also don't have a document!
            print(f'Cannot find a connection for {media_obj.label} [{media_obj.uuid}]')
            continue
        sub_doc_assert_qs = AllAssertion.objects.filter(
            subject__item_type='subjects',
            object=doc_assert_obj.subject,
        ).order_by(
            '-subject__path',
        )
        if sub_doc_assert_qs.count() < 1:
            print(
                f'Cannot find a connection for {media_obj.label} [{media_obj.uuid}] '
                f'via document {doc_assert_obj.subject.label} [{doc_assert_obj.subject.uuid}]'
            )
            continue
        print(
            f'Made a subjects connection for {media_obj.label} [{media_obj.uuid}] '
        )
        act_sub_doc_assert = None
        if sub_doc_assert_qs.count() > 2:
            # We have multiple things linking to this, choose the one with the shortest path
            # which will be the more general thing.
            act_sub_doc_assert = sub_doc_assert_qs.last()
        else:
            # Choose the first thing, since there's few things linking.
            act_sub_doc_assert = sub_doc_assert_qs.first()
        make_link_assertion_and_inverse(
            source_id=f'{pc_configs.SOURCE_ID_MEDIA_LINKS}-via-tb',
            subject_obj=media_obj,
            object_obj=act_sub_doc_assert.subject,
            predicate_obj=link_pred_obj,
            inv_predicate_obj=link_pred_obj,
        )


def add_persons():
    person_class_obj = AllManifest.objects.get(
        uuid=configs.CLASS_FOAF_PERSON_UUID,
    )
    project_obj = AllManifest.objects.get(
        uuid=pc_configs.PROJECT_UUID,
    )
    df = pd.read_csv(pc_configs.PEOPLE_CSV_PATH)
    for _, row in df.iterrows():
        uuid = row['uuid']
        man_obj = AllManifest.objects.filter(
            uuid=uuid,
            item_type='persons',
        ).first()
        if man_obj:
            continue
        man_obj, made_new = get_or_create_manifest_obj(
            item_label=row['label_oc'],
            item_class_obj=person_class_obj,
            item_uuid=uuid,
            item_type='persons',
            item_data_type='id',
            context=project_obj,
            source_id=pc_configs.SOURCE_ID_PERSONS,
            meta_json={
                'combined_name': row['label_oc'],
                'surname': row.get('surname'),
                'initials': row.get('name'),
            }
        )
    return df