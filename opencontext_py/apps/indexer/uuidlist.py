from django.db.models import F
from django.db.models import Q
from opencontext_py.apps.ocitems.manifest.models import Manifest


class UUIDList:
    '''
    The list of UUIDs that the crawler will crawl.
    '''
    def __init__(self):
        self.uuids = Manifest.objects.values_list(
            'uuid', flat=True
            ).filter(Q(indexed__isnull=True) | Q(indexed__lt=F('revised'))
                     ).order_by('sort').iterator()
