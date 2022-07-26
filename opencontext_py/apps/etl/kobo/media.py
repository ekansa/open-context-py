import copy
import uuid as GenUUID
import os
import shutil
import numpy as np
import pandas as pd

from PIL import Image, ImageFile
from opencontext_py.apps.all_items.models import (
    AllManifest,
)
from opencontext_py.apps.all_items import configs

from opencontext_py.apps.etl.kobo import db_lookups
from opencontext_py.apps.etl.kobo import kobo_oc_configs
from opencontext_py.apps.etl.kobo import pc_configs
from opencontext_py.apps.etl.kobo import utilities


"""Uses Pandas to prepare Kobotoolbox exports for Open Context import

import importlib
from opencontext_py.apps.etl.kobo import media
importlib.reload(media)

df = media.make_all_export_media_df()



"""


MEDIAFILE_COLS_ENDSWITH = [
    ('Primary Image', 'link-primary', '_uuid', 'subject_uuid'),
    ('Supplemental Image', 'link-supplemental', '_submission__uuid', 'subject_uuid'),
    ('Image File', 'primary', '_uuid', 'media_uuid'),
    ('Video File', 'primary', '_uuid', 'media_uuid'),
    ('Audio File', 'primary', '_uuid', 'media_uuid'),
]

MEDIA_DESCRIPTION_COLS_ENDSWITH = [
    'Note about Primary Image',
    'Note about Supplemental Image',
    'File Title', 
    'Date Metadata Recorded', 
    'Date Created', 
    'File Creator',
    'Data Entry Person',
    'Media Type', 
    'Image Type', 
    'Other Image Type Note', 
    'Type of Composition Subject', 
    'Type of Composition Subject/Object (artifact, ecofact)', 
    'Type of Composition Subject/Field', 
    'Type of Composition Subject/Work', 
    'Type of Composition Subject/Social', 
    'Type of Composition Subject/Publicity', 
    'Type of Composition Subject/Other', 
    'Other Composition Type Note', 
    'Direction or Orientation Notes/Object Orientation Note', 
    'Direction or Orientation Notes/Direction Faced in Field', 
    'Description', 
    'Upload a File with Form?',  
    'Media File Details (file not to be uploaded with this form)/Other Media Type Note', 
    'Media File Details (file not to be uploaded with this form)/File Storage Type', 
    'Media File Details (file not to be uploaded with this form)/Web URL', 
    'Media File Details (file not to be uploaded with this form)/Name of Offline Device', 
    'Media File Details (file not to be uploaded with this form)/Filename', 
    'Media File Details (file not to be uploaded with this form)/Director Path', 
]

MEDIA_SOURCE_FILE_PREFIXS = {
    'Catalog': 'cat-',
    'Conservation': 'consrv-',
    'Field Bulk': 'field-bulk-',
    'Field Small': 'field-small-',
    'Locus': 'locus-',
    'Media': '',
    'Trench Book': 'trench-book-',
}

MEDIA_SOURCE_COMPOSITION_TYPES = {
    'Catalog': 'Object (artifact, ecofact)',
    'Conservation': 'Conservation',
    'Field Bulk': 'Field',
    'Field Small': 'Field',
    'Locus': 'Field',
    'Trench Book': 'Field',
}


MEDIA_ATTRIBUTES_SHEET = 'Media File Metadata Entry'
MEDIA_RELS_SHEET = 'Rel_ID_Group_Rep'


REL_COLS = [
    'File Upload/Image File',
    'subject_uuid',
    'subject_uuid_source',
    pc_configs.LINK_RELATION_TYPE_COL,
    'object_uuid',
    'object_uuid_source',
    'object_related_id',
    'object_related_type',
]


def revise_filename(filename):
    """Revises a filename to be URL friendly."""
    filename = filename.lower()
    filename = filename.replace(' ', '-').replace('_', '-')
    return filename


