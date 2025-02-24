import copy
import hashlib
from operator import sub
import re

import numpy as np
import pandas as pd

from django.core.cache import caches
from django.db.models import Q
from django.db.models.functions import Length

from opencontext_py.apps.all_items.models import (
    AllManifest,
    AllAssertion,
)
from opencontext_py.apps.all_items.legacy_all import update_old_id

from opencontext_py.apps.etl.importer.models import (
    DataSourceField,
    DataSourceAnnotation,
)

from opencontext_py.apps.all_items import configs

from opencontext_py.apps.all_items.editorial.api import get_man_obj_by_any_id


from opencontext_py.apps.etl.kobo import pc_configs
from opencontext_py.apps.etl.kobo import utilities

RECONCILE_PROJECT_IDS = [
    configs.OPEN_CONTEXT_PROJ_UUID,
    pc_configs.PROJECT_UUID,
]

def make_cache_key(item_id):
    hash_obj = hashlib.sha1()
    item_id = str(item_id)
    hash_obj.update(item_id.encode('utf-8'))
    return 'key-' + hash_obj.hexdigest()


def cache_get_man_obj_by_any_id(item_id):
    cache_key = make_cache_key(item_id)
    cache = caches['redis']
    item_obj = cache.get(cache_key)
    if item_obj:
        return item_obj
    item_obj = get_man_obj_by_any_id(item_id)
    try:
        cache.set(cache_key, item_obj)
    except:
        pass
    return item_obj


def db_reconcile_manifest_obj(
    item_type,
    item_label,
    item_class_obj,
    item_any_id=None,
    context=None,
    reconcile_project_ids=None,
    item_data_type='id',
    meta_json=None,
):
    """Attempts to reconcile a manifest item via arguments."""
    if not meta_json:
        meta_json = {}

    if not reconcile_project_ids:
        reconcile_project_ids = copy.deepcopy(RECONCILE_PROJECT_IDS)

    if context and item_type == 'subjects' and context.item_type == 'projects':
        # We are only trying to reconcile by a project, we lack a
        # parent spatial context for item
        reconcile_project_ids.append(context.uuid)
        context = None

    item_label = AllManifest().clean_label(item_label)
    man_qs = AllManifest.objects.filter(
        project_id__in=reconcile_project_ids,
        item_type=item_type,
        data_type=item_data_type,
    )
    if context:
        if item_type == 'subjects' and context.item_type == 'projects':
            # Don't do a context filter.
            pass
        else:
            man_qs = man_qs.filter(context=context)

    if not item_any_id:
        item_any_id = item_label

    if item_type in configs.URI_CONTEXT_PREFIX_ITEM_TYPES:
        # Some flexibility in reconcile these.
        man_qs = man_qs.filter(
            Q(uri=AllManifest().clean_uri(item_any_id))
            | Q(item_key=item_any_id)
            | Q(slug=item_any_id)
            | Q(label=item_label)
        )
    elif item_type == 'persons' and meta_json.get('reconcile_on_initials'):
        # We're allowing reconciliation on initials.
        man_qs = man_qs.filter(
            Q(meta_json__initials=item_label)
            | Q(meta_json__combined_name=item_label)
            | Q(label=item_label)
        )
    elif item_type == 'persons' and not meta_json.get('reconcile_on_initials'):
        # We're reconciling a persons item, but not with initials.
        man_qs = man_qs.filter(
            Q(meta_json__combined_name=item_label)
            | Q(label=item_label)
        )
    else:
        # Use the label as the main identifier (obviously with other
        # filter to contextualize)
        man_qs = man_qs.filter(
            Q(label=item_label)
            | Q(slug=item_any_id)
        )

    if (item_type == 'predicates'
        and (
            not item_class_obj
            or
            str(item_class_obj.uuid) not in configs.CLASS_LIST_OC_PREDICATES
        )
    ):
        # We are attempting to reconcile an item_type = 'predicates'
        # item, but we don't have a correct record_item_class_obj set. So
        # default to the class for a variable (not a link)
        item_class_obj = cache_get_man_obj_by_any_id(
            configs.CLASS_OC_VARIABLES_UUID
        )

    if item_class_obj:
        man_qs = man_qs.filter(item_class=item_class_obj)

    # Now handle the results where of our query to attempt to
    # find matching records for this specific item.
    num_matching = len(man_qs)
    if num_matching == 1:
        # We have found exactly one match for this, meaning this
        # entity already exists so return it
        return man_qs[0], num_matching
    return None, num_matching



