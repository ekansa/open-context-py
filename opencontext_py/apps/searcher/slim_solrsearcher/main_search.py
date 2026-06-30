import copy
import json
import logging
import re
import time

import warnings

from fastembed import TextEmbedding

from django.conf import settings
from django.core.cache import caches

from opencontext_py.libs.rootpath import RootPath

from opencontext_py.apps.indexer.embeddings import (
    make_vectorized_embedding_query_str
)
from opencontext_py.apps.indexer.solrdocument_slim_schema import (
    EMBEDDING_FIELD_SOLR,
)

from opencontext_py.libs.solrclient import SolrClient

from opencontext_py.libs.queue_utilities import make_hash_id_from_args

logger = logging.getLogger(__name__)



'''
import importlib
import logging
from opencontext_py.apps.all_items.models import (
    AllManifest,
    AllAssertion,
    AllIdentifier,
)
from opencontext_py.apps.all_items import configs
from opencontext_py.apps.searcher.slim_solrsearcher.main_search import vibe_search

solr_response = vibe_search('remains of a cow')
items = solr_response.get('response', {}).get('docs')
print(items[0]['text'])

solr_response = vibe_search('remains of a giant bull')
items = solr_response.get('response', {}).get('docs')
print(items[0]['text'])

solr_response = vibe_search('a cute little bunny')
items = solr_response.get('response', {}).get('docs')
print(items[0]['text'])
print(items[1]['text'])

solr_response = vibe_search('a hip bone')
items = solr_response.get('response', {}).get('docs')
print(items[0]['text'])

solr_response = vibe_search('an arm bone')
items = solr_response.get('response', {}).get('docs')
print(items[0]['text'])

solr_response = vibe_search('artifact used for spinning threads')
items = solr_response.get('response', {}).get('docs')
print(items[0]['text'])

solr_response = vibe_search('remains from feasting on pork')
items = solr_response.get('response', {}).get('docs')
print(items[0]['text'])

solr_response = vibe_search('artifact from Italy used in making clothing')
items = solr_response.get('response', {}).get('docs')
print(items[0]['text'])

solr_response = vibe_search('artifact from Italy used as a spool')
items = solr_response.get('response', {}).get('docs')
print(items[0]['text'])

solr_response = vibe_search('daily life in ancient Egypt')
items = solr_response.get('response', {}).get('docs')
print(items[0]['text'])

solr_response = vibe_search('food in ancient Egypt')
items = solr_response.get('response', {}).get('docs')
print(items[0]['text'])

solr_response = vibe_search('has the image of a greek god')
items = solr_response.get('response', {}).get('docs')
print(items[0]['text'])

solr_response = vibe_search('evidence of office work')
items = solr_response.get('response', {}).get('docs')
print(items[0]['text'])

solr_response = vibe_search('artifact from Italy used in making textiles. DOT include anything relating to involving pottery vessels')
items = solr_response.get('response', {}).get('docs')
print(items[0]['text'])

solr_response = vibe_search('artifact from Tuscany used in making textiles.')
items = solr_response.get('response', {}).get('docs')
print(items[0]['text'])

solr_response = vibe_search('spindle whorl object from Poggio Civitate used in making textiles.')
items = solr_response.get('response', {}).get('docs')
print(items[0]['text'])

# Arabic for "lamb shank"
solr_response = vibe_search('موزة لحم الضأن')
items = solr_response.get('response', {}).get('docs')
print(items[0]['text'])

solr_response = vibe_search('leg of lamb')
items = solr_response.get('response', {}).get('docs')
print(items[0]['text'])

solr_response = vibe_search('a medusa head')
items = solr_response.get('response', {}).get('docs')
print(items[0]['text'])

solr_response = vibe_search('a bronze age house')
items = solr_response.get('response', {}).get('docs')
print(items[0]['text'])

'''


if settings.DEBUG:
    SEARCH_CACHE_TIMEOUT = 60 # 1 minute
else:
    SEARCH_CACHE_TIMEOUT = 60 * 60 * 24 * 7 # 1 week


TOP_K_DOCUMENTS = 20
VECTOR_MIN_RETURN = 0.5


# --------------------------------------------------------------------
# NOTE: These functions provide a simple general purpose means to search
# Solr and cache search results.
# --------------------------------------------------------------------

def get_solr_connection():
    """ Connects to solr """
    solr =  SolrClient(use_alt_collection=True, ).solr
    return solr


def add_str_to_vector_to_solr_query(str_to_vectorize, solr_query={}):
    """adds a prompt term to a solr query"""
    embedding_str =  make_vectorized_embedding_query_str(str_to_vectorize)
    if not embedding_str:
        return solr_query
    q_str = '{!knn f=' + EMBEDDING_FIELD_SOLR + ' topK=' + str(TOP_K_DOCUMENTS) + '}' + embedding_str
    # q_str = '{!vectorSimilarity f=' + EMBEDDING_FIELD_SOLR + ' minReturn=' + str(VECTOR_MIN_RETURN) + '}' + embedding_str
    solr_query['q'] = q_str
    return solr_query


def vibe_search(str_to_vectorize, solr_query={}):
    solr_query = add_str_to_vector_to_solr_query(str_to_vectorize, solr_query=solr_query)
    solr = get_solr_connection()
    try:
        results = solr.search(**solr_query)
        solr_response = results.raw_response
    except Exception as error:
        solr_response = None
        if settings.DEBUG:
            # Print the query problem if in debug mode
            print(solr_query)
            print(str(error))
    return solr_response
