import json
import logging
import time

import numpy as np
import pandas as pd

from django.db.models import Q

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
    get_immediate_context_parent_obj_db,
    get_immediate_context_children_objs_db,
)
from opencontext_py.apps.etl.importer import df as etl_df
from opencontext_py.apps.etl.importer import utilities as etl_utils
from opencontext_py.apps.etl.importer.transforms import reconcile
from opencontext_py.apps.etl.importer.transforms import utilities as trans_utils


logger = logging.getLogger("etl-importer-logger")

# ---------------------------------------------------------------------
# NOTE: These functions manage the transformations for making
# assertions on already reconciled entities. These assertions will
# typically include assertions about literal values.
# ---------------------------------------------------------------------

LITERAL_ATTRIBUTE_DATA_TYPES = [
    ('obj_string', 'xsd:string',),
    ('obj_boolean', 'xsd:boolean',),
    ('obj_integer', 'xsd:integer',),
    ('obj_double', 'xsd:double',),
    ('obj_datetime',  'xsd:date',),
]

# These are attributes needed to calculate the uuid
# (primary key ID) for a given assertion.
ASSERT_ID_ATTRIBUTES = [
    'subject_id',
    'predicate_id',
    'object_id',
    'obj_string',
    'obj_boolean',
    'obj_integer',
    'obj_double',
    'obj_datetime',
    'observation_id',
    'event_id',
    'attribute_group_id',
    'language_id',
]

# These are predicates have special handling, and are NOT to be
# considered when making linking assertions between named entities.
LINKS_EXCLUDE_PREDICATE_IDS = [
    configs.PREDICATE_OC_ETL_DESCRIBED_BY,
    configs.PREDICATE_CONTAINS_UUID,
    configs.PREDICATE_OC_ETL_MEDIA_HAS_FILES,
]


def update_df_object_column_for_ds_anno(
    ds_anno, 
    df, 
    act_obj_col=None, 
    act_obj_dt_col=None,
    filter_index=None,
):
    """Updates an ETL import dataframe by setting object item and literal columns"""
    if filter_index is None:
        # No filter index set, so process the whole dataframe df
        filter_index = df['row_num'] >= 0

    if not act_obj_col:
        act_obj_col = f'assertion_object__{ds_anno.data_source.source_id}'
    if not act_obj_dt_col:
        act_obj_dt_col = f'assertion_object_dt__{ds_anno.data_source.source_id}'
    
    # Set the columns with empty values.
    df.loc[filter_index, act_obj_col] = np.nan
    df.loc[filter_index, act_obj_dt_col] = np.nan

    if not ds_anno.object_field:
        # We're trying to assign a preset literal value.
        for lit_attrib, data_type in LITERAL_ATTRIBUTE_DATA_TYPES:
            literal_val = getattr(ds_anno, lit_attrib)
            if not literal_val:
                continue
            df.loc[filter_index, act_obj_col] = literal_val
            df.loc[filter_index, act_obj_dt_col] = data_type
        return df
    
    object_field = ds_anno.object_field
    act_item_obj_col = f'{object_field.field_num}_item'
    act_item_literal_col = f'{object_field.field_num}_col'
    df.loc[filter_index, act_obj_dt_col] = object_field.data_type
    if object_field.data_type != 'id':
        # Copy literal (non-named entity) values 
        df.loc[filter_index, act_obj_col] = df[filter_index][act_item_literal_col]
    else:
        # Copy the already reconciled uuids to named entities
        df.loc[filter_index, act_obj_col] = df[filter_index][act_item_obj_col]
    return df


