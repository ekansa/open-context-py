import numpy as np
import pandas as pd



from opencontext_py.apps.etl.importer.models import (
    DataSourceField,
    DataSourceAnnotation,
)

# ---------------------------------------------------------------------
# NOTE: These functions help to automatically prepopulate data source
# field attributes and annotations based on prior ETL configurations
# defined within the scope of a project
# ---------------------------------------------------------------------

def get_matching_project_field_by_labels(
    project,
    label, 
    ref_name=None, 
    ref_origin_name=None, 
    added_filters=None,
    added_excludes=None,
):
    """Gets a DataSourceField object by matching labels in projects
    
    :param AllManifest project: The project that is getting updated
        by this ETL process.
    :param str label: The label for the field that we're trying to
        match within the project.
    :param str ref_name: The most recent label for the field as stored 
        in Open Refine
    :param str ref_origin_name: The original label for the field as
        first imported into Open Refine.
    :param dict added_fileters: A dictionary of optional additional
        filters to use in limiting the query set for a match.
    :param dict added_excludes: A dictionary of optional additional
        filters to use in limiting the query set for a match.
    """
    # Make a project query-set of data source fields from this project
    projs_qs = DataSourceField.objects.filter(
        data_source__project=project
    )
    if isinstance(added_filters, dict):
        projs_qs = projs_qs.filter(**added_filters)
    prior_field = projs_qs.filter(
        label=label
    ).order_by('-updated').first()
    if prior_field:
        return prior_field
    if ref_name:
        prior_field = projs_qs.filter(
            ref_name=ref_name
        ).order_by('-updated').first()
    if prior_field:
        return prior_field
    if ref_origin_name:
        prior_field = projs_qs.filter(
            ref_origin_name=ref_origin_name
        ).order_by('-updated').first()
    if prior_field:
        return prior_field
    return None



def get_matching_project_field(ds_new_field):
    """Gets a DataSourceField object by matching labels in projects
    
    :param DataSourceField ds_new_field: The new data source field 
        that we want to match with a prior data source field already
        defined in this project.
    """
    # If we have some attribute data already assigned to the
    # ds_new_field, we can use that to be more specific in finding
    # matches from prior data source fields.
    added_filters = {}
    poss_filters = ['item_type', 'data_type', 'item_class']
    for poss_filter in poss_filters:
        filter_val = getattr(ds_new_field, poss_filter)
        if not filter_val:
            continue
        added_filters[poss_filter] = filter_val
    
    if not added_filters:
        added_filters = None

    return get_matching_project_field_by_labels(
        project=ds_new_field.data_source.project,
        label=ds_new_field.label, 
        ref_name=ds_new_field.ref_name, 
        ref_origin_name=ds_new_field.ref_origin_name, 
        added_filters=added_filters,
        # NOTE: the added_excludes makes sure that we match data source
        # fields from a different datasource within this project.
        added_excludes={'data_source': ds_new_field.data_source},
    )


def copy_prior_project_field_attributes(ds_new_field, prior_field):
    """Copies attributes from a field in the same project """
    # Copy certain attributes from the a field, defined
    # within this project.  
    ds_new_field.label = prior_field.label
    ds_new_field.item_type = prior_field.item_type
    ds_new_field.data_type = prior_field.data_type
    ds_new_field.item_class = prior_field.item_class
    ds_new_field.value_prefix = prior_field.value_prefix
    ds_new_field.meta_json['prior_field_id'] = str(prior_field.uuid)
    ds_new_field.save()
    return ds_new_field


