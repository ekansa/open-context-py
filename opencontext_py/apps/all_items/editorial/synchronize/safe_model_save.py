import copy
import json
import uuid as GenUUID

from django.conf import settings
from django.core.cache import caches

from django.db.models import Q
from django.db import transaction
from django.utils import timezone


from opencontext_py.apps.all_items import configs
from opencontext_py.apps.all_items.models import (
    AllManifest,
    AllAssertion,
    AllHistory,
    AllResource,
    AllIdentifier,
    AllSpaceTime,
)


DB_SYNC_CACHE_LIFE = 60 * 60 * 6 # Allow hours for keeping the cache alive

# These configure foreign key relationships to 
# Manifest objects. This config helps to identify foreign key
# referenced objects that must be synchronized.
MODEL_FK_MANIFEST_ATTRIBUTES = {
    AllManifest: [
        'publisher',
        'project',
        'item_class',
        'context',
    ],
    AllSpaceTime: [
        'publisher',
        'project',
        'item',
        'event',
    ],
    AllAssertion: [
        'publisher',
        'project',
        'subject',
        'observation',
        'event',
        'attribute_group',
        'predicate',
        'object',
        'language',
    ],
    AllResource: [
        'project',
        'item',
        'resourcetype',
        'mediatype',
    ],
    AllHistory: [
        'item',
    ],
    AllIdentifier: [
        'item',
    ],
}



def prod_safe_save_model_object(model_object, raise_on_error=True):
    """Safely save a model object to the PROD database"""

    # NOTE: This helps to make sure that we only do INSERTs to the
    # production DB, not updates or deletions.

    if not settings.CONNECT_PROD_DB:
        if raise_on_error:
            raise RuntimeError('No "prod" database connection config.')
        return None
    if model_object.pk is None:
        if raise_on_error:
            raise ValueError('Model object has no "primary key" cannot safely insert.')
        return None
    ok = None
    try:
        with transaction.atomic():
            model_object.save(using='prod', force_insert=True)
            ok = True
    except Exception as e:
        ok = False
    return ok


def local_safe_save_model_object(model_object, raise_on_error=True):
    """Safely save a model object from the PROD to the LOCAL database"""
    if not settings.CONNECT_PROD_DB:
        if raise_on_error:
            raise RuntimeError('No "prod" database connection config.')
        return None
    if model_object.pk is None:
        if raise_on_error:
            raise ValueError('Model object has no "primary key" cannot safely insert.')
        return None
    ok = None
    try:
        with transaction.atomic():
            # NOTE: This allows updates, not just inserts, 
            # so as to sync data from prod locally.
            model_object.save(using='default')
            ok = True
    except Exception as e:
        ok = False
    return ok


def check_prod_model_exists(model_object, raise_on_error=True):
    """Check if the model exists on the prod server"""
    if not settings.CONNECT_PROD_DB:
        if raise_on_error:
            raise RuntimeError('No "prod" database connection config.')
        return None
    if model_object.pk is None:
        if raise_on_error:
            raise ValueError('Model object has no "primary key" cannot safely insert.')
        return None
    cache = caches['redis']
    cache_key = str(model_object.pk)
    prod_exists = cache.get(cache_key)
    if not prod_exists:
        prod_obj = AllManifest.objects.filter(pk=model_object.pk)


def prod_safe_save_model_object_and_related(model_object, raise_on_error=True):
    """Safely save a model object, and foreign key related objects to the PROD database"""
    if not settings.CONNECT_PROD_DB:
        if raise_on_error:
            raise RuntimeError('No "prod" database connection config.')
        return False
    if model_object.pk is None:
        if raise_on_error:
            raise ValueError('Model object has no "primary key" cannot safely insert.')
        return False

    cache = caches['redis']
    cache_key = f'prod-pk-{str(model_object.pk)}'
    prod_exists = cache.get(cache_key)
    if prod_exists:
        # Our work is done, we know this already exists on prod, 
        # because we cached our knowledge that it does exist.
        return True
    
    act_model = model_object._meta.model

    # Check the production database to see if this object already exists there.
    prod_obj = act_model.objects.using('prod').filter(pk=model_object.pk).first()
    if prod_obj:
        # The prod sb actually already have this item. Cache our new
        # knowledge of this so we can avoid future lookups on the remote
        # database.
        if act_model == AllManifest:
            # Only set the cache if this is a manifest item,
            # which we hit often b/c of foreign key relations
            cache.set(cache_key, True, timeout=DB_SYNC_CACHE_LIFE)
        return True

    # OK we actually have not saved this on prod, so do it.
    fk_attribs = MODEL_FK_MANIFEST_ATTRIBUTES.get(act_model, [])
    all_fk_ok = True
    for fk_attrib in fk_attribs:
        fk_obj = getattr(model_object, fk_attrib)
        fk_ok = prod_safe_save_model_object_and_related(fk_obj)
        if not fk_ok:
            # Sadly, we can't save this foreign key refed object.
            all_fk_ok = False

    if not all_fk_ok:
        if raise_on_error:
            raise ValueError('Model object foreign key object problem.')
        return False
    
    # Now save this!
    # NOTE: This will fail if default objects are not yet present in the
    # 'prod' database, because ultimately, those default objects give context
    # to other objects.
    ok = prod_safe_save_model_object(model_object, raise_on_error=raise_on_error)
    if ok and act_model == AllManifest:
        # Only set the cache if this is a manifest item,
        # which we hit often b/c of foreign key relations
        cache.set(cache_key, True, timeout=DB_SYNC_CACHE_LIFE)
    return ok