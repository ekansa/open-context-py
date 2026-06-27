
import json
import numpy as np
import re

import warnings

from fastembed import TextEmbedding



# NOTE: this uses the cosine similarity function, which is also configured in the solr
# schema configuration for the dense vector field.
EMBEDDING_MODEL = 'sentence-transformers/paraphrase-multilingual-mpnet-base-v2'
EMBEDDING_MODEL_DIM = 768
SUPRESS_EMBEDDING_WARNINGS = True



ACTIVE_EMBEDDING_MODEL = TextEmbedding(EMBEDDING_MODEL)
# Access the underlying HuggingFace tokenizer used by FastEmbed
ACTIVE_TOKENIZER = ACTIVE_EMBEDDING_MODEL.model.tokenizer


# Add some additional context information to the strings that get made into
# embeddings. Hopefully this will help make "vibe-searches" more sensible!
CLASS_EXPLAIN_DICT = {
    'Animal Bone': """
    An 'Animal Bone' record category describes a specimen of bone (and sometimes tooth or antler) material
    from a dead animal.
    When used with bones, the term "element" generally describes the anatomical name of a type of bone, 
    not a chemical. Zooarchaeologists and archaeozoologists study animal bones.
    """,
    'Human Bone': """
    An 'Human Bone' record category describes a specimen of bone (and sometimes tooth) material
    from a dead person.
    When used with bones, the term "element" generally describes the anatomical name of a type of bone, 
    not a chemical.
    """,
    'Plant remains': """
    An 'Plant remains' record category describes botanical specimen usually described by a botanist,
    or an ethnobotanist, or an archaeobotanist. 
    When used with plant remains, the terms "family" and "order" generally describe biological taxonomy.
    """,
    'Region': """
    When record category is a region, it describes a geographic region.
    """,
    'Object': """
    An 'Object' record category typically means an archaeological artifact.
    """,
    'Coin': """
    A 'Coin' record category describes an archaeological artifact, usually made of metal, and likely used as currency.
    """,
    'Pottery': """
    A 'Pottery' record category describes an archaeological artifact made of ceramic material.
    A pottery may describe a broken and fragmented as a sherd (shard) or more or less complete and intact vessel.
    """,
    'Glass': """
    A 'Glass' record category describes an archaeological artifact made of glass.
    """,
    'Groundstone': """
    A 'Groundstone' record category describes an archaeological artifact made of rock, 
    that was shaped by grinding and polishing.
    """,
    'Architectural Element': """
    An 'Architectural Element' record category describes a component of a building, 
    including decorative features.
    """,
    'Non Diagnostic Bone': """
    A 'Non Diagnostic Bone' record category describes bone remains that lack identifying characteristics.
    """,
    'Survey Unit': """
    A 'Survey Unit' record category describes an area of the Earth's surface studied for indications
    of human activity in the past.
    """,
    'Site': """
    A 'Site' record category describes a place with indications of human activity in the past. 
    """,
    'Site Area': """
    A 'Site Area' record category describes a part of an archaeological site. 
    A site is a place with indications of human activity in the past. 
    'Site Area', 'Area', 'Operation', and 'Field Project' have similar meanings.
    """,
    'Context': """
    A 'Context' record category describes a place that contained or contains physical remains studied 
    by archaeologists. Place, the type of soil, depth, coordinates, stratigraphic layer are often 
    aspects of context. 
    """,
    'Feature': """
    A 'Feature' record category describes archaeologically observed physical modifications of a place, 
    especially an area of ground. Remains of architecture, like walls and floors, but also pits, 
    ditches, hearths, ovens, and dumps can be features.
    """,
    'Structure': """
    A 'Structure' record category describes a part of architecture or a building. It is a type of 
    archaeological feature.
    """,
    'Space': """
    A 'Space' record category describes a zone or part of architecture or a building. It is a type of 
    archaeological context.
    """,
    'Excavation Unit': """
    A 'Excavation Unit' record category describes a distinct archaeological context recorded on a dig.
    'Excavation Unit', 'Locus', 'Lot', and 'Unit' typically mean the same thing.
    """,
    'Locus': """
    A 'Locus' record category describes a distinct archaeological context recorded on a dig.
    'Excavation Unit', 'Locus', 'Lot', and 'Unit' typically mean the same thing.
    """,
    'Lot': """
    A 'Lot' record category describes a distinct archaeological context recorded on a dig.
    'Excavation Unit', 'Locus', 'Lot', and 'Unit' typically mean the same thing.
    """,
    'Basket': """
    A 'Basket' record category describes a collection of material from a given archaeological context
    such as an 'Excavation Unit', 'Locus', 'Lot', or 'Unit'.
    """,
    'Area': """
    An 'Area' record category describes a part of an archaeological site. 
    A site is a place with indications of human activity in the past. 
    'Site Area', 'Area', 'Operation', and 'Field Project' have similar meanings.
    """,
    'Trench': """
    A 'Trench' record category describes an excavated part of an archaeological site. 
    A trench may contain many different excavated contexts, and each context may
    be called an 'Excavation Unit', 'Locus', 'Lot', or 'Unit'. 
    """,
    'Square': """
    A 'Square' record category describes geometrically defined part of an archaeological site. 
    A square is used to help archaeologists to help record the locations of
    features, deposits, contexts, artifacts, etc. 
    """,
    'Unit': """
    A 'Unit' record category describes a distinct archaeological context recorded on a dig.
    'Excavation Unit', 'Locus', 'Lot', and 'Unit' typically mean the same thing.
    """,
    'Sequence': """
    A 'Sequence' record category describes a stratigraphic layer. It is an aspect of archaeological 
    context, especially relevant to recording chronology.
    'Sequence', 'Stratum', and 'Phase' have similar meanings.
    """,
    'Stratum': """
    A 'Stratum' record category describes a stratigraphic layer. It is an aspect of archaeological 
    context, especially relevant to recording chronology.
    'Sequence', 'Stratum', and 'Phase' have similar meanings.
    """,
    'Phase': """
    A 'Phase' record category describes a stratigraphic layer. It is an aspect of archaeological 
    context, especially relevant to recording chronology.
    'Sequence', 'Stratum', and 'Phase' have similar meanings.
    """,
    'Mound': """
    A 'Mound' record category describes a hill-like part of an archaeological site.
    """,
    'Sample': """
    A 'Sample' record category describes a very general physical thing collected for study and 
    analysis.
    """,
    'Bulk Ceramic': """
    A 'Bulk Ceramic' record category describes several items of pottery that are described 
    altogether as a group, not as individual pieces. 
    """,
    'Bulk Lithic': """
    A 'Bulk Lithic' record category describes several items of stone that are described 
    altogether as a group, not as individual pieces. 
    """,
    'Sample, Collection, or Aggregation': """
    A 'Sample, Collection, or Aggregation' record category describes a very general 
    group of one or more physical things collected for study and analysis.
    """,
    'Reference Collection': """
    A 'Reference Collection' record category describes a group of well-known and described specimens
    kept to help identify and compare with newly discovered objects.  
    """,
    'stela': """
    A 'stela' record category describes type carved or inscribed stone slab or pillar.
    """,
    'Bone grouping': """
    A 'Bone grouping' record category describes a group or collection of bone found together.
    """,
    'Biological record': """
    A 'Biological record' record category describes the remains or trace of a living thing, including
    plants, animals, and humans. 'Biological record' and 'ecofact' have similar meanings.
    """,
    'Lithic': """
    A 'Lithic' record category describes an artifact made of stone.
    """,
    'Radiocarbon Sample': """
    A 'Radiocarbon Sample' record category describes a specimen of organic material used for
    radiocarbon dating.
    """,
    'Arbitrary Grouping': """
    A 'Arbitrary Grouping' record category describes a random and meaningless grouping 
    of database records. 
    """,
    'Sampling site': """
    A 'Sampling site' record category describes a place where sample specimens where obtained. A
    sampling site may or may not be an archaeological site. 
    """,
    'Collection': """
    A 'Collection' record category describes a set of physical materials, typically artifacts 
    and samples, stored for study. 
    """,
    'Data Publication': """
    A 'Data Publication' record category describes one more datasets submitted by a researcher, a 
    team of researchers, or an organization for sharing and archiving. Data publications can
    contain many different types of data records and digital media like images and 3D models.
    """,
}