def get_make_note_predicate_for_invalid_literal_db(
    ds_source, 
    predicate_uuid, 
    sort,
    add_assoction_uuid=None
):
    """Gets a note predicate for use with a literal value that is not valid"""
    # Get the manifest object for the literal predicate for which we 
    # have an object value with the wrong data_type.
    man_obj = AllManifest.objects.filter(uuid=predicate_uuid).first()
    if not man_obj:
        return None
    pred_note_label = f'{man_obj.label} [Note]'
    pred_note_obj = AllManifest.objects.filter(
        label=pred_note_label,
        item_type='predicates',
        project=ds_source.project,
        data_type='xsd:string',
        item_class_id=configs.CLASS_OC_VARIABLES_UUID,
    ).first()
    if pred_note_obj:
        return pred_note_obj

    # Make a new Manifest item
    man_dict = {
        'publisher': ds_source.publisher,
        'project': ds_source.project,
        'source_id': ds_source.source_id,
        'item_type': 'predicates',
        'data_type': 'xsd:string',
        'item_class_id': configs.CLASS_OC_VARIABLES_UUID,
        'label': pred_note_label,
        'context': ds_source.project,
        'meta_json':  {'sort': sort},
    }

    try:
        pred_note_obj = AllManifest(**man_dict)
        pred_note_obj.save()
    except:
        pred_note_obj = None
    
    if not pred_note_obj:
        return None

    logger.info(f'Made note field: {pred_note_obj} from {man_obj}')
    if pred_note_obj and add_assoction_uuid:
        # Add an association between the new pred_note_obj
        # and the literal predicate object.
        assert_dict = {
            'project': ds_source.project,
            'publisher': ds_source.publisher,
            'source_id': ds_source.source_id,
            'subject': pred_note_obj,
            'predicate_id': add_assoction_uuid,
            'object': man_obj,
        }
        ass_obj, _ = AllAssertion.objects.get_or_create(
            uuid=AllAssertion().primary_key_create(
                subject_id=assert_dict['subject'].uuid,
                predicate_id=assert_dict['predicate_id'],
                object_id=assert_dict['object'].uuid,
            ),
            defaults=assert_dict
        )
    return pred_note_obj


