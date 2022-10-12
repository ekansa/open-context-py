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
from opencontext_py.apps.all_items.editorial.item import updater_assertions
from opencontext_py.apps.all_items.editorial.link_annotations import utilities

from opencontext_py.apps.all_items.representations import rep_utils

"""
Example use.

import importlib
from pathlib import Path
from opencontext_py.apps.all_items.editorial.link_annotations import link_types
importlib.reload(link_types)

HOME = str(Path.home())
csv_path = f'{HOME}/data-dumps/pc-material-types.csv'

df = link_types.make_csv_suggest_linked_data_equiv_for_predicate_types(
    csv_path=csv_path,
    predicate_obj=None,
    predicate_uuid='a70236ca-1599-42f5-4a12-acec8c423850', # fabric category
    concept_man_obj=None,
    concept_uuid=None,
    concept_uri='https://erlangen-crm.org/current/P45_consists_of',
    types_equiv_vocab_objs=None,
    types_equiv_vocab_uris=['vocab.getty.edu/aat',],
    default_equiv_pred_obj=None,
    default_equiv_pred_uri=None,
)

added, errors = link_types.make_new_types_ld_assertions_from_csv(
    csv_path=csv_path,
)
"""

DEFAULT_SOURCE_ID = 'auto-ld-equiv'


def most_frequent(act_list):
    """Returns the most frequently repeating item in a list"""
    return max(set(act_list), key=act_list.count)


def get_existing_equiv_concepts(
    concept_man_obj, 
    equiv_item_type='predicates',
    equiv_item_contexts=None,
    skip_equiv_obj=None
):
    """Makes a list of Manifest objects that are equivalent to the 
    concept_man_obj
    
    :param AllManifest concept_man_obj: An AllManifest object instance
        for which we want to query for a list of semantically equivalent 
        (or nearly equivalent) AllManifest objects
    :param str equiv_item_type: Limit the AllManifest item_type for 
        equivalent AllManifest objects
    :param list equiv_item_contexts: A list of AllManifest contexts for 
        equivalent AllManifest objects
    param AllManifest skip_equiv_obj: Do NOT include this AllManifest
        object in the equivalent list.
    
    return list (of AllManifest objects)
    """
    equiv_subj_qs = AllAssertion.objects.filter(
        subject__item_type=equiv_item_type,
        predicate_id__in=configs.PREDICATE_LIST_SBJ_EQUIV_OBJ,
        object=concept_man_obj,
    ).select_related(
        'subject'
    )
    if equiv_item_contexts:
        equiv_subj_qs = equiv_subj_qs.filter(
            subject__context__in=equiv_item_contexts,
        )
    equiv_items = [act_ass.subject for act_ass in equiv_subj_qs if act_ass.subject != skip_equiv_obj]
    equiv_obj_qs = AllAssertion.objects.filter(
        subject=concept_man_obj,
        predicate_id__in=configs.PREDICATE_LIST_SBJ_EQUIV_OBJ,
        object__item_type=equiv_item_type,
    ).exclude(
        object__in=equiv_items
    ).select_related(
        'object'
    )
    if equiv_item_contexts:
        equiv_obj_qs = equiv_obj_qs.filter(
            object__context__in=equiv_item_contexts,
        )
    equiv_items += [act_ass.object for act_ass in equiv_obj_qs if act_ass.object != skip_equiv_obj]
    return equiv_items


def get_ld_equiv_objs_for_types_in_pred_list_context(
    match_label,
    pred_list_context, 
    types_equiv_vocab_objs=None,
):
    """Makes a list of linked data AllManifest object equivalent to AllManifest
    item_type='types' that match a match_label
    
    :param str match_label: A label to match (case-insensitive) against
        other AllManifest item_type='types' or labels for linked data
        AllManifest items.
    :param list pred_list_context: A list of AllManifest item_type='predicates'
        contexts to search for item_type='types' records with matching labels
    :param list types_equiv_vocab_objs:  A list of AllManifest item_type='vocabularies'
        that limit what equivalent linked data objects this will return
    
    returns list (of AllManifest objects)
    """
    equiv_ld_objs = {}
    equiv_qs = AllAssertion.objects.filter(
        object__context__in=pred_list_context,
        object__item_type='types',
        predicate_id__in=configs.PREDICATE_LIST_SBJ_EQUIV_OBJ,
        subject__item_type__in=configs.URI_CONTEXT_PREFIX_ITEM_TYPES,
    ).select_related(
        'subject'
    ).select_related(
        'object'
    )
    equiv_qs = equiv_qs.filter(
        Q(subject__label__iexact=match_label)|Q(object__label__iexact=match_label)
    )
    if types_equiv_vocab_objs:
        equiv_qs = equiv_qs.filter(
            subject__context__in=types_equiv_vocab_objs,
        )
    # In this case, the subject item is the ld equivalent item.
    equiv_ld_objs = [act_ass.subject for act_ass in equiv_qs]
    equiv_qs = AllAssertion.objects.filter(
        subject__context__in=pred_list_context,
        subject__item_type='types',
        predicate_id__in=configs.PREDICATE_LIST_SBJ_EQUIV_OBJ,
        object__item_type__in=configs.URI_CONTEXT_PREFIX_ITEM_TYPES,
    ).select_related(
        'subject'
    ).select_related(
        'object'
    )
    equiv_qs = equiv_qs.filter(
        Q(subject__label__iexact=match_label)|Q(object__label__iexact=match_label)
    )
    if types_equiv_vocab_objs:
        equiv_qs = equiv_qs.filter(
            object__context__in=types_equiv_vocab_objs,
        )
    # In this case, the object item is the ld equivalent item.
    equiv_ld_objs += [act_ass.object for act_ass in equiv_qs]
    return equiv_ld_objs


