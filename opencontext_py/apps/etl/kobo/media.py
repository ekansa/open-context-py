import copy
import uuid as GenUUID
import os
import re
import shutil
import numpy as np
import pandas as pd
import rawpy
from unidecode import unidecode

from PIL import Image, ImageFile


from django.template.defaultfilters import slugify

from opencontext_py.apps.all_items.models import (
    AllManifest,
)
from opencontext_py.apps.all_items.legacy_all import update_old_id

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
    ('Primary Image_URL', 'link-primary', '_uuid', 'subject_uuid', None,),
    ('Supplemental Image_URL', 'link-supplemental', '_submission__uuid', 'subject_uuid', None,),
    ('Image File_URL', 'primary', '_uuid', 'media_uuid', None,),
    ('Video File_URL', 'primary', '_uuid', 'media_uuid', None,),
    ('Audio File_URL', 'primary', '_uuid', 'media_uuid', None,),

    # 2024
    ('Image_Sup', 'link-primary', '_uuid', 'subject_uuid', None,),
    ('Supplemental Image_URL', 'link-supplemental', '_submission__uuid', 'subject_uuid', None,),
    ('Image File_URL', 'primary', '_uuid', 'media_uuid', None,),
    ('Video File_URL', 'primary', '_uuid', 'media_uuid', None,),
    ('Audio File_URL', 'primary', '_uuid', 'media_uuid', None,),

    ('Image_URL', 'primary', '_uuid', 'media_uuid', 'media',),
    ('Video_URL', 'primary', '_uuid', 'media_uuid', 'media',),
    ('Video URL', 'primary', '_uuid', 'media_uuid', 'media',),
    ('Audio_URL', 'primary', '_uuid', 'media_uuid', 'media',),
    ('Audio URL', 'primary', '_uuid', 'media_uuid', 'media',),

    ('Image URL', 'primary', '_uuid', 'subject_uuid', None,),
    ('Image_Sup_URL', 'link-supplemental', '_submission__uuid', 'subject_uuid', None,),
    ('Image Sup URL', 'link-supplemental', '_submission__uuid', 'subject_uuid', None,),
]

MEDIA_DESCRIPTION_COLS_ENDSWITH = [
    'Note about Primary Image',
    'Note about Supplemental Image',
    'Image',
    'Image Sup',
    'Image Note',
    'File Title',
    'Media Title',
    'Date Metadata Recorded',
    'Date Created',
    'File Creator',
    'Data Entry Person',
    'Media Type',
    'Image Type',
    'Other Image Type Note',
    'Image Sup Note',
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
    'Field_Bulk': 'field-bulk-',
    'Field_Small': 'field-small-',
    'Locus': 'locus-',
    'Media': '',
    'Trench_Book': 'trench-book-',
}

MEDIA_SOURCE_COMPOSITION_TYPES = {
    'Catalog': 'Object (artifact, ecofact)',
    'Conservation': 'Conservation',
    'Field_Bulk': 'Field',
    'Field_Small': 'Field',
    'Locus': 'Field',
    'Trench_Book': 'Field',
}


MEDIA_ATTRIBUTES_SHEET = 'Media File Metadata Entry'
MEDIA_RELS_SHEET = 'Rel_ID_Group_Rep'


REL_COLS = [
    'subject_label',
    'subject_uuid',
    'subject_uuid_source',
    pc_configs.LINK_RELATION_TYPE_COL,
    'object_label',
    'object_uuid',
    'object_uuid_source',
    'object_related_id',
    'object_related_type',
    'Data Entry Person',
    'File Creator',
]


def make_deterministic_media_uuid(row):
    """Makes a deterministic media item uuid based on inputs"""
    # import pdb; pdb.set_trace()
    input = str(row['filename']) + ' ' + str(row['subject_uuid'])
    _, media_uuid = update_old_id(input)
    return media_uuid


def get_path_uuid_from_url(url):
    """Gets the path_uuid from the file URL"""
    if not '%2F' in url:
        return None
    url_ex = url.split('%2F')
    if len(url_ex) < 2:
        return None
    return url_ex[-2]


def get_filename_from_url(url):
    """Gets the filename from the file URL"""
    if not '%2F' in url:
        return None
    url_ex = url.split('%2F')
    return url_ex[-1]


def make_fs_filename(filename):
    """Makes a filesystem OK filename for linking purposes"""
    filename = filename.replace(' ', '_').replace(',', '')
    return filename


