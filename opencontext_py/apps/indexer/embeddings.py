
import numpy as np
import re

import warnings

from fastembed import TextEmbedding

EMBEDDING_MODEL = 'sentence-transformers/paraphrase-multilingual-mpnet-base-v2'
EMBEDDING_MODEL_DIM = 768
SUPRESS_EMBEDDING_WARNINGS = True



ACTIVE_EMBEDDING_MODEL = TextEmbedding(EMBEDDING_MODEL)
# Access the underlying HuggingFace tokenizer used by FastEmbed
ACTIVE_TOKENIZER = ACTIVE_EMBEDDING_MODEL.model.tokenizer


def prepare_text_str_for_index_embedding(text_field_str):
    """Prepares the text field as a set of passages for an embedding"""
    text_field_str = re.sub(r"<.*?>", "", text_field_str)
    orig_lines = text_field_str.split('\n')
    lines = [l for l in orig_lines if len(l) > 0]
    embedding_str = '\n'.join(lines)
    return f'passage:{embedding_str}'


def embed_with_chunk_pooling(
    embedding_str: str,
    max_tokens: int = 500,
    embedding_model=ACTIVE_EMBEDDING_MODEL,
    tokenizer=ACTIVE_TOKENIZER,
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