def get_annotations_on_mapped_prior_fields(prior_to_new_fields):
    """Gets lists of DataSourceAnnotation for each prior_field in prior_to_new_fields

    :param dict prior_to_new_fields: A dictionary keyed by a prior_field
       object that has a mapping to a new data source field
    
    returns a dictionary keyed by prior_field objects that lists
        DataSourceAnnotation objects that can be mapped to a
        new DataSource
    """
    map_ready_field_annotations = {
        prior_field: [] 
        for prior_field, _ in prior_to_new_fields.items()
    }
    for prior_field, _ in prior_to_new_fields.items():
        f_annotations_qs = DataSourceAnnotation.objects.filter(
            subject_field=prior_field,
        )
        for act_anno in f_annotations_qs:
            ok_to_add = True
            for field_attrib in DataSourceAnnotation.FIELD_ATTRIBUTE_LIST:
                # Get the attribute field from the act_anno
                # This can be None.
                act_field_obj = getattr(act_anno, field_attrib)
                if not act_field_obj or act_field_obj in prior_to_new_fields:
                    # This act_field_obj is either None or is in our
                    # mapping between prior and new fields. So continue
                    # to check
                    continue
                # The act_anno has a relationship to a field that
                # has NO mapping between prior and new fields, so it is 
                # NOT ok to add
                ok_to_add = False
                break
            if not ok_to_add:
                continue
            map_ready_field_annotations[prior_field].append(act_anno)
    return map_ready_field_annotations


def copy_prior_annotations_to_new_datasource(
    prior_to_new_fields, 
    map_ready_field_annotations=None
):
    """Map and copies prior annotations on fields mapped to fields in a new data source"""
    if not prior_to_new_fields:
        return None
    
    if not map_ready_field_annotations:
        # We haven't already made a dictionary of annotations that
        # are OK for mapping.
        map_ready_field_annotations = get_annotations_on_mapped_prior_fields(
            prior_to_new_fields
        )

    new_annotations = []
    for prior_field, prior_annotations in map_ready_field_annotations.items():
        ds_new_field = prior_to_new_fields.get(prior_field)
        if not ds_new_field:
            # This is weird, but we don't have a mapping to a new field.
            continue
        if not prior_annotations:
            continue
        for prior_anno in prior_annotations:
            ok_to_add = True
            new_dict = {
                'data_source': ds_new_field.data_source,
                'subject_field': ds_new_field,
                'predicate': prior_anno.predicate,
                'object': prior_anno.object,
                'obj_string': prior_anno.obj_string,
                'obj_boolean': prior_anno.obj_boolean,
                'obj_integer': prior_anno.obj_integer,
                'obj_double': prior_anno.obj_double,
                'obj_datetime':  prior_anno.obj_datetime,
                'observation': prior_anno.observation,
                'event': prior_anno.event,
                'attribute_group': prior_anno.attribute_group,
                'language': prior_anno.language,
                'meta_json': {'prior_annotation_id': str(prior_anno.uuid)}
            }
            for field_attrib in DataSourceAnnotation.FIELD_ATTRIBUTE_LIST:
                # Get the attribute field from the act_anno
                # This can be None.
                act_field_obj = getattr(prior_anno, field_attrib)
                if not act_field_obj:
                    # The field attribute has a null value.
                    new_dict[field_attrib] = None
                    continue
                ds_new_mapped_field_obj = prior_to_new_fields.get(act_field_obj)
                if not ds_new_mapped_field_obj:
                    # Something is wrong, we have a reference to a field
                    # that has no mapping to the new data source.
                    ok_to_add = False
                    continue
                if ds_new_mapped_field_obj.data_source != ds_new_field.data_source:
                    # We can only make data source field annotations if all
                    # the fields are for the same data source.
                    ok_to_add = False
                    continue
                new_dict[field_attrib] = ds_new_mapped_field_obj
            if not ok_to_add:
                # Skip saving this mapped field annotation.
                continue
            new_anno, _ = DataSourceAnnotation.objects.get_or_create(
                **new_dict
            )
            new_annotations.append(new_anno)
    return new_annotations


def copy_prior_project_fields_for_data_source(ds_source, copy_annotations=True):
    """Copies attributes from a field in the same project """
    df_new_field_qs = DataSourceField.objects.filter(
        data_source=ds_source
    )
    prior_to_new_fields = {}
    for ds_new_field in df_new_field_qs:
        prior_field = get_matching_project_field(ds_new_field)
        if not prior_field:
            continue
        # Now copy the attributes made on the prior field to the
        # ds_new_field.
        ds_new_field = copy_prior_project_field_attributes(
            ds_new_field, 
            prior_field
        )
        prior_to_new_fields[prior_field] = ds_new_field

    if not copy_annotations:
        return None
    
    # Now copy the mapped prior to new datasource field annotations.
    copy_prior_annotations_to_new_datasource(prior_to_new_fields)



