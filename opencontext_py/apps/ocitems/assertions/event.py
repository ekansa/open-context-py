import hashlib
from django.conf import settings
from django.db import models
from opencontext_py.apps.ocitems.assertions.models import Assertion
from opencontext_py.apps.ocitems.events.models import Event
from opencontext_py.apps.ocitems.octypes.models import OCtype


class EventAssertions():
    """
    This class manages event (chronology) data based on assertion data

from opencontext_py.apps.ocitems.assertions.event import EventAssertions
eva = EventAssertions()
project_uuid = 'd1c85af4-c870-488a-865b-b3cf784cfc60'
eva.process_unused_type_events(project_uuid)


    """

    def assign_events_from_type(self, type_uuid,
                                delete_old_source=False,
                                feature_id=1,
                                meta_type=Event.DEFAULT_METATYPE):
        """
        assigns an event to subjects items based on association
        with a uuid identified type that has event data
        """
        type_events = Event.objects.filter(uuid=type_uuid)
        type_event = type_events[0]
        rel_subjects = Assertion.objects.filter(subject_type='subjects',
                                                object_uuid=type_uuid)
        for sub in rel_subjects:
            if(delete_old_source is not False):
                Event.objects.filter(uuid=sub.uuid, source_id=delete_old_source).delete()
            record = {'uuid': sub.uuid,
                      'item_type': sub.subject_type,
                      'project_uuid': sub.project_uuid,
                      'source_id': type_uuid,
                      'meta_type': meta_type,
                      'when_type': Event.DEFAULT_WHENTYPE,
                      'feature_id': feature_id,
                      'earliest': type_event.earliest,
                      'start': type_event.start,
                      'stop': type_event.stop,
                      'latest': type_event.latest,
                      'note': type_event.note}
            newr = Event(**record)
            newr.save()
        return len(rel_subjects)

    def process_unused_type_events(self,
                                   project_uuid=False,
                                   delete_old_source=False,
                                   feature_id=1,
                                   meta_type=Event.DEFAULT_METATYPE):
        """
        assigns events to subjects items based on associations
        with uuid identified types that have event data
        but are not yet used as source_ids for events
        """
        output = {}
        if project_uuid is False:
            type_events = Event.objects.filter(item_type='types')
        else:
            type_events = Event.objects\
                               .filter(item_type='types',
                                       project_uuid=project_uuid)
        for tevent in type_events:
            type_uuid = tevent.uuid
            tused_count = Event.objects.filter(source_id=type_uuid).count()
            if(tused_count < 1):
                output[type_uuid] = self.assign_events_from_type(type_uuid,
                                                                 delete_old_source,
                                                                 feature_id,
                                                                 meta_type
                                                                 )
        return output
