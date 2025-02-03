
from django.conf import settings
from opencontext_py.apps.all_items.editorial.synchronize import safe_model_save

from opencontext_py.apps.all_items.models import (
    AllManifest,
    AllAssertion,
    AllHistory,
    AllResource,
    AllIdentifier,
    AllSpaceTime,
)

"""
# Invocation:

import importlib
import datetime
from opencontext_py.apps.all_items.editorial.synchronize import sync_data
importlib.reload(sync_data)

sync_data.update_prod_from_default(after_date='2024-12-23', prod_only_insert=False)



import importlib
from opencontext_py.apps.all_items.editorial.synchronize import sync_data
from opencontext_py.apps.all_items.models import (
    AllManifest,
    AllAssertion,
    AllHistory,
    AllResource,
    AllIdentifier,
    AllSpaceTime,
)
project_uuid = 'df043419-f23b-41da-7e4d-ee52af22f92f'
update_models = [
    (AllSpaceTime, 'project_id',),
    (AllAssertion, 'project_id',),
    (AllResource, 'project_id',),
    (AllHistory, 'item__project_id',),
    (AllIdentifier, 'item__project_id',),
]
sync_data.update_default_from_prod(project_uuid=project_uuid, update_models=update_models)

"""

# These configure foreign key relationships to
# Manifest objects. This config helps to identify foreign key
# referenced objects that must be synchronized.
MODELS_TO_SYNC = [
    (AllManifest, 'project_id',),
    (AllSpaceTime, 'project_id',),
    (AllAssertion, 'project_id',),
    (AllResource, 'project_id',),
    (AllHistory, 'item__project_id',),
    (AllIdentifier, 'item__project_id',),
]


def update_default_from_prod(
    project_uuid=None,
    after_date=None,
    only_insert=True,
    raise_on_error=True,
    update_models=MODELS_TO_SYNC,
):
    if not project_uuid and not after_date:
        raise ValueError('Must limit sync by project, date, or both')

    if not settings.CONNECT_PROD_DB:
        if raise_on_error:
            raise RuntimeError('No "prod" database connection config.')
        return None

    all_migrated_objs = 0
    for model, project_id_attrib in update_models:
        filter_args = {}
        if project_uuid:
            filter_args[project_id_attrib] = project_uuid
        if after_date:
            filter_args[f'updated__gte'] = after_date
        m_qs = model.objects.all()
        if filter_args:
            m_qs = m_qs.filter(**filter_args)
        if model != AllManifest:
            safe_model_save.bulk_update_create(
                act_model=model,
                m_qs=m_qs,
                from_db='prod',
                to_db='default'
            )
            continue
        m_qs = m_qs.using('prod')
        print(
            f'Prod queryset returns {model._meta.label}: {len(m_qs)}'
        )
        migrated_model_objs = 0
        for model_object in m_qs:
            ok = safe_model_save.default_safe_save_model_object_and_related(
                model_object,
                raise_on_error=True,
                only_insert=only_insert,
            )
            if not ok:
                print(f'Failed to save: {model_object}')
                continue
            migrated_model_objs += 1
            all_migrated_objs += 1
        print(
            f'Migrated to default (local) {model._meta.label}: {migrated_model_objs}, '
            f'total {all_migrated_objs}'
        )


def update_prod_from_default(
    project_uuid=None,
    after_date=None,
    raise_on_error=True,
    update_models=MODELS_TO_SYNC,
    prod_only_insert=True,
):
    if not project_uuid and not after_date:
        raise ValueError('Must limit sync by project, date, or both')

    if not settings.CONNECT_PROD_DB:
        if raise_on_error:
            raise RuntimeError('No "prod" database connection config.')
        return None

    all_migrated_objs = 0
    for model, project_id_attrib in update_models:
        filter_args = {}
        if project_uuid:
            filter_args[project_id_attrib] = project_uuid
        if after_date:
            filter_args[f'updated__gte'] = after_date

        # Check the default database to get rows that we may want to
        # transfer to prod.
        m_qs = model.objects.all()
        if filter_args:
            m_qs = m_qs.filter(**filter_args)
        if model != AllManifest:
            safe_model_save.bulk_update_create(
                act_model=model,
                m_qs=m_qs,
                from_db='default',
                to_db='prod',
                prod_only_insert=prod_only_insert,
            )
            continue
        m_qs = m_qs.using('default')
        print(
            f'Default (local) queryset returns {model._meta.label}: {len(m_qs)}'
        )
        migrated_model_objs = 0
        for model_object in m_qs:
            ok = safe_model_save.prod_safe_save_model_object_and_related(
                model_object,
                raise_on_error=True,
                only_insert=prod_only_insert,
            )
            if not ok:
                print(f'Failed to save: {model_object}')
                continue
            migrated_model_objs += 1
            all_migrated_objs += 1
        print(
            f'Migrated to PROD {model._meta.label}: {migrated_model_objs}, '
            f'total {all_migrated_objs}'
        )