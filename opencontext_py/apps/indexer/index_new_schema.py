import datetime
from datetime import timezone
import logging
from re import U
import time
from time import sleep

from itertools import islice

from django.conf import settings
from django.core.cache import caches

from django.db.models import Q

from opencontext_py.apps.all_items import configs
from opencontext_py.apps.all_items.models import AllAssertion, AllManifest
from opencontext_py.apps.all_items.project_contexts.context import (
    clear_project_context_df_from_cache
)
from opencontext_py.apps.all_items.representations import metadata as rep_metadata

from opencontext_py.libs.solrclient import SolrClient
from opencontext_py.apps.indexer.solrdocument_new_schema import SolrDocumentNS
from opencontext_py.apps.indexer import index_site_pages as isp

from opencontext_py.apps.searcher.new_solrsearcher import configs as solr_search_configs


"""
# testing

import importlib
import logging
from opencontext_py.apps.all_items.models import (
    AllManifest,
    AllAssertion,
    AllIdentifier,
)
from opencontext_py.apps.all_items import configs
from opencontext_py.apps.searcher.new_solrsearcher import suggest
from opencontext_py.apps.indexer import index_new_schema as new_ind
importlib.reload(new_ind)


new_ind.make_indexed_solr_documents_in_chunks(uuids, start_clear_caches=False)
suggest.get_rebuild_solr_suggest()


m_qs = AllManifest.objects.filter(item_type__in=['projects', 'subjects', 'media', 'documents', 'tables'])
m_qs = m_qs.order_by('project', 'item_type', 'item_class', 'sort')
uuids = m_qs.values_list('uuid', flat=True)[1325800:]



d_slugs = [
    '52-georgia-archaeological-site-file-gasf',
    '52-florida-site-files',
    '52-south-carolina-shpo',
    '52-missouri-site-files',
    '52-indiana-site-files',
    '52-kentucky-site-files',
    '52-illinois-site-files',
    '52-iowa-site-files',
    '52-digital-index-of-north-american-archaeology-dinaa',
    '52-alabama-site-files',
    '52-virginia-site-files',
    '52-louisiana-site-files',
    '52-maryland-site-files',
    '52-pennsylvania-site-files',
    '52-ohio-site-files',
    '52-north-carolina-site-files',
    '52-tennessee-site-files',
    '52-digital-index-of-north-american-archaeology-linking-si',
    '52-dinaa-sites-from-aggregate-totals',
]
m_qs = AllManifest.objects.filter(
    project__slug__in=d_slugs,
    item_type__in=['projects', 'subjects', 'media', 'documents'],
).order_by('project_id', 'sort')


new_ind.make_index_site_page_solr_documents()

# index things that aren't indexed or have new ids
ids_qs = AllIdentifier.objects.filter(
    item__item_type__in=['projects', 'subjects', 'media', 'documents'],
).select_related(
    'item'
).order_by(
    'item__project_id', 'item__sort'
)

uuids = [str(i.item.uuid) for i in ids_qs if not i.item.indexed or i.item.indexed < i.updated]

class_slugs = [
    'oc-gen-cat-bio-subj-ecofact',
    'oc-gen-cat-plant-remains',
    'oc-gen-cat-animal-bone',
    'oc-gen-cat-shell',
    'oc-gen-cat-human-bone',
    'oc-gen-cat-non-diag-bone',
    'oc-gen-cat-human-subj'
]
m_qs = AllManifest.objects.filter(
    item_class__slug__in=class_slugs
).exclude(
    indexed__gte='2022-10-25'
).order_by('project_id', 'sort')

# Reindex Getty AAT related items
all_uuids = new_ind.get_uuids_associated_with_vocab(vocab_uri='vocab.getty.edu/aat')
# Limit item type of reindexing, have good sorting.
m_qs = AllManifest.objects.filter(
    uuid__in=all_uuids,
    item_type__in=['projects', 'subjects', 'media', 'documents'],
).order_by('project_id', 'sort')
uuids = [str(m.uuid) for m in m_qs]
new_ind.clear_caches()
new_ind.make_indexed_solr_documents_in_chunks(uuids)
suggest.get_rebuild_solr_suggest()

# Gabii for now.
project_ids = ['3585b372-8d2d-436c-9a4c-b5c10fce3ccd', 'df043419-f23b-41da-7e4d-ee52af22f92f',]
m_qs = AllManifest.objects.filter(
    item_type__in=['projects', 'subjects', 'media', 'documents'],
    project_id__in=project_ids,
).order_by('project_id', 'sort')
uuids = [str(m.uuid) for m in m_qs]
new_ind.clear_caches()
new_ind.make_indexed_solr_documents_in_chunks(uuids)


p_uuids = AllAssertion.objects.all().distinct('predicate').order_by('predicate_id').values_list('predicate_id', flat=True)
uuids = []
for p_uuid in p_uuids:
    act_ass = AllAssertion.objects.filter(
        predicate_id=p_uuid, subject__item_type__in=['projects', 'subjects', 'media', 'documents'],
    ).exclude(subject_id__in=uuids).first()
    if act_ass:
        uuids.append(str(act_ass.subject.uuid))

# Update recently edited items
after_date = '2022-07-31'
m_qs = AllManifest.objects.filter(
    updated__gte=after_date,
    item_type__in=['projects', 'subjects', 'media', 'documents'],
)
uuids = [str(m.uuid) for m in m_qs]
a_uuids = AllAssertion.objects.filter(
    updated__gte=after_date,
    subject__item_type__in=['projects', 'subjects', 'media', 'documents'],
).distinct(
    'subject'
).order_by(
    'subject_id'
).values_list(
    'subject_id',
    flat=True
)
uuids += [str(u) for u in a_uuids if not str(u) in uuids]
new_ind.clear_caches()
new_ind.make_indexed_solr_documents_in_chunks(uuids)

"""


