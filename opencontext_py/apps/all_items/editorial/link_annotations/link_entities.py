import copy
from re import sub

import pandas as pd

from django.db.models import Q
from django.utils import timezone

from opencontext_py.apps.all_items import configs
from opencontext_py.apps.all_items.models import (
    AllManifest,
    AllAssertion,
)
from opencontext_py.apps.all_items import models_utils
from opencontext_py.apps.all_items.editorial.link_annotations import utilities



"""
Example use.

import importlib
from pathlib import Path
from opencontext_py.apps.all_items.editorial.link_annotations import link_entities
importlib.reload(link_entities)

HOME = str(Path.home())
csv_path = f'{HOME}/data-dumps/oc-uberon.csv'

df = link_entities.make_ld_entities_for_vocab_csv(
    csv_path=csv_path, 
    vocab_uri='uberon.org',
)

csv_path = f'{HOME}/data-dumps/oc-aat.csv'
df = link_entities.make_ld_entities_for_vocab_csv(
    csv_path=csv_path, 
    vocab_uri='vocab.getty.edu/aat',
)
"""


def get_ld_entities_for_vocab_qs(vocab_obj=None, vocab_uuid=None, vocab_uri=None):
    """Gets a queryset of AllManifest instances that are part of a vocabulary
    
    :param AllManifest vocab_obj: An AllManifest object instance
        of a Linked Data vocabulary what we're querying for instances
    :param str(uuid) vocab_uuid: A uuid to identifier the vocab_obj if a
        vocab_obj is not passed.
    :param str vocab_uri: A uri to identifier the vocab_obj if a
        vocab_obj is not passed.
    
    return queryset (AllManifest)
    """
    if not vocab_obj:
        vocab_obj = utilities.get_manifest_object_by_uuid_or_uri(
            uuid=vocab_uuid,
            uri=vocab_uri,
        )
    if not vocab_obj:
        print(f'No record for vocabulary: {vocab_uuid} or {vocab_uri}')
        return None
    m_qs = AllManifest.objects.filter(
        item_type__in=configs.URI_CONTEXT_PREFIX_ITEM_TYPES,
        context=vocab_obj,
    ).order_by(
        'sort'
    )
    return m_qs


def get_ld_entities_for_vocab_df(vocab_obj=None, vocab_uuid=None, vocab_uri=None):
    """Gets a DataFrame of AllManifest instances that are part of a vocabulary
    
    :param AllManifest vocab_obj: An AllManifest object instance
        of a Linked Data vocabulary what we're querying for instances
    :param str(uuid) vocab_uuid: A uuid to identifier the vocab_obj if a
        vocab_obj is not passed.
    :param str vocab_uri: A uri to identifier the vocab_obj if a
        vocab_obj is not passed.
    
    return DataFrame
    """
    m_qs = get_ld_entities_for_vocab_qs(
        vocab_obj=vocab_obj, 
        vocab_uuid=vocab_uuid, 
        vocab_uri=vocab_uri,
    )
    if not m_qs:
        return None
    rows = []
    for m_obj in m_qs:
        parent_label = None
        parent_uuid = None
        parent_uri = None
        parent_objs = models_utils.get_immediate_concept_parent_objs(
            m_obj, 
            use_cache=True,
        )
        if parent_objs:
            parent_label = parent_objs[0].label
            parent_uuid = str(parent_objs[0].uuid)
            parent_uri = f'https://{parent_objs[0].uri}'
        row = {
            'parent_label': parent_label,
            'parent_uuid': parent_uuid,
            'parent_uri': parent_uri,
            'label': m_obj.label,
            'uri': f'https://{m_obj.uri}',
            'slug': m_obj.slug,
            'item_key': m_obj.item_key,
            'uuid': str(m_obj.uuid),
            'vocab_label': m_obj.context.label,
            'vocab_uuid': str(m_obj.context.uuid),
            'vocab_uri': f'https://{m_obj.context.uri}',
        }
        rows.append(row)
    df = pd.DataFrame(data=rows)
    return df


def make_ld_entities_for_vocab_csv(
    csv_path, 
    vocab_obj=None, 
    vocab_uuid=None, 
    vocab_uri=None,
):
    """Gets and saves DataFrame of AllManifest instances that are part of a vocabulary
    
    :param str csv_path: A directory path to save a CSV of the suggested equivalents
    :param AllManifest vocab_obj: An AllManifest object instance
        of a Linked Data vocabulary what we're querying for instances
    :param str(uuid) vocab_uuid: A uuid to identifier the vocab_obj if a
        vocab_obj is not passed.
    :param str vocab_uri: A uri to identifier the vocab_obj if a
        vocab_obj is not passed.
    
    return DataFrame
    """
    df = get_ld_entities_for_vocab_df(
        vocab_obj=vocab_obj, 
        vocab_uuid=vocab_uuid, 
        vocab_uri=vocab_uri,
    )
    if df is None:
        return None
    df.sort_values(by=['parent_label', 'label'], inplace=True)
    df.to_csv(csv_path, index=False)
    return df