import pytz

from django.conf import settings
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.ocitems.assertions.models import Assertion
from opencontext_py.apps.ocitems.events.models import Event
from opencontext_py.apps.ocitems.geospace.models import Geospace
from opencontext_py.apps.ocitems.obsmetadata.models import ObsMetadata
from opencontext_py.apps.ocitems.predicates.models import Predicate
from opencontext_py.apps.ocitems.octypes.models import OCtype
from opencontext_py.apps.ocitems.strings.models import OCstring
from opencontext_py.apps.ocitems.subjects.models import Subject
from opencontext_py.apps.ocitems.mediafiles.models import Mediafile
from opencontext_py.apps.ocitems.documents.models import OCdocument
from opencontext_py.apps.ocitems.persons.models import Person
from opencontext_py.apps.ocitems.projects.models import Project
from opencontext_py.apps.ocitems.identifiers.models import StableIdentifer
from opencontext_py.apps.ldata.linkannotations.models import LinkAnnotation
from opencontext_py.apps.ldata.linkentities.models import LinkEntity
from opencontext_py.apps.exports.expfields.models import ExpField
from opencontext_py.apps.exports.exprecords.models import ExpCell
from opencontext_py.apps.exports.exptables.models import ExpTable

from opencontext_py.apps.all_items.editorial.synchronize import safe_model_save


"""
# Invocation:

import importlib
from opencontext_py.apps.ocitems.identifiers.models import StableIdentifer
from opencontext_py.apps.all_items.editorial.synchronize.legacy import model_objects
importlib.reload(model_objects)

after_date = '2021-06-15'
update_models_prod = [(Project, 'updated', True,),]
model_objects.update_default_from_prod(
    project_uuid='bc71c724-eb1e-47d6-9d45-b586ddafdcfe', after_date=after_date, update_models=update_models_prod
)

update_models=[
    (Manifest, 'record_updated', True,),
    (Geospace, 'updated', True,),
    (Mediafile, 'updated', True,),
    (OCstring, 'updated', True,),
    (Assertion, 'updated', True,),
]
model_objects.update_prod_from_default(
    project_uuid='bc71c724-eb1e-47d6-9d45-b586ddafdcfe', after_date=after_date, update_models=update_models
)

# model_objects.update_default_from_prod(after_date=after_date)
"""


LEGACY_MODELS = [
    (Manifest, 'record_updated', True,),        
    (Event, 'updated', True,),
    (Geospace, 'updated', True,),
    (ObsMetadata, 'updated', True,),
    (Predicate, 'updated', True,),
    (OCtype, 'updated', True,),
    (OCstring, 'updated', True,),
    (Subject, 'updated', True,),
    (OCdocument, 'updated', True,),
    (Person, 'updated', True,),
    # (Project, 'updated', True,),
    (StableIdentifer, 'updated', True,),
    (LinkAnnotation, 'updated', True,),
    (LinkEntity, 'updated', False,),
    (Assertion, 'updated', True,),
    (Mediafile, 'updated', True,),
]

LEGACT_EXTABLE_MODELS = [
    (ExpField, 'updated', True,),
    (ExpCell, 'updated', False,),
    (ExpTable, 'updated', False,),
]


def update_default_from_prod(
    project_uuid=None, 
    after_date=None, 
    only_insert=True,
    raise_on_error=True,
    update_models=LEGACY_MODELS,
):
    if not project_uuid and not after_date:
        raise ValueError('Must limit sync by project, date, or both')

    if not settings.CONNECT_PROD_DB:
        if raise_on_error:
            raise RuntimeError('No "prod" database connection config.')
        return None
    
    all_migrated_objs = 0
    for model, update_attrib, has_project_attrib in update_models:
        filter_args = {}
        if has_project_attrib and project_uuid:
            filter_args['project_uuid'] = project_uuid
        if after_date:
            filter_args[f'{update_attrib}__gte'] = after_date
        m_qs = model.objects.using('prod').all()
        if filter_args:
            m_qs = m_qs.filter(**filter_args)
        print(
            f'Prod queryset returns {model._meta.label}: {len(m_qs)}'
        )
        migrated_model_objs = 0
        for model_object in m_qs:
            ok = safe_model_save.default_safe_save_model_object_and_related(
                model_object, 
                raise_on_error=True, 
                only_insert=True,
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
    update_models=LEGACY_MODELS,
):
    if not project_uuid and not after_date:
        raise ValueError('Must limit sync by project, date, or both')

    if not settings.CONNECT_PROD_DB:
        if raise_on_error:
            raise RuntimeError('No "prod" database connection config.')
        return None
    
    all_migrated_objs = 0
    for model, update_attrib, has_project_attrib in update_models:
        filter_args = {}
        if has_project_attrib and project_uuid:
            filter_args['project_uuid'] = project_uuid
        if after_date:
            filter_args[f'{update_attrib}__gte'] = after_date
        
        # Check the default database to get rows that we may want to
        # transfer to prod.
        m_qs = model.objects.using('default').all()
        if filter_args:
            m_qs = m_qs.filter(**filter_args)
        print(
            f'Default (local) queryset returns {model._meta.label}: {len(m_qs)}'
        )
        migrated_model_objs = 0
        for model_object in m_qs:
            ok = safe_model_save.prod_safe_save_model_object_and_related(
                model_object, 
                raise_on_error=True,
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


def sync_prod_events(project_uuid, after_date=None):
    e_qs = Event.objects.using('default').filter(project_uuid=project_uuid)
    if after_date:
        e_qs = e_qs.filter(updated__gte=after_date)
    for eobj in e_qs:
        ok = None
        try:
            eobj.save(using='prod')
            ok = True
        except:
            ok = False
        if ok:
            print(f'Event {eobj.hash_id} updated or inserted OK')
            continue
        n = Event.objects.using(
            'prod'
        ).filter(
            uuid=eobj.uuid,
            meta_type=eobj.meta_type,
            feature_id=eobj.feature_id,
            event_id=eobj.event_id,
        ).update(
            source_id=eobj.source_id,
            earliest=eobj.earliest,
            start=eobj.start,
            stop=eobj.stop,
            latest=eobj.latest,
            updated=eobj.updated,
            when_type=eobj.when_type,
        )
        print(f'Event {eobj.hash_id} updated {n} on prod')