def db_reconcile_trench_unit(trench_id, trench_year):
    """Database reconciliation of a trench unit"""
    trench_year = int(float(trench_year))
    map_dict = utilities.get_trench_unit_mapping_dict(trench_id)
    if not map_dict:
        return None
    if '_' in trench_id:
        # no spaces if we have an underscore trench_id
        trench_id = trench_id.replace(' ', '')
    if ' ' in trench_id:
        t_ex = trench_id.split(' ')
        if t_ex[-1].isnumeric():
            trench_id = t_ex[0]
    unit_num = ''.join([c for c in trench_id if c.isnumeric()])
    if unit_num.endswith(str(trench_year)):
        unit_num = unit_num[0:-(len(str(trench_year)))]
    if not map_dict.get('prefix'):
        trench_name = f"{map_dict['area']} {unit_num}"
        b_trench_name = f"{map_dict['area']}{unit_num}"
    else:
        trench_name = f"{map_dict['prefix']} {unit_num}"
        b_trench_name = f"{map_dict['prefix']}{unit_num}"
    search_path = f"{map_dict['site']}/{map_dict['area']}/{trench_name}"
    b_search_path = f"{map_dict['site']}/{map_dict['area']}/{b_trench_name}"
    man_qs = AllManifest.objects.filter(
        item_type='subjects',
        project__uuid=pc_configs.PROJECT_UUID,
        label__contains=str(trench_year),
        item_class__slug='oc-gen-cat-exc-unit',
    ).filter(
        Q(path__contains=search_path)
        |Q(path__contains=b_search_path)
    ).select_related('context')
    if man_qs.count() == 1:
        # Happy scenario where we found exactly 1, unambiguous match!
        return man_qs[0]
    elif man_qs.count() > 1:
        print(
            f'WARNING: Found {man_qs.count()} matches for '
            f'unit number: {unit_num}, year {trench_year} in {search_path}'
        )
        return man_qs[0]
    print(
        f'PROBLEM: Found NO matches for '
        f'unit number: {unit_num}, year {trench_year} in {search_path} or {b_search_path}'
    )
    return None


def db_reconcile_locus(unit_uuid, locus_name):
    """Database reconciliation of a locus within a unit"""
    man_qs = AllManifest.objects.filter(
        item_type='subjects',
        project__uuid=pc_configs.PROJECT_UUID,
        label=locus_name,
        item_class__slug='oc-gen-cat-locus',
        context__uuid=unit_uuid
    ).select_related('context')
    if man_qs.count() == 1:
        # Happy scenario where we found exactly 1, unambiguous match!
        return man_qs[0]
    elif man_qs.count() > 1:
        print(
            f'PROBLEM: Found {man_qs.count()} matches for '
            f'locus: {locus_name} in {unit_uuid}'
        )
    print(
        f'PROBLEM: Found NO matches for '
        f'locus: {locus_name} in {unit_uuid}'
    )
    return None



def db_lookup_manifest_obj(
    label,
    item_type,
    label_alt_configs=None,
    class_slugs=None,
    trench_id=None,
    trench_year=None,
    unit_uuid=None,
    locus_name=None,
    project_uuid=pc_configs.PROJECT_UUID,
):
    """Returns a manifest object based on label variations"""
    if unit_uuid and locus_name and 'oc-gen-cat-locus' in class_slugs:
        return db_reconcile_locus(unit_uuid, locus_name)
    if trench_id and trench_year and 'oc-gen-cat-locus' in class_slugs:
        unit_obj = db_reconcile_trench_unit(trench_id, trench_year)
        if not unit_obj:
            return None
        return  db_reconcile_locus(unit_obj.uuid, label)
    if trench_id and trench_year and 'oc-gen-cat-exc-unit' in class_slugs:
        return db_reconcile_trench_unit(trench_id, trench_year)
    if trench_year and 'oc-gen-cat-exc-unit' in class_slugs:
        return db_reconcile_trench_unit(label, trench_year)
    label_variations = utilities.get_alternate_labels(
        label,
        project_uuid,
        config=label_alt_configs
    )
    man_objs = AllManifest.objects.filter(
        label__in=label_variations,
        item_type=item_type,
        project__uuid=project_uuid
    )
    if class_slugs is not None:
        # Further filter if we have slugs for item classes
       man_objs = man_objs.filter(item_class__slug__in=class_slugs)
    man_obj = man_objs.first()
    return man_obj


