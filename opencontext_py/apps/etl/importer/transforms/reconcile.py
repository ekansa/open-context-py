import logging

import numpy as np
import pandas as pd

from unidecode import unidecode

from django.db.models import Q
from django.template.defaultfilters import slugify

from opencontext_py.apps.all_items import configs
from opencontext_py.apps.all_items.models import (
    AllManifest,
)

from opencontext_py.apps.etl.importer.models import (
    DataSourceRecord,
    DataSourceAnnotation,
)

from opencontext_py.apps.all_items.legacy_all import is_valid_uuid

from opencontext_py.apps.etl.importer import df as etl_df


logger = logging.getLogger("etl-importer-logger")



# ---------------------------------------------------------------------
# NOTE: These functions manage general entity reconciliation
# ---------------------------------------------------------------------
def get_or_create_single_predicate_manifest_entity(
    ds_source,
    label,
    sort=100,
    item_class_id=configs.CLASS_OC_LINKS_UUID,
    data_type='id',
    new_uuid=None,
):
    """Gets or creates a predicate manifest entity after reconciliation"""

    # NOTE: This is usually for making predicates used for linking
    # relationships, which is why the item_class_id defaults to a
    # linking relationship item class.

    # Limit the projects in which we will search for matching spatial items
    # for this col_record
    reconcile_project_ids = [
        configs.OPEN_CONTEXT_PROJ_UUID, 
        str(ds_source.project.uuid), 
        str(ds_source.project.project.uuid),
    ]

    label = AllManifest().clean_label(label)

    man_qs = AllManifest.objects.filter(
        project_id__in=reconcile_project_ids,
        item_type='predicates',
        item_class_id=item_class_id,
        data_type=data_type,
        label=label,
    )
    if new_uuid:
        man_qs = man_qs.filter(uuid=new_uuid)

    # Now handle the results where of our query to attempt to
    # find matching records for this specific item.
    made_new = False
    num_matching = len(man_qs)
    if num_matching == 1:
        # We have found exactly one match for this, meaning this
        # entity already exists so return it
        return man_qs[0], made_new, num_matching
    elif num_matching > 1:
        # Too many items found, meaning our reconciliation filters where too
        # permissive.
        return None, made_new, num_matching

    # Make a new Manifest item
    man_dict = {
        'publisher': ds_source.publisher,
        'project': ds_source.project,
        'source_id': ds_source.source_id,
        'item_type': 'predicates',
        'item_class_id': item_class_id,
        'data_type': data_type,
        'label': label,
        'context': ds_source.project,
        'meta_json': {'sort': sort, },
    }
    if new_uuid:
        # Use a specified uuid for this new item.
        man_dict['uuid'] = new_uuid

    try:
        item_obj = AllManifest(**man_dict)
        item_obj.save()
        made_new = True
    except:
        item_obj = None
        made_new = False
    return item_obj, made_new, 0


def get_ds_field_context(ds_field, context=None):
    """Gets the context for a ds_field, from specific to more general prioritization"""
    if context:
        # The context object is already defined, so just return that.
        return context
    if ds_field.context:
        # The field has a context object defined for it, so return that.
        return ds_field.context
    # If all else fails, return the default most general context which is
    # the project that we're importing into.
    return ds_field.data_source.project


def ensure_ok_item_class_for_item_type(ds_field, context, record_item_class=None):
    """Makes sure the item_type and item_class are OK"""
    item_type = ds_field.item_type
    if (
        record_item_class is None
        and ds_field.item_class
        and str(ds_field.item_class.uuid) != configs.DEFAULT_CLASS_UUID
    ):
        record_item_class = ds_field.item_class

    if not ds_field.item_type in ['predicates', 'types']:
        return item_type, record_item_class

    if (
        ds_field.data_type == 'id'
        and context.item_type == 'predicates'
        and (
            (str(context.item_class.uuid) == configs.CLASS_OC_VARIABLES_UUID)
            or (
                ds_field.item_class
                and
                str(ds_field.item_class.uuid) == configs.CLASS_OC_VARIABLES_UUID
            )
        )
    ):
        # The ds_field has a predicates context, and that context is
        # a variable, meaning it has types items as values.
        item_type = 'types'
        record_item_class = AllManifest.objects.filter(
            uuid=configs.DEFAULT_CLASS_UUID
        ).first()
        return item_type, record_item_class

    if (ds_field.item_type == 'predicates'
        and (
            not record_item_class
            or
            str(record_item_class.uuid) not in configs.CLASS_LIST_OC_PREDICATES
        )
    ):
        # We are attempting to reconcile an item_type = 'predicates'
        # item, but we don't have a correct record_item_class set. So
        # default to the class for a variable (not a link)
        record_item_class = AllManifest.objects.filter(
            uuid=configs.CLASS_OC_VARIABLES_UUID
        ).first()
    return item_type, record_item_class