logger = logging.getLogger(__name__)

def get_crawl_rate_in_seconds(document_count, start_time):
    return str(round(document_count/(time.time() - start_time), 3))


def get_elapsed_time_in_seconds(start_time):
    return str(round((time.time() - start_time), 3))


def get_solr_connection():
    """ Connects to solr """
    if solr_search_configs.USE_TEST_SOLR_CONNECTION:
        # Connect to the testing solr server
        solr = SolrClient(use_test_solr=True).solr
    else:
        # Connect to the default solr server
        solr =  SolrClient().solr
    return solr

def clear_all_caches():
    """Clears caches to make sure reidexing uses fresh data. """
    cache_names = list(settings.CACHES.keys())
    for cache_name in cache_names:
        try:
            cache = caches[cache_name]
            cache.clear()
        except Exception as e:
            print(str(e))

def clear_caches():
    """Clears caches to make sure reidexing uses fresh data. """
    cache_names = ['redis_search', 'redis', 'default', 'memory']
    for cache_name in cache_names:
        try:
            cache = caches[cache_name]
            cache.clear()
        except Exception as e:
            print(str(e))

def clear_search_cache():
    """Clears only the search cache. """
    cache_names = ['redis_search', ]
    for cache_name in cache_names:
        try:
            cache = caches[cache_name]
            cache.clear()
        except Exception as e:
            print(str(e))


def chunk_list(act_list, chunk_size):
    """Break a list into smaller chunks"""
    # looping till length l
    for i in range(0, len(act_list), chunk_size):
        yield act_list[i:i + chunk_size]


def make_solr_documents(uuids):
    """Makes a list of solr documents"""
    solr_docs = []
    for uuid in uuids:
        solrdoc = SolrDocumentNS(uuid)
        if solrdoc.flag_do_not_index:
            print(f'Flagged to NOT index: {solrdoc.man_obj.label} [{uuid}]')
            continue
        ok = solrdoc.make_solr_doc()
        if not ok:
            logger.warn(f'Problem making solr doc for {str(uuid)}')
            print(f'Problem making solr doc for {str(uuid)}')
        solr_docs.append(solrdoc.fields)
    return solr_docs