def db_lookup_trenchbooks_linked_to_trench_id(trench_id, trench_year):
    """Gets a list of documents uuids that are linked to a given trench id."""
    # Get mappings for the trench_id and more canonical names
    unit_obj = db_reconcile_trench_unit(trench_id, trench_year)
    if not unit_obj:
        return None
    # Now get the document items that are related to the trench_id and
    # its child items
    linked_docs_qs = AllAssertion.objects.filter(
        subject=unit_obj,
        object__item_type='documents'
    )
    # Make a list of the document uuids
    doc_uuids = [str(a.object.uuid) for a in linked_docs_qs]
    return doc_uuids

def int_convert(val):
    try:
        int_val = int(float(val))
    except:
        int_val = None
    return int_val

def db_lookup_trenchbook(trench_id, trench_year, entry_date, start_page, end_page):
    """Look up trenchbook entries via database queries."""
    trench_year = int_convert(trench_year)
    start_page = int_convert(start_page)
    end_page = int_convert(end_page)
    doc_uuids = db_lookup_trenchbooks_linked_to_trench_id(trench_id, trench_year)
    if not doc_uuids:
        return None
    if isinstance(entry_date, pd.Timestamp):
        entry_date = entry_date.strftime('%Y-%m-%d')

    # Further filter the documents for the ones on the correct date.
    tb_qs = AllManifest.objects.filter(
        uuid__in=doc_uuids,
        item_type='documents',
        label__contains=entry_date,
    ).annotate(
        label_len=Length('label'),
    ).order_by(
        'sort', 'label_len', 'label'
    )
    if len(tb_qs) == 0:
        # Match on page numbers only, so don't
        # worry about the specific date of the trench
        # book entry.
        tb_qs = AllManifest.objects.filter(
            uuid__in=doc_uuids,
            item_type='documents',
        ).order_by(
            'sort', 'label'
        )
    if len(tb_qs) == 0:
        print(f'No trench book for trench id: {trench_id}, date: {entry_date}')
        # Sad case, not found at all.
        return None
    if len(tb_qs) == 1:
        # Happy case, no need to match pages.
        print(f'One trench book match for trench id: {trench_id}, date: {entry_date}')
        return tb_qs[0]
    if not start_page:
        return tb_qs[0]
    # OK, now try to narrow down by pages
    tb_uuids = [str(m.uuid) for m in tb_qs]
    ass_start_qs = AllAssertion.objects.filter(
        subject_id__in=tb_uuids,
        predicate_id=pc_configs.TB_START_PAGE_PRED_UUID,
        obj_integer__gte=start_page
    ).order_by(
        'obj_integer'
    )
    if len(ass_start_qs) < 1:
        print(f'No trench book match for trench id: {trench_id}, start page: {start_page}')
        return None
    st_uuids = list(set([str(a.subject.uuid) for a in ass_start_qs]))
    if len(st_uuids) == 1 or not end_page:
        # We found it by the only matched page start
        return ass_start_qs[0].subject
    ass_end_qs = AllAssertion.objects.filter(
        subject_id__in=st_uuids,
        predicate_id=pc_configs.TB_END_PAGE_PRED_UUID,
        obj_integer__lte=end_page
    ).order_by(
        'obj_integer'
    )
    if len(ass_end_qs) < 1:
        print(f'No trench book match for trench id: {trench_id}, pages: {start_page} to {end_page}')
        return None
    # Return the first match
    return ass_end_qs[0].subject


def db_lookup_smallfind(
    trench_id,
    trench_year,
    locus_id,
    find_number,
):
    """Looks up a small find record from the Manifest."""
    unit_obj = db_reconcile_trench_unit(trench_id, trench_year)
    if not unit_obj:
        return None

    man_obj_qs = AllManifest.objects.filter(
        project_id=pc_configs.PROJECT_UUID,
        item_type='subjects',
        item_class__slug='oc-gen-cat-sample',
        label__endswith=f'-{locus_id}-{find_number}'
    ).filter(
        context__label=f'Locus {locus_id}',
        context__item_class__slug='oc-gen-cat-locus',
        context__context=unit_obj,
    )
    if len(man_obj_qs) == 1:
        # We have an exact match.
        return man_obj_qs[0]
    return None


