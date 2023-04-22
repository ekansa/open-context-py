import os
import hashlib
import time

import numpy as np
import pandas as pd


from opencontext_py.apps.all_items.models import (
    AllManifest,
)
from opencontext_py.apps.etl.importer.models import (
    DataSource,
    DataSourceField,
    DataSourceRecord,
    DataSourceAnnotation,
)
from opencontext_py.apps.etl.importer import autofields

# ---------------------------------------------------------------------
# NOTE: These functions provide a means to load data into our ETL
# workflow from CSV data sources using Pandas. It also provides a
# function to read data already loaded into the ETL related models
# for expression as a Pandas Dataframe.
# ---------------------------------------------------------------------

"""
Testing:
from opencontext_py.apps.all_items.models import (
    AllManifest,
    AllAssertion,
)
from opencontext_py.apps.etl.importer.df import *
file_path = '/home/ekansa/github/datasets/naga-ed-deir-csv.csv'
file_path = '/home/ekansa/github/datasets/pinar-bird-specimen-test.csv'
df = df_str_cols_load_csv(file_path)
project = AllManifest.objects.filter(item_type='projects').last()
ds_source = load_csv_for_etl(file_path, project=project, source_exists="replace")
df_etl = db_make_dataframe_from_etl_data_source(ds_source, use_column_labels=True)
"""

# How many rows will we update in 1 database query?
DB_ROW_UPDATE_CHUNK_SIZE = 100


def chunk_list(list_name, n=DB_ROW_UPDATE_CHUNK_SIZE):
    """Breaks a long list into chunks of size n"""
    for i in range(0, len(list_name), n):
        yield list_name[i:i + n]


def db_make_dataframe_from_etl_data_source(
    ds_source,
    include_uuid_cols=False,
    include_error_cols=False,
    use_column_labels=False,
    limit_field_num_list=None,
    limit_row_num_start=None,
    limit_row_num_last=None,
    limit_row_count=None,
    limit_row_num_list=None,
    exclude_row_list=None,
):
    """Makes a dataframe from the etl ds_source

    :param DataSource ds_source: A DataSource object that provides
        metadata about the data source for an ETL process.
    """

    start = time.time()

    # Start making the output datafame by adding of its columns.
    ds_fields_qs = DataSourceField.objects.filter(data_source=ds_source)
    if limit_field_num_list:
        # We're limiting the query set to a list of field_nums.
        ds_fields_qs = ds_fields_qs.filter(field_num__in=limit_field_num_list)

    data = {'row_num': [],}
    for df_field in ds_fields_qs:
        if include_uuid_cols:
            data[f'{df_field.field_num}_context'] = []
            data[f'{df_field.field_num}_item'] = []
        data[f'{df_field.field_num}_col'] = []

    df = pd.DataFrame(data=data)

    # Get the queryset of records for this data source.
    ds_recs_qs = DataSourceRecord.objects.filter(data_source=ds_source)

    if limit_field_num_list:
        # We're limiting the query set to a list of field_nums.
        ds_recs_qs = ds_recs_qs.filter(field_num__in=limit_field_num_list)

    if limit_row_num_start is not None and limit_row_count is not None:
        # We're limiting the query set a range of rows.
        ds_recs_qs = ds_recs_qs.filter(
            row_num__gte=limit_row_num_start,
            row_num__lt=(limit_row_num_start + limit_row_count),
        )

    if limit_row_num_start is not None and limit_row_num_last is not None:
        # We're limiting the query set a range of rows.
        ds_recs_qs = ds_recs_qs.filter(
            row_num__gte=limit_row_num_start,
            row_num__lte=limit_row_num_last,
        )

    if limit_row_num_list is not None:
        # We're limiting the query set a list of row numbers.
        ds_recs_qs = ds_recs_qs.filter(
            row_num__in=limit_row_num_list,
        )

    if exclude_row_list is not None:
        ds_recs_qs = ds_recs_qs.exclude(
            row_num__in=exclude_row_list,
        )

    ds_recs_qs = ds_recs_qs.select_related(
        'context'
    ).select_related(
        'item'
    )

    # NOTE: We make a list, all_rows, that will have a row_data dict
    # for each row we want to add to the dataframe. Making a dataframe
    # from a list (all_rows) is about 30x faster than appending each
    # individual row_data dict directly to the dataframe
    all_rows = []
    row_data = {}
    prior_row_num = 1
    for ds_rec in ds_recs_qs.iterator():
        if ds_rec.row_num != prior_row_num:
            all_rows.append(row_data)
            row_data = {}
            prior_row_num = ds_rec.row_num
        # Make a row dictionary.
        row_data['row_num'] = ds_rec.row_num
        if include_uuid_cols:
            context = None
            item = None
            if ds_rec.context:
                context = str(ds_rec.context.uuid)
            if ds_rec.item:
                item = str(ds_rec.item.uuid)
            row_data[f'{ds_rec.field_num}_context'] = context
            row_data[f'{ds_rec.field_num}_item'] = item
        if include_error_cols:
            row_data[f'{ds_rec.field_num}_reconcile_errors'] = None
        row_data[f'{ds_rec.field_num}_col'] = ds_rec.record
    # Now add the final row.
    all_rows.append(row_data)
    df_all_rows = pd.DataFrame(data=all_rows)
    # Append the all_rows list all at once for a major speed boost.
    df = pd.concat([df, df_all_rows], ignore_index=True)

    # Fill na with empty strings for missing records.
    for df_field in ds_fields_qs:
        df[f'{df_field.field_num}_col'].fillna('', inplace=True)

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

    end = time.time()
    print(f'df generation time: {(end - start)}')
    return df