def suggest_linked_data_equiv_for_predicate_types(
    predicate_obj,
    concept_man_obj,
    types_equiv_vocab_objs=None,
    default_equiv_pred_obj=None,
):
    """Suggests lists of linked data AllManifest object equivalent to AllManifest
    item_type='types' used with a predicate_obj based on existing data.
    
    :param AllManifest predicate_obj: An AllManifest item_type='predicates' instance
        that is the context for item_type='types' records that we want to associate
        with suggested linked data equivalents.
    :param AllManifest concept_man_obj: An AllManifest object instance
        for which we want to query for a list of semantically equivalent 
        (or nearly equivalent) AllManifest objects
    :param list types_equiv_vocab_objs:  A list of AllManifest item_type='vocabularies'
        that limit what equivalent linked data objects this will return
    :param AllManifest default_equiv_pred_obj:  An AllManifest item_type='property'
        to be used as a predicate linking AllManifest item_type='types' instances with
        linked data entities
    
    returns list (of dicts conforming to updater_assertions expectations)

    """
    if not default_equiv_pred_obj:
        # Default to the SKOS close match predicate for an equivalence relation.
        default_equiv_pred_obj = AllManifest.objects.get(uuid=configs.PREDICATE_SKOS_CLOSE_MATCH_UUID)
    preds_equiv_to_concept = get_existing_equiv_concepts(
        concept_man_obj=concept_man_obj, 
        equiv_item_type='predicates',
        equiv_item_contexts=None,
        skip_equiv_obj=predicate_obj,
    )
    pred_types = AllManifest.objects.filter(
        context=predicate_obj, 
        item_type='types',
    ).order_by(
        'sort'
    )
    assert_rows = []
    for type_obj in pred_types:
        equiv_ld_objs = get_ld_equiv_objs_for_types_in_pred_list_context(
            match_label=type_obj.label,
            pred_list_context=preds_equiv_to_concept, 
            types_equiv_vocab_objs=types_equiv_vocab_objs,
        )
        print(f'Type: {type_obj.label} ({str(type_obj.uuid)}) has {len(equiv_ld_objs)} equivalent concepts')
        row = {
            'subject_label': type_obj.label,
            'subject_id': str(type_obj.uuid),
        }
        if len(equiv_ld_objs) > 0:
            equiv_ld_obj = most_frequent(equiv_ld_objs)
            print(f'The best matching equivalent LD concept is: {equiv_ld_obj.label} {equiv_ld_obj.uri}')
            row['predicate_label'] = default_equiv_pred_obj.label
            row['predicate_id'] = str(default_equiv_pred_obj.uuid)
            row['predicate_uri'] = default_equiv_pred_obj.uri
            row['object_label'] = equiv_ld_obj.label
            row['object_id'] = str(equiv_ld_obj.uuid)
            row['object_uri'] = equiv_ld_obj.uri
        assert_rows.append(row)
    return assert_rows


