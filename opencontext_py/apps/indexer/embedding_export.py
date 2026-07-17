
import json
import numpy as np
import os
import pandas as pd
import re
from scipy.spatial.distance import cosine

import warnings

from opencontext_py.apps.all_items.models import (
    AllManifest,
    AllAssertion,
    ManifestCachedSpacetime,
)
from opencontext_py.apps.all_items import hierarchy

from opencontext_py.apps.indexer.solrdocument_slim_schema import (
    EMBEDDING_FIELD_SOLR,
    SolrDocumentSlim
)
from opencontext_py.apps.indexer.embeddings import (
    embed_with_chunk_pooling
)


# The item_class slugs that help select manifest records
# associated with 'artifacts'
GENERAL_ARTIFACT_OBJECT_ITEM_CLASS_SLUGS = [
    'oc-gen-cat-object',
    'oc-gen-cat-arch-element',
    'oc-gen-cat-coin',
    'oc-gen-cat-glass',
    'oc-gen-cat-bio-subj-ecofact',
    'oc-gen-cat-pottery',
]

FILE_CACHE_COLS = [
    'uuid',
    'label',
    'path',
    'item_class__slug',
    'project__label',
    'project__uuid',
    'geo_source__path',
    'geo_source__uuid',
    'chrono_source__path',
    'chrono_source__uuid',
    'latitude',
    'longitude',
    'earliest',
    'latest',
    'str_for_embedding',
    'embedding',
]



def get_all_artifact_item_class_slugs():
    """Get all item-class manifest objects related to iSamples records"""
    m_qs = AllManifest.objects.filter(
        item_type='class',
        slug__in=['oc-gen-cat-object'],
    )
    artifact_item_classes = []
    for man_obj in m_qs:
        m_children = hierarchy.get_list_concept_children_recursive(man_obj)
        if man_obj not in artifact_item_classes:
            artifact_item_classes.append(man_obj)
        for child_obj in m_children:
            if child_obj not in artifact_item_classes:
                artifact_item_classes.append(child_obj)
    artifact_slugs = [s for s in GENERAL_ARTIFACT_OBJECT_ITEM_CLASS_SLUGS]
    artifact_slugs += [m.slug for m in artifact_item_classes if m.slug not in GENERAL_ARTIFACT_OBJECT_ITEM_CLASS_SLUGS]
    return artifact_slugs


def get_or_make_embeddings_csv(path):
    if os.path.exists(path):
        df = pd.read_csv(path)
        return df
    data = {c:[] for c in FILE_CACHE_COLS}
    df = pd.DataFrame(data=data)
    return df


def get_artifacts_man_spacetime_qs(filter_args={}, exclude_args={}):
    artifact_slugs = get_all_artifact_item_class_slugs()
    mspt_qs = ManifestCachedSpacetime.objects.filter(
        item__item_class__slug__in=artifact_slugs,
    ).select_related(
        'item'
    ).select_related(
        'geo_source'
    ).select_related(
        'chrono_source'
    ).select_related(
        'item__project'
    ).select_related(
        'item__item_class'
    )
    if filter_args:
        mspt_qs = mspt_qs.filter(**filter_args)
    if exclude_args:
        mspt_qs = mspt_qs.exclude(**exclude_args)
    return mspt_qs


def convert_decimal_to_float(val):
    try:
        value = float(val)
    except:
        value = None
    return value


def file_cache_artifact_embeddings(
    path,
    filter_args={}, 
    exclude_args={},
    old_path=None,
    exclude_uuids=[],
):
    df = get_or_make_embeddings_csv(path)
    if not exclude_uuids:
        exclude_uuids = []
    exclude_uuids += df['uuid'].unique().tolist()
    if old_path:
        df_old = pd.read_csv(old_path)
        exclude_uuids += df_old['uuid'].unique().tolist()
    exclude_uuids = list(set(exclude_uuids))
    if exclude_uuids:
        print(f'Skipping {len(exclude_uuids)} already completed records.')
        exclude_args['item_id__in'] = exclude_uuids
    mspt_qs = get_artifacts_man_spacetime_qs(
        filter_args=filter_args, 
        exclude_args=exclude_args,
    )
    total_count = mspt_qs.count()
    i = 0
    for mspt_obj in mspt_qs:
        i += 1
        man_obj = mspt_obj.item
        solrdoc_obj = SolrDocumentSlim(
            uuid=man_obj.uuid,
            man_obj=man_obj,
            context_path_in_embedding=False,
            proj_meta_in_embedding=False,
        )
        if solrdoc_obj.flag_do_not_index:
            print(f'Flagged to NOT index: {solrdoc_obj.man_obj.label} [{man_obj.uuid}]')
            continue
        ok = solrdoc_obj.make_solr_doc()
        if not ok:
            print(f'Problem making solr doc for {str(man_obj.uuid)}')
        str_for_embedding = '\n'.join(solrdoc_obj.text_for_embedding_list)
        embedding_json = json.dumps(solrdoc_obj.fields[EMBEDDING_FIELD_SOLR])
        
        geo_source_uuid = None
        geo_source_path = None
        if mspt_obj.geo_source:
            geo_source_uuid = str(mspt_obj.geo_source.uuid)
            geo_source_path = mspt_obj.geo_source.path

        chrono_source_uuid = None
        chrono_source_path = None
        if mspt_obj.chrono_source:
            chrono_source_uuid = str(mspt_obj.chrono_source.uuid)
            chrono_source_path = mspt_obj.chrono_source.path

        row = {
            'uuid': str(man_obj.uuid),
            'label': man_obj.label,
            'path': man_obj.path,
            'item_class__slug': man_obj.item_class.slug,
            'project__label': man_obj.project.label,
            'project__uuid': str(man_obj.project.slug),
            'geo_source__path': geo_source_path,
            'geo_source__uuid': str(geo_source_uuid),
            'chrono_source__path': chrono_source_path,
            'chrono_source__uuid': str(chrono_source_uuid),
            'latitude': convert_decimal_to_float(mspt_obj.latitude),
            'longitude': convert_decimal_to_float(mspt_obj.longitude),
            'earliest': mspt_obj.earliest,
            'latest': mspt_obj.latest,
            'str_for_embedding': str_for_embedding,
            'embedding': embedding_json,
        }
        new_row = pd.DataFrame(data=[row])
        df = pd.concat([df, new_row], ignore_index=True)
        df.to_csv(path, index=False)
        print(f'[{i} of {total_count}] Saved embedding for {solrdoc_obj.man_obj.label} [{str(man_obj.uuid)}]')
    return df