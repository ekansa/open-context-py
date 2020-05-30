import time
import json
from collections import OrderedDict
from django.conf import settings
from django.db import models
from django.db.models import Q
from opencontext_py.libs.rootpath import RootPath
from opencontext_py.libs.languages import Languages
from opencontext_py.libs.isoyears import ISOyears
from opencontext_py.libs.general import LastUpdatedOrderedDict, DCterms
from opencontext_py.apps.entities.uri.models import URImanagement
from opencontext_py.apps.contexts.models import ItemContext
from opencontext_py.apps.ocitems.ocitem.itemkeys import ItemKeys
from opencontext_py.apps.ocitems.ocitem.caching import ItemGenerationCache
from opencontext_py.apps.ocitems.ocitem.spatialtemporal import ItemSpatialTemporal
from opencontext_py.apps.ocitems.ocitem.attributes import ItemAttributes
from opencontext_py.apps.ocitems.ocitem.partsjsonld import PartsJsonLD
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.ocitems.predicates.models import Predicate
from opencontext_py.apps.ocitems.octypes.models import OCtype
from opencontext_py.apps.ocitems.mediafiles.models import Mediafile
from opencontext_py.apps.ocitems.documents.models import OCdocument
from opencontext_py.apps.ocitems.persons.models import Person
from opencontext_py.apps.ocitems.projects.models import Project
from opencontext_py.apps.ocitems.projects.metadata import ProjectRels, ProjectMeta
from opencontext_py.apps.ldata.linkannotations.authorship import Authorship
from opencontext_py.apps.ldata.linkannotations.licensing import Licensing


