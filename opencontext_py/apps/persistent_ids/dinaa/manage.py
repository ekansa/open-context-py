
import re
import traceback

from django.db.models import OuterRef, Subquery

from django.template.defaultfilters import slugify


from opencontext_py.apps.persistent_ids.ezid.ezid import EZID, PRE_REGISTER_SHOULDER
from opencontext_py.apps.persistent_ids.ezid.metaark import metaARK
from opencontext_py.apps.persistent_ids.ezid.metadoi import metaDOI
from opencontext_py.apps.persistent_ids.ezid.manage import EZIDmanage
from opencontext_py.apps.persistent_ids.preregister import utilities as prereg_utils

from opencontext_py.apps.all_items.models import (
    AllManifest,
    AllAssertion,
    AllIdentifier,
)
from opencontext_py.apps.all_items.representations import item

"""
Test:
from opencontext_py.apps.persistent_ids.dinaa import manage as dinaa_ids
from opencontext_py.apps.all_items.models import (
    AllManifest,
    AllIdentifier,
)

from opencontext_py.apps.persistent_ids.dinaa import manage as dinaa_ids
m_qs = dinaa_ids.get_dinaa_sites_queryset()
for project_uuid in dinaa_ids.PROJECT_UUIDS:
    am_qs = m_qs.filter(project_id=project_uuid)
    for man_obj in am_qs[:500]:
        preregistered_id, _ = dinaa_ids.get_or_make_preregistered_id_for_man_obj(man_obj)
        print(f'Site {man_obj.label} [{man_obj.uuid}]: {preregistered_id}')

        

from opencontext_py.apps.persistent_ids.dinaa import manage as dinaa_ids
dinaa_ids.create_pre_registered_county_state_ids_for_qs()        
"""

NON_UNIQUE_PID_HANDLING = 'db_store'  # or 'raise'


# DINAA PROJECT UUID
PROJECT_UUID = '416a274c-cf88-4471-3e31-93db825e9e4a'
PROJECT_UUIDS = [str(m.uuid) for m in AllManifest.objects.filter(item_type='projects', context_id=PROJECT_UUID)]
PROJECT_UUIDS += [PROJECT_UUID]

PROJECT_PART = 'DINAA' # For the project part


# The ARK pre-registered prefix for this project. Will be:
# 'ark:/28722/r2p24/' it is defined with EZID
ID_PREFIX = f'{PRE_REGISTER_SHOULDER}{PROJECT_PART}/'

def get_smithsonian_trinomial_identifier_predicate_queryset():
    """
    Get the Smithsonian Trinomial Identifier AllManifest predicate object
    
    Returns:
        AllManifest queryset
    """
    man_qs = AllManifest.objects.filter(
        label__in=['Smithsonian Trinomial Identifier', 'Trinomial'],
        item_type='predicates',
        project_id__in=PROJECT_UUIDS,
    )
    return man_qs

SMITHSONIAN_TRINOMIAL_ID_PRED_OBJS = [m for m in get_smithsonian_trinomial_identifier_predicate_queryset()]



def parse_smithsonian_trinomial(text):
    """
    Evaluates a string to determine if it is a valid Smithsonian Trinomial.
    If valid, returns a tuple of (state_code, county_code, site_number).
    If invalid, returns None.
    
    Args:
        text (str): The string to check (e.g., "41NV659", "41-NV-659", or "49-AAA-14").
        
    Returns:
        tuple: (state, county, site) or None
    """
    if not text:
        return None
    # Regex Pattern Breakdown:
    # ^                     : Start of string
    # (\d{1,2}|[a-zA-Z]{2}) : Part 1: State Code (1-2 digits OR 2 letters)
    # [- ]?                 : Optional separator (hyphen or space)
    # ([a-zA-Z]{2,3})       : Part 2: County Code (2 or 3 letters)
    # [- ]?                 : Optional separator
    # (\d+[a-zA-Z]?)        : Part 3: Site Number (Digits + optional single letter suffix)
    # $                     : End of string
    pattern = r"^(\d{1,2}|[a-zA-Z]{2})[- ]?([a-zA-Z]{2,3})[- ]?(\d+[a-zA-Z]?)$"
    match = re.match(pattern, text.strip())
    if match:
        state_code, county_code, site_number = match.groups()
        state_code = state_code.lstrip('0')
        site_number = site_number.lstrip('0')
        # Optional validation: check if numeric state code is within 1-50
        if state_code.isdigit():
            if not (1 <= int(state_code) <= 50):
                # While strictly 1-50, we return it to be flexible with 
                # potentially newer or territorial designations.
                pass
        # Returning normalized uppercase values for the codes
        return (state_code.upper(), county_code.upper(), site_number.upper())
    return None


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
    if not PROJECT_PART in check_id:
        return False
    if check_id.startswith('ark:/'):
        check_id = check_id.split('ark:/')[-1]
    # See regular expression: https://bioregistry.io/registry/ark
    # Compact URIs (CURIEs) constructed from Archival Resource Key should match this regular expression:
    # ^ark:/*[0-9A-Za-z]+(?:/[\w/.=*+@\$-]*)?(?:\?.*)?$
    return re.match(r"^[0-9A-Za-z]+(?:/[\w/.=*+@\$-]*)?(?:\?.*)?$", check_id) is not None