def make_sheet_media_df(
    df, 
    subjects_df,
    form_type,
    media_col_end, 
    media_source_type, 
    act_uuid, 
    new_uuid,
):
    media_col = None
    if not act_uuid in df.columns:
        return None
    for col in df.columns:
        if not col.endswith(media_col_end):
            continue
        media_col = col
        break
    if media_col is None:
        return None
    # We have found some columns for media files,
    # now gather the descriptive fields used with
    # these media.
    sheet_des_cols = []
    for des_col_end in MEDIA_DESCRIPTION_COLS_ENDSWITH:
        for col in df.columns:
            if not col.endswith(des_col_end):
                continue
            if (form_type != 'media'
                and col in ['Description', 'General Description']):
                # A total hack. We don't want to describe media
                # with field used to describe catalog objects.
                continue
            sheet_des_cols.append(col)
    # Make a df_sheet_media dataframe that has the
    # media file name column, uuid column, and the
    # descriptive fields for the media.
    df_sheet_media = df[
        ([media_col, act_uuid] + sheet_des_cols)    
    ].copy()
    df_sheet_media[media_col].replace('', np.nan, inplace=True)
    df_sheet_media.dropna(subset=[media_col], inplace=True)
    df_sheet_media['media_source_type'] = media_source_type
    df_sheet_media['kobo_form'] = form_type
    df_sheet_media.rename(
        columns={media_col: 'filename'},
        inplace=True
    )
    if pc_configs.SUBJECTS_SHEET_PRIMARY_IDs.get(form_type):
        df_sheet_media = utilities.add_final_subjects_uuid_label_cols(
            df=df_sheet_media, 
            subjects_df=subjects_df,
            form_type=form_type,
            final_label_col=new_uuid.replace('uuid', 'label'),
            final_uuid_col=new_uuid,
            final_uuid_source_col=(new_uuid + '_source'),
            orig_uuid_col=act_uuid,
        )
    else:
        df_sheet_media.rename(
            columns={act_uuid: new_uuid,},
            inplace=True
        )
    df_sheet_media.reset_index(drop=True, inplace=True)
    if df_sheet_media.empty:
        return None
    return df_sheet_media


def make_dfs_media_df(dfs, file_form_type, subjects_df):
    """Makes a dataframe of media files from a dataframe dict."""
    df_media_list = []
    for media_col_end, media_source_type, act_uuid, new_uuid in MEDIAFILE_COLS_ENDSWITH:
        for sheet_name, df in dfs.items():
            form_type = file_form_type
            if utilities.get_general_form_type_from_sheet_name(sheet_name):
                form_type = utilities.get_general_form_type_from_sheet_name(
                    sheet_name
                )
            df_sheet_media = make_sheet_media_df(
                df, 
                subjects_df,
                form_type,
                media_col_end, 
                media_source_type, 
                act_uuid, 
                new_uuid,
            )
            if df_sheet_media is None:
                continue
            df_media_list.append(df_sheet_media)
    if not len(df_media_list):
        return None
    df_media = pd.concat(df_media_list)
    if df_media.empty:
        return None
    if '_uuid' in df_media.columns:
        df_media.rename(columns={'_uuid': 'path_uuid'}, inplace=True)
    return df_media


