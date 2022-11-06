import copy
import os
import shutil
import numpy as np
import pandas as pd
from unidecode import unidecode

from PIL import Image, ImageFile


from django.template.defaultfilters import slugify

from opencontext_py.apps.all_items import configs


"""General utilities to manage media files, especially image files in
preparation for import

import importlib
from opencontext_py.apps.etl.general import image_media as imm
importlib.reload(imm)

imm.OK_HUGE_IMAGES = True
df = imm.inventory_make_oc_files(
    media_files_path='/home/ekansa/github/open-context-py/static/imports/micromorph-thinsection-images',
    media_inventory_csv_path='/home/ekansa/github/open-context-py/static/imports/micromorph-thinsection-images.csv',
    oc_media_root_dir='/home/ekansa/github/open-context-py/static/imports/mallol-micomorphology',
    media_base_url='https://artiraq.org/static/opencontext/mallol-micomorphology/',
)

"""

OK_HUGE_IMAGES = False

OPENCONTEXT_MEDIA_FULL_DIR = 'full'
OPENCONTEXT_MEDIA_PREVIEW_DIR = 'preview'
OPENCONTEXT_MEDIA_THUMBS_DIR = 'thumbs'

OPENCONTEXT_MEDIA_DIRS = [
    OPENCONTEXT_MEDIA_FULL_DIR,
    OPENCONTEXT_MEDIA_PREVIEW_DIR,
    OPENCONTEXT_MEDIA_THUMBS_DIR,
]

OPENCONTEXT_MEDIA_TYPES = [
    {
        'dir': OPENCONTEXT_MEDIA_FULL_DIR,
        'col': f'MEDIA_URL_{OPENCONTEXT_MEDIA_FULL_DIR}',
        'resourcetype': configs.OC_RESOURCE_FULLFILE_UUID,
    },
    {
        'dir': OPENCONTEXT_MEDIA_PREVIEW_DIR,
        'col': f'MEDIA_URL_{OPENCONTEXT_MEDIA_PREVIEW_DIR}',
        'resourcetype': configs.OC_RESOURCE_PREVIEW_UUID,
    },
    {
        'dir': OPENCONTEXT_MEDIA_THUMBS_DIR,
        'col': f'MEDIA_URL_{OPENCONTEXT_MEDIA_THUMBS_DIR}',
        'resourcetype': configs.OC_RESOURCE_THUMBNAIL_UUID,
    },
]

OPENCONTEXT_URL_COLS = [(f'URL_{d_type}', d_type,) for d_type in OPENCONTEXT_MEDIA_DIRS]

MAX_PREVIEW_WIDTH = 650
MAX_THUMBNAIL_WIDTH = 150



def make_oc_filename(filename):
    """Makes an Open Context filename to be URL friendly."""
    filename = filename.lower()
    ext = ''
    if '.' in filename:
        f_explode = filename.split('.')
        ext = f'.{f_explode[-1]}'
        filename = '-'.join(f_explode[0:-1])
    ext = ext.replace('.jpeg', '.jpg')
    filename = slugify(unidecode(filename))
    filename = filename.replace(' ', '-').replace('_', '-').replace(',', '-')
    filename = filename.replace('----', '-').replace('---', '-').replace('--', '-')
    return filename + ext


