
import copy
from turtle import up
from django.conf import settings
from django.core.cache import caches
from django.core.paginator import Paginator

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



def prod_safe_save_model_object(model_object, raise_on_error=True, only_insert=True):
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
            if not only_insert:
                model_object.save(using='prod')
            else:
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


def prod_safe_save_model_object_and_related(model_object, raise_on_error=True, only_insert=True):
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
        fk_ok = prod_safe_save_model_object_and_related(fk_obj, only_insert=only_insert)
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
    ok = prod_safe_save_model_object(model_object, raise_on_error=raise_on_error, only_insert=only_insert)
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
        if not fk_obj:
            print(f'No attribute {str(fk_attrib)} in {str(act_model._meta.label)}')
            continue
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


def make_migrate_safe_dict_obj(model_object):
    """Makes a data migration safe dictionary object from a Django model instance object"""
    dict_skips = [
        '_django_version', '_state', 'meta_json'
    ]
    raw_dict = model_object.__dict__
    dict_obj = {k:v for k, v in raw_dict.items() if k not in dict_skips}
    if raw_dict.get('meta_json'):
        dict_obj['meta_json'] = copy.deepcopy(model_object.meta_json)
    # dict_obj['pk'] = model_object.pk
    return dict_obj


def check_other_db_foreign_keys_in_qs(act_model, m_qs, from_db, to_db):
    to_db_missing_ids = set()
    for fK_attib in MODEL_FK_MANIFEST_ATTRIBUTES.get(act_model, []):
        act_qs = copy.deepcopy(m_qs)
        act_ids = act_qs.using(
            from_db
        ).distinct(
            fK_attib
        ).order_by(
            fK_attib
        ).values_list(
            f'{fK_attib}_id',
            flat=True
        )
        act_ids = set(act_ids)
        check_db_ids = AllManifest.objects.using(
            to_db
        ).filter(
            uuid__in=act_ids
        ).order_by(
            'uuid'
        ).values_list(
            'uuid',
            flat=True
        )
        check_db_ids = set(check_db_ids)
        missing_fk_ids = act_ids - check_db_ids
        print(f'{from_db} model {act_model._meta.label}.{fK_attib} records {len(missing_fk_ids)} of {len(act_ids)} missing in {to_db}')
        to_db_missing_ids.update(missing_fk_ids)
    return to_db_missing_ids


def make_list_of_model_objs(act_ids, from_objs, act_model):
    """Makes a list of model objects """
    model_objs = []
    update_attribs = None
    for id in act_ids:
        dict_obj = from_objs.get(id)
        if not dict_obj:
            continue
        if not update_attribs:
            update_attribs = [k for k,_ in dict_obj.items() if k not in ['pk','uuid'] ]
        model_objs.append(act_model(**dict_obj))
    return model_objs, update_attribs


def bulk_update_create(act_model, m_qs, from_db, to_db, chunk_size=500, target_page=None, prod_only_insert=True):
    to_db_missing_ids = check_other_db_foreign_keys_in_qs(
        act_model=act_model,
        m_qs=m_qs,
        from_db=from_db,
        to_db=to_db
    )
    all_ok = True
    if len(to_db_missing_ids):
        print(f'Migrate {len(to_db_missing_ids)} missing foreign key referenced manifest items from {from_db} to {to_db}')
        fk_qs = AllManifest.objects.using(from_db).filter(uuid__in=to_db_missing_ids)
        for model_object in fk_qs:
            if from_db == 'default' and to_db == 'prod':
                ok = prod_safe_save_model_object_and_related(model_object, only_insert=prod_only_insert)
            elif from_db == 'prod' and to_db == 'default':
                ok = default_safe_save_model_object_and_related(model_object)
            else:
                ok = False
            if not ok:
                print(f'Cannot migrate {model_object.__dict__} from database {from_db} to {to_db}')
                all_ok = False
    if not all_ok:
        print(f'Cannot migrate data for {from_db} model {act_model._meta.label} -> bad referential integrity')
        return None
    m_qs = m_qs.using(from_db)
    paginator = Paginator(m_qs, chunk_size)
    for page in range(1, paginator.num_pages + 1):
        if target_page and page != target_page:
            continue
        from_objs = {}
        from_pks = []
        for model_object in paginator.page(page).object_list:
            from_objs[model_object.pk] = make_migrate_safe_dict_obj(model_object)
            from_pks.append(model_object.pk)

        # Query to make a list of the items that already exist in the destination to_db
        to_exists_ids = act_model.objects.using(
            to_db
        ).filter(
            pk__in=from_pks
        ).values_list(
            'pk',
            flat=True
        )
        # Make a list if records for a bulk UPDATE (where the PKs exist in the destination to_db)
        # Note we're removing the primary key (the uuid) and making a list of the update_attributes.
        update_attribs = None
        to_exists_ids = list(to_exists_ids)
        update_items, update_attribs = make_list_of_model_objs(to_exists_ids, from_objs, act_model)
        # Make a list if records for a bulk INSERT (where the PKs do NOT exist in the destination to_db)
        to_new_ids = [id for id in from_pks if id not in to_exists_ids]
        create_items, _ = make_list_of_model_objs(to_new_ids, from_objs, act_model)
        print(
            f'{page} of {paginator.num_pages}: {from_db} model {act_model._meta.label} will '
            f'update {len(update_items)} and insert {len(create_items)} to {to_db}'
        )
        if update_items and update_attribs:
            n_up = act_model.objects.using(
                to_db
            ).bulk_update(
                update_items,
                update_attribs,
            )
            print(f'Updated {n_up} in {to_db}')
        if create_items:
            n_new = act_model.objects.using(
                to_db
            ).bulk_create(
                create_items,
            )
            print(f'Created {len(n_new)} in {to_db}')
            if len(n_new) != len(create_items):
                msg = (
                    f'{page} of {paginator.num_pages}: '
                    f'{to_db} has bulk_insert problem. {len(n_new)} of {len(create_items)} rows actually created!'
                )
                if not target_page:
                    raise ValueError(msg)
                else:
                    print(msg)