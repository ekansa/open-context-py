
import re
from unidecode import unidecode

from django.template.defaultfilters import slugify


from opencontext_py.apps.persistent_ids.ezid.ezid import EZID, PRE_REGISTER_SHOULDER
from opencontext_py.apps.persistent_ids.ezid.metaark import metaARK
from opencontext_py.apps.persistent_ids.ezid.metadoi import metaDOI
from opencontext_py.apps.persistent_ids.ezid.manage import EZIDmanage

from opencontext_py.apps.all_items.models import (
    AllManifest,
    AllIdentifier,
)
from opencontext_py.apps.all_items.representations import item

"""
Test:
from opencontext_py.apps.persistent_ids.poggio_civitate import manage as pc_ids
from opencontext_py.apps.all_items.models import (
    AllManifest,
    AllIdentifier,
)

persistent_id_list, id_obj_list = pc_ids.create_pre_registered_ids_for_qs(
    filter_args={'source_id__contains': '2023'},
)


man_obj = AllManifest.objects.get(uuid='0274cd4d-25c9-4e68-9ee7-c2922063d507')
persistent_id, id_obj = pc_ids.create_pre_registered_ezid_and_oc_records(
    man_obj=man_obj,
    do_staging=False,
    id_type_key='pc',
    update_if_exists=True,
    show_ezid_resp=True,
)

proj_persistent_id, id_obj = pc_ids.create_update_pre_registered_ezid_and_oc_records_project_prefix()
id_objs = pc_ids.create_update_pre_registered_ezid_and_oc_records_project_id_types_prefix()

"""

PROJECT_UUID = 'df043419-f23b-41da-7e4d-ee52af22f92f'
PROJ_SLUG_PREFIX = '24-'


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
# 'ark:/28722/r2p24/' it is defined with EZID
ID_PREFIX = f'{PRE_REGISTER_SHOULDER}{PROJECT_PART}/'


