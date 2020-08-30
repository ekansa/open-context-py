
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
    AllSpaceTime,
)
from opencontext_py.apps.all_items import utilities

from opencontext_py.apps.ldata.linkannotations.models import LinkAnnotation

from opencontext_py.apps.ocitems.projects.models import Project


def migrate_legacy_projects():
    """Migrates project entities to the new schema"""
    for old_proj in Project.objects.all():
        if old_proj.uuid != old_proj.project_uuid:
            parent_proj = Project.objects.get(uuid=old_proj.project_uuid)