def make_oc_filename(filename):
    """Makes an Open Context filename to be URL friendly."""
    filename = filename.lower()
    ext = ''
    if '.' in filename:
        f_explode_raw = filename.split('.')
        f_explode = [p for p in f_explode_raw if p != '']
        ext = f'.{f_explode[-1]}'
        filename = '-'.join(f_explode[0:-1])
    ext = ext.replace('.jpeg', '.jpg')
    filename = slugify(unidecode(filename))
    filename = filename.replace(' ', '-').replace('_', '-').replace(',', '-')
    filename = filename.replace('----', '-').replace('---', '-').replace('--', '-')
    return filename + ext


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
                and col in ['Description', 'General Description', 'Updated Description']):
                # A total hack. We don't want to describe media
                # with field used to describe catalog objects.
                continue
            sheet_des_cols.append(col)
    if form_type == 'locus' and media_source_type == 'primary':
        # import pdb; pdb.set_trace()
        pass
    # Make a df_sheet_media dataframe that has the
    # media file name column, uuid column, and the
    # descriptive fields for the media.
    df_sheet_media = df[
        ([media_col, act_uuid] + sheet_des_cols)
    ].copy()
    # Drop null values for the media_col.
    null_index = df_sheet_media[media_col].isnull()
    df_sheet_media.loc[null_index, media_col] = np.nan
    df_sheet_media.dropna(subset=[media_col], inplace=True)
    df_sheet_media['filename'] = df_sheet_media[media_col].apply(get_filename_from_url)
    df_sheet_media['path_uuid'] = df_sheet_media[media_col].apply(get_path_uuid_from_url)
    df_sheet_media['media_source_type'] = media_source_type
    df_sheet_media['kobo_form'] = form_type
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
        if form_type == 'trench book' and 'Open Context Label' in df.columns:
            # This is a special case hack, because the trench book won't
            # have labels available on the subjects_df. So we'll bring in the
            # trench book labels as subject_labels via a merge.
            act_df = df.copy()
            act_df['subject_label'] = act_df['Open Context Label']
            act_df = act_df[[act_uuid, 'subject_label']]
            df_sheet_media = pd.merge(df_sheet_media, act_df, on=[act_uuid], how='left')
        df_sheet_media.rename(
            columns={act_uuid: new_uuid,},
            inplace=True
        )
    all_drop_cols = [media_col, '_uuid', '_submission__uuid',]
    drop_cols = [c for c in all_drop_cols if c in df_sheet_media.columns]
    df_sheet_media.drop(columns=drop_cols, inplace=True)
    df_sheet_media.reset_index(drop=True, inplace=True)
    if df_sheet_media.empty:
        return None
    if not 'media_uuid' in df_sheet_media.columns:
        # Make a deterministic media_uuid if not already present.
        df_sheet_media['media_uuid'] = df_sheet_media.apply(
            make_deterministic_media_uuid,
            axis=1
        )
        df_sheet_media['media_uuid_source'] = 'deterministic'
    else:
        df_sheet_media['media_uuid_source'] = pc_configs.UUID_SOURCE_KOBOTOOLBOX
    df_sheet_media = utilities.drop_empty_cols(df_sheet_media)
    df_sheet_media = utilities.update_multivalue_columns(df_sheet_media)
    df_sheet_media = utilities.clean_up_multivalue_cols(df_sheet_media)
    # Now make the 'subject_label' and 'subject_uuid' the objects
    # to keep things consistent, where the media item is the subject and
    # the associated other records are the objects.
    df_sheet_media['media_label'] = df_sheet_media['filename']
    
    print('-'*50)
    print(f'Sheet_df {form_type} {media_source_type}')
    print(df_sheet_media.columns.tolist())

    df_sheet_media.rename(
        columns={
            'subject_label': 'object_label',
            'subject_uuid': 'object_uuid',
            'subject_uuid_source': 'object_uuid_source',
        },
        inplace=True,
    )
    copy_cols = [
        ('media_label', 'subject_label',),
        ('media_uuid', 'subject_uuid',),
        ('media_uuid_source', 'subject_uuid_source',),
    ]
    for old_c, new_c in copy_cols:
        df_sheet_media[new_c] = df_sheet_media[old_c]
    return df_sheet_media


