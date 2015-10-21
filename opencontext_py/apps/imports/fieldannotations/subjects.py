import json
import hashlib
import uuid as GenUUID
from django.conf import settings
from django.db import models
from unidecode import unidecode
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.apps.ocitems.assertions.models import Assertion
from opencontext_py.apps.ocitems.geospace.models import Geospace, GeospaceGeneration
from opencontext_py.apps.ocitems.events.models import Event
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.ocitems.subjects.models import Subject
from opencontext_py.apps.entities.entity.models import Entity
from opencontext_py.apps.imports.fields.models import ImportField
from opencontext_py.apps.imports.fieldannotations.models import ImportFieldAnnotation
from opencontext_py.apps.imports.records.models import ImportCell
from opencontext_py.apps.imports.records.process import ProcessCells
from opencontext_py.apps.imports.fieldannotations.general import ProcessGeneral
from opencontext_py.apps.imports.sources.unimport import UnImport


# Processes to generate subjects items for an import
class ProcessSubjects():

    def __init__(self, source_id):
        self.source_id = source_id
        pg = ProcessGeneral(source_id)
        pg.get_source()
        self.project_uuid = pg.project_uuid
        self.subjects_fields = False
        self.geospace_fields = {}  # subject field num is key, dict has valid lat + lon fields
        self.geojson_rels = {}  # subject field_num is key, integer value is geojson field_num
        self.contain_ordered_subjects = {}
        self.non_contain_subjects = []
        self.root_subject_field = False  # field_num for the root subject field
        self.field_parent_entities = {}  # Parent entities named for a given field
        self.start_row = 1
        self.batch_size = settings.IMPORT_BATCH_SIZE
        self.end_row = self.batch_size
        self.example_size = 5
        self.count_active_fields = 0
        self.new_entities = []
        self.reconciled_entities = []
        self.not_reconciled_entities = []

    def clear_source(self):
        """ Clears a prior import if the start_row is 1.
            This makes sure new entities and assertions are made for
            this source_id, and we don't duplicate things
        """
        if self.start_row <= 1:
            # get rid of "subjects" related assertions made from this source
            unimport = UnImport(self.source_id,
                                self.project_uuid)
            unimport.delete_containment_assertions()
            unimport.delete_geospaces()
            unimport.delete_subjects_entities()

    def get_contained_examples(self):
        example_containment = []
        self.get_subject_fields()
        if self.root_subject_field is not False:
            example_containment = self.get_contained_field_exp(self.root_subject_field,
                                                               False,
                                                               True)
        return example_containment

    def get_contained_field_exp(self,
                                field_num,
                                in_rows=False,
                                check_parent_entity=False):
        """ get examples of entities in containment fields, does recursive lookups
            to get a whole tree, limited to a maximum of a few examples
        """
        contain_nodes = False
        add_field_examples = True
        if field_num == self.root_subject_field and check_parent_entity:
            # Check to see if the root is contained in a named entity
            if self.field_parent_entities[field_num] is not False:
                # Root is in a named entity, so add it.
                contain_nodes = []
                add_field_examples = False
                parent_uuid = self.field_parent_entities[field_num].uuid
                parent_context = self.field_parent_entities[field_num].context
                contain_node = LastUpdatedOrderedDict()
                contain_node['label'] = parent_context
                contain_node['type'] = 'subjects'
                contain_node['field_label'] = 'Parent of field: ' + self.subjects_fields[field_num].label
                contain_node['field_num'] = 0
                contain_node['id'] = parent_uuid
                # now look for children of the root entity.
                contain_node['children'] = self.get_contained_field_exp(field_num)
                contain_nodes.append(contain_node)
        if add_field_examples:
            pc = ProcessCells(self.source_id,
                              self.start_row)
            distinct_records = pc.get_field_records(field_num,
                                                    in_rows)
            if distinct_records is not False:
                contain_nodes = []
                unique_labels = []
                field_obj = self.subjects_fields[field_num]
                for rec_hash, dist_rec in distinct_records.items():
                    if len(contain_nodes) <= self.example_size:
                        # only add examples if we're less or equal to the the total example size
                        contain_node = LastUpdatedOrderedDict()
                        entity_label = dist_rec['imp_cell_obj'].record
                        if len(entity_label) < 1:
                            entity_label = '[BLANK]'
                        entity_label = field_obj.value_prefix + entity_label
                        contain_node['label'] = entity_label
                        contain_node['type'] = 'import-record'
                        contain_node['field_label'] = field_obj.label
                        contain_node['field_num'] = field_num
                        contain_node['id'] = dist_rec['rows'][0]
                        contain_node['children'] = False
                        if field_num in self.contain_ordered_subjects:
                            if self.contain_ordered_subjects[field_num] is not False:
                                unique_child_labels = []
                                for child_field in self.contain_ordered_subjects[field_num]:
                                    act_children = self.get_contained_field_exp(child_field,
                                                                                dist_rec['rows'])
                                    if act_children is not False:
                                        if contain_node['children'] is False:
                                            contain_node['children'] = []
                                        for act_child in act_children:
                                            if act_child['label'] not in unique_child_labels:
                                                # so we only list the same entity once
                                                contain_node['children'].append(act_child)
                                                unique_child_labels.append(act_child['label'])
                        if entity_label not in unique_labels:
                            # so we only list the same entity once
                            contain_nodes.append(contain_node)
                            unique_labels.append(entity_label)
        return contain_nodes

    def process_subjects_batch(self):
        """ processes containment fields for subject
            entities starting with a given row number.
            This iterates over all containment fields, starting
            with the root subject field

            Once containment subjects are done, this looks up
            subjects entities not in a containment hierarchy
        """
        self.clear_source()  # clear prior import for this source
        self.end_row = self.start_row + self.batch_size
        self.get_subject_fields()
        self.get_geospace_fields()
        self.get_geojson_fields()
        if self.root_subject_field is not False:
            self.process_field_hierarchy(self.root_subject_field)
        self.process_non_contain_subjects()

    def process_field_hierarchy(self,
                                field_num,
                                parent_uuid=False,
                                parent_context='',
                                in_rows=False):
        """ processes subject entitites from a given field. takes arguments
            about:
            1. field_num (the field to find candidate subject entities)
            2. parent_uuid (the uuid for the parent / containing subject entity)
            3. parent_context (the context path of the parent entitiy)
            4. in_rows (a list of row numbers to search within. this insures
               that entities are reconciled within contexts so that a
               Bone 1 in a Locus 1 is noted as different from a Bone 1 in
               Locus 2)

            Note: this function is recursive and calls itself if the
            the field_num has child fields.
        """
        pc = ProcessCells(self.source_id,
                          self.start_row)
        distinct_records = pc.get_field_records(field_num,
                                                in_rows)
        if distinct_records is not False:
            field_obj = self.subjects_fields[field_num]
            if field_num == self.root_subject_field and parent_uuid is False:
                if field_num in self.field_parent_entities:
                    if self.field_parent_entities[field_num] is not False:
                        parent_uuid = self.field_parent_entities[field_num].uuid
                        parent_context = self.field_parent_entities[field_num].context
            for rec_hash, dist_rec in distinct_records.items():
                cs = CandidateSubject()
                cs.project_uuid = self.project_uuid
                cs.source_id = self.source_id
                cs.obs_node = 'obs-' + str(field_obj.obs_num)
                cs.obs_num = field_obj.obs_num
                cs.parent_context = parent_context
                cs.parent_uuid = parent_uuid
                cs.label_prefix = field_obj.value_prefix
                cs.allow_new = True  # allow new because it is a hierarchic field
                cs.class_uri = field_obj.field_value_cat
                cs.import_rows = dist_rec['rows']  # list of rows where this record value is found
                cs.reconcile_item(dist_rec['imp_cell_obj'])
                # show_item = str(unidecode(dist_rec['imp_cell_obj'].record))
                # print('Reconciled item: ' + show_item)
                # print('--- Has uuid: ' + str(cs.uuid))
                if cs.uuid is not False:
                    self.process_geospace_item(field_num,
                                               cs.import_rows,
                                               cs.uuid)
                    self.process_geojson_item(field_num,
                                              cs.import_rows,
                                              cs.uuid)
                    if cs.is_new:
                        self.new_entities.append({'id': str(cs.uuid),
                                                  'label': cs.context})
                    else:
                        self.reconciled_entities.append({'id': str(cs.uuid),
                                                         'label': cs.context})
                    if field_num in self.contain_ordered_subjects:
                        if self.contain_ordered_subjects[field_num] is not False:
                            # subject entity successfully reconciled or created
                            # now process next level down in hierarchy, if it exists
                            for child_field in self.contain_ordered_subjects[field_num]:
                                self.process_field_hierarchy(child_field,
                                                             cs.uuid,
                                                             cs.context,
                                                             dist_rec['rows'])
                else:
                    bad_id = str(dist_rec['imp_cell_obj'].field_num) + '-' + str(dist_rec['imp_cell_obj'].row_num)
                    self.not_reconciled_entities.append({'id': str(bad_id),
                                                         'label': dist_rec['imp_cell_obj'].record})

    def process_non_contain_subjects(self):
        """ processes subject entitites that are not in
            containment relations.
            This only allows reconciliation based
            on subject labels, it does not allow
            creation of new subjects.
            Subjects can only be created if they are
            defined in a spatial hierarchy
        """
        if len(self.non_contain_subjects) > 0:
            print('Non-contain process')
            for field_num in self.non_contain_subjects:
                pc = ProcessCells(self.source_id,
                                  self.start_row)
                distinct_records = pc.get_field_records(field_num,
                                                        False)
                if distinct_records is not False:
                    field_obj = self.subjects_fields[field_num]
                    for rec_hash, dist_rec in distinct_records.items():
                        cs = CandidateSubject()
                        cs.project_uuid = self.project_uuid
                        cs.source_id = self.source_id
                        cs.obs_node = 'obs-' + str(field_obj.obs_num)
                        cs.obs_num = field_obj.obs_num
                        cs.parent_context = False
                        cs.parent_uuid = False
                        cs.label_prefix = field_obj.value_prefix
                        cs.allow_new = False  # do not allow new, not in a hierarchy
                        cs.class_uri = field_obj.field_value_cat
                        cs.import_rows = dist_rec['rows']  # list of rows where this record value is found
                        cs.reconcile_item(dist_rec['imp_cell_obj'])
                        if cs.uuid is not False:
                            self.process_geospace_item(field_num,
                                                       cs.import_rows,
                                                       cs.uuid)
                            self.process_geojson_item(field_num,
                                                      cs.import_rows,
                                                      cs.uuid)
                            self.reconciled_entities.append({'id': cs.uuid,
                                                             'label': cs.label})
                        else:
                            bad_id = str(dist_rec['imp_cell_obj'].field_num)
                            bad_id += '-' + str(dist_rec['imp_cell_obj'].row_num)
                            self.not_reconciled_entities.append({'id': bad_id,
                                                                 'label': dist_rec['imp_cell_obj'].record})

    def process_geospace_item(self,
                              subject_field_num,
                              subject_in_rows,
                              subject_uuid):
        """ adds lat lon data if it exists for an item
        """
        if subject_field_num in self.geospace_fields:
            # this subject field has associated lat - lon data
            # now make a list where of rows that have non-blank lat data
            act_geo_fields = self.geospace_fields[subject_field_num]
            rows = {}
            lat_recs = ImportCell.objects\
                                 .filter(source_id=self.source_id,
                                         field_num=act_geo_fields['lat'],
                                         row_num__in=subject_in_rows)\
                                 .exclude(record='')
            for lat_rec in lat_recs:
                rows[lat_rec.row_num] = {'lat': False,
                                         'lon': False}
                rows[lat_rec.row_num]['lat'] = self.validate_geo_coordinate(lat_rec.record,
                                                                            'lat')
            lon_recs = ImportCell.objects\
                                 .filter(source_id=self.source_id,
                                         field_num=act_geo_fields['lon'],
                                         row_num__in=subject_in_rows)\
                                 .exclude(record='')
            for lon_rec in lon_recs:
                if lon_rec.row_num not in rows:
                    rows[lon_rec.row_num] = {'lat': False,
                                             'lon': False}
                rows[lon_rec.row_num]['lon'] = self.validate_geo_coordinate(lon_rec.record,
                                                                            'lon')
            # the rows object now has a list of all the rows, with validated coordinate
            # data. Now we can add these to the database!
            geo_feature = 1
            geo_keys_done = []
            for row_key, row in rows.items():
                if row['lat'] is not False and \
                   row['lon'] is not False:
                    geo_key = str(row['lat']) + ',' + str(row['lon'])
                    if geo_key not in geo_keys_done:
                        # we havent checked this set of coordinates yet
                        geo_keys_done.append(geo_key)
                        # now check to make sure we don't already have these coordinates
                        # on this item
                        same_geos = Geospace.objects\
                                            .filter(uuid=subject_uuid,
                                                    latitude=row['lat'],
                                                    longitude=row['lon'])[:1]
                        if len(same_geos) < 1:
                            # it is a new coordinate, ok to add
                            geo = Geospace()
                            geo.uuid = str(subject_uuid)
                            geo.project_uuid = self.project_uuid
                            geo.source_id = self.source_id
                            geo.item_type = 'subjects'
                            geo.feature_id = geo_feature
                            geo.meta_type = ImportFieldAnnotation.PRED_GEO_LOCATION
                            geo.ftype = 'Point'
                            geo.latitude = row['lat']
                            geo.longitude = row['lon']
                            geo.specificity = 0
                            # dump coordinates as json string in lon - lat (GeoJSON order)
                            geo.coordinates = json.dumps([row['lon'], row['lat']],
                                                         indent=4,
                                                         ensure_ascii=False)
                            try:
                                geo.save()
                                geo_feature += 1
                            except:
                                print('Did not like ' + str(row) + ' with ' + str(subject_uuid))
                                quit()

    def process_geojson_item(self,
                             subject_field_num,
                             subject_in_rows,
                             subject_uuid):
        """ adds geojson data if it exists for an item
        """
        if subject_field_num in self.geojson_rels:
            geojson_field_num = self.geojson_rels[subject_field_num]
            geojson_recs = ImportCell.objects\
                                     .filter(source_id=self.source_id,
                                             field_num=geojson_field_num,
                                             row_num__in=subject_in_rows)\
                                     .exclude(record='')
            # the rows object now has a list of all the rows, with validated coordinate
            # data. Now we can add these to the database!
            geo_keys_done = []
            gg = GeospaceGeneration()
            for geojson_rec in geojson_recs:
                geo_key = geojson_rec.rec_hash
                record = geojson_rec.record
                if geo_key not in geo_keys_done:
                    geo_keys_done.append(geo_key)
                    try:
                        json_obj = json.loads(record)
                    except:
                        json_obj = False
                    if isinstance(json_obj, dict):
                        if 'type' in json_obj \
                           and 'coordinates' in json_obj:
                            # OK we've got good data
                            lon_lat = gg.get_centroid_lonlat_coordinates(record,
                                                                         json_obj['type'])
                            if isinstance(lon_lat, tuple):
                                # print('Good centroid for ' + str(subject_uuid))
                                # great! We have centroid lon_lat
                                # this is another data validation passed
                                coordinates = json_obj['coordinates']
                                same_geos = Geospace.objects\
                                                    .filter(uuid=subject_uuid,
                                                            coordinates=coordinates)[:1]
                                if len(same_geos) < 1:
                                    # OK it is valid and does not exist for the item
                                    # we can add it
                                    geo = Geospace()
                                    geo.uuid = str(subject_uuid)
                                    geo.project_uuid = self.project_uuid
                                    geo.source_id = self.source_id
                                    geo.item_type = 'subjects'
                                    geo.feature_id = len(geo_keys_done)
                                    geo.meta_type = ImportFieldAnnotation.PRED_GEO_LOCATION
                                    geo.ftype = json_obj['type']
                                    geo.latitude = lon_lat[1]
                                    geo.longitude = lon_lat[0]
                                    geo.specificity = 0
                                    # dump coordinates as json string
                                    geo.coordinates = json.dumps(coordinates,
                                                                 indent=4,
                                                                 ensure_ascii=False)
                                    try:
                                        geo.save()
                                    except:
                                        print('Did not like ' + str(row) + ' with ' + str(subject_uuid))
                                        quit()

    def validate_geo_coordinate(self, coordinate, coord_type):
        """ validates a geo-spatial coordinate
            returns a float if valid, or false if not valid
        """
        is_valid = False
        try:
            fl_coord = float(coordinate)
        except ValueError:
            fl_coord = False
        if fl_coord is not False:
            if 'lat' in coord_type:
                if fl_coord <= 90 and\
                   fl_coord >= -90:
                    is_valid = True
            elif 'lon' in coord_type:
                if fl_coord <= 180 and\
                   fl_coord >= -180:
                    is_valid = True
        if is_valid:
            return fl_coord
        else:
            return False

    def get_geospace_fields(self):
        """ finds geospatial (lat + lon) fields that may describe
            subjects fields.
        """
        # first make a list of subject field numbers
        sub_field_list = []
        for sub_field_num, sub_field in self.subjects_fields.items():
            sub_field_list.append(sub_field_num)
        geo_des = ImportFieldAnnotation.objects\
                                       .filter(source_id=self.source_id,
                                               predicate=ImportFieldAnnotation.PRED_GEO_LOCATION,
                                               object_field_num__in=sub_field_list)
        if len(geo_des) >= 2:
            # print('Found ' + str(len(geo_des)) + ' lat lon fields')
            # we have geospatial coordinate data describing our subjects
            # now get the lat fields, and the lon fields
            lats = {}
            lons = {}
            lats_lons = ImportField.objects\
                                   .filter(source_id=self.source_id,
                                           field_type__in=['lat', 'lon'])
            for act_f in lats_lons:
                if act_f.field_type == 'lat':
                    lats[act_f.field_num] = act_f
                else:
                    lons[act_f.field_num] = act_f
            # now make an object that checks to see if
            # the subject (location/object field), which is the
            # object of the ImportFieldAnnotations, has exactly 1
            # lat field and 1 lon field
            geo_lats_lons = {}
            for geo_anno in geo_des:
                if geo_anno.object_field_num not in geo_lats_lons:
                    geo_lats_lons[geo_anno.object_field_num] = {'lats': [],
                                                                'lons': []}
                if geo_anno.field_num in lats:
                    # it's a lat field
                    geo_lats_lons[geo_anno.object_field_num]['lats'].append(geo_anno.field_num)
                elif geo_anno.field_num in lons:
                    geo_lats_lons[geo_anno.object_field_num]['lons'].append(geo_anno.field_num)
            # print('geo_lat_lons: ' + str(geo_lats_lons))
            for subject_field_num, act_geo_lats_lons in geo_lats_lons.items():
                if len(act_geo_lats_lons['lats']) == 1 \
                   and len(act_geo_lats_lons['lons']) == 1:
                    # case where the subject_field_num has exactly 1 lat and 1 lon field. OK for
                    # making geospatial data
                    self.geospace_fields[subject_field_num] = {'lat': act_geo_lats_lons['lats'][0],
                                                               'lon': act_geo_lats_lons['lons'][0]}

    def get_geojson_fields(self):
        """ gets fields with geojson data """
        geojson_fields = ImportField.objects\
                                    .filter(source_id=self.source_id,
                                            field_type='geojson')
        geojson_field_nums = []
        for geojson_field in geojson_fields:
            geojson_field_nums.append(geojson_field.field_num)
        sub_field_list = []
        for sub_field_num, sub_field in self.subjects_fields.items():
            sub_field_list.append(sub_field_num)
        geo_des = ImportFieldAnnotation.objects\
                                       .filter(source_id=self.source_id,
                                               field_num__in=geojson_field_nums,
                                               predicate=ImportFieldAnnotation.PRED_GEO_LOCATION,
                                               object_field_num__in=sub_field_list)
        for geo_anno in geo_des:
            self.geojson_rels[geo_anno.object_field_num] = geo_anno.field_num

    def get_subject_fields(self):
        """ Gets subject fields, puts them into a containment hierarchy
            or a list of fields that are not in containment relationships
        """
        sub_fields = ImportField.objects\
                                .filter(source_id=self.source_id,
                                        field_type='subjects')
        if len(sub_fields) > 0:
            self.count_active_fields = len(sub_fields)
            self.subjects_fields = {}
            # Assertion.PREDICATES_CONTAINS
            for sub_field in sub_fields:
                self.subjects_fields[sub_field.field_num] = sub_field
                parent_anno = ImportFieldAnnotation.objects\
                                                   .filter(source_id=self.source_id,
                                                           object_field_num=sub_field.field_num,
                                                           predicate=Assertion.PREDICATES_CONTAINS)[:1]
                child_anno = ImportFieldAnnotation.objects\
                                                  .filter(source_id=self.source_id,
                                                          field_num=sub_field.field_num,
                                                          predicate=Assertion.PREDICATES_CONTAINS)
                if len(child_anno) > 0:
                    self.contain_ordered_subjects[sub_field.field_num] = []
                    for child in child_anno:
                        self.contain_ordered_subjects[sub_field.field_num].append(child.object_field_num)
                    if len(parent_anno) < 1:
                        # field has children, but no parent it's at the root level
                        self.root_subject_field = sub_field.field_num
                        # check to see if the root field has a parent entity
                        self.get_field_parent_entity(sub_field.field_num)
                else:
                    if len(parent_anno) > 0:
                        # field has no child fields.
                        self.contain_ordered_subjects[sub_field.field_num] = False
                    else:
                        # check to see if the uncontained field has a parent entity
                        parent_entity_found = self.get_field_parent_entity(sub_field.field_num)
                        if parent_entity_found is False:
                            # field has no containment relations
                            self.non_contain_subjects.append(sub_field.field_num)

    def get_field_parent_entity(self, field_num):
        """ Get's a parent entity named for a given field """
        parent_entity_found = False
        self.field_parent_entities[field_num] = False
        parent_anno = ImportFieldAnnotation.objects\
                                           .filter(source_id=self.source_id,
                                                   field_num=field_num,
                                                   predicate=ImportFieldAnnotation.PRED_CONTAINED_IN)[:1]
        if len(parent_anno) > 0:
            ent = Entity()
            ent.get_context = True
            found = ent.dereference(parent_anno[0].object_uuid)
            if found:
                self.field_parent_entities[field_num] = ent
                parent_entity_found = True
        return parent_entity_found