def make_all_export_media_df(
    excels_dirpath=pc_configs.KOBO_EXCEL_FILES_PATH,
    subjects_path=pc_configs.SUBJECTS_CSV_PATH,
    all_media_kobo_files_path=pc_configs.MEDIA_ALL_KOBO_REFS_CSV_PATH,
):
    """Make a dataframe of all media in all export files."""
    subjects_df = pd.read_csv(subjects_path)
    df_all_media_list = []
    for excel_filepath in utilities.list_excel_files(excels_dirpath):
        excel_file = os.path.basename(excel_filepath)
        file_form_type = utilities.get_general_form_type_from_file_sheet_name(
            excel_file
        )
        dfs = utilities.read_excel_to_dataframes(excel_filepath)
        df_media = make_dfs_media_df(
            dfs,
            file_form_type=file_form_type,
            subjects_df=subjects_df,
        )
        if df_media is None:
            continue
        df_media['new_filename'] = df_media['filename'].apply(revise_filename)
        for file_start, prefix in MEDIA_SOURCE_FILE_PREFIXS.items():
            if not excel_file.startswith(file_start):
                continue
            df_media['new_filename'] = prefix + df_media['new_filename']
            if MEDIA_SOURCE_COMPOSITION_TYPES.get(file_start):
                df_media['Type of Composition Subject'] = MEDIA_SOURCE_COMPOSITION_TYPES[file_start]
        df_all_media_list.append(df_media)
    if not len(df_all_media_list):
        return None
    df_all_media = pd.concat(df_all_media_list)
    if df_all_media.empty:
        return None
    df_all_media = df_all_media[df_all_media['new_filename'].notnull()]
    df_all_media.drop_duplicates(subset=['new_filename'], inplace=True)
    expected_len = len(df_all_media.index)
    if (len(df_all_media['new_filename'].unique().tolist()) != expected_len or
        len(df_all_media['filename'].unique().tolist()) != expected_len):
        raise RuntimeError(
            'Expected {}, but have {} filenames, and {} new-filenames'.format(
                expected_len,
                len(df_all_media['filename'].unique().tolist()),
                len(df_all_media['new_filename'].unique().tolist())
            )
        )
    if all_media_kobo_files_path:
        df_all_media.to_csv(all_media_kobo_files_path, index=False)
    return df_all_media


def combine_media_with_files(df_media, df_files):
    """Combines a media df with the df of files in the file system."""
    df_output = pd.merge(
        df_media,
        df_files,
        how='left',
        on=['filename']
    )
    return df_output

def set_check_directory(root_dir, act_dir):
    """ Prepares a directory to find import GeoJSON files """
    output = None
    full_dir_path = os.path.join(root_dir, act_dir)
    if not os.path.exists(full_dir_path):
        os.makedirs(full_dir_path)
    if os.path.exists(full_dir_path):
        output = full_dir_path
    return output

def get_make_directories(oc_media_root_dir, oc_sub_dirs=None):
    """ gets and make directories for the preparing files """
    dirs = {}
    if oc_sub_dirs is None:
        oc_sub_dirs = kobo_oc_configs.OPENCONTEXT_MEDIA_DIRS
    if not os.path.exists(oc_media_root_dir):
        os.makedirs(oc_media_root_dir)
    for sub_dir in oc_sub_dirs:
        sub_dir_path = set_check_directory(oc_media_root_dir, sub_dir)
        if sub_dir_path is None:
            raise RuntimeError('Cannot find or make {}'.format(sub_dir_path))
        dirs[sub_dir] = sub_dir_path
    return dirs

def get_image_obj(src_file, new_file):
    """Gets an image object and png flag."""
    png = False
    if src_file.lower().endswith('.png'):
        png = True
    if src_file == new_file:
        return None, None
    if not os.path.exists(src_file):
        raise RuntimeError('Cannot find ' + src_file)
    ImageFile.LOAD_TRUNCATED_IMAGES = True
    try:
        im = Image.open(src_file)
        im.LOAD_TRUNCATED_IMAGES = True
    except:
        print('Cannot use as image: ' + src_file)
        im = None
    if im is None:
        return None, None
    return im, png

def make_new_size_file(src_file, new_file, new_width):
    """Makes a new file with a new size."""
    output = None
    im, png = get_image_obj(src_file, new_file)
    if im is None:
        return None
    ratio = 1  # default to same size
    if im.width > new_width:
        ratio = im.width / new_width
    else:
        new_width = im.width
    new_height = int(round((im.height * ratio), 0))
    size = (new_width, new_height)
    rescale_ok = None
    try:
        im.load()
        rescale_ok = True
    except IOError:
        rescale_ok = False
        raise RuntimeWarning('Problem rescaling image for: ' + new_file)
    if not rescale_ok:
        return None
    if png:
        im.thumbnail(size, Image.ANTIALIAS)
        background = Image.new("RGB", im.size, (255, 255, 255))
        try:
            background.paste(im, mask=im.split()[3]) # 3 is the alpha channel
            background.save(new_file, "JPEG", quality=100)
            output = new_file
        except:
            png = False
            raise RuntimeWarning('Problem with PNG changes for: ' + new_file)
        del background
    else:
        im.thumbnail(size, Image.ANTIALIAS)
        try:
            im.save(new_file, "JPEG", quality=100)
            output = new_file
        except:
            raise RuntimeWarning('Problem with saving changes for: ' + new_file)
    im.close()
    return output

