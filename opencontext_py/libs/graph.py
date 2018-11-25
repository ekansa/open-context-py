#!/usr/bin/env python
import json

from django.conf import settings
from django.http import HttpResponse
from opencontext_py.libs.general import LastUpdatedOrderedDict
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

def make_point_feature_list(old_features):
    """Makes a new list of point-only features."""
    new_features = []
    for feature in old_features:
        if 'geometry' not in feature:
            continue
        if 'type' not in feature['geometry']:
            continue
        if feature['geometry']['type'].lower() == 'point':
            new_features.append(feature)
    return new_features

def strip_non_point_features(json_ld):
    """Removes non point features from a JSON-LD response."""
    # This is a HACK, but useful for the short term because JSON-LD
    # does not support lists of lists, so complex geospatial features
    # need to get removed to keep fussy validators happy.
    if not isinstance(json_ld, dict):
        return json_ld
    if 'features' not in json_ld:
        return json_ld
    new_json_ld = LastUpdatedOrderedDict()
    for key, vals in json_ld.items():
        if key == 'features':
            new_json_ld['features'] = make_point_feature_list(
                                        json_ld['features'])
        else:
            new_json_ld[key] = vals
    return new_json_ld