def make_dfs_media_df(dfs, file_form_type, subjects_df):
    """Makes a dataframe of media files from a dataframe dict."""
    df_media_list = []
    for media_col_end, media_source_type, act_uuid, new_uuid, form_type_only in MEDIAFILE_COLS_ENDSWITH:
        for sheet_name, df in dfs.items():
            form_type = file_form_type
            if form_type_only and form_type_only != form_type:
                # Skip this, because this configuration does not apply to the
                # current form type.
                continue
            if utilities.get_general_form_type_from_sheet_name(sheet_name):
                form_type = utilities.get_general_form_type_from_sheet_name(
                    sheet_name
                )
            # Fix underscores in column names
            df = utilities.fix_df_col_underscores(df)
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
    df_media = utilities.df_fill_in_by_shared_id_cols(
        df=df_media,
        col_to_fill='subject_label',
        id_cols=['subject_uuid'],
    )
    df_media = utilities.df_fill_in_by_shared_id_cols(
        df=df_media,
        col_to_fill='object_label',
        id_cols=['object_uuid'],
    )
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
        df_media['new_filename'] = df_media['filename'].apply(make_oc_filename)
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
    # Make sure everything has a uuid.
    df_all_media = utilities.not_null_subject_uuid(df_all_media)
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
    if src_file.lower().endswith('.nef'):
        print('Special loading process for a .nef file')
        try:
            raw = rawpy.imread(src_file)
            rgb = raw.postprocess()
            im = Image.fromarray(rgb)
        except Exception as e:
            print(e)
            print('Cannot load .nef image: ' + src_file)
            im = None
        return im, False
    try:
        im = Image.open(src_file)
        im.LOAD_TRUNCATED_IMAGES = True
    except:
        print('Cannot use as image: ' + src_file)
        im = None
    if im is None:
        return None, None
    if im.format_description == 'Adobe TIFF':
        selected_layer = 0
        im.seek(selected_layer)
        png = False
    return im, png

def replace_extension(filename, new_extension):
    if filename.endswith(f'.{new_extension}'):
        return filename
    f_ex = filename.split('.')
    return f'{f_ex[0]}.{new_extension}'

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
    if not png:
        # Make new files a jpg, unless it's a png.
        new_file = replace_extension(new_file, new_extension='jpg')
    if png:
        im.thumbnail(size, Image.LANCZOS)
        background = Image.new("RGB", im.size, (255, 255, 255))
        ok = None
        try:
            background.paste(im, mask=im.split()[3]) # 3 is the alpha channel
            background.save(new_file, "JPEG", quality=100)
            output = new_file
            ok = True
            del background
        except Exception as e:
            print(e)
            ok = False
        if not ok:
            new_file = replace_extension(new_file, new_extension='jpg')
            try:
                im.save(new_file, "JPEG", quality=100)
                output = new_file
                ok = True
            except Exception as e:
                print(e)
                ok = False
        if not ok:
            png = False
            raise RuntimeWarning(f'Problem with PNG changes from {src_file} to {new_file}')
    else:
        im = im.convert("RGB")
        im.thumbnail(size, Image.LANCZOS)
        try:
            im.save(new_file, "JPEG", quality=100)
            output = new_file
        except Exception as e:
            raise RuntimeWarning(f'Problem with saving changes rom {src_file} to {new_file}. {e}')
    im.close()
    return output


def make_file_version_dir_and_sub_dirs(
    new_file_name,
    file_version_dir,
    src_file,
    make_sub_dirs_within=None
):
    """Creates a full, preview, or thumb directory file path that may contain
    internal subdirectories if make_sub_dirs_within is a string"""
    if not make_sub_dirs_within:
        return os.path.join(file_version_dir, new_file_name)
    if not src_file.startswith(make_sub_dirs_within):
        return os.path.join(file_version_dir, new_file_name)
    # get the subdirectory that is contained within the make_sub_dirs_within
    sub_path_ex = src_file.split(make_sub_dirs_within)
    sub_path = sub_path_ex[-1]
    sub_path_list = sub_path.split('/')
    # iterate through the subdirectory hierarchy, skipping the last item which is the
    # filename.
    act_path = file_version_dir
    for sub_path in sub_path_list[:-1]:
        # make an Open Context URL friendly path from the sub_path
        sub_path = make_oc_filename(sub_path)
        act_path = set_check_directory(act_path, sub_path)
    return os.path.join(act_path, new_file_name)