def create_preregistered_id_from_trinomial(trinomial, id_prefix=ID_PREFIX):
    """Uses a trinomial string to make a pre-registered ID of a given
    id_type_key.

    :param str trinomial: The trinomial identifier
    :param str id_prefix: The prefix (scheme, shoulder part, project part)

    returns str pre-registered ID
    """
    if not trinomial:
        return None
    parsed_tri = parse_smithsonian_trinomial(trinomial)
    if not parsed_tri:
        return None
    state_code = parsed_tri[0]
    county_code = parsed_tri[1]
    site_number = parsed_tri[2]
    prereg_id = f'{id_prefix}{state_code}{county_code}{site_number}'
    if not is_valid_preregistered_id(prereg_id):
        return None
    return prereg_id


def check_preregistered_id_for_man_obj(
    man_obj,
    preregistered_id,
    id_prefix=ID_PREFIX,
    non_unique_pid_handling=NON_UNIQUE_PID_HANDLING,
):
    """Gets or save a pre-registered ID for a Manifest object of a given id_type_key

    :param AllManifest man_obj: The item that will get a valid preregistered ID.
    :param str preregistered_id: The pre-registered ID

    returns str, id_obj (a validated and unique pre-registered ID, existing id object record)
    """
    id_obj = prereg_utils.get_existing_preregistered_id_obj_for_man_obj(
        man_obj,
        id_prefix=id_prefix,
    )
    if id_obj:
        # Return the existing pre-registered ID, and is_new=False
        return f'ark:/{id_obj.id}', id_obj  
    if not is_valid_preregistered_id(preregistered_id):
        # We failed to make a valid pre-registered ID
        print(f'{man_obj.label} [{str(man_obj.uuid)}] led to invalid ark: {preregistered_id}')
        return None, None
    clashing_obj = prereg_utils.get_manifest_obj_using_ark_id(man_obj, preregistered_id)
    if clashing_obj:
        if non_unique_pid_handling == 'db_store':
            man_obj.meta_json['clashing_pid'] = preregistered_id
            man_obj.meta_json['clashing_pid_item_id'] = str(clashing_obj.uuid)
            man_obj.save()
            print(
                f'Cannot use {preregistered_id} for item: {man_obj.label} [{str(man_obj.uuid)}], '
                f'ID already used by item: {clashing_obj.label} [{str(clashing_obj.uuid)}] '
            )
            print('Database saved flag of conflicting PID to item meta_json')
            # The item would have a pre-registered id that's already in use with another
            # item. So return None, None.
            return None, None
        elif non_unique_pid_handling == 'raise':
            raise ValueError(
                f'Cannot use {preregistered_id} for item: {man_obj.label} [{str(man_obj.uuid)}], '
                f'ID already used by item: {clashing_obj.label} [{str(clashing_obj.uuid)}] '
            )
        else:
            raise ValueError(
                f'Cannot use {preregistered_id} for item: {man_obj.label} [{str(man_obj.uuid)}], '
                f'ID already used by item: {clashing_obj.label} [{str(clashing_obj.uuid)}] '
            )
    # Return the valid preregistered_id, and id_obj=None
    return preregistered_id, None


