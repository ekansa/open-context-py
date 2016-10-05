import json
import requests
from time import sleep
from django.conf import settings
from django.db import connection
from django.db import models
from django.db.models import Q
from django.core.cache import caches
from django.utils.http import urlquote, quote_plus, urlquote_plus
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.libs.generalapi import GeneralAPI
from opencontext_py.libs.isoyears import ISOyears
from opencontext_py.apps.entities.uri.models import URImanagement
from opencontext_py.apps.entities.entity.models import Entity
from opencontext_py.apps.ldata.linkentities.models import LinkEntity
from opencontext_py.apps.ldata.linkannotations.models import LinkAnnotation
from opencontext_py.apps.ldata.linkannotations.equivalence import LinkEquivalence
from opencontext_py.apps.ldata.pelagios.gazgraph import PelagiosGazetteerGraph
from opencontext_py.apps.ldata.pelagios.models import PelagiosData, OaItem
from opencontext_py.apps.ldata.tdar.api import tdarAPI

class PelagiosGazetteerAnnotations():
    """ Calls the database to collect data needed
        to make a Pelagios compliant annotations for
        web resources (ourside of Open Context) that link
        with Open Context published gazetteer entities
        

from opencontext_py.apps.ldata.pelagios.gazetteer import PelagiosGazetteer
pg = PelagiosGazetteer()
pg.get_linked_sites()
len(pg.gaz_uuids)        
    """
    DESCRIPTIONS ={
        'dinaa': {
            'other': 'Content in this data source relates to one or '\
                'more archaeological site file records published in the '\
                'Digital Index of North American Archaeology (DINAA).',
            'tdar': 'Content in the tDAR repository identified to relate to one '\
                'or more archaeological site file records published in the '\
                'Digital Index of North American Archaeology (DINAA). '\
                'Open Context automatically identified such relationships via '\
                'using tDAR\'s API to match Smithsonian Trinomial identifiers.'
        },
        'other': {
            'other': 'Content in this data source relates to one or more '\
                'archaeological site records published by Open Context. '\
                'Open Context contributors and/or editors identified this relationship. ',
            'tdar': 'Content in this data source relates to one or more '\
                'archaeological site records published by Open Context. '\
                'Open Context contributors and/or editors identified this relationship. ',
        }
    }

    DINAA_URI = 'http://opencontext.org/projects/416A274C-CF88-4471-3E31-93DB825E9E4A'
    
    def __init__(self):
        self.gaz_items = {}  # dict with uuid key of gazetteer item objects
        self.gaz_uuids = []
        self.oa_items = LastUpdatedOrderedDict()  # dict with URI key of open annotation item objects
        self.mem_cache_entities = {}
        self.ignore_vocabs = PelagiosData.GAZETTEER_VOCABS
        self.ignore_vocabs.append('http://en.wikipedia.org/')
    
    def make_annotations(self):
        """ makes annoations to note relationships to Open Context Gazetteer places """
        self.get_gaz_places()
        # get references to entities that link to OC places, but not to items in OC
        # or items in PeriodO
        links = LinkAnnotation.objects\
                              .filter(subject__in=self.gaz_uuids)\
                              .exclude(object_uri__contains=settings.CANONICAL_HOST)\
                              .order_by('object_uri')\
                              .iterator()
        for la in links:
            uuid = la.subject
            object_ok = True
            for ignore_uri_base in self.ignore_vocabs:
                if ignore_uri_base in la.object_uri:
                    object_ok = False
            if uuid in self.gaz_items and object_ok:
                # only do this if we have a gazetteer object
                oc_gaz_item = self.gaz_items[uuid]
                if oc_gaz_item.is_valid:
                    if tdarAPI.BASE_URI in la.object_uri:
                        # we have a tDAR item
                        self.make_tdar_annotations(oc_gaz_item, la.obj_extra)
                    else:
                        obj_uri = la.object_uri
                        if obj_uri in self.oa_items:
                            # add the URI of the gazetteer item
                            if oc_gaz_item.uri not in self.oa_items[obj_uri].gazetteer_uris:
                                self.oa_items[obj_uri].gazetteer_uris.append(oc_gaz_item.uri)
                        else:
                            oa_item = OaItem()
                            oa_item.is_valid = True
                            oa_item.mem_cache_entities = self.mem_cache_entities
                            obj_ent = oa_item.get_entity(obj_uri)
                            self.mem_cache_entities = oa_item.mem_cache_entities
                            if obj_ent is not False:
                                # we found the object!
                                oa_item.uri = obj_uri
                                oa_item.title = obj_ent.label
                                oa_item.description = self.get_description_text(oc_gaz_item,
                                                                                'other')
                                oa_item.temporal = oc_gaz_item.temporal
                                if isinstance(obj_ent.vocab_uri, str):
                                    # make the vocabulary for the entity the item's project uri
                                    oa_item.project_uri = obj_ent.vocab_uri
                                else:
                                    oa_item.project_uri = obj_uri
                                oa_item.gazetteer_uris.append(oc_gaz_item.uri)
                                self.oa_items[obj_uri] = oa_item
    
    def make_tdar_annotations(self, oc_gaz_item, obj_extra):
        """ makes annotations for resources in tDAR
            that relate to Open Context gazetteer items
        """
        if isinstance(obj_extra, dict):
            if 'dc-terms:isReferencedBy' in obj_extra:
                if isinstance(obj_extra['dc-terms:isReferencedBy'], list):
                    if len(obj_extra['dc-terms:isReferencedBy']) > 0:
                        for tdar_item in obj_extra['dc-terms:isReferencedBy']:
                            tdar_uri = tdar_item['id']
                            if tdar_uri in self.oa_items:
                                # add the URI of the gazetteer item
                                if oc_gaz_item.uri not in self.oa_items[tdar_uri].gazetteer_uris:
                                    self.oa_items[tdar_uri].gazetteer_uris.append(oc_gaz_item.uri)
                            else:
                                oa_item = OaItem()
                                oa_item.is_valid = True
                                oa_item.uri = tdar_uri
                                oa_item.title = tdar_item['label']
                                oa_item.description = self.get_description_text(oc_gaz_item,
                                                                                'tdar')
                                oa_item.temporal = oc_gaz_item.temporal
                                # use the tDAR uri for the item's project URI
                                oa_item.project_uri = tdarAPI.BASE_URI
                                oa_item.gazetteer_uris.append(oc_gaz_item.uri)
                                self.oa_items[tdar_uri] = oa_item
    
    def get_description_text(self, oc_gaz_item, sub_key='other'):
        """ get description text appropriate for a given gazetteer item.
            This checks to see if the gazetteer item is related to the DINAA
            project, and if the item is a tDAR item or other (the sub_key)
        """
        output = None
        key = 'other'
        if oc_gaz_item.parent_project_uri == self.DINAA_URI:
            key = 'dinaa'
        if key in self.DESCRIPTIONS:
            des_options = self.DESCRIPTIONS[key]
            if sub_key in des_options:
                output = des_options[sub_key]
        return output
                        
    def get_gaz_places(self):
        """ gets site entities that link to
            collections outside of open context,
            prepare them for use as a gazetteer
        """
        p_gg = PelagiosGazetteerGraph()
        p_gg.get_db_data()
        self.gaz_items = p_gg.data_obj.gaz_items
        self.gaz_uuids = p_gg.data_obj.gaz_uuids
    
    
