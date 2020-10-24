import os
import hashlib

import numpy as np
import pandas as pd

from opencontext_py.apps.all_items import configs
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
from opencontext_py.apps.etl.importer import autofields

"""
Testing:
from opencontext_py.apps.all_items.models import (
    AllManifest,
    AllAssertion,
)
from opencontext_py.apps.etl.importer.df import *

file_path = '/home/ekansa/github/datasets/pinar-bird-specimen-test.csv'
df = df_str_cols_load_csv(file_path)
project = AllManifest.objects.filter(item_type='projects').last()
ds_source = load_csv_for_etl(project, file_path, source_exists="replace")
df_etl = db_make_dataframe_from_etl_data_source(ds_source, use_column_labels=True)
"""


def db_make_dataframe_from_etl_data_source(
    ds_source, 
    include_uuid_cols=False, 
    use_column_labels=False
):
    """Makes a dataframe from the etl ds_source
    
    :param DataSource ds_source: A DataSource object that provides
        metadata about the data source for an ETL process.
    """

    # Start making the output datafame by adding of its columns.
    ds_fields_qs = DataSourceField.objects.filter(data_source=ds_source)
    data = {'row_num': [],}
    for df_field in ds_fields_qs:
        if include_uuid_cols:
            data[f'{df_field.field_num}_context'] = []
            data[f'{df_field.field_num}_item'] = []
        data[f'{df_field.field_num}_col'] = []

    df = pd.DataFrame(data=data)

    # Get the queryset of records for this data source.
    ds_recs_qs = DataSourceRecord.objects.filter(data_source=ds_source).iterator()
    prior_row_num = 1
    row_data = {}
    for ds_rec in ds_recs_qs:
        if ds_rec.row_num != prior_row_num:
            df = df.append(row_data, ignore_index=True)
            row_data = {}
            prior_row_num = ds_rec.row_num
        # Make a row dictionary.
        row_data['row_num'] = ds_rec.row_num
        if include_uuid_cols:
            context = ''
            item = ''
            if ds_rec.context:
                context = str(ds_rec.context.uuid)
            if ds_rec.item:
                item = str(ds_rec.item.uuid)
            row_data[f'{ds_rec.field_num}_context'] = context
            row_data[f'{ds_rec.field_num}_item'] = item
        row_data[f'{ds_rec.field_num}_col'] = ds_rec.record
    # Now add the final row.
    df = df.append(row_data, ignore_index=True)

    # We want to replace the numeric column names with corresponding
    # field labels.
    if use_column_labels:
        used_labels = []
        rename_cols = {}
        for df_field in ds_fields_qs:
            if df_field.label in used_labels:
                label = f'{df_field.label} [{df_field.field_num}]'
            else:
                label = df_field.label
            used_labels.append(df_field.label)
            rename_cols[f'{df_field.field_num}_col'] = label
        df.rename(columns=rename_cols, inplace=True) 
    return df


def df_str_cols_load_csv(file_path):
    """Imports a dataset from a CSV file"""
    if not os.path.exists(file_path):
        return None
    col_names = pd.read_csv(file_path, nrows=0).columns
    cols_to_str = {col:str for col in col_names}
    df = pd.read_csv(file_path, dtype=cols_to_str)
    return df


def map_cols_to_prior_fields(df, project, limit_prior_data_source=None):
    """Makes a dict mapping dataframe columns to fields in a project's prior data sources
    
    :param DataFrame df: A dataframe that we are currently preparing for ETL,
    :param AllManifest project: A manifest object for the project that we
        want to update via an ETL process.
    :param DataSource limit_prior_data_source: An ETL datasource object
        that is an optional limit to filters for looking matching fields
        between the df's columns and prior data sources.
    """
    if  limit_prior_data_source:
        added_filters = {"data_source": limit_prior_data_source}
    else:
        added_filters = None
    col_prior_fields = {
        col: autofields.get_matching_project_field_by_labels(
            project=project,
            label=col, 
            added_filters=added_filters,
        )
        for col in df.columns
    }
    return col_prior_fields


def save_data_source_for_df(df, project, source_id, label=None):
    """Create a datasource object from a dataframe for a project
    
    :param DataFrame df: A dataframe that we are currently preparing for ETL,
    :param AllManifest project: The project that is getting updated
        by this ETL process.
    :param str source_id: A string (maybe human meaningful) identifying the
        data source. This is not the primary key, but needs to be unique in
        the ETL datasource models.
    :param str label: A label to describe the data source.

    returns DataSource ds_source: Returns a data source object.
    """
    if not label:
        label = source_id
    new_dict = {
        "publisher": project.publisher,
        "project": project,
        "source_id": source_id,
        "label": label,
        "field_count": len(df.columns),
        "row_count": len(df.index),
        "source_type": "DataFrame",
        "meta_json": {
            "to_csv_sha256_hash": hashlib.sha256(df.to_csv().encode()).hexdigest()
        }
    }
    ds_source = DataSource.objects.create(
        **new_dict
    )
    return ds_source


def save_data_source_fields_for_df(df, ds_source, col_prior_fields):
    """Saves a datasource field objects for dataframe columns

    :param DataFrame df: A dataframe that we are currently preparing for ETL,
    :param DataSource ds_source: A DataSource object that provides
        metadata about the data source for an ETL process.
    :param dict col_prior_fields: A dictionary keyed by the df's
        column names with values of None or a DataSourceField that
        has been matched within this project.
    
    returns dict prior_to_new_fields: prior_to_new_fields is keyed
       by prior matching DataSourceFields with corresponding new
       DataSourceFields for this ds_source.
    """
    prior_to_new_fields = {}
    cols = df.columns.tolist()
    for field_num, col in enumerate(cols, start=1):
        new_dict = {
            'data_source': ds_source,
            'field_num': field_num,
            'label': col,
            'unique_count': len(df[col].unique()),
        }
        ds_new_field = DataSourceField.objects.create(**new_dict)
        prior_field = col_prior_fields.get(col)
        if not prior_field:
            continue
        # Copy the mapped prior field attributes to this new field.
        ds_new_field = autofields.copy_prior_project_field_attributes(
            ds_new_field, 
            prior_field
        )
        prior_to_new_fields[prior_field] = ds_new_field
    return prior_to_new_fields


