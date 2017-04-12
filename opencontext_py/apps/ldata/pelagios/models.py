import json
import requests
from time import sleep
from django.conf import settings
from django.db import connection
from django.db import models
from django.db.models import Q
from django.utils.http import urlquote, quote_plus, urlquote_plus
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.libs.generalapi import GeneralAPI
from opencontext_py.libs.isoyears import ISOyears
from opencontext_py.apps.entities.uri.models import URImanagement
from opencontext_py.apps.entities.entity.models import Entity
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.ocitems.assertions.models import Assertion
from opencontext_py.apps.ocitems.assertions.containment import Containment
from opencontext_py.apps.ocitems.subjects.models import Subject
from opencontext_py.apps.ocitems.mediafiles.models import Mediafile
from opencontext_py.apps.ldata.linkentities.models import LinkEntity
from opencontext_py.apps.ldata.linkannotations.models import LinkAnnotation
from opencontext_py.apps.ldata.linkannotations.equivalence import LinkEquivalence
from opencontext_py.apps.searcher.solrsearcher.complete import CompleteQuery


class PelagiosData():
    """ Calls the database to collect data needed
        to make Pelagios compliant open annotations
    """

    # vocabularies that have place entities
    GAZETTEER_VOCABS = [
        'http://www.geonames.org',
        'http://www.geonames.org/',
        'http://pleiades.stoa.org/',
        'http://pleiades.stoa.org',
        'http://n2t.net/ark:/99152/p0'
    ]
    
    # stings that we want to EXCLUDE from URIs, so as to exclude
    # non place entities
    EXCLUDE_URI_PARTS = [
        '/time-periods/'
    ]
    
    # open context item times that we want to use as targets of
    # open annotations for pelagios
    OC_OA_TARGET_TYPES = [
        'subjects',
        'documents',
        'media',
        'projects'
    ]
    
    # for making dcterms:description of individual records
    ITEM_TYPE_DESCRIPTIONS = {
        'subjects': 'data record',
        'media': 'media item',
        'documents': 'document (field notes, diaries, narratives)',
        'projects': 'project or collection publication'
    }

    # for making dcterms:description of sets of records
    ITEM_TYPE_DESCRIPTIONS_PLR = {
        'subjects': 'Data Records',
        'media': 'Media Items',
        'documents': 'Documents (Field notes, Diaries, Narratives)',
        'projects': 'Project or Collection Publications'
    }
    def __init__(self):
        self.oa_items = {}  # dict with uuid key of open annotation item objects
        self.db_chunk_size = 100
        self.test_limit = None
        self.project_uuids = []
        self.mem_cache_entities = {}
    
    def get_prep_ocitems_rel_gazetteer(self):
        """ gets gazetteer related items, then
            populates these with manifest objects and context
            paths (for subjects)
        """
        self.get_ocitems_rel_gazetteer()
        self.get_oaitems_db_objects()
        valid_cnt = 0
        invalid_cnt = 0
        i = -1
        do_loop = True
        for uuid, oa_item in self.oa_items.items():
            i += 1
            if isinstance(self.test_limit, int):
                if i >= self.test_limit:
                    do_loop = False
            if do_loop:
                # print('Check: ' + oa_item.uuid)
                oa_item.validate()
                if oa_item.is_valid:
                    oa_item.get_geo_event_metadata()
                    oa_item.get_associated_categories()
                    oa_item.mem_cache_entities = self.mem_cache_entities
                    oa_item.prep_item_dc_metadata()
                    oa_item.prep_assocated_dc_metadata()
                    self.mem_cache_entities = oa_item.mem_cache_entities
                    # print(oa_item.manifest.label)
                    # print('Number associated: ' + str(len(oa_item.associated)))
                    valid_cnt += 1
                else:
                    invalid_cnt += 1
            else:
                break
        print('Valid: ' + str(valid_cnt))
        print('Invalid: ' + str(invalid_cnt))
    
    def get_oaitems_db_objects(self):
        """ runs queries to get database objects for OA items """
        man_uuids = []
        subjects_uuids = []
        temp_oa_items = self.oa_items
        for uuid, oa_item in temp_oa_items.items():
            if len(man_uuids) >= self.db_chunk_size:
                # we have enough man_uuids to run a query, update the
                # self.oa_items dict
                subjects_uuids += self.get_add_manifest_objs(man_uuids)
                man_uuids = []
            else:
                man_uuids.append(uuid)
            if len(subjects_uuids) >= self.db_chunk_size:
                # we have enough uuids of subject items to run a query,
                # update the self.oa_items dict
                self.get_add_contexts(subjects_uuids)
                subjects_uuids = []
        if len(man_uuids) > 0:
            # update the self.oa_items dict for remaining man_uuids
            subjects_uuids += self.get_add_manifest_objs(man_uuids)
        if len(subjects_uuids) > 0:
            # update the remaining oa_items for remaining man_uuids
            self.get_add_contexts(subjects_uuids)
    
    def get_add_manifest_objs(self, man_uuids):
        """ queries for a list of manifest objects,
            updates the self.oa_items dict so oa_items
            have manifest objects,
            returns list of subjects uuids
        """
        subjects_uuids = []
        if len(self.project_uuids) < 1:
            # not filtering by projects
            man_objs = Manifest.objects\
                               .filter(uuid__in=man_uuids)
        else:
            # filter by project
            proj_list = self.project_uuids
            proj_list.append('0')  # add a project 0 (Open Context to the proj list)
            man_objs = Manifest.objects\
                               .filter(uuid__in=man_uuids,
                                       project_uuid__in=proj_list)
        for man_obj in man_objs:
            act_uuid = man_obj.uuid
            self.oa_items[act_uuid].manifest = man_obj
            if man_obj.item_type == 'subjects':
                subjects_uuids.append(act_uuid)
        return subjects_uuids
    
    def get_add_contexts(self, subjects_uuids):
        """ queries for a list of subject objects,
            to update the self.oc_items dict
            and add context infromation
        """
        sub_objs = Subject.objects\
                          .filter(uuid__in=subjects_uuids)
        for sub_obj in sub_objs:
            act_uuid = sub_obj.uuid
            self.oa_items[act_uuid].context = sub_obj.context
    
    def get_ocitems_rel_gazetteer(self):
        """ gets open context items that
            link to gazetteer entities
        """
        oa_items = {}
        rel_oc_types = []
        act_gaz_list = self.get_used_gazetteer_entities()
        # get list of gazetteer vocabularies actually in use
        if len(self.project_uuids) < 1:
            used_gaz_annos = LinkAnnotation.objects\
                                           .filter(object_uri__in=act_gaz_list)
        else:
            # Some gazetter references go to items belonging to Open Context, which is project 0
            # the following does a complicated SQL query to get gazetter references
            # to items that are in our self.project_uuids list
            # OR are in project '0' AND contain items in our self.project_uuids list
            oa_item = OaItem()
            ok_rows = oa_item.get_project_gaz_rels(self.project_uuids,
                                                   act_gaz_list)
            hash_ids = []
            for ok_row in ok_rows:
                hash_ids.append(ok_row['hash_id'])
            used_gaz_annos = LinkAnnotation.objects\
                                           .filter(hash_id__in=hash_ids)
        for gaz_anno in used_gaz_annos:
            if gaz_anno.subject_type in self.OC_OA_TARGET_TYPES:
                oa_items = self.update_oa_items(gaz_anno.subject,
                                                gaz_anno.object_uri,
                                                oa_items)
            elif gaz_anno.subject_type == 'types':
                rel_asserts = Assertion.objects\
                                       .filter(subject_type__in=self.OC_OA_TARGET_TYPES,
                                               object_uuid=gaz_anno.subject)
                for rel_assert in rel_asserts:
                    oa_items = self.update_oa_items(rel_assert.uuid,
                                                    gaz_anno.object_uri,
                                                    oa_items)
        self.oa_items = oa_items
        return self.oa_items

    def update_oa_items(self, uuid, gazetteer_uri, oa_items):
        """ updates the target_uris object with more data """
        if uuid not in oa_items:
            # created a new open annoation item
            oa_item = OaItem()
            oa_item.uuid = uuid
        else:
            oa_item = oa_items[uuid]
        if gazetteer_uri not in oa_item.gazetteer_uris:
            # update gazetteer reference
            oa_item.gazetteer_uris.append(gazetteer_uri)
        oa_items[uuid] = oa_item 
        return oa_items

    def get_used_gazetteer_entities(self):
        """ gets entities in gazetteer vocabularies
            that are actually being used
        """
        act_gaz_list = []
        # get list of all entities in gazetteer vocabularies
        # exclude pleiades time periods
        all_gaz_ents = LinkEntity.objects\
                                 .filter(vocab_uri__in=self.GAZETTEER_VOCABS)
        for gaz_ent in all_gaz_ents:
            add_to_list = True
            for ex_uri_part in self.EXCLUDE_URI_PARTS:
                if ex_uri_part in gaz_ent.uri:
                    # part of the uri has text we want to exclude
                    add_to_list = False
            if add_to_list:
                act_gaz_list.append(gaz_ent.uri)
        return act_gaz_list

    