def make_descriptive_assertions(
    ds_anno, 
    df, 
    invalid_literal_to_str=True, 
    log_new_assertion=False,
    filter_index=None,
    print_progress=False,
):
    """Make a descriptive assertion based on a ds_anno object"""

    start = time.time()
    if print_progress:
        print(
            f'Start assertion creation with: {ds_anno.subject_field.label} '
        )
    if print_progress and ds_anno.object_field:
        print(
            f'-> {ds_anno.object_field.label} '
        )

    if filter_index is None:
        # No filter index set, so process the whole dataframe df
        filter_index = df['row_num'] >= 0

    ds_source = ds_anno.data_source
    act_subj_col = f'assertion_subject_uuid__{ds_source.source_id}'
    act_pred_col = f'assertion_predicate_uuid__{ds_source.source_id}'
    act_obs_col = f'assertion_obs_uuid__{ds_source.source_id}'
    act_event_col = f'assertion_event_uuid__{ds_source.source_id}'
    act_attrib_group_col = f'assertion_attribute_group_uuid__{ds_source.source_id}'
    act_lang_col = f'assertion_language_uuid__{ds_source.source_id}'
    act_obj_col = f'assertion_object__{ds_source.source_id}'
    act_obj_dt_col = f'assertion_object_dt__{ds_source.source_id}'

    assert_cols = [
        act_subj_col,
        act_pred_col,
        act_obs_col,
        act_event_col,
        act_attrib_group_col,
        act_lang_col,
        act_obj_col,
        act_obj_dt_col,
    ]
    for assert_col in assert_cols:
        df[assert_col] = np.nan

    # Set up the subjects of the assertions
    subj_item_col = f'{ds_anno.subject_field.field_num}_item'
    df.loc[filter_index, act_subj_col] = df[filter_index][subj_item_col]

    # This list of tuples defines which dataframe columns go with which
    # ds_anno attributes.
    node_col_attributes = [
        (act_obs_col, ds_anno.observation_field, ds_anno.observation,),
        (act_event_col, ds_anno.event_field, ds_anno.event,),
        (act_attrib_group_col, ds_anno.attribute_group_field, ds_anno.attribute_group,),
        (act_lang_col, ds_anno.language_field, ds_anno.language,),
    ]
    for df_node_col, ds_node_field, ds_node_obj in node_col_attributes:
        if ds_node_field:
            # Multiple node entities come from this node_field.
            # copy them in to the df_node_col
            field_item_col = f'{ds_node_field.field_num}_item'
            df.loc[filter_index, df_node_col] = df[filter_index][field_item_col]
            continue
        # The simple case, where the node is a single object, not 
        # multiple objects in a field. 
        # NOTE: this sets all values in the df_node_col to the same value.
        df.loc[filter_index, df_node_col] = str(ds_node_obj.uuid)
    
    if ds_anno.object_field and ds_anno.object_field.item_type == 'variables':
        # In this case assertion predicate will come from a 
        # ds_field of item_type = 'variables', and the objects will
        # come from an associated item_type = 'values' or 'types' field.
        var_val_anno = DataSourceAnnotation.objects.filter(
            data_source=ds_source,
            subject_field=ds_anno.object_field,
            predicate_id=configs.PREDICATE_RDFS_RANGE_UUID,
        ).first()
        if not var_val_anno:
            # We can't do a description in a variables field has no
            # associated values.
            return None
        des_pred_field = var_val_anno.subject_field
        des_pred_col = f'{des_pred_field.field_num}_item'
        df.loc[filter_index, act_pred_col] = df[filter_index][des_pred_col]
        # Get the columns for the assertion objects.
        df = update_df_object_column_for_ds_anno(
            var_val_anno, 
            df, 
            act_obj_col=act_obj_col, 
            act_obj_dt_col=act_obj_dt_col,
            filter_index=filter_index,
        )
    else:
        # This is a simpler case where assertion predicates come from the
        # context object of the ds_anno object field. The ds_anno object
        # field will have either literal or named entities as objects of
        # assertions.
        if (ds_anno.object_field 
            and ds_anno.object_field.context 
            and ds_anno.object_field.context.item_type in DataSourceAnnotation.PREDICATE_OK_ITEM_TYPES
        ):
            # NOTE: this sets all values in the act_pred_col to the same value.
            df.loc[filter_index, act_pred_col] = str(ds_anno.object_field.context.uuid)
        # Get the columns for the assertion objects.
        df = update_df_object_column_for_ds_anno(
            ds_anno, 
            df, 
            act_obj_col=act_obj_col, 
            act_obj_dt_col=act_obj_dt_col,
            filter_index=filter_index,
        )
    
    df_act = df[filter_index][assert_cols].copy()
    # Remove rows with null values, these can't have assertions.
    df_act.dropna(inplace=True)
    df_grp = df_act.groupby(assert_cols).first().reset_index()
    sort_denom = 10 * len(df_grp.index)

    t_now = time.time()
    if print_progress:
        print(
            f'Grouped unique values {(sort_denom / 10)} time: {(t_now - start)}'
        )

    if ds_anno.object_field:
        sort_start = ds_anno.object_field.field_num
    else:
        # Put this to the very end.
        sort_start = ds_source.field_count

    # Mappings between literal to note predicates.
    literal_to_note_preds = {}

    assert_uuids = []
    unsaved_assert_objs = []
    for i, row in df_grp.iterrows():
        # Start making a dict that includes most of the
        # assertion's attributes.
        raw_object_val = str(row[act_obj_col]).strip()
        act_data_type = str(row[act_obj_dt_col])

        if not raw_object_val:
            # We have a blank value, so skip.
            continue
        if not act_data_type:
            # We have a data type that is empty, skip.
            continue
        
        predicate_uuid = str(row[act_pred_col])
        if log_new_assertion:
            logger.info(f'Make assertion on: {predicate_uuid} {raw_object_val}')

        assert_dict = {
            'project': ds_source.project,
            'publisher': ds_source.project.publisher,
            'source_id': ds_source.source_id,
            'subject_id': str(row[act_subj_col]),
            'observation_id': str(row[act_obs_col]),
            'event_id': str(row[act_event_col]),
            'attribute_group_id': str(row[act_attrib_group_col]),
            'predicate_id': predicate_uuid,
            'sort': (sort_start + (i/sort_denom)),
            'language_id': str(row[act_lang_col]),
        }
        if act_data_type == 'id':
            # We're making an assertion where the object is a named
            # entity.
            assert_dict['object_id'] = raw_object_val
        else:
            # We're making an assertion where the object is a 
            # literal of some data_type.
            literal_done = False
            for lit_attrib, data_type in LITERAL_ATTRIBUTE_DATA_TYPES:
                if literal_done or act_data_type != data_type:
                    # The assertion is not about this data_type
                    continue
                # Convert the raw_object_val to an object value that
                # conforms to the expected data type.
                object_val = etl_utils.validate_transform_data_type_value(
                    raw_object_val, 
                    data_type
                )
                if object_val is not None:
                    # We have a literal value that is valid for this
                    # assertion. Add it.
                    assert_dict[lit_attrib] = object_val
                    literal_done = True
                    continue
                # We're in a sad situation where the raw_object_val cannot
                # be parsed into an object_value of the correct data type. So
                # we need to get or make a new predicate
                pred_note_obj = literal_to_note_preds.get(predicate_uuid)
                if invalid_literal_to_str and pred_note_obj is None:
                    # We don't have an object_val that is
                    # valid for this data type, so make a string
                    # literal assertion instead.
                    pred_note_obj = get_make_note_predicate_for_invalid_literal_db(
                        ds_source=ds_source, 
                        predicate_uuid=predicate_uuid, 
                        sort=ds_anno.object_field.field_num,
                        add_assoction_uuid=configs.PREDICATE_SKOS_RELATED_UUID,
                    )
                    literal_to_note_preds[predicate_uuid] = pred_note_obj
                if not pred_note_obj:
                    # We don't have a predicate note object, so skip.
                    continue

                if print_progress:
                    print(f'Using {pred_note_obj.label} for {raw_object_val}')
                assert_dict['predicate_id'] = str(pred_note_obj.uuid)
                assert_dict['obj_string'] = raw_object_val
                literal_done = True
        
        # Make a UUID keyword arg dict for making the assertion uuid.
        uuid_kargs = {k:assert_dict.get(k) for k in ASSERT_ID_ATTRIBUTES}
        assert_uuid = AllAssertion().primary_key_create(**uuid_kargs)
        assert_uuids.append(assert_uuid)
        assert_dict['uuid'] = assert_uuid
        assert_obj = AllAssertion(**assert_dict)
        unsaved_assert_objs.append(assert_obj)
        if log_new_assertion:
            logger.info(ass_obj)

    # Bulk save these assertions. This does a fallback to saving saving assertion
    # objects individually if something goes wrong, but that's far slower.
    trans_utils.bulk_create_assertions(
        assert_uuids, 
        unsaved_assert_objs
    )

    end = time.time()
    if print_progress:
        print(f'Assertion generation time: {(end - start)}')