def make_index_site_page_solr_documents(solr=None):
    if not solr:
        solr = get_solr_connection()
    solr_docs = isp.make_site_pages_solr_docs()
    try:
        solr.add(
            solr_docs,
            commit=False,
            overwrite=True,
        )
    except:
        for solr_doc in solr_docs:
            try:
                solr.add(
                    [solr_doc],
                    commit=False,
                    overwrite=True,
                )
            except:
                logger.warn(
                    f'Problem committing {solr_doc.get("uuid")}'
                )
                print(
                    f'Problem committing {solr_doc.get("uuid")}'
                )
    solr.commit()
    logger.info(f'Indexed committing site pages: {len(solr_docs)}')
    print(f'Indexed committing site pages: {len(solr_docs)}')
    summary = [(solr_doc.get('uuid'), solr_doc.get('slug_type_uri_label'),) for solr_doc in solr_docs]
    print(summary)


def make_index_solr_documents(uuids, solr=None):
    """Makes and indexes solr documents for a list of uuids"""
    if not solr:
        solr = get_solr_connection()
    solr_docs =  make_solr_documents(uuids)
    try:
        solr.add(
            solr_docs,
            commit=False,
            overwrite=True,
        )
    except:
        for solr_doc in solr_docs:
            try:
                solr.add(
                    [solr_doc],
                    commit=False,
                    overwrite=True,
                )
            except:
                logger.warn(
                    f'Problem committing {solr_doc.get("uuid")}'
                )
                print(
                    f'Problem committing {solr_doc.get("uuid")}'
                )
    solr.commit()
    logger.info(f'Indexed committing {str(uuids)}')
    print(f'Indexed committing {str(uuids)}')


def reset_project_context_and_metadata_cache(project_id):
    """Resets the project context and metadata cache for a project."""
    clear_project_context_df_from_cache(project_id)
    rep_metadata.get_project_metadata_qs(
        project_id=project_id,
        reset_cache=True,
    )


def clear_new_project_context(act_uuids, cleared_project_ids):
    proj_id_qs = AllManifest.objects.filter(
        uuid__in=act_uuids
    ).distinct(
        'project_id'
    ).order_by(
        'project_id'
    ).values_list(
        'project_id', flat=True
    )
    if len(cleared_project_ids):
        proj_id_qs = proj_id_qs.exclude(project_id__in=cleared_project_ids)
    for project_id in proj_id_qs:
        project_id = str(project_id)
        if project_id in cleared_project_ids:
            continue
        print(f'First clear context_df cache for new project: {project_id}')
        reset_project_context_and_metadata_cache(project_id)
        cleared_project_ids.append(project_id)
    return cleared_project_ids


def make_indexed_solr_documents_in_chunks(
    uuids,
    solr=None,
    chunk_size=20,
    start_clear_all_caches=False,
    start_clear_caches=True,
    update_index_time=True,
):
    """Makes and indexes solr documents in chunks"""
    if not solr:
        solr = get_solr_connection()
    i = 0
    total_count = len(uuids)
    logger.info(f'Index {total_count} total items.')
    print(f'Index {total_count} total items.')

    if start_clear_all_caches:
        print('Clearing ALL caches for fresh indexing')
        clear_all_caches()
    elif start_clear_caches:
        print('Clearing caches for fresh indexing')
        clear_caches()
    else:
        print('No caches cleared')
    cleared_project_ids = []
    all_start = time.time()
    total_indexed = 0
    count_groups, r =  divmod(total_count, chunk_size)
    if r > 0:
        count_groups += 1
    for act_uuids in chunk_list(uuids, chunk_size):
        i += 1
        print('*' * 50)
        if start_clear_caches:
            # Make sure we have cleared the project contexts
            # for only those projects relevant to the items
            # we are reindexing.
            cleared_project_ids = clear_new_project_context(
                act_uuids,
                cleared_project_ids
            )
        act_chunk_size = len(act_uuids)
        print(
            f'Attempting to index chunk {i} of {count_groups} chunks'
            f' with {act_chunk_size} items.'
        )
        chunk_start = time.time()
        done = False
        attempt = 0
        while not done and attempt < 5:
            attempt += 1
            try:
                make_index_solr_documents(act_uuids, solr=solr)
                done = True
            except:
                print(f'Problem with solr on attempt {attempt}, wait a minute and try again.')
                done = False
                sleep(60)
        if update_index_time:
            now = datetime.datetime.now(timezone.utc)
            _ = AllManifest.objects.filter(
                uuid__in=act_uuids,
            ).update(
                indexed=now,
            )

        chunk_rate = get_crawl_rate_in_seconds(act_chunk_size, chunk_start)
        total_indexed += act_chunk_size
        print(
            f'Chunk indexing rate: {chunk_rate} items/second. '
            f'{total_indexed} of {total_count} done.'
        )
    full_rate = get_crawl_rate_in_seconds(total_count, all_start)
    print(f'ALL {total_count} items indexed at rate: {full_rate} items/second')


