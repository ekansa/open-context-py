
import logging
import time

from itertools import islice

from django.core.cache import caches



from opencontext_py.libs.solrclient import SolrClient
from opencontext_py.apps.indexer.solrdocument_new_schema import SolrDocumentNS

from opencontext_py.apps.searcher.new_solrsearcher import configs as solr_search_configs


"""
# testing

import importlib
import logging
from opencontext_py.apps.all_items.models import (
    AllManifest,
    AllAssertion,
)
from opencontext_py.apps.indexer import index_new_schema as new_ind
importlib.reload(new_ind)

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


def clear_caches():
    """Clears caches to make sure reidexing uses fresh data. """
    cache = caches['redis']
    cache.clear()
    cache = caches['default']
    cache.clear()
    cache = caches['memory']
    cache.clear()


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
        ok = solrdoc.make_solr_doc()
        if not ok:
            logger.warn(f'Problem making solr doc for {str(uuid)}')
            print(f'Problem making solr doc for {str(uuid)}')
        solr_docs.append(solrdoc.fields)
    return solr_docs


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


def make_indexed_solr_documents_in_chunks(
    uuids, 
    solr=None, 
    chunk_size=20, 
    start_clear_caches=True
):
    """Makes and indexes solr documents in chunks"""
    if not solr:
        solr = get_solr_connection()
    i = 0
    total_count = len(uuids)
    logger.info(f'Index {total_count} total items.')
    print(f'Index {total_count} total items.')
    
    if start_clear_caches:
        print('Clearing caches for fresh indexing')
        clear_caches()
    
    all_start = time.time()
    total_indexed = 0
    count_groups, r =  divmod(total_count, chunk_size)
    if r > 0: 
        count_groups += 1
    for act_uuids in chunk_list(uuids, chunk_size):
        i += 1
        print('*' * 50)
        act_chunk_size = len(act_uuids)
        print(
            f'Attempting to index chunk {i} of {count_groups} chunks'
            f' with {act_chunk_size} items.'
        )
        chunk_start = time.time()
        make_index_solr_documents(act_uuids, solr=solr)
        chunk_rate = get_crawl_rate_in_seconds(act_chunk_size, chunk_start)
        total_indexed += act_chunk_size
        print(
            f'Chunk indexing rate: {chunk_rate} items/second. '
            f'{total_indexed} of {total_count} done.'
        )
    full_rate = get_crawl_rate_in_seconds(total_count, all_start)
    print(f'ALL {total_count} items indexed at rate: {full_rate} items/second')


def delete_solr_documents(uuids, solr=None):
    """Deletes solr documents identified by a list of uuids"""
    if not solr:
        solr = get_solr_connection()
    print(f'Delete {len(uuids)} solr documents from solr index.')
    for uuid in uuids:
        solr.delete(id=uuid)
    solr.commit()