def get_or_create_manifest_entity(
    ds_field,
    context,
    raw_column_record,
    record_item_class=None,
    record_uuid=None,
    record_other_id=None,
):
    """Gets or creates a manifest entity after reconciliation"""

    # Limit the projects in which we will search for matching spatial items
    # for this col_record
    reconcile_project_ids = ds_field.meta_json.get(
        'reconcile_project_ids',
        [
            configs.OPEN_CONTEXT_PROJ_UUID, 
            str(ds_field.data_source.project.uuid), 
            str(ds_field.data_source.project.project.uuid),
        ]
    )
    context = get_ds_field_context(ds_field, context)
    if ds_field.item_type == 'subjects' and context.item_type == 'projects':
        # We are only trying to reconcile by a project, we lack a
        # parent spatial context for item in this ds_field.
        reconcile_project_ids.append(context.uuid)
        context = None

    item_type, record_item_class = ensure_ok_item_class_for_item_type(
        ds_field,
        context,
        record_item_class
    )

    # Pass in a slug identifier to use to identify an item.
    slug_check = slugify(unidecode(str(raw_column_record)))
    if str(raw_column_record) != slug_check:
        # The raw_column_record is not a slug.
        slug_check = None

    # Prepare the item label.
    item_label = str(raw_column_record)
    if ds_field.value_prefix:
        item_label = ds_field.value_prefix + raw_column_record
    item_label = AllManifest().clean_label(item_label, item_type=item_type)

    man_qs = AllManifest.objects.filter(
        project_id__in=reconcile_project_ids,
        item_type=item_type,
        data_type=ds_field.data_type,
    )
    # If we're passing a UUID argument, use it!
    if record_uuid:
        # resets, so we skip project id filters.
        man_qs = AllManifest.objects.filter(
            uuid=record_uuid,
            item_type=item_type,
            data_type=ds_field.data_type,
        )

    if record_other_id:
        record_uri = AllManifest().clean_uri(record_other_id)
        man_qs = man_qs.filter(Q(uri=record_uri)|Q(slug=record_other_id))

    # Limit by context if we don't know the uuid
    if context and not record_uuid and not record_other_id:
        man_qs = man_qs.filter(context=context)

    # Limit by item_class if we don't know the uuid
    if record_item_class and not record_uuid:
        man_qs = man_qs.filter(item_class=record_item_class)

    if ds_field.item_type in configs.URI_CONTEXT_PREFIX_ITEM_TYPES:
        # Some flexibility in reconcile these.
        man_qs = man_qs.filter(
            Q(uri=AllManifest().clean_uri(raw_column_record))
            | Q(item_key=raw_column_record)
            | Q(label=item_label)
        )
    elif ds_field.item_type == 'persons' and ds_field.meta_json.get('reconcile_on_initials'):
        # We're allowing reconciliation on initials.
        man_qs = man_qs.filter(
            Q(meta_json__initials=item_label)
            | Q(meta_json__combined_name=item_label)
            | Q(label=item_label)
        )
    elif ds_field.item_type == 'persons' and not ds_field.meta_json.get('reconcile_on_initials'):
        # We're reconciling a persons item, but not with initials.
        man_qs = man_qs.filter(
            Q(meta_json__combined_name=item_label)
            | Q(label=item_label)
        )
    elif slug_check:
        man_qs = man_qs.filter(
            Q(slug=slug_check)
            | Q(label=item_label)
        )
    else:
        # Use the label as the main identifier (obviously with other
        # filter to contextualize)
        man_qs = man_qs.filter(label=item_label)

    more_filter_args = ds_field.meta_json.get('reconcile_filter_args')
    more_exclude_args = ds_field.meta_json.get('reconcile_exclude_args')
    if more_filter_args:
        man_qs = man_qs.filter(**more_filter_args)
    if more_exclude_args:
        man_qs = man_qs.exclude(**more_exclude_args)

    # Now handle the results where of our query to attempt to
    # find matching records for this specific item.
    made_new = False
    num_matching = len(man_qs)
    if num_matching == 1:
        # We have found exactly one match for this, meaning this
        # entity already exists so return it
        return man_qs[0], made_new, num_matching
    elif num_matching > 1:
        # Too many items found, meaning our reconciliation filters where too
        # permissive.
        return None, made_new, num_matching
    if num_matching == 0 and context is None:
        # We didn't find a match, but we lack the context to mint
        # a new item. This is likely a result of a subjects item that
        # we tried to match, but we lack context to assign it.
        logger.info(f'NEED CONTEXT to make {item_type}: {item_label}')
        return None, made_new, 0

    if context and context.item_type != 'subjects' and item_type == 'subjects':
        # We can't make a new subjects item if the context doesn't
        # exist or if it is not a subjects item type
        logger.info(f'NEED subjects CONTEXT to make {item_type}: {item_label}')
        return None, made_new, 0

    # Make a new Manifest item
    man_dict = {
        'publisher': ds_field.data_source.publisher,
        'project': ds_field.data_source.project,
        'source_id': ds_field.data_source.source_id,
        'item_type': item_type,
        'data_type': ds_field.data_type,
        'label': item_label,
        'context': context,
    }
    if record_uuid:
        man_dict['uuid'] = record_uuid
    if record_item_class:
        man_dict['item_class'] = record_item_class
    if ds_field.item_type == 'predicates':
        man_dict['meta_json'] = {
            'sort': ds_field.field_num,
        }

    try:
        item_obj = AllManifest(**man_dict)
        item_obj.save()
        made_new = True
    except Exception as e:
        item_obj = None
        made_new = False
        print(f'Failed to make new manifest item: {str(man_dict)}')
        print(f'Exception: {str(e)}')
    return item_obj, made_new, 0