def get_updated_uuid_list(
        after_date,
        item_type_list=['projects', 'subjects', 'media', 'documents']
    ):
    """Gets a list of UUIDs updated after_date"""
    a_qs = AllAssertion.objects.filter(
        subject__item_type__in=item_type_list,
        updated__gte=after_date,
        subject__meta_json__flag_do_not_index__isnull=True,
    ).distinct(
        'subject_id'
    ).order_by(
        'subject_id'
    ).values_list(
        'subject_id',
        flat=True,
    )
    uuids = [str(uuid) for uuid in a_qs]
    m_qs = AllManifest.objects.filter(
        item_type__in=item_type_list,
        updated__gte=after_date,
        meta_json__flag_do_not_index__isnull=True,
    )
    uuids += [str(m.uuid) for m in m_qs]
    uuids = list(set(uuids))
    return uuids


def updated_solr_documents_in_chunks(
    after_date,
    solr=None,
    chunk_size=20,
    start_clear_caches=True,
    update_index_time=True,
    item_type_list=['projects', 'subjects', 'media', 'documents'],
):
    """Makes and indexes solr documents in chunks for items updated after_date"""
    uuids = get_updated_uuid_list(
        after_date=after_date,
        item_type_list=item_type_list,
    )
    return make_indexed_solr_documents_in_chunks(
        uuids=uuids,
        solr=solr,
        chunk_size=chunk_size,
        start_clear_caches=start_clear_caches,
        update_index_time=update_index_time,
    )