def get_or_make_preregistered_id_for_man_obj(
    man_obj,
    id_prefix=ID_PREFIX,
    non_unique_pid_handling=NON_UNIQUE_PID_HANDLING,
):
    """Makes a valid pre-registered ID for a Manifest object of a given id_type_key

    :param AllManifest man_obj: The item that will get a valid preregistered ID.
    :param str id_type_key: The preregistered ID type within the DINAA project
    :param str id_prefix: The prefix (scheme, shoulder part, project part)

    returns str, id_obj (a validated and unique pre-registered ID, existing id object record)
    """
    id_obj = prereg_utils.get_existing_preregistered_id_obj_for_man_obj(
        man_obj,
        id_prefix=id_prefix,
    )
    if id_obj:
        # Return the existing pre-registered ID, and is_new=False
        return f'ark:/{id_obj.id}', id_obj
    # OK, we don't already have a pre-registered ID object for this
    # manifest item, so go make one.
    preregistered_id = None
    # Check first for smithsonian trinomials as noted in the assertions. The site's
    # manifest label is a less reliable source for a trinomial.
    id_assert_obj = AllAssertion.objects.filter(
        subject=man_obj,
        visible=True,
        predicate__in=SMITHSONIAN_TRINOMIAL_ID_PRED_OBJS,
    ).first()
    if id_assert_obj:
        preregistered_id = create_preregistered_id_from_trinomial(
            id_assert_obj.obj_string, 
            id_prefix=id_prefix,
        )
    if not preregistered_id:
        preregistered_id = create_preregistered_id_from_trinomial(
            trinomial=man_obj.label,
        id_prefix=id_prefix,
    )
    if not preregistered_id:
        return None, None
    if not is_valid_preregistered_id(preregistered_id):
        # We failed to make a valid pre-registered ID
        print(f'{man_obj.label} [{str(man_obj.uuid)}] led to invalid ark: {preregistered_id}')
        return None, None
    # On more check to make sure we have a valid trinomial afterall
    trinomial = preregistered_id.split('/')[-1]
    parse_tri = parse_smithsonian_trinomial(trinomial)
    if not parse_tri:
        # We failed to make a valid pre-registered ID
        print(f'{man_obj.label} [{str(man_obj.uuid)}] led to invalid Trinomial in the ark: {preregistered_id}')
        return None, None
    preregistered_id, id_obj = check_preregistered_id_for_man_obj(
        man_obj=man_obj,
        preregistered_id=preregistered_id,
        id_prefix=id_prefix,
        non_unique_pid_handling=non_unique_pid_handling,
    )
    return preregistered_id, id_obj


