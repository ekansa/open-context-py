import datetime
import pandas as pd

from django.db.models import Q

from opencontext_py.apps.persistent_ids.ezid.ezid import EZID
from opencontext_py.apps.persistent_ids.ezid.metaark import metaARK
from opencontext_py.apps.persistent_ids.ezid.metadoi import metaDOI
from opencontext_py.apps.persistent_ids.ezid.manage import EZIDmanage

from opencontext_py.apps.all_items import configs
from opencontext_py.apps.all_items.models import (
    AllManifest,
    AllIdentifier,
)
from opencontext_py.apps.all_items.representations import item

# Old item data
from opencontext_py.apps.all_items.legacy_all import update_old_id
from opencontext_py.apps.ocitems.manifest.models import Manifest as OldManifest

"""
Example.

import importlib
from opencontext_py.apps.persistent_ids.ezid import fix_broken as ezid_fb
importlib.reload(ezid_fb)

path = '~/data-dumps/bad_links.csv'

ezid_fb.update_ezid_bad_links(path=path, show_ezid_resp=True)
"""


def read_prepare_ezid_bad_links_csv(path):
    """Reads and prepares a CSV file of EZID reported bad links"""
    df = pd.read_csv(path)
    if not 'fixed' in df.columns:
        df['fixed'] = False
    if not 'new_url' in df.columns:
        df['new_url'] = ''
    if not 'resolution_note' in df.columns:
        df['resolution_note'] = ''
    if not 'last_step' in df.columns:
        df['last_step'] = 0
    return df


def get_id_scheme_from_ezid_identifier(identifier):
    id = None
    scheme = None
    if identifier.startswith('ark:/'):
        scheme = 'ark'
        id = identifier.split('ark:/')[-1]
    if identifier.startswith('doi:'):
        scheme = 'doi'
        id = identifier.split('doi:')[-1]
    return id, scheme


def get_item_type_from_target_url(targ_url):
    """Gets the item type from a target URL"""
    for check_type in configs.OC_ITEM_TYPES:
        url_type = f'/{check_type}/'
        if url_type in targ_url:
           return check_type
    return None

def lookup_legacy_manifest_obj(targ_url):
    """Looks up a legacy manifest object from a target URL"""
    targ_url = AllManifest().clean_uri(targ_url)
    item_type = get_item_type_from_target_url(targ_url)
    if not item_type:
        return None
    id = targ_url.split(f'/{item_type}/')[-1]
    if not item_type or not id:
        return None
    old_man_obj = OldManifest.objects.filter(
        item_type=item_type,
        uuid=id,
    ).first()
    return old_man_obj


def lookup_current_manifest_obj(targ_url):
    """Looks up a current manifest object from a target URL"""
    old_man_obj = lookup_legacy_manifest_obj(targ_url)
    if not old_man_obj:
        return None
    _, new_uuid = update_old_id(old_man_obj.uuid)
    man_obj = AllManifest.objects.filter(
        Q(uuid=new_uuid) | Q(meta_json__legacy_id=old_man_obj.uuid)
    ).first()
    if man_obj:
        return man_obj
    # Try to get the item from the item type and label
    _, new_proj_uuid = update_old_id(old_man_obj.project_uuid)
    man_obj = AllManifest.objects.filter(
        project_id=new_proj_uuid,
        item_type=old_man_obj.item_type,
        label=old_man_obj.label,
    ).first()
    return man_obj


def lookup_current_project_manifest_obj(targ_url):
    """Gets the current project for a legacy manifest object"""
    old_man_obj = lookup_legacy_manifest_obj(targ_url)
    if not old_man_obj:
        return None, None
    _, new_proj_uuid = update_old_id(old_man_obj.project_uuid)
    man_obj = AllManifest.objects.filter(
        project_id=new_proj_uuid,
        item_type='projects',
    ).first()
    return man_obj, old_man_obj.label


def lookup_current_table_man_obj(targ_url, label):
    """Looks up a current table manifest object from a target url"""
    targ_url = AllManifest().clean_uri(targ_url)
    item_type = get_item_type_from_target_url(targ_url)
    if item_type != 'tables':
        return None
    man_obj = AllManifest.objects.filter(
        item_type=item_type,
        label=label,
    ).first()
    return man_obj


