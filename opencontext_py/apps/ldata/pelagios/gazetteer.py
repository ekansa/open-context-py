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
from opencontext_py.apps.ocitems.projects.models import Project
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.ocitems.assertions.models import Assertion
from opencontext_py.apps.ocitems.assertions.containment import Containment
from opencontext_py.apps.ocitems.subjects.models import Subject
from opencontext_py.apps.ocitems.mediafiles.models import Mediafile
from opencontext_py.apps.ldata.linkentities.models import LinkEntity
from opencontext_py.apps.ldata.linkannotations.models import LinkAnnotation
from opencontext_py.apps.ldata.linkannotations.equivalence import LinkEquivalence
from opencontext_py.apps.searcher.solrsearcher.complete import CompleteQuery


class PelagiosGazetteer():
    """ Calls the database to collect data needed
        to make a Pelagios compliant set of Gazetteer assertions

from opencontext_py.apps.ldata.pelagios.gazetteer import PelagiosGazetteer
pg = PelagiosGazetteer()
pg.get_linked_sites()
len(pg.gaz_uuids)        
    """

    TRINOMIAL_PRED_UUID = 'a5c308c3-52f8-4076-b315-d3258d485572'

    def __init__(self):
        self.gaz_items = {}  # dict with uuid key of gazetteer item objects
        self.gaz_uuids = []
        self.db_chunk_size = 100
        self.test_limit = None
        self.project_uuids = []
        self.trinomial_prefix = 'Site '
        self.mem_cache_entities = {}
    
    def get_prep_linked_sites(self):
        """ gets site entities that link to
            collections outside of open context,
            prepare them for use as a gazetteer
        """
        self.get_linked_sites()
    
    def get_linked_sites(self):
        """ gets site entities that link to 
            collections outside of open context
        """
        links = LinkAnnotation.objects\
                              .filter(subject_type='subjects')\
                              .exclude(object_uri__contains=settings.CANONICAL_HOST)\
                              .distinct('subject')\
                              .iterator()
        uuids = []
        for link in links:
            uuids.append(link.subject)
            if len(uuids) >= self.db_chunk_size:
                self.make_gaz_items_from_list(uuids)
                uuids = []
        if len(uuids) > 0:
            self.make_gaz_items_from_list(uuids)
    
    def make_gaz_items_from_list(self, uuids):
        """ gets site manifest objects in a list of uuids
        """
        man_sites = Manifest.objects\
                            .filter(uuid__in=uuids,
                                    class_uri='oc-gen:cat-site')
        for man in man_sites:
            gi = GazetteerItem()
            gi.uuid = man.uuid
            gi.manifest = man
            self.gaz_items[man.uuid] = gi
            self.gaz_uuids.append(man.uuid)
        # now add context paths to new gazetteer items
        self.prep_metadata_contexts_in_list(uuids)
        # now add trinomials as labels
        self.prep_trinomials_in_list(uuids)
    
    def prep_metadata_contexts_in_list(self, uuids):
        """ gets context paths in a uuid list """
        subj_objs = Subject.objects\
                           .filter(uuid__in=uuids)
        for subj_obj in subj_objs:
            uuid = subj_obj.uuid
            if uuid in self.gaz_items:
                self.gaz_items[uuid].context = subj_obj.context
                if self.gaz_items[uuid].manifest is not None:
                    self.gaz_items[uuid].mem_cache_entities = self.mem_cache_entities
                    self.gaz_items[uuid].is_valid = True
                    self.gaz_items[uuid].get_geo_event_metadata()
                    self.gaz_items[uuid].prep_item_dc_metadata()
                    self.mem_cache_entities = self.gaz_items[uuid].mem_cache_entities

    def prep_trinomials_in_list(self, uuids):
        """ prepares trinomial labels by getting values for items in a list,
            if trinomial is found, make it a label for the item
        """
        tris = self.get_trinomals_in_list(uuids)
        # print('Tris: ' + str(len(tris)))
        for tri in tris:
            uuid = tri['uuid']
            if uuid in self.gaz_items:
                self.gaz_items[uuid].label = self.trinomial_prefix + tri['content']

    def get_trinomals_in_list(self, uuids):
        """ gets trinomial values for items in a list
        """
        pred_uuids = [self.TRINOMIAL_PRED_UUID]
        q_pred_uuids = self.make_query_list(pred_uuids)
        q_uuids = self.make_query_list(uuids)
        query = ('SELECT ass.uuid AS uuid, '
                 's.content AS content '
                 'FROM oc_assertions AS ass '
                 'JOIN oc_strings AS s ON ass.object_uuid = s.uuid '
                 'WHERE ass.uuid IN (' + q_uuids + ') '
                 'AND ass.predicate_uuid IN (' + q_pred_uuids + '); ')
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


class GazetteerItem():    

    def __init__(self):
        self.uuid = None
        self.manifest = None
        self.context = None
        self.is_valid = False
        self.uri = None
        self.label = None
        self.title = None
        self.project_uri = None
        self.class_label = 'Site'
        self.parent_project_uri = None
        self.geo_meta = None
        self.event_meta = None
        self.temporal = None
        self.mem_cache_entities = {}
    
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
            project_ent = self.get_entity(self.manifest.project_uuid)
            if not isinstance(self.label, str):
                self.label = self.manifest.label
            self.title = self.make_dcterms_title(self.manifest.label,
                                                 self.context)
            self.description = 'An archaeological site record'
            context = self.remove_label_from_context(self.manifest.label,
                                                     self.context)
            if isinstance(context, str):
                self.description += ' from: ' + context
            if project_ent is not False:
                self.parent_project_uri = URImanagement.make_oc_uri(project_ent.parent_project_uuid,
                                                                    'projects')
                self.description += '; part of the "' + project_ent.label
                self.description += '" data publication.'
            if self.geo_meta is not None and self.geo_meta is not False:
                if len(self.geo_meta) > 0:
                    geo = self.geo_meta[0]
                    if isinstance(geo.note, str):
                        if len(geo.note) > 0:
                            # self.description += ' ' + geo.note
                            pass
                    if geo.specificity < 0:
                        self.description += ' Location data approximated as a security precaution.'
                    if self.manifest.uuid != geo.uuid:
                        rel_meta = self.get_entity(geo.uuid)
                        if rel_meta is not False:
                            self.description += ' Location data provided through relationship to the'
                            self.description += ' related place: ' + rel_meta.label
                            self.description += ' (' + rel_meta.uri + ')'
    
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
            title = label + ' from ' + context       
        else:
            title = label
        return title

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
                if ent.item_type == 'projects':
                    try:
                        proj_obj = Project.objects.get(uuid=ent.uuid)
                    except Project.DoesNotExist:
                        proj_obj = False
                    if proj_obj is not False:
                        ent.parent_project_uuid = proj_obj.project_uuid
                self.mem_cache_entities[identifier] = ent
        return output