class CandidateSubject():

    DEFAULT_BLANK = '[Blank]'

    def __init__(self):
        self.project_uuid = False
        self.source_id = False
        self.parent_uuid = False
        self.obs_node = False
        self.obs_num = 0
        self.parent_context = ''
        self.label_prefix = ''
        self.context = ''
        self.label = False
        self.class_uri = ''
        self.uuid = False  # final, uuid for the item
        self.imp_cell_obj = False  # ImportCell object
        self.evenif_blank = False  # Mint a new item even if the record is blank
        self.allow_new = False  # only allow new if item is imported in a hierachy, otherwise match with manifest
        self.import_rows = False  # if a list, then changes to uuids are saved for all rows in this list
        self.is_new = False

    def reconcile_item(self, imp_cell_obj):
        """ Checks to see if the item exists in the subjects table """
        self.imp_cell_obj = imp_cell_obj
        if len(imp_cell_obj.record) > 0:
            self.label = self.label_prefix + imp_cell_obj.record
        else:
            pg = ProcessGeneral(self.source_id)
            if self.import_rows is not False:
                check_list = self.import_rows
            else:
                check_list = [imp_cell_obj.row_num]
            self.evenif_blank = pg.check_blank_required(imp_cell_obj.field_num,
                                                        check_list)
            if self.evenif_blank:
                self.label = self.label_prefix + self.DEFAULT_BLANK
        if self.allow_new and self.label is not False:
            # Only create a new item if it is allowed and if the label is not false
            if len(self.parent_context) > 0:
                self.context = self.parent_context + Subject.HIEARCHY_DELIM + self.label
            else:
                self.context = self.label
            match_found = self.match_against_subjects(self.context)
            if match_found is False:
                # create new subject, manifest objects. Need new UUID, since we can't assume
                # the fl_uuid for the ImportCell reflects unique entities in a field, since
                # uniqueness depends on context (values in other cells)
                self.uuid = GenUUID.uuid4()
                self.create_subject_item()
                self.is_new = True
        else:
            if self.label is not False:
                # only allow matches on non-blank items when not creating a record
                match_found = self.match_against_manifest(self.label,
                                                          self.class_uri)
        self.update_import_cell_uuid()
        self.add_contain_assertion()

    def add_contain_assertion(self):
        """ Adds a containment assertion for the new subject item """
        if self.allow_new\
           and self.parent_uuid is not False\
           and self.uuid is not False:
            old_ass = Assertion.objects\
                               .filter(uuid=self.parent_uuid,
                                       obs_num=self.obs_num,
                                       predicate_uuid=Assertion.PREDICATES_CONTAINS,
                                       object_uuid=self.uuid)[:1]
            if len(old_ass) < 1:
                new_ass = Assertion()
                new_ass.uuid = self.parent_uuid
                new_ass.subject_type = 'subjects'
                new_ass.project_uuid = self.project_uuid
                new_ass.source_id = self.source_id
                new_ass.obs_node = '#contents-' + str(self.obs_num)
                new_ass.obs_num = self.obs_num
                new_ass.sort = 1
                new_ass.visibility = 1
                new_ass.predicate_uuid = Assertion.PREDICATES_CONTAINS
                new_ass.object_uuid = self.uuid
                new_ass.object_type = 'subjects'
                try:
                    # in case the relationship already exists
                    new_ass.save()
                except:
                    print('Containment failed: ' + str(new_ass.uuid) + ' ' + str(new_ass.object_uuid))
            else:
                print('Containment already exists')
        else:
            print('No attempt at Containment: ' + str(self.parent_uuid) + ' ' + str(self.uuid))

    def create_subject_item(self):
        """ Create and save a new subject object"""
        new_sub = Subject()
        new_sub.uuid = self.uuid  # use the previously assigned temporary UUID
        new_sub.project_uuid = self.project_uuid
        new_sub.source_id = self.source_id
        new_sub.context = self.context
        new_sub.save()
        new_man = Manifest()
        new_man.uuid = self.uuid
        new_man.project_uuid = self.project_uuid
        new_man.source_id = self.source_id
        new_man.item_type = 'subjects'
        new_man.repo = ''
        new_man.class_uri = self.class_uri
        new_man.label = self.label
        new_man.des_predicate_uuid = ''
        new_man.views = 0
        new_man.save()

    def update_import_cell_uuid(self):
        """ Saves the uuid to the import cell record """
        if self.uuid is not False:
            if self.import_rows is False:
                # only update the current import cell object
                self.imp_cell_obj.fl_uuid = self.uuid
                self.imp_cell_obj.uuids_save()
            else:
                # update all the import cells in the list of rows
                # to have the relevant uuid
                self.imp_cell_obj.fl_uuid = self.uuid
                self.imp_cell_obj.save()
                up_cells = ImportCell.objects\
                                     .filter(source_id=self.source_id,
                                             field_num=self.imp_cell_obj.field_num,
                                             row_num__in=self.import_rows)
                for up_cell in up_cells:
                    # save each cell with the correct UUID
                    up_cell.fl_uuid = self.uuid
                    up_cell.uuids_save()

    def match_against_subjects(self, context):
        """ Checks to see if the item exists in the subjects table """
        match_found = False
        hash_id = Subject().make_hash_id(self.project_uuid, context)
        try:
            subject_match = Subject.objects\
                                   .get(hash_id=hash_id)
        except Subject.DoesNotExist:
            subject_match = False
        if subject_match is not False:
            match_found = True
            self.uuid = subject_match.uuid
        return match_found

    def match_against_manifest(self, label, class_uri):
        """ Checks to see if the item exists in the manifest """
        match_found = False
        manifest_match = Manifest.objects\
                                 .filter(project_uuid=self.project_uuid,
                                         label=label,
                                         class_uri=class_uri)[:1]
        if len(manifest_match) > 0:
            match_found = True
            self.uuid = manifest_match[0].uuid
            self.imp_cell_obj.fl_uuid = self.uuid
            self.imp_cell_obj.cell_ok = True
            self.imp_cell_obj.save()
        else:
            # can't match the item in the manifest
            if self.allow_new is False:
                # mark the cell to be ignored. It can't be associated with any entities
                self.imp_cell_obj.cell_ok = False
                self.imp_cell_obj.save()
        return match_found