def make_image_versions_src_and_new_file(
    dirs,
    src_file,
    new_file_name,
    over_write=False,
    preview_width=kobo_oc_configs.MAX_PREVIEW_WIDTH,
    thumbnail_width=kobo_oc_configs.MAX_THUMBNAIL_WIDTH,
    make_sub_dirs_within=None,
):
    """Make different file versions in different directories."""
    if not isinstance(src_file, str):
        return None
    if not os.path.exists(src_file):
        raise RuntimeError('Cannot find {}'.format(src_file))
    # full_file = os.path.join(dirs['full'], new_file_name)
    full_file = make_file_version_dir_and_sub_dirs(
        new_file_name,
        file_version_dir=dirs['full'],
        src_file=src_file,
        make_sub_dirs_within=make_sub_dirs_within,
    )
    if over_write or not os.path.exists(full_file):
        print('Copy full file {}'.format(new_file_name))
        shutil.copy2(src_file, full_file)
    mod_new_possible_files = [
        new_file_name,
        replace_extension(new_file_name, new_extension='jpg')
    ]
    for mod_new_file in mod_new_possible_files:
        # prev_file = os.path.join(dirs['preview'], mod_new_file)
        prev_file = make_file_version_dir_and_sub_dirs(
            new_file_name=mod_new_file,
            file_version_dir=dirs['preview'],
            src_file=src_file,
            make_sub_dirs_within=make_sub_dirs_within,
        )
        if over_write or not os.path.exists(prev_file):
            prev_file = make_new_size_file(src_file, prev_file, new_width=preview_width)
            print(f'Made preview {prev_file}')
            break
    for mod_new_file in mod_new_possible_files:
        # thumb_file = os.path.join(dirs['thumbs'], mod_new_file)
        thumb_file = make_file_version_dir_and_sub_dirs(
            new_file_name=mod_new_file,
            file_version_dir=dirs['thumbs'],
            src_file=src_file,
            make_sub_dirs_within=make_sub_dirs_within,
        )
        if over_write or not os.path.exists(thumb_file):
            thumb_file = make_new_size_file(src_file, thumb_file, new_width=thumbnail_width)
            print(f'Made thumbnail {thumb_file}')
            break
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
    make_sub_dirs_within=None,
):
    """Makes different file versions expected by Open Context."""
    df_media = pd.read_csv(all_media_kobo_files_path)
    dirs = get_make_directories(oc_media_root_dir, oc_sub_dirs=oc_sub_dirs)
    for col in ['MEDIA_URL_full', 'MEDIA_URL_preview', 'MEDIA_URL_thumbs']:
        if col in df_media.columns:
            continue
        df_media[col] = ''
    files_indx = (
        df_media['path'].notnull() & df_media['new_filename'].notnull()
    )
    for _, row in df_media[files_indx].iterrows():
        full_file, prev_file, thumb_file = make_image_versions_src_and_new_file(
            dirs,
            row['path'],
            row['new_filename'],
            make_sub_dirs_within=make_sub_dirs_within,
        )
        act_index = (df_media['path'] == row['path'])
        df_media.loc[act_index, 'MEDIA_URL_full'] = make_media_url(
            file_path=full_file,
            file_type='full'
        )
        if prev_file:
            df_media.loc[act_index, 'MEDIA_URL_preview'] = make_media_url(
                file_path=prev_file,
                file_type='preview'
            )
        if thumb_file:
            df_media.loc[act_index, 'MEDIA_URL_thumbs'] = make_media_url(
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


def get_prep_all_media_files_for_links(
    all_media_kobo_files_path=pc_configs.MEDIA_ALL_KOBO_REFS_CSV_PATH
):
    df_media = pd.read_csv(all_media_kobo_files_path)
    act_indx = (
        ~df_media['subject_uuid'].isnull()
    )
    if df_media[act_indx].empty:
        return None
    df_link = df_media[act_indx].copy()
    df_link.reset_index(drop=True, inplace=True)
    return df_link


def extract_links_df_from_all_media_df(
    all_media_kobo_files_path=pc_configs.MEDIA_ALL_KOBO_REFS_CSV_PATH
):
    """Make a links df from the all-media df"""
    df_link = get_prep_all_media_files_for_links(
        all_media_kobo_files_path
    )
    if df_link is None:
        return None
    print(df_link.columns.tolist())
    act_indx = (
        ~df_link['subject_uuid'].isnull()
        & ~df_link['object_uuid'].isnull()
    )
    if df_link[act_indx].empty:
        return None
    df_link = df_link[act_indx].copy()
    df_link[pc_configs.LINK_RELATION_TYPE_COL] = 'link'
    act_cols = [c for c in REL_COLS if c in df_link.columns]
    df_link = df_link[act_cols].copy()
    return df_link


def add_creator_links_from_all_media_df(
    df_links,
    all_media_kobo_files_path=pc_configs.MEDIA_ALL_KOBO_REFS_CSV_PATH
):
    df_other_link = get_prep_all_media_files_for_links(
        all_media_kobo_files_path
    )
    if df_other_link is None:
        return df_links
    for person_col in ['Data Entry Person', 'File Creator']:
        cols = ['subject_label', 'subject_uuid', 'subject_uuid_source', person_col]
        if not set(cols).issubset(set(df_other_link.columns.tolist())):
            continue
        df_orig = df_other_link[cols].copy()
        # Get the unique combination of the subjects and non-null creator values.
        act_index = ~df_orig[person_col].isnull()
        df = df_orig[act_index].groupby(cols, as_index=False).first()
        df.reset_index(drop=True, inplace=True)
        df = utilities.add_person_object_rels(
            df=df,
            person_col=person_col,
            link_rel='Photographed by',
        )
        ok_index = ~df['object_uuid'].isnull()
        if df[ok_index].empty:
            continue
        df_links.append(df)
    return df_links


def prep_links_df(dfs):
    """Prepares a dataframe of links between media items and related objects"""
    df_link, _ = utilities.get_df_by_sheet_name_part(
        dfs,
        sheet_name_part='Rel_ID'
    )
    if df_link is None:
        return None
    df_link = utilities.prep_df_link_cols(df_link)
    df_sub, _ = utilities.get_df_by_sheet_name_part(
        dfs,
        sheet_name_part='Media'
    )
    # Fixes underscore columns in df
    df_sub = utilities.fix_df_col_underscores(df_sub)
    missing_cols = [
        ('Media Title', 'File Title',),
    ]
    for f, r in missing_cols:
        if not r in df_sub.columns and f in df_sub.columns:
            df_sub[r] = df_sub[f]

    df_sub['subject_label'] = df_sub['File Title']
    df_sub['subject_uuid'] = df_sub['_uuid']
    df_sub['subject_uuid_source'] = pc_configs.UUID_SOURCE_KOBOTOOLBOX
    df_sub = df_sub[['subject_label', 'subject_uuid', 'subject_uuid_source']].copy()
    # Get rid of columns that we don't want, because we want to replace these with a merge
    # from df_sub
    bad_cols = [c for c in ['subject_label', 'subject_uuid_source'] if c in df_link.columns]
    df_link.drop(columns=bad_cols, inplace=True)
    # Now do the merge
    df_link = pd.merge(
        df_link,
        df_sub,
        how='left',
        on=['subject_uuid']
    )
    # Now look up the UUIDs for the objects.
    df_link['object_related_id'] = df_link['object_related_id'].astype(str)
    df_link['object_label'] = ''
    df_link['object_uuid'] = ''
    df_link['object_uuid_source'] = ''
    df_link[pc_configs.LINK_RELATION_TYPE_COL] = 'link'
    for _, row in df_link.iterrows():
        act_labels = None
        object_uuid = None
        object_uuid_source = None
        raw_object_id = row['object_related_id']
        object_type = row['object_related_type']
        act_labels = [str(raw_object_id)]
        if '2023' in str(raw_object_id):
            act_labels.append(str(raw_object_id).lower())
        act_prefixes, act_classes = pc_configs.REL_SUBJECTS_PREFIXES.get(object_type, ([], []))
        if len(act_classes) == 0:
            # Didn't find any classes in our object type lookup, so continue
            continue
        act_labels += [p + str(raw_object_id) for p in act_prefixes]        
        act_labels.append(utilities.normalize_catalog_label(raw_object_id))
        man_obj = db_lookups.db_reconcile_by_labels_item_class_slugs(
            label_list=act_labels,
            item_class_slug_list=act_classes,
        )
        if not man_obj:
            print(f'Cannot find raw_object_id: {raw_object_id}')
            # try to extract the related ID from the label of the media resource
            man_obj = db_lookups.get_related_object_from_item_label(
                item_label=row['subject_label']
            )
        if not man_obj:
            object_label = np.nan
            object_uuid = np.nan
            object_uuid_source = np.nan
        else:
            # Only accept a single result from the
            # lookup.
            object_label = man_obj.label
            object_uuid = str(man_obj.uuid)
            object_uuid_source = pc_configs.UUID_SOURCE_OC_LOOKUP
        up_indx = (
            (df_link['object_related_id'] == raw_object_id)
            & (df_link['object_related_type'] == object_type)
        )
        df_link.loc[up_indx, 'object_label'] = object_label
        df_link.loc[up_indx, 'object_uuid'] = object_uuid
        df_link.loc[up_indx, 'object_uuid_source'] = object_uuid_source
    cols = [c for c in REL_COLS if c in df_link.columns]
    df_link = df_link[cols].copy()
    return df_link


def fill_in_missing_catalog_links(df_all_links):
    """Fills in links to catalog objects based on the media label if missing object relations"""
    if df_all_links is None:
        return df_all_links
    if df_all_links.empty:
        return df_all_links
    req_cols = ['subject_label', 'subject_uuid', 'object_label', 'object_uuid', 'object_uuid_source', 'object_related_id']
    if not set(req_cols).issubset(set(df_all_links.columns.tolist())):
        return df_all_links
    df_subjects = pd.read_csv(pc_configs.SUBJECTS_CSV_PATH)
    index_missing_objs = (
        df_all_links['object_uuid'].isnull()
        & ~df_all_links['subject_label'].isnull()
        & ~df_all_links['subject_uuid'].isnull()
    )
    for _, row in df_all_links[index_missing_objs].iterrows():
        object_label = None
        object_uuid = None
        object_uuid_source = None
        subject_label = row['subject_label']
        subject_uuid = row['subject_uuid']
        object_related_id = row['object_related_id']
        man_obj = db_lookups.get_related_object_from_item_label(
            item_label=subject_label
        )
        if man_obj:
            object_label = man_obj.label
            object_uuid = str(man_obj.uuid)
            object_uuid_source = pc_configs.UUID_SOURCE_OC_LOOKUP
        if not object_uuid:
            object_label, object_uuid, object_uuid_source = utilities.get_missing_catalog_item_from_df_subjects(
                item_label=subject_label,
                df_subjects=df_subjects,
            )
        if not object_uuid and object_related_id:
            object_label, object_uuid, object_uuid_source = utilities.get_missing_catalog_item_from_df_subjects(
                item_label=object_related_id,
                df_subjects=df_subjects,
            )
        if not object_uuid:
            print(f'Cannot find object related to media: {subject_label} [{subject_uuid}]')
            continue
        up_indx = (
            (df_all_links['subject_uuid'] == subject_uuid)
        )
        df_all_links.loc[up_indx, 'object_label'] = object_label
        df_all_links.loc[up_indx, 'object_uuid'] = object_uuid
        df_all_links.loc[up_indx, 'object_uuid_source'] = object_uuid_source
        # print(f'Media item {subject_label} [{subject_uuid}] links with {object_label} [{object_uuid}] based on media label')
    return df_all_links


def prepare_media_links_df(
    excel_dirpath=pc_configs.KOBO_EXCEL_FILES_PATH,
    links_csv_path=pc_configs.MEDIA_ALL_LINKS_CSV_PATH,
):
    """Prepares a media link dataframe."""
    df_links = []
    for excel_filepath in utilities.list_excel_files(excel_dirpath):
        if not 'Media' in excel_filepath:
            continue
        dfs = utilities.read_excel_to_dataframes(excel_filepath)
        df_link = prep_links_df(
            dfs,
        )
        if df_link is not None:
            df_links.append(df_link)
    df_other_link = extract_links_df_from_all_media_df()
    if df_other_link is not None:
        df_links.append(df_other_link)
    # Use the all media df to find the media person creators.
    df_links = add_creator_links_from_all_media_df(df_links)
    if len(df_links) == 0:
        return None
    df_all_links = pd.concat(df_links)
    if df_all_links.empty:
        return None
    # Use label matching to associate images with missing objects
    df_all_links = fill_in_missing_catalog_links(df_all_links)
    if links_csv_path:
        df_all_links.to_csv(links_csv_path, index=False)
    return df_all_links