def make_image_versions_src_and_new_file(
    dirs,
    src_file,
    new_file_name,
    over_write=False,
    preview_width=kobo_oc_configs.MAX_PREVIEW_WIDTH,
    thumbnail_width=kobo_oc_configs.MAX_THUMBNAIL_WIDTH
):
    """Make different file versions in different directories."""
    if not isinstance(src_file, str):
        return None
    if not os.path.exists(src_file):
        raise RuntimeError('Cannot find {}'.format(src_file))
    full_file = os.path.join(dirs['full'], new_file_name)
    prev_file = os.path.join(dirs['preview'], new_file_name)
    thumb_file = os.path.join(dirs['thumbs'], new_file_name)
    if over_write or not os.path.exists(full_file):
        print('Copy full file {}'.format(new_file_name))
        shutil.copy2(src_file, full_file)
    if over_write or not os.path.exists(prev_file):
        print('Copy preview {}'.format(prev_file))
        make_new_size_file(src_file, prev_file, new_width=preview_width)
    if over_write or not os.path.exists(thumb_file):
        print('Copy thumbnail {}'.format(thumb_file))
        make_new_size_file(src_file, thumb_file, new_width=thumbnail_width)
    return full_file, prev_file, thumb_file


def make_media_url(file_path, file_type, media_base_url=pc_configs.MEDIA_BASE_URL):
    """Makes a media URL for a give file type"""
    type_dir = f'/{file_type}/'
    if not type_dir in file_path:
        return None
    f_ex = file_path.split(type_dir)
    return f'{media_base_url}{type_dir}{f_ex[-1]}'


def make_opencontext_file_versions(
    all_media_kobo_files_path=pc_configs.MEDIA_ALL_KOBO_REFS_CSV_PATH,
    oc_media_root_dir=pc_configs.OC_MEDIA_FILES_PATH,
    oc_sub_dirs=None,
):
    """Makes different file versions expected by Open Context."""
    df_media = pd.read_csv(all_media_kobo_files_path)
    dirs = get_make_directories(oc_media_root_dir, oc_sub_dirs=oc_sub_dirs)
    for col in ['FULL_URL', 'PREVIEW_URL', 'THUMBS_URL']:
        if col in df_media.columns:
            continue
        df_media[col] = np.nan
    files_indx = (
        df_media['path'].notnull() & df_media['new_filename'].notnull()
    )
    for _, row in df_media[files_indx].iterrows():
        full_file, prev_file, thumb_file = make_image_versions_src_and_new_file(
            dirs,
            row['path'],
            row['new_filename']
        )
        act_index = (df_media['path'] == row['path'])
        df_media.loc[act_index, 'FULL_URL'] = make_media_url(
            file_path=full_file, 
            file_type='full'
        )
        df_media.loc[act_index, 'PREVIEW_URL'] = make_media_url(
            file_path=prev_file, 
            file_type='preview'
        )
        df_media.loc[act_index, 'THUMBS_URL'] = make_media_url(
            file_path=thumb_file, 
            file_type='thumbs'
        )
    df_media.to_csv(all_media_kobo_files_path, index=False)
    return df_media
    

