import datetime
import json
from django.db import models
from django.db.models import Avg, Max, Min
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.apps.exports.fields.models import ExpField
from opencontext_py.apps.exports.records.models import ExpCell
from opencontext_py.apps.exports.records.uuidlist import UUIDListSimple, UUIDListExportTable
from opencontext_py.apps.entities.uri.models import URImanagement
from opencontext_py.apps.entities.entity.models import Entity
from opencontext_py.apps.ocitems.geospace.models import Geospace
from opencontext_py.apps.ocitems.events.models import Event
from opencontext_py.apps.ocitems.assertions.containment import Containment
from opencontext_py.apps.ocitems.assertions.models import Assertion
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.ldata.linkannotations.authorship import Authorship
from opencontext_py.apps.ldata.linkannotations.models import LinkAnnotation
from opencontext_py.apps.ldata.linkentities.sorting import LinkEntitySorter


# Creates an export table
class Create():

    EQUIV_PREDICATES = ['skos:closeMatch',
                        'http://www.w3.org/2004/02/skos/core#closeMatch']

    def __init__(self):
        self.table_id = False
        self.label = False
        self.dates_bce_ce = True  # calendar dates in BCE/CE, if false BP
        self.include_equiv_ld = True  # include linked data related by EQUIV_PREDICATES
        self.inlude_ld_obj_uris = True  # include URIs to linked data objects
        self.include_ld_equiv_values = True  # include original values annoted as
                                             # equivalent to linked data
        self.boolean_multiple_ld_fields = 'yes'  # for multiple values of linked data
                                                 # (same predicate, multiple objects)
                                                 # make multiple fields if NOT False.
                                                 # When this value is NOT False, its
                                                 # string value indicates presence of
                                                 # a linked data object uri.
        self.include_original_fields = False  # include original field data
        self.fields = []
        self.context_fields = LastUpdatedOrderedDict()
        self.ld_fields = LastUpdatedOrderedDict()
        self.entities = {}
        self.predicate_uris_boolean_types = False  # predicate_uris expressed as boolean types
        self.predicate_uuids = LastUpdatedOrderedDict()  # predicate uuids used with a table
        self.ld_predicates = LastUpdatedOrderedDict()  # unique linked_data predicates
        self.uuidlist = []

    def prep_default_fields(self):
        """ Prepares initial set of default fields for export tables """
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
        self.fields.append({'label': 'Last Updated',
                            'rel_ids': ['last-updated'],
                            'field_num': 6})
        self.fields.append({'label': 'Authorship',
                            'rel_ids': ['authorship'],
                            'field_num': 7})
        self.fields.append({'label': 'Latitude (WGS-84)',
                            'rel_ids': ['latitude'],
                            'field_num': 8})
        self.fields.append({'label': 'Longitude (WGS-84)',
                            'rel_ids': ['longitude'],
                            'field_num': 9})
        self.fields.append({'label': 'Geospatial note',
                            'rel_ids': ['geospatial-note'],
                            'field_num': 10})
        if self.dates_bce_ce:
            self.fields.append({'label': 'Early Date (BCE/CE)',
                                'rel_ids': ['early-bce-ce'],
                                'field_num': 11})
            self.fields.append({'label': 'Late Date (BCE/CE)',
                                'rel_ids': ['late-bce-ce'],
                                'field_num': 12})
        else:
            self.fields.append({'label': 'Early Date (BP)',
                                'rel_ids': ['early-bp'],
                                'field_num': 11})
            self.fields.append({'label': 'Late Date (BP)',
                                'rel_ids': ['late-bp'],
                                'field_num': 12})
        self.fields.append({'label': 'Context URI',
                            'rel_ids': ['context-uri'],
                            'field_num': 13})
        for field in self.fields:
            self.save_field(field)

    def save_field(self, field):
        """ Saves a record of a field """
        exfield = ExpField()
        exfield.table_id = self.table_id
        exfield.field_num = field['field_num']
        exfield.label = field['label']
        exfield.rel_ids = json.dumps(field['rel_ids'], ensure_ascii=False)
        exfield.save()

    def process_uuids_simple(self, project_uuids, class_uri):
        """ Gets a list of uuids and basic metadata about items for the
            export table. Does so in the simpliest way, filtering only
            by a list of project_uuids and class_uri """
        self.prep_default_fields()
        self.uuidlist = UUIDListSimple(project_uuids, class_uri).uuids
        self.process_uuid_list(self.uuidlist)

    def process_uuid_list(self, uuids, starting_row=1):
        row_num = starting_row
        for uuid in uuids:
            try:
                man = Manifest.objects.get(uuid=uuid)
            except Manifest.DoesNotExist:
                man = False
            if man is not False:
                print(str(row_num) + ': ' + str(uuid))
                self.save_basic_default_field_cells(row_num, man)
                self.save_authorship(row_num, man)
                act_contain = Containment()
                parents = act_contain.get_parents_by_child_uuid(man.uuid)
                subject_list = act_contain.contexts_list
                subject_list.insert(0, man.uuid)
                geo_meta = act_contain.get_geochron_from_subject_list(subject_list, 'geo')
                event_meta = act_contain.get_geochron_from_subject_list(subject_list, 'event')
                self.save_default_geo(row_num, man, geo_meta)
                self.save_default_chrono(row_num, man, event_meta)
                self.save_context(row_num, man, parents)
                row_num += 1
            else:
                print(uuid + ' Failed!')

    def get_predicate_uuids(self):
        """ Gets predicate uuids for a table """
        self.entities = {}  # resets the entites, no need to keep context entitites in memory
        uuids = UUIDListExportTable(self.table_id).uuids
        # seems faster than a select distinct with a join.
        for uuid in uuids:
            pred_uuids = Assertion.objects\
                                  .values_list('predicate_uuid', flat=True)\
                                  .filter(uuid=uuid)
            item_preds = LastUpdatedOrderedDict()
            for pred_uuid in pred_uuids:
                if pred_uuid not in item_preds:
                    item_preds[pred_uuid] = 1
                else:
                    item_preds[pred_uuid] += 1
            for pred_uuid, count in item_preds.items():
                if pred_uuid not in self.predicate_uuids:
                    pred_label = self.deref_entity_label(pred_uuid)
                    pred_type = self.entities[pred_uuid].data_type
                    self.predicate_uuids[pred_uuid] = {'count': count,
                                                       'label': pred_label,
                                                       'type': pred_type}
                else:
                    if self.predicate_uuids[pred_uuid]['count'] < count:
                        self.predicate_uuids[pred_uuid]['count'] = count
        return self.predicate_uuids

    def get_predicate_link_annotations(self):
        """ Gets the link data annotations for predicates used on a table """
        auth = Authorship()
        for pred_uuid, pred in self.predicate_uuids.items():
            la_s = LinkAnnotation.objects\
                                 .filter(subject=pred_uuid)
            if len(la_s) > 0:
                self.predicate_uuids[pred_uuid]['annotations'] = []
            for la in la_s:
                link_anno = {'pred': la.predicate_uri,
                             'obj': la.object_uri}
                self.predicate_uuids[pred_uuid]['annotations'].append(link_anno)
                if la.predicate_uri in self.EQUIV_PREDICATES:
                    authorship = auth.check_authorship_object(la.object_uri)
                    if authorship is False:  # only keep predicates not related to authorship
                        if la.object_uri not in self.ld_predicates:
                            pred_equiv_label = self.deref_entity_label(la.object_uri)
                            self.ld_predicates[la.object_uri] = {'uuids': [pred_uuid],
                                                                 'obj_uuids': {},
                                                                 'obj_uris': [],
                                                                 'label': pred_equiv_label}
                        else:
                            self.ld_predicates[la.object_uri]['uuids'].append(pred_uuid)
        return self.ld_predicates

    def get_ld_predicate_values(self, ld_field_uri):
        """ gets a list of object_uuids used with predicates related to a
            ld_field_uri
        """
        object_uuids = Assertion.objects\
                                .values_list('object_uuid', flat=True)\
                                .filter(predicate_uuid__in=self.ld_predicates[ld_field_uri]['uuids'])\
                                .distinct()
        for obj_uuid in object_uuids:
            if obj_uuid not in self.ld_predicates[ld_field_uri]['obj_uuids']:
                obj_equiv_uris = []
                # get link data annotations for the object_uuid
                la_s = LinkAnnotation.objects\
                                     .filter(subject=obj_uuid)
                for la in la_s:
                    if la.predicate_uri in self.EQUIV_PREDICATES:
                        obj_equiv_uri = la.object_uri
                        obj_equiv_uris.append(obj_equiv_uri)
                        if obj_equiv_uri not in self.ld_predicates[ld_field_uri]['obj_uris']:
                            self.ld_predicates[ld_field_uri]['obj_uris'].append(obj_equiv_uri)
                self.ld_predicates[ld_field_uri]['obj_uuids'][obj_uuid] = obj_equiv_uris
        return self.ld_predicates[ld_field_uri]

    def process_ld_fields_values(self):
        """ Creates fields for linked data, then saves
            records of linked data for each item in the export
            table
        """
        if self.include_equiv_ld and len(self.ld_predicates) > 0:
            for ld_pred_uri, ld_pred in self.ld_predicates.items():
                if self.boolean_multiple_ld_fields is not False:
                    le_sort = LinkEntitySorter()
                    #  sort the URIs for the objects, so the fields come in a
                    #  nice, reasonable order.
                    sort_obj_uris = le_sort.sort_ld_entity_list(ld_pred['obj_uris'])
                    for ld_obj_uri in sort_obj_uris:
                        field_num = self.get_add_ld_field_number('[Has]',
                                                                 ld_pred_uri,
                                                                 ld_obj_uri)

    def get_add_ld_field_number(self, field_type, ld_obj_uri, ld_obj_uri=False):
        """ Gets the field_num for a linked data field, given the uri
            for the linked data field, and optionally the object
            Creates a new field for the linked data as needed
        """
        if ld_obj_uri is not False:
            field_key = ld_pred_uri + '::' + ld_obj_uri
        else:
            field_key = ld_pred_uri
        if len(field_type) > 0:
            field_key += '::' + field_type
        if field_key in self.ld_fields:
            field_num = self.ld_fields[field_key]
        else:
            field_num = len(self.fields) + 1
            label = self.deref_entity_label(ld_pred_uri)
            rel_ids = [field_type, ld_pred_uri]
            if ld_obj_uri is not False:
                rel_ids.append(ld_obj_uri)
                obj_label = self.deref_entity_label(ld_obj_uri)
                label = label + ' :: ' + obj_label
            if len(field_type) > 0:
                label += ' ' + field_type
            field = {'label': label,
                     'rel_ids': rel_ids,
                     'field_num': field_num}
            self.fields.append(field)
            self.save_field(field)
            self.ld_fields[field_key] = field_num
        return field_num

    def save_context(self, row_num, man, raw_parents):
        """ Save context information, will also add new context fields
            as needed
        """
        use_parents = False
        context_uri = ''
        if raw_parents is not False:
            if len(raw_parents) > 0:
                for tree_node, r_parents in raw_parents.items():
                    # the first parent is the the one to use for making a context URI
                    context_uri = URImanagement.make_oc_uri(r_parents[0], 'subjects')
                    # now reverse the order, so the top most general is first
                    use_parents = r_parents[::-1]
        # save a record of the context URI
        cell = ExpCell()
        cell.table_id = self.table_id
        cell.uuid = man.uuid
        cell.project_uuid = man.project_uuid
        cell.row_num = row_num
        cell.field_num = 13
        cell.record = context_uri
        cell.save()
        cell = None
        if use_parents is not False:
            pindex = 0
            for parent_uuid in use_parents:
                pindex += 1
                context_label = self.deref_entity_label(parent_uuid)
                field_num = self.get_add_context_field_number(pindex)
                cell = ExpCell()
                cell.table_id = self.table_id
                cell.uuid = man.uuid
                cell.project_uuid = man.project_uuid
                cell.row_num = row_num
                cell.field_num = field_num
                cell.record = context_label
                cell.save()
                cell = None

    def get_add_context_field_number(self, pindex):
        """ Gets the field_num for a context field, given the pindex
            which indicates depth in the context hierarchy.
            Creates a new field for the context level as needed
        """
        if pindex in self.context_fields:
            field_num = self.context_fields[pindex]
        else:
            field_num = len(self.fields) + 1
            field = {'label': 'Context (' + str(pindex) + ')',
                     'rel_ids': ['context', pindex],
                     'field_num': field_num}
            self.fields.append(field)
            self.save_field(field)
            self.context_fields[pindex] = field_num
        return field_num

    def save_default_chrono(self, row_num, man, event_meta):
        """ Saves earliest / latest times for an item """
        earliest = ''
        latest = ''
        if event_meta is not False:
            times = []
            for event in event_meta:
                times.append(event.start)
                times.append(event.stop)
            earliest = min(times)
            latest = max(times)
            if self.dates_bce_ce is False:
                earliest = 1950 - earliest
                latest = 1950 - latest
            earliest = round(earliest, 0)
            latest = round(latest, 0)
        # save earliest
        cell = ExpCell()
        cell.table_id = self.table_id
        cell.uuid = man.uuid
        cell.project_uuid = man.project_uuid
        cell.row_num = row_num
        cell.field_num = 11
        cell.record = str(earliest)
        cell.save()
        cell = None
        # save latest
        cell = ExpCell()
        cell.table_id = self.table_id
        cell.uuid = man.uuid
        cell.project_uuid = man.project_uuid
        cell.row_num = row_num
        cell.field_num = 12
        cell.record = str(latest)
        cell.save()
        cell = None

    def save_default_geo(self, row_num, man, geo_meta):
        """ Saves geo lat / lon data for an item """
        latitude = ''
        longitude = ''
        note = 'Best available location data'
        if geo_meta is not False:
            for geo in geo_meta:
                if geo.meta_type == 'oc-gen:discovey-location':
                    latitude = geo.latitude
                    longitude = geo.longitude
                    if geo.specificity < 0:
                        note = 'Location approximated \
                        as a security precaution (Zoom: ' + str(abs(geo.specificity)) + ')'
                    break
        # save Latitude
        cell = ExpCell()
        cell.table_id = self.table_id
        cell.uuid = man.uuid
        cell.project_uuid = man.project_uuid
        cell.row_num = row_num
        cell.field_num = 8
        cell.record = str(latitude)
        cell.save()
        cell = None
        # save Longitude
        cell = ExpCell()
        cell.table_id = self.table_id
        cell.uuid = man.uuid
        cell.project_uuid = man.project_uuid
        cell.row_num = row_num
        cell.field_num = 9
        cell.record = str(longitude)
        cell.save()
        cell = None
        # save Note
        cell = ExpCell()
        cell.table_id = self.table_id
        cell.uuid = man.uuid
        cell.project_uuid = man.project_uuid
        cell.row_num = row_num
        cell.field_num = 10
        cell.record = note
        cell.save()
        cell = None

    def save_authorship(self, row_num, man):
        """ Saves authorship information """
        authors = ''
        auth = Authorship()
        found = auth.get_authors(man.uuid,
                                 man.project_uuid)
        if found:
            all_author_ids = auth.creators + auth.contributors
            all_authors = []
            for auth_id in all_author_ids:
                author = self.deref_entity_label(auth_id)
                all_authors.append(author)
            authors = '; '.join(all_authors)
        # save Authors
        cell = ExpCell()
        cell.table_id = self.table_id
        cell.uuid = man.uuid
        cell.project_uuid = man.project_uuid
        cell.row_num = row_num
        cell.field_num = 7
        cell.record = authors
        cell.save()
        cell = None

    def save_basic_default_field_cells(self, row_num, man):
        """ Saves the default fields that do not involve containment lookups """
        # save URI
        cell = ExpCell()
        cell.table_id = self.table_id
        cell.uuid = man.uuid
        cell.project_uuid = man.project_uuid
        cell.row_num = row_num
        cell.field_num = 1
        cell.record = URImanagement.make_oc_uri(man.uuid, man.item_type)
        cell.save()
        cell = None
        # save label
        cell = ExpCell()
        cell.table_id = self.table_id
        cell.uuid = man.uuid
        cell.project_uuid = man.project_uuid
        cell.row_num = row_num
        cell.field_num = 2
        cell.record = man.label
        cell.save()
        cell = None
        # save project label
        cell = ExpCell()
        cell.table_id = self.table_id
        cell.uuid = man.uuid
        cell.project_uuid = man.project_uuid
        cell.row_num = row_num
        cell.field_num = 3
        cell.record = self.deref_entity_label(man.project_uuid)
        cell.save()
        cell = None
        # save project URI
        cell = ExpCell()
        cell.table_id = self.table_id
        cell.uuid = man.uuid
        cell.project_uuid = man.project_uuid
        cell.row_num = row_num
        cell.field_num = 4
        cell.record = URImanagement.make_oc_uri(man.project_uuid, 'projects')
        cell.save()
        cell = None
        # save item category / class
        cell = ExpCell()
        cell.table_id = self.table_id
        cell.uuid = man.uuid
        cell.project_uuid = man.project_uuid
        cell.row_num = row_num
        cell.field_num = 5
        cell.record = self.deref_entity_label(man.class_uri)
        cell.save()
        cell = None
        # last updated
        if man.revised is datetime:
            last_update = man.revised
        else:
            last_update = man.record_updated
        cell = ExpCell()
        cell.table_id = self.table_id
        cell.uuid = man.uuid
        cell.project_uuid = man.project_uuid
        cell.row_num = row_num
        cell.field_num = 6
        cell.record = last_update.strftime('%Y-%m-%d')
        cell.save()
        cell = None

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
                print('Missing id: ' + entity_id)
        return output
