import json
from django.conf import settings
from opencontext_py.libs.rootpath import RootPath
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.libs.languages import Languages


class GeneralContext():
    """
    General namespaces used for JSON-LD
    for project contexts and for items
    """
    
    GEO_JSON_CONTEXT_URI = 'http://geojson.org/geojson-ld/geojson-context.jsonld'
    
    # Cache the GeoJSON context locally so that we can use this in
    # cases of a deployment that has no larger Web access.
    GEO_JSON_CONTEXT = """
{
  "@context": {
    "geojson": "https://purl.org/geojson/vocab#",
    "Feature": "geojson:Feature",
    "FeatureCollection": "geojson:FeatureCollection",
    "GeometryCollection": "geojson:GeometryCollection",
    "LineString": "geojson:LineString",
    "MultiLineString": "geojson:MultiLineString",
    "MultiPoint": "geojson:MultiPoint",
    "MultiPolygon": "geojson:MultiPolygon",
    "Point": "geojson:Point",
    "Polygon": "geojson:Polygon",
    "bbox": {
      "@container": "@list",
      "@id": "geojson:bbox"
    },
    "coordinates": {
      "@container": "@list",
      "@id": "geojson:coordinates"
    },
    "features": {
      "@container": "@set",
      "@id": "geojson:features"
    },
    "geometry": "geojson:geometry",
    "id": "@id",
    "properties": "geojson:properties",
    "type": "@type"
  }
}
"""

    def __init__(self, id_href=True):
        # for geo_json_context
        self.geo_json_context = self.GEO_JSON_CONTEXT_URI
        context = LastUpdatedOrderedDict()
        context['rdf'] = 'http://www.w3.org/1999/02/22-rdf-syntax-ns#'
        context['rdfs'] = 'http://www.w3.org/2000/01/rdf-schema#'
        context['xsd'] = 'http://www.w3.org/2001/XMLSchema#'
        context['skos'] = 'http://www.w3.org/2004/02/skos/core#'
        context['owl'] = 'http://www.w3.org/2002/07/owl#'
        context['dc-terms'] = 'http://purl.org/dc/terms/'
        context['dcmi'] = 'http://dublincore.org/documents/dcmi-terms/'
        context['bibo'] = 'http://purl.org/ontology/bibo/'
        context['foaf'] = 'http://xmlns.com/foaf/0.1/'
        context['cidoc-crm'] = 'http://erlangen-crm.org/current/'
        context['dcat'] = 'http://www.w3.org/ns/dcat#'
        context['geojson'] = 'https://purl.org/geojson/vocab#'
        context['cc'] = 'http://creativecommons.org/ns#'
        context['nmo'] = 'http://nomisma.org/ontology#'
        context['oc-gen'] = 'http://opencontext.org/vocabularies/oc-general/'
        context['oc-pred'] = 'http://opencontext.org/predicates/'
        context['@language'] = Languages().DEFAULT_LANGUAGE
        context['id'] = '@id'
        context['label'] = 'rdfs:label'
        context['uuid'] = 'dc-terms:identifier'
        context['slug'] = 'oc-gen:slug'
        context['type'] = '@type'
        context['category'] = {'@id': 'oc-gen:category', '@type': '@id'}
        context['owl:sameAs'] = {'@type': '@id'}
        context['skos:altLabel'] = {'@container': '@language'}
        context['xsd:string'] = {'@container': '@language'}
        context['description'] = {'@id': 'dc-terms:description', '@container': '@language'}
        for pred in settings.TEXT_CONTENT_PREDICATES:
            if pred not in context:
                context[pred] = {'@container': '@language'}
        self.context = context
    
    def geo_json_dict(self):
        """ Returns the GeoJSON context as a dictionary object """
        return json.loads(self.GEO_JSON_CONTEXT)


