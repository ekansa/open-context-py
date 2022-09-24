import copy
from re import sub

import pandas as pd

from django.db.models import Q
from django.utils import timezone

from opencontext_py.apps.all_items import configs
from opencontext_py.apps.all_items.models import (
    AllManifest,
    AllAssertion,
)


def get_manifest_object_by_uuid_or_uri(uuid, uri):
    """Returns an AllManifest object via lookup of uuid or uri"""
    if uuid:
        return AllManifest.objects.filter(uuid=uuid).first()
    uri = AllManifest().clean_uri(uri)
    return AllManifest.objects.filter(uri=uri).first()