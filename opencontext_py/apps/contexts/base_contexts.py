import copy
import json
from django.conf import settings
from opencontext_py.libs.rootpath import RootPath

from opencontext_py.apps.all_items import configs


rp = RootPath()
BASE_URL = rp.get_baseurl()


GEO_JSON_CONTEXT_URI = "http://geojson.org/geojson-ld/geojson-context.jsonld"
ITEM_CONTEXT_URI = BASE_URL + '/contexts/item.json'
SEARCH_CONTEXT_URI = BASE_URL + '/contexts/search.json'


GENERAL_NAMESPACES_DICT = {
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
    "xsd": "http://www.w3.org/2001/XMLSchema#",
    "skos": "http://www.w3.org/2004/02/skos/core#",
    "owl": "http://www.w3.org/2002/07/owl#",
    "dc-terms": "http://purl.org/dc/terms/",
    "dcmi": "http://dublincore.org/documents/dcmi-terms/",
    "bibo": "http://purl.org/ontology/bibo/",
    "foaf": "http://xmlns.com/foaf/0.1/",
    "cidoc-crm": "http://erlangen-crm.org/current/",
    "dcat": "http://www.w3.org/ns/dcat#",
    "schema": "http://schema.org/",
    "geojson": "https://purl.org/geojson/vocab#",
    "cc": "http://creativecommons.org/ns#",
    "nmo": "http://nomisma.org/ontology#",
    "oc-gen": "http://opencontext.org/vocabularies/oc-general/",
    "oc-pred": "http://opencontext.org/predicates/",
}


SEARCH_NAMESPACES = {
    "opensearch": "http://a9.com/-/spec/opensearch/1.1/",
    "oai-pmh": "http://www.openarchives.org/OAI/2.0/",
    "oc-api": "http://opencontext.org/vocabularies/oc-api/",
}


ITEM_CONTEXT_DICT = {
    "@language": "en",
    "id": "@id",
    "label": "rdfs:label",
    "uuid": "dc-terms:identifier",
    "slug": "dc-terms:identifier",
    "type": "@type",
    "category": {
        "@id": "oc-gen:category",
        "@type": "@id",
    },
    "owl:sameAs": {
        "@type": "@id",
    },
    "skos:altLabel": {
        "@container": "@language",
    },
    "xsd:string": {
        "@container": "@language",
    },
    "description": {
        "@id": "dc-terms:description",
        "@container": "@language",
    },
    "dc-terms:description": {
        "@container": "@language",
    },
    "dc-terms:abstract": {
        "@container": "@language",
    },
    "rdfs:comment": {
        "@container": "@language",
    },
    "reference_type": {
        "@id": "oc-gen:reference-type",
        "@type": "@id",
    },
    "reference_uri": {
        "@id": "oc-gen:reference-uri",
        "@type": "@id",
    },
    "reference_label": {
        "@id": "oc-gen:reference-label",
        "@type": "xsd:string",
    },
    "reference_slug": {
        "@id": "oc-gen:reference-slug",
        "@type": "xsd:string",
    },
    "contained_in_region":{
        "@id": "oc-gen:contained-in-region",
        "@type": "@id",
    },
    "location_precision_note": {
        "@id": "oc-gen:location-precision-note",
        "@type": "xsd:string",
    },
    "dc-terms:creator": {
        "@container": "@list",
    },
    "dc-terms:contributor": {
        "@container": "@list",
    },
    "dc-terms:subject": {
        "@container": "@list",
    },
    "dc-terms:coverage": {
        "@container": "@list",
    },
    "dc-terms:spatial": {
        "@container": "@list",
    },
    "dc-terms:temporal": {
        "@container": "@list",
    },
    "dc-terms:isPartOf": {
        "@container": "@list",
    },
    "dc-terms:license": {
        "@container": "@list",
    },
    "oc-gen:has-contexts": {
        "@container": "@list",
    },
    "oc-gen:has-linked-contexts": {
        "@container": "@list",
    },
    "oc-gen:has-files": {
        "@container": "@list",
    },
    "oc-gen:has-obs": {
        "@container": "@list",
    },
    "oc-gen:has-events": {
        "@container": "@list",
    },
    "oc-gen:has-attribute-groups": {
        "@container": "@list",
    },
    "oc-gen:has-path-items": {
        "@container": "@list",
    },
    "oc-pred:oc-gen-has-geo-overlay": {
        "@container": "@list",
    },
}


ITEM_DICT = {
    **GENERAL_NAMESPACES_DICT,
    **ITEM_CONTEXT_DICT,
}


SEARCH_CONTEXT_DICT = {
    "totalResults": {
        "@id": "opensearch:totalResults",
        "@type": "xsd:integer",
    },
    "startIndex": {
        "@id": "opensearch:startIndex",
        "@type": "xsd:integer",
    },
    "itemsPerPage": {
        "@id": "opensearch:itemsPerPage",
        "@type": "xsd:integer",
    },
    "rdfs:isDefinedBy": {
        "@type": "@id",
    },
    "first": {
        "@id": "oc-api:first",
        "@type": "@id",
    },
    "previous": {
        "@id": "oc-api:previous",
        "@type": "@id",
    },
    "next": {
        "@id": "oc-api:next",
        "@type": "@id",
    },
    "last": {
        "@id": "oc-api:last",
        "@type": "@id",
    },
    "first-json": {
        "@id": "oc-api:first",
        "@type": "@id",
    },
    "previous-json": {
        "@id": "oc-api:previous",
        "@type": "@id",
    },
    "next-json": {
        "@id": "oc-api:next",
        "@type": "@id",
    },
    "last-json": {
        "@id": "oc-api:last",
        "@type": "@id",
    },
    "count": {
        "@id": "oc-api:count",
        "@type": "xsd:integer",
    },
}

SEARCH_DICT = {
    **GENERAL_NAMESPACES_DICT,
    **SEARCH_NAMESPACES,
    **SEARCH_CONTEXT_DICT,
}