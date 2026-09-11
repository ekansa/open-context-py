
import json
import numpy as np
import re
from scipy.spatial.distance import cosine

import warnings

from opencontext_py.apps.indexer.embeddings import (
    embed_with_chunk_pooling
)

"""
NOTES: use the period-o dataset to get structured data
of periods and regions. 

* The regions have Wikidata URIs so we can get geographic
extent, and get a bounding box. 
* The periods have start and end dates that we can use to for queries to 
Open Context.

Those elements of structured data will help compose search filters.

We associate embeddings of the text descriptions of periods, including their
time period name and their geographic places


embedding_str = (
    'Time Period: Constantinian dynasty (Roman Noricum) \n'
    'Geographic Places: Noricum | Austria | Italy | Slovenia | Roman Empire | Germany'
)

that string will have some time range 307 - 364 and be associated with a bounding box.
We can store Open Context query parameters with it:

{
    'bbox': 'sw-lon,sw-lat,ne-lon,ne-lat',
    'allevent-start': 307,
    'allevent-end': 364,
}


depending on the cosine similarity score, we can chose to use the query parameters
associated with an embedding or not.


TODO: experiment with combing period o periods and regions with Open Context
item_categories (Animal bone, object, etc.) to generate strings who's embeddings
can be compared with user queries to generate search parameters.

Think about looping. We can take the top 20 or so embedding texts with different
types of query parameters. by combining those texts with different query parameters into
longer embedding texts, we can test the best scores for the combined embeddings.


"""


def get_similarity_between_embeddings(e1, e2):
    """Get a similarity score between two embeddings"""
    v1 = np.array(e1)
    v2 = np.array(e2)
    return 1 - cosine(v1, v2)


def get_difference_between_embeddings(e1, e2):
    """Get a difference distance between two embeddings"""
    v1 = np.array(e1)
    v2 = np.array(e2)
    return cosine(v1, v2)


def get_similarity_scores_for_strs(
    embedding_str_1, 
    embedding_str_2,
    embedding_str_list_1=[],
    embedding_str_list_2=[],
):
    if not embedding_str_list_1 and embedding_str_1:
        embedding_str_list_1 = [embedding_str_1]
    if not embedding_str_list_2 and embedding_str_2:
        embedding_str_list_2 = [embedding_str_2]
    e1 = embed_with_chunk_pooling(
        embedding_str=None,
        embedding_str_list=embedding_str_list_1,
    )
    e2 = embed_with_chunk_pooling(
        embedding_str=None,
        embedding_str_list=embedding_str_list_2,
    )
    return get_similarity_between_embeddings(e1, e2)