class ItemContext():
    """
    General namespaces used for JSON-LD
    for Items
    """
    DOI = 'https://doi.org/10.6078/M7P848VC'  # DOI for this
    URL = 'https://raw.githubusercontent.com/ekansa/open-context-py/master/json-ld-examples/Item-context.json'

    def __init__(self, id_href=True):
        self.id = self.DOI  # DOI for this
        rp = RootPath()
        base_url = rp.get_baseurl()
        self.href = base_url + '/contexts/item.json'  # URL for this
        if id_href:
            self.id = self.href
        gen_context = GeneralContext()
        context = gen_context.context
        self.geo_json_context = GeneralContext.GEO_JSON_CONTEXT_URI
        context['oc-gen:has-path-items'] = {'@container': '@list'}  # order of containment semantically important
        context['dc-terms:creator'] = {'@container': '@list'}  # order of authorship semantically important
        context['dc-terms:contributor'] = {'@container': '@list'}  # order of authorship semantically important
        context['oc-gen:has-path-items'] = {'@container': '@list'}
        # below are GeoJSON-LD context declarations, commented out to
        """
        context['Feature'] = 'geojson:Feature'
        context['FeatureCollection'] = 'geojson:FeatureCollection'
        context['GeometryCollection'] = 'geojson:GeometryCollection'
        context['LineString'] = 'geojson:LineString'
        context['MultiLineString'] = 'geojson:MultiLineString'
        context['MultiPoint'] = 'geojson:MultiPoint'
        context['MultiPolygon'] = 'geojson:MultiPolygon'
        context['Point'] = 'geojson:Point'
        context['Polygon'] = 'geojson:Polygon'
        context['bbox'] = {'@id': 'geojson:bbox', '@container': '@list'}
        context['coordinates'] = 'geojson:coordinates'
        context['features'] = {'@id': 'geojson:features', '@container': '@set'}
        context['geometry'] = 'geojson:geometry'
        context['properties'] = 'geojson:properties'
        """
        context['Instant'] = 'http://www.w3.org/2006/time#Instant'
        context['Interval'] = 'http://www.w3.org/2006/time#Interval'
        context['datetime'] = 'http://www.w3.org/2006/time#inXSDDateTime'
        context['circa'] = 'geojson:circa'
        context['start'] = 'http://www.w3.org/2006/time#hasBeginning'
        context['stop'] = 'http://www.w3.org/2006/time#hasEnding'
        context['when'] = 'geojson:when'
        context['title'] = 'dc-terms:title'
        context['reference-type'] = {'@id': 'oc-gen:reference-type', '@type': '@id'}
        context['inferred'] = 'oc-gen:inferred'
        context['specified'] = 'oc-gen:specified'
        context['reference-uri'] = 'oc-gen:reference-uri'
        context['reference-label'] = 'oc-gen:reference-label'
        context['location-precision'] = 'oc-gen:location-precision'
        context['location-note'] = 'oc-gen:location-note'
        self.context = context


class SearchContext():
    """
    General namespaces used for JSON-LD
    for faceted search
    """

    DOI = 'https://doi.org/10.6078/M7JH3J42'  # DOI for this
    URL = 'https://raw.githubusercontent.com/ekansa/open-context-py/master/json-ld-examples/Search-context.json'

    def __init__(self, id_href=True):
        self.id = self.DOI  # DOI for this
        rp = RootPath()
        base_url = rp.get_baseurl()
        self.href = base_url + '/contexts/search.json'  # URL for this
        if id_href:
            self.id = self.href
        item_context_obj = ItemContext()
        context = item_context_obj.context
        self.geo_json_context = GeneralContext.GEO_JSON_CONTEXT_URI # link to geojson
        context['opensearch'] = 'http://a9.com/-/spec/opensearch/1.1/'
        context['totalResults'] = {'@id': 'opensearch:totalResults', '@type': 'xsd:integer'}
        context['startIndex'] = {'@id': 'opensearch:startIndex', '@type': 'xsd:integer'}
        context['itemsPerPage'] = {'@id': 'opensearch:itemsPerPage', '@type': 'xsd:integer'}
        context['oc-api'] = 'http://opencontext.org/vocabularies/oc-api/'
        context['oai-pmh'] = 'http://www.openarchives.org/OAI/2.0/'
        context['rdfs:isDefinedBy'] = {'@type': '@id'}
        context['first'] = {'@id': 'oc-api:first', '@type': '@id'}
        context['previous'] = {'@id': 'oc-api:previous', '@type': '@id'}
        context['next'] = {'@id': 'oc-api:next', '@type': '@id'}
        context['last'] = {'@id': 'oc-api:last', '@type': '@id'}
        context['first-json'] = {'@id': 'oc-api:first', '@type': '@id'}
        context['previous-json'] = {'@id': 'oc-api:previous', '@type': '@id'}
        context['next-json'] = {'@id': 'oc-api:next', '@type': '@id'}
        context['last-json'] = {'@id': 'oc-api:last', '@type': '@id'}
        context['count'] = {'@id': 'oc-api:count', '@type': 'xsd:integer'}
        self.context = context