def check_prepare_media_uuid(df_all):
    """Checks on the media-uuid, adding uuids that are needing."""
    df_all['media_created'] = np.nan
    df_all['media_uuid_source'] = np.nan
    df_working = df_all.copy()
    for _, row in df_working.iterrows():
        man_obj = None
        update_indx = (
            df_all['filename']==row['filename']
        )
        if isinstance(row['media_uuid'], str):
            man_obj = AllManifest.objects.filter(
                uuid=row['media_uuid'],
                item_type='media',
                project__uuid=pc_configs.PROJECT_UUID,
            ).first()
        else:
            # Check by matching the Kobo given file name and
            # link-uuid.
            man_obj = AllManifest.objects.filter(
                item_type='media',
                project__uuid=pc_configs.PROJECT_UUID,
                meta_json__filename=row['filename'],
            ).filter(
                meta_json__link_uuid=row['link_uuid']
            ).first()
        
        if man_obj is not None:
            df_all.loc[update_indx, 'media_uuid_source'] = man_obj.source_id
            df_all.loc[update_indx, 'media_created'] = man_obj.revised
            if not isinstance(row['media_uuid'], str):
                df_all.loc[update_indx, 'media_uuid'] = man_obj.uuid
        else:
            if not isinstance(row['media_uuid'], str):
                df_all.loc[update_indx, 'media_uuid'] = str(GenUUID.uuid4())
                df_all.loc[update_indx, 'media_uuid_source'] = UUID_SOURCE_OC_KOBO_ETL
            else:
                df_all.loc[update_indx, 'media_uuid_source'] = UUID_SOURCE_KOBOTOOLBOX
    return df_all


def compose_file_title(filename, prefix="Working "):
    name_part = filename
    if '.' in filename:
        name_part = '.'.join(filename.split('.')[:-1])
    return prefix + name_part
    

def finalize_combined_media_df(
    df_all,
    base_url,
    dir_url_configs={},
    media_title_col='File Title',
    media_filename_col='new_filename'):
    """Updates the combined all media dataframe to have final descriptions, names, URLs"""
    ft_indx = (
        df_all[media_title_col].isnull()
        & (df_all['media_source_type'] != 'primary')
    )
    df_all.loc[
        ft_indx,
        media_title_col
    ] = df_all[media_filename_col].apply(compose_file_title)
    # Default the Image Type for non-primary media to working, informal.
    if 'Image Type' in df_all.columns:
        img_type_indx = (
            df_all['Image Type'].isnull()
            & (df_all['media_source_type'] != 'primary')
        )
        df_all.loc[img_type_indx, 'Image Type'] = 'Working, informal'
    # Default the Media Type for non-primary media files as Image.
    if 'Media Type' in df_all.columns:
        media_type_indx = (
            df_all['Media Type'].isnull()
            & (df_all['media_source_type'] != 'primary')
        )
        df_all.loc[media_type_indx, 'Media Type'] = 'Image'
    # Add columns with the URls to different types of versions of
    # the media item.
    for oc_media_type in kobo_oc_configs.OPENCONTEXT_MEDIA_TYPES:
        dir_type = oc_media_type['dir']
        type_col = oc_media_type['col']
        type_base_url = dir_url_configs.get(
            dir_type,
            # Default to the normal OC template for media urls
            (base_url + dir_type + '/')
        )
        df_all[type_col] = type_base_url + df_all[media_filename_col]
    # Finally, add the _uuid column so that it is clear what we should
    # create for a media uuid.
    df_all['_uuid'] = df_all['media_uuid']
    return df_all


def prepare_media(
    excels_filepath=pc_configs.KOBO_EXCEL_FILES_PATH,
    files_path=pc_configs.KOBO_MEDIA_FILES_PATH,
    all_media_kobo_files_path=pc_configs.MEDIA_ALL_KOBO_REFS_CSV_PATH,
):
    """Prepares a dataframe consolidating media from all export excels."""
    df_media = make_all_export_media_df(excels_filepath)
    df_files = utilities.make_directory_files_df(files_path)
    df_media = pd.merge(
        df_media, 
        df_files, 
        on=['path_uuid', 'filename'], 
        how='left'
    )
    if all_media_kobo_files_path:
        df_media.to_csv(all_media_kobo_files_path, index=False)
    return df_media





