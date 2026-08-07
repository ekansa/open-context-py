
import json
import os
import numpy as np
import re

import warnings

from fastembed import TextEmbedding

from django.conf import settings


# NOTE: this uses the cosine similarity function, which is also configured in the solr
# schema configuration for the dense vector field.


# This is very slow, takes more than a second to make an embedding.
# EMBEDDING_MODEL = "intfloat/multilingual-e5-large"
# EMBEDDING_MODEL_DIM = 1024
SUPRESS_EMBEDDING_WARNINGS = True


ALT_MODEL_CONFIGS = {
    768: {
        'dim': 768,
        # very small token limit 
        # for sentence-transformers/paraphrase-multilingual-mpnet-base-v2
        'max_tokens': 120,
        'model_name': settings.LANGUAGE_MODEL_NAME_768,
        'model_path': settings.LANGUAGE_MODEL_PATH_768,
    },
    1024: {
        'dim': 1024,
        # technically, 512, but let's buffer things a bit
        'max_tokens': 504,
        'model_name': settings.LANGUAGE_MODEL_NAME_1024,
        'model_path': settings.LANGUAGE_MODEL_PATH_1024,
    },
}

MODEL_CONFIGS = {
    1024: {
        'dim': 1024,
        # technically, 512, but let's buffer things a bit
        'max_tokens': 504,
        'model_name': settings.LANGUAGE_MODEL_NAME_1024,
        'model_path': settings.LANGUAGE_MODEL_PATH_1024,
    },
}


def load_language_models(configs=MODEL_CONFIGS):
    """Load language models based on configs"""
    models = {}
    for key, config in configs.items():
        act_model = TextEmbedding(
            config.get('model_name'), 
            specific_model_path=config.get('model_path'),
        )
        act_tokenizer = act_model.model.tokenizer
        new_config = {k:v for k,v in config.items()}
        new_config['model'] = act_model
        new_config['tokenizer'] = act_tokenizer
        models[key] = new_config
    return models


LANGUAGE_MODELS = load_language_models(configs=MODEL_CONFIGS)

EMBEDDING_MODEL_DIM = 1024

ACTIVE_EMBEDDING_MODEL = LANGUAGE_MODELS[EMBEDDING_MODEL_DIM]['model']
# Access the underlying HuggingFace tokenizer used by FastEmbed
ACTIVE_TOKENIZER = LANGUAGE_MODELS[EMBEDDING_MODEL_DIM]['tokenizer']

# our model truncates at 384 tokens, so we will need to chunk in batches of
# 380
MAX_TOKENS = LANGUAGE_MODELS[EMBEDDING_MODEL_DIM]['max_tokens']
CHUCK_TOKEN_OVERLAP = 64
CHUNK_POSITION_DECAY = 0.3

QUERY_PARTS = [
    '"Element" can describe anatomy. "Family" and "order" can be biological classification. ',
    'Used with pottery, the words "fabric" and "ware" can describe ceramic material.',
    '"Excavation Unit", "Locus", "Lot", and "Unit" typically mean archaeological context.',
    'Architecture, walls, floors, pits, ditches, hearths, ovens, and dumps can be features.',
]

# This still fits in the max token length
QUERY_PART = '\n'.join(QUERY_PARTS)

