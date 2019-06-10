import fnmatch
from time import sleep
import uuid as GenUUID
import os, sys, shutil
import codecs
import numpy as np
import pandas as pd

from PIL import Image, ImageFile
from django.db import models
from django.db.models import Q
from django.conf import settings
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.ocitems.mediafiles.models import Mediafile
from opencontext_py.apps.imports.kobotoolbox.utilities import (
    UUID_SOURCE_KOBOTOOLBOX,
    UUID_SOURCE_OC_KOBO_ETL,
    make_directory_files_df,
    list_excel_files,
    read_excel_to_dataframes,
    drop_empty_cols,
)

"""Uses Pandas to prepare Kobotoolbox exports for Open Context import

import csv
from django.conf import settings
from opencontext_py.apps.imports.kobotoolbox.media import (
    make_all_export_media_df,
    combine_media_with_files,
    prepare_media
)
from opencontext_py.apps.imports.kobotoolbox.utilities import (
    make_directory_files_df,
    lookup_manifest_uuid
)

files_path = settings.STATIC_IMPORTS_ROOT + 'pc-2018/attachments'
excels_filepath = settings.STATIC_IMPORTS_ROOT + 'pc-2018/'
oc_media_root_dir = settings.STATIC_IMPORTS_ROOT + 'pc-2018/2018-media'
all_media_csv_path = settings.STATIC_IMPORTS_ROOT + 'pc-2018/all-media-files.csv'
project_uuid = 'DF043419-F23B-41DA-7E4D-EE52AF22F92F'

df_media = make_all_export_media_df(excels_filepath)
df_files = make_directory_files_df(files_path)
df_all = combine_media_with_files(df_media, df_files)
print('All recs {} paths {}'.format(
        len(df_all.index),
        len(df_all['path'].unique().tolist())
    )
)

df_all = prepare_media(
    excels_filepath,
    files_path,
    oc_media_root_dir,
    project_uuid
)
df_all.to_csv(all_media_csv_path, index=False, quoting=csv.QUOTE_NONNUMERIC)

"""


MEDIAFILE_COLS_ENDSWITH = [
    ('/Primary Image', 'link-primary', '_uuid', 'link-uuid'),
    ('/Supplemental Image', 'link-supplemental', '_submission__uuid', 'link-uuid'),
    ('/Image File', 'primary', '_uuid', 'media-uuid'),
    ('/Video File', 'primary', '_uuid', 'media-uuid'),
    ('/Audio File', 'primary', '_uuid', 'media-uuid'),
]

