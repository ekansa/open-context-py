
import os

from opencontext_py.apps.all_items import configs
from opencontext_py.apps.all_items.models import (
    AllManifest,
    AllAssertion,
    AllHistory,
    AllResource,
    AllIdentifier,
    AllSpaceTime,
)

from opencontext_py.apps.all_items import defaults
from opencontext_py.apps.all_items import owl_vocabulary
from opencontext_py.apps.all_items import legacy_ld
from opencontext_py.apps.all_items import legacy_oc

"""
from pathlib import Path
from opencontext_py.apps.all_items.migrate import *
home = str(Path.home())
project_uuids = ['3', '3585b372-8d2d-436c-9a4c-b5c10fce3ccd', 'a52bd40a-9ac8-4160-a9b0-bd2795079203',]
p_ids = [
    '3F6DCD13-A476-488E-ED10-47D25513FCB2', 
    'b9472eec-e622-4838-b6d8-5a2958b9d4d3', 
    'a52bd40a-9ac8-4160-a9b0-bd2795079203', 
    'bc71c724-eb1e-47d6-9d45-b586ddafdcfe', 
    '95b1ef01-9ccb-4484-b0f2-540f4dc54672', 
    'a9dbf427-cff6-41b7-8462-a9ab8d9908f4', 
    '10aa84ad-c5de-4e79-89ce-d83b75ed72b5', 
    '141e814a-ba2d-4560-879f-80f1afb019e9', 
    'c89e6a9e-105a-4368-9e90-26940d7bf37a'
]
migrate_single_project('3', error_path=f'{home}/migration-errors')
"""

def migrate_all_general():
    """Migrates all general legacy data to the new schema"""

    defaults.verify_manifest_uuids()
    defaults.load_default_entities()

    # Now load in default Open Context vocabularies
    owl_vocabulary.load_vocabularies_and_related_namespaces()

    # Now migrate legacy linked data vocabularies, entities, and assertions
    legacy_ld.load_legacy_link_entities_vocabs()
    legacy_ld.load_legacy_link_entities()
    legacy_ld.migrate_legacy_link_annotations()

    # Now migrate legacy project '0' (Open Context) items
    legacy_oc.migrate_legacy_projects()
    legacy_oc.migrate_root_subjects()
    legacy_oc.migrate_legacy_manifest_for_project(project_uuid='0')
    legacy_oc.migrate_legacy_spacetime_for_project(project_uuid='0')
     # Now add the link data annotations specific to this project
    legacy_ld.migrate_legacy_link_annotations(
        project_uuid='0',
        more_filters_dict=None,
        use_cache=True,
    )


def migrate_single_project(old_project_uuid, error_path=''):
    """Fully migrates a single project, by reference to its old project_uuid"""
    project = legacy_oc.get_cache_new_manifest_obj_from_old_id(
        old_project_uuid, 
        use_cache=False,
    )
    legacy_oc.migrate_legacy_project_hero_media(old_project_uuid, new_proj_man_obj=project)
    legacy_oc.migrate_legacy_manifest_for_project(project_uuid=old_project_uuid)

    legacy_oc.migrate_legacy_spacetime_for_project(project_uuid=old_project_uuid)
    orig_assert_migrate_errors = legacy_oc.migrate_legacy_assertions_for_project(old_project_uuid)
    if orig_assert_migrate_errors:
        # Save the migration errors.
        file_name = f'assert-m-errors-{project.slug[:20]}.csv'
        file_path = os.path.join(error_path, file_name)
        legacy_oc.save_old_assertions_to_csv(file_path, orig_assert_migrate_errors)
    
    # Now add the link data annotations specific to this project
    legacy_ld.migrate_legacy_link_annotations(
        project_uuid=old_project_uuid,
        more_filters_dict=None,
        use_cache=True,
    )
    # Make sure any EOL related assertions are de-emphasized.
    legacy_ld.eol_assertion_fix(project_id=project.uuid)
