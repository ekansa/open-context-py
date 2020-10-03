
import copy
import hashlib
import uuid as GenUUID

from django.core.cache import caches
from django.db.models import OuterRef, Subquery

from opencontext_py.libs.general import LastUpdatedOrderedDict

from opencontext_py.apps.all_items import configs
from opencontext_py.apps.all_items.models import (
    AllManifest,
    AllAssertion,
    AllHistory,
    AllResource,
    AllIdentifier,
    AllSpaceTime,
)
from opencontext_py.apps.all_items import utilities



def db_get_project_metadata_qs(project_id):
    """Get Dublin Core project metadata"""
    qs = AllAssertion.objects.filter(
        subject_id=project_id,
        predicate__context_id=configs.DCTERMS_VOCAB_UUID,
        predicate__data_type='id',
        visible=True,
    ).select_related(
        'predicate'
    ).select_related( 
        'object'
    )
    return qs


def get_project_metadata_qs(project=None, project_id=None, use_cache=True):
    """Get Dublin Core project metadata via the cache"""
    if not project and project_id:
        project = AllManifest.objects.filter(uuid=project_id).first()
    if not project:
        return None

    if not use_cache:
        # Skip the case, just use the database.
        return db_get_project_metadata_qs(project_id=project.uuid)

    cache_key = f'proj-meta-{project.slug}'
    cache = caches['memory']

    proj_meta_qs = cache.get(cache_key)
    if proj_meta_qs is not None:
        # We've already cached this, so returned the cached queryset
        return proj_meta_qs

    proj_meta_qs = db_get_project_metadata_qs(project_id=project.uuid)
    try:
        cache.set(cache_key, proj_meta_qs)
    except:
        pass
    return proj_meta_qs


def add_dublin_core_literal_metadata(subject, assert_qs, act_dict=None):
    """Adds Dublin Core (literal) metadata"""
    if not act_dict:
        act_dict = LastUpdatedOrderedDict()
    if subject.item_type == 'subjects':
        from_path = '/'.join((subject.path.split('/'))[:-1])
        act_dict['dc-terms:title'] = f'{subject.label} from {from_path}'
    elif subject.item_type in ['media', 'documents']:
        subj_path = None
        for assert_obj in assert_qs:
            if assert_obj.object.item_type != 'subjects':
                continue
            subj_path = '/'.join(assert_obj.object.path.split('/'))
            break
        if subj_path:
            act_dict['dc-terms:title'] = f'{subject.label} from {subj_path}'
        else:
            act_dict['dc-terms:title'] = subject.label
    else:
        act_dict['dc-terms:title'] = subject.label
    # NOTE: Adds DC date metadata
    act_dict['dc-terms:issued'] = subject.published.date().isoformat()
    act_dict['dc-terms:modified'] = subject.revised.date().isoformat()
    return act_dict