# Add some additional context information to the strings that get made into
# embeddings. Hopefully this will help make "vibe-searches" more sensible!
CLASS_EXPLAIN_DICT = {
    "Animal Bone": """
    This is about animal bone. The word "element" describes anatomy, not a chemical.
    """,
    "Human Bone": """
    This is about human bone. The word "element" describes anatomy, not a chemical.
    """,
    "Plant remains": """
    This is about plant remains. The words "family" and "order" describe biological taxonomy.
    """,
    "Region": """
    This is about a geographic region.
    """,
    "Object": """
    This is about an archaeological artifact.
    """,
    "Coin": """
    This is about an archaeological artifact, usually made of metal, and likely used as currency.
    """,
    "Pottery": """
    This is about an archaeological artifact made of ceramic material.
    This may be a fragmented sherd (shard) or more or less complete and intact vessel.
    The words "fabric" and "ware" describe ceramic material.
    """,
    "Glass": """
    This is about an archaeological artifact made of glass.
    """,
    "Groundstone": """
    This is about an archaeological artifact made of rock, that was shaped by grinding and polishing.
    """,
    "Architectural Element": """
    This is about an component of a building, including decorative features.
    """,
    "Non Diagnostic Bone": """
    This is about bone remains that lack identifying characteristics.
    """,
    "Survey Unit": """
    This is about an area of the Earth"s surface studied for indications of human activity in the past.
    """,
    "Site": """
    This is about a place with indications of human activity in the past. 
    """,
    "Site Area": """
    This is about a part of an archaeological site. 
    A site is a place with indications of human activity in the past. 
    "Site Area", "Area", "Operation", and "Field Project" have similar meanings.
    """,
    "Context": """
    This is about a place that contained or contains physical remains studied by archaeologists. 
    Place, the type of soil, depth, coordinates, stratigraphic layer are often aspects of context. 
    """,
    "Feature": """
    This is about archaeologically observed physical modifications of a place, especially an area of ground.
    Remains of architecture, like walls and floors, but also pits, ditches, hearths, ovens, and dumps can be features.
    """,
    "Structure": """
    This is about a part of architecture or a building. It is an archaeological feature.
    """,
    "Space": """
    This is about a zone or part of architecture or a building. It is an archaeological context.
    """,
    "Excavation Unit": """
    This is about a distinct archaeological context recorded on a dig.
    "Excavation Unit", "Locus", "Lot", and "Unit" typically mean the same thing.
    """,
    "Locus": """
    This is about a distinct archaeological context recorded on a dig.
    "Excavation Unit", "Locus", "Lot", and "Unit" typically mean the same thing.
    """,
    "Lot": """
    This is about a distinct archaeological context recorded on a dig.
    "Excavation Unit", "Locus", "Lot", and "Unit" typically mean the same thing.
    """,
    "Basket": """
    This is about a collection of material from a given archaeological context such as an "Excavation Unit", "Locus", "Lot", or "Unit".
    """,
    "Area": """
    This is about a part of an archaeological site. 
    A site is a place with indications of human activity in the past. 
    "Site Area", "Area", "Operation", and "Field Project" have similar meanings.
    """,
    "Trench": """
    This is about an excavated part of an archaeological site. 
    A trench may contain many different excavated contexts, and each context may be called an "Excavation Unit", "Locus", "Lot", or "Unit". 
    """,
    "Square": """
    This is about a geometrically defined part of an archaeological site. 
    A square is used to help archaeologists to help record the locations of features, deposits, contexts, artifacts, etc. 
    """,
    "Unit": """
    This is about a distinct archaeological context recorded on a dig.
    "Excavation Unit", "Locus", "Lot", and "Unit" typically mean the same thing.
    """,
    "Sequence": """
    This is about a stratigraphic layer. It is an aspect of archaeological context, especially relevant to recording chronology.
    "Sequence", "Stratum", and "Phase" have similar meanings.
    """,
    "Stratum": """
    This is about a stratigraphic layer. It is an aspect of archaeological context, especially relevant to recording chronology.
    "Sequence", "Stratum", and "Phase" have similar meanings.
    """,
    "Phase": """
    This is about a stratigraphic layer. It is an aspect of archaeological context, especially relevant to recording chronology.
    "Sequence", "Stratum", and "Phase" have similar meanings.
    """,
    "Mound": """
    This is about a hill-like part of an archaeological site.
    """,
    "Sample": """
    This is about a very general physical thing collected for study and analysis.
    """,
    "Bulk Ceramic": """
    This is about several items of pottery that are described altogether as a group, not as individual pieces. 
    """,
    "Bulk Lithic": """
    This is about several items of stone that are described altogether as a group, not as individual pieces. 
    """,
    "Sample, Collection, or Aggregation": """
    This is about a very general group of one or more physical things collected for study and analysis.
    """,
    "Reference Collection": """
    This is about a group of well-known and described specimens kept to help identify and compare with newly discovered objects.  
    """,
    "stela": """
    This is about a carved or inscribed stone slab or pillar.
    """,
    "Bone grouping": """
    This is about a group or collection of bone found together.
    """,
    "Biological record": """
    This is about the remains of a living thing, including plants, animals, and humans. 
    This record is also about an ecofact.
    """,
    "Lithic": """
    This is about an artifact made of stone.
    """,
    "Radiocarbon Sample": """
    This is about a specimen of organic material used for radiocarbon dating.
    """,
    "Arbitrary Grouping": """
    This is about a chance grouping of database records. 
    """,
    "Sampling site": """
    This is about a place where sample specimens where obtained. A sampling site may or may not be an archaeological site. 
    """,
    "Collection": """
    This is about a set of physical materials, typically artifacts and samples, stored for study. 
    """,
    "Data Publication": """
    This is about a group of related scientific datasets.
    """,
}


TERM_EXPLAINS = [
    """When used with bones, the term "element" generally describes the anatomical name of a type of bone, 
    not a chemical.
    """,
    """Used with pottery, the words "fabric" and "ware" further describe ceramic material."""
]


GENERAL_PASSAGE_STR = """
This is a data record from scientific research.
Creators and contributors authored this data record.
Subjects generally describe the database that contains this record. 
"""