def db_lookup_manifest_uuid(
    label,
    item_type,
    label_alt_configs=None,
    class_slugs=None
):
    """Returns a manifest object uuid on label variations"""
    man_obj = db_lookup_manifest_obj(
        label=label,
        item_type=item_type,
        label_alt_configs=label_alt_configs,
        class_slugs=class_slugs,
    )
    if man_obj is None:
        return None
    return str(man_obj.uuid)


def db_reconcile_by_labels_item_class_slugs(
    label_list,
    item_class_slug_list
):
    """Reconciles against the manifest by labels
    and item class slugs
    """
    man_qs = AllManifest.objects.filter(
        project_id=pc_configs.PROJECT_UUID,
        label__in=label_list,
        item_class__slug__in=item_class_slug_list
    )
    if man_qs.count() == 1:
        return man_qs[0]
    if man_qs.count() > 1:
        print(f'Ambiguous: {man_qs.count()} results for {label_list} item-class: {item_class_slug_list}')
    return None



def db_lookup_manifest_by_uri(uri, item_class_slugs=None):
    """Returns a manifest object uuid on label variations

    :param str uri: A URI to identify the item in the manifest
    :param list item_class_slugs: An optional list of
       slugs that we allow.
    """
    if not uri:
        return None
    uri = str(uri)
    uuid_part = None
    uri = AllManifest().clean_uri(uri)
    if '/' in uri:
        uri_ex = uri.split('/')
        _, uuid_part = update_old_id(uri_ex[-1])
    if uuid_part:
        man_qs = AllManifest.objects.filter(
            Q(uuid=uuid_part)
            |Q(uri=uri)
        )
    else:
        man_qs= AllManifest.objects.filter(
            uri=uri
        )
    if item_class_slugs:
        man_qs = man_qs.filter(
            item_class__slug__in=item_class_slugs,
        )
    return man_qs.first()


def get_related_object_from_item_label(item_label):
    clean_object_labels = utilities.get_related_object_labels_from_item_label(item_label)
    if not clean_object_labels:
        return None
    _, class_slugs = pc_configs.REL_SUBJECTS_PREFIXES.get('Cataloged Object', (None, None,))
    if not class_slugs:
        return None
    return db_reconcile_by_labels_item_class_slugs(
        label_list=clean_object_labels,
        item_class_slug_list=class_slugs,
    )

def check_catalog_item_exists(cat_label, new_cat_uuid=None):
    """Checks to see if a catalog item already exists"""
    output = {
        'catalog_name': cat_label,
        'catalog_uuid__to_match': new_cat_uuid,
        'match_count': 0,
        'uuid_match_exists': None,
        'assertion_count': 0,
        'found_label': None,
        'found_uuid': None,
        'man_obj': None,
    }
    clean_object_labels = utilities.get_related_object_labels_from_item_label(cat_label)
    if not clean_object_labels:
        return output
    _, class_slugs = pc_configs.REL_SUBJECTS_PREFIXES.get('Cataloged Object', (None, None,))
    if not class_slugs:
        return output
    man_qs = AllManifest.objects.filter(
        project_id=pc_configs.PROJECT_UUID,
        label__in=clean_object_labels,
        item_class__slug__in=class_slugs
    )
    output['match_count'] = man_qs.count()
    if output['match_count'] > 0:
        for man_obj in  man_qs:
            if str(man_obj.uuid) == new_cat_uuid:
                output['uuid_match_exists'] = True
                output['man_obj'] = man_obj
        if not output.get('man_obj'):
            output['man_obj'] = man_qs.first()
    if output.get('man_obj'):
        output['found_label'] = man_obj.label
        output['found_uuid'] = man_obj.uuid
        output['assertion_count'] = AllAssertion.objects.filter(
            subject=output.get('man_obj'),
        ).count()
        output.pop('man_obj')
    return output


def make_catalog_exists_df(df_cat_data, cat_label_col, cat_uuid_col):
    """Makes a dataframe of catalog items to check if they exist and have assertions"""
    if not set([cat_label_col, cat_uuid_col]).issubset(set(df_cat_data.columns.tolist())):
        return None
    rows = []
    index = ~df_cat_data[cat_label_col].isnull()
    for _, row in df_cat_data[index].iterrows():
        cat_label = str(row[cat_label_col])
        new_cat_uuid = None
        if isinstance(row[cat_uuid_col], str):
            new_cat_uuid = row[cat_uuid_col]
        check_output = check_catalog_item_exists(cat_label, new_cat_uuid)
        rows.append(check_output)
    df = pd.DataFrame(data=rows)
    return df