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


from opencontext_py.apps.indexer.solrdocument_slim_schema import (
    EMBEDDING_MODEL,
    EMBEDDING_FIELD_SOLR,
    SUPRESS_EMBEDDING_WARNINGS,
    SolrDocumentSlim
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

solr_response = vibe_search('artifact used for spinning threads')
items = solr_response.get('response', {}).get('docs')

solr_response = vibe_search('remains from feasting on pork')
items = solr_response.get('response', {}).get('docs')
'''


if settings.DEBUG:
    SEARCH_CACHE_TIMEOUT = 60 # 1 minute
else:
    SEARCH_CACHE_TIMEOUT = 60 * 60 * 24 * 7 # 1 week


TOP_K_DOCUMENTS = 10
# Activate an embedding model
ACTIVE_EMBEDDING_MODEL = TextEmbedding(EMBEDDING_MODEL)


# --------------------------------------------------------------------
# NOTE: These functions provide a simple general purpose means to search
# Solr and cache search results.
# --------------------------------------------------------------------

def get_solr_connection():
    """ Connects to solr """
    solr =  SolrClient(use_alt_collection=True, ).solr
    return solr


def make_vectorized_embedding_str(str_to_vectorize, embedding_model=ACTIVE_EMBEDDING_MODEL):
    if not str_to_vectorize:
        return None
    str_to_vectorize = str(str_to_vectorize)
    if not embedding_model:
        if SUPRESS_EMBEDDING_WARNINGS:
            with warnings.catch_warnings(action="ignore"):
                embedding_model = TextEmbedding(EMBEDDING_MODEL)
        else:
            embedding_model = TextEmbedding(EMBEDDING_MODEL)
    embedding_text = re.sub(r"<.*?>", "", str_to_vectorize)
    embedding_text = 'query: ' + embedding_text
    documents = [embedding_text]
    embeddings_generator = embedding_model.embed(documents)
    embeddings_list = list(embeddings_generator)
    embedding = embeddings_list[0]
    return json.dumps(embedding.flatten().tolist())


def add_str_to_vector_to_solr_query(str_to_vectorize, solr_query={}):
    """adds a prompt term to a solr query"""
    embedding_str =  make_vectorized_embedding_str(str_to_vectorize)
    if not embedding_str:
        return solr_query
    q_str = '{!knn f= ' + EMBEDDING_FIELD_SOLR + ' topK=' + str(TOP_K_DOCUMENTS) + '}' + embedding_str
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