MEDIA_DESCRIPTION_COLS_ENDSWITH = [
    '/Note about Primary Image',
    '/Note about Supplemental Image',
    'File Title', 
    'Date Metadata Recorded', 
    'Date Created', 
    'File Creator',  
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


OPENCONTEXT_MEDIA_DIRS = [
    'full',
    'preview',
    'thumbs',
]

MAX_PREVIEW_WIDTH = 650
MAX_THUMBNAIL_WIDTH = 150

def revise_filename(filename):
    """Revises a filename to be URL friendly."""
    filename = filename.lower()
    filename = filename.replace(' ', '-').replace('_', '-')
    return filename

def make_dfs_media_df(
    dfs,
    media_cols_endswith=None,
    describe_cols_endswith=None
):
    """Makes a dataframe of media files from a dataframe dict."""
    df_media_list = []
    if media_cols_endswith is None:
        media_cols_endswith = MEDIAFILE_COLS_ENDSWITH
    if describe_cols_endswith is None:
        describe_cols_endswith = MEDIA_DESCRIPTION_COLS_ENDSWITH
    for media_col_end, media_type, act_uuid, new_uuid in media_cols_endswith:
        for sheet, df in dfs.items():
            media_col = None
            if not act_uuid in df.columns:
                continue
            for col in df.columns:
                if not col.endswith(media_col_end):
                    continue
                media_col = col
                break
            if media_col is None:
                continue
            # We have found some columns for media files,
            # now gather the descriptive fields used with
            # these media.
            sheet_des_cols = []
            for des_col_end in describe_cols_endswith:
                for col in df.columns:
                    if not col.endswith(des_col_end):
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
            df_sheet_media['media-type'] = media_type
            df_sheet_media['sheet'] = sheet
            df_sheet_media.rename(
                columns={media_col: 'filename', act_uuid: new_uuid},
                inplace=True
            )       
            df_sheet_media.reset_index(drop=True, inplace=True)
            if df_sheet_media.empty:
                continue
            df_media_list.append(df_sheet_media)
    if not len(df_media_list):
        return None
    df_media = pd.concat(df_media_list)
    if df_media.empty:
        return None
    return df_media   

def make_all_export_media_df(
    excels_dirpath,
    media_cols_endswith=None,
    new_file_prefixes=None
):
    """Make a dataframe of all media in all export files."""
    if new_file_prefixes is None:
        new_file_prefixes = MEDIA_SOURCE_FILE_PREFIXS
    df_all_media_list = []
    for excel_filepath in list_excel_files(excels_dirpath):
        excel_file = os.path.basename(excel_filepath)
        dfs = read_excel_to_dataframes(excel_filepath)
        df_media = make_dfs_media_df(
            dfs,
            media_cols_endswith=media_cols_endswith
        )
        if df_media is None:
            continue
        df_media['source_file'] = excel_file
        df_media['new-filename'] = df_media['filename'].apply(revise_filename)
        for file_start, prefix in new_file_prefixes.items():
            if not excel_file.startswith(file_start):
                continue
            df_media['new-filename'] = prefix + df_media['new-filename']
        df_all_media_list.append(df_media)
    if not len(df_all_media_list):
        return None
    df_all_media = pd.concat(df_all_media_list)
    if df_all_media.empty:
        return None
    expected_len = len(df_all_media.index)
    if (len(df_all_media['new-filename'].unique().tolist()) != expected_len or
        len(df_all_media['filename'].unique().tolist()) != expected_len):
        raise RuntimeError(
            'Expected {}, but have {} filenames, and {} new-filenames'.format(
                expected_len,
                len(df_all_media['filename'].unique().tolist()),
                len(df_all_media['new-filename'].unique().tolist())
            )
        )
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
        oc_sub_dirs = OPENCONTEXT_MEDIA_DIRS
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
    output = None
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
    preview_width=MAX_PREVIEW_WIDTH,
    thumbnail_width=MAX_THUMBNAIL_WIDTH
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

def make_opencontext_file_versions(
    df_all,
    oc_media_root_dir,
    oc_sub_dirs=None
):
    """Makes different file versions expected by Open Context."""
    dirs = get_make_directories(oc_media_root_dir, oc_sub_dirs=oc_sub_dirs)
    df_all_use = df_all[
        df_all['path'].notnull() &
        df_all['new-filename'].notnull()
    ]
    print(df_all.head(10))
    for _, row in df_all_use.iterrows():
        full_file, prev_file, thumb_file = make_image_versions_src_and_new_file(
            dirs,
            row['path'],
            row['new-filename']
        )

def check_prepare_media_uuid(df_all, project_uuid):
    """Checks on the media-uuid, adding uuids that are needing."""
    df_all['media-created'] = np.nan
    df_all['media-uuid-source'] = np.nan
    df_working = df_all.copy()
    for i, row in df_working.iterrows():
        man_obj = None
        update_indx = (
            df_all['filename']==row['filename']
        )
        if isinstance(row['media-uuid'], str):
            man_obj = Manifest.objects.filter(
                uuid=row['media-uuid'],
                item_type='media',
                project_uuid=project_uuid
            ).first()
        else:
            # Check by matching the Kobo given file name and
            # link-uuid.
            man_obj = Manifest.objects.filter(
                item_type='media',
                project_uuid=project_uuid,
                sup_json__contains=row['filename'],
            ).filter(
                sup_json__contains=row['link-uuid']
            ).first()
        
        if man_obj is not None:
            df_all.loc[update_indx, 'media-uuid-source'] = man_obj.source_id
            df_all.loc[update_indx, 'media-created'] = man_obj.revised
            if not isinstance(row['media-uuid'], str):
                df_all.loc[update_indx, 'media-uuid'] = man_obj.uuid
        else:
            if not isinstance(row['media-uuid'], str):
                df_all.loc[update_indx, 'media-uuid'] = str(GenUUID.uuid4())
                df_all.loc[update_indx, 'media-uuid-source'] = UUID_SOURCE_OC_KOBO_ETL
            else:
                df_all.loc[update_indx, 'media-uuid-source'] = UUID_SOURCE_KOBOTOOLBOX
    return df_all

def prepare_media(
    excels_filepath,
    files_path,
    oc_media_root_dir,
    project_uuid
):
    """Prepares a dataframe consolidating media from all export excels."""
    df_media = make_all_export_media_df(excels_filepath)
    df_files = make_directory_files_df(files_path)
    df_all = combine_media_with_files(df_media, df_files)
    df_all = check_prepare_media_uuid(df_all, project_uuid)
    make_opencontext_file_versions(df_all, oc_media_root_dir)
    return df_all