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
from opencontext_py.apps.ocitems.ocitem.caching import ItemGenerationCache
from opencontext_py.apps.ocitems.ocitem.partsjsonld import PartsJsonLD
from opencontext_py.apps.ocitems.assertions.models import Assertion
from opencontext_py.apps.ocitems.assertions.containment import Containment
from opencontext_py.apps.ocitems.obsmetadata.models import ObsMetadata
from opencontext_py.apps.ocitems.predicates.models import Predicate
from opencontext_py.apps.ocitems.octypes.models import OCtype
from opencontext_py.apps.ocitems.strings.models import OCstring
from opencontext_py.apps.ocitems.identifiers.models import StableIdentifer
from opencontext_py.apps.ldata.linkannotations.models import LinkAnnotation
from opencontext_py.apps.ldata.linkannotations.authorship import Authorship
from opencontext_py.apps.ldata.linkannotations.licensing import Licensing


# OCitem is a very general class for all Open Context items.
# This class is used to make a JSON-LD output from data returned from the database via other apps
class ItemAttributes():
    
    PREDICATES_DCTERMS_PUBLISHED = 'dc-terms:issued'
    PREDICATES_DCTERMS_MODIFIED = 'dc-terms:modified'
    PREDICATES_DCTERMS_CREATOR = 'dc-terms:creator'
    PREDICATES_DCTERMS_CONTRIBUTOR = 'dc-terms:contributor'
    PREDICATES_DCTERMS_ISPARTOF = 'dc-terms:isPartOf'
    PREDICATES_DCTERMS_TITLE = 'dc-terms:title'
    PREDICATES_OCGEN_PREDICATETYPE = 'oc-gen:predType'
    PREDICATES_OCGEN_HASOBS = 'oc-gen:has-obs'
    PREDICATES_OCGEN_SOURCEID = 'oc-gen:sourceID'
    PREDICATES_OCGEN_OBSTATUS = 'oc-gen:obsStatus'
    PREDICATES_OCGEN_OBSLABEL = 'label'
    PREDICATES_OCGEN_OBSNOTE = 'oc-gen:obsNote'
    PREDICATES_FOAF_PRIMARYTOPICOF = 'foaf:isPrimaryTopicOf'
    
    # predicates not for use in observations
    NO_OBS_ASSERTION_PREDS = [
        'skos:note'
    ]

    def __init__(self):
        self.proj_context_json_ld = None
        self.project_uuid = None
        self.manifest = None
        self.assertion_hashes = False
        self.assertions = None
        self.link_annotations = None
        self.stable_ids = None
        dc_terms_obj = DCterms()
        self.DC_META_PREDS = dc_terms_obj.get_dc_terms_list()
        self.item_gen_cache = ItemGenerationCache()
        rp = RootPath()
        self.base_url = rp.get_baseurl()
        self.class_uri_list = []  # uris of item classes used in this item

    def get_db_item_attributes(self):
        """ gets item attributes (other than context, space, temporal) that describe
            an item
        """
        self.get_db_assertions()
        self.get_db_link_anotations()
        self.get_db_stable_ids()

    def get_db_assertions(self):
        """ gets assertions that describe an item, except for assertions about spatial containment """
        self.assertions = Assertion.objects.filter(uuid=self.manifest.uuid) \
                                           .exclude(predicate_uuid=Assertion.PREDICATES_CONTAINS)\
                                           .exclude(visibility__lt=1)\
                                           .order_by('obs_num', 'sort')
    
    def get_db_link_anotations(self):
        """ gets linked data (using standard vocabularies, ontologies) assertions
            that describe an item
        """
        self.link_annotations = LinkAnnotation.objects\
                                              .filter(subject=self.manifest.uuid)\
                                              .order_by('predicate_uri', 'sort')
    
    def get_db_stable_ids(self):
        """ gets stable identifiers (DOIs, ARKs, ORCIDS) """
        self.stable_ids = StableIdentifer.objects.filter(uuid=self.manifest.uuid)