def make_all_descriptive_assertions(
    ds_source, 
    df=None, 
    invalid_literal_to_str=True, 
    log_new_assertion=False,
    filter_index=None,
    ds_anno_index_limit=None,
):
    """Makes descriptive assertions on entities already reconciled in a data source"""
    if df is None:
        df = etl_df.db_make_dataframe_from_etl_data_source(
            ds_source,
            include_uuid_cols=True,
        )
    
    if filter_index is None:
        # No filter index set, so process the whole dataframe df
        filter_index = df['row_num'] >= 0

    ds_anno_qs =  DataSourceAnnotation.objects.filter(
        data_source=ds_source,
        subject_field__item_type__in=configs.OC_ITEM_TYPES,
        predicate_id=configs.PREDICATE_OC_ETL_DESCRIBED_BY,
    )

    count_anno_qs = len(ds_anno_qs)
    use_annos = ds_anno_qs
    if ds_anno_index_limit is not None:
        if ds_anno_index_limit >= count_anno_qs:
            # Skip out, we're don't have this index number.
            return count_anno_qs
        use_annos = [ds_anno_qs[ds_anno_index_limit]]

    for ds_anno in use_annos:
        # Makes descriptive assertions from fields that are related
        # by the configs.PREDICATE_OC_ETL_DESCRIBED_BY relationship.
        make_descriptive_assertions(
            ds_anno, 
            df, 
            invalid_literal_to_str=invalid_literal_to_str,
            log_new_assertion=log_new_assertion,
            filter_index=filter_index,
        )
    
    return count_anno_qs