def get_predicate_list_subject_is_super_objects(only_spatial_contains, only_variable_range=False):
    """Gets a list of predicates where the subject is super (parent) of objects"""
    if only_spatial_contains:
        return [configs.PREDICATE_CONTAINS_UUID]
    if only_variable_range:
        return [configs.PREDICATE_RDFS_RANGE_UUID]
    return (
        configs.PREDICATE_LIST_SBJ_IS_SUPER_OF_OBJ
        + configs.PREDICTATE_LIST_CONTEXT_SBJ_IS_SUPER_OF_OBJ
        # This is for field type variable -> value annotations.
        + [configs.PREDICATE_RDFS_RANGE_UUID]
    )

def get_immediate_parent_field_objs_db(child_field_obj):
    """Get the immediate parents of a child ds_field object using DB"""
    only_spatial_contains = False
    only_variable_range = False
    if child_field_obj.item_type == 'subjects':
        only_spatial_contains = True

    if child_field_obj.item_type in ['types', 'values']:
        only_variable_range = True

    pred_list_sbj_is_super_obj = get_predicate_list_subject_is_super_objects(
        only_spatial_contains, only_variable_range
    )
    subj_super_qs = DataSourceAnnotation.objects.filter(
        object_field=child_field_obj,
        predicate_id__in=pred_list_sbj_is_super_obj,
        object_field__data_type='id',
    )
    all_parents = [a.subject_field for a in subj_super_qs]

    if only_spatial_contains or only_variable_range:
        # Our work is done, spatial containment hierarchies are defined in
        # only one direction. Same with relations to variable fields.
        return all_parents

    subj_subord_qs = DataSourceAnnotation.objects.filter(
        subject_field=child_field_obj,
        predicate_id__in=configs.PREDICATE_LIST_SBJ_IS_SUBORD_OF_OBJ,
        subject_field__data_type='id',
    ).exclude(
        object_field=None
    )
    all_parents += [a.object_field for a in subj_subord_qs if a.object_field not in all_parents]
    return all_parents