# OCitem is a very general class for all Open Context items.
# This class is used to make a JSON-LD output from data returned from the database via other apps
class OCitem():

    def __init__(self, cannonical_uris=False):
        self.cannonical_uris = cannonical_uris
        self.time_start = time.time()
        self.json_ld = LastUpdatedOrderedDict()
        self.assertion_hashes = False  # provide hash ids for assertions, useful for edits
        self.exists = None
        self.uuid = None
        self.slug = None
        self.label = None
        self.item_type = None
        self.project_uuid = None
        self.published = None
        self.modified = None
        self.manifest = None
        self.proj_context_json_ld = None
        self.item_space_time = None
        self.item_attributes = None
        self.class_uri_list = []  # uris of item classes used in this item
        self.item_gen_cache = ItemGenerationCache(cannonical_uris)
        rp = RootPath()
        if self.cannonical_uris:
            self.base_url = rp.cannonical_host
        else:
            self.base_url = rp.get_baseurl()
    
    def check_exists(self, uuid_or_slug):
        """ checks to see it the item is in the manifest """
        exists = True
        try:
            exists = True
            self.manifest = Manifest.objects.get(Q(uuid=uuid_or_slug) | Q(slug=uuid_or_slug))
            self.uuid = self.manifest.uuid
            self.slug = self.manifest.slug
            self.label = self.manifest.label
            self.item_type = self.manifest.item_type
            self.project_uuid = self.manifest.project_uuid
        except Manifest.DoesNotExist:
            exists = False
            self.manifest = False
        self.exists = exists
        return exists

    def generate_json_ld(self):
        """ make json_ld for an item """
        if isinstance(self.manifest, Manifest):
            self.add_context_json_ld(self.project_uuid)
            # we've got an item in the manifest, so OK to make some JSON-LD for it
            if self.manifest.item_type == 'projects':
                # prep the cache of project metadata, which will be useful for geospatial data
                # and making project specific data
                self.item_gen_cache.get_all_project_metadata(self.manifest.uuid)
            self.get_item_spatial_temporal()
            self.get_item_attributes()
            self.add_general_json_ld()
            # add spatial context information
            self.json_ld = self.item_space_time.add_json_ld_geojson_contexts(self.json_ld)
            # add child item information
            self.json_ld = self.item_space_time.add_contents_json_ld(self.json_ld)
            # give the item_attributes object a list of parent contexts
            self.item_attributes.parent_context_list = self.item_space_time.parent_context_list
            # add attribute information
            self.json_ld = self.item_attributes.add_json_ld_attributes(self.json_ld) 
    
    def get_item_spatial_temporal(self):
        """ gets spatial temporal and context information from the cache and / or database
            that describes this item
        """
        if isinstance(self.manifest, Manifest) and self.item_space_time is None:
            # we've got a manifest object and we don't yet have item space time context gathered
            self.item_space_time = ItemSpatialTemporal()
            self.item_space_time.manifest = self.manifest
            self.item_space_time.assertion_hashes = self.assertion_hashes
            self.item_space_time.get_spatial_temporal_context()
            
    def get_item_attributes(self):
        """ gets attribute information from the cache and / or database
            that describes this item
        """
        if isinstance(self.manifest, Manifest) and self.item_attributes is None:
            # we've got a manifest object and we don't yet have item attributes gathered
            self.item_attributes = ItemAttributes()
            self.item_attributes.manifest = self.manifest
            self.item_attributes.assertion_hashes = self.assertion_hashes
            self.item_attributes.proj_context_json_ld = self.proj_context_json_ld
            self.item_attributes.get_db_item_attributes()

    def add_context_json_ld(self, project_uuid):
        """ adds context to the json_ld """
        context = []
        item_context_obj = ItemContext(False)
        context.append(item_context_obj.id)  # add the URI for the general item context
        context.append(item_context_obj.geo_json_context)  # add the URI for GeoJSON context
        self.proj_context_json_ld = self.item_gen_cache.get_project_context(
            project_uuid,
            self.assertion_hashes
        )
        proj_context_uri = None
        for id_key in ['@id', 'id']:
            if not id_key in self.proj_context_json_ld:
                continue
            proj_context_uri = self.proj_context_json_ld[id_key]
        
        if proj_context_uri:
            context.append(proj_context_uri)  # add the URI for project context
        
        self.json_ld['@context'] = context
    
    
    
    def add_general_json_ld(self):
        """ adds general (manifest) information to the JSON-LD object """
        self.json_ld['id'] = URImanagement.make_oc_uri(self.uuid, self.item_type)
        self.json_ld['uuid'] = self.uuid
        self.json_ld['slug'] = self.slug
        self.json_ld['label'] = self.label
        # add multilingual alternative labels
        if isinstance(self.manifest.localized_json, dict):
            if len(self.manifest.localized_json) > 0:
                json_ld['skos:altLabel'] = self.manifest.localized_json
        if self.manifest.item_type in PartsJsonLD.ITEM_TYPE_CLASS_LIST \
           and len(self.manifest.class_uri) > 1:
            self.json_ld['category'] = [
                self.manifest.class_uri
            ]
        if self.manifest.item_type == 'projects':
            # now add the project specific data to the JSON-LD
            self.add_project_json_ld()
        elif self.manifest.item_type == 'documents':
            # now add document specific information to the JSON-LD
            self.add_document_json_ld()
        elif self.manifest.item_type == 'predicates':
            # now add the predicate specific data the JSON-LD
            self.add_predicate_json_ld()
        elif self.manifest.item_type == 'types':
            self.add_type_json_ld()
    
    def add_project_json_ld(self):
        """ adds project specific information to the JSON-LD object """
        project = self.item_gen_cache.get_project_model_object(self.manifest.uuid)
        if isinstance(project, Project):
            dc_abstract = ItemKeys.PREDICATES_DCTERMS_ABSTRACT
            lang_obj = Languages()
            self.json_ld['description'] = lang_obj.make_json_ld_value_obj(project.short_des,
                                                                          project.sm_localized_json)
            self.json_ld[dc_abstract] = lang_obj.make_json_ld_value_obj(project.content,
                                                                        project.lg_localized_json)
            if isinstance(project.edit_status, int):
                # add editorial status
                oc_status = 'oc-gen:edit-level-' + str(project.edit_status)
                parts_json_ld = PartsJsonLD()
                self.json_ld = parts_json_ld.addto_predicate_list(self.json_ld,
                                                                  'bibo:status',
                                                                   oc_status,
                                                                  'uri')
                if project.edit_status == 0:
                    self.json_ld = parts_json_ld.addto_predicate_list(self.json_ld,
                                                                      'bibo:status',
                                                                      'bibo:status/forthcoming',
                                                                      'uri')
                elif project.edit_status >= 1 and project.edit_status <= 2:
                    self.json_ld = parts_json_ld.addto_predicate_list(self.json_ld,
                                                                      'bibo:status',
                                                                      'bibo:status/nonPeerReviewed',
                                                                      'uri')
                else:
                    self.json_ld = parts_json_ld.addto_predicate_list(self.json_ld,
                                                                      'bibo:status',
                                                                      'bibo:status/peerReviewed',
                                                                      'uri')
    
    def add_document_json_ld(self):
        """ adds document specific information to the JSON-LD object """
        try:
            document = OCdocument.objects.get(uuid=self.manifest.uuid)
        except OCdocument.DoesNotExist:
            document = None
        if isinstance(document, OCdocument):
            rdf_html = ItemKeys.PREDICATES_RDF_HTML
            lan_obj = Languages()
            self.json_ld[rdf_html] = lan_obj.make_json_ld_value_obj(document.content,
                                                                    document.localized_json)
    
    def add_predicate_json_ld(self):
        """ adds predicate specific information to the JSON-LD object """
        try:
            predicate = Predicate.objects.get(uuid=self.manifest.uuid)
        except Predicate.DoesNotExist:
            predicate = None
        if isinstance(predicate, Predicate):
            self.json_ld['oc-gen:data-type'] = predicate.data_type
            p_range = LastUpdatedOrderedDict()
            p_range['id'] = predicate.data_type
            if predicate.data_type == 'id':
                p_range['id'] = 'http://opencontext.org/vocabularies/oc-general/items'
                p_range['label'] = 'URI identified items'
            elif predicate.data_type == 'xsd:string':
                p_range['label'] = 'Alphanumeric text strings'
            elif predicate.data_type == 'xsd:double':
                p_range['label'] = 'Decimal values'
            elif predicate.data_type == 'xsd:integer':
                p_range['label'] = 'Integer values'
            elif predicate.data_type == 'xsd:date':
                p_range['label'] = 'Calendar / date values'
            self.json_ld['rdfs:range'] = [p_range]
            if self.assertion_hashes:
                # add a default sort order, for edit view JSON
                self.json_ld['oc-gen:default-sort-order'] = float(predicate.sort)
    
    def add_type_json_ld(self):
        """ adds type specific information to the JSON-LD object """
        try:
            octype = OCtype.objects.get(uuid=self.manifest.uuid)
        except OCtype.DoesNotExist:
            octype = None
        if isinstance(octype, OCtype):
            parts_json_ld = PartsJsonLD()
            parts_json_ld.proj_context_json_ld = self.proj_context_json_ld
            parts_json_ld.predicate_uri_as_stable_id = ItemKeys.PREDICATES_OWL_SAMEAS
            self.json_ld = parts_json_ld.addto_predicate_list(self.json_ld,
                                                              ItemKeys.PREDICATES_SKOS_RELATED,
                                                              octype.predicate_uuid,
                                                              'predicates')