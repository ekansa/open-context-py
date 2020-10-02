
import hashlib
import uuid as GenUUID

from opencontext_py.apps.all_items import configs
from opencontext_py.apps.all_items.models import (
    AllManifest,
    AllAssertion,
    AllHistory,
    AllResource,
    AllIdentifier,
    AllSpaceTime,
)
from opencontext_py.apps.all_items import utilities


SALT = (
    'a53b5bc896b2ace7a812d33ec895279d2c4dcd3f932ce2d9c7811690aabd7e92bbf9'
    '3d5440f7b51a6b1171bcc57c94a0e6860b7b26b64fa7b5e39748de22e291652bdac2'
    '3382fe9d8b4ec405d4e79bc886ea36b7cf366098ca4deaaf86dd57b0181cbd8432ee'
    '5a7c1c259f0da8af327f0b4363fb7fc337d16d41ad666a02367c80f7ed9b1ac3035e'
    '32f666e2026d198068a6ba26c9f7ceca18e8c8d19a8fe2fd2b53a715e8d682a803f6'
    '2eb51ca594d00700b37f3fdc2707d197c0efae0574a86a09500b31ce75b8ab8c13b0'
    'aff9cd2b9d68b6acdadb5317efa542739827a0492418ceca0e9b995eafb92181a4cd'
)


def is_valid_uuid(val):
    try:
        return GenUUID.UUID(str(val))
    except ValueError:
        return None


def update_old_id(old_id):
    """Updates an old ID deterministically so as to be repeatable"""
    if is_valid_uuid(old_id):
        # The old ID is fine and needs no updating.
        return old_id, old_id.lower()
    if old_id == '0':
        # This maps project '0' to the new general open context project
        return old_id, configs.OPEN_CONTEXT_PROJ_UUID  

    hash_obj = hashlib.sha1()
    # The salt added to our hash adds some randomness so that we're less
    # likely to make an ID that collides with something else out there in the wild.
    hash_this = f'{SALT}-{old_id}'
    hash_obj.update(hash_this.encode('utf-8'))
    hash_val = hash_obj.hexdigest()
    new_uuid = str(
        GenUUID.UUID(hex=hash_val[:32])
    )
    return old_id, new_uuid
