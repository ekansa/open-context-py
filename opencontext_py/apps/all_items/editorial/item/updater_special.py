import copy
from ipaddress import v4_int_to_packed

import reversion
 
from django.db.models import Q
from django.utils import timezone


from opencontext_py.apps.all_items import configs
from opencontext_py.apps.all_items.defaults import (
    DEFAULT_MANIFESTS,
)
from opencontext_py.apps.all_items.models import (
    AllManifest,
    AllAssertion,
    AllHistory,
    AllResource,
    AllIdentifier,
    AllSpaceTime,
)

from opencontext_py.apps.all_items import permissions
from opencontext_py.apps.all_items.editorial.item import updater_general
from opencontext_py.apps.all_items.editorial.item import item_validation
from opencontext_py.apps.all_items.editorial.item import edit_configs
from opencontext_py.apps.all_items.editorial.item import updater_manifest


from opencontext_py.apps.all_items.editorial.tables import cloud_utilities
from opencontext_py.apps.all_items.editorial.tables import metadata as tables_metadata

from opencontext_py.libs.models import (
    make_model_object_json_safe_dict
)


#----------------------------------------------------------------------
# NOTE: These are methods for handling requests to change make changes
# to many individual items based on commonly occurring circumstances (
# especially badly configured ETL/import jobs where problems get 
# discovered late)
# ---------------------------------------------------------------------

def recursive_merge_duplicate_subjects_by_path(
    keep_man_obj, 
    to_delete_man_obj,
    note=None, 
    merges=None, 
    errors=None, 
    warnings=None
):
    """Merges duplicate manifest objects sharing a common label but
    are in different context paths.

    :param AllManifest keep_man_obj: The manifest object that will be
        retained and has child objects that will be retained.
    :param AllManifest to_delete_man_obj: The manifest object that
        will be deleted after merging into the keep_man_obj. And it's children
        objects will be deleted.
    """
    # NOTE: This function will merge duplicate records inside context "paths".
    # Duplicates are identified by having the same item_class, project, label,
    # and mostly the same containment path (except for different roots of the
    # containment path). This function is needed to merge together duplicate
    # records created by error because of a root context had an unwanted
    # duplicate. For example, the records:
    #
    # (keep item) /Asia/Iraq/Surezha 
    # (to delete item) /Asia/Iraq/Tell Surezha (to delete item)
    #
    # This function would find and merge contexts like:
    # (keep item) /Asia/Iraq/Surezha/Operation 1/Locus 1
    # (to delete item) /Asia/Iraq/Tell Surezha/Operation 1/Locus 1
    # (keep item) /Asia/Iraq/Surezha/Operation 1
    # (to delete item) /Asia/Iraq/Tell Surezha/Operation 1
    # (keep item) /Asia/Iraq/Surezha
    # (to delete item) /Asia/Iraq/Tell Surezha
    #
    # If an item exists in the path that's being deleted but does not exist in
    # the corresponding keep_man_obj path, it will be RETAINED and it's context
    # will be updated into the appropriate context of the keep_man_obj path
    if note is None:
        note = ''
    if merges is None:
        merges = []
    if errors is None:
        errors = []
    if warnings is None:
        warnings = []
    keep_children_qs = AllManifest.objects.filter(
        path__startswith=keep_man_obj.path,
        item_type='subjects',
    ).order_by(
        '-path'
    ).exclude(
        uuid=keep_man_obj.uuid
    )
    merge_delete_tups = []
    for keep_child_obj in keep_children_qs:
        to_delete_path  = to_delete_man_obj.path + keep_child_obj.path.split(keep_man_obj.path)[-1]
        print('-'*50)
        print(f'Processing for a duplicate of keep item {keep_child_obj.path} in bad path {to_delete_path}')
        to_delete_child_obj = AllManifest.objects.filter(
            label=keep_child_obj.label,
            project=keep_child_obj.project,
            item_class=keep_child_obj.item_class,
            path=to_delete_path,
        ).exclude(
            uuid=keep_child_obj.uuid
        ).first()
        if not to_delete_child_obj:
            print(f'NO duplicate of keep item {keep_child_obj.path} in bad path {to_delete_path}')
            continue
        print(
            f'Found duplicate of keep item {keep_child_obj.label} ({keep_child_obj.uuid}) '
            f'is {to_delete_child_obj.label} ({to_delete_child_obj.uuid})'
        )
        merge_tup = (keep_child_obj, to_delete_child_obj,)
        merge_delete_tups.append(merge_tup)
    # Now add the final ones.
    final_tup = (keep_man_obj, to_delete_man_obj,)
    merge_delete_tups.append(final_tup)
    print(f'Ready to merge-delete {len(merge_delete_tups)} items with clearly identified duplicates')
    for keep_obj, delete_obj in merge_delete_tups:
        merges, errors, warnings = updater_manifest.merge_manifest_objs(
            keep_man_obj=keep_obj, 
            to_delete_man_obj=delete_obj, 
            note=note, 
            merges=merges, 
            errors=errors, 
            warnings=warnings
        )
    print(f'FINISHED merge-delete. Merges: {len(merges)}; Errors: {len(errors)}; Warnings: {len(warnings)}')
    return  merges, errors, warnings