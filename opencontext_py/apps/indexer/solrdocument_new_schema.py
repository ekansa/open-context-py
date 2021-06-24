import copy
import datetime
import json
from django.conf import settings
from django.utils.encoding import force_text
from opencontext_py.libs.isoyears import ISOyears
from opencontext_py.libs.general import LastUpdatedOrderedDict, DCterms
from opencontext_py.libs.chronotiles import ChronoTile
from opencontext_py.libs.globalmaptiles import GlobalMercator

from opencontext_py.apps.all_items.models import (
    AllManifest,
    AllAssertion,
    AllHistory,
    AllResource,
    AllIdentifier,
    AllSpaceTime,
)
from opencontext_py.apps.all_items import configs
from opencontext_py.apps.all_items import hierarchy
from opencontext_py.apps.all_items import labels
from opencontext_py.apps.all_items import utilities
from opencontext_py.apps.all_items.representations import item
from opencontext_py.apps.all_items.representations.template_prep import (
    prepare_for_item_dict_solr_and_html_template,
    prepare_for_item_dict_html_template
)

from opencontext_py.apps.indexer import solr_utils 


# the list below defines predicates used for
# semantic equivalence in indexing
# linked data
LD_EQUIVALENT_PREDICATES = [
    'skos:closeMatch',
    'skos:exactMatch',
    'owl:sameAs',
    'foaf:isPrimaryTopicOf'
]

LD_IDENTIFIER_PREDICATES = [
    'owl:sameAs',
    'foaf:isPrimaryTopicOf'
]

LD_DIRECT_PREDICATES = [
    'http://nomisma.org/ontology#hasTypeSeriesItem',
    'http://erlangen-crm.org/current/P2_has_type',
    'http://www.wikidata.org/wiki/Property:P3328',
    'oc-gen:has-technique',
    'rdfs:range',
    'skos:example',
    'skos:related',
]

PERSISTENT_ID_ROOTS = [
    'https://doi.org',
    'http://doi.org',
    'https://dx.doi.org',
    'http://dx.doi.org',
    'https://n2t.net/ark:/',
    'http://n2t.net/ark:/',
    'https://orcid.org',
    'http://orcid.org'
]

LABELING_PREDICATES = [
    'label',
    'skos:altLabel',
    'skos:prefLabel',
    'dc-terms:title',
]


# Default publication date, if the record does not exist.
# This should ONLY be the case for the very first example
# datasets in Open Context, before we got our metadata
# house in better order.
DEFAULT_PUBLISHED_DATETIME = datetime.date(2007, 1, 1)

# The delimiter for parts of an object value added to a
# solr field.
SOLR_VALUE_DELIM = solr_utils.SOLR_VALUE_DELIM 

FIELD_SUFFIX_CONTEXT = 'context_id'
FIELD_SUFFIX_PREDICATE = 'pred_id'
FIELD_SUFFIX_PROJECT = 'project_id'

ALL_CONTEXT_SOLR = 'obj_all' + SOLR_VALUE_DELIM + FIELD_SUFFIX_CONTEXT
ROOT_CONTEXT_SOLR = 'root' + SOLR_VALUE_DELIM + FIELD_SUFFIX_CONTEXT
ROOT_PREDICATE_SOLR = 'root' + SOLR_VALUE_DELIM + FIELD_SUFFIX_PREDICATE
ROOT_LINK_DATA_SOLR = 'ld' + SOLR_VALUE_DELIM + FIELD_SUFFIX_PREDICATE
ROOT_PROJECT_SOLR = 'root' + SOLR_VALUE_DELIM + FIELD_SUFFIX_PROJECT
ALL_PROJECT_SOLR = 'obj_all' + SOLR_VALUE_DELIM + FIELD_SUFFIX_PROJECT
EQUIV_LD_SOLR = 'skos_closematch' + SOLR_VALUE_DELIM + FIELD_SUFFIX_PREDICATE
FILE_SIZE_SOLR = 'filesize'
FILE_MIMETYPE_SOLR = 'mimetype' + SOLR_VALUE_DELIM + FIELD_SUFFIX_PREDICATE
RELATED_SOLR_DOC_PREFIX = 'REL_'


# Maximum depth of geotile zoom
MAX_GEOTILE_ZOOM = 30
# Minimum allowed geotile zoom
MIN_GEOTILE_ZOOM = 6



class SolrDocumentNS:
    '''
    Defines the Solr Document objects that the crawler will crawl. Solr
    fields are stored in a Solr Document's "fields" property.
    '''

    def __init__(self, uuid, man_obj=None, rep_dict=None):
        '''
        Using our expanded representation dict to make a solr
        document.
        '''
    
        # Are we doing a related document? Related documents are
        # made to add extra metadata to a solr document. Typically
        # documents for "media" and "document" item_types lack much
        # description, so we use related documents from "subjects"
        # item_types that are linked to media and document item_types
        # to add more descriptive information.
        # prefix for related solr_documents
        self.solr_doc_prefix = ''
        # do_related means that we're making solr fields for
        # a related item (a subject linked to a media resource)
        # this makes only some solr fields
        self.do_related = False
        # First get core data structures
        if not man_obj or not rep_dict:
            man_obj, rep_dict = item.make_representation_dict(
                subject_id=uuid,
                for_solr_or_html=True,
            )
            rep_dict = prepare_for_item_dict_solr_and_html_template(
                man_obj, 
                rep_dict
            )
        self.man_obj = man_obj
        self.rep_dict = rep_dict

        self.geo_specified = False
        self.chrono_specified = False
        # Store values here
        self.fields = {}
        self.fields['text'] = ''  # Start of full-text field
        self.fields['human_remains'] = 0  # Default, item is not about human remains.
        # Default media counts.
        self.fields['image_media_count'] = 0
        self.fields['other_binary_media_count'] = 0
        self.fields['document_count'] = 0
        # The solr field for joins by uuid.
        self.join_solr_field = 'join' +  SOLR_VALUE_DELIM + 'pred_id'




    def _set_required_solr_fields(self):
        """Sets data for the core solr fields (non-dynamic, required)."""
        self.fields['uuid'] = str(self.man_obj.uuid)
        self.fields['slug_type_uri_label'] = solr_utils.make_entity_string_for_solr(
            slug=self.man_obj.slug,
            data_type=self.man_obj.data_type,
            uri=self.man_obj.uri,
            label=self.man_obj.label,
        )
        self.fields['project_uuid'] =  str(self.man_obj.project_id)
        if not self.man_obj.published:
            published_datetime = DEFAULT_PUBLISHED_DATETIME
        else:
            published_datetime = self.man_obj.published
        self.fields['published'] = published_datetime.strftime(
            '%Y-%m-%dT%H:%M:%SZ'
        )
        self.fields['updated'] = datetime.datetime.utcnow().strftime(
            '%Y-%m-%dT%H:%M:%SZ'
        )
        # default, can add as image media links discovered
        self.fields['image_media_count'] = 0
        # default, can add as other media links discovered
        self.fields['other_binary_media_count'] = 0
        # default, can add as doc links discovered
        self.fields['document_count'] = 0
        self.fields['sort_score'] = float(
            '0.' + self.man_obj.sort.replace('-', '')
        )
        # default, adds to interest score once other fields determined
        self.fields['interest_score'] = 0
        self.fields['item_type'] = self.man_obj.item_type
        self.fields['item_class'] = self.man_obj.item_class.label

    
    def make_solr_doc(self):
        """Make a solr document """
        if not self.man_obj or not self.rep_dict:
            return None
        # Set the required, universal fields for Solr
        self._set_required_solr_fields()
        
    
    def make_related_solr_doc(self):
        """Make a related solr document """
        self.do_related = True
