import hashlib
from django.db import models
from opencontext_py.apps.ocitems.geospace.models import Geospace


# Events enables modeling of aspects of time and space for an item
# a zero in the feature_id field means that the time data is not tied to
# a specific feature associated with an item.
class Event(models.Model):
    hash_id = models.CharField(max_length=50, primary_key=True)
    uuid = models.CharField(max_length=50, db_index=True)
    item_type = models.CharField(max_length=50, db_index=True)
    project_uuid = models.CharField(max_length=50, db_index=True)
    event_id = models.IntegerField()
    meta_type = models.CharField(max_length=50)
    when_type = models.CharField(max_length=50)
    feature_id = models.IntegerField()
    earliest = models.DecimalField(max_digits=19, decimal_places=5)
    start = models.DecimalField(max_digits=19, decimal_places=5)
    stop = models.DecimalField(max_digits=19, decimal_places=5)
    latest = models.DecimalField(max_digits=19, decimal_places=5)
    updated = models.DateTimeField(auto_now=True)
    note = models.TextField()

    def make_hash_id(self):
        """
        creates a hash-id to insure unique combinations of uuids, locations, and times
        """
        hash_obj = hashlib.sha1()
        concat_string = self.uuid + " " + str(self.meta_type) + " " + \
            str(self.feature_id) + " " + str(self.earliest) + " " + str(self.start) + " " + \
            str(self.stop) + " " + str(self.latest)
        hash_obj.update(concat_string.encode('utf-8'))
        return hash_obj.hexdigest()

    def save(self):
        """
        creates the hash-id on saving to insure a unique event
        """
        self.hash_id = self.make_hash_id()
        super(Event, self).save()

    class Meta:
        db_table = 'oc_events'
        ordering = ['event_id']


class EventAssignment():
    # iteracts with the Event, Geospace, and Chrono classes

    def __init__(self):
        do_something = True

    """
    def assign_initial_events(self):
        chrono_items = Chrono.objects.all()
        for citem in chrono_items:
            meta_type = citem.meta_type
            act_uuid = citem.uuid
            geo_items = Geospace.objects.filter(uuid=act_uuid)
            if(len(geo_items) > 0):
                event_id = 1
                for geoitem in geo_items:
                    newr = Event(uuid=act_uuid,
                                 item_type='subjects',
                                 project_uuid=citem.project_uuid,
                                 event_id=event_id,
                                 meta_type=meta_type,
                                 when_type='Interval',
                                 feature_id=geoitem.fid,
                                 earliest=citem.start_lc,
                                 start=citem.start_c,
                                 stop=citem.end_c,
                                 latest=citem.end_lc,
                                 note='')
                    newr.save()
                    event_id += 1
            else:
                newr = Event(uuid=act_uuid,
                             item_type='subjects',
                             project_uuid=citem.project_uuid,
                             event_id=1,
                             meta_type=meta_type,
                             when_type='Interval',
                             feature_id=0,
                             earliest=citem.start_lc,
                             start=citem.start_c,
                             stop=citem.end_c,
                             latest=citem.end_lc,
                             note='')
                newr.save()
        return Event.objects.all().count()
    """