def get_uuids_associated_with_vocab(
    vocab_obj=None,
    vocab_uuid=None,
    vocab_uri=None,
):
    """Gets UUIDs for Open Context item types that have some sort of
    relationship with entities in a given linked data vocabulary.

    :param AllManifest vocab_obj: An AllManifest object instance
        for a vocabulary that's the target for reindexing
    :param str(uuid) vocab_uuid: A uuid to identifier the vocab_obj if a
        vocab_obj is not passed.
    :param str vocab_uri: A uri to identifier the vocab_obj if a
        vocab_obj is not passed.
    """
    if not vocab_obj and vocab_uuid:
        vocab_obj = AllManifest.objects.get(uuid=vocab_uuid)
    if not vocab_obj and vocab_uri:
        vocab_uri = AllManifest().clean_uri(vocab_uri)
        vocab_obj = AllManifest.objects.get(uri=vocab_uri)
    # Now get just the predicates associated with entities in the
    # vocabulary.
    pred_s_qs = AllAssertion.objects.filter(
        subject__item_type='predicates',
        object__context=vocab_obj,
    ).exclude(
        subject__project_id=configs.OPEN_CONTEXT_PROJ_UUID,
        project_id=configs.OPEN_CONTEXT_PROJ_UUID,
    ).order_by(
        'subject_id'
    ).distinct(
        'subject'
    ).values_list(
        'subject_id',
        flat=True,
    )
    pred_uuids = [uuid for uuid in pred_s_qs]
    pred_uuids = list(set(pred_uuids))
    pred_o_qs = AllAssertion.objects.filter(
        object__item_type='predicates',
        subject__context=vocab_obj,
    ).exclude(
        object_id__in=pred_uuids,
        object__project_id=configs.OPEN_CONTEXT_PROJ_UUID,
        project_id=configs.OPEN_CONTEXT_PROJ_UUID,
    ).order_by(
        'object_id'
    ).distinct(
        'object'
    ).values_list(
        'object_id',
        flat=True,
    )
    pred_uuids += [uuid for uuid in pred_o_qs]
    pred_uuids = list(set(pred_uuids))
    print(f'{len(pred_uuids)} predicates associated with {vocab_obj.label} ({vocab_obj.uri})')
    # Now get just the types associated with entities in the
    # vocabulary.
    t_s_qs = AllAssertion.objects.filter(
        subject__item_type='types',
        object__context=vocab_obj,
    ).order_by(
        'subject_id'
    ).distinct(
        'subject'
    ).values_list(
        'subject_id',
        flat=True,
    )
    t_uuids = [uuid for uuid in t_s_qs]
    t_o_qs = AllAssertion.objects.filter(
        object__item_type='types',
        subject__context=vocab_obj,
    ).exclude(
        object_id__in=t_uuids,
    ).order_by(
        'object_id'
    ).distinct(
        'object'
    ).values_list(
        'object_id',
        flat=True,
    )
    t_uuids += [uuid for uuid in t_o_qs]
    t_uuids = list(set(t_uuids))
    print(f'{len(t_uuids)} types associated with {vocab_obj.label} ({vocab_obj.uri})')
    # Now get the subjects associated with predicates that are
    # associated with the vocabulary (whew!)
    sub_pred_qs = AllAssertion.objects.filter(
        subject__item_type__in=configs.OC_ITEM_TYPES,
        predicate_id__in=pred_uuids,
    ).order_by(
        'subject_id'
    ).distinct(
        'subject'
    ).values_list(
        'subject_id',
        flat=True,
    )
    uuids = [uuid for uuid in sub_pred_qs]
    uuids = list(set(uuids))
    print(f'{len(uuids)} oc items via predicates associated with {vocab_obj.label} ({vocab_obj.uri})')
    # Now get the subjects associated with types that are
    # associated with the vocabulary (whew!)
    sub_types_qs = AllAssertion.objects.filter(
        subject__item_type__in=configs.OC_ITEM_TYPES,
        object_id__in=t_uuids,
    ).order_by(
        'subject_id'
    ).distinct(
        'subject'
    ).values_list(
        'subject_id',
        flat=True,
    )
    print(f'{len(sub_types_qs)} oc items via types (objs) associated with {vocab_obj.label} ({vocab_obj.uri})')
    uuids += [uuid for uuid in sub_types_qs]
    # Get UUIDS directly associated with the concepts in the vocab
    subj_qs = AllAssertion.objects.filter(
        subject__item_type__in=configs.OC_ITEM_TYPES,
        object__context=vocab_obj,
    ).order_by(
        'subject_id'
    ).distinct(
        'subject'
    ).values_list(
        'subject_id',
        flat=True,
    )
    print(f'{len(subj_qs)} oc items directly associated (as subjects) with {vocab_obj.label} ({vocab_obj.uri})')
    uuids += [uuid for uuid in subj_qs]
    obj_qs = AllAssertion.objects.filter(
        subject__context=vocab_obj,
        object__item_type__in=configs.OC_ITEM_TYPES,
    ).order_by(
        'object_id'
    ).distinct(
        'object'
    ).values_list(
        'object_id',
        flat=True,
    )
    print(f'{len(obj_qs)} oc items directly associated (as objects) with {vocab_obj.label} ({vocab_obj.uri})')
    uuids += [uuid for uuid in obj_qs]
    print('Deduplicating uuids. This may take a bit...')
    uuids = list(set(uuids))
    print(f'{len(uuids)} oc items associated with {vocab_obj.label} ({vocab_obj.uri})')
    return uuids


def delete_solr_documents(uuids, solr=None):
    """Deletes solr documents identified by a list of uuids"""
    if not solr:
        solr = get_solr_connection()
    print(f'Delete {len(uuids)} solr documents from solr index.')
    for uuid in uuids:
        solr.delete(id=uuid)
    solr.commit()


def delete_flagged_no_index_from_solr(filter_args=None, solr=None):
    """Deletes solr documents flagged for NOT indexing with solr"""
    m_uuid_qs = AllManifest.objects.filter(
        Q(meta_json__flag_do_not_index=True)
        | Q(project__meta_json__flag_do_not_index=True)
    ).values_list(
        'uuid',
        flat=True,
    )
    if filter_args:
        m_uuid_qs = m_uuid_qs.filter(**filter_args)
    print(f'Identified {len(m_uuid_qs)} items to remove from solr (if indexed by solr)')
    if not solr:
        solr = get_solr_connection()
    for uuid in m_uuid_qs:
        uuid = str(uuid)
        solr.delete(id=uuid)
    solr.commit()
