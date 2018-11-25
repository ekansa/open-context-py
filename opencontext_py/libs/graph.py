#!/usr/bin/env python
import json

from django.conf import settings
from django.http import HttpResponse

from rdflib.plugin import register, Parser
from rdflib import ConjunctiveGraph, Graph, URIRef, Literal

register('json-ld', Parser, 'rdflib_jsonld.parser', 'JsonLDParser')

"""
Functions to load JSON-LD into a graph to make serialization into
other formats easier.

from opencontext_py.libs.graph import (
    RDF_SERIALIZATIONS,
    graph_serialize
)


import requests
from opencontext_py.libs.graph import make_graph_from_json_ld
urlp = 'http://127.0.0.1:8000/contexts/project-vocabs/C5B4F73B-5EF8-4099-590E-B0275EDBA2A7'
rp = requests.get(urlp)
gp = make_graph_from_json_ld(rp.json())

import requests
urlp = 'http://127.0.0.1:8000/contexts/project-vocabs/C5B4F73B-5EF8-4099-590E-B0275EDBA2A7'
headers = {'Accept': 'text/turtle'}
rp = requests.get(urlp, headers=headers)
rp.text



"""

RDF_SERIALIZATIONS = [
    # 'application/n-quads', # .nq
    'application/n-triples', # .nt
    'application/rdf+xml', # .rdf
    'text/turtle', # .ttl
]

def make_graph_from_json_ld(json_ld, id=None):
    """Returns a graph made from JSON-LD."""
    if isinstance(json_ld, dict):
        if not id and 'id' in json_ld:
            # ID for graph is in the JSON-LD
            id = json_ld['id']
        elif not id and '@id' in json_ld:
            # ID for graph is in the JSON-LD
            id = json_ld['@id']
        json_ld = json.dumps(json_ld, ensure_ascii=False)
    if isinstance(id, str):
        id = URIRef(id)
    try:
        g = ConjunctiveGraph().parse(
            data=json_ld,
            publicID=id,
            format='json-ld')
    except:
        return None
    return g

def graph_serialize(graph_media_type, json_ld, id=None):
    """Returns a serialization of a graph from a JSON-LD object"""
    if graph_media_type not in RDF_SERIALIZATIONS:
        return None
    graph = make_graph_from_json_ld(json_ld, id=None)
    if graph is None:
        return None
    return graph.serialize(format=graph_media_type)
    try:
        output = graph.serialize(format=graph_media_type)
    except:
        return None
    return output

def strip_non_point_features(json_ld):
    """Removes non point features from a JSON-LD response."""
    # This is a HACK, but useful for the short term because JSON-LD
    # does not support lists of lists, so complex geospatial features
    # need to get removed to keep fussy validators happy.
    if not isinstance(json_ld, dict):
        return json_ld
    if 'features' not in json_ld:
        return json_ld
    new_features = []
    for feature in json_ld['features']:
        if 'geometry' not in feature:
            continue
        if 'type' not in feature['geometry']:
            continue
        if feature['geometry']['type'].lower() == 'point':
            new_features.append(feature)
    json_ld['features'] = new_features
    return json_ld