def get_immediate_child_field_objs_db(parent_field_obj):
    """Get the immediate children fields of a parent field object using DB"""

    only_spatial_contains = False
    only_variable_range = False
    if parent_field_obj.item_type == 'subjects':
        only_spatial_contains = True

    if parent_field_obj.item_type in ['variables', 'predicates']:
        only_variable_range = True

    # item_type subjects only have 1 possible kind of hierarchy relation
    # that we care about in this function.
    pred_list_sbj_is_super_obj = get_predicate_list_subject_is_super_objects(
        only_spatial_contains, only_variable_range
    )

    subj_super_qs = DataSourceAnnotation.objects.filter(
        subject_field=parent_field_obj,
        predicate_id__in=pred_list_sbj_is_super_obj,
        object_field__data_type='id',
    ).exclude(
        object_field=None,
    )
    all_children = [a.object_field for a in subj_super_qs]
    if only_spatial_contains or only_variable_range:
        # Our work is done! Spatial hierarchy only works in one direction, with
        # a subject_field as parent of a child object_field.
        # Similarly with variables fields.
        return all_children

    # When item_type is not "subjects", there may be cases where the subject_field
    # is a child of a parent object_field. Query for that below.
    subj_subord_qs = DataSourceAnnotation.objects.filter(
        object_field=parent_field_obj,
        predicate_id__in=configs.PREDICATE_LIST_SBJ_IS_SUBORD_OF_OBJ,
        subject_field__data_type='id',
    )
    all_children += [a.subject_field for a in subj_subord_qs if a.subject_field not in all_children]
    return all_children


