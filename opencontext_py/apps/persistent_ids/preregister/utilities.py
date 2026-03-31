import re

from opencontext_py.apps.all_items.models import (
    AllManifest,
    AllIdentifier,
)



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


def get_existing_preregistered_id_obj_for_man_obj(man_obj, id_prefix):
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