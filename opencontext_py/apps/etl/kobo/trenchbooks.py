
import uuid as GenUUID
import numpy as np
import pandas as pd

from opencontext_py.apps.all_items.models import (
    AllManifest,
)
from opencontext_py.apps.all_items import configs

from opencontext_py.apps.etl.kobo import db_lookups
from opencontext_py.apps.etl.kobo import kobo_oc_configs
from opencontext_py.apps.etl.kobo import pc_configs
from opencontext_py.apps.etl.kobo import utilities


"""Uses Pandas to prepare Kobotoolbox exports for Open Context import

"""

TRENCH_BOOK_ROOT_GROUPS = [
    'region',
    'site',
    'area',
    'trench_name',
    'Trench ID',
    'Unit ID',
    'Trench Supervisor'
]

# These columns uniquely describe a trench book entry.
# They are useful for look ups of a given trench book.
TRENCH_BOOK_INDEX_COLS = [
    'Trench Book Title',
    'Date Documented',
    'Start Page',
    'End Page',
]

TRENCH_BOOK_CONTEXT_COLS = [
    'Trench ID',
    'Unit ID'
]

TRENCH_BOOK_REL_CONFIGS = {
    'tb-locus-links': {
        'tb_entry_sheet': 'Trench Book Entry',
        'tb_rel_sheet': 'group_rel_locus',
        'tb_rel_col': 'Related Locus / Loci (Discussed in this entry)/Related Locus',
        'tb_rel_col_rename': 'object__locus_id',
        'tb_rel_link_type': 'Related Open Locus',
    },
    'tb-finds-links': {
        'tb_entry_sheet': 'Trench Book Entry',
        'tb_rel_sheet': 'group_rel_find',
        'tb_rel_col': 'Related Find(s) (Discussed in this entry)/Related Find',
        'tb_rel_col_rename': 'object__Find Number',
        'tb_rel_link_type': 'Related Small Find',
    },
}

TRENCH_BOOK_REL_UUID_CONFIGS = {
    'tb-locus-links': {
        'lookup_sheet': 'Locus Summary Entry',
        'index_cols': {
            'Unit ID': 'object__unit_id',
            'Locus ID': 'object__locus_id',
        },
        'final_renames': {
            'Trench Book Title': 'subject__tb_title'
        },
    },
    'tb-finds-links': {
        'lookup_sheet': 'Field Small Find Entry',
        'index_cols': {
            'Unit ID': 'object__unit_id',
            'Find Number': 'object__Find Number',
        },
        'final_renames': {
            'Trench Book Title': 'subject__tb_title'
        },
    }
}

TRENCH_BOOK_FINAL_REL_COLS = [
    'Date Documented',
    'Start Page',
    'End Page',
    'Trench ID',
    'Trench Book Title',
    'subject__tb_title',
    'subject__tb_supervisor',
    'subject__unit_id',
    'subject_uuid_source',
    'subject_uuid',
    
    pc_configs.LINK_RELATION_TYPE_COL,
    
    'object_uuid',
    'object_uuid_source',
    'object__tb_supervisor',
    'object__unit_id',
    'object__trench_id',
    'object__locus_id',
    'object__Find Number',
    'object__subject__tb_title'
]

# Columns found in related sheets that can be dropped
RELATED_SHEET_DROP_COLS = [
    '_index',
    '_parent_table_name',
    '_parent_index',
    '_submission__id',
    '_submission__submission_time',
]

SKIP_MULTI_VALUE_REDACTIONS = [
    'Trench Supervisor'
]
        
def look_up_parent(parent_sheet, parent_uuid, dfs):
    """Looks up and returns a 1 record dataframe of the record for the parent item."""
    df_parent = dfs[parent_sheet][
        dfs[parent_sheet]['_uuid'] == parent_uuid
    ].copy().reset_index(drop=True)
    return df_parent

