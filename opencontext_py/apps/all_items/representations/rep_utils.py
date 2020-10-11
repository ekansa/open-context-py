
import copy
import hashlib
import uuid as GenUUID

from django.db.models import OuterRef, Subquery

from opencontext_py.libs.general import LastUpdatedOrderedDict

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



def get_item_key_or_uri_value(manifest_obj):
    """Gets an item_key if set, falling back to uri value"""
    if manifest_obj.item_key:
        return manifest_obj.item_key
    return f"https://{manifest_obj.uri}"
