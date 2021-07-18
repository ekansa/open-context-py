
import logging
from math import remainder
import time

from datetime import datetime
from itertools import islice

from django.conf import settings
from django.core.cache import caches

from opencontext_py.apps.all_items.models import AllManifest

from opencontext_py.libs.solrconnection import SolrConnection
from opencontext_py.apps.indexer.solrdocument_new_schema import SolrDocumentNS


"""
# testing

import importlib
import logging
from opencontext_py.apps.all_items.models import (
    AllManifest,
)
from opencontext_py.apps.indexer import index_new_schema as new_ind
importlib.reload(new_ind)

# Gabii for now.
project_ids = ['df043419-f23b-41da-7e4d-ee52af22f92f',]
m_qs = AllManifest.objects.filter(
    item_type__in=['projects', 'subjects', 'media', 'documents'],
    project_id__in=project_ids,
)
uuids = [str(m.uuid) for m in m_qs]
new_ind.clear_caches()
new_ind.make_indexed_solr_documents_in_chunks(uuids)

"""


logger = logging.getLogger(__name__)

def get_crawl_rate_in_seconds(document_count, start_time):
    return str(round(document_count/(time.time() - start_time), 3))


def get_elapsed_time_in_seconds(start_time):
    return str(round((time.time() - start_time), 3))


def get_solr_connection():
    solr = SolrConnection(
        exit_on_error=False,
        solr_host=settings.SOLR_HOST_TEST,
        solr_port=settings.SOLR_PORT_TEST,
        solr_collection=settings.SOLR_COLLECTION_TEST
    ).connection
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
    solr_status = solr.update(
        solr_docs, 
        'json',
        commit=False
    ).status
    if solr_status == 200:
        solr.commit()
        logger.info(f'Indexed committing {str(uuids)}')
        print(f'Indexed committing {str(uuids)}')
    else:
        for solr_doc in solr_docs:
            solr_status = solr.update(
                [solr_doc], 
                'json',
                commit=False
            ).status
            if not solr_status == 200:
                logger.warn(
                    f'Problem committing {solr_doc.get("uuid")}'
                )
                print(
                    f'Problem committing {solr_doc.get("uuid")}'
                )

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