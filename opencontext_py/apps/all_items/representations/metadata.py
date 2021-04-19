
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
from opencontext_py.apps.all_items.representations import rep_utils


# Make easy to look up manifest objects for dublin core metadata that
# we use for authorship, based on equivalence relationships with other predicates.
# This lets us avoid a query to the database to look up these manifest objects.
DC_CREATOR_CONTRIBUTOR_OBJECTS = {
    configs.PREDICATE_DCTERMS_CONTRIBUTOR_UUID: AllManifest(**configs.DCTERMS_CONTRIBUTOR_MANIFEST_DICT),
    configs.PREDICATE_DCTERMS_CREATOR_UUID: AllManifest(**configs.DCTERMS_CREATOR_MANIFEST_DICT),
}

DC_DEFAULT_LICENSE_OBJECT = AllManifest(**configs.CC_DEFAULT_LICENSE_CC_BY_DICT)

DC_IS_PART_OF_OBJECT = AllManifest(**configs.DCTERMS_CREATOR_IS_PART_OF_DICT)
DC_HAS_PART_OBJECT = AllManifest(**configs.DCTERMS_CREATOR_HAS_PART_DICT)


def add_dc_creator_contributor_equiv_metadata(assert_qs, act_dict=None):
    """Makes a dictionary keyed by DC creator or contributor id with
    equivalent assertion objects

    :param QuerySet assert_qs: An assertion object queryset for assertions
        that describe the item for which we're creating a representation
    :param dict act_dict: The dictionary object that is being created as 
        a representation of an item.
    """
    equiv_dict = {}
    for assert_obj in assert_qs:
        predicate_dc_creator = None
        predicate_dc_contributor = None
        if str(assert_obj.predicate.uuid) == configs.PREDICATE_DCTERMS_CREATOR_UUID:
            # The item itself has a creator assertion
            predicate_dc_creator = assert_obj.predicate
        elif str(assert_obj.predicate.uuid) == configs.PREDICATE_DCTERMS_CONTRIBUTOR_UUID:
            # The item itself as a contributor assertion
            predicate_dc_contributor = assert_obj.predicate
        elif assert_obj.predicate_dc_creator:
            # The assertion is equivalent to a dublin core creator assertion.
            predicate_dc_creator = DC_CREATOR_CONTRIBUTOR_OBJECTS.get(
                str(assert_obj.predicate_dc_creator)
            )
        elif assert_obj.predicate_dc_contributor:
            # The assertion is equivalent to a dublin core contributor assertion.
            predicate_dc_contributor = DC_CREATOR_CONTRIBUTOR_OBJECTS.get(
                str(assert_obj.predicate_dc_contributor)
            )
        else:
            # The assertion has nothing to do with Dublin Core creators or contributors
            continue
        if predicate_dc_creator:
            equiv_dict.setdefault(predicate_dc_creator, [])
            equiv_dict[predicate_dc_creator].append(assert_obj)
        if predicate_dc_contributor:
            equiv_dict.setdefault(predicate_dc_contributor, [])
            equiv_dict[predicate_dc_contributor].append(assert_obj)
    if not equiv_dict:
        # No dublin core equivalences found, so skip.
        return act_dict
    # Return the act_dict with the Dublin core creator and/or contributors
    # added.
    return rep_utils.add_predicates_assertions_to_dict(equiv_dict, act_dict=act_dict)


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


def add_dublin_core_literal_metadata(item_man_obj, rel_subjects_man_obj=None, act_dict=None):
    """Adds Dublin Core (literal) metadata"""
    if not act_dict:
        act_dict = LastUpdatedOrderedDict()
    if item_man_obj.item_type == 'subjects':
        from_path = '/'.join((item_man_obj.path.split('/'))[:-1])
        act_dict['dc-terms:title'] = f'{item_man_obj.label} from {from_path}'
    elif rel_subjects_man_obj and item_man_obj.item_type in ['media', 'documents']:
        act_dict['dc-terms:title'] = f'{item_man_obj.label} from {rel_subjects_man_obj.path}'
    else:
        act_dict['dc-terms:title'] = item_man_obj.label
    # NOTE: Adds DC date metadata
    if item_man_obj.published:
        act_dict['dc-terms:issued'] = item_man_obj.published.date().isoformat()
    if item_man_obj.revised:
        act_dict['dc-terms:modified'] = item_man_obj.revised.date().isoformat()
    return act_dict


def check_add_default_license(act_dict=None):
    """Adds a default license if no license already exists"""
    if not act_dict:
        act_dict = LastUpdatedOrderedDict()
    if len(act_dict.get('dc-terms:license', [])) > 0:
        return act_dict
    
    lic_uri = AllManifest().clean_uri(DC_DEFAULT_LICENSE_OBJECT.uri)
    lic_dict = LastUpdatedOrderedDict()
    lic_dict['id'] = f'https://{lic_uri}'
    lic_dict['slug'] = DC_DEFAULT_LICENSE_OBJECT.slug
    lic_dict['label'] = DC_DEFAULT_LICENSE_OBJECT.label
    act_dict['dc-terms:license'] = [lic_dict]
    return act_dict


def check_add_project(project, act_dict=None):
    """Adds a Dublin Core Part-of relationship for the project"""
    if not act_dict:
        act_dict = LastUpdatedOrderedDict()
    if len(act_dict.get('dc-terms:isPartOf', [])) > 0:
        return act_dict
    
    proj_dict = LastUpdatedOrderedDict()
    proj_dict['id'] = f'https://{project.uri}'
    proj_dict['slug'] = project.slug
    proj_dict['label'] = project.label
    act_dict['dc-terms:isPartOf'] = [proj_dict]
    return act_dict