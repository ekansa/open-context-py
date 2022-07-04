import copy
import os

from opencontext_py.apps.all_items import configs


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