def make_directory_files_df(media_files_path):
    """Makes a dataframe listing all the files a Kobo Attachments directory."""
    file_data = []
    for dirpath, _, filenames in os.walk(media_files_path):
        for filename in filenames:
            if filename.endswith(':Zone.Identifier'):
                # A convenience hack for Windows subsystem for linux
                continue
            file_path = os.path.join(dirpath, filename)
            rec = {
                'path': file_path,
                'filename': filename,
                'new_filename': make_oc_filename(filename),
            }
            file_data.append(rec)
    df = pd.DataFrame(data=file_data)
    return df


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
    png = False
    if src_file.lower().endswith('.png'):
        png = True
    if src_file == new_file:
        return None, None
    if not os.path.exists(src_file):
        raise RuntimeError('Cannot find ' + src_file)
    ImageFile.LOAD_TRUNCATED_IMAGES = True
    if OK_HUGE_IMAGES:
        Image.MAX_IMAGE_PIXELS = None
    try:
        im = Image.open(src_file)
        im.LOAD_TRUNCATED_IMAGES = True
    except:
        print('Cannot use as image: ' + src_file)
        im = None
    if im is None:
        return None, None
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
        im.thumbnail(size, Image.ANTIALIAS)
        background = Image.new("RGB", im.size, (255, 255, 255))
        ok = None
        try:
            background.paste(im, mask=im.split()[3]) # 3 is the alpha channel
            background.save(new_file, "JPEG", quality=100)
            output = new_file
            ok = True
            del background
        except:
            ok = False
        if not ok:
            new_file = replace_extension(new_file, new_extension='jpg')
            try:
                im.save(new_file, "JPEG", quality=100)
                output = new_file
                ok = True
            except:
                ok = False
        if not ok:
            png = False
            raise RuntimeWarning(f'Problem with PNG changes from {src_file} to {new_file}')
    else:
        im.thumbnail(size, Image.ANTIALIAS)
        try:
            im.save(new_file, "JPEG", quality=100)
            output = new_file
        except:
            raise RuntimeWarning(f'Problem with saving changes rom {src_file} to {new_file}')
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
    if over_write or not os.path.exists(full_file):
        print('Copy full file {}'.format(new_file_name))
        shutil.copy2(src_file, full_file)
    mod_new_possible_files = [
        new_file_name,
        replace_extension(new_file_name, new_extension='jpg')
    ]
    for mod_new_file in mod_new_possible_files:
        prev_file = os.path.join(dirs['preview'], mod_new_file)
        if over_write or not os.path.exists(prev_file):
            prev_file = make_new_size_file(src_file, prev_file, new_width=preview_width)
            print(f'Made preview {prev_file}')
            break
    for mod_new_file in mod_new_possible_files:
        thumb_file = os.path.join(dirs['thumbs'], mod_new_file)
        if over_write or not os.path.exists(thumb_file):
            thumb_file = make_new_size_file(src_file, thumb_file, new_width=thumbnail_width)
            print(f'Made thumbnail {thumb_file}')
            break
    return full_file, prev_file, thumb_file


def make_media_url(file_path, file_type, media_base_url=''):
    """Makes a media URL for a give file type"""
    type_dir = f'/{file_type}/'
    if not type_dir in file_path:
        return None
    f_ex = file_path.split(type_dir)
    return f'{media_base_url}{type_dir}{f_ex[-1]}'


def make_opencontext_file_versions(
    media_inventory_csv_path,
    oc_media_root_dir,
    media_base_url='',
    oc_sub_dirs=None,
):
    """Makes different file versions expected by Open Context."""
    if not oc_sub_dirs:
        oc_sub_dirs = copy.deepcopy(OPENCONTEXT_MEDIA_DIRS)
    df_media = pd.read_csv(media_inventory_csv_path)
    dirs = get_make_directories(oc_media_root_dir, oc_sub_dirs=oc_sub_dirs)
    for col in ['MEDIA_URL_full', 'MEDIA_URL_preview', 'MEDIA_URL_thumbs']:
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
        df_media.loc[act_index, 'MEDIA_URL_full'] = make_media_url(
            file_path=full_file,
            file_type='full',
            media_base_url=media_base_url,
        )
        df_media.loc[act_index, 'MEDIA_URL_preview'] = make_media_url(
            file_path=prev_file,
            file_type='preview',
            media_base_url=media_base_url,
        )
        df_media.loc[act_index, 'MEDIA_URL_thumbs'] = make_media_url(
            file_path=thumb_file,
            file_type='thumbs',
            media_base_url=media_base_url,
        )
    df_media.to_csv(media_inventory_csv_path, index=False)
    return df_media


def inventory_make_oc_files(
    media_files_path,
    media_inventory_csv_path,
    oc_media_root_dir,
    media_base_url='',
):
    """Generates a CSV inventory of media files from a contributor, and makes
    different file versions expected by Open Context.

    :param str media_files_path: The root directory of the contributor's media
        files
    :param str media_inventory_csv_path: The filename and path for the CSV file
        that inventories the media files and their Open Context versions
    :param str oc_media_root_dir: The root directory path for where the Open
        Context versions of the media files are stored

    returns DataFrame df_media (a dataframe of the file inventory)
    """
    df_media = make_directory_files_df(media_files_path)
    df_media.to_csv(media_inventory_csv_path, index=False)
    df_media = make_opencontext_file_versions(
        media_inventory_csv_path=media_inventory_csv_path,
        oc_media_root_dir=oc_media_root_dir,
        media_base_url=media_base_url,
    )
    return df_media