def create_pre_registered_ezid_and_oc_records(
    uuid=None,
    man_obj=None,
    do_staging=False,
    id_prefix=ID_PREFIX,
    update_if_exists=True,
    show_ezid_resp=False,
    ezid_client=None,
):
    """Makes a valid pre-registered ID and records them in EZID and Open Context

    :param str/uuid uuid: UUID identifier for the item that will get a valid preregistered ID.
    :param AllManifest man_obj: The item that will get a valid preregistered ID.
    :param bool do_staging: Use the staging site for EZID requests
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
        id_prefix=id_prefix,
    )
    if not preregistered_id:
        return None, None
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
    try:
        ezid_client.create_ark_identifier(
            oc_uri=oc_uri,
            metadata=metadata,
            id_str=preregistered_id,
            update_if_exists=update_if_exists,
            show_ezid_resp=show_ezid_resp,
        )
    except Exception as err:
        print(f'{man_obj.label} [{str(man_obj.uuid)}] has EZID problem!')
        traceback.print_tb(err.__traceback__)
        raise ValueError('EZID fail')
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


def get_dinaa_sites_queryset(
    filter_args=None,
    exclude_args=None,
    exclude_existing_ids_in_queryset=False,
    optional_sort='sort',
):
    """
    Get the DINAA site records as a AllManifest queryset
    
    Returns:
        AllManifest queryset
    """
    m_qs = AllManifest.objects.filter(
        item_class__slug='oc-gen-cat-site',
        item_type='subjects',
        project_id__in=PROJECT_UUIDS,
    )
    if filter_args:
        m_qs = m_qs.filter(**filter_args)
    if exclude_args:
        m_qs = m_qs.exclude(**exclude_args)
    if exclude_existing_ids_in_queryset:
        skip_id_qs = AllIdentifier.objects.filter(
            scheme='ark',
            id__contains=f'{PROJECT_PART}/',
        )
        skip_ids = [obj.item.uuid for obj in skip_id_qs]
        print(f'Skip {len(skip_ids)} that already have pre-registered ARKs')
        m_qs = m_qs.exclude(uuid__in=skip_ids)
    if optional_sort:
        m_qs = m_qs.order_by(optional_sort)
    return m_qs


def create_pre_registered_trinomial_ids_for_qs(
    filter_args=None,
    exclude_args=None,
    do_staging=False,
    id_prefix=ID_PREFIX,
    update_if_exists=True,
    show_ezid_resp=False,
    exclude_existing_ids_in_queryset=False,
    optional_sort='sort',
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
    m_qs = get_dinaa_sites_queryset(
        filter_args=filter_args,
        exclude_args=exclude_args,
        exclude_existing_ids_in_queryset=exclude_existing_ids_in_queryset,
        optional_sort=optional_sort,
    )
    print(f'Working on manifest object count: {m_qs.count()}')
    for man_obj in m_qs:
        preregistered_id, id_obj = create_pre_registered_ezid_and_oc_records(
            man_obj=man_obj,
            do_staging=do_staging,
            id_prefix=id_prefix,
            update_if_exists=update_if_exists,
            show_ezid_resp=show_ezid_resp,
        )
        preregistered_id_list.append(preregistered_id)
        id_obj_list.append(id_obj)
    return preregistered_id_list, id_obj_list


def make_ark_free_stable_id(id_str):
    """Makes a stable id without the ark part"""
    if id_str.startswith('ark:/'):
        return id_str.split('ark:/')[-1]
    return id_str


def remove_delete_bad_id_obj(bad_id, id_obj=None):
    """Deletes a bad ID from EZID, removes from database """
    if not id_obj:
        bad_stable_id = make_ark_free_stable_id(bad_id)
        bad_id_qs = AllIdentifier.objects.filter(
            id__in=[bad_id, bad_stable_id]
        )
        if bad_id_qs.count() != 1:
            print(f'Cannot resolve 1 record of {bad_id} to remove. Found {bad_id_qs.count()} records.')
            return None
        id_obj = bad_id_qs.first()
    ezid_client = EZID()
    ok = ezid_client.delete_ark_identifier(id_str=f'ark:/{id_obj.id}', show_ezid_resp=True)
    if not ok:
        raise ValueError(f'EZID fail could not delete id: {id_obj.id} [{id_obj.uuid}]')
    if ok:
        print(f'DELETE BAD ID FOR: {id_obj.item.label} [{id_obj.item.uuid}] id: {id_obj.id}')
        id_obj.delete()
    return ok


def check_man_obj_is_state(man_obj):
    """Checks if a manifest object is a US state"""
    if not man_obj:
        return False
    if str(man_obj.context.uuid) != '2a1b75e6-8c79-49b9-873a-a2e006669691':
        # this needs to have the United States as the parent context
        return False
    if man_obj.item_class.slug != 'oc-gen-cat-region':
        # The item must be a region
        return False
    if man_obj.item_type != 'subjects':
        return False
    return True



def create_pre_registered_county_state_ids_for_qs(
    do_staging=False,
    id_prefix=ID_PREFIX,
    update_if_exists=True,
    show_ezid_resp=False,
    non_unique_pid_handling=NON_UNIQUE_PID_HANDLING,
):
    """Create pre-registered IDs for parent county and state regions
    in a DINAA site AllManifest query-set

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
    id_qs = AllIdentifier.objects.filter(
        scheme='ark',
        id__contains=f'{PROJECT_PART}/',
        item__item_class__slug='oc-gen-cat-site',
        item__item_type='subjects',
        item__project_id__in=PROJECT_UUIDS,
    ).select_related(
        'item'
    ).select_related(
        'item__context'
    ).select_related(
        'item__context__context'
    ).distinct(
        'item__context'
    ).order_by(
        'item__context'
    )
    print(f'Working on DINAA pre-registered distinct context count: {id_qs.count()}')
    site_contexts = []
    ids_change_to_counties = []
    for id_obj in id_qs:
        c_id_qs = AllIdentifier.objects.filter(
            scheme='ark',
            id__contains=f'{PROJECT_PART}/',
            item__item_class__slug='oc-gen-cat-site',
            item__item_type='subjects',
            item__project_id__in=PROJECT_UUIDS,
            item__context=id_obj.item.context,
        ).order_by(
            '?'
        )
        context_dict = {
            'context_obj': id_obj.item.context,
            'county_codes': [],
            'state_codes': [],
        }
        for c_id_obj in c_id_qs[:300]:
            trinomial = c_id_obj.id.split(f'{PROJECT_PART}/')[-1]
            parse_tri = parse_smithsonian_trinomial(trinomial)
            if not parse_tri:
                print(f'BAD TRINOMIAL FOR: {c_id_obj.item.label} [{c_id_obj.item.uuid}] id: {c_id_obj.id}')
                _ = remove_delete_bad_id_obj(bad_id=c_id_obj.id, id_obj=c_id_obj)
                continue
            state_code = parse_tri[0]
            county_code = parse_tri[1]
            if not state_code in context_dict['state_codes']:
                context_dict['state_codes'].append(state_code)
            if not county_code in context_dict['county_codes']:
                context_dict['county_codes'].append(county_code)
        site_contexts.append(context_dict)
    print(f'Found {len(site_contexts)} unique contexts that contain DINAA sites')
    ezid_m = EZIDmanage()
    finished_state_codes = []
    finished_state_county_codes = []
    for context_dict in site_contexts:
        skip = False
        context_obj = context_dict['context_obj']
        if len(context_dict['county_codes']) == 0 or len(context_dict['county_codes']) > 1:
            skip = True
            print(f"WARNING {context_obj.label} [{context_obj.uuid}] has multiple county codes: {context_dict['county_codes']}")
        if len(context_dict['state_codes']) == 0 or len(context_dict['state_codes']) > 1:
            skip = True
            print(f"WARNING {context_obj.label} [{context_obj.uuid}] has multiple state codes: {context_dict['state_codes']}")
        if skip:
            print('-'*100)
            continue
        state_code = context_dict['state_codes'][0]
        county_code = context_dict['county_codes'][0]
        state_county_code_tup = (state_code, county_code)
        if state_county_code_tup in finished_state_county_codes:
            # We already did the state and county code.
            continue
        county_prereg_id = f'{id_prefix}{state_code}{county_code}'
        county_stable_id = make_ark_free_stable_id(county_prereg_id)
        print(f"{context_obj.label} [{context_obj.uuid}] will have a preregistered ID of: {county_prereg_id}")
        county_prereg_id, county_id_obj = check_preregistered_id_for_man_obj(
            man_obj=context_obj,
            preregistered_id=county_prereg_id,
            id_prefix=id_prefix,
            non_unique_pid_handling='raise',
        )
        if not county_id_obj:
            county_id_obj = ezid_m.save_man_obj_stable_id(man_obj=context_obj, stable_id=county_stable_id, scheme='ark',)
            print(f'{context_obj.label} [{str(context_obj.uuid)}] **SAVED** preregistered_id record: {county_prereg_id}')
        finished_state_county_codes.append(state_county_code_tup)
        state_obj = context_obj.context
        if not check_man_obj_is_state(state_obj):
            print(f'{state_obj.path} [{str(context_obj.uuid)}] is not a state? Skip')
            continue
        if state_code in finished_state_codes:
            continue
        state_prereg_id = f'{id_prefix}{state_code}'
        state_stable_id = make_ark_free_stable_id(state_prereg_id)
        print(f"{state_obj.label} [{state_obj.uuid}] will have a preregistered ID of: {state_prereg_id}")
        state_prereg_id, state_id_obj = check_preregistered_id_for_man_obj(
            man_obj=state_obj,
            preregistered_id=state_prereg_id,
            id_prefix=id_prefix,
            non_unique_pid_handling='raise',
        )
        if not state_id_obj:
            state_id_obj = ezid_m.save_man_obj_stable_id(man_obj=state_obj, stable_id=state_stable_id, scheme='ark',)
            print(f'{state_obj.label} [{str(state_obj.uuid)}] **SAVED** preregistered_id record: {state_prereg_id}')
        finished_state_codes.append(state_code)



def ezid_mint_region_arks(
    update_if_exists=True, 
    do_staging=False,
    show_ezid_resp=True,
):
    id_qs = AllIdentifier.objects.filter(
        scheme='ark',
        id__contains=f'{PROJECT_PART}',
        item__item_type__in=['subjects', 'projects'],
    ).exclude(
        item__item_class__slug='oc-gen-cat-site',
    ).select_related(
        'item'
    )
    print(f'Working on DINAA pre-registered non-site ARKs: {id_qs.count()}')
    ezid_client = EZID()
    for id_obj in id_qs:
        man_obj = id_obj.item
        preregistered_id = f'ark:/{id_obj.id}'
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
        try:
            ezid_client.create_ark_identifier(
                oc_uri=oc_uri,
                metadata=metadata,
                id_str=preregistered_id,
                update_if_exists=update_if_exists,
                show_ezid_resp=show_ezid_resp,
            )
        except Exception as err:
            print(f'{man_obj.label} [{str(man_obj.uuid)}] has EZID problem!')
            traceback.print_tb(err.__traceback__)
            raise ValueError('EZID fail')