def save_data_source_records_for_df(df, ds_source, chuck_size=50):
    """Saves a datasource field objects for dataframe columns

    :param DataFrame df: A dataframe that we are currently preparing for ETL,
    :param DataSource ds_source: A DataSource object that provides
        metadata about the data source for an ETL process.
    """
    # Fill null values with a blank string.
    df.fillna('', inplace=True)

    cols = df.columns.tolist()
    for df_chunk in np.array_split(df, chuck_size):
        data_source_records = []
        for i, row in df_chunk.iterrows():
            for field_num, col in enumerate(cols, start=1):
                record = str(row[col])
                if not record:
                    # Skip empty records. We should be able to handle
                    # these without clogging our DB with missing junk.
                    continue
                ds_rec = DataSourceRecord()
                ds_rec.uuid = DataSourceRecord().primary_key_create(
                    data_source_id=ds_source.uuid,
                    row_num=(i + 1),
                    field_num=field_num,
                )
                ds_rec.data_source = ds_source
                ds_rec.row_num = (i + 1)
                ds_rec.field_num = field_num
                ds_rec.record = record
                data_source_records.append(ds_rec)
        # Now bulk create the records in this chunk of rows.
        DataSourceRecord.objects.bulk_create(data_source_records)


def load_df_for_etl(
    df, 
    project, 
    prelim_source_id, 
    data_source_label=None, 
    source_exists="raise"
):
    
    col_prior_fields = {}
    prior_to_new_fields = None
    map_ready_field_annotations = None

    ds = DataSource.objects.filter(
        source_id=prelim_source_id
    ).first()
    if source_exists == "raise" and ds:
        raise ValueError(f'Already loaded data from {prelim_source_id}')
    elif source_exists == "replace" and ds and ds.project != project:
        raise ValueError(
            f'We cannot replace data from {prelim_source_id} because '
            f'it was imported into another project "{ds.project.label}", '
            f'uuid: {str(ds.project.uuid)} '
        )
    elif source_exists == "replace" and ds and ds.project == project:
        # We're replacing data from the same source into the same
        # project. This may happen if we discover an error, made some
        # edits to a file, and want to redo an ETL process.
        col_prior_fields = map_cols_to_prior_fields(
            df, 
            project, 
            limit_prior_data_source=ds,
        )
        # Make a mapping from the prior field to the column name in the new dataframe.
        prior_to_new_fields = {
            prior_field: col 
            for col, prior_field in col_prior_fields.items() if prior_field is not None
        }
        # NOTE: We're only looking these up if we're replacing a source within a project
        # because this helps to cache prior annotations prior to deleting them.
        map_ready_field_annotations = autofields.get_annotations_on_mapped_prior_fields(
            prior_to_new_fields
        )
        # Now that we have copied over related field attributes and annotations
        # we can safely delete the prior data source.
        DataSourceRecord.objects.filter(data_source=ds).delete()
        DataSourceAnnotation.objects.filter(data_source=ds).delete()
        DataSourceField.objects.filter(data_source=ds).delete()
        DataSource.objects.filter(uuid=ds.uuid).delete()
        source_id = prelim_source_id

    elif source_exists == "new" and ds:
        # The prelim_source_id exists, but we're treating this as 
        # new data source to load. So make a source id that
        # add an integer value to the prelim_source_id.
        col_prior_fields = map_cols_to_prior_fields(
            df, 
            project,
        )
        ds_check = ds
        i = 0
        while ds_check is not None:
            # Iterate through this until
            i += 1
            ds_count = DataSource.objects.filter(
                source_id__startswith=prelim_source_id
            ).count()
            source_id = f'{prelim_source_id}---{(ds_count + i)}'
            ds_check = DataSource.objects.filter(
                source_id=source_id
            ).first()
            if i > 10:
                raise ValueError(f'Too many {prelim_source_id} data sources!')
    else:
        # This prelim_source_id is new, so not conflicting with prior
        # ETL data sources.
        col_prior_fields = map_cols_to_prior_fields(
            df, 
            project,
        )
        source_id = prelim_source_id
    
    # Now make the new data source object.
    ds_source = save_data_source_for_df(
        df, 
        project, 
        source_id, 
        label=data_source_label
    )
    # Save data source fields for this dataframe, and update with any prior
    # matched fields. 
    prior_to_new_fields = save_data_source_fields_for_df(
        df, 
        ds_source, 
        col_prior_fields
    )
    # Save any field annotations from prior matched fields.
    autofields.copy_prior_annotations_to_new_datasource(
        prior_to_new_fields=prior_to_new_fields,
        map_ready_field_annotations=map_ready_field_annotations,
    )
    # Now finally, save all the records from the dataframe into
    # the DataSourceRecords table.
    save_data_source_records_for_df(df, ds_source)
    return ds_source


def load_csv_for_etl(project, file_path, data_source_label=None, source_exists="raise"):
    """Loads a csv file for an etl"""
    df = df_str_cols_load_csv(file_path)
    if df is None:
        # No data returned from loading the CSV.
        return None
    filename = os.path.basename(file_path)
    return load_df_for_etl(
        df=df,
        project=project, 
        prelim_source_id=filename, 
        data_source_label=data_source_label, 
        source_exists=source_exists
    )
