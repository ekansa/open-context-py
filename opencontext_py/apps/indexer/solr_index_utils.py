import copy
import requests
from urllib.parse import urlparse, parse_qs

from opencontext_py.apps.all_items.models import AllManifest


UUID_ROWS = 500


def fetch_solr_index_metadata_uuids_json(query_url, uuid_rows=UUID_ROWS):
    if '#' in query_url:
        # Remove the client side hash frag identifer
        url_x = query_url.split('#')
        query_url = url_x[0]
    parsed_url = urlparse(query_url, allow_fragments=False)
    if not parsed_url.query:
        q_dict = {}
    else:
        q_dict = parse_qs(parsed_url.query)
    act_resp = q_dict.get('response', [])
    expected_resp_found = False
    for resp_val in ['metadata,uuid', 'metadata%2Cuuid',]:
        if resp_val in act_resp:
            expected_resp_found = True
            break
    if not expected_resp_found:
        q_dict['response'] = ['metadata,uuid']
    if uuid_rows:
        q_dict['rows'] =[uuid_rows]
    r_url = f'https://{parsed_url.netloc}{parsed_url.path}'
    try:
        r = requests.get(
            url=r_url,
            headers={'Accept': 'application/json'},
            params=q_dict,
            timeout=60,
        )
        r.raise_for_status()
        json_r = r.json()
    except:
        json_r = None
    return json_r


def get_solr_uuids(query_url, uuids=None, do_paging=True):
    if uuids is None:
        uuids = []
    json_r = fetch_solr_index_metadata_uuids_json(query_url)
    if not json_r:
        return uuids
    uuids += json_r.get('uuids', [])
    print(f'Fetched {query_url}')
    print(f' - now have {len(uuids)} uuids of expected {json_r.get("totalResults")} total')
    next_json_page_url = json_r.get('next-json')
    if do_paging and next_json_page_url:
        uuids = get_solr_uuids(
            query_url=next_json_page_url,
            uuids=uuids,
            do_paging=do_paging,
        )
    return uuids