def lookup_related_locus(
    rel_locus_id,
    parent_sheet,
    parent_locus_uuid,
    dfs,
    context_delim='/'
):
    """Looks up a related locus on the parent sheet, and returns a dictionary of relevant data for the locus"""
    df_parent = look_up_parent(parent_sheet, parent_locus_uuid, dfs)
    if df_parent.empty:
        raise RuntimeError('Parent locus uuid {} not found.'.format(parent_locus_uuid))
    orig_rel_locus_id = rel_locus_id
    rel_locus_id = str(rel_locus_id)
    trench_id = str(df_parent['Trench ID'].iloc[0])
    if context_delim in rel_locus_id:
        locus_ex = rel_locus_id.split(context_delim)
        trench_id = locus_ex[0].strip()
        rel_locus_id = locus_ex[1].strip()
    df = dfs[parent_sheet]
    df['Trench ID'] = df['Trench ID'].astype(str)
    df['Locus ID'] = df['Locus ID'].astype(str)
    df_rel = df[
        (df['Trench ID'] == trench_id) & (df['Locus ID'] == rel_locus_id)
    ].copy().reset_index(drop=True)
    df_rel['object__locus_id'] = orig_rel_locus_id
    df_rel['object__locus_id'] = df_rel['object__locus_id'].astype(str)
    df_rel['subject_uuid'] = parent_locus_uuid
    return df_rel

def merge_context_df(
    df,
    df_context,
    key_cols,
    context_cols,
    rename_prefix
):
    """Merges a df_context with a df"""
    df_context = df_context[(context_cols + key_cols)]
    renames = {
        c: (rename_prefix + c)
        for c in df_context.columns
        if (not c in key_cols) and ((rename_prefix + c) not in df_context.columns)
    }
    df_context.rename(columns=renames, inplace=True)
    df_output = pd.merge(
        df,
        df_context,
        how='left',
        on=key_cols
    )
    return df_output


def make_new_trench_book_titles(row):
    """Makes a new trench book title for a row."""
    if row['Start Page'] < row['End Page']:
        page_part = '{}-{}'.format(
            int(row['Start Page']),
            int(row['End Page'])
        )
    elif row['Start Page'] == row['End Page']:
        page_part = int(row['Start Page'])
    elif row['Start Page'] > row['End Page']:
        page_part = '{}-{}'.format(
            int(row['End Page']),
            int(row['Start Page'])
        )
    return '{} ({}):{}; {}'.format(
        row['Trench ID'],
        row['Date Documented'],
        page_part,
        row['Entry Type']
    )


def add_make_new_trench_book_title_column(df, new_tb_title_col):
    """Adds a new column with a new trench book title."""
    df[new_tb_title_col] = df.apply(
        make_new_trench_book_titles,
        axis=1
    )
    return df