GENERAL_PASSAGE_DATA_PUB_STR = """
This is scientific research project.
Creators and contributors authored this data record.
Subjects generally describe the database that contains this record. 
"""


def prepare_text_str_for_index_embedding(text_field_str):
    """Prepares the text field as a set of passages for an embedding"""
    padded_text_field_str = re.sub(r"<.*?>", "", text_field_str)
    orig_lines = padded_text_field_str.split("\n")
    lines = [l for l in orig_lines if len(l) > 0]
    embedding_str = "\n".join(lines)
    return embedding_str


def chunk_tokens(token_ids, max_tokens, overlap):
    stride = max_tokens - overlap
    for start in range(0, len(token_ids), stride):
        end = min(start + max_tokens, len(token_ids))
        yield token_ids[start:end]
        if end >= len(token_ids):
            break


def chunk_text_for_embedding(
    embedding_str,
    max_tokens=MAX_TOKENS,
    tokenizer=ACTIVE_TOKENIZER,
    overlap=CHUCK_TOKEN_OVERLAP,
):
    """Pack lines into chunks when possible; slide a token window for long lines."""
    token_ids = tokenizer.encode(embedding_str).ids
    if len(token_ids) <= max_tokens:
        return [embedding_str]

    chunks = []
    current_lines = []

    def flush_current_lines():
        if current_lines:
            chunks.append("\n".join(current_lines))

    def append_token_window_chunks(text):
        for window_ids in chunk_tokens(tokenizer.encode(text).ids, max_tokens, overlap):
            chunks.append(tokenizer.decode(window_ids))

    for line in embedding_str.split("\n"):
        line_token_len = len(tokenizer.encode(line).ids)
        if line_token_len > max_tokens:
            flush_current_lines()
            current_lines = []
            append_token_window_chunks(line)
            continue

        candidate_lines = current_lines + [line]
        candidate_token_len = len(tokenizer.encode("\n".join(candidate_lines)).ids)
        if current_lines and candidate_token_len > max_tokens:
            flush_current_lines()
            current_lines = [line]
        else:
            current_lines = candidate_lines

    flush_current_lines()
    return chunks


def position_decay_weights(num_chunks, decay=CHUNK_POSITION_DECAY):
    weights = np.exp(-decay * np.arange(num_chunks))
    return weights / weights.sum()


def embed_with_chunk_pooling(
    embedding_str: str,
    embedding_str_list=None,
    max_tokens: int = MAX_TOKENS,
    embedding_model=ACTIVE_EMBEDDING_MODEL,
    tokenizer=ACTIVE_TOKENIZER,
    overlap=CHUCK_TOKEN_OVERLAP,
    position_decay=CHUNK_POSITION_DECAY,
    add_query_part=False,
) -> list:
    """Embed long text via line-aware chunking and position-weighted pooling.

    Chunks respect the model token limit (384 for mpnet; we use max_tokens=380).
    Line boundaries are preserved when possible; overlong lines use a sliding
    token window. Chunk embeddings are L2-normalized, pooled with exponential
    decay weights that favor earlier chunks, then re-normalized for cosine kNN.
    """
    
    if embedding_str and not embedding_str_list:
        embedding_str_list = [embedding_str]

    chunks_text = []

    for embedding_str in embedding_str_list:
        chunks_text += chunk_text_for_embedding(
            embedding_str,
            max_tokens=max_tokens,
            tokenizer=tokenizer,
            overlap=overlap,
        )

    if False and add_query_part:
        # add the general background information later, so they influence the
        # query embedding, but get weighted less than the actual user query.
        chunks_text.append(QUERY_PART)

    chunk_embeddings = list(embedding_model.embed(chunks_text))
    chunk_embeddings_matrix = np.array(chunk_embeddings)

    norms = np.linalg.norm(chunk_embeddings_matrix, axis=1, keepdims=True)
    norms = np.where(norms > 0, norms, 1)
    chunk_embeddings_matrix = chunk_embeddings_matrix / norms

    weights = position_decay_weights(len(chunks_text), decay=position_decay)
    pooled_embedding = (chunk_embeddings_matrix * weights[:, np.newaxis]).sum(axis=0)

    norm = np.linalg.norm(pooled_embedding)
    if norm > 0:
        pooled_embedding = pooled_embedding / norm

    return pooled_embedding.flatten().tolist()


def make_vectorized_embedding_query_str(
    str_to_vectorize,
    embedding_model=ACTIVE_EMBEDDING_MODEL,
):
    if not str_to_vectorize:
        return None
    embedding = embed_with_chunk_pooling(
        str(str_to_vectorize),
        embedding_model=embedding_model,
        add_query_part=True,
    )
    return json.dumps(embedding)




