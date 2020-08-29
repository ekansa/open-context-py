
import uuid as GenUUID

from django.db.models import Q

from opencontext_py.apps.all_items import configs
from opencontext_py.apps.all_items.models import (
    AllManifest,
    AllString,
    AllAssertion,
    AllHistory,
    AllResource,
    AllIdentifier,
)
from opencontext_py.apps.all_items import utilities

from opencontext_py.apps.ldata.linkannotations.models import LinkAnnotation

from opencontext_py.apps.ocitems.projects.models import Project


def migrate_legacy_projects():
    # NOTE TODO This.