def join_tb_entries_to_related_df(
    tb_dfs,
    tb_index_cols=None,
    tb_rel_sheet='group_rel_locus',
    tb_rel_col='Related Locus / Loci (Discussed in this entry)/Related Locus',
    tb_rel_col_rename='object__locus_id',
    tb_rel_link_type='Related Open Locus',
    context_cols=None,
    rel_drop_cols=None
):
    """Joins trench book entries to a trench book related DF."""
    df_output = tb_dfs[tb_rel_sheet].copy().reset_index(drop=True)
    df_output[pc_configs.LINK_RELATION_TYPE_COL] = tb_rel_link_type
    df_output.rename(
        columns={
            tb_rel_col: tb_rel_col_rename,
            '_submission__uuid': 'subject_uuid'
        },
        inplace=True
    )
    df_parents = []
    if tb_index_cols is None:
        tb_index_cols = TRENCH_BOOK_INDEX_COLS
    if context_cols is None:
        context_cols = TRENCH_BOOK_CONTEXT_COLS
    for i, row in df_output.iterrows():
        df_parent = look_up_parent(
            row['_parent_table_name'],
            row['subject_uuid'],
            tb_dfs
        )
        df_parent = df_parent[(
            context_cols +
            ['_uuid'] +
            tb_index_cols
        )]
        df_parents.append(df_parent)
    # Now combine all the related data
    df_all_parents = pd.concat(df_parents)
    df_all_parents.drop_duplicates(subset=['_uuid'], inplace=True)
    df_all_parents.rename(
        columns={'_uuid': 'subject_uuid'},
        inplace=True
    )
    # Make a dataframe that has the index columns
    # of the trench book entries.
    df_tb_index = df_all_parents[(
        tb_index_cols +
        ['subject_uuid']
    )].copy().reset_index(drop=True)
    # Now drop the trenchbook index colums from the df_all_parents,
    # because we don't want to rename the columns when we merge it
    # into the tb_locus_df.
    df_all_parents.drop(tb_index_cols, axis=1, inplace=True, errors='ignore')
    df_output = merge_context_df(
        df_output,
        df_all_parents,
        ['subject_uuid'],
        context_cols,
        'object__'
    )
    # Merge in the index columns that uniquely describe a
    # trench book entry
    df_output = pd.merge(
        df_output,
        df_tb_index,
        how='left',
        on=['subject_uuid']
    )
    obj_context_cols = ['object__' + c for c in context_cols]
    # Make sure the output df has the tb_index_cols first.
    df_output = utilities.reorder_first_columns(
        df_output, (
            tb_index_cols +
            ['subject_uuid', pc_configs.LINK_RELATION_TYPE_COL] +
            obj_context_cols
        )
    )
    if rel_drop_cols is None:
        rel_drop_cols = RELATED_SHEET_DROP_COLS
    # Drop columns that we don't want.
    df_output.drop(rel_drop_cols, axis=1, inplace=True, errors='ignore')
    return df_output

def prep_trench_book_related(tb_dfs, related_config=None):
    """Prepares trench book related relationship dfs"""
    if related_config is None:
        related_config = TRENCH_BOOK_REL_CONFIGS
    tb_rel_dfs = {}
    for rel_type, rel_config_args in related_config.items():
        rel_config_args['tb_dfs'] = tb_dfs
        tb_rel_dfs[rel_type] = join_tb_entries_to_related_df(
            **rel_config_args
        )
    
    return tb_rel_dfs

def add_trench_book_related_uuids(
    tb_rel_dfs,
    field_config_dfs,
    tb_rel_uuid_configs=None
):
    """Adds UUIDS of trench book related entities."""
    if tb_rel_uuid_configs is None:
        tb_rel_uuid_configs = TRENCH_BOOK_REL_UUID_CONFIGS
    new_tb_rel_dfs = {}
    for rel_type, tb_rel_df in tb_rel_dfs.items():
        if not rel_type in tb_rel_uuid_configs:
            # We do not have a configuration to look this up, so skip
            new_tb_rel_dfs[rel_type] = tb_rel_df
            continue
        # Get the configuration for joining in UUIDs for this type of related entity
        config = tb_rel_uuid_configs[rel_type]
        join_cols = [join_col for _, join_col in config['index_cols'].items()]
        keep_cols = [col for col in config['index_cols'].keys()]
        keep_cols.append('_uuid')
        lookup_sheet = config['lookup_sheet']
        lookup_df = field_config_dfs[lookup_sheet]['dfs'][lookup_sheet]
        lookup_df = lookup_df[keep_cols].copy().reset_index(drop=True)
        lookup_df.rename(columns={'_uuid':'object_uuid'}, inplace=True)
        lookup_df.rename(columns=config['index_cols'], inplace=True)
        # Convert join columns to string to ensure joins.
        for join_col in join_cols:
            lookup_df[join_col] = lookup_df[join_col].astype(str)
            tb_rel_df[join_col] = tb_rel_df[join_col].astype(str)
        
        # Now finally merge the data with UUIDs.
        tb_rel_df = pd.merge(
            tb_rel_df,
            lookup_df,
            how='left',
            on=join_cols
        )
        # Now indicate where we got the UUID
        good_index = (tb_rel_df['object_uuid'] != np.nan)
        tb_rel_df.loc[good_index, 'object_uuid_source'] = UUID_SOURCE_KOBOTOOLBOX
        tb_rel_df.loc[~good_index, 'object_uuid_source'] = np.nan
        
        # Rename columns as needed.
        if 'final_renames' in config:
            tb_rel_df.rename(columns=config['final_renames'], inplace=True)
        
        # Add the revised tb_rel_df to the output dict.
        new_tb_rel_dfs[rel_type] = tb_rel_df
    return new_tb_rel_dfs



