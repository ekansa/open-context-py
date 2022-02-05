

from django.core.cache import caches

from opencontext_py.apps.all_items import configs
from opencontext_py.apps.all_items.models import (
    AllManifest,
    AllAssertion,
)


# ---------------------------------------------------------------------
# NOTE: These are functions to get other, non-default labels for a
# Manifest item
# ---------------------------------------------------------------------


LABEL_PREDICATE_IDS = [
    configs.PREDICATE_SKOS_PREFLABEL_UUID,
    configs.PREDICATE_SKOS_ALTLABEL_UUID,
    configs.PREDICATE_DCTERMS_TITLE_UUID,
]


def get_other_label_assertions_db(man_obj, use_cache=True, filters=None):
    """Gets Assertions about alternative labels via a database query
    """
    a_qs = AllAssertion.objects.filter(
        subject=man_obj,
        predicate_id__in=LABEL_PREDICATE_IDS
    ).order_by(
        # This basically makes the alt-label the last of all the alternate
        # labels to be returned.
        '-predicate__slug', 
        'sort'
    )
    if filters:
        a_qs = a_qs.filter(**filters)
    return a_qs


def get_other_label_assertions(man_obj, use_cache=True):
    """Gets Assertions about alternative labels, with preference for cached data
    """
    if not use_cache:
        return get_other_label_assertions_db(man_obj)
    # Use the cache
    cache_key = f'{str(man_obj.uuid)}-item-labels-qs'
    cache = caches['redis']
    a_qs = cache.get(cache_key)
    if a_qs is not None:
        # We found the result in the cache.
        return a_qs
    a_qs = get_other_label_assertions_db(man_obj)
    try:
        cache.set(cache_key, a_qs)
    except:
        pass
    return a_qs


def get_other_labels(man_obj, use_cache=True):
    """Gets a list of other labels for an item, if they exist
    """
    labels = []
    a_qs = get_other_label_assertions(man_obj, use_cache=use_cache)
    if not a_qs:
        return labels
    for assert_obj in a_qs:
        if assert_obj.obj_string.lower() == man_obj.label.lower():
            continue
        if assert_obj.obj_string in labels:
            continue
        labels.append(assert_obj.obj_string)
    return labels