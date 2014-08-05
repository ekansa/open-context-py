import hashlib
from django.conf import settings
from django.db import models
from opencontext_py.apps.ocitems.geospace.models import Geospace
from opencontext_py.apps.ocitems.events.models import Event
from opencontext_py.apps.ocitems.octypes.models import OCtype
from opencontext_py.apps.ocitems.strings.models import OCstring
from opencontext_py.apps.entities.uri.models import URImanagement
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.ocitems.predicates.models import Predicate, PredicateManage
from opencontext_py.apps.ldata.linkannotations.models import LinkAnnotation


# Assertions store descriptions and linking relations for Open Context items
# Assertion data mainly represents data contributed from data authors, not OC editors
class Assertion(models.Model):
    # standard predicate for spatial containment
    PREDICATES_CONTAINS = 'oc-gen:contains'
    # standard predicate for generic link
    PREDICATES_LINK = 'oc-3'
    hash_id = models.CharField(max_length=50, primary_key=True)
    uuid = models.CharField(max_length=50, db_index=True)
    subject_type = models.CharField(max_length=50, choices=settings.ITEM_TYPES)
    project_uuid = models.CharField(max_length=50)
    source_id = models.CharField(max_length=50)
    obs_node = models.CharField(max_length=50)
    obs_num = models.IntegerField()
    sort = models.DecimalField(max_digits=8, decimal_places=3)
    visibility = models.IntegerField()
    predicate_uuid = models.CharField(max_length=50, db_index=True)
    object_uuid = models.CharField(max_length=50, db_index=True)
    object_type = models.CharField(max_length=50)
    data_num = models.DecimalField(max_digits=19, decimal_places=10, blank=True)
    data_date = models.DateTimeField(blank=True)
    created = models.DateTimeField()
    updated = models.DateTimeField(auto_now=True)

    def make_hash_id(self):
        """
        creates a hash-id to insure unique combinations of uuids, obs_nums, predicates, and objects
        """
        hash_obj = hashlib.sha1()
        concat_string = str(self.uuid) + " " + str(self.obs_num) + " " + str(self.predicate_uuid) + " "
        concat_string = concat_string + str(self.object_uuid) + " " + str(self.data_num) + " " + str(self.data_date)
        hash_obj.update(concat_string.encode('utf-8'))
        return hash_obj.hexdigest()

    def save(self):
        """
        creates the hash-id on saving to insure a unique assertion
        """
        self.hash_id = self.make_hash_id()
        super(Assertion, self).save()

    class Meta:
        db_table = 'oc_assertions'
        ordering = ['uuid', 'sort']