def df_reconcile_id_field(
    df,
    ds_field,
    context=None,
    col_record_tuples=None,
    do_recursive=True,
    filter_index=None,
    ):
    """Reconciles a data_type = 'id' field, walking down a hierarchy if hierarchic.

    :param DataFrame df: A dataframe that we are currently preparing for ETL. This
        df may be limited to the fields specifically involved in entity reconciliation.
    :param DataSourceField ds_field: A DataSourceField object that has attributes
        and possible annotations (in the DataSourceAnnotations model) that configure
        entity reconciliation for associated records in DataSourceRecords.
    :param AllManifest context: An AllManifest object that provides context in which
        entity reconciliation is scoped. For item_type = 'subjects', this would be the
        containing (parent) spatial context.
    :param list col_record_types: A list of tuples, where each tuple has two elements.
        The first tuple element is a dataframe column name and the second tuple element
        is the value used to filter the dataframe df to select records for entity
        reconciliation. This list gets longer as we progress down a hierarchy of nested
        fields.
    :param bool do_recursive: A flag to continue this function recursively by looking
        up child fields for continued entity reconciliation.
    """
    context = get_ds_field_context(ds_field, context)
    # Set up the filter index for the dataframe so as to
    if col_record_tuples is None:
        col_record_tuples = []

    if filter_index is None:
        filter_index = df['row_num'] >= 0

    current_index = filter_index
    for index_col, index_col_record in col_record_tuples:
        current_index &= (df[index_col] == index_col_record)

    # Check to see if the ds_field has a uuid field.
    col_uuid = None
    ds_anno_uuid =  DataSourceAnnotation.objects.filter(
        subject_field=ds_field,
        predicate_id=configs.PREDICATE_OC_ETL_DESCRIBED_BY,
        object_field__item_type='uuid'
    ).first()
    if ds_anno_uuid:
        col_uuid = f'{ds_anno_uuid.object_field.field_num}_col'

    # Check to se if the ds_field has a URI field id.
    col_other_id = None
    ds_anno_other_id =  DataSourceAnnotation.objects.filter(
        subject_field=ds_field,
        predicate_id=configs.PREDICATE_OC_ETL_DESCRIBED_BY,
        object_field__item_type__in=['uri'],
    ).first()
    if ds_anno_other_id:
        col_other_id = f'{ds_anno_other_id.object_field.field_num}_col'


    col_context = f'{ds_field.field_num}_context'
    col_item =  f'{ds_field.field_num}_item'
    col = f'{ds_field.field_num}_col'

    df.loc[current_index, col_context] = str(context.uuid)

    if do_recursive:
        # Get immediate child field objects.
        child_field_objs = get_immediate_child_field_objs_db(ds_field)
    else:
        # An empty list, so don't try to get the next children down.
        child_field_objs = []

    done_rec_uuid_tups = []
    # Now iterate through all the record values within the column
    # as subsetted by the current index.
    # NOTE: Because of the possibility that a raw_column_record maybe
    # associated with a UUID, we need to iterate through all the rows
    # so as to maintain the association between raw_column_record and
    # UUID.
    for _, row in  df[current_index].iterrows():
        raw_column_record = row[col]
        record_uuid = None
        record_other_id = None
        if col_uuid:
            record_uuid = is_valid_uuid(row[col_uuid])
        if col_other_id and row[col_other_id]:
            record_other_id = row[col_other_id]
        act_index = current_index & (df[col] == raw_column_record)
        if record_uuid:
            act_index &= (df[col_uuid] == row[col_uuid])
        if record_other_id:
            act_index &= (df[col_other_id] == row[col_other_id])
        act_rec_uuid_tup = (raw_column_record, record_uuid, record_other_id,)
        if act_rec_uuid_tup in done_rec_uuid_tups:
            # We've already done this combination of raw_column_record and
            # record uuid, so continue to the next one.
            continue
        done_rec_uuid_tups.append(act_rec_uuid_tup)
        item_obj = None
        if raw_column_record:
            item_obj, made_new, num_matching = get_or_create_manifest_entity(
                ds_field,
                context,
                raw_column_record,
                record_uuid=record_uuid,
                record_other_id=record_other_id,
            )
            if not item_obj:
                logger.info(
                    f'Could not reconcile or create "{raw_column_record}" '
                    f'in context {context.label} {context.uuid} '
                    f'from {ds_field.label} (field_num: {ds_field.field_num}) '
                    f'{made_new} num_matching: {num_matching}'
                )
        if item_obj:
            df.loc[act_index, col_item] = str(item_obj.uuid)
            for rows in etl_df.chunk_list(df[act_index]['row_num'].unique().tolist()):
                # Update the context and the item fields form this ds_field.
                # Storing these data will let us make assertions about the
                # item_obj that we just created or reconciled.
                DataSourceRecord.objects.filter(
                    data_source=ds_field.data_source,
                    field_num=ds_field.field_num,
                    row_num__in=rows,
                ).update(
                    context=context,
                    item=item_obj,
                )

        # Now iterate through all the child fields for this current ds_field.
        for child_field_obj in child_field_objs:
            # The default next_context is None, but the conditionals below may
            # specify a next_context (a manifest object)
            next_context = None
            if child_field_obj.item_type in ['subjects', 'types']:
                if item_obj and item_obj.item_type in ['subjects', 'predicates']:
                    # The child field is for a subject or a type, which means that
                    # it is reconciled within a specific context. Item_type =
                    # 'subjects' get reconciled within the context of another
                    # item_type subjects context. Item_types = 'types' get reconciled
                    # within the context of an item_type = 'predicates' context.
                    next_context = item_obj
                elif (
                        ds_field.item_type in ['subjects', 'predicates',]
                        and context.item_type in ['subjects', 'predicates']
                    ):
                    # We don't have an item_obj, so use the current context to
                    # carry down to be the context for the next level down
                    # in the hierarchy of ds_fields.
                    next_context = context
            # Now process the items down in this next child field. We add the
            # col, raw_column_record to the filters so that the df is further filtered
            # at next level down the hierarchy.
            df = df_reconcile_id_field(
                df=df,
                ds_field=child_field_obj,
                context=next_context,
                col_record_tuples=(col_record_tuples + [(col, raw_column_record,)])
            )
    return df
