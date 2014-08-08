import datetime
import json
from django.db import models
from django.db.models import Avg, Max, Min
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.apps.exports.fields.models import ExpField
from opencontext_py.apps.exports.records.models import ExpRecord
from opencontext_py.apps.entities.uri.models import URImanagement
from opencontext_py.apps.entities.entity.models import Entity
from opencontext_py.apps.ocitems.geospace.models import Geospace
from opencontext_py.apps.ocitems.events.models import Event
from opencontext_py.apps.ocitems.assertions.containment import Containment
from opencontext_py.apps.ocitems.assertions.model import Assertion
from opencontext_py.apps.ocitems.manifest.model import Manifest


# Creates an export table
class Create():

    def __init__(self):
        self.table_id = False
        self.label = False
        self.dates_bce_ce = True
        self.fields = False
        self.entities = {}
        self.records = LastUpdatedOrderedDict()

    def prep_default_fields(self):
        """ Prepares initial set of default fields for export tables """
        self.fields = []
        self.fields.append({'label': 'URI',
                            'rel_ids': ['@id'],
                            'field_num': 1})
        self.fields.append({'label': 'Label',
                            'rel_ids': ['label'],
                            'field_num': 2})
        self.fields.append({'label': 'Project',
                            'rel_ids': ['proj-label'],
                            'field_num': 3})
        self.fields.append({'label': 'Project URI',
                            'rel_ids': ['proj-uri'],
                            'field_num': 4})
        self.fields.append({'label': 'Item Category',
                            'rel_ids': ['item-category'],
                            'field_num': 5})
        self.fields.append({'label': 'Latitude (WGS-84)',
                            'rel_ids': ['latitude'],
                            'field_num': 6})
        self.fields.append({'label': 'Longitude (WGS-84)',
                            'rel_ids': ['longitude'],
                            'field_num': 7})
        if self.dates_bce_ce:
            self.fields.append({'label': 'Early Date (BCE/CE)',
                                'rel_ids': ['early-bce-ce'],
                                'field_num': 8})
            self.fields.append({'label': 'Late Date (BCE/CE)',
                                'rel_ids': ['late-bce-ce'],
                                'field_num': 9})
        else:
            self.fields.append({'label': 'Early Date (BP)',
                                'rel_ids': ['early-bp'],
                                'field_num': 8})
            self.fields.append({'label': 'Late Date (BP)',
                                'rel_ids': ['late-bp'],
                                'field_num': 9})
        self.fields.append({'label': 'Context URI',
                            'rel_ids': ['context-uri'],
                            'field_num': 10})
        for field in self.fields.items():
            exfield = ExpField()
            exfield.table_id = self.table_id
            exfield.field_num = field['field_num']
            exfield.label = field['label']
            exfield.rel_ids = json.dumps(field['rel_ids'], ensure_ascii=False)
            exfield.save()

    def get_set_uuids_simple(self, project_uuids, class_uri):
        """ Gets a list of uuids and basic metadata about items for the
            export table. Does so in the simpliest way, filtering only
            by a list of project_uuids and class_uri """
        man_objs = Manifest.objects.filter(project_uuid__in=project_uuids,
                                           class_uri=class_uri)
        row_num = 0
        for man in man_objs:
            row_num += 1
            self.save_basic_default_field_cells(row_num, man)
            act_contain = Containment()
            parents = act_contain.get_parents_by_child_uuid(man.uuid)
            subject_list = act_contain.contexts_list
            subject_list.insert(0, man.uuid)
            geo_meta = act_contain.get_geochron_from_subject_list(subject_list, 'geo')
            event_meta = act_contain.get_geochron_from_subject_list(subject_list, 'event')
            self.save_default_geo(row_num, man, geo_meta)

    def save_default_geo(self, row_num, man, geo_meta):
        """ Saves geo lat / lon data for an item """
        latitude = ''
        longitude = ''
        if geo_meta is not False:
            for geo in geo_meta:
                if geo.meta_type == 'oc-gen:formation-use-life':
                    latitude = geo.latitude
                    longitude = geo.longitude
                    break
        # save Latitude
        rec = ExpRecord()
        rec.table_id = self.table_id
        rec.uuid = man.uuid
        rec.project_uuid = man.project_uuid
        rec.row_num = row_num
        rec.field_num = 6
        rec.record = latitude
        rec.save()
        rec = None
        # save Longitude
        rec = ExpRecord()
        rec.table_id = self.table_id
        rec.uuid = man.uuid
        rec.project_uuid = man.project_uuid
        rec.row_num = row_num
        rec.field_num = 7
        rec.record = longitude
        rec.save()
        rec = None

    def save_basic_default_field_cells(self, row_num, man):
        """ Saves the default fields that do not involve containment lookups """
        # save URI
        rec = ExpRecord()
        rec.table_id = self.table_id
        rec.uuid = man.uuid
        rec.project_uuid = man.project_uuid
        rec.row_num = row_num
        rec.field_num = 1
        rec.record = URImanagement.make_oc_uri(man.uuid, man.item_type)
        rec.save()
        rec = None
        # save label
        rec = ExpRecord()
        rec.table_id = self.table_id
        rec.uuid = man.uuid
        rec.project_uuid = man.project_uuid
        rec.row_num = row_num
        rec.field_num = 2
        rec.record = man.label
        rec.save()
        rec = None
        # save project label
        rec = ExpRecord()
        rec.table_id = self.table_id
        rec.uuid = man.uuid
        rec.project_uuid = man.project_uuid
        rec.row_num = row_num
        rec.field_num = 3
        rec.record = self.deref_entity_label(man.project_uuid)
        rec.save()
        rec = None
        # save project URI
        rec = ExpRecord()
        rec.table_id = self.table_id
        rec.uuid = man.uuid
        rec.project_uuid = man.project_uuid
        rec.row_num = row_num
        rec.field_num = 4
        rec.record = URImanagement.make_oc_uri(man.project_uuid, 'projects')
        rec.save()
        rec = None
        # save item category / class
        rec = ExpRecord()
        rec.table_id = self.table_id
        rec.uuid = man.uuid
        rec.project_uuid = man.project_uuid
        rec.row_num = row_num
        rec.field_num = 5
        rec.record = self.deref_entity_label(man.class_uri)
        rec.save()
        rec = None

    def deref_entity_label(self, entity_id):
        """ Dereferences an entity """
        output = False
        if entity_id in self.entities:
            ent = self.entities[entity_id]
            output = ent.label
        else:
            ent = Entity()
            found = ent.dereference(entity_id)
            if found:
                output = ent.label
                self.entities[entity_id] = ent
            else:
                self.entities[entity_id] = False
        return output
