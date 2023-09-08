import datetime
from unidecode import unidecode

from django.template.defaultfilters import slugify


from opencontext_py.apps.persistent_ids.ezid.ezid import EZID
from opencontext_py.apps.persistent_ids.ezid.metaark import metaARK
from opencontext_py.apps.persistent_ids.ezid.metadoi import metaDOI

from opencontext_py.apps.all_items.models import (
    AllManifest,
    AllIdentifier,
)
from opencontext_py.apps.all_items.representations import item



PROJECT_UUID = 'df043419-f23b-41da-7e4d-ee52af22f92f'
PROJ_SLUG_PREFIX = '24-'


PRE_REGISTER_SHOULDER = 'ark:/28722/r2'

PROJECT_PART = 'p24' # For Murlo project

# The item_class slugs that help select manifest records
# associated with 'catalog' records from the Murlo project.
CATALOG_OBJECT_ITEM_CLASS_SLUGS = [
    'oc-gen-cat-object',
    'oc-gen-cat-arch-element',
    'oc-gen-cat-coin',
    'oc-gen-cat-bio-subj-ecofact',
    'oc-gen-cat-pottery',
]

# The ARK pre-registered prefix for this project. Will be:
# 'ark:/28722/r2p24/'
ID_PREFIX = f'{PRE_REGISTER_SHOULDER}{PROJECT_PART}/'


PRE_REG_CONFIGS = {
    'pc': {
        'label': 'Cataloged, Registered Finds for the Poggio Civitate site',
        'filter_args': {
            'project_id': PROJECT_UUID,
            'item_type': 'subjects',
            'path__startswith': 'Europe/Italy/Poggio Civitate/',
            'item_class__slug_in': CATALOG_OBJECT_ITEM_CLASS_SLUGS,
        },
    },
    'vdm': {
        'label': 'Cataloged, Registered Finds for the Vescovado di Murlo site',
        'filter_args': {
            'project_id': PROJECT_UUID,
            'item_type': 'subjects',
            'path__startswith': 'Europe/Italy/Vescovado di Murlo/',
            'item_class__slug_in': CATALOG_OBJECT_ITEM_CLASS_SLUGS,
        },
    },
    'bf': {
        'label': 'Bulk Finds Registration',
        'filter_args': {
            'project_id': PROJECT_UUID,
            'item_type': 'subjects',
            'item_class__slug': 'oc-gen-cat-sample-col',
        },
    },
    'fa': {
        'label': 'Animal Bone, Zooarchaeological Registration',
        'filter_args': {
            'project_id': PROJECT_UUID,
            'item_type': 'subjects',
            'item_class__slug': 'oc-gen-cat-animal-bone',
        },
    },
}

LABEL_CHAR_REPLACEMENTS = {
    '-': '_',
    '.': '_',
    ' ': '_',
    '(': '_',
    ')': '_',
}

# Remove these parts of the label of bulk finds.
BULK_CHAR_REPLACEMENTS = {
    'ceramic': '',
    'tile': '',
    'stone': '',
    'bone': '',
    'architectural': '',
    'architecture': '',
    'metal': '',
    'plaster': '',
    'other': '',
}


def clean_labeling_str_for_ark(label, id_type_key):
    """Converts a (hopefully unique with the context of the project)
    item label into a pre-registeration ARK ID string.
    """
    len_id_type_key = len(id_type_key)
    label = str(label).lower().strip()
    if id_type_key == 'bf':
        for f, r in BULK_CHAR_REPLACEMENTS.items():
            label = label.replace(f, r)
    for f, r in LABEL_CHAR_REPLACEMENTS.items():
        label = label.replace(f, r)
    if label.startswith(id_type_key) and len(label) > len_id_type_key:
        label = label[len_id_type_key:]
    # Use the django slugify library to make sure we're OK with characters
    label = slugify(unidecode(label))
    # ARKs ignore '-' characters, so replace with an underscore
    label = label.replace('-', '_')
    if label.startswith('_'):
        label = label[1:]
    if label.endswith('_'):
        label = label[:-1]
    while '__' in label:
        label = label.replace('__', '_')
    return label


def create_preregistered_id_from_label(label, id_type_key, id_prefix=ID_PREFIX):
    if not label:
        return None
    label = clean_labeling_str_for_ark(label, id_type_key)
    if not label:
        return None
    return f'{id_prefix}{id_type_key}_{label}'


def create_preregistered_id_from_slug(
    slug,
    id_type_key,
    id_prefix=ID_PREFIX,
    strip_slug_prefix=PROJ_SLUG_PREFIX
):
    if not slug:
        return None
    len_slug_prefix = len(strip_slug_prefix)
    if slug.startswith(strip_slug_prefix) and len(slug) > len_slug_prefix:
        slug = slug[len_slug_prefix:]
    slug = clean_labeling_str_for_ark(slug, id_type_key)
    if not slug:
        return None
    return f'{id_prefix}{id_type_key}_{slug}'


def get_manifest_obj_using_ark_id(check_man_obj, check_id):
    """Checks to see if the check_id is already in use with a manifest record
    other than the check_man_obj

    :param AllManifest check_man_obj: The item that we want to check to see
        if we can use check_id without clashing with other manifest records
    :param str check_id: An ARK identifier that we want to check to see if
        it is in use with a manifest record OTHER than check_man_obj

    returns AllManifest that clashes (or None, if no clash)
    """
    # Open Context currently doesn't store the 'ark:/' part as part of the
    # ID in the database. So remove it if present.
    if check_id.startswith('ark:/'):
        query_id = check_id.split('ark:/')[-1]
    else:
        query_id = check_id
    # This should return None, if it returns a record, then we've
    # got a clashing ID problem.
    clashing_id = AllIdentifier.objects.filter(
        scheme='ark',
        id=query_id,
    ).exclude(
        item=check_man_obj,
    ).first()
    if not clashing_id:
        # The happy, expected scenario where there is record of this
        # check_id identifier in use with a different manifest
        # object.
        return None
    # The sad, unexpected scenario where we already have a different
    # manifest record that has the same check_id
    return clashing_id.item
