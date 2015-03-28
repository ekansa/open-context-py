import uuid as GenUUID
from django.conf import settings
from django.db import models
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.apps.ocitems.events.models import Event
from opencontext_py.apps.entities.entity.models import Entity
from opencontext_py.apps.imports.fields.models import ImportField
from opencontext_py.apps.imports.fieldannotations.models import ImportFieldAnnotation
from opencontext_py.apps.imports.records.models import ImportCell
from opencontext_py.apps.imports.records.process import ProcessCells
from opencontext_py.apps.imports.fieldannotations.general import ProcessGeneral
from opencontext_py.apps.imports.sources.unimport import UnImport


# Processes to generate subjects items for an import
class ProcessTypes():

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
                                              field_type='start-date')[:1]
        if len(start_field_list) > 0:
            self.start_field = start_field_list[0]
        stop_field_list = ImportField.objects\
                                     .filter(source_id=self.source_id,
                                             field_type='stop-date')[:1]
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
        