def make_link_assertions(ds_anno, df, log_new_assertion=False, filter_index=None):
    """Makes linking assertions between named entities"""

    if filter_index is None:
        # No filter index set, so process the whole dataframe df
        filter_index = df['row_num'] >= 0

    ds_source = ds_anno.data_source
    act_subj_col = f'assertion_subject_uuid__{ds_source.source_id}'
    act_pred_col = f'assertion_predicate_uuid__{ds_source.source_id}'
    act_obs_col = f'assertion_obs_uuid__{ds_source.source_id}'
    act_event_col = f'assertion_event_uuid__{ds_source.source_id}'
    act_attrib_group_col = f'assertion_attribute_group_uuid__{ds_source.source_id}'
    act_lang_col = f'assertion_language_uuid__{ds_source.source_id}'
    act_obj_col = f'assertion_object__{ds_source.source_id}'

    assert_cols = [
        act_subj_col,
        act_pred_col,
        act_obs_col,
        act_event_col,
        act_attrib_group_col,
        act_lang_col,
        act_obj_col,
    ]

    for assert_col in assert_cols:
        df[assert_col] = np.nan

    # Set up the subjects of the assertions
    subj_item_col = f'{ds_anno.subject_field.field_num}_item'
    df.loc[filter_index, act_subj_col] = df[filter_index][subj_item_col]

    # This list of tuples defines which dataframe columns go with which
    # ds_anno attributes.
    col_attributes = [
        (act_obs_col, ds_anno.observation_field, ds_anno.observation,),
        (act_event_col, ds_anno.event_field, ds_anno.event,),
        (act_attrib_group_col, ds_anno.attribute_group_field, ds_anno.attribute_group,),
        (act_lang_col, ds_anno.language_field, ds_anno.language,),
        (act_pred_col, ds_anno.predicate_field, ds_anno.predicate,), 
        (act_obj_col, ds_anno.object_field, ds_anno.object,), 
    ]

    for df_col, ds_field, ds_obj in col_attributes:
        if ds_field:
            if ds_field.data_type != 'id':
                # Skip out, we're only dealing with named entities, no literals
                return None
            # Multiple node entities come from this ds_field.
            # copy them in to the df_col
            field_item_col = f'{ds_field.field_num}_item'
            df.loc[filter_index, df_col] = df[filter_index][field_item_col]
            continue
        # The simple case, where the node is a single object, not 
        # multiple objects in a field. 
        # NOTE: this sets all values in the df_col to the same value.
        if ds_obj and ds_obj.data_type != 'id':
            # Skip out, we're only dealing with named entities, no literals
            return None
        df.loc[filter_index, df_col] = str(ds_obj.uuid)
    
    df_act = df[filter_index][assert_cols].copy()
    # Remove rows with null values, these can't have assertions.
    df_act.dropna(inplace=True)
    df_grp = df_act.groupby(assert_cols).first().reset_index()
    sort_denom = 10 * len(df_grp.index)

    if ds_anno.predicate_field:
        sort_start = ds_anno.predicate_field.field_num
    elif ds_anno.object_field:
        sort_start = ds_anno.object_field.field_num
    else:
        # Put this to the very end.
        sort_start = ds_source.field_count * 2

    for i, row in df_grp.iterrows():
        # Start making a dict that includes most of the
        # assertion's attributes.
        object_uuid = str(row[act_obj_col])
        if not object_uuid:
            continue

        assert_dict = {
            'project': ds_source.project,
            'publisher': ds_source.project.publisher,
            'source_id': ds_source.source_id,
            'subject_id': str(row[act_subj_col]),
            'observation_id': str(row[act_obs_col]),
            'event_id': str(row[act_event_col]),
            'attribute_group_id': str(row[act_attrib_group_col]),
            'predicate_id': str(row[act_pred_col]),
            'sort': (sort_start + (i/sort_denom)),
            'language_id': str(row[act_lang_col]),
            'object_id': object_uuid,
        }
        
        # Make a UUID keyword arg dict for making the assertion uuid.
        uuid_kargs = {k:assert_dict.get(k) for k in ASSERT_ID_ATTRIBUTES}
        ass_obj, _ = AllAssertion.objects.get_or_create(
            uuid=AllAssertion().primary_key_create(**uuid_kargs),
            defaults=assert_dict
        )
        if log_new_assertion:
            logger.info(ass_obj)
    

def make_all_linking_assertions(
    ds_source, 
    df=None, 
    log_new_assertion=False, 
    filter_index=None,
    ds_anno_index_limit=None,
):
    """Makes linking assertions on entities already reconciled in a data source"""
    if df is None:
        df = etl_df.db_make_dataframe_from_etl_data_source(
            ds_source,
            include_uuid_cols=True,
        )

    if filter_index is None:
        # No filter index set, so process the whole dataframe df
        filter_index = df['row_num'] >= 0

    ds_anno_qs =  DataSourceAnnotation.objects.filter(
        data_source=ds_source,
        subject_field__item_type__in=configs.OC_ITEM_TYPES,
        subject_field__data_type__isnull=False,
    ).filter(
        # Make sure the object has a named entity, either a single
        # named entity (in the 'object' attribute, or a field with
        # multiple named entities, in the 'object_field' attribute.)
        Q(object__isnull=False)|Q(object_field__isnull=False)
    ).filter(
        # Make sure that the data type for the predicate or the 
        # predicate_field is 'id' for named entities.
        Q(predicate__data_type='id')|Q(predicate_field__data_type='id')
    ).exclude(
        predicate_id__in=LINKS_EXCLUDE_PREDICATE_IDS
    )

    count_anno_qs = len(ds_anno_qs)
    use_annos = ds_anno_qs
    if ds_anno_index_limit is not None:
        if ds_anno_index_limit >= count_anno_qs:
            # Skip out, we're don't have this index number.
            return count_anno_qs
        use_annos = [ds_anno_qs[ds_anno_index_limit]]

    for ds_anno in use_annos:
        # Makes link assertions from fields that are related
        # by the configs.PREDICATE_OC_ETL_DESCRIBED_BY relationship.
        make_link_assertions(
            ds_anno, 
            df, 
            log_new_assertion=log_new_assertion,
            filter_index=filter_index,
        )
    
    return count_anno_qs
