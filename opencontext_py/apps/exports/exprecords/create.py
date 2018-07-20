import datetime
import json
from django.db import models
from django.db.models import Avg, Max, Min
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.apps.exports.exptables.models import ExpTable
from opencontext_py.apps.exports.expfields.models import ExpField
from opencontext_py.apps.exports.exprecords.models import ExpCell
from opencontext_py.apps.exports.exprecords.uuidlist import UUIDListSimple,\
    UUIDListExportTable,\
    UUIDsRowsExportTable
from opencontext_py.apps.entities.uri.models import URImanagement
from opencontext_py.apps.entities.entity.models import Entity
from opencontext_py.apps.ocitems.geospace.models import Geospace
from opencontext_py.apps.ocitems.events.models import Event
from opencontext_py.apps.ocitems.assertions.containment import Containment
from opencontext_py.apps.ocitems.assertions.models import Assertion
from opencontext_py.apps.ocitems.strings.models import OCstring
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.ldata.linkannotations.authorship import Authorship
from opencontext_py.apps.ldata.linkannotations.models import LinkAnnotation
from opencontext_py.apps.ldata.linkentities.sorting import LinkEntitySorter


# Creates records for an export table
class Create():

    EQUIV_PREDICATES = ['skos:closeMatch',
                        'http://www.w3.org/2004/02/skos/core#closeMatch',
                        'skos:exactMatch',
                        'http://www.w3.org/2004/02/skos/core#exactMatch']

    # some linked data predicates should be exported into more than 1 field, depending
    # on the object used. the LD_MULTI_FIELD constant configures such fields
    LD_MULTI_FIELD = {
        'http://opencontext.org/vocabularies/open-context-zooarch/has-fusion-char': [
            {'prefix': 'Proximal ',  # proximal fusion state
             'object_uris':
                ['http://opencontext.org/vocabularies/open-context-zooarch/prox-epi-fused',
                 'http://opencontext.org/vocabularies/open-context-zooarch/prox-epi-fusing',
                 'http://opencontext.org/vocabularies/open-context-zooarch/prox-epi-unfused']},
            {'prefix': 'Distal ',  # distal fusion state
             'object_uris':
                ['http://opencontext.org/vocabularies/open-context-zooarch/dist-epi-fused',
                 'http://opencontext.org/vocabularies/open-context-zooarch/dist-epi-fusing',
                 'http://opencontext.org/vocabularies/open-context-zooarch/dist-epi-unfused']}
        ]
    }

    def __init__(self):
        self.table_id = False
        self.label = False
        self.dates_bce_ce = True  # calendar dates in BCE/CE, if false BP
        self.include_equiv_ld = True  # include linked data related by EQUIV_PREDICATES
        self.include_equiv_ld_literals = True  # include linked data related by Equiv Predicates for literal objects
        self.include_ld_obj_uris = True  # include URIs to linked data objects
        self.include_ld_source_values = True  # include original values annoted as
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
        self.predicate_fields = LastUpdatedOrderedDict()
        self.source_field_label_suffix = ' [Source]'
        self.multi_source_value_delim = '; '  # delimiter for multiple values in source data field
        self.obs_limits = []  # limits predicate exports to listed observation numbers, no limit if empty
        self.entities = {}
        self.numeric_fields_last = False
        self.predicate_uris_boolean_types = False  # predicate_uris expressed as boolean types
        self.predicate_uuids = LastUpdatedOrderedDict()  # predicate uuids used with a table
        self.ld_predicates = LastUpdatedOrderedDict()  # unique linked_data predicates
        self.ld_literal_preds = LastUpdatedOrderedDict()  # unique linked_data for literal values
        self.ld_object_equivs = LastUpdatedOrderedDict()  # unique linked_data predicates
        self.dc_contributor_ids = {}  # dict with ID keys and counts of dc-terms:contributor
        self.dc_creator_ids = {}  # dict with ID keys and counts of dc-terms:creator
        self.uuidlist = []
        self.parents = {}  # dict of uuids for parent entities to keep them in memory

    def prep_default_fields(self):
        """ Prepares initial set of default fields for export tables """
        self.fields.append({'label': 'URI',
                            'rel_ids': {'rdfs:isDefinedBy': '@id'},
                            'field_num': 1})
        self.fields.append({'label': 'Label',
                            'rel_ids': {'rdfs:isDefinedBy': 'label'},
                            'field_num': 2})
        self.fields.append({'label': 'Project',
                            'rel_ids': {'rdfs:isDefinedBy': 'oc-tab:proj-label'},
                            'field_num': 3})
        self.fields.append({'label': 'Project URI',
                            'rel_ids': {'rdfs:isDefinedBy': 'oc-tab:proj-uri'},
                            'field_num': 4})
        self.fields.append({'label': 'Item Category',
                            'rel_ids': {'rdfs:isDefinedBy': 'category'},
                            'field_num': 5})
        self.fields.append({'label': 'Last Updated',
                            'rel_ids': {'rdfs:isDefinedBy': 'dc-terms:modified'},
                            'field_num': 6})
        self.fields.append({'label': 'Authorship',
                            'rel_ids': {'rdfs:isDefinedBy': 'cc:attributionName'},
                            'field_num': 7})
        self.fields.append({'label': 'Latitude (WGS-84)',
                            'rel_ids': {'rdfs:isDefinedBy': 'geo:lat'},
                            'field_num': 8})
        self.fields.append({'label': 'Longitude (WGS-84)',
                            'rel_ids': {'rdfs:isDefinedBy': 'geo:lon'},
                            'field_num': 9})
        self.fields.append({'label': 'Geospatial note',
                            'rel_ids': {'rdfs:isDefinedBy': 'oc-tab:geo-note'},
                            'field_num': 10})
        if self.dates_bce_ce:
            self.fields.append({'label': 'Early Date (BCE/CE)',
                                'rel_ids': {'rdfs:isDefinedBy': 'oc-tab:early-bce-ce'},
                                'field_num': 11})
            self.fields.append({'label': 'Late Date (BCE/CE)',
                                'rel_ids': {'rdfs:isDefinedBy': 'oc-tab:late-bce-ce'},
                                'field_num': 12})
        else:
            self.fields.append({'label': 'Early Date (BP)',
                                'rel_ids': {'rdfs:isDefinedBy': 'oc-tab:early-bp'},
                                'field_num': 11})
            self.fields.append({'label': 'Late Date (BP)',
                                'rel_ids': {'rdfs:isDefinedBy': 'oc-tab:late-bp'},
                                'field_num': 12})
        self.fields.append({'label': 'Context URI',
                            'rel_ids': {'rdfs:isDefinedBy': 'oc-gen:contained-in'},
                            'field_num': 13})
        for field in self.fields:
            self.save_field(field)

    def save_field(self, field):
        """ Saves a record of a field """
        exfield = ExpField()
        exfield.table_id = self.table_id
        exfield.field_num = field['field_num']
        exfield.label = field['label']
        # exfield.rel_ids = json.dumps(field['rel_ids'], ensure_ascii=False)
        exfield.rel_ids = field['rel_ids']
        exfield.save()

    def check_reload_fields_from_db(self):
        """ Reloads fields, incase a process was interrupted """
        if len(self.fields) < 1:
            exfields = ExpField.objects\
                               .filter(table_id=self.table_id)\
                               .order_by('field_num')
            for exfield in exfields:
                field = {}
                field['field_num'] = exfield.field_num
                field['label'] = exfield.label
                # field['rel_ids'] = json.loads(exfield.rel_ids)
                field['rel_ids'] = exfield.rel_ids
                self.fields.append(field)

    def prep_process_uuids_by_projects_class(self, project_uuids, class_uri):
        """ Gets a list of uuids and basic metadata about items for the
            export table. Does so in the simpliest way, filtering only
            by a list of project_uuids and class_uri """
        self.prep_default_fields()
        self.uuidlist = UUIDListSimple(project_uuids, class_uri).uuids
        self.process_uuid_list(self.uuidlist)
        self.get_predicate_uuids()  # now prepare to do item descriptions
        self.get_predicate_link_annotations()  # even if not showing linked data
        self.process_ld_predicates_values()  # only if exporting linked data
        self.save_ld_fields()  # only if exporting linked data
        self.update_table_metadata()  # save a record of the table metadata

    def prep_process_uuid_list(self, uuids, do_linked_data=False):
        """ prepares default fields and exports a list of items """
        self.uuidlist = uuids
        self.prep_default_fields()
        self.process_uuid_list(self.uuidlist)
        self.get_predicate_uuids()  # now prepare to do item descriptions
        self.get_predicate_link_annotations()  # even if not showing linked data
        if do_linked_data:
            self.process_ld_predicates_values()  # only if exporting linked data
            self.save_ld_fields()  # only if exporting linked data
        self.save_source_fields()  # save source data, possibly limited by observations
        self.update_table_metadata()  # save a record of the table metadata

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
                context_metadata = self.get_parents_context_metadata(man.uuid)
                self.save_default_geo(row_num, man, context_metadata['geo'])
                self.save_default_chrono(row_num, man, context_metadata['event'])
                self.save_context(row_num, man, context_metadata['p_list'])
                row_num += 1
            else:
                print(uuid + ' Failed!')

    def get_parents_context_metadata(self, uuid):
        """ get all parents from memory or by DB lookups """
        if len(self.parents) >= 5000:
            self.parents = {}
        par_res = Assertion.objects\
                           .filter(object_uuid=uuid,
                                   predicate_uuid=Assertion.PREDICATES_CONTAINS)[:1]
        if len(par_res) > 0:
            # item has a parent
            parent_uuid = par_res[0].uuid
            if parent_uuid not in self.parents:
                # we don't have a context path parent list for this parent in memory yet
                # so let's go and make it
                p_list = []
                act_contain = Containment()
                raw_parents = act_contain.get_parents_by_child_uuid(parent_uuid)
                if raw_parents is not False:
                    if len(raw_parents) > 0:
                        for tree_node, r_parents in raw_parents.items():
                            p_list = r_parents
                            break
                p_list.insert(0, parent_uuid)  # add the 1st parent to the start of the list
                context_metadata = {'p_list': p_list}
                self.parents[parent_uuid] = context_metadata
            else:
                context_metadata = self.parents[parent_uuid]
        else:
            parent_uuid = False
        # now get geo and chrono metadata
        context_metadata = self.get_geo_chrono_metadata(uuid,
                                                        parent_uuid,
                                                        context_metadata)
        return context_metadata

    def get_geo_chrono_metadata(self, uuid, parent_uuid, context_metadata):
        """ gets and saves geo and chrono metadata """
        act_contain = Containment()
        geo_meta = False
        event_meta = False
        uuid_geo = Geospace.objects.filter(uuid=uuid)[:1]
        if len(uuid_geo) > 0:
            geo_meta = uuid_geo[0]
        else:
            # geo information for this item not found, look to parents
            if parent_uuid is not False \
               and 'p_list' in context_metadata:
                # we have at least 1 parent
                if 'p_geo' not in context_metadata:
                    # no saved geo information in this context path, so look it up
                    p_list = context_metadata['p_list']
                    geo_meta = act_contain.get_geochron_from_subject_list(p_list, 'geo')
                    context_metadata['p_geo'] = geo_meta
                    self.parents[parent_uuid] = context_metadata
                else:
                    # we have saved geo information for this context path so use it
                    geo_meta = context_metadata['p_geo']
        uuid_event = Event.objects.filter(uuid=uuid)[:1]
        if len(uuid_event) > 0:
            event_meta = uuid_event
        else:
            # chrono information for this item not found, look to parents
            if parent_uuid is not False \
               and 'p_list' in context_metadata:
                # we have at least 1 parent
                if 'p_event' not in context_metadata:
                    # no saved chrono information in this context path, so look it up
                    p_list = context_metadata['p_list']
                    event_meta = act_contain.get_geochron_from_subject_list(p_list, 'event')
                    context_metadata['p_event'] = event_meta
                    self.parents[parent_uuid] = context_metadata
                else:
                    # we have saved chrono information for this context path so use it
                    event_meta = context_metadata['p_event']
        context_metadata['geo'] = geo_meta
        context_metadata['event'] = event_meta
        return context_metadata

    def get_predicate_uuids(self):
        """ Gets predicate uuids for a table """
        self.entities = {}  # resets the entites, no need to keep context entitites in memory
        self.check_reload_fields_from_db()  # gets fields from DB, if process was interrupted
        limit_obs = False
        if isinstance(self.obs_limits, list):
            if len(self.obs_limits) > 0:
                limit_obs = True
        uuids = UUIDListExportTable(self.table_id).uuids
        # seems faster than a select distinct with a join.
        temp_predicate_uuids = LastUpdatedOrderedDict()
        max_count = 1  #  useful for sorting
        for uuid in uuids:
            if limit_obs:
                pred_uuids = Assertion.objects\
                                      .values_list('predicate_uuid', flat=True)\
                                      .filter(uuid=uuid,
                                              obs_num__in=self.obs_limits)\
                                      .order_by('obs_num', 'sort')
            else:
                pred_uuids = Assertion.objects\
                                      .values_list('predicate_uuid', flat=True)\
                                      .filter(uuid=uuid)\
                                      .order_by('obs_num', 'sort')
            item_preds = LastUpdatedOrderedDict()
            for pred_uuid in pred_uuids:
                # make sure we can dereference the predicate
                pred_label = self.deref_entity_label(pred_uuid)
                if pred_uuid in self.entities:
                    # only do this if we succeeded in dereferencing the predicate
                    if pred_uuid not in item_preds:
                        item_preds[pred_uuid] = 1
                    else:
                        item_preds[pred_uuid] += 1
            for pred_uuid, count in item_preds.items():
                if pred_uuid not in self.predicate_uuids:
                    pred_label = self.deref_entity_label(pred_uuid)
                    pred_type = self.entities[pred_uuid].data_type
                    pred_sort = self.entities[pred_uuid].sort
                    if pred_sort is False:
                        pred_sort = 10000 # default to putting this at the end
                    # print('Type {} sort to {}'.format(pred_label, pred_type))
                    self.numeric_fields_last = True
                    if self.numeric_fields_last and pred_type in ['xsd:integer', 'xsd:double']:
                        pred_sort += 1000
                        # print('Changing {} sort to {}'.format(pred_label, pred_sort))
                    temp_predicate_uuids[pred_uuid] = {'count': count,
                                                       'sort': pred_sort,
                                                       'label': pred_label,
                                                       'type': pred_type}
                else:
                    if max_count < count:
                        max_count = count
                    if temp_predicate_uuids[pred_uuid]['count'] < count:
                        temp_predicate_uuids[pred_uuid]['count'] = count
        # now sort the temp_predicates
        keys = []
        keyed_pred_uuids = {}
        i = 0
        for pred_uuid, pred_data in temp_predicate_uuids.items():
            make_new_key = True
            # first sort by the sort value, then by count (more is higher ranking)
            key = float(pred_data['sort']) +  (1 - (float(pred_data['count']) / float(max_count)))
            while make_new_key:
                # make sure the key is unique, so add some for the index
                i += (1 / 1000000000)
                key += i
                if key not in keys:
                    make_new_key = False
            keys.append(key)
            keyed_pred_uuids[key] = pred_uuid
        # now sort the key and add to the self.predicate_uuids (a sorted dict)
        for key in sorted(keys):
            pred_uuid = keyed_pred_uuids[key]
            # now the self.predicate_uuids are properly sorted by pred sort order
            # then by count
            self.predicate_uuids[pred_uuid] = temp_predicate_uuids[pred_uuid]
        return self.predicate_uuids

    def get_predicate_link_annotations(self):
        """ Gets the link data annotations for predicates used on a table """
        auth = Authorship()
        for pred_uuid, pred in self.predicate_uuids.items():
            la_s = LinkAnnotation.objects\
                                 .filter(subject=pred_uuid)
            if len(la_s) > 0:
                self.predicate_uuids[pred_uuid]['annotations'] = []
                self.predicate_uuids[pred_uuid]['ld-equiv'] = []
            for la in la_s:
                link_anno = {'pred': la.predicate_uri,
                             'obj': la.object_uri}
                self.predicate_uuids[pred_uuid]['annotations'].append(link_anno)
                if la.predicate_uri in self.EQUIV_PREDICATES:
                    authorship = auth.check_authorship_object(la.object_uri)
                    if authorship is False:  # only keep predicates not related to authorship
                        pred_ld_equiv_uri = la.object_uri  # the object_uri is equivalent to
                                                           # the predicate_uuid
                        self.predicate_uuids[pred_uuid]['ld-equiv'].append(pred_ld_equiv_uri)
                        if pred['type'] == 'id':
                            # the predicate links to URI identified ressoures
                            if la.object_uri not in self.ld_predicates:
                                pred_equiv_label = self.deref_entity_label(pred_ld_equiv_uri)
                                self.ld_predicates[pred_ld_equiv_uri] = {'uuids': [pred_uuid],
                                                                         'obj_uuids': {},
                                                                         'obj_uris': [],
                                                                         'label': pred_equiv_label}
                            else:
                                self.ld_predicates[pred_ld_equiv_uri]['uuids'].append(pred_uuid)
                        else:
                            # the predicate takes literal values, so handle seperately
                            if la.object_uri not in self.ld_literal_preds:
                                pred_equiv_label = self.deref_entity_label(pred_ld_equiv_uri)
                                self.ld_literal_preds[pred_ld_equiv_uri] = {
                                    'uuids': [pred_uuid],
                                    'label': pred_equiv_label
                                }
                            else:
                                self.ld_literal_preds[pred_ld_equiv_uri]['uuids'].append(pred_uuid)
        return self.ld_predicates

    def process_ld_predicates_values(self):
        """ Processes linked uri equivalents for predicates to
            get linked data for objects assocated with these predicates
        """
        if (self.boolean_multiple_ld_fields is not False or self.include_equiv_ld) \
           and len(self.ld_predicates) > 0:
            for pred_ld_equiv_uri, ld_pred in self.ld_predicates.items():
                self.get_ld_predicate_values(pred_ld_equiv_uri)

    def get_ld_predicate_values(self, pred_ld_equiv_uri):
        """ gets a list of object_uuids used with predicates related to a
            ld_field_uri
        """
        object_uuids = Assertion.objects\
                                .values_list('object_uuid', flat=True)\
                                .filter(predicate_uuid__in=self.ld_predicates[pred_ld_equiv_uri]['uuids'])\
                                .distinct()
        for obj_uuid in object_uuids:
            if obj_uuid not in self.ld_object_equivs:
                self.ld_object_equivs[obj_uuid] = []
            if obj_uuid not in self.ld_predicates[pred_ld_equiv_uri]['obj_uuids']:
                obj_equiv_uris = []
                # get link data annotations for the object_uuid
                la_s = LinkAnnotation.objects\
                                     .filter(subject=obj_uuid)
                for la in la_s:
                    if la.predicate_uri in self.EQUIV_PREDICATES:
                        obj_equiv_uri = la.object_uri
                        if obj_equiv_uri not in self.ld_predicates[pred_ld_equiv_uri]['obj_uris']:
                            self.ld_predicates[pred_ld_equiv_uri]['obj_uris'].append(obj_equiv_uri)
                        if obj_equiv_uri not in self.ld_object_equivs[obj_uuid]:
                            self.ld_object_equivs[obj_uuid].append(obj_equiv_uri)
        return self.ld_predicates[pred_ld_equiv_uri]

    def do_boolean_multiple_ld_fields(self, pred_ld_equiv_uri):
        """ Checks to see if a ld_field_uri (equivalent to a predicate_uuid in assertions)
            has multiple values in a given item. If so, then returns true.
            Otherwise, this returns false.
        """
        output = False
        if self.boolean_multiple_ld_fields is not False:
            if pred_ld_equiv_uri in self.ld_predicates:
                for predicate_uuid in self.ld_predicates[pred_ld_equiv_uri]['uuids']:
                    if predicate_uuid in self.predicate_uuids:
                        if self.predicate_uuids[predicate_uuid]['count'] > 1:
                            output = True
        return output

    def save_source_fields(self):
        """ Creates fields for source data, then saves
            records of source data for each item in the export
            table
        """
        if self.include_original_fields and len(self.predicate_uuids) > 0:
            limit_obs = False
            if isinstance(self.obs_limits, list):
                if len(self.obs_limits) > 0:
                    limit_obs = True
            pred_uuid_list = []
            for predicate_uuid, pred_dict in self.predicate_uuids.items():
                field_num = self.get_add_predicate_field_number(predicate_uuid)
                pred_uuid_list.append(predicate_uuid)
            # get the rows for the export table
            rows = UUIDsRowsExportTable(self.table_id).rows
            for row in rows:
                if limit_obs:
                    item_data = Assertion.objects.filter(uuid=row['uuid'],
                                                         predicate_uuid__in=pred_uuid_list,
                                                         obs_num__in=self.obs_limits)
                else:
                    item_data = Assertion.objects.filter(uuid=row['uuid'],
                                                         predicate_uuid__in=pred_uuid_list)
                if len(item_data) > 0:
                    self.add_source_cells(row['uuid'],
                                          row['row_num'],
                                          item_data)

    def add_source_cells(self, uuid, row_num, item_data):
        """ Adds source data records for an assertion """
        predicate_values = LastUpdatedOrderedDict()
        project_uuid = item_data[0].project_uuid
        for assertion in item_data:
            predicate_uuid = assertion.predicate_uuid
            object_uuid = assertion.object_uuid
            if assertion.object_type == 'xsd:string':
                try:
                    oc_str = OCstring.objects.get(uuid=object_uuid)
                    obj_val = oc_str.content
                except OCstring.DoesNotExist:
                    obj_val = ''
            elif assertion.object_type in ['xsd:integer', 'xsd:double']:
                # numeric value
                obj_val = str(assertion.data_num)
            elif assertion.object_type == 'xsd:date':
                obj_val = str(assertion.data_date)
            else:
                obj_val = str(self.deref_entity_label(object_uuid))
            if predicate_uuid not in predicate_values:
                # make a list, since some predicates are multi-valued
                predicate_values[predicate_uuid] = []
            predicate_values[predicate_uuid].append(obj_val)
        for predicate_uuid, val_list in predicate_values.items():
            field_num = self.get_add_predicate_field_number(predicate_uuid)
            cell = ExpCell()
            cell.table_id = self.table_id
            cell.uuid = uuid
            cell.project_uuid = project_uuid
            cell.row_num = row_num
            cell.field_num = field_num
            cell.record = self.multi_source_value_delim.join(val_list)  # semi-colon delim for multivalued predicates
            cell.save()
            cell = None

    def get_add_predicate_field_number(self, predicate_uuid):
        """ Gets the field_num for a source predicate_uuid field,
            givem the predicate_uuid
            Creates a new field for the predicate as needed
        """
        if predicate_uuid in self.predicate_fields:
            field_num = self.predicate_fields[predicate_uuid]
        else:
            field_num = len(self.fields) + 1
            label = self.deref_entity_label(predicate_uuid) + self.source_field_label_suffix
            if ':' in predicate_uuid:
                rel_ids = {'rdfs:isDefinedBy': predicate_uuid}
            else:
                rel_ids = {'rdfs:isDefinedBy': ('oc-pred:' + predicate_uuid)}
            field = {'label': label,
                     'rel_ids': rel_ids,
                     'field_num': field_num}
            self.fields.append(field)
            self.save_field(field)
            self.predicate_fields[predicate_uuid] = field_num
        return field_num

    def save_ld_fields(self):
        """ Creates fields for linked data, then saves
            records of linked data for each item in the export
            table
        """
        if self.include_equiv_ld and len(self.ld_predicates) > 0:
            self.save_ld_fields_w_object_uris()
        # now check for linked data equivalents that have literal values for objects
        if self.include_equiv_ld_literals and len(self.ld_literal_preds) > 0:
            self.save_ld_fields_w_object_literals()

    def save_ld_fields_w_object_uris(self):
        """ Saves linked data fields that have
            URI identified objects (as opposed to literals)
        """
        for pred_ld_equiv_uri, ld_pred in self.ld_predicates.items():
            if self.do_boolean_multiple_ld_fields(pred_ld_equiv_uri):
                le_sort = LinkEntitySorter()
                #  sort the URIs for the objects, so the fields come in a
                #  nice, reasonable order.
                sort_obj_uris = le_sort.sort_ld_entity_list(ld_pred['obj_uris'])
                for ld_obj_uri in sort_obj_uris:
                    # make a field for each linked data pred and object
                    field_num = self.get_add_ld_field_number('[Has]',
                                                             pred_ld_equiv_uri,
                                                             ld_obj_uri)
            else:
                if pred_ld_equiv_uri not in self.LD_MULTI_FIELD:
                    if self.include_ld_obj_uris:
                        field_num = self.get_add_ld_field_number('[URI]',
                                                                 pred_ld_equiv_uri)
                    field_num = self.get_add_ld_field_number('[Label]',
                                                             pred_ld_equiv_uri)
                    if self.include_ld_source_values:
                        field_num = self.get_add_ld_field_number('[Source]',
                                                                 pred_ld_equiv_uri)
                else:
                    # the predicate needs to be exported in multiple fields
                    for multi_field in self.LD_MULTI_FIELD[pred_ld_equiv_uri]:
                        prefix = multi_field['prefix']
                        if self.include_ld_obj_uris:
                            field_num = self.get_add_ld_field_number('[' + prefix + 'URI]',
                                                                     pred_ld_equiv_uri)
                        field_num = self.get_add_ld_field_number('[' + prefix + 'Label]',
                                                                 pred_ld_equiv_uri)
                        if self.include_ld_source_values:
                            field_num = self.get_add_ld_field_number('[' + prefix + 'Source]',
                                                                     pred_ld_equiv_uri)
        # get the rows for the export table
        rows = UUIDsRowsExportTable(self.table_id).rows
        for row in rows:
            for pred_ld_equiv_uri, ld_pred in self.ld_predicates.items():
                item_data = Assertion.objects.filter(uuid=row['uuid'],
                                                     predicate_uuid__in=ld_pred['uuids'])
                if len(item_data) > 0:
                    if pred_ld_equiv_uri not in self.LD_MULTI_FIELD \
                       or self.do_boolean_multiple_ld_fields(pred_ld_equiv_uri):
                        # NOT splitting the LD predicate into mutiple table output fields
                        # based on Object URIs
                        self.add_ld_cells(row['uuid'],
                                          row['row_num'],
                                          item_data,
                                          pred_ld_equiv_uri)
                    else:
                        # LD predicate output into multiple fields, depending
                        # on the LD equivalent object URIs
                        self.add_ld_multi_field_cells(row['uuid'],
                                                      row['row_num'],
                                                      item_data,
                                                      pred_ld_equiv_uri)

    def save_ld_fields_w_object_literals(self):
        """ saves ld fields where the objects of assertions are literals """
        # saves linked data fields that take literal values
        # first, order the fields in alphabetic order of label
        keys = []
        keyed_ld_lit_preds = {}
        for pred_ld_equiv_uri, ld_pred in self.ld_literal_preds.items():
            key = ld_pred['label'] + ' ' + pred_ld_equiv_uri
            keys.append(key)
            keyed_ld_lit_preds[key] = {'uri': pred_ld_equiv_uri,
                                       'ld_pred': ld_pred}
        reordered_ld_lt_preds = LastUpdatedOrderedDict()
        for key in sorted(keys):
            act_pred = keyed_ld_lit_preds[key]
            pred_ld_equiv_uri = act_pred['uri']
            reordered_ld_lt_preds[pred_ld_equiv_uri] = act_pred['ld_pred']
        self.ld_literal_preds = reordered_ld_lt_preds
        # now that the literal preds are sorted by label, lets make field
        # values for them
        for pred_ld_equiv_uri, ld_pred in self.ld_literal_preds.items():
            field_num = self.get_add_ld_field_number('[Value]',
                                                     pred_ld_equiv_uri)
            print('Prepping field: ' + str(field_num) + ' for equiv. LD (literal objects)')
        # get the rows for the export table
        rows = UUIDsRowsExportTable(self.table_id).rows
        for row in rows:
            for pred_ld_equiv_uri, ld_pred in self.ld_literal_preds.items():
                item_data = Assertion.objects\
                                     .filter(uuid=row['uuid'],
                                             predicate_uuid__in=ld_pred['uuids'])
                if len(item_data) > 0:
                    field_num = self.get_add_ld_field_number('[Value]',
                                                             pred_ld_equiv_uri)
                    project_uuid = item_data[0].project_uuid
                    val_list = []
                    for assertion in item_data:
                        obj_val = ''
                        if assertion.object_type == 'xsd:string':
                            try:
                                oc_str = OCstring.objects.get(uuid=assertion.object_uuid)
                                obj_val = oc_str.content
                            except OCstring.DoesNotExist:
                                obj_val = ''
                        elif assertion.object_type in ['xsd:integer', 'xsd:double']:
                            # numeric value
                            obj_val = str(assertion.data_num)
                        elif assertion.object_type == 'xsd:date':
                            obj_val = str(assertion.data_date)
                        else:
                            obj_val = ''
                        if len(obj_val) > 0:
                            val_list.append(obj_val)
                    if len(val_list) > 0:
                        cell = ExpCell()
                        cell.table_id = self.table_id
                        cell.uuid = row['uuid']
                        cell.project_uuid = project_uuid
                        cell.row_num = row['row_num']
                        cell.field_num = field_num
                        # semi-colon delim for multivalued predicates
                        cell.record = self.multi_source_value_delim.join(val_list)
                        cell.save()
                        cell = None

    def add_ld_cells(self, uuid, row_num, item_data, pred_ld_equiv_uri):
        """ Adds linked data records for an assertion """
        if self.do_boolean_multiple_ld_fields(pred_ld_equiv_uri):
            multi_ld_fields = True
        else:
            multi_ld_fields = False
        obj_values = LastUpdatedOrderedDict()
        obj_values['[URI]'] = []
        obj_values['[Label]'] = []
        obj_values['[Source]'] = []
        project_uuid = item_data[0].project_uuid
        for assertion in item_data:
            object_uuid = assertion.object_uuid
            if assertion.object_type == 'xsd:string':
                try:
                    oc_str = OCstring.objects.get(uuid=object_uuid)
                    obj_label = oc_str.content
                except OCstring.DoesNotExist:
                    obj_label = ''
            else:
                obj_label = self.deref_entity_label(object_uuid)
                obj_label = str(obj_label)
            if obj_label not in obj_values['[Source]']:
                obj_values['[Source]'].append(obj_label)
            obj_ld_found = False
            if object_uuid in self.ld_object_equivs:
                for obj_ld_equiv_uri in self.ld_object_equivs[object_uuid]:
                    obj_ld_found = True
                    if multi_ld_fields:
                        cell_value = self.boolean_multiple_ld_fields
                        field_num = self.get_add_ld_field_number('[Has]',
                                                                 pred_ld_equiv_uri,
                                                                 obj_ld_equiv_uri)
                        cell = ExpCell()
                        cell.table_id = self.table_id
                        cell.uuid = uuid
                        cell.project_uuid = project_uuid
                        cell.row_num = row_num
                        cell.field_num = field_num
                        cell.record = cell_value
                        cell.save()
                        cell = None
                    else:
                        # predicate not broken into seperate fields for different values
                        obj_equiv_label = self.deref_entity_label(obj_ld_equiv_uri)
                        if obj_equiv_label is False:
                            obj_equiv_label = obj_ld_equiv_uri
                        if obj_equiv_label not in obj_values['[Label]']:
                            obj_values['[Label]'].append(obj_equiv_label)
                        if obj_ld_equiv_uri not in obj_values['[URI]']:
                            obj_values['[URI]'].append(obj_ld_equiv_uri)
            if obj_ld_found is False:
                print('No linked data for object:' + object_uuid)
        if multi_ld_fields is False:
            # predicate not broken into seperate fields for different values
            if self.include_ld_obj_uris is False:
                # we're not including the URIs for the equivalent objects
                obj_values.pop('[URI]', None)
            if self.include_ld_source_values is False:
                # we're not including the labels source objects that have LD equivalents
                obj_values.pop('[Source]', None)
            for field_type, value_list in obj_values.items():
                self.save_ld_cell_value_from_value_list(uuid,
                                                        row_num,
                                                        project_uuid,
                                                        field_type,
                                                        pred_ld_equiv_uri,
                                                        value_list)

    def save_ld_cell_value_from_value_list(self,
                                           uuid,
                                           row_num,
                                           project_uuid,
                                           field_type,
                                           pred_ld_equiv_uri,
                                           value_list):
        """ saves a ld cell value for a value_list of a given field type """
        if len(value_list) > 0:
            try:
                cell_value = self.multi_source_value_delim.join(value_list)
            except:
                # some messiness in the data, won't join into a string
                cell_value = False
                for val in value_list:
                    val = str(val)
                    if cell_value is False:
                        cell_value = val
                    else:
                        cell_value += self.multi_source_value_delim + val
            field_num = self.get_add_ld_field_number(field_type,
                                                     pred_ld_equiv_uri)
            cell = ExpCell()
            cell.table_id = self.table_id
            cell.uuid = uuid
            cell.project_uuid = project_uuid
            cell.row_num = row_num
            cell.field_num = field_num
            cell.record = cell_value
            cell.save()
            cell = None

    def add_ld_multi_field_cells(self, uuid, row_num, item_data, pred_ld_equiv_uri):
        """ add cells for linked data predicates that need to be expressed in
            multiple fields
        """
        if pred_ld_equiv_uri in self.LD_MULTI_FIELD:
            # different object_uris go into different fields,
            # the object_uri_prefixes maps an object_uri to the right prefix
            object_uri_prefixes = {}
            field_type_values = LastUpdatedOrderedDict()
            for multi_field in self.LD_MULTI_FIELD[pred_ld_equiv_uri]:
                prefix = multi_field['prefix']
                for object_uri in multi_field['object_uris']:
                    object_uri_prefixes[object_uri] = prefix
                if self.include_ld_obj_uris:
                    field_type = '[' + prefix + 'URI]'
                    field_type_values[field_type] = []
                field_type = '[' + prefix + 'Label]'
                field_type_values[field_type] = []
                if self.include_ld_source_values:
                    field_type = '[' + prefix + 'Source]'
                    field_type_values[field_type] = []
            # now start making the cells
            project_uuid = item_data[0].project_uuid
            for assertion in item_data:
                obj_label = ''
                object_uuid = assertion.object_uuid
                if assertion.object_type == 'xsd:string':
                    try:
                        oc_str = OCstring.objects.get(uuid=object_uuid)
                        obj_label = oc_str.content
                    except OCstring.DoesNotExist:
                        obj_label = ''
                else:
                    obj_label = self.deref_entity_label(object_uuid)
                    obj_label = str(obj_label)
                if object_uuid in self.ld_object_equivs:
                    # the object_uuid has an equivalent linked data URI
                    for obj_ld_equiv_uri in self.ld_object_equivs[object_uuid]:
                        # get the label for the equivalent object uri
                        obj_equiv_label = self.deref_entity_label(obj_ld_equiv_uri)
                        if obj_equiv_label is False:
                            obj_equiv_label = obj_ld_equiv_uri
                        if obj_ld_equiv_uri in object_uri_prefixes:
                            # we have the multi-field prefix!
                            prefix = object_uri_prefixes[obj_ld_equiv_uri]
                            field_type = '[' + prefix + 'URI]'
                            if field_type in field_type_values:
                                # we're outputting uris for LD equivalent objects, add to
                                # output list
                                field_type_values[field_type].append(obj_ld_equiv_uri)
                            field_type = '[' + prefix + 'Label]'
                            if field_type in field_type_values:
                                # we're outputting labels for LD equivalent objects, add to
                                # add object equiv label to output list
                                field_type_values[field_type].append(obj_equiv_label)
                            field_type = '[' + prefix + 'Source]'
                            if field_type in field_type_values:
                                # we're outputting labels of source objects that have LD equivalents
                                # add source object label output list
                                field_type_values[field_type].append(obj_label)
            # now make the cell values
            for field_type, value_list in field_type_values.items():
                self.save_ld_cell_value_from_value_list(uuid,
                                                        row_num,
                                                        project_uuid,
                                                        field_type,
                                                        pred_ld_equiv_uri,
                                                        value_list)

    def make_ld_rel_id(self, field_type, equiv_uri):
        """ makes a rel_id object, to add to a list
        """
        field_type_l = field_type.lower()
        field_type_mappings = {'uri': 'oc-tab:equiv-uri',
                               'value': 'oc-tab:equiv-uri',
                               'label': 'oc-tab:equiv-label',
                               'source': 'oc-tab:rel-source',
                               'has': 'oc-tab:rel-ld'}
        for type_key, mapped in field_type_mappings.items():
            if type_key in field_type_l:
                field_type = mapped
        output = {}
        output[field_type] = equiv_uri
        return output

    def get_add_ld_field_number(self,
                                field_type,
                                pred_ld_equiv_uri,
                                obj_ld_equiv_uri=False):
        """ Gets the field_num for a linked data field, given the uri
            for the linked data field, and optionally the object
            Creates a new field for the linked data as needed
        """
        if obj_ld_equiv_uri is not False:
            field_key = pred_ld_equiv_uri + '::' + obj_ld_equiv_uri
        else:
            field_key = pred_ld_equiv_uri
        if field_type is not False:
            if len(field_type) > 0:
                field_key += '::' + field_type
        else:
            field_key += '::[Type unknown]'
        if field_key in self.ld_fields:
            field_num = self.ld_fields[field_key]
        else:
            field_num = len(self.fields) + 1
            label = self.deref_entity_label(pred_ld_equiv_uri)
            if label is False:
                label = pred_ld_equiv_uri
            rel_ids = self.make_ld_rel_id(field_type, pred_ld_equiv_uri)
            if obj_ld_equiv_uri is not False:
                rel_ids['oc-tab:obj-equiv'] = obj_ld_equiv_uri
                obj_label = self.deref_entity_label(obj_ld_equiv_uri)
                if obj_label is False:
                    obj_label = obj_ld_equiv_uri
                label = label + ' :: ' + str(obj_label)
            if field_type is not False:
                if len(field_type) > 0:
                    label += ' ' + field_type
            field = {'label': label,
                     'rel_ids': rel_ids,
                     'field_num': field_num}
            self.fields.append(field)
            self.save_field(field)
            self.ld_fields[field_key] = field_num
        return field_num

    def save_context(self, row_num, man, parent_list):
        """ Save context information, will also add new context fields
            as needed
        """
        use_parents = False
        context_uri = ''
        if isinstance(parent_list, list):
            if len(parent_list) > 0:
                context_uri = URImanagement.make_oc_uri(parent_list[0], 'subjects')
                use_parents = parent_list[::-1]
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
                     'rel_ids': {'rdfs:isDefinedBy': 'oc-tab:context-label',
                                 'oc-tab:context-index': pindex},
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
            # a hack since for some reason a single geospace object occationally gets returned
            try:
                geo_len = len(geo_meta)
            except:
                geo_meta = [geo_meta]
            for geo in geo_meta:
                if geo.meta_type == 'oc-gen:discovey-location':
                    latitude = geo.latitude
                    longitude = geo.longitude
                    if geo.specificity < 0:
                        note = 'Location approximated '
                        note += 'as a security precaution (Zoom: ' + str(abs(geo.specificity)) + ')'
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
            # save counts of different dc-terms:creator for use as table metadata
            for auth_id in auth.creators:
                if auth_id not in self.dc_creator_ids:
                    self.dc_creator_ids[auth_id] = 0
                self.dc_creator_ids[auth_id] += 1
            # save counts of different dc-terms:contributor for use as table metadata
            for auth_id in auth.contributors:
                if auth_id not in self.dc_contributor_ids:
                    self.dc_contributor_ids[auth_id] = 0
                self.dc_contributor_ids[auth_id] += 1
            all_author_ids = auth.creators + auth.contributors
            all_authors = []
            for auth_id in all_author_ids:
                author = self.deref_entity_label(auth_id)
                if isinstance(author, str):
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

    def update_table_metadata(self):
        """ saves the final table author metadata """
        try:
            exp_tab = ExpTable.objects.get(table_id=self.table_id)
        except ExpTable.DoesNotExist:
            exp_tab = ExpTable()
            exp_tab.table_id = self.table_id
            exp_tab.label = '[Not yet named]'
        tcells_ok = ExpCell.objects.filter(table_id=self.table_id)[:1]
        if len(tcells_ok):
            sum_cell = ExpCell.objects\
                              .filter(table_id=self.table_id)\
                              .aggregate(Max('row_num'))
            exp_tab.row_count = sum_cell['row_num__max']
        else:
            exp_tab.row_count = 0
        tfields_ok = ExpField.objects.filter(table_id=self.table_id)[:1]
        if len(tfields_ok):
            sum_field = ExpField.objects\
                                .filter(table_id=self.table_id)\
                                .aggregate(Max('field_num'))
            exp_tab.field_count = sum_field['field_num__max']
        else:
            exp_tab.field_count = 0
        authors = LastUpdatedOrderedDict()
        if len(self.dc_contributor_ids) > 0:
            sauthors = sorted(self.dc_contributor_ids.items(),
                              key=lambda x: (-x[1], x[0]))
            authors['dc-terms:contributor'] = self.add_author_list(sauthors,
                                                                   'contributor')
        if len(self.dc_creator_ids) > 0:
            sauthors = sorted(self.dc_creator_ids.items(),
                              key=lambda x: (-x[1], x[0]))
            authors['dc-terms:creator'] = self.add_author_list(sauthors,
                                                               'creator')
        exp_tab.meta_json = authors
        exp_tab.save()

    def add_author_list(self, sauthors, dc_type):
        """ makes an author list from a sorted tuple of
            author identifiers
        """
        i = 0
        author_list = []
        for uri_key, count in sauthors:
            i += 1
            auth = LastUpdatedOrderedDict()
            auth['id'] = '#' + dc_type + '-' + str(i)
            if 'http://' in uri_key or 'https://' in uri_key:
                auth['rdfs:isDefinedBy'] = uri_key
            else:
                auth['rdfs:isDefinedBy'] = URImanagement.make_oc_uri(uri_key,
                                                                     'persons')
            auth['label'] = self.deref_entity_label(uri_key)
            auth['count'] = count
            author_list.append(auth)
        return author_list

    def recursive_context_build(self,
                                parent_level=0):
        """ recusrively builds a list of parent contexts """
        if parent_level == 0:
            sql = 'INSERT INTO exp_records(table_id, uuid, project_uuid,\
                   row_num, field_num, record_id, record)\
                   SELECT exp.table_id, exp.uuid, exp.project_uuid,\
                   exp.row_num, -1, pman.label, ass.uuid \
                   FROM exp_records AS exp \
                   LEFT OUTER JOIN oc_assertions AS ass\
                   ON (ass.object_uuid = exp.uuid \
                       AND ass.predicate_uuid = \'' + Assertion.PREDICATES_CONTAINS + '\') \
                   LEFT OUTER JOIN oc_manifest AS pman ON (ass.uuid = pman.uuid) \
                   WHERE ass.predicate_uuid = \'' + Assertion.PREDICATES_CONTAINS + '\' \
                   AND exp.table_id = \'' + self.table_id + '\' \
                   AND exp.field_num = 1; '
        else:
            sql = 'INSERT INTO exp_records(table_id, uuid, project_uuid,\
                   row_num, field_num, record_id, record)\
                   SELECT exp.table_id, exp.uuid, exp.project_uuid,\
                   exp.row_num, -1, pman.label, ass.uuid \
                   FROM exp_records AS exp \
                   LEFT OUTER JOIN oc_assertions AS ass\
                   ON (ass.object_uuid = exp.uuid \
                       AND ass.predicate_uuid = \'' + Assertion.PREDICATES_CONTAINS + '\') \
                   LEFT OUTER JOIN oc_manifest AS pman ON (ass.uuid = pman.uuid) \
                   WHERE ass.predicate_uuid = \'' + Assertion.PREDICATES_CONTAINS + '\' \
                   AND exp.table_id = \'' + self.table_id + '\' \
                   AND exp.field_num = ' + parent_level + ' ;'
        parent_res = cursor.execute(sql)
        print(str(parent_res))
        parent_level = parent_level - 1

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
                print('Missing id: ' + entity_id)
        return output