def look_up_current_proj_from_label_text(label):
    """Looks up a current project from text within a label"""
    config_tups = [
        ('Bulgaria/Tundzha Study Area', '24e2aa20-59e6-4d66-948b-50ee245a7cfc',),
    ]
    man_obj = None
    for check_text, proj_uuid in config_tups:
        if check_text in label:
            man_obj = AllManifest.objects.filter(
                uuid=proj_uuid,
                item_type='projects',
            ).first()
            break
    return man_obj, label


def update_ezid_id_metadata(
    man_obj,
    id,
    scheme,
    ezid_client=None,
    show_ezid_resp=False,
    deprecate_to_proj=None,
):
    """Updates the metadata for an identifier"""
    ezid_m = EZIDmanage()
    metadata = ezid_m.make_ark_metadata_by_uuid(man_obj=man_obj, verbatim_id=man_obj.label)
    if not metadata:
        raise ValueError(f'Could not generate ARK metadata for {man_obj.label} [{str(man_obj.uuid)}]')
    if deprecate_to_proj:
        dep_key = None
        dep_val = None
        for key, value in metadata.items():
            if key.endswith('.what'):
                dep_key = key
                dep_val = f'Deprecated item: "{deprecate_to_proj}", Removed from project: {value}'
                break
        if dep_key and dep_val:
            metadata[dep_key] = dep_val
    if not ezid_client:
        ezid_client = EZID()
    oc_uri = metadata.get('_target', f'https://{man_obj.uri}')
    # The create is also an update.
    if scheme == 'ark':
        ezid_id = f'ark:/{id}'
    if scheme == 'doi':
        ezid_id = f'doi:{id}'
    ezid_client.create_ark_identifier(
        oc_uri=oc_uri,
        metadata=metadata,
        id_str=ezid_id,
        update_if_exists=True,
        show_ezid_resp=show_ezid_resp,
    )


def update_ezid_links_for_known_ids(df, ezid_client=None, show_ezid_resp=False, step=1):
    """Updates the EZID links for known IDs"""
    broken_index = df['fixed'] == False
    for i, row in df[broken_index].iterrows():
        identifier = row['identifier']
        id, scheme = get_id_scheme_from_ezid_identifier(identifier)
        if not id or not scheme:
            continue
        if scheme == 'doi':
            print(f'Skip automatic processing of DOI: {id}')
            continue
        print(f'Check EZID for {id} [{scheme}]')
        id_obj = AllIdentifier.objects.filter(
            id=id,
            scheme=scheme,
        ).first()
        if not id_obj:
            # Sadly, we could not use this simple fix.
            continue
        update_ezid_id_metadata(
            man_obj=id_obj.item,
            id=id,
            scheme=scheme,
            ezid_client=ezid_client,
            show_ezid_resp=show_ezid_resp,
        )
        fix_index = df['identifier'] == identifier
        df.loc[fix_index, 'fixed'] = True
        df.loc[fix_index, 'new_url'] = f'https://{id_obj.item.uri}'
        df.loc[fix_index, 'resolution_note'] = 'Updated EZID resolution to match OC database'
    return df


def update_ezid_links_for_updated_items(df, ezid_client=None, show_ezid_resp=False, step=2):
    """Updates the EZID links for known IDs"""
    broken_index = df['fixed'] == False
    for i, row in df[broken_index].iterrows():
        identifier = row['identifier']
        id, scheme = get_id_scheme_from_ezid_identifier(identifier)
        if not id or not scheme:
            continue
        if scheme == 'doi':
            print(f'Skip automatic processing of DOI: {id}')
            continue
        man_obj = lookup_current_manifest_obj(row['target URL'])
        if not man_obj:
            # Sadly, we could not use this simple fix.
            continue
        update_ezid_id_metadata(
            man_obj=man_obj,
            id=id,
            scheme=scheme,
            ezid_client=ezid_client,
            show_ezid_resp=show_ezid_resp,
        )
        fix_index = df['identifier'] == identifier
        df.loc[fix_index, 'fixed'] = True
        df.loc[fix_index, 'new_url'] = f'https://{man_obj.uri}'
        df.loc[fix_index, 'resolution_note'] = 'Updated EZID resolution to updated OC item'
    return df