def make_previous_next_trench_book_rels_dfs(
    df_f
):
    """Makes previous and next relations between entries"""

    sort_cols = ['Trench ID', 'Date Documented', 'Start Page',  'End Page']
    tb_ent_indx = (
        (df_f['Trench ID'].notnull())
        & ((df_f['Start Page']>0) | (df_f['End Page']>0))
    )
    df_tb_ents = df_f[tb_ent_indx].copy().reset_index(drop=True)
    trench_ids = df_tb_ents['Trench ID'].unique().tolist()
    
    df_tb_ents.sort_values(by=['Trench ID', 'Date Documented', 'Start Page',  'End Page'], inplace=True)
    
    df_rels = []
    rel_configs = [
        ('Previous Entry', -1),
        ('Next Entry', 1),
    ]
    for trench_id in trench_ids:
        for rel_type, index_dif in rel_configs:
            df_rel = df_tb_ents[
                (df_tb_ents['Trench ID'] == trench_id)
            ].copy().reset_index(drop=True)
            len_df = len(df_rel.index)
            df_rel.rename(
                columns={
                    '_uuid':'subject_uuid',
                    'Trench Book Title': 'subject__tb_title',
                },
                inplace=True
            )
            # Organize the columns that we want to keep for the df_p_n output.
            df_rel_cols_temp = sort_cols + [c for c in TRENCH_BOOK_INDEX_COLS if not c in sort_cols]
            df_rel_cols_temp += [c for c in TRENCH_BOOK_CONTEXT_COLS if not c in sort_cols]
            df_rel_cols = [c for c in df_rel_cols_temp if c in df_rel.columns]
            df_rel_cols += ['subject__tb_title', 'subject_uuid']
            df_rel = df_rel[df_rel_cols]
            # Sort the df rel!
            df_rel.sort_values(by=sort_cols, inplace=True)
            df_rel[pc_configs.LINK_RELATION_TYPE_COL] = np.nan
            df_rel['object_uuid'] = np.nan
            df_rel['object__subject__tb_title'] = np.nan
            for i, row in df_rel.iterrows():
                other_index = i + index_dif
                if other_index < 0 or other_index >= len_df:
                    # we're outside of the index range, so skip.
                    continue
                up_indx = (df_rel['subject_uuid'] == row['subject_uuid'])
                df_rel.loc[up_indx, pc_configs.LINK_RELATION_TYPE_COL] = rel_type
                df_rel.loc[up_indx, 'object_uuid'] = df_rel['subject_uuid'].iloc[other_index]
                df_rel.loc[up_indx, 'object__subject__tb_title'] = df_rel['subject__tb_title'].iloc[other_index]

            # Drop missing records.
            df_rel = df_rel[df_rel[pc_configs.LINK_RELATION_TYPE_COL].notnull()]
            df_rels.append(df_rel)

    return df_rels

