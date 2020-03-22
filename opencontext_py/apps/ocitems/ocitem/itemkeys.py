from django.conf import settings
from opencontext_py.libs.general import LastUpdatedOrderedDict, DCterms



# This class has predicates used as keys in JSON_LD objects
class ItemKeys():
    
    # Dublin Core Predicates
    PREDICATES_DCTERMS_TITLE = 'dc-terms:title'
    PREDICATES_DCTERMS_PUBLISHED = 'dc-terms:issued'
    PREDICATES_DCTERMS_MODIFIED = 'dc-terms:modified'
    PREDICATES_DCTERMS_ISPARTOF = 'dc-terms:isPartOf'
    PREDICATES_DCTERMS_CREATOR = 'dc-terms:creator'
    PREDICATES_DCTERMS_CONTRIBUTOR = 'dc-terms:contributor'
    PREDICATES_DCTERMS_LICENSE = 'dc-terms:license'
    PREDICATES_DCTERMS_TEMPORAL = 'dc-terms:temporal'
    PREDICATES_DCTERMS_ABSTRACT = 'dc-terms:abstract'
    PREDICATES_DCTERMS_HASPART = 'dc-terms:hasPart'
    
    # Context and Containment related Predicates
    PREDICATES_OCGEN_HASCONTEXTPATH = 'oc-gen:has-context-path'
    PREDICATES_OCGEN_HASLINKEDCONTEXTPATH = 'oc-gen:has-linked-context-path'
    PREDICATES_OCGEN_HASPATHITEMS = 'oc-gen:has-path-items'
    PREDICATES_OCGEN_HASCONTENTS = 'oc-gen:has-contents'
    PREDICATES_OCGEN_CONTAINS = 'oc-gen:contains'
    
    # Observation and Description related predicates
    PREDICATES_OCGEN_PREDICATETYPE = 'oc-gen:predType'
    PREDICATES_OCGEN_HASOBS = 'oc-gen:has-obs'
    PREDICATES_OCGEN_SOURCEID = 'oc-gen:sourceID'
    PREDICATES_OCGEN_OBSTATUS = 'oc-gen:obsStatus'
    PREDICATES_OCGEN_OBSLABEL = 'label'
    PREDICATES_OCGEN_OBSNOTE = 'oc-gen:obsNote'
    
    # General metadata related predicates
    PREDICATES_FOAF_PRIMARYTOPICOF = 'foaf:isPrimaryTopicOf'
    PREDICATES_OWL_SAMEAS = 'owl:sameAs'
    PREDICATES_SKOS_RELATED = 'skos:related'
    PREDICATES_RDF_HTML = 'rdf:HTML'

    def __init__(self):
        pass

    