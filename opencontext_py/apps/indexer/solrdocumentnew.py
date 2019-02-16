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

from opencontext_py.apps.indexer.solrdocument import SolrDocument
uuid = '70554607-439a-4684-9b58-6f1de54ef403'
uuid = 'AF4DFB9E-9E5F-45F7-891F-ADBE5A9AA0C4'
sd_obj = SolrDocument(uuid)
sd_obj.process_item()
sd_a = sd_obj.fields
sd_a['text']
sd_a['discovery_geotile']
sd_a['form_use_life_chrono_earliest']
uuid = 'f266d43c-cdea-465c-9135-8c39b7ba6cd9'
sd_obj = SolrDocument(uuid)
sd_obj.process_item()
sd_b = sd_obj.fields
    '''

    # the list below defines predicates used for semantic equivalence in indexing
    # linked data
    LD_EQUIVALENT_PREDICATES = ['skos:closeMatch',
                                'skos:exactMatch',
                                'owl:sameAs',
                                'foaf:isPrimaryTopicOf']

    LD_IDENTIFIER_PREDICATES = ['owl:sameAs',
                                'foaf:isPrimaryTopicOf']

    LD_DIRECT_PREDICATES = ['http://nomisma.org/ontology#hasTypeSeriesItem',
                            'nmo:hasTypeSeriesItem',
                            'http://erlangen-crm.org/current/P2_has_type',
                            'cidoc-crm:P2_has_type']

    PERSISTENT_ID_ROOTS = ['doi.org',
                           'n2t.net/ark:/',
                           'orcid.org']

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
        # First get core data structures
        oc_item = OCitem()
        ok = oc_item.check_exists(uuid)
        if ok:
            # we found a record for this in the manifest
            self.json_ld = oc_item.generate_json_ld()
            self.oc_item = oc_item
        else:
            self.json_ld = False
            self.oc_item = None            
        # Store values here
        self.fields = {}
        self.fields['text'] = ''  # Start of full-text field

    def make_solr_doc():
        """Make a solr document """
        if self.oc_item is None:
            return None
    
    