PRE_REG_CONFIGS = {
    'pc': {
        'label': 'Cataloged, Registered Finds for the Poggio Civitate Site',
        'doc_uuid': '42b2a088-4828-4b57-bcba-2bd3071b442f',
        'filter_args': {
            'project_id': PROJECT_UUID,
            'item_type': 'subjects',
            'path__startswith': 'Europe/Italy/Poggio Civitate/',
            'item_class__slug__in': CATALOG_OBJECT_ITEM_CLASS_SLUGS,
            'label__istartswith': 'pc',
        },
    },
    'vdm': {
        'label': 'Cataloged, Registered Finds for the Vescovado di Murlo Site',
        'doc_uuid': '0d18afa8-7692-4db1-a083-47484e6e11c4',
        'filter_args': {
            'project_id': PROJECT_UUID,
            'item_type': 'subjects',
            'path__startswith': 'Europe/Italy/Vescovado di Murlo/',
            'item_class__slug__in': CATALOG_OBJECT_ITEM_CLASS_SLUGS,
            'label__istartswith': 'vdm',
        },
    },
    'bf': {
        'label': 'Bulk Finds Registration for the Murlo Project',
        'doc_uuid': '7f9f97ff-2e7a-46b2-a540-5b3cf334c556',
        'filter_args': {
            'project_id': PROJECT_UUID,
            'item_type': 'subjects',
            'item_class__slug': 'oc-gen-cat-sample-col',
        },
    },
    'fa': {
        'label': 'Animal Bone, Zooarchaeological Registration for the Murlo Project',
        'doc_uuid': '885adbd5-6608-4458-a9cb-fcadd241cb4c',
        'filter_args': {
            'project_id': PROJECT_UUID,
            'item_type': 'subjects',
            'item_class__slug': 'oc-gen-cat-animal-bone',
            'label__istartswith': 'fa',
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
    item label into a pre-registration ARK ID string.

    :param str label: The Manifest object label
    :param str id_type_key: The pre-registered ID type within the Murlo project

    returns str label (cleaned for use in an ID)
    """
    if not PRE_REG_CONFIGS.get(id_type_key):
        raise ValueError(f'Unknown id_type_key: {id_type_key}')
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
    """Uses a Manifest object label to make a pre-registered ID of a given
    id_type_key.

    :param str label: The Manifest object label
    :param str id_type_key: The preregistered ID type within the Murlo project
    :param str id_prefix: The prefix (scheme, shoulder part, project part)

    returns str pre-registered ID
    """
    if not PRE_REG_CONFIGS.get(id_type_key):
        raise ValueError(f'Unknown id_type_key: {id_type_key}')
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
    """Uses a Manifest object slug to make a pre-registered ID of a given
    id_type_key.

    :param str slug: The Manifest object slug
    :param str id_type_key: The preregistered ID type within the Murlo project
    :param str id_prefix: The prefix (scheme, shoulder part, project part)

    returns str pre-registered ID
    """
    if not slug:
        return None
    if not PRE_REG_CONFIGS.get(id_type_key):
        raise ValueError(f'Unknown id_type_key: {id_type_key}')
    len_slug_prefix = len(strip_slug_prefix)
    if slug.startswith(strip_slug_prefix) and len(slug) > len_slug_prefix:
        slug = slug[len_slug_prefix:]
    slug = clean_labeling_str_for_ark(slug, id_type_key)
    if not slug:
        return None
    return f'{id_prefix}{id_type_key}_{slug}'


def is_valid_preregistered_id(check_id):
    """Validates allowed characters and patterns for a pre-registered ID

    :param str check_id: An ARK identifier that we want to check to see if
        it is a string with valid characters

    returns bool (True if valid, False if not valid)
    """
    if not check_id:
        return False
    if not isinstance(check_id, str):
        return False
    if check_id.startswith('ark:/'):
        check_id = check_id.split('ark:/')[-1]
    return re.match(r"^[a-z0-9_]+(?:/[a-z0-9_]+)*\.?[a-z0-9_]+$", check_id) is not None


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


def determine_item_type_key_for_man_obj(man_obj):
    """Get the item type key for a given manifest object by checking
    to see if the manifest object is within the filter query set for
    each given item type key

    :param AllManifest man_obj: The item for which we want to know the
        applicable id_type_key

    returns str (id_type_key or None if not found)
    """
    for item_type_key, conf_dict in PRE_REG_CONFIGS.items():
        match_obj = AllManifest.objects.filter(
            **conf_dict['filter_args']
        ).filter(
            uuid=man_obj.uuid
        ).first()
        if not match_obj:
            # This manifest object doesn't match the query criteria
            # for this item_type_key, so continue
            continue
        # The manifest object matches the filter criteria for tis
        # item_type_key!
        return item_type_key
    # No matches found.
    return None


def get_existing_preregistered_id_obj_for_man_obj(man_obj, id_prefix=ID_PREFIX,):
    """Gets and existing (if present) pre-registered ID for a Manifest object with a
    given id_prefix

    :param AllManifest man_obj: The item that may have a preregistered ID.
    :param str id_prefix: The prefix (scheme, shoulder part, project part)

    returns str a validated, unique pre-registered ID
    """
    if id_prefix.startswith('ark:/'):
        query_id = id_prefix.split('ark:/')[-1]
    else:
        query_id = id_prefix
    id_obj = AllIdentifier.objects.filter(
        item=man_obj,
        scheme='ark',
        id__startswith=query_id,
    ).first()
    return id_obj


def get_or_make_preregistered_id_for_man_obj(
    man_obj,
    id_type_key=None,
    id_prefix=ID_PREFIX,
):
    """Makes a valid pre-registered ID for a Manifest object of a given id_type_key

    :param AllManifest man_obj: The item that will get a valid preregistered ID.
    :param str id_type_key: The preregistered ID type within the Murlo project
    :param str id_prefix: The prefix (scheme, shoulder part, project part)

    returns str, id_obj (a validated and unique pre-registered ID, existing id object record)
    """
    id_obj = get_existing_preregistered_id_obj_for_man_obj(
        man_obj,
        id_prefix=id_prefix,
    )
    if id_obj:
        # Return the existing pre-registered ID, and is_new=False
        return f'ark:/{id_obj.id}', id_obj
    # OK, we don't already have a pre-registered ID object for this
    # manifest item, so go make one.
    if not id_type_key:
        id_type_key = determine_item_type_key_for_man_obj(man_obj)
    if not id_type_key:
        # The manifest object does not seem to match the correct criteria
        # for ID pre-registration
        return None, None
    # Make pre-registered ID
    preregistered_id = create_preregistered_id_from_label(
        label=man_obj.label,
        id_type_key=id_type_key,
        id_prefix=id_prefix,
    )
    if not is_valid_preregistered_id(preregistered_id):
        # We failed to make a valid pre-registered ID
        raise ValueError(f'{man_obj.label} [{str(man_obj.uuid)}] led to invalid ark: {preregistered_id}')
    # Now check to see if we have a clashing use of the preregistered_id
    clashing_obj = get_manifest_obj_using_ark_id(man_obj, preregistered_id)
    if clashing_obj:
        raise ValueError(
            f'Cannot use {preregistered_id} for item: {man_obj.label} [{str(man_obj.uuid)}], '
            f'ID already used by item: {clashing_obj.label} [{str(clashing_obj.uuid)}] '
        )
    # Return the valid preregistered_id, and id_obj=None
    return preregistered_id, None


def create_update_pre_registered_ezid_and_oc_records_project_prefix(
    do_staging=False,
    update_if_exists=True,
    show_ezid_resp=False,
    ezid_client=None,
):
    """Makes pre-registered ID and records it in EZID and Open Context for the Murlo
    project.

    :param bool do_staging: Use the staging site for EZID requests
    :param bool update_if_exists: Update EZID metadata if we already have a record for a
        pre-registered ID
    :param bool show_ezid_resp: Show raw request response text from EZID
    :param EZID ezid_client: An instance of the EZID (ezid_client) class

    returns str, id_obj (a validated and unique pre-registered ID, id object record)
    """
    man_obj = AllManifest.objects.get(uuid=PROJECT_UUID)
    ezid_m = EZIDmanage()
    metadata = ezid_m.make_ark_metadata_by_uuid(man_obj=man_obj)
    oc_uri = metadata.get('_target', f'https://{man_obj.uri}')
    if not ezid_client:
        ezid_client = EZID()
    if do_staging:
        # Make requests to the staging server
        ezid_client.use_staging_site()
    preregistered_id = f'{PRE_REGISTER_SHOULDER}{PROJECT_PART}'
    ezid_client.create_ark_identifier(
        oc_uri=oc_uri,
        metadata=metadata,
        id_str=preregistered_id,
        update_if_exists=update_if_exists,
        show_ezid_resp=show_ezid_resp,
    )
    # Now save the stable ID.
    if preregistered_id.startswith('ark:/'):
        stable_id = preregistered_id.split('ark:/')[-1]
    else:
        stable_id  = preregistered_id
    # Make an ID object to save the record of this pre-registered ID.
    id_obj = ezid_m.save_man_obj_stable_id(man_obj=man_obj, stable_id=stable_id, scheme='ark',)
    print(f'{man_obj.label} [{str(man_obj.uuid)}] **SAVED** preregistered_id record: {preregistered_id}')
    return preregistered_id, id_obj


def create_update_pre_registered_ezid_and_oc_records_project_id_types_prefix(
    do_staging=False,
    update_if_exists=True,
    show_ezid_resp=False,
    ezid_client=None,
    id_prefix=ID_PREFIX,
):
    """Makes pre-registered ID and records them in EZID and Open Context for different types
    of identifiers used within the Murlo project.

    :param bool do_staging: Use the staging site for EZID requests
    :param bool update_if_exists: Update EZID metadata if we already have a record for a
        pre-registered ID
    :param bool show_ezid_resp: Show raw request response text from EZID
    :param EZID ezid_client: An instance of the EZID (ezid_client) class

    returns str, id_obj (a validated and unique pre-registered ID, id object record)
    """
    id_objs = []
    for id_type_key, conf_dict in PRE_REG_CONFIGS.items():
        man_obj = AllManifest.objects.get(uuid=conf_dict.get('doc_uuid'))
        ezid_m = EZIDmanage()
        metadata = ezid_m.make_ark_metadata_by_uuid(man_obj=man_obj)
        oc_uri = metadata.get('_target', f'https://{man_obj.uri}')
        if not ezid_client:
            ezid_client = EZID()
        if do_staging:
            # Make requests to the staging server
            ezid_client.use_staging_site()
        preregistered_id = f'{id_prefix}{id_type_key}'
        ezid_client.create_ark_identifier(
            oc_uri=oc_uri,
            metadata=metadata,
            id_str=preregistered_id,
            update_if_exists=update_if_exists,
            show_ezid_resp=show_ezid_resp,
        )
        # Now save the stable ID.
        if preregistered_id.startswith('ark:/'):
            stable_id = preregistered_id.split('ark:/')[-1]
        else:
            stable_id  = preregistered_id
        # Make an ID object to save the record of this pre-registered ID.
        id_obj = ezid_m.save_man_obj_stable_id(man_obj=man_obj, stable_id=stable_id, scheme='ark',)
        print(f'{man_obj.label} [{str(man_obj.uuid)}] **SAVED** preregistered_id record: {preregistered_id}')
        id_objs.append(id_obj)
    return id_objs


def create_pre_registered_ezid_and_oc_records(
    uuid=None,
    man_obj=None,
    do_staging=False,
    id_type_key=None,
    id_prefix=ID_PREFIX,
    update_if_exists=True,
    show_ezid_resp=False,
    ezid_client=None,
):
    """Makes a valid pre-registered ID and records them in EZID and Open Context

    :param str/uuid uuid: UUID identifier for the item that will get a valid preregistered ID.
    :param AllManifest man_obj: The item that will get a valid preregistered ID.
    :param bool do_staging: Use the staging site for EZID requests
    :param str id_type_key: The preregistered ID type within the Murlo project
    :param str id_prefix: The prefix (scheme, shoulder part, project part)
    :param bool update_if_exists: Update EZID metadata if we already have a record for a
        pre-registered ID
    :param bool show_ezid_resp: Show raw request response text from EZID
    :param EZID ezid_client: An instance of the EZID (ezid_client) class

    returns str, id_obj (a validated and unique pre-registered ID, id object record)
    """
    if not uuid and man_obj:
        # We have a manifest object
        uuid = man_obj.uuid
    elif not man_obj and uuid:
        man_obj = AllManifest.objects.get(uuid=uuid)
    else:
        raise ValueError('Must provide either an AllManifest uuid or an AllManifest object')
    # Make a preregistered id for the man_obj
    preregistered_id, id_obj = get_or_make_preregistered_id_for_man_obj(
        man_obj=man_obj,
        id_type_key=id_type_key,
        id_prefix=id_prefix,
    )
    if id_obj and not update_if_exists:
        print(f'{man_obj.label} [{str(man_obj.uuid)}] already has a preregistered_id record: {preregistered_id}')
        return preregistered_id, id_obj
    # Make the ARK metadata for this record.
    ezid_m = EZIDmanage()
    metadata = ezid_m.make_ark_metadata_by_uuid(man_obj=man_obj, verbatim_id=man_obj.label)
    if not metadata:
        raise ValueError(f'Could not generate ARK metadata for {man_obj.label} [{str(man_obj.uuid)}]')
    # Set up the EZID client
    if not ezid_client:
        ezid_client = EZID()
    if do_staging:
        # Make requests to the staging server
        ezid_client.use_staging_site()
    # The oc_uri should be in the _target, with a fallback of our manifest object uri attribute
    oc_uri = metadata.get('_target', f'https://{man_obj.uri}')
    ezid_client.create_ark_identifier(
        oc_uri=oc_uri,
        metadata=metadata,
        id_str=preregistered_id,
        update_if_exists=update_if_exists,
        show_ezid_resp=show_ezid_resp,
    )
    if do_staging:
        print(f'{man_obj.label} [{str(man_obj.uuid)}], no ID object saved in Open Context; using EZID staging site for preregistered_id: {preregistered_id}')
        return preregistered_id, None
    # Now save the stable ID.
    if preregistered_id.startswith('ark:/'):
        stable_id = preregistered_id.split('ark:/')[-1]
    else:
        stable_id  = preregistered_id
    # Make an ID object to save the record of this pre-registered ID.
    id_obj = ezid_m.save_man_obj_stable_id(man_obj=man_obj, stable_id=stable_id, scheme='ark',)
    print(f'{man_obj.label} [{str(man_obj.uuid)}] **SAVED** preregistered_id record: {preregistered_id}')
    return preregistered_id, id_obj


def create_pre_registered_ids_for_qs(
        filter_args=None,
        exclude_args=None,
        do_staging=False,
        id_prefix=ID_PREFIX,
        update_if_exists=True,
        show_ezid_resp=False,
    ):
    """Create pre-registered IDs for items in an AllManifest query-set

    :param dict filter_args: Optional dict of filter args to filter the
        AllManifest query set
    :param dict exclude_args: Optional dict of exclude args to use as
        exclusion criteria in an AllManifest query set
    :param bool do_staging: Use the staging site for EZID requests
    :param str id_prefix: The prefix (scheme, shoulder part, project part)
    :param bool update_if_exists: Update EZID metadata if we already have a record for a
        pre-registered ID
    :param bool show_ezid_resp: Show raw request response text from EZID

    returns preregistered_id_list, id_obj_list
    """
    preregistered_id_list = []
    id_obj_list = []
    for id_type_key, type_conf in PRE_REG_CONFIGS.items():
        m_qs = AllManifest.objects.filter(
            **type_conf['filter_args']
        )
        if filter_args:
            m_qs = m_qs.filter(**filter_args)
        if exclude_args:
            m_qs = m_qs.exclude(**exclude_args)
        print(f'Working on {id_type_key}, manifest object count: {m_qs.count()}')
        for man_obj in m_qs:
            preregistered_id, id_obj = create_pre_registered_ezid_and_oc_records(
                man_obj=man_obj,
                do_staging=do_staging,
                id_type_key=id_type_key,
                id_prefix=id_prefix,
                update_if_exists=update_if_exists,
                show_ezid_resp=show_ezid_resp,
            )
            preregistered_id_list.append(preregistered_id)
            id_obj_list.append(id_obj)
    return preregistered_id_list, id_obj_list