def update_ezid_links_for_removed_items(df, ezid_client=None, show_ezid_resp=False, step=3):
    """Updates the EZID links for known IDs"""
    broken_index = df['fixed'] == False
    for i, row in df[broken_index].iterrows():
        identifier = row['identifier']
        id, scheme = get_id_scheme_from_ezid_identifier(identifier)
        if not id or not scheme:
            continue
        if scheme == 'doi':
            print(f'Skip automatic processing of DOI: {id}')
            continue
        man_obj, deprecate_to_proj  = lookup_current_project_manifest_obj(row['target URL'])
        if not man_obj:
            # Sadly, we could not use this simple fix.
            continue
        update_ezid_id_metadata(
            man_obj=man_obj,
            id=id,
            scheme=scheme,
            ezid_client=ezid_client,
            show_ezid_resp=show_ezid_resp,
            deprecate_to_proj=deprecate_to_proj,
        )
        fix_index = df['identifier'] == identifier
        df.loc[fix_index, 'fixed'] = True
        df.loc[fix_index, 'new_url'] = f'https://{man_obj.uri}'
        df.loc[fix_index, 'resolution_note'] = 'Updated EZID resolution to updated OC item'
    return df


def update_ezid_links_for_table_items(df, ezid_client=None, show_ezid_resp=False, step=3):
    """Updates the EZID links for known IDs"""
    broken_index = df['fixed'] == False
    for i, row in df[broken_index].iterrows():
        identifier = row['identifier']
        id, scheme = get_id_scheme_from_ezid_identifier(identifier)
        if not id or not scheme:
            continue
        if scheme == 'doi':
            print(f'Skip automatic processing of DOI: {id}')
            continue
        man_obj = lookup_current_table_man_obj(
            targ_url=row['target URL'],
            label=row['resource title'],
        )
        if not man_obj:
            # Sadly, we could not use this simple fix.
            continue
        update_ezid_id_metadata(
            man_obj=man_obj,
            id=id,
            scheme=scheme,
            ezid_client=ezid_client,
            show_ezid_resp=show_ezid_resp,
            deprecate_to_proj=None,
        )
        fix_index = df['identifier'] == identifier
        df.loc[fix_index, 'fixed'] = True
        df.loc[fix_index, 'new_url'] = f'https://{man_obj.uri}'
        df.loc[fix_index, 'resolution_note'] = 'Updated EZID resolution to updated OC table item'
    return df


def update_ezid_links_for_label_contains_text_items(df, ezid_client=None, show_ezid_resp=False, step=4):
    """Updates the EZID links for known IDs"""
    broken_index = df['fixed'] == False
    for i, row in df[broken_index].iterrows():
        identifier = row['identifier']
        id, scheme = get_id_scheme_from_ezid_identifier(identifier)
        if not id or not scheme:
            continue
        if scheme == 'doi':
            print(f'Skip automatic processing of DOI: {id}')
            continue
        man_obj, label = look_up_current_proj_from_label_text(
            label=row['resource title'],
        )
        if not man_obj:
            # Sadly, we could not use this simple fix.
            continue
        update_ezid_id_metadata(
            man_obj=man_obj,
            id=id,
            scheme=scheme,
            ezid_client=ezid_client,
            show_ezid_resp=show_ezid_resp,
            deprecate_to_proj=label,
        )
        fix_index = df['identifier'] == identifier
        df.loc[fix_index, 'fixed'] = True
        df.loc[fix_index, 'new_url'] = f'https://{man_obj.uri}'
        df.loc[fix_index, 'resolution_note'] = 'Updated EZID resolution to project for deleted item'
    return df


def update_ezid_bad_links(path, show_ezid_resp=False,):
    """Updates EZID to fix reported bad links"""
    df = read_prepare_ezid_bad_links_csv(path)
    ezid_client = EZID()
    if False:
        df = update_ezid_links_for_known_ids(
            df,
            ezid_client=ezid_client,
            show_ezid_resp=show_ezid_resp,
        )
        df.to_csv(path, index=False)
    if False:
        df = update_ezid_links_for_updated_items(
            df,
            ezid_client=ezid_client,
            show_ezid_resp=show_ezid_resp,
        )
        df.to_csv(path, index=False)
    if False:
        df = update_ezid_links_for_removed_items(
            df,
            ezid_client=ezid_client,
            show_ezid_resp=show_ezid_resp,
        )
        df.to_csv(path, index=False)
    if False:
        df = update_ezid_links_for_table_items(
            df,
            ezid_client=ezid_client,
            show_ezid_resp=show_ezid_resp,
        )
        df.to_csv(path, index=False)
    if True:
        df = update_ezid_links_for_label_contains_text_items(
            df,
            ezid_client=ezid_client,
            show_ezid_resp=show_ezid_resp,
        )
        df.to_csv(path, index=False)
    return df