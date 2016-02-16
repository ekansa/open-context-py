import hashlib
import reversion  # version control object
from django.db import models
from opencontext_py.apps.ocitems.geospace.models import Geospace


# Events enables modeling of aspects of time and space for an item
# a zero in the feature_id field means that the time data is not tied to
# a specific feature associated with an item.
@reversion.register  # records in this model under version control
class Event(models.Model):
    DEFAULT_METATYPE = 'oc-gen:formation-use-life'
    DEFAULT_WHENTYPE = 'Interval'
    INSTANT_WHENTYPE = 'Instant'
    hash_id = models.CharField(max_length=50, primary_key=True)
    uuid = models.CharField(max_length=50, db_index=True)
    item_type = models.CharField(max_length=50, db_index=True)
    project_uuid = models.CharField(max_length=50, db_index=True)
    source_id = models.CharField(max_length=50, db_index=True)
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

    def make_event_id(self):
        """
        assigns an id to an event
        """
        ea = EventAssignment()
        return ea.make_event_id(self.uuid)

    def validate_times(self):
        """
        makes sure time data is properly validated
        """
        time_list = [self.earliest, self.start, self.stop, self.latest]
        time_list.sort()
        self.earliest = time_list[0]
        self.start = time_list[1]
        self.stop = time_list[2]
        self.latest = time_list[3]

    def save(self, *args, **kwargs):
        """
        creates the hash-id on saving to insure a unique event
        """
        self.validate_times()
        self.event_id = self.make_event_id()
        self.hash_id = self.make_hash_id()
        super(Event, self).save(*args, **kwargs)

    class Meta:
        db_table = 'oc_events'
        ordering = ['earliest', 'start', 'stop', 'latest']


class EventAssignment():
    # iteracts with the Event, Geospace, and Chrono classes

    def __init__(self):
        do_something = True

    def make_event_id(self, uuid):
        """
        assigns an event_id based on uuid
        """
        uuid_count = Event.objects.filter(uuid=uuid).count()
        return uuid_count + 1
