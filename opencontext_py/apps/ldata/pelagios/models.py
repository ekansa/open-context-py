import json
import requests
from time import sleep
from django.conf import settings
from django.db import connection
from django.db import models
from django.db.models import Q
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.libs.generalapi import GeneralAPI
from opencontext_py.apps.entities.entity.models import Entity
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.ocitems.assertions.models import Assertion
from opencontext_py.apps.ocitems.subjects.models import Subject
from opencontext_py.apps.ldata.linkentities.models import LinkEntity
from opencontext_py.apps.ldata.linkannotations.models import LinkAnnotation
from opencontext_py.apps.ldata.linkannotations.equivalence import LinkEquivalence


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
    
    def __init__(self):
        self.oa_items = {}  # dict with uuid key of open annotation item objects
        self.mem_cache_entities = {}
        self.db_chunk_size = 100
        self.test_limit = False
        self.project_uuids = []
    
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
                oa_item.validate()
                if oa_item.is_valid:
                    oa_item.get_associated_categories()
                    print(oa_item.manifest.label)
                    print('Number associated: ' + str(len(oa_item.associated)))
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
            man_objs = Manifest.objects\
                               .filter(uuid__in=man_uuids,
                                       project_uuid__in=self.project_uuids)
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
            used_gaz_annos = LinkAnnotation.objects\
                                           .filter(object_uri__in=act_gaz_list,
                                                   project_uuid__in=self.project_uuids)
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
        self.uuid = None
        self.manifest = None
        self.context = None
        self.contents_cnt = 0
        self.gazetteer_uris = []
        self.mem_cache_entities = {}
        self.associated = {}
    
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
        else:
            if self.manifest.item_type == 'subjects':
                if not isinstance(self.context, str):
                    self.is_valid = False
        if self.is_valid is None:
            # since it's not false, and is none
            # it is valid
            self.is_valid = True
        return self.is_valid
    
    def get_associated_categories(self):
        """ get categories of items related to the current
            annotated item
        """
        if self.is_valid:
            if isinstance(self.context, str):
                # we have a context path string
                cont_uuids = Subject.objects\
                                    .filter(context__startswith=self.context)\
                                    .values_list('uuid', flat=True)
                if len(cont_uuids) > 1:
                    self.contents_cnt = len(cont_uuids) 
                # now get categories of items contained in this list
                act_categories = self.get_distinct_categories_from_uuids(cont_uuids)
                # add these categories to the self.associated dict
                self.make_associated_from_categories(act_categories)
                # now get media + document items related to this list
                act_categories = self.get_media_rel_categories(cont_uuids)
                # add these categories to the self.associated dict
                self.make_associated_from_categories(act_categories)
            elif self.manifest.item_type == 'projects':
                project_uuid = self.manifest.project_uuid
                # add subjects categories
                act_categories = self.get_distinct_categories_from_project(project_uuid)
                self.make_associated_from_categories(act_categories)
                # now add media + documents, classified also by related subjects 
                act_categories = self.get_project_media_rel_categories(project_uuid)
                self.make_associated_from_categories(act_categories)
            else:
                self.associated = {}
    
    def make_associated_from_categories(self, categories):
        """ takes category data and consolidates it as a
            for the associated dict
        """
        for cat in categories:
            key_fields = []
            key_fields.append(cat['item_type'])
            key_fields.append(cat['class_uri'])
            if 'media_class_uri' in cat:
                key_fields.append(cat['media_class_uri'])
            else:
                cat['media_class_uri'] = False
                key_fields.append('False')
            if 'label' not in cat:
                cat['label'] = False
            key = '/'.join(key_fields)
            if key not in self.associated:
                self.associated = cat
                            
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
                                 .values('label', 'item_type', 'class_uri')\
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
        media_obj_types = ['media', 'documents']
        q_obj_types = self.make_query_list(media_obj_types)
        q_uuids = self.make_query_list(uuid_list)
        query = ('SELECT mm.item_type AS item_type, '
                 'm.class_uri AS class_uri, '
                 'mm.class_uri AS media_class_uri '
                 'FROM oc_manifest AS m '
                 'JOIN oc_assertions AS ass ON ass.uuid = m.uuid '
                 'JOIN oc_manifest AS mm ON ass.object_uuid = mm.uuid '
                 'WHERE m.uuid IN (' + q_uuids + ') '
                 'AND ass.object_type IN (' + q_obj_types + ') '
                 'GROUP BY mm.item_type, m.class_uri, mm.class_uri; ')
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