def make_trench_book_unit_id_relations_df(df_f, all_contexts_df):
    """Makes a dataframe of relations between trench books and Units"""
    tb_first_cols = [
        'Date Documented',
        'Start Page',
        'End Page',
        'Trench ID',
        'Unit ID',
        'Trench Book Title',
        'Document Type',
    ]
    rel_df = df_f[tb_first_cols + ['_uuid']].copy()
    rel_df['subject__tb_title'] = rel_df['Trench Book Title']
    rel_df['subject_uuid'] = rel_df['_uuid']
    rel_df[pc_configs.LINK_RELATION_TYPE_COL] = 'link'
    unit_df = all_contexts_df[all_contexts_df['class_uri']=='oc-gen:cat-exc-unit'].copy()
    unit_df = unit_df[['label',	'context_uuid',	'uuid_source']]
    unit_df['object__unit_id'] = unit_df['label']
    unit_df.rename(
        columns={
            'label': 'Unit ID',
            'context_uuid': 'object_uuid',
            'uuid_source': 'object_uuid_source',
        },
        inplace=True
    )
    # Now join the Units to the trench books.
    rel_df = pd.merge(
        rel_df,
        unit_df,
        how='left',
        on=['Unit ID']
    )
    return rel_df
    
    
def make_trench_book_parent_relations_df(
    df_f,
    config=FIELD_DATA_PREPS['Trench Book Entry']
):
    """Makes relations between trench book entries and parent books
    
    :param dataframe df_f: Trench book description dataframe
    :parma dict tb_rel_dfs: Dictionary of trench book relations
        dataframes.
    """
    # Configures columns and how columns get renamed for subject_df and
    # object_df.
    mapping_tups = [
        (
            'Trench Supervisor',
            'subject__tb_supervisor',
            'object__tb_supervisor'
        ),
        ('Unit ID', 'subject__unit_id', 'object__unit_id'),
        (
            config['tb_new_title'],
            'subject__' + config['tb_new_title'],
            'object__' + 'subject__' + config['tb_new_title']
        ),
        ('subject_uuid_source', 'subject_uuid_source', 'object_uuid_source'),
        ('_uuid', 'subject_uuid', 'object_uuid'),
    ]
    
    # The columns used to join parent_df and child_df
    join_cols = [
        'Trench Supervisor',
        'Unit ID',
    ]
    doc_type_col, doc_type = config.get('tb_doc_type_root')
    parent_df = df_f[
        (df_f[doc_type_col] == doc_type)
    ].copy().reset_index(drop=True)
    child_df = df_f[
        (df_f[doc_type_col] != doc_type)
    ].copy().reset_index(drop=True)
    
    # Copy the join columns to make temporary join columns that
    # will be common in the parent_df and child_df and will not
    # get renamed.
    temp_join_cols = []
    for i, join_col in enumerate(join_cols, 1):
        temp_join = 'TEMP_JOIN_COL_{}'.format(i)
        parent_df[temp_join] = parent_df[join_col].astype(str)
        child_df[temp_join] = child_df[join_col].astype(str)
        temp_join_cols.append(temp_join)
    
    subset_cols = [col for col, _, _ in mapping_tups] + temp_join_cols
    subject_df_cols = [col for _, col, _ in mapping_tups]
    object_df_cols = [col for _, _, col in mapping_tups]
    rel_df_cols = subject_df_cols + [pc_configs.LINK_RELATION_TYPE_COL] + object_df_cols
    
    # Now iterate through and actually do the joins
    rel_dfs = []
    linking_rels = [
        ('Is Part of', child_df, parent_df, 'left'),
        ('Has Part', parent_df, child_df, 'right'),
    ]
    for link_rel, subject_df, object_df, join_how in linking_rels:
        subject_df = subject_df[subset_cols].copy().reset_index(drop=True)
        object_df = object_df[subset_cols].copy().reset_index(drop=True)
        # Now rename the columns
        subject_df.rename(
            columns={old:new for old, new, _ in mapping_tups},
            inplace=True
        )
        object_df.rename(
            columns={old:new for old, _, new in mapping_tups},
            inplace=True
        )
        # Do the join, as a left or right join depending
        # on if the child_df is the object_df or subject_df.
        rel_df = pd.merge(
            subject_df,
            object_df,
            how=join_how,
            on=temp_join_cols
        )
        rel_df[pc_configs.LINK_RELATION_TYPE_COL] = link_rel
        rel_dfs.append(rel_df)
    # Make the TB parent relation dataframe
    tb_parent_rels = pd.concat(rel_dfs)
    tb_parent_rels = tb_parent_rels[rel_df_cols]
    return tb_parent_rels
    

