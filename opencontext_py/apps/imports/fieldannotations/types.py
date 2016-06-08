import uuid as GenUUID
from django.conf import settings
from django.db import models
from django.utils.http import urlunquote
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.apps.ocitems.events.models import Event
from opencontext_py.apps.entities.entity.models import Entity
from opencontext_py.apps.imports.fields.models import ImportField
from opencontext_py.apps.imports.fieldannotations.models import ImportFieldAnnotation
from opencontext_py.apps.imports.records.models import ImportCell
from opencontext_py.apps.imports.records.process import ProcessCells
from opencontext_py.apps.imports.fieldannotations.general import ProcessGeneral
from opencontext_py.apps.imports.sources.unimport import UnImport
from opencontext_py.apps.ocitems.octypes.manage import TypeManagement
from opencontext_py.apps.ldata.linkentities.models import LinkEntity
from opencontext_py.apps.ldata.linkentities.web import WebLinkEntity
from opencontext_py.apps.ldata.linkannotations.models import LinkAnnotation
from opencontext_py.apps.ldata.linkannotations.recursion import LinkRecursion
from opencontext_py.apps.entities.uri.models import URImanagement


# Processes to generate subjects items for an import
class ProcessTypes():
    """
    Methods for importing type data as data
    so linked data can be added
    to describe it

from opencontext_py.apps.imports.fieldannotations.types import ProcessTypes
source_id = 'ref:1903543025071'
pred_uuid = 'c01b2f13-8c6f-4fca-8a47-50e573dd01d0'  # Materials 1
type_f = 17
rel_pred = 'skos:exactMatch'
le_f = 19
pt = ProcessTypes(source_id)
pt.make_type_ld_annotations(pred_uuid, type_f, rel_pred, le_f)

from opencontext_py.apps.imports.fieldannotations.types import ProcessTypes
source_id = 'ref:1903543025071'
pred_uuid = '7cdf8d0a-521c-4fab-ae8c-8fd3adafa776'  # Materials 2
type_f = 21
rel_pred = 'skos:exactMatch'
le_f = 23
pt = ProcessTypes(source_id)
pt.make_type_ld_annotations(pred_uuid, type_f, rel_pred, le_f)


from opencontext_py.apps.imports.fieldannotations.types import ProcessTypes
source_id = 'ref:1699742791864'
pred_uuid = '636239c2-b90c-4b62-9720-2221e4a56742'
pt = ProcessTypes(source_id)
type_f = 1
start_f = 2
stop_f = 3
pt.make_type_event_from_type_label_records(pred_uuid, type_f, start_f, stop_f)

from opencontext_py.apps.ocitems.assertions.event import EventAssertions
eva = EventAssertions()
project_uuid = 'd1c85af4-c870-488a-865b-b3cf784cfc60'
eva.process_unused_type_events(project_uuid)


from opencontext_py.apps.ldata.eol.api import eolAPI
from opencontext_py.apps.ldata.linkentities.models import LinkEntity
eol_api = eolAPI()
bad_ents = LinkEntity.objects.filter(label='Apororhynchida', vocab_uri='http://eol.org/')
for bad_ent in bad_ents:
    labels = eol_api.get_labels_for_uri(bad_ent.uri)
    if isinstance(labels, dict):
        bad_ent.label = labels['label']
        bad_ent.alt_label = labels['alt_label']
        bad_ent.save()


    """

    # default predicate for subject item is subordinate to object item
    PRED_SBJ_IS_SUB_OF_OBJ = 'skos:broader'

    def __init__(self, source_id):
        self.source_id = source_id
        pg = ProcessGeneral(source_id)
        pg.get_source()
        self.project_uuid = pg.project_uuid
        self.types_fields = False
        self.start_field = False
        self.stop_field = False
        self.start_row = 1
        self.batch_size = 250
        self.end_row = self.batch_size
        self.example_size = 5

    def clear_source(self):
        """ Clears a prior import if the start_row is 1.
            This makes sure new entities and assertions are made for
            this source_id, and we don't duplicate things
        """
        if self.start_row <= 1:
            # get rid of "subjects" related assertions made from this source
            unimport = UnImport(self.source_id,
                                self.project_uuid)
            # to do, figure out the unimport

    def make_type_ld_annotations(self,
                                 sub_type_pred_uuid,
                                 sub_type_f_num,
                                 rel_pred,
                                 obj_le_f_num):
        """ Makes linked data annotations
            for a type in an import
        """
        rels = []
        sub_type_list = ImportCell.objects\
                                  .filter(source_id=self.source_id,
                                          field_num=sub_type_f_num)
        if len(sub_type_list) > 0:
            distinct_records = {}
            for cell in sub_type_list:
                if cell.rec_hash not in distinct_records:
                    distinct_records[cell.rec_hash] = {}
                    distinct_records[cell.rec_hash]['rows'] = []
                    distinct_records[cell.rec_hash]['imp_cell_obj'] = cell
                distinct_records[cell.rec_hash]['rows'].append(cell.row_num)
            for rec_hash_key, distinct_type in distinct_records.items():
                # iterate through the distinct types and get associated linked data
                type_label = distinct_type['imp_cell_obj'].record
                rows = distinct_type['rows']
                if len(type_label) > 0:
                    # the type isn't blank, so we can use it
                    pc = ProcessCells(self.source_id, 0)
                    ld_entities = pc.get_field_records(obj_le_f_num, rows)
                    for ld_hash_key, distinct_ld in ld_entities.items():
                        obj_uri = distinct_ld['imp_cell_obj'].record
                        if len(obj_uri) > 8:
                            if obj_uri[:7] == 'http://'\
                               or obj_uri[:8] == 'https://':
                                # we have a valid linked data entity
                                #
                                # now get the UUID for the type
                                tm = TypeManagement()
                                tm.project_uuid = self.project_uuid
                                tm.source_id = self.source_id
                                sub_type = tm.get_make_type_within_pred_uuid(sub_type_pred_uuid,
                                                                             type_label)
                                rel = {'subject_label': type_label,
                                       'subject': sub_type.uuid,
                                       'object_uri': obj_uri}
                                rels.append(rel)
        if len(rels) > 0:
            for rel in rels:
                new_la = LinkAnnotation()
                new_la.subject = rel['subject']
                new_la.subject_type = 'types'
                new_la.project_uuid = self.project_uuid
                new_la.source_id = self.source_id
                new_la.predicate_uri = rel_pred
                new_la.object_uri = rel['object_uri']
                new_la.creator_uuid = ''
                new_la.save()
                web_le = WebLinkEntity()
                web_le.check_add_link_entity(rel['object_uri'])

    def make_type_relations(self, sub_type_pred_uuid,
                                  sub_type_f_num,
                                  rel_pred,
                                  obj_type_pred_uuid,
                                  obj_type_f_num):
        """ Makes semantic relationships between
            different types in an import
        """
        rels = {}
        sub_type_list = ImportCell.objects\
                                  .filter(source_id=self.source_id,
                                          field_num=sub_type_f_num)
        for sub_type_obj in sub_type_list:
            sub_type_text = sub_type_obj.record
            row = sub_type_obj.row_num
            if len(sub_type_text) > 0:
                tm = TypeManagement()
                tm.project_uuid = self.project_uuid
                tm.source_id = self.source_id
                sub_type = tm.get_make_type_within_pred_uuid(sub_type_pred_uuid,
                                                             sub_type_text)
                obj_type_list = ImportCell.objects\
                                          .filter(source_id=self.source_id,
                                                  field_num=obj_type_f_num,
                                                  row_num=row)[:1]
                if len(obj_type_list) > 0:
                    obj_type_text = obj_type_list[0].record
                    if len(obj_type_text) > 0 \
                       and sub_type_text != obj_type_text:
                        tmo = TypeManagement()
                        tmo.project_uuid = self.project_uuid
                        tmo.source_id = self.source_id
                        obj_type = tmo.get_make_type_within_pred_uuid(obj_type_pred_uuid,
                                                                      obj_type_text)
                        # make a uri for this, since we're making a link assertion
                        obj_uri = URImanagement.make_oc_uri(obj_type.uuid, 'types')
                        # the following bit is so we don't make the
                        # same link assertions over and over.
                        rel_id = str(sub_type.uuid) + ' ' + str(obj_type.uuid)
                        if rel_id not in rels:
                            rels[rel_id] = {'subject': sub_type.uuid,
                                            'object_uri': obj_uri}
        # now make the link data annotation relating these types.
        for rel_id, rel in rels.items():
            new_la = LinkAnnotation()
            new_la.subject = rel['subject']
            new_la.subject_type = 'types'
            new_la.project_uuid = self.project_uuid
            new_la.source_id = self.source_id
            new_la.predicate_uri = rel_pred
            new_la.object_uri = rel['object_uri']
            new_la.creator_uuid = ''
            new_la.save()

    def make_type_event_from_type_label_records(self,
                                                type_pred_uuid,
                                                type_field_num,
                                                start_field_num,
                                                stop_field_num):
        """ make event records from types identified by
            the predicate uuid for a type and its field number
        """
        type_list = ImportCell.objects\
                              .filter(source_id=self.source_id,
                                      field_num=type_field_num)
        if len(type_list) > 0:
            for type_row in type_list:
                row = type_row.row_num
                type_label = type_row.record
                start_date = self.get_date_record(start_field_num,
                                                  row)
                stop_date = self.get_date_record(stop_field_num,
                                                 row)
                if start_date is not False\
                   and stop_date is not False:
                    tmo = TypeManagement()
                    tmo.project_uuid = self.project_uuid
                    tmo.source_id = self.source_id
                    type_obj = tmo.get_make_type_within_pred_uuid(type_pred_uuid,
                                                                  type_label)
                    tet = TimeEventType()
                    tet.uuid = type_obj.uuid
                    tet.start_date = start_date
                    tet.stop_date = stop_date
                    tet.source_id = self.source_id
                    tet.project_uuid = self.project_uuid
                    tet.create_type_event()

    def make_type_event_from_uuid_records(self,
                                          type_field_num,
                                          start_field_num,
                                          stop_field_num):
        """ make event records from types identified by
            uuids
        """
        type_list = ImportCell.objects\
                              .filter(source_id=self.source_id,
                                      field_num=type_field_num)
        if len(type_list) > 0:
            for type_row in type_list:
                row = type_row.row_num
                type_uuid = type_row.record
                start_date = self.get_date_record(start_field_num,
                                                  row)
                stop_date = self.get_date_record(stop_field_num,
                                                 row)
                if start_date is not False\
                   and stop_date is not False:
                    tet = TimeEventType()
                    tet.uuid = type_uuid
                    tet.start_date = start_date
                    tet.stop_date = stop_date
                    tet.source_id = self.source_id
                    tet.project_uuid = self.project_uuid
                    tet.create_type_event()

    def get_date_record(self, date_field_num, row):
        """ get a date record, returns false if not found
            or not a number
        """
        output = False
        date_list = ImportCell.objects\
                              .filter(source_id=self.source_id,
                                      field_num=date_field_num,
                                      row_num=row)[:1]
        if len(date_list) > 0:
            try:
                output = float(date_list[0].record)
            except ValueError:
                output = False
        return output

    def get_date_fields(self):
        """ Gets the start and stop date fields
        """
        start_field_list = ImportField.objects\
                                      .filter(source_id=self.source_id,
                                              field_type='early')[:1]
        if len(start_field_list) > 0:
            self.start_field = start_field_list[0]
        stop_field_list = ImportField.objects\
                                     .filter(source_id=self.source_id,
                                             field_type='late')[:1]
        if len(stop_field_list) > 0:
            self.stop_field = stop_field_list[0]


class TimeEventType():
    """ Methods for assigning time spans to a
        type
    """

    def __init__(self):
        self.uuid = False
        self.start_date = False
        self.stop_date = False
        self.source_id = False
        self.project_uuid = False
        self.event_id = 0
        self.meta_type = 'oc-gen:formation-use-life'
        self.when_type = 'Interval'

    def create_type_event(self):
        """ makes an event object for a
            type entity
        """
        # validate start and end dates
        if self.start_date <= self.stop_date:
            start = self.start_date
            stop = self.stop_date
        else:
            start = self.stop_date
            stop = self.start_date
        event = Event()
        event.uuid = self.uuid
        event.item_type = 'types'
        event.project_uuid = self.project_uuid
        event.source_id = self.source_id
        event.event_id = self.event_id
        event.meta_type = self.meta_type
        event.when_type = self.when_type
        event.feature_id = 1
        event.earliest = start
        event.start = start
        event.stop = stop
        event.latest = stop
        event.save()