def df_str_cols_load_csv(file_path):
    """Creates a dataframe with all string datatype columns from a CSV file

    :param str file_path: The file path to a CSV file that will be read into
        a dataframe for ingest in an ETL process.
    """
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
            # The ref_name can help match the original column name
            # should we have changed the label of a field while preparing
            # an ETL process.
            'ref_name': col,
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
                # We store each cell value as a string in the
                # DataSourceRecord model.
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
    """Loads a DataFrame into the ETL related database models

    :param DataFrame df: A dataframe that we are currently preparing for ETL,
    :param AllManifest project: A manifest object for the project that we
        want to update via an ETL process.
    :param str prelim_source_id: A provisional human-readable ID for a
        data-source (typically a filename). This may be altered if this
        ID already exists in the ETL models.
    :param str source_exists: Handling options if a prelim_source_id
        already exists in the ETL records. If "raise" then throw an
        exception, if "replace" then replace the prior data source with
        new data (provided the projects are the same between the old and
        new ETL), if "new" then change the prelim_source_id to be a new
        identifier, as the user claims this is a new dataset for ETL.
    """

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
            f'it belongs to another project "{ds.project.label}", '
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
            # Iterate through this until we get a source_id that
            # is new and not used.
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
    elif ds is None:
        # This prelim_source_id is new, so not conflicting with prior
        # ETL data sources.
        col_prior_fields = map_cols_to_prior_fields(
            df,
            project,
        )
        source_id = prelim_source_id
    else:
        raise ValueError(
            'This data source already exists, but source_exists handling '
            f'must be "raise", "replace", or "new" not {source_exists}'
        )

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


def load_csv_for_etl(
    file_path,
    project=None,
    project_id=None,
    data_source_label=None,
    prelim_source_id=None,
    source_exists="raise"
):
    """Loads a csv file for an ETL process.
    :param str file_path: The file path to a CSV file that will be read into
        a dataframe for ingest in an ETL process.
    :param AllManifest project: A manifest object for the project that we
        want to update via an ETL process.
    :param str(UUID) project_id: Project manifest object uuid
    :param str data_source_label: A human readable label for to give this
        datafile a bit of descriptive metadata.
    :param str prelim_source_id: An informal identifier for this specific
        dataset.
    :param str source_exists: Handling options if a prelim_source_id
        already exists in the ETL records. If "raise" then throw an
        exception, if "replace" then replace the prior data source with
        new data (provided the projects are the same between the old and
        new ETL), if "new" then change the prelim_source_id to be a new
        identifier, as the user claims this is a new dataset for ETL.
    """
    df = df_str_cols_load_csv(file_path)
    if df is None:
        # No data returned from loading the CSV.
        return None
    if not prelim_source_id:
        # No prelim_source_id, so use the filename.
        prelim_source_id = os.path.basename(file_path)
    if not project and project_id:
        project = AllManifest.objects.filter(uuid=project_id).first()
    if not project:
        raise ValueError('Need a manifest object for a project')
    return load_df_for_etl(
        df=df,
        project=project,
        prelim_source_id= prelim_source_id,
        data_source_label=data_source_label,
        source_exists=source_exists
    )
