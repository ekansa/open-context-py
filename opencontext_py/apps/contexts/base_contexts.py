import copy
import json
from django.conf import settings
from opencontext_py.libs.rootpath import RootPath

from opencontext_py.apps.all_items import configs
from opencontext_py.apps.all_items.project_contexts.context import get_cache_project_context_df


ITEM_CONTEXT_DICT = {
    "@language": "en",
    "id": "@id",
    "label": "rdfs:label",
    "uuid": "dc-terms:identifier",
    "slug": "oc-gen:slug",
    "type": "@type",
    "category": {
        "@id": "oc-gen:category",
        "@type": "@id"
    },
    "owl:sameAs": {
        "@type": "@id"
    },
    "skos:altLabel": {
        "@container": "@language"
    },
    "xsd:string": {
        "@container": "@language"
    },
    "description": {
        "@id": "dc-terms:description",
        "@container": "@language"
    },
    "dc-terms:description": {
        "@container": "@language"
    },
    "dc-terms:abstract": {
        "@container": "@language"
    },
    "rdfs:comment": {
        "@container": "@language"
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
        "@container": "@list"
    },
    "dc-terms:contributor": {
        "@container": "@list"
    },
    "dc-terms:subject": {
        "@container": "@list"
    },
    "dc-terms:coverage": {
        "@container": "@list"
    },
    "dc-terms:spatial": {
        "@container": "@list"
    },
    "dc-terms:temporal": {
        "@container": "@list"
    },
    "dc-terms:isPartOf": {
        "@container": "@list"
    },
    "dc-terms:license": {
        "@container": "@list"
    },
    "oc-gen:has-contexts": {
        "@container": "@list"
    },
    "oc-gen:has-linked-contexts": {
        "@container": "@list"
    },
    "oc-gen:has-files": {
        "@container": "@list"
    },
    "oc-gen:has-obs": {
        "@container": "@list"
    },
    "oc-gen:has-events": {
        "@container": "@list"
    },
    "oc-gen:has-attribute-groups": {
        "@container": "@list"
    },
    "oc-gen:has-path-items": {
        "@container": "@list"
    },
    "oc-pred:oc-gen-has-geo-overlay": {
        "@container": "@list"
    },
}
