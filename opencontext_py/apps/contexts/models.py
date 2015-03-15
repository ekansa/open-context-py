from opencontext_py.libs.rootpath import RootPath
from opencontext_py.libs.general import LastUpdatedOrderedDict


class ItemContext():
    """
    General namespaces used for JSON-LD
    for Items
    """
    DOI = 'http://dx.doi.org/10.6078/M7P848VC'  # DOI for this

    def __init__(self, id_href=True):
        self.id = self.DOI  # DOI for this
        rp = RootPath()
        base_url = rp.get_baseurl()
        self.href = base_url + '/contexts/item.json'  # URL for this
        if id_href:
            self.id = self.href
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
        context['geojson'] = 'http://ld.geojson.org/vocab#'
        context['cc'] = 'http://creativecommons.org/ns#'
        context['oc-gen'] = 'http://opencontext.org/vocabularies/oc-general/'
        context['oc-pred'] = 'http://opencontext.org/predicates/'
        context['id'] = '@id'
        context['label'] = 'rdfs:label'
        context['uuid'] = 'dc-terms:identifier'
        context['slug'] = 'oc-gen:slug'
        context['type'] = '@type'
        context['category'] = {'@id': 'oc-gen:category', '@type': '@id'}
        context['Feature'] = 'geojson:Feature'
        context['FeatureCollection'] = 'geojson:FeatureCollection'
        context['GeometryCollection'] = 'geojson:GeometryCollection'
        context['Instant'] = 'http://www.w3.org/2006/time#Instant'
        context['Interval'] = 'http://www.w3.org/2006/time#Interval'
        context['LineString'] = 'geojson:LineString'
        context['MultiLineString'] = 'geojson:MultiLineString'
        context['MultiPoint'] = 'geojson:MultiPoint'
        context['MultiPolygon'] = 'geojson:MultiPolygon'
        context['Point'] = 'geojson:Point'
        context['Polygon'] = 'geojson:Polygon'
        context['bbox'] = {'@id': 'geojson:bbox', '@container': '@list'}
        context['circa'] = 'geojson:circa'
        context['coordinates'] = 'geojson:coordinates'
        context['datetime'] = 'http://www.w3.org/2006/time#inXSDDateTime'
        context['description'] = 'dc-terms:description'
        context['features'] = {'@id': 'geojson:features', '@container': '@set'}
        context['geometry'] = 'geojson:geometry'
        context['properties'] = 'geojson:properties'
        context['start'] = 'http://www.w3.org/2006/time#hasBeginning'
        context['stop'] = 'http://www.w3.org/2006/time#hasEnding'
        context['title'] = 'dc-terms:title'
        context['when'] = 'geojson:when'
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

    DOI = 'http://dx.doi.org/10.6078/M7JH3J42'  # DOI for this

    def __init__(self, id_href=True):
        self.id = self.DOI  # DOI for this
        rp = RootPath()
        base_url = rp.get_baseurl()
        self.href = base_url + '/contexts/search.json'  # URL for this
        if id_href:
            self.id = self.href
        item_context_obj = ItemContext()
        context = item_context_obj.context
        context['opensearch'] = 'http://a9.com/-/spec/opensearch/1.1/'
        context['totalResults'] = {'@id': 'opensearch:totalResults', '@type': 'xsd:integer'}
        context['startIndex'] = {'@id': 'opensearch:startIndex', '@type': 'xsd:integer'}
        context['itemsPerPage'] = {'@id': 'opensearch:itemsPerPage', '@type': 'xsd:integer'}
        context['oc-api'] = 'http://opencontext.org/vocabularies/oc-api/'
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