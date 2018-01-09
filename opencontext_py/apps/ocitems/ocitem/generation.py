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
from opencontext_py.apps.entities.entity.models import Entity
from opencontext_py.apps.contexts.models import ItemContext
from opencontext_py.apps.ocitems.ocitem.caching import ItemGenerationCache
from opencontext_py.apps.ocitems.ocitem.attributes import OCitemAttributes
from opencontext_py.apps.ocitems.ocitem.partsjsonld import PartsJsonLD
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.ocitems.predicates.models import Predicate
from opencontext_py.apps.ocitems.octypes.models import OCtype
from opencontext_py.apps.ocitems.strings.models import OCstring
from opencontext_py.apps.ocitems.mediafiles.models import Mediafile
from opencontext_py.apps.ocitems.documents.models import OCdocument
from opencontext_py.apps.ocitems.persons.models import Person
from opencontext_py.apps.ocitems.projects.models import Project
from opencontext_py.apps.ocitems.projects.metadata import ProjectRels, ProjectMeta
from opencontext_py.apps.ocitems.identifiers.models import StableIdentifer
from opencontext_py.apps.ldata.linkannotations.models import LinkAnnotation
from opencontext_py.apps.ldata.linkannotations.authorship import Authorship
from opencontext_py.apps.ldata.linkannotations.licensing import Licensing


# OCitem is a very general class for all Open Context items.
# This class is used to make a JSON-LD output from data returned from the database via other apps
class OCitem():
    PREDICATES_DCTERMS_PUBLISHED = 'dc-terms:issued'
    PREDICATES_DCTERMS_MODIFIED = 'dc-terms:modified'
    PREDICATES_DCTERMS_CREATOR = 'dc-terms:creator'
    PREDICATES_DCTERMS_CONTRIBUTOR = 'dc-terms:contributor'
    PREDICATES_DCTERMS_ISPARTOF = 'dc-terms:isPartOf'
    PREDICATES_DCTERMS_TITLE = 'dc-terms:title'
    PREDICATES_OCGEN_PREDICATETYPE = 'oc-gen:predType'
    PREDICATES_OCGEN_HASCONTEXTPATH = 'oc-gen:has-context-path'
    PREDICATES_OCGEN_HASLINKEDCONTEXTPATH = 'oc-gen:has-linked-context-path'
    PREDICATES_OCGEN_HASPATHITEMS = 'oc-gen:has-path-items'
    PREDICATES_OCGEN_HASCONTENTS = 'oc-gen:has-contents'
    PREDICATES_OCGEN_CONTAINS = 'oc-gen:contains'
    PREDICATES_OCGEN_HASOBS = 'oc-gen:has-obs'
    PREDICATES_OCGEN_SOURCEID = 'oc-gen:sourceID'
    PREDICATES_OCGEN_OBSTATUS = 'oc-gen:obsStatus'
    PREDICATES_OCGEN_OBSLABEL = 'label'
    PREDICATES_OCGEN_OBSNOTE = 'oc-gen:obsNote'
    PREDICATES_FOAF_PRIMARYTOPICOF = 'foaf:isPrimaryTopicOf'

    def __init__(self):
        self.time_start = time.time()
        self.json_ld = LastUpdatedOrderedDict()
        self.assertion_hashes = False  # provide hash ids for assertions, useful for edits
        self.proj_context_json_ld = None
        self.item_attributes = None
        self.uuid = None
        self.slug = None
        self.label = None
        self.item_type = None
        self.project_uuid = None
        self.published = None
        self.modified = None
        self.manifest = None
        dc_terms_obj = DCterms()
        self.DC_META_PREDS = dc_terms_obj.get_dc_terms_list()
        self.item_gen_cache = ItemGenerationCache()
        rp = RootPath()
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
        return exists

    def get_item_attributes(self):
        """ gets attribute information from the cache and / or database
            that describes this item
        """
        if isinstance(self.manifest, Manifest) and self.item_attributes is None:
            # we've got a manifest object and we don't yet have item attributes gathered 
            self.item_attributes = OCitemAttributes()
            self.item_attributes.manifest = self.manifest
            self.item_attributes.get_spatial_temporal_context()
    
    def generate_json_ld(self):
        """ make json_ld for an item """
        if isinstance(self.manifest, Manifest):
            # we've got an item in the manifest, so OK to make some JSON-LD for it
            self.get_item_attributes()
            self.add_context_json_ld(self.project_uuid)
            self.add_general_json_ld()
            # add spatial context information
            self.json_ld = self.item_attributes.add_json_ld_contexts(self.json_ld)

    def add_context_json_ld(self, project_uuid):
        """ adds context to the json_ld """
        context = []
        item_context_obj = ItemContext()
        context.append(item_context_obj.id)  # add the URI for the general item context
        context.append(item_context_obj.geo_json_context)  # add the URI for GeoJSON context
        self.proj_context_json_ld = self.item_gen_cache.get_project_context(project_uuid,
                                                                            self.assertion_hashes)
        proj_context_uri = self.proj_context_json_ld['id']
        context.append(proj_context_uri)  # add the URI for project context
        self.json_ld['@context'] = context
        
    def add_general_json_ld(self):
        """ adds general (manifest) information to the JSON-LD object """
        self.json_ld['id'] = self.base_url + '/' + self.item_type + '/' + self.uuid
        self.json_ld['uuid'] = self.uuid
        self.json_ld['slug'] = self.slug
        self.json_ld['label'] = self.label
        self.json_ld['category'] = [
            self.manifest.class_uri
        ] 
        