def is_valid_and_new_types_ld_assertion_row(row):
    """Checks if an assertion relating an AllManifest item_type='types' object
    to a linked data object would be both valid and new.
    
    :param dict row: A row with assertion information to associate a subject of
        AllManifest.item_type = 'types' with an object that is an AllManifest
        linked data instance
    
    returns row (if valid and new)
    """
    type_obj = utilities.get_manifest_object_by_uuid_or_uri(
        uuid=row.get('subject_id'),
        uri=row.get('subject_uri'),
    )

    if not type_obj:
        return None
    if type_obj.item_type != 'types':
        print(
            f'act_type: {type_obj.label} ({str(type_obj.uuid)}) is a {type_obj.item_type} not a "types"'
        )
        return None
    pred_obj = utilities.get_manifest_object_by_uuid_or_uri(
        uuid=row.get('predicate_id'),
        uri=row.get('predicate_uri'),
    )
    if not pred_obj:
        return None
    if pred_obj.item_type != 'property':
        print(
            f'pred_obj: {pred_obj.label} ({str(pred_obj.uuid)}) is a {pred_obj.item_type} not a "property"'
        )
        return None
    ld_obj = utilities.get_manifest_object_by_uuid_or_uri(
        uuid=row.get('object_id'),
        uri=row.get('object_uri'),
    )
    if not ld_obj:
        return None
    if not ld_obj.item_type in configs.URI_CONTEXT_PREFIX_ITEM_TYPES:
        print(
            f'ld_obj: {ld_obj.label} ({str(ld_obj.uuid)}) is a {ld_obj.item_type} not, not linked-data'
        )
        return None
    act_ass = AllAssertion.objects.filter(
        subject=type_obj,
        predicate=pred_obj,
        object=ld_obj,
    ).first()
    if act_ass:
        # This assertion is valid but not new
        return None
    # Make sure the row has subject_id, predicate_id, and object_id in case the input data
    # used a uri as the identifier. The updater_assertions functions expect uuid identifiers
    # for AllManifest instances, this step makes sure we have the UUIDs required.
    row['subject_id'] = str(type_obj.uuid)
    row['predicate_id'] = str(pred_obj.uuid)
    row['object_id'] = str(ld_obj.uuid)
    # This assertion would be valid and new
    return row
    

def make_new_types_ld_assertions(assert_rows, source_id=DEFAULT_SOURCE_ID):
    """Makes new assertions to associate AllManifest types items with Linked Data entities

    :param list assert_rows: A list of dicts that meet the expectations of the 
        updater_assertions.add_assertions and are valid for 
        AllManifest types items with Linked Data entities associations.
    :param str source_id: A source_id for tracking the source of AllAssertions that may
        be created
    
    returns added, errors
    """
    ok_new_rows = []
    for row in assert_rows:
        row = is_valid_and_new_types_ld_assertion_row(row)
        if not row:
            # The row is already in the database, or has missing required data, or
            # an identifier can't be resolved, so skip.
            continue
        ok_new_rows.append(row)
    added, errors = updater_assertions.add_assertions(
        request_json=ok_new_rows,
        request=None,
        source_id=source_id,
    )
    return added, errors


def make_csv_suggest_linked_data_equiv_for_predicate_types(
    csv_path,
    predicate_obj=None,
    predicate_uuid=None,
    concept_man_obj=None,
    concept_uuid=None,
    concept_uri=None,
    types_equiv_vocab_objs=None,
    types_equiv_vocab_uris=None,
    default_equiv_pred_obj=None,
    default_equiv_pred_uri=None,
):
    """Suggests lists of linked data AllManifest object equivalent to AllManifest
    item_type='types' used with a predicate_obj based on existing data.
    
    :param str csv_path: A directory path to save a CSV of the suggested equivalents
    :param AllManifest predicate_obj: An AllManifest item_type='predicates' instance
        that is the context for item_type='types' records that we want to associate
        with suggested linked data equivalents.
    :param str(uuid) predicate_uuid: A uuid to identifier the predicate_obj if a
        predicate_obj is not passed.
    :param AllManifest concept_man_obj: An AllManifest object instance
        for which we want to query for a list of semantically equivalent 
        (or nearly equivalent) AllManifest objects
    :param str(uuid) concept_uuid: A uuid to identifier the concept_man_obj if a
        concept_man_obj is not passed.
    :param str concept_uri: A uri to identifier the concept_man_obj if a
        concept_man_obj is not passed.
    :param list types_equiv_vocab_objs:  A list of AllManifest item_type='vocabularies'
        that limit what equivalent linked data objects this will return
    :param list types_equiv_vocab_uris:  A list of uris to identify 
        types_equiv_vocab_objs if types_equiv_vocab_objs is not passed.
    :param AllManifest default_equiv_pred_obj:  An AllManifest item_type='property'
        to be used as a predicate linking AllManifest item_type='types' instances with
        linked data entities
    :param str default_equiv_pred_uri: A uri to identifier the default_equiv_pred_uri if a
        concept_man_obj is not passed.

    returns DataFrame
    """
    if not predicate_obj:
        predicate_obj = AllManifest.objects.get(uuid=predicate_uuid)
    if not concept_man_obj:
        concept_man_obj = utilities.get_manifest_object_by_uuid_or_uri(
            uuid=concept_uuid,
            uri=concept_uri,
        )
    if not concept_man_obj:
        raise ValueError('Must have a concept_man_obj')
    if not types_equiv_vocab_objs and types_equiv_vocab_uris:
        types_equiv_vocab_objs = []
        for type_equiv_vocab_uri in types_equiv_vocab_uris:
            vocab_obj = utilities.get_manifest_object_by_uuid_or_uri(
                uuid=None,
                uri=type_equiv_vocab_uri,
            )
            if not vocab_obj:
                continue
            types_equiv_vocab_objs.append(vocab_obj)
        if not len(types_equiv_vocab_objs):
            types_equiv_vocab_objs = None
    if not default_equiv_pred_obj and default_equiv_pred_uri:
        default_equiv_pred_obj = utilities.get_manifest_object_by_uuid_or_uri(
            uuid=None,
            uri=default_equiv_pred_uri,
        )
    assert_rows = suggest_linked_data_equiv_for_predicate_types(
        predicate_obj,
        concept_man_obj,
        types_equiv_vocab_objs=types_equiv_vocab_objs,
        default_equiv_pred_obj=default_equiv_pred_obj,
    )
    df = pd.DataFrame(data=assert_rows)
    df.to_csv(csv_path, index=False)
    return df


