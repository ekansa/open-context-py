import datetime
import json
from django.conf import settings
from opencontext_py.libs.languages import Languages
from django.utils.encoding import force_text
from opencontext_py.libs.isoyears import ISOyears
from opencontext_py.libs.general import LastUpdatedOrderedDict, DCterms
from opencontext_py.apps.contexts.readprojectcontext import ReadProjectContextVocabGraph
from opencontext_py.apps.ocitems.ocitem.generation import OCitem
from opencontext_py.apps.ocitems.ocitem.itemkeys import ItemKeys
from opencontext_py.apps.ldata.linkannotations.recursion import LinkRecursion
from opencontext_py.apps.ldata.linkannotations.equivalence import LinkEquivalence
from opencontext_py.apps.ocitems.projects.metadata import ProjectRels
from opencontext_py.apps.ocitems.queries.geochrono import GeoChronoQueries
from opencontext_py.libs.chronotiles import ChronoTile
from opencontext_py.libs.globalmaptiles import GlobalMercator
from opencontext_py.apps.entities.uri.models import URImanagement


class SolrDocumentNew:
    '''
    Defines the Solr Document objects that the crawler will crawl. Solr
    fields are stored in a Solr Document's "fields" property.

from opencontext_py.apps.indexer.solrdocumentnew import SolrDocumentNew
uuid = '9095FCBB-35A8-452E-64A3-B8D52A0B2DB3'
sd_obj = SolrDocumentNew(uuid)
sd_obj.make_solr_doc()
sd_a = sd_obj.fields

    '''

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
        'nmo:hasTypeSeriesItem',
        'http://erlangen-crm.org/current/P2_has_type',
        'cidoc-crm:P2_has_type'
    ]

    PERSISTENT_ID_ROOTS = [
        'doi.org',
        'n2t.net/ark:/',
        'orcid.org'
    ]
    
    LABELING_PREDICATES = [
        'label',
        'skos:altLabel',
        'skos:prefLabel',
        'dc-terms:title',
    ]
    
    CONTEXT_PREDICATES = [
        ItemKeys.PREDICATES_OCGEN_HASCONTEXTPATH,
        ItemKeys.PREDICATES_OCGEN_HASLINKEDCONTEXTPATH,
    ]
    
    # Default publication date, if the record does not exist.
    # This should ONLY be the case for the very first example
    # datasets in Open Context, before we got our metadata
    # house in better order.
    DEFAULT_PUBISHED_DATETIME = datetime.date(2007, 1, 1)

    ALL_CONTEXT_SOLR = 'obj_all___context_id'
    ROOT_CONTEXT_SOLR = 'root___context_id'
    ROOT_PREDICATE_SOLR = 'root___pred_id'
    ROOT_LINK_DATA_SOLR = 'ld___pred_id'
    ROOT_PROJECT_SOLR = 'root___project_id'
    FILE_SIZE_SOLR = 'filesize___pred_numeric'
    FILE_MIMETYPE_SOLR = 'mimetype___pred_id'
    RELATED_SOLR_FIELD_PREFIX = 'rel--'
    
    MISSING_PREDICATE_TYPES = [
        False,
        None,
        '',
        'None',
        'False'
    ]

    def __init__(self, uuid):
        '''
        Using our Python JSON-LD and other info provided in OCitem,
        build up dictionary of solr fields to index.
        '''
        # prefix for related solr_documents
        self.field_prefix = ''
        # do_related means that we're making solr fields for
        # a related item (a subject linked to a media resource)
        # this makes only some solr fields
        self.do_related = False
        self.max_file_size = 0
        self.oc_item = None
        # First get core data structures
        oc_item = OCitem()
        if oc_item.check_exists(uuid):
            # We found a record for this in the manifest
            oc_item.generate_json_ld()
            self.oc_item = oc_item
        self.geo_specified = False
        self.chrono_specified = False
        # Store values here
        self.fields = {}
        self.fields['text'] = ''  # Start of full-text field
        self.fields['human_remains'] = 0  # Default, item is not about human remains.

    def _set_solr_field_prefix(self):
        """Sets the solr field_prefix, depending on do_related."""
        if self.do_related:
            self.field_prefix = self.RELATED_SOLR_FIELD_PREFIX
        else:
            self.field_prefix = ''
    
    def ensure_text_ok(self):
        """ makes sure the text is solr escaped """
        self.fields['text'] = force_text(self.fields['text'],
                                         encoding='utf-8',
                                         strings_only=False,
                                         errors='surrogateescape')

    def _get_context_path_items(self):
        """Gets the context path items from the oc_item.json_ld."""
        for context_key in self.CONTEXT_PREDICATES:
            if not context_key in self.oc_item.json_ld:
                continue
            context = self.oc_item.json_ld[context_key]
            if ItemKeys.PREDICATES_OCGEN_HASPATHITEMS in context:
                return context[ItemKeys.PREDICATES_OCGEN_HASPATHITEMS]
        return None
    
    def _convert_slug_to_solr(self, slug):
        """Converts a slug to a solr style slug."""
        slug = self.field_prefix + slug
        return slug.replace('-', '_')

    def _add_labels_titles_to_text_field(self):
        """Adds multiple language labels and titles to add to text field."""
        lang_obj = Languages()
        for label_pred in self.LABELING_PREDICATES:
            if not label_pred in self.oc_item.json_ld:
                continue
            self.fields['text'] += lang_obj.get_all_value_str(
                    self.oc_item.json_ld[label_pred]
                )
            self.fields['text'] += ' \n'
    
    def _make_slug_type_uri_label(self):
        """Makes a slug_type_uri_label field for solr """
        parts = []
        parts.append(self.oc_item.json_ld['slug'])
        if self.oc_item.manifest.item_type == 'predicates':
            if self.oc_item.json_ld['oc-gen:data-type']:
                # Looks up the predicte type mapped to Solr types
                parts.append(self._get_predicate_type_string(
                                    self.oc_item.json_ld['oc-gen:data-type']
                                ))
            else:
                # Defaults to ID
                parts.append('id')
        else:
            parts.append('id')
        parts.append('/' + self.oc_item.manifest.item_type + '/' + self.oc_item.manifest.uuid)
        parts.append(self.oc_item.json_ld['label'])
        return '___'.join(parts)

    def _set_required_solr_fields(self):
        """Sets data for the core solr fields (non-dynamic, required)."""
        self.fields['uuid'] = self.oc_item.manifest.uuid
        self.fields['slug_type_uri_label'] = self._make_slug_type_uri_label()
        self.fields['project_uuid'] = self.oc_item.manifest.project_uuid
        if not self.oc_item.manifest.published:
            published_datetime = self.DEFAULT_PUBISHED_DATETIME
        else:
            published_datetime = self.oc_item.manifest.published
        self.fields['published'] = published_datetime.strftime(
                                    '%Y-%m-%dT%H:%M:%SZ')
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
                '.' + self.oc_item.manifest.sort.replace('-', '')
            )
        # default, adds to interest score once other fields determined
        self.fields['interest_score'] = 0
        self.fields['item_type'] = self.oc_item.manifest.item_type

    def make_solr_doc(self):
        """Make a solr document """
        self._set_solr_field_prefix()
        if self.oc_item is None:
            return None
        # Set the required, universal fields for Solr
        self._set_required_solr_fields()
        # Add (multilingual) labels and titles to the text field
        self._add_labels_titles_to_text_field()
        # Make sure the text field is valid for Solr
        self.ensure_text_ok()
        
    