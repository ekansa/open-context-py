import os
import shutil
from time import sleep

from django.db.models import OuterRef, Subquery

from django.conf import settings
from opencontext_py.libs.general import LastUpdatedOrderedDict

from opencontext_py.apps.archive import utilities as zen_utilities
from opencontext_py.apps.archive import metadata as zen_metadata
from opencontext_py.apps.archive.zenodo import ArchiveZenodo

from opencontext_py.apps.all_items import configs
from opencontext_py.apps.all_items.models import (
    AllManifest,
    AllAssertion,
    AllHistory,
    AllResource,
    AllIdentifier,
    AllSpaceTime,
)



from opencontext_py.apps.all_items.editorial.archive import file_utilities as fu
from opencontext_py.apps.all_items.editorial.synchronize import safe_model_save
from opencontext_py.apps.all_items.editorial.tables import create_df

from opencontext_py.apps.all_items.representations import item


"""
# Running this:
import importlib
from opencontext_py.apps.archive import structured as zen_struct

importlib.reload(zen_struct)

gather_external_manifest_dependency_entity_uuids(project_id)

"""


MODEL_PROJECT_FILTER_CONFIGS = {
    AllManifest: {
        'entity_uuid': 'uuid',
        'proj_filter': 'project_id',
    },
    AllSpaceTime: {
        'entity_uuid': 'item_id',
        'proj_filter': 'item__project_id',
    },
    AllAssertion: {
        'entity_uuid': 'subject_id',
        'proj_filter': 'subject__project_id',
    },
    AllResource: {
        'entity_uuid': 'item_id',
        'proj_filter': 'item__project_id',
    },
    AllHistory: {
        'entity_uuid': 'item_id',
        'proj_filter': 'item__project_id',
    },
    AllIdentifier: {
        'entity_uuid': 'item_id',
        'proj_filter': 'item__project_id',
    },
}

JSON_LD_ITEM_TYPES = [
    'projects',
    'subjects',
    'media',
    'documents',
    'persons',
    'types',
    'predicates',
    'tables',
]



def create_save_rep_dict(act_path, man_obj):
    """Creates a JSON-LD dictionary representation of an Open Context
    item to save in a file
    """
    if not isinstance(man_obj, AllManifest):
        return None
    _, rep_dict = item.make_representation_dict(
        subject_id=man_obj.uuid,
        for_solr=False,
    )
    item_type_path = os.path.join(act_path, man_obj.item_type)
    zen_utilities.save_serialized_json(
        path=item_type_path,
        filename=f'{str(man_obj.uuid)}.json',
        dict_obj=rep_dict,
    )


def gather_external_manifest_dependency_entity_uuids(entity_uuids, project_id):
    """Gathers all entity UUIDs that are external dependencies for a project
    """
    fk_man_attrs = safe_model_save.MODEL_FK_MANIFEST_ATTRIBUTES.get(
        AllManifest,
        [],
    )
    # 1. Filter the entity_uuids to only include those that are not in the project
    dep_uuids = set()
    for chunk_entity_uuids in create_df.chunk_list(entity_uuids):
        # We chunk the entity_uuids to avoid a large query
        m_qs = AllManifest.objects.filter(
            uuid__in=chunk_entity_uuids,
        ).exclude(
            project_id=project_id
        ).values_list(
            'uuid',
            flat=True,
        )
        dep_uuids.update(m_qs)
        # 2. Now gather all the foreign key dependencies for this chunk of entity_uuids.
        for fk_attr in fk_man_attrs:
            fk_uuid = f'{fk_attr}_id'
            exclude_args = {f'{fk_attr}__project_id': project_id}
            fk_qs = AllManifest.objects.filter(
                uuid__in=chunk_entity_uuids,
            ).exclude(
                **exclude_args
            ).order_by(
                fk_attr
            ).distinct(
                fk_attr
            ).values_list(fk_uuid, flat=True)
            dep_uuids.update(fk_qs)
    # 3. Now we can recursively gather foreign key dependencies for the dep_uuids
    # We will loop through this process until we run out of new dependencies to gather.
    continue_gathering = True
    loop_count = 0
    while continue_gathering:
        loop_count += 1
        current_count = len(dep_uuids)
        for chunk_dep_uuids in create_df.chunk_list(list(dep_uuids)):
            for fk_attr in fk_man_attrs:
                fk_uuid = f'{fk_attr}_id'
                exclude_args = {f'{fk_attr}__project_id': project_id}
                fk_qs = AllManifest.objects.filter(
                    uuid__in=chunk_dep_uuids,
                ).exclude(
                    **exclude_args
                ).order_by(
                    fk_attr
                ).distinct(
                    fk_attr
                ).values_list(fk_uuid, flat=True)
                dep_uuids.update(fk_qs)
        if len(dep_uuids) == current_count:
            continue_gathering = False
        if loop_count > 20:
            continue_gathering = False
    print(f'Gathered {len(dep_uuids)} external dependencies entity UUIDs from {loop_count} loops.')
    return dep_uuids


def gather_external_manifest_dependency_entity_uuids(project_id):
    """Gathers all entity UUIDs from external dependencies
    """
    entity_uuids = set()
    # 1. Gather all the entity UUIDs for the project
    for model, config_dict in MODEL_PROJECT_FILTER_CONFIGS.items():
        ent_attrib = config_dict['entity_uuid']
        proj_filter_dict = {config_dict['proj_filter']: project_id}
        qs = model.objects.filter(
            **proj_filter_dict
        ).values_list(
            ent_attrib,
            flat=True,
        )
        entity_uuids.update(qs)
        # 2. Now gather other related entities that are referenced by foreign keys
        # in rows defined by this model.
        fk_attrs = safe_model_save.MODEL_FK_MANIFEST_ATTRIBUTES.get(model, [])
        for fk_attr in fk_attrs:
            fk_uuid = f'{fk_attr}_id'
            if fk_uuid == ent_attrib:
                # we don't want to gather the same UUIDs twice
                continue
            fk_qs =  model.objects.filter(
                **proj_filter_dict
            ).values_list(
                fk_uuid,
                flat=True,
            )
            entity_uuids.update(fk_qs)
        print(f'Gathered {len(entity_uuids)} entity UUIDs after {model._meta.label}.')
    # 3. Now that we have all the entity UUIDs, we can gather all the external dependencies
    dep_uuids = gather_external_manifest_dependency_entity_uuids(
        entity_uuids=entity_uuids,
        project_id=project_id,
    )
    return dep_uuids