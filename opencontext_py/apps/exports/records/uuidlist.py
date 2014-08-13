from django.db.models import F
from django.db.models import Q
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.exports.records.models import ExpCell


class UUIDListSimple:
    '''
    The list of UUIDs used to create an export table.
    '''
    def __init__(self, project_uuids, class_uri):
        self.uuids = Manifest.objects.values_list(
            'uuid', flat=True)\
            .filter(project_uuid__in=project_uuids,
                    class_uri=class_uri).iterator()


class UUIDListExportTable:
    '''
    The list of UUIDs in an export table.
    '''
    def __init__(self, table_id):
        self.uuids = ExpCell.objects\
                            .values_list('uuid', flat=True)\
                            .order_by()\
                            .filter(table_id=table_id)\
                            .distinct()\
                            .iterator()