def prepare_media_links_from_dfs(dfs, subjects_df):
    """Prepares a dataframe of links between media items and related objects"""
    df_link = utilities.get_prepare_df_link_from_rel_id_sheet(dfs)
    if df_link is None:
        return None
    media_subject_uuids = df_link['subject_uuid'].unique().tolist()
    df_all_parents = dfs[MEDIA_ATTRIBUTES_SHEET].copy()
    df_all_parents['subject_uuid'] = df_all_parents['_uuid']
    df_all_parents['subject_uuid_source'] = UUID_SOURCE_KOBOTOOLBOX
    df_all_parents = df_all_parents[df_all_parents['subject_uuid'].isin(media_subject_uuids)]
    df_all_parents = df_all_parents[['File Upload/Image File', 'subject_uuid', 'subject_uuid_source']]
    df_link = pd.merge(
        df_link,
        df_all_parents,
        how='left',
        on=['subject_uuid']
    )
    # Now look up the UUIDs for the objects.
    df_link['object_related_id'] = df_link['object_related_id'].astype(str)
    df_link['object_uuid'] = np.nan
    df_link['object_uuid_source'] = np.nan
    df_link[pc_configs.LINK_RELATION_TYPE_COL] = 'link'
    for _, row in df_link.iterrows():
        object_uuid = None
        object_uuid_source = None
        raw_object_id = row['object_related_id']
        object_type = row['object_related_type']
        if not raw_object_id:
            # Empty string, so skip.
            continue
        act_labels = utilities.get_alternate_labels(
            label=raw_object_id,
            project_uuid=pc_configs.PROJECT_UUID,
        )
        act_prefixes, act_classes = pc_configs.REL_SUBJECTS_PREFIXES.get(object_type, ([], []))
        if object_type in ['Locus', 'Trench']:
            act_labels += [prefix + str(raw_object_id) for prefix in act_prefixes]
            if object_type == 'Trench':
                act_labels.append('{} {}'.format(raw_object_id, row['Year']))
            context_indx = (
                subjects_df['label'].isin(act_labels)
                & (subjects_df['Trench ID'] == row['Trench ID'])
            )
        else:
            context_indx = (subjects_df['label'].isin(act_labels))
        
        if len(act_classes) > 0:
            context_indx &= (subjects_df['class_uri'].isin(act_classes))
        if not subjects_df[context_indx].empty:
            object_uuid = subjects_df[context_indx]['context_uuid'].iloc[0]
            object_uuid_source = subjects_df[context_indx]['uuid_source'].iloc[0]
        else:
            object_uuid = db_lookups.db_lookup_manifest_uuid(
                label=raw_object_id,
                item_type='subjects',
                class_slugs=act_classes
            )
            if object_uuid is not None:
                object_uuid_source = utilities.UUID_SOURCE_OC_LOOKUP
        if object_uuid is None:
            # Don't do an update if we don't have an object_uuid.
            continue
        update_indx = (
            (df_link['object_related_id'] == raw_object_id)
            & (df_link['object_related_type'] == object_type)
        )
        df_link.loc[update_indx, 'object_uuid'] = object_uuid
        df_link.loc[update_indx, 'object_uuid_source'] = object_uuid_source
    df_link = df_link[REL_COLS]
    return df_link


def prepare_media_links_df(
    excel_dirpath, 
    subjects_path=pc_configs.SUBJECTS_CSV_PATH
):
    """Prepares a media link dataframe."""
    df_link = None
    subjects_df = pd.read_csv(subjects_path)
    for excel_filepath in utilities.list_excel_files(excel_dirpath):
        if not 'Media' in excel_filepath:
            continue
        dfs = utilities.read_excel_to_dataframes(excel_filepath)
        df_link = prepare_media_links_from_dfs(
            dfs,
            subjects_df
        )
    return df_link