def make_new_types_ld_assertions_from_csv(csv_path, source_id=DEFAULT_SOURCE_ID):
    """Makes new assertions to associate AllManifest types items with Linked Data entities
    from data in a CSV file

    :param str csv_path: A directory path to load CSV data of the suggested equivalents
    :param str source_id: A source_id for tracking the source of AllAssertions that may
        be created
    
    returns added, errors
    """
    df = pd.read_csv(csv_path)
    ok_indx = (
        ~df['subject_id'].isnull()
        & ~df['predicate_id'].isnull()
        & ~df['object_id'].isnull()
    )
    assert_rows = df[ok_indx].to_dict('records')
    added, errors = make_new_types_ld_assertions(assert_rows, source_id=source_id)
    return added, errors


def get_vocab_concepts_equiv_types(vocab_man_obj):
    """Gets concepts in a vocabulary and any equivalent project types
    
    :param AllManifest vocab_man_obj: An AllManifest object instance
        of a vocabulary where we want to list concepts used in Open 
        Context and equivalent types for different projects.
    
    return list (rows)
    """
    vocab_man_qs = AllManifest.objects.filter(
        context=vocab_man_obj,
    ).order_by(
        'label'
    )
    rows = []
    for class_man_obj in vocab_man_qs:
        row_start = {
            'concept_label': class_man_obj.label,
            'concept_uuid': str(class_man_obj.uuid),
            'concept_uri': rep_utils.make_web_url(class_man_obj),
        }
        equiv_qs = AllManifest.objects.filter(
            Q(
                uuid__in=AllAssertion.objects.filter(
                    object__item_type='types',
                    predicate_id__in=configs.PREDICATE_LIST_SBJ_EQUIV_OBJ,
                    subject=class_man_obj,
                ).values_list(
                    'object_id', 
                    flat=True
                )
            )|Q(
                uuid__in=AllAssertion.objects.filter(
                    subject__item_type='types',
                    predicate_id__in=configs.PREDICATE_LIST_SBJ_EQUIV_OBJ,
                    object=class_man_obj,
                ).values_list(
                    'subject_id', 
                    flat=True
                )
            )
        ).select_related(
            'project'
        ).order_by(
            'label',
            'project__label',
        )
        if equiv_qs.count() < 1:
            rows.append(row_start)
            continue
        for equiv_obj in equiv_qs:
            row = copy.deepcopy(row_start)
            row['equiv_type_label'] = equiv_obj.label
            row['equiv_type_uuid'] = str(equiv_obj.uuid)
            row['equiv_type_project'] = equiv_obj.project.label
            row['equiv_type_project_slug'] = equiv_obj.project.slug
            rows.append(row)
    return rows


def make_csv_suggest_linked_data_equiv_for_predicate_types(
    csv_path,
    vocab_man_obj=None,
    vocab_uuid=None,
    vocab_uri=None,
):
    """Suggests lists of linked data AllManifest object equivalent to AllManifest
    item_type='types' used with a predicate_obj based on existing data.
    
    :param str csv_path: A directory path to save a CSV of the suggested equivalents
    :param AllManifest vocab_man_obj: An AllManifest object instance
        of a vocabulary where we want to list concepts used in Open 
        Context and equivalent types for different projects.
    :param str(uuid) vocab_uuid: A uuid to identify the vocab_man_obj if a
       vocab_man_obj is not passed.
    :param str vocab_uri: A uri to identify the vocab_man_obj if a
       vocab_man_obj is not passed.

    returns DataFrame
    """
    if not vocab_man_obj:
        vocab_man_obj = utilities.get_manifest_object_by_uuid_or_uri(
            uuid=vocab_uuid,
            uri=vocab_uri,
        )
    if not vocab_man_obj:
        raise ValueError('Must have a vocab_man_obj')
    rows = get_vocab_concepts_equiv_types(vocab_man_obj)
    df = pd.DataFrame(data=rows)
    df.to_csv(csv_path, index=False)
    return df