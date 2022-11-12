import copy
import json

from opencontext_py.apps.all_items import configs
from opencontext_py.apps.all_items.project_contexts.context import get_cache_project_context_df


PROJ_NAMESPACES_DICT = {
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
    "geojson": "https://purl.org/geojson/vocab#",
    "cc": "http://creativecommons.org/ns#",
    "nmo": "http://nomisma.org/ontology#",
    "oc-gen": "http://opencontext.org/vocabularies/oc-general/",
    "oc-pred": "http://opencontext.org/predicates/",
}

PROJ_NAMESPACE_KEYS = [k for k,_ in PROJ_NAMESPACES_DICT.items()]

PROJ_MORE_CONTEXT_DICT = {
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
    "rdf:HTML": {
        "@container": "@language"
    },
    "skos:note": {
        "@container": "@language"
    },
}

PROJ_STANDARD_CONTEXT_DICT = {**PROJ_NAMESPACES_DICT, **PROJ_MORE_CONTEXT_DICT}


def in_known_namspace_prefix(item_key):
    for namespace_key in PROJ_NAMESPACE_KEYS:
        if item_key.startswith(f'{namespace_key}:'):
            return True
    return False


def make_web_uri(item_type, uri):
    if item_type in configs.OC_ITEM_TYPES:
        return f'https://{uri}'
    return f'http://{uri}'


def make_json_ld_id(item_type, slug, uri, item_key=None):
    """Makes the main ID for of an item for use in JSON-LD"""
    if item_type == 'predicates':
        return f'oc-pred:{slug}'
    if item_key and in_known_namspace_prefix(item_key):
        return item_key
    return make_web_uri(item_type, uri)


def make_project_context_json_ld(project_id, add_df_json=False):
    df = get_cache_project_context_df(project_id)
    context = copy.deepcopy(PROJ_STANDARD_CONTEXT_DICT)
    graph = []
    for item_type in ['predicates', 'types']:
        item_type_index = df['subject__item_type'] == item_type
        for i, row in df[item_type_index].iterrows():
            uuid_index = df['subject_id'] == row['subject_id']
            label = df[uuid_index]['subject__label'].iloc[0]
            uri = df[uuid_index]['subject__uri'].iloc[0]
            slug = df[uuid_index]['subject__slug'].iloc[0]
            data_type = df[uuid_index]['subject__data_type'].iloc[0]
            if data_type == 'id':
                data_type = '@id'
            id_key = make_json_ld_id(
                item_type=item_type,
                slug=slug,
                uri=uri,
            )
            if item_type == 'predicates':
                context_item = {
                    '@type': data_type,
                }
                # A predicates item_type is added to the context object.
                context[id_key] = context_item
                graph_item = {
                    'id': id_key,
                    'label': label,
                    'owl:sameAs': f'https://{uri}',
                }
            else:
                # We only add item_types types to the graph, not the context.
                graph_item = {
                    'id': id_key,
                    'label': label,
                }
            rel_pred_index = (
                uuid_index
                & ~df['predicate__uri'].isnull()
                & ~(df['object_id'] == configs.DEFAULT_NULL_OBJECT_UUID)
            )
            for rel_pred_uri in df[rel_pred_index]['predicate__uri'].unique().tolist():
                uuid_pred_index = (uuid_index & (df['predicate__uri'] == rel_pred_uri))
                pred_key = make_json_ld_id(
                    item_type=df[uuid_pred_index]['predicate__item_type'].iloc[0],
                    slug=df[uuid_pred_index]['predicate__slug'].iloc[0],
                    uri=rel_pred_uri,
                    item_key=df[uuid_pred_index]['predicate__item_key'].iloc[0]
                )
                graph_item[pred_key] = []
                for _, obj_row in df[uuid_pred_index].iterrows():
                    obj_index = df['object__slug'] == obj_row['object__slug']
                    obj_uri = make_web_uri(
                        item_type=df[obj_index]['object__item_type'].iloc[0],
                        uri=df[obj_index]['object__uri'].iloc[0],
                    )
                    obj_id = make_json_ld_id(
                        item_type=df[obj_index]['object__item_type'].iloc[0],
                        slug=df[obj_index]['object__slug'].iloc[0],
                        uri=df[obj_index]['object__uri'].iloc[0],
                        item_key=df[obj_index]['object__item_key'].iloc[0]
                    )
                    if df[(df['subject__slug'] == obj_row['object__slug'])].empty:
                        obj_dict = {
                            'id': obj_id,
                            'label': df[obj_index]['object__label'].iloc[0],
                        }
                        if not in_known_namspace_prefix(obj_id) and obj_id != obj_uri:
                            obj_dict['owl:sameAs'] = obj_uri
                    else:
                        # We have an object that is defined elsewhere in the df, so just point to it.
                        obj_dict = {
                            'id': obj_id,
                        }
                    graph_item[pred_key].append(obj_dict)
            graph.append(graph_item)
    json_ld = {
        '@context': context,
        '@graph': graph,
    }
    if add_df_json:
        df_json = df.to_json(orient='records')
        df_json_obj = json.loads(df_json)
        json_ld['df'] = df_json_obj[:20]
    return json_ld, df