class EventAssertions():
    """
    This class manages event data based on assertion data
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

    def process_unused_type_events(self, delete_old_source=False,
                                   feature_id=1,
                                   meta_type=Event.DEFAULT_METATYPE):
        """
        assigns events to subjects items based on associations
        with uuid identified types that have event data
        but are not yet used as source_ids for events
        """
        output = {}
        type_events = Event.objects.filter(item_type='types')
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


class PredicateTypeAssertions():
    """ Class for managing data_types for predicates, make sure consistency in data types
        used for predicates across manifest, predicate, and assertions tables
    """

    def __init__(self):
        self.alt_data_type = "xsd:string"

    def seperate_inconsistent_data_type(self, predicate_uuid):
        """ This looks for assertions that have different object types than the
            required main data_type of a given predicate. If such different assertions
            are found, the offending assertion is deleted and replaced by a new predicate
            and that new predicate is related back to the old predicate via 'skos:related'
        """
        plabel = False
        ptype = False
        pdata_type = False
        new_rel_predicates = []  # list of new predicates made from old
        try:
            pman = Manifest.objects.get(uuid=predicate_uuid)
            plabel = pman.label
            ptype = pman.class_uri
        except Manifest.DoesNotExist:
            pman = False
        try:  # look for the predicate item
            pred = Predicate.objects.get(uuid=predicate_uuid)
            pdata_type = pred.data_type
        except Predicate.DoesNotExist:
            pred = False
        if(plabel is not False
           and ptype is not False
           and pdata_type is not False):
            adistinct = Assertion.objects.filter(predicate_uuid=predicate_uuid)\
                                 .exclude(object_type=pdata_type)\
                                 .order_by('object_type')\
                                 .distinct('object_type')  # get distinct list of object_types
            for aitem in adistinct:  # list of assertions that are not using the good data type
                pm = PredicateManage()
                pm.source_id = pman.source_id
                pm.project_uuid = pman.project_uuid
                pm.sort = pred.sort
                cpred = pm.get_make_predicate(plabel, ptype, aitem.object_type)
                if(cpred is not False):
                    if(cpred.uuid not in new_rel_predicates):
                        new_rel_predicates.append(cpred.uuid)
            if(len(new_rel_predicates) > 0):
                #  add annotations storing the relationship between the new predicates and the old
                print('---- New predicates: ' + str(len(new_rel_predicates)))
                for new_pred_uuid in new_rel_predicates:
                    print('New predicate: ' + str(new_pred_uuid))
                    la = LinkAnnotation()
                    la.subject = new_pred_uuid
                    la.subject_type = 'predicates'
                    la.project_uuid = pman.project_uuid
                    la.source_id = pman.source_id
                    la.predicate_uri = 'skos:related'
                    la.object_uri = URImanagement.make_oc_uri(predicate_uuid, 'predicates')
                    la.save()
                alist = Assertion.objects.filter(predicate_uuid=predicate_uuid).exclude(object_type=pdata_type)
                for aitem in alist:  # list of assertions that are not using the good data type
                    pm = PredicateManage()
                    pm.source_id = pman.source_id
                    pm.project_uuid = pman.project_uuid
                    pm.sort = pred.sort
                    cpred = pm.get_make_predicate(plabel, ptype, aitem.object_type)
                    if(cpred is not False):
                        if(cpred.uuid not in new_rel_predicates):
                            new_rel_predicates.append(cpred.uuid)
                        Assertion.objects.filter(hash_id=aitem.hash_id).delete()
                        # delete the old instance of the assertion
                        aitem.predicate_uuid = cpred.uuid  # change the predicate to the new predicate
                        aitem.save()  # save the assertion with the new predicate
            else:
                print('--OK Predicate--: ' + str(predicate_uuid))

    def fix_inconsistent_data_types(self, data_type):
        """ fixes all predicates of a certain data_type and separates
           out assertions that have object_types that are different.
        """
        plist = Predicate.objects.filter(data_type=data_type)
        print('Predicate count: ' + str(len(plist)))
        for pitem in plist:
            print('Predicate: ' + pitem.uuid)
            self.seperate_inconsistent_data_type(pitem.uuid)

    def fix_all_inconsistent_data_types(self):
        """ fixes all predicates so that assertions have the correct object_type
           matching the data_type of the predicate """
        data_types = ['xsd:integer', 'xsd:double', 'xsd:date', 'xsd:boolean']
        for data_type in data_types:
            print('DATA-TYPE: ' + data_type)
            self.fix_inconsistent_data_types(data_type)


class ItemAssertion():
    """
    This class has useful functions for accessing assertion data
    """
    def __init__(self):
        self.assertion = False
        self.content = None

    def get_comment_from_des_predicate_uuid(self, uuid, des_predicate_uuid):
        """ Gets a comment (string) for an item based on an assertion
            using a particular predicate_uuid
        """
        try:
            self.assertion = Assertion.objects.filter(uuid=uuid, predicate_uuid=predicate_uuid)[0]
        except Assertion.DoesNotExist:
            self.assertion = False
        if(self.assertion is not False):
            if(self.assertion.object_type == 'xsd.string'):
                try:
                    string_item = OCstring.objects.get(uuid=self.assertion.object_uuid)
                    self.content = string_item.content
                except OCstring.DoesNotExist:
                    self.content = False
            elif(self.assertion.object_type == 'types'):
                try:
                    t_item = OCstring.objects.get(uuid=self.assertion.object_uuid)
                    self.content = string_item.content
                except OCstring.DoesNotExist:
                    self.content = False


class ManageAssertions():
    """
    This class has useful functions for creating and updating assertion data
    """

    def change_predicate_object_uuid(self, predicate_uuid, old_object_uuid,
                                     new_object_uuid, new_object_type):
        """ Changes an object of a given predicate. Useful if an object_uuid has changed """
        old_assertions = Assertion.objects.filter(predicate_uuid=predicate_uuid,
                                                  object_uuid=old_object_uuid)
        for act_ass in old_assertions:
            act_ass.object_uuid = new_object_uuid
            act_ass.object_type = new_object_type
            act_ass.save()
        return len(old_assertions)
