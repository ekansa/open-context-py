
from django.conf import settings
from django.core.cache import caches

from django.db import transaction


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


def default_safe_save_model_object(model_object, raise_on_error=True, only_insert=False):
    """Safely save a model object from the PROD to the DEFAULT database"""
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
            # so as to sync data from prod to the default (usually local)
            if not only_insert:
                model_object.save(using='default')
            else:
                model_object.save(using='default', force_insert=True)
            ok = True
    except Exception as e:
        ok = False
    return ok


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
    
    act_model = model_object._meta.model

    cache = caches['redis']
    cache_key = f'prod-pk-{str(act_model._meta.label)}-{str(model_object.pk)}'
    prod_exists = cache.get(cache_key)
    if prod_exists:
        # Our work is done, we know this already exists on prod, 
        # because we cached our knowledge that it does exist.
        return True

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
        if not fk_obj:
            print(f'No attribute {str(fk_attrib)} in {str(act_model._meta.label)}')
            continue
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


def default_safe_save_model_object_and_related(model_object, raise_on_error=True, only_insert=False):
    """Safely save a model object, and foreign key related objects to the DEFAULT database"""
    if not settings.CONNECT_PROD_DB:
        if raise_on_error:
            raise RuntimeError('No "prod" database connection config.')
        return False
    if model_object.pk is None:
        if raise_on_error:
            raise ValueError('Model object has no "primary key" cannot safely insert.')
        return False

    cache = caches['redis']
    cache_key = f'default-pk-{str(model_object.pk)}'
    default_exists = cache.get(cache_key)
    if default_exists:
        # Our work is done, we know this already exists on default 
        # because we cached our knowledge that it does exist.
        return True
    
    act_model = model_object._meta.model

    # Check the production database to see if this object already exists there.
    default_obj = act_model.objects.using('default').filter(pk=model_object.pk).first()
    if default_obj:
        # The default db actually already have this item. Cache our new
        # knowledge of this so we can avoid future DB lookups.
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
        fk_ok = default_safe_save_model_object_and_related(
            fk_obj, 
            raise_on_error=raise_on_error,
            only_insert=only_insert
        )
        if not fk_ok:
            # Sadly, we can't save this foreign key refed object.
            all_fk_ok = False

    if not all_fk_ok:
        if raise_on_error:
            raise ValueError('Model object foreign key object problem.')
        return False
    
    # Now save this!
    # NOTE: This will fail if default objects are not yet present in the
    # local default database, because ultimately, those default objects give context
    # to other objects.
    ok = default_safe_save_model_object(
        model_object, 
        raise_on_error=raise_on_error,
        only_insert=only_insert
    )
    if ok and act_model == AllManifest:
        # Only set the cache if this is a manifest item,
        # which we hit often b/c of foreign key relations
        cache.set(cache_key, True, timeout=DB_SYNC_CACHE_LIFE)
    return ok