from opencontext_py.libs.general import LastUpdatedOrderedDict


class ItemNamespaces():
    """
    General namespaces used for JSON-LD
    """
    def __init__(self):
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
        self.namespaces = context
