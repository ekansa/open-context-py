from django.db.models import F
from django.db.models import Q
from opencontext_py.apps.ocitems.manifest.models import Manifest


class UUIDListSimple:
    '''
    The list of UUIDs that the crawler will crawl.
    '''
    def __init__(self, project_uuids, class_uri):
        self.uuids = Manifest.objects.values_list(
            'uuid', flat=True)\
            .filter(project_uuid__in=project_uuids,
                    class_uri=class_uri).iterator()