def make_final_trench_book_relations_df(field_config_dfs, all_contexts_df):
    """Makes final consolidated dataframe of Trench Book link relations."""
    tb_dfs = field_config_dfs['Trench Book Entry']['dfs']
    df_f = tb_dfs['Trench Book Entry']
    # Make several dataframes of TB relations to loci, small finds.
    tb_rel_dfs = prep_trench_book_related(tb_dfs)
    tb_rel_dfs = add_trench_book_related_uuids(tb_rel_dfs, field_config_dfs)
    all_rel_dfs = [rel_df for _, rel_df in tb_rel_dfs.items()]
    all_rel_dfs += make_previous_next_trench_book_rels_dfs(df_f)
    # Add a single dataframe of TB entry and TB book relations
    tb_parent_rels = make_trench_book_parent_relations_df(df_f)
    all_rel_dfs.append(tb_parent_rels)
    # Add a single dataframe of TB relations to Unit IDs.
    tb_unit_rel_df = make_trench_book_unit_id_relations_df(df_f, all_contexts_df)
    all_rel_dfs.append(tb_unit_rel_df)
    # Now bring all of these individual TB relations dataframes into a single
    # dataframe of TB relations.
    tb_all_rels_df = pd.concat(all_rel_dfs)
    # Reorder and limit final output columns to a pre-determined config.
    use_cols = [c for c in TRENCH_BOOK_FINAL_REL_COLS if c in tb_all_rels_df.columns]
    tb_all_rels_df = tb_all_rels_df[use_cols]
    tb_all_rels_df.sort_values(by=[
        pc_configs.LINK_RELATION_TYPE_COL,
        'subject__tb_title',
        'object__subject__tb_title',
        'object__unit_id',
        'object__locus_id',
        'object__Find Number',
    ], inplace=True)
    return tb_all_rels_df


def add_trench_book_parents(
    df,
    year,
    config
):
    """Adds root-level trench book parent records."""
    df_grp = df.groupby(TRENCH_BOOK_ROOT_GROUPS, as_index=False).first()
    df_grp = df_grp[TRENCH_BOOK_ROOT_GROUPS]
    doc_type_col, doc_type = config.get('tb_doc_type_root')
    entry_text_col, entry_text = config.get('tb_root_entry')
    # Add columns and values that apply to ALL the root documents
    df_grp[entry_text_col] = entry_text    
    df_grp[doc_type_col] = doc_type
    df_grp[config['tb_root_year']] = year
    #
    # Now iterate through the root documents to get or make their UUIDs
    # and titles.
    df_working = df_grp.copy().reset_index(drop=True)
    for i, row in df_working.iterrows():
        indx = (
            (df_grp['Unit ID'] == row['Unit ID']) &
            (df_grp['Trench Supervisor'] == row['Trench Supervisor'])
        )
        tb_title = doc_type + ' ' + row['Unit ID']
        df_grp.loc[indx, config['tb_new_title']] = doc_type + ' ' + row['Unit ID']
        uuid = db_lookups.db_lookup_manifest_uuid(
            label=tb_title,
            item_type='documents',
        )
        if uuid is not None:
            df_grp.loc[indx, '_uuid'] = uuid
            df_grp.loc[indx, 'subject_uuid_source'] = pc_configs.UUID_SOURCE_OC_LOOKUP
        else:
            df_grp.loc[indx, '_uuid'] = str(GenUUID.uuid4())
            df_grp.loc[indx, 'subject_uuid_source'] = pc_configs.UUID_SOURCE_OC_KOBO_ETL
    
    # Add the new root document records to the general trench book description
    # dataframe.
    df_first_cols = df.columns.tolist()
    df = df.append(df_grp, ignore_index=True)
    df = utilities.reorder_first_columns(df, df_first_cols)
    return df

    