START_PASSAGE_STR = """
This is a data record from a scientific research project or collection that described 
and cataloged physical remains of the human past.
Creators and contributors are people that helped to author this data record.
Subjects provide general descriptions of the database that contains this record. 
"""

START_PASSAGE_DATA_PUB_STR = """
This is scientific research project or collection that described 
and cataloged physical remains of the human past.
Creators and contributors are people that helped to author this data record.
Subjects provide general descriptions of the database that contains this record. 
"""


def prepare_text_str_for_index_embedding(text_field_str, item_class_label=None):
    """Prepares the text field as a set of passages for an embedding"""
    text_field_str = re.sub(r"<.*?>", "", text_field_str)
    class_explain = ''
    if item_class_label:
        class_explain = CLASS_EXPLAIN_DICT.get(item_class_label, '')
    start_str = START_PASSAGE_STR
    if item_class_label == 'Data Publication':
        start_str = START_PASSAGE_DATA_PUB_STR
    padded_text_field_str = (
        start_str
        + f'\n{class_explain}'
        + f'\n{text_field_str}'
    )
    orig_lines = padded_text_field_str.split('\n')
    lines = [l for l in orig_lines if len(l) > 0]
    embedding_str = '\n'.join(lines)
    return f'passage: {embedding_str}'


def embed_with_chunk_pooling(
    embedding_str: str,
    max_tokens: int = 500,
    embedding_model=ACTIVE_EMBEDDING_MODEL,
    tokenizer=ACTIVE_TOKENIZER,
    chunk_prefix='passage: '
) -> list:
    """Chunks a long text by its token representation, generates embeddings

    for each chunk using FastEmbed, and mean-pools them into a single vector.
    """
    # Encode the entire text to token IDs
    tokens = tokenizer.encode(embedding_str)
    token_ids = tokens.ids

    # If the text fits in a single chunk, embed it directly
    if len(token_ids) <= max_tokens:
        embeddings_generator = embedding_model.embed([embedding_str])
        embeddings_list = list(embeddings_generator)
        embedding = embeddings_list[0].flatten().tolist()
        return embedding

    # Split the token IDs into blocks of `max_tokens`
    chunks_text = []
    for i in range(0, len(token_ids), max_tokens):
        chunk_ids = token_ids[i : i + max_tokens]
        # Decode token IDs back into string pieces
        chunk_str = tokenizer.decode(chunk_ids)
        if not chunk_str.startswith(chunk_prefix):
            # make sure the chuck has the chunk prefix
            chunk_str = chunk_prefix + chunk_str
            # print('Added prefix to long text for embedding') 
        chunks_text.append(chunk_str)

    # Generate embeddings for all chunks in a single batched pass
    chunk_embeddings = list(embedding_model.embed(chunks_text))

    # Convert to a 2D NumPy array -> Shape: (num_chunks, 768)
    chunk_embeddings_matrix = np.array(chunk_embeddings)

    # Apply Mean Pooling across the chunk axis (axis=0)
    # This averages out the features to return a single (768,) vector
    pooled_embedding = np.mean(chunk_embeddings_matrix, axis=0)

    # Normalize the final vector to maintain cosine similarity invariants
    norm = np.linalg.norm(pooled_embedding)
    if norm > 0:
        pooled_embedding = pooled_embedding / norm

    return pooled_embedding.flatten().tolist()


def make_vectorized_embedding_query_str(str_to_vectorize, embedding_model=ACTIVE_EMBEDDING_MODEL):
    if not str_to_vectorize:
        return None
    embedding_str = str(str_to_vectorize)
    if not embedding_str.startswith('query:'):
        embedding_str = 'query: ' + embedding_str
    embedding = embed_with_chunk_pooling(embedding_str, chunk_prefix='query: ')  
    return json.dumps(embedding)