class OaItem():
    """ object for an Open Annotation item """
    
    def __init__(self):
        self.is_valid = None
        self.title = None
        self.description = None
        self.depiction = None
        self.temporal = None
        self.class_label = None
        self.class_slug = None
        self.uri = None
        self.project_uri = None
        self.uuid = None
        self.manifest = None
        self.context = None
        self.contents_cnt = 0
        self.geo_meta = None
        self.event_meta = None
        self.gazetteer_uris = []
        self.mem_cache_entities = {}
        self.associated = []
        self.raw_associated = {}
    
    def get_manifest_obj_context(self, uuid):
        """ gets manifest object and context for an item """
        if self.manifest is None:
            try:
                self.manifest = Manifest.objects.get(uuid=uuid)
            except Manifest.DoesNotExist:
                self.manifest = False
                self.is_valid = False
            if self.manifest is not False:
                # check to see if we need a context (path)
                if self.manifest.item_type == 'subjects':
                    try:
                        subj_obj = Subject.objects.get(uuid=uuid)
                    except Subject.DoesNotExist:
                        subj_obj = False
                        self.is_valid = False
                    if subj_obj is not False:
                       self.context = subj_obj.context 
            return False
    
    def validate(self):
        """ validates the item """
        if self.manifest is None or self.manifest is False:
            self.is_valid = False
            # print('Missing manifest for ' + self.uuid)
        else:
            if self.manifest.item_type == 'subjects':
                if not isinstance(self.context, str):
                    self.is_valid = False
                    # print('Missing context for ' + self.uuid)
        if self.is_valid is None:
            # since it's not false, and is none
            # it is valid
            self.is_valid = True
        return self.is_valid
    
    def prep_item_dc_metadata(self):
        """ prepared dublin core metadata for an item,
            this needs to happen before we prep dc metadata
            for associated items and sets of items
        """
        if self.is_valid:
            # make some uris
            self.uri = URImanagement.make_oc_uri(self.manifest.uuid,
                                                 self.manifest.item_type)
            self.project_uri = URImanagement.make_oc_uri(self.manifest.project_uuid,
                                                         'projects')
            # get data about entities describing the item
            category_ent = self.get_entity(self.manifest.class_uri)
            if category_ent is not False:
                self.class_label = category_ent.label
                self.class_slug = category_ent.slug
            project_ent = self.get_entity(self.manifest.project_uuid)
            self.title = self.make_dcterms_title(self.manifest.label,
                                                 self.context)
            item_type = self.manifest.item_type
            if item_type == 'subjects':
                if category_ent is not False:
                    self.description = category_ent.label
                    if item_type in PelagiosData.ITEM_TYPE_DESCRIPTIONS:
                        self.description += ' ' + PelagiosData.ITEM_TYPE_DESCRIPTIONS[item_type].lower()
                context = self.remove_label_from_context(self.manifest.label,
                                                         self.context)
                if isinstance(context, str):
                    self.description += ' from the context: ' + context
                if project_ent is not False:
                    self.description += '; part of the "' + project_ent.label
                    self.description += '" data publication.'
            else:
                self.description = 'A ' + PelagiosData.ITEM_TYPE_DESCRIPTIONS[item_type]
                if project_ent is not False and item_type != 'projects':
                    self.description += '; part of the "' + project_ent.label
                    self.description += '" data publication.'
    
    def prep_assocated_dc_metadata(self):
        """ prepares dc_metadata for items associated to the
            main item that actually has 1 or more gazetteer links
        """
        if self.is_valid and len(self.raw_associated) > 0:
            project_ent = self.get_entity(self.manifest.project_uuid)
            ass_items = []  # list of associated items
            ass_sets = [] # list of associated sets
            for key, ass in self.raw_associated.items():
                if isinstance(ass['uuid'], str) and \
                   isinstance(ass['label'], str):
                    # we have a uuid identified item, meaning a specific
                    # related resource
                    ass['uri'] = URImanagement.make_oc_uri(ass['uuid'],
                                                           ass['item_type'])
                    ass['title'] = self.make_dcterms_title(ass['label'],
                                                           self.context)
                    # now prepare description information
                    description = ''
                    cat_ent = self.get_entity(ass['media_class_uri'])
                    if cat_ent is not False:
                        ass['class_label'] = cat_ent.label
                        ass['class_slug'] = cat_ent.slug
                        description += cat_ent.label
                    if ass['item_type'] in PelagiosData.ITEM_TYPE_DESCRIPTIONS:
                        if description == '':
                            description = 'A'
                        description += ' ' + PelagiosData.ITEM_TYPE_DESCRIPTIONS[ass['item_type']]
                    ass['description'] = self.add_description_item_class_project(description,
                                                                                 project_ent)
                    if ass['temporal'] is None:
                        ass['temporal'] = self.temporal
                    ass_items.append(ass)
                elif self.contents_cnt > 1 or self.manifest.item_type == 'projects':
                    # the associated item is for a result set, not an individual item
                    rel_media_cat_ent = False
                    if isinstance(ass['media_class_uri'], str):
                        rel_media_cat_ent = self.get_entity(ass['media_class_uri'])
                    cat_ent = self.get_entity(ass['class_uri'])
                    description = 'A set of '
                    if cat_ent is not False:
                        ass['class_label'] = cat_ent.label
                        ass['class_slug'] = cat_ent.slug
                        ass['title'] = cat_ent.label
                        description += cat_ent.label.lower()
                    else:
                        ass['title'] = 'Related'
                    if rel_media_cat_ent is not False:
                        ass['title'] += ' ' + rel_media_cat_ent.label
                        description += ' ' + rel_media_cat_ent.label.lower()
                    if ass['item_type'] in PelagiosData.ITEM_TYPE_DESCRIPTIONS_PLR:
                        type_des = PelagiosData.ITEM_TYPE_DESCRIPTIONS_PLR[ass['item_type']]
                        ass['title'] += ' ' + type_des
                        description += ' ' + type_des.lower()
                    ass['title'] += ' Related to: ' + self.manifest.label
                    if isinstance(self.class_label, str) and \
                       self.manifest.item_type != 'projects':
                        ass['title'] += ' (' + self.class_label + ')'
                    ass['description'] = self.add_description_item_class_project(description,
                                                                                 project_ent)
                    param_sep = '?'
                    # payload is for querying for temporal data
                    payload = {
                        'response': 'metadata',
                        'type': ass['item_type'],
                        'prop': []}
                    if ass['item_type'] == 'media': 
                        ass['uri'] = settings.CANONICAL_HOST + '/media-search/'
                        if isinstance(self.context, str):
                            ass['uri'] += self.encode_url_context_path(self.context)
                        if cat_ent is not False:
                            ass['uri'] += param_sep + 'prop=rel--' + cat_ent.slug
                            param_sep = '&'
                            payload['prop'].append('rel--' + cat_ent.slug)
                        if rel_media_cat_ent is not False:
                            ass['uri'] += param_sep + 'prop=' + rel_media_cat_ent.slug
                            param_sep = '&'
                            payload['prop'].append(rel_media_cat_ent.slug)
                        elif isinstance(ass['media_class_uri'], str):
                            ass['uri'] += param_sep + 'prop=' + quote_plus(ass['media_class_uri'])
                            payload['prop'].append(ass['media_class_uri'])
                    elif ass['item_type'] == 'subjects':
                        ass['uri'] = settings.CANONICAL_HOST + '/subjects-search/'
                        if isinstance(self.context, str):
                            ass['uri'] += self.encode_url_context_path(self.context)
                        if cat_ent is not False:
                            ass['uri'] += param_sep + 'prop=' + cat_ent.slug
                            param_sep = '&'
                            payload['prop'].append(cat_ent.slug)
                    else:
                        ass['uri'] = settings.CANONICAL_HOST + '/search/'
                        if isinstance(self.context, str):
                            ass['uri'] += self.encode_url_context_path(self.context)
                        if cat_ent is not False:
                            ass['uri'] += param_sep + 'prop=rel--' + cat_ent.slug
                            param_sep = '&'
                            payload['prop'].append('rel--' + cat_ent.slug)
                        ass['uri'] += param_sep + 'type=' + ass['item_type']
                        param_sep = '&'
                    if project_ent is not False:
                        ass['uri'] += param_sep + 'proj=' + project_ent.slug
                        payload['proj'] = project_ent.slug
                    # now query Solr for temporal data
                    cq = CompleteQuery()
                    spatial_context = None
                    if isinstance(self.context, str):
                        spatial_context = self.context
                    if len(payload['prop']) < 1:
                        # remove unused property key
                        payload.pop('prop', None)
                    ass_metadata = cq.get_json_query(payload, spatial_context)
                    if 'dc-terms:temporal' in ass_metadata:
                        ass['temporal'] = ass_metadata['dc-terms:temporal']
                    ass_sets.append(ass)
                else:
                    pass
            if self.manifest.item_type == 'projects':
                # we have a project so get the hero image (if exists) directly
                # for the depiction (note: returns None if not found)
                self.depiction = self.get_depiction_image_file(self.uuid)
            else:
                # we have another item_type, so the self.depiction comes
                # from the list of associated items
                for ass in ass_items:
                    if isinstance(ass['depiction'], str):
                        # the item depiction file is the first one we find
                        # from the associated item list
                        self.depiction = ass['depiction']
                        break      
            self.associated = ass_items + ass_sets
    
    def add_description_item_class_project(self, description, project_ent):
        """ adds item class and project information to a dublin core metadata
            description for associated items
        """ 
        description += ' associated with the '
        if isinstance(self.class_label, str) and \
           self.manifest.item_type != 'projects':
            description += self.class_label.lower() + ' record: ' + self.title
        elif self.manifest.item_type == 'projects':
            description += 'data publication: "' + self.title + '"'
        else:
            description += 'item: ' + self.title
        if project_ent is not False and self.manifest.item_type != 'projects':
            description += '; part of the "' + project_ent.label
            description += '" data publication.'
        return description
     
    def remove_label_from_context(self, label, context):
        """ removes a label from a context """
        if isinstance(context, str):
            if '/' in context:
                context_ex = context.split('/')
                if context_ex[-1] == label:
                    context_ex.pop(-1)
                context = '/'.join(context_ex)
            elif label == context:
                context = None
        return context
    
    def make_dcterms_title(self, label, context):
        """ makes a dcterms title, includes context if present """
        if isinstance(context, str):
            context = self.remove_label_from_context(label, context)
            if not isinstance(context, str):
                title = label
            else:
                title = label + ' from ' + context       
        else:
            title = label
        return title
    
    def encode_url_context_path(self, context):
        """ encodes a context path for a URL, retains
            the path '/' characters
        """
        if '/' in context:
            context_ex = context.split('/')
        else:
            context_ex = [context]
        quote_context_list = []
        for c_part in context_ex:
            url_c_part = urlquote_plus(c_part)
            quote_context_list.append(url_c_part)
        return '/'.join(quote_context_list)        
    
    def get_geo_event_metadata(self):
        """ gets geospatial and event metadata for the item """
        if self.is_valid:
            act_contain = Containment()
            if self.manifest.item_type == 'subjects':
                parents = act_contain.get_parents_by_child_uuid(self.manifest.uuid)
                subject_list = act_contain.contexts_list
                subject_list.insert(0, self.manifest.uuid)
                self.geo_meta = act_contain.get_geochron_from_subject_list(subject_list,
                                                                           'geo')
                self.event_meta = act_contain.get_geochron_from_subject_list(subject_list,
                                                                             'event')
            else:
                self.geo_meta = act_contain.get_related_geochron(self.manifest.uuid,
                                                                 self.manifest.item_type,
                                                                 'geo')
                self.event_meta = act_contain.get_related_geochron(self.manifest.uuid,
                                                                   self.manifest.item_type,
                                                                   'event')
            if self.event_meta is not False and self.event_meta is not None:
                start = None
                stop = None
                for event in self.event_meta:
                    if start is None:
                        start = event.start
                    if stop is None:
                        stop = event.stop
                    if start < event.start:
                        start = event.start
                    if stop > event.stop:
                        stop = event.stop
                if stop is None:
                    stop = start
                if start is not None:
                    if stop < start:
                        stop_temp = start
                        start = stop
                        stop = stop_temp
                    # we have a start year, so make a temporal value in ISON 8601 format
                    self.temporal = ISOyears().make_iso_from_float(start)
                    if stop != start:
                        # stop year different from start, so add a / sep and the stop
                        # year in ISO 8601 format
                        self.temporal += '/' + ISOyears().make_iso_from_float(stop)
            if self.temporal is None and self.manifest.item_type == 'projects':
                # get project teporal metadata via solr
                # now query Solr for temporal data
                cq = CompleteQuery()
                payload = {'proj': self.manifest.slug}
                ass_metadata = cq.get_json_query(payload, None)
                if 'dc-terms:temporal' in ass_metadata:
                     self.temporal = ass_metadata['dc-terms:temporal']

    def get_associated_categories(self):
        """ get categories of items related to the current
            annotated item
        """
        if self.is_valid:
            if isinstance(self.context, str):
                # we have a context path string
                cont_uuids = Subject.objects\
                                    .filter(context__startswith=self.context)\
                                    .exclude(uuid=self.manifest.uuid)\
                                    .values_list('uuid', flat=True)
                if len(cont_uuids) > 1:
                    self.contents_cnt = len(cont_uuids) 
                # now get categories of items contained in this list
                act_categories = self.get_distinct_categories_from_uuids(cont_uuids)
                # add these categories to the self.associated dict
                self.make_raw_associated_from_categories(act_categories)
                # now get media + document items related to this list
                act_categories = self.get_media_rel_categories(cont_uuids)
                # add these categories to the self.associated dict
                self.make_raw_associated_from_categories(act_categories)
            elif self.manifest.item_type == 'projects':
                project_uuid = self.manifest.project_uuid
                # add subjects categories
                act_categories = self.get_distinct_categories_from_project(project_uuid)
                self.make_raw_associated_from_categories(act_categories)
                # now add media + documents, classified also by related subjects 
                act_categories = self.get_project_media_rel_categories(project_uuid)
                self.make_raw_associated_from_categories(act_categories)
            else:
                self.raw_associated = {}
    
    def make_raw_associated_from_categories(self, categories):
        """ takes category data and consolidates it as a
            for the raw_associated dict
        """
        for cat in categories:
            key_fields = []
            key_fields.append(cat['item_type'])
            key_fields.append(cat['class_uri'])
            cat['depiction'] = None
            if 'media_class_uri' in cat:
                key_fields.append(cat['media_class_uri'])
            else:
                cat['media_class_uri'] = False
                key_fields.append('False')
            if 'label' not in cat:
                cat['label'] = False
            if 'uuid' not in cat:
                cat['uuid'] = False
            else:
                if cat['media_class_uri'] == 'oc-gen:image':
                    # we have an image, get the preview of it
                    cat['depiction'] = self.get_depiction_image_file(cat['uuid'])
            cat['title'] = None
            cat['description'] = None
            cat['temporal'] = None  # for temporal metadata
            cat['class_label'] = None
            cat['class_slug'] = None
            cat['uri'] = None
            cat['related'] = self.uri
            key = '/'.join(key_fields)
            if key not in self.raw_associated:
                # adds the category to the dict of raw_associated
                self.raw_associated[key] = cat
    
    def get_depiction_image_file(self, uuid):
        """ gets the file for the media depiction """
        man_files = []
        output = None
        if uuid == self.uuid and \
            self.manifest.item_type == 'projects':
                # get a project hero image
                man_files = Mediafile.objects\
                                     .filter(uuid=uuid,
                                             file_type='oc-gen:hero')[:1]
        else:
            man_files = Mediafile.objects\
                                 .filter(uuid=uuid,
                                         file_type='oc-gen:preview')[:1]
        if len(man_files) > 0:
            output = man_files[0].file_uri
        return output
            
    def get_distinct_categories_from_uuids(self, uuid_list):
        """ gets distinct categories in a list of uuids """
        if self.contents_cnt > 1:
            categories = Manifest.objects\
                                 .filter(uuid__in=uuid_list)\
                                 .values('item_type', 'class_uri')\
                                 .distinct()
        else:
            categories = Manifest.objects\
                                 .filter(uuid__in=uuid_list)\
                                 .values('uuid', 'label', 'item_type', 'class_uri')\
                                 .distinct()
        return categories
    
    def get_distinct_categories_from_project(self, project_uuids):
        """ gets distinct categories in a list of uuids """
        if not isinstance(project_uuids, list):
            project_uuids = [project_uuids]
        categories = Manifest.objects\
                             .filter(project_uuid__in=project_uuids,
                                     item_type='subjects')\
                             .values('item_type', 'class_uri')\
                             .distinct()
        return categories
    
    def get_entity(self, identifier):
        """ gets entities, but checkes first if they are in memory """
        output = False
        if identifier in self.mem_cache_entities:
            output = self.mem_cache_entities[identifier]
        else:
            ent = Entity()
            found = ent.dereference(identifier)
            if found:
                output = ent
                self.mem_cache_entities[identifier] = ent
        return output
    
    def get_media_rel_categories(self, uuid_list):
        """ gets distinct categories (class_uri)
            of items associated with media and document
            resources. This is useful to say
            we have images or documents related to
            bones, sites, potttery or other class_uri
        """
        if len(uuid_list) < 1:
            uuid_list = [self.manifest.uuid]
        media_obj_types = ['media', 'documents']
        q_obj_types = self.make_query_list(media_obj_types)
        q_uuids = self.make_query_list(uuid_list)
        if len(uuid_list) > 1:
            query = ('SELECT mm.item_type AS item_type, '
                     'm.class_uri AS class_uri, '
                     'mm.class_uri AS media_class_uri '
                     'FROM oc_manifest AS m '
                     'JOIN oc_assertions AS ass ON ass.uuid = m.uuid '
                     'JOIN oc_manifest AS mm ON ass.object_uuid = mm.uuid '
                     'WHERE m.uuid IN (' + q_uuids + ') '
                     'AND ass.object_type IN (' + q_obj_types + ') '
                     'GROUP BY mm.item_type, m.class_uri, mm.class_uri; ')
        else:
            query = ('SELECT mm.uuid AS uuid, mm.label AS label, '
                     'mm.item_type AS item_type, '
                     'm.class_uri AS class_uri, '
                     'mm.class_uri AS media_class_uri '
                     'FROM oc_manifest AS m '
                     'JOIN oc_assertions AS ass ON ass.uuid = m.uuid '
                     'JOIN oc_manifest AS mm ON ass.object_uuid = mm.uuid '
                     'WHERE m.uuid IN (' + q_uuids + ') '
                     'AND ass.object_type IN (' + q_obj_types + ') '
                     '; ')
        cursor = connection.cursor()
        cursor.execute(query)
        rows = self.dictfetchall(cursor)
        return rows
    
    def get_project_media_rel_categories(self, project_uuids):
        """ gets distinct categories (class_uri)
            of items in a project associated with media and document
            resources. This is useful to say
            we have images or documents related to
            bones, sites, potttery or other class_uri
        """
        media_obj_types = ['media', 'documents']
        q_obj_types = self.make_query_list(media_obj_types)
        if not isinstance(project_uuids, list):
            project_uuids = [project_uuids]
        q_uuids = self.make_query_list(project_uuids)
        query = ('SELECT mm.item_type AS item_type, '
                 'm.class_uri AS class_uri, '
                 'mm.class_uri AS media_class_uri '
                 'FROM oc_manifest AS m '
                 'JOIN oc_assertions AS ass ON ass.uuid = m.uuid '
                 'JOIN oc_manifest AS mm ON ass.object_uuid = mm.uuid '
                 'WHERE m.project_uuid IN (' + q_uuids + ') '
                 'AND ass.object_type IN (' + q_obj_types + ') '
                 'GROUP BY mm.item_type, m.class_uri, mm.class_uri; ')
        cursor = connection.cursor()
        cursor.execute(query)
        rows = self.dictfetchall(cursor)
        return rows
    
    def get_project_gaz_rels(self, project_uuids, act_gaz_list):
        """ gets distinct categories (class_uri)
            of items in a project associated with media and document
            resources. This is useful to say
            we have images or documents related to
            bones, sites, potttery or other class_uri
        """
        con_pred = Assertion.PREDICATES_CONTAINS
        if not isinstance(act_gaz_list, list):
            act_gaz_list = [act_gaz_list]
        q_gazs = self.make_query_list(act_gaz_list)
        if not isinstance(project_uuids, list):
            project_uuids = [project_uuids]
        good_p_uuids = self.make_query_list(project_uuids)
        project_uuids.append('0')  # now add a project 0 so we get general Open Context items
        # print('all ps: ' + str(project_uuids))
        qall_proj_uuids = self.make_query_list(project_uuids)
        query = ('SELECT la.hash_id AS hash_id '
                 'FROM link_annotations AS la '
                 'JOIN oc_assertions AS oa ON la.subject = oa.uuid '
                 'WHERE la.project_uuid IN (' + qall_proj_uuids + ') '
                 'AND la.object_uri IN (' + q_gazs + ') '
                 'AND oa.predicate_uuid = \'' + con_pred + '\' '
                 'AND oa.project_uuid IN (' + good_p_uuids + ') '
                 '; ')
        cursor = connection.cursor()
        cursor.execute(query)
        rows = self.dictfetchall(cursor)
        return rows

    def make_query_list(self, item_list):
        """ makes a string for item list query """
        list_q = []
        for item in item_list:
            item = '\'' + item + '\''
            list_q.append(item)
        return ', '.join(list_q)

    def dictfetchall(self, cursor):
        """ Return all rows from a cursor as a dict """
        columns = [col[0] for col in cursor.description]
        return [
            dict(zip(columns, row))
            for row in cursor.fetchall()
        ]