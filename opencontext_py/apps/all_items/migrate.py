
import uuid as GenUUID
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


def migrate_single_project(old_project_uuid, error_path=''):
    """Fully migrates a single project, by reference to its old project_uuid"""
    project = legacy_oc.get_cache_new_manifest_obj_from_old_id(
        old_project_uuid, 
        use_cache=False,
    )
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