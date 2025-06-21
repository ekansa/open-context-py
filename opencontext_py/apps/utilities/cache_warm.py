import requests
import time
from time import sleep
from urllib.parse import urlparse
from urllib.parse import parse_qs

import pandas as pd

from opencontext_py.libs.generalapi import GeneralAPI

from opencontext_py.apps.all_items import configs
from opencontext_py.apps.all_items.models import (
    AllManifest,
)

from opencontext_py.apps.searcher.new_solrsearcher import configs as query_configs


'''
Warm caches on Open Context

import importlib
from opencontext_py.apps.utilities import cache_warm
importlib.reload(cache_warm)

df_i = cache_warm.test_time_oc_requests()
df_q = cache_warm.warm_query_cache(url='https://opencontext.org/query/')

'''


SLEEP_TIME = 0.25
NUM_PROJECT_ITEM_FETCH = 15 # Fetch 15 records per project
URL_MIN_FACET_COUNT = 150000
MAX_PARAM_VALS = 3
ALLOWED_DEPTH = 5

def get_elapsed_time_in_seconds(start_time):
    return str(round((time.time() - start_time), 3))


def test_time_oc_requests_in_project(
        project=None,
        project_id=None,
        num_requests=NUM_PROJECT_ITEM_FETCH,
        delay_before_request=SLEEP_TIME,
        extension='',
        staging=False,
    ):
    rows = []
    if not project and project_id:
        project = AllManifest.objects.filter(uuid=project_id, item_type='projects').first()
    if not project:
        return rows
    m_qs = AllManifest.objects.filter(
        project=project,
        item_type__in=configs.OC_ITEM_TYPES
    ).order_by('?')[:num_requests]
    for man_obj in m_qs:
        if delay_before_request > 0:
            sleep(delay_before_request)
        if staging:
            url = f'https://staging.{man_obj.uri}{extension}'
        else:
            url = f'https://{man_obj.uri}{extension}'
        check = {
            'url': url,
            'label': man_obj.label,
            'slug': man_obj.slug,
            'project__label': man_obj.project.label,
            'item_class__slug': man_obj.item_class.slug,
        }
        print(f'Check: {check}')
        gapi = GeneralAPI()
        start_time = time.time()
        r = requests.get(
            url,
            timeout=240,
            headers=gapi.client_headers
        )
        check['elapsed'] = get_elapsed_time_in_seconds(start_time)
        check['status'] = r.status_code
        print(f"Done: {check['elapsed']} secs, status:  {check['status']}")
        if r.status_code == requests.codes.ok:
            check['ok'] = True
            check['text_len'] = len(str(r.text))
        else:
            check['ok'] = False
            check['text_len'] = None
        rows.append(check)
    return rows


def test_time_oc_requests(
    num_project_requests=NUM_PROJECT_ITEM_FETCH,
    delay_before_request=SLEEP_TIME,
    extension='',
    staging=False,
):
    rows = []
    p_qs = AllManifest.objects.filter(item_type='projects').order_by('?')
    for project in p_qs:
        rows += test_time_oc_requests_in_project(
            project=project,
            num_requests=num_project_requests,
            delay_before_request=delay_before_request,
            extension=extension,
            staging=staging,
        )
    df = pd.DataFrame(data=rows)
    df['time'] = pd.to_numeric(df['elapsed'])
    return df


def add_url_above_min_facet_count(opt_dict, urls, url_min_facet_count=URL_MIN_FACET_COUNT):
    url = opt_dict.get('id')
    if not url:
        return urls
    if opt_dict.get('count', 0) < url_min_facet_count:
        return urls
    urls.append(url)
    return urls


def get_query_urls_from_response_dict(resp_dict, url_min_facet_count=URL_MIN_FACET_COUNT):
    """Gets a list of query URLs that have counts above a minimum count threshold"""
    urls = []
    if resp_dict.get('totalResults', 0) < url_min_facet_count:
        return urls
    for feature in resp_dict.get('features', []):
        urls = add_url_above_min_facet_count(feature, urls, url_min_facet_count)
    for facet in resp_dict.get('oc-api:has-facets', []):
        for _, vals in facet.items():
            if not isinstance(vals, list):
                # this is not a list of options
                continue
            for opt_dict in vals:
                urls = add_url_above_min_facet_count(opt_dict, urls, url_min_facet_count)
    return urls


def check_param_len_and_repeating_hierarchies(url, prior_urls):
    ok_params = True
    parsed_url = urlparse(url)
    if not parsed_url.query:
        return ok_params
    url_qs_dict = parse_qs(parsed_url.query)
    for param, vals in url_qs_dict.items():
        if len(vals) > MAX_PARAM_VALS:
            # The current URL has too many vales for this parameter
            # so we don't want to go down this rabbit hole.
            ok_params = False
            return ok_params
        for p_url in prior_urls:
            p_parsed_url = urlparse(p_url)
            if not p_parsed_url.query:
                continue
            # make a query parameter dict for the prior url
            p_qs_dict = parse_qs(p_parsed_url.query)
            if not p_qs_dict.get(param):
                # the prior url does not have this param, so continue
                continue
            # iterate through the values for the current
            # url and the current param
            for val in vals:
                val_and_delim = f'{val}---'
                for prior_val in p_qs_dict.get(param, []):
                    if prior_val.startswith(val_and_delim):
                        ok_params = False
                        return ok_params
    return ok_params


def recursive_query_url_fetch(
        url,
        prior_urls=None,
        rows=None,
        depth=0,
        url_min_facet_count=URL_MIN_FACET_COUNT,
        do_recursive=True,
    ):
    if prior_urls is None:
        prior_urls = []
    if rows is None:
        rows = []
    if depth > ALLOWED_DEPTH:
        return prior_urls, rows
    if url in prior_urls:
        return prior_urls, rows
    ok_params = check_param_len_and_repeating_hierarchies(url, prior_urls)
    if not ok_params:
        return prior_urls, rows
    prior_urls.append(url)
    depth += 1
    check = {
        'url': url,
        'depth': depth,
    }
    print(f'Check: {check}')
    gapi = GeneralAPI()
    headers = gapi.client_headers
    headers['Accept'] = 'application/json'
    start_time = time.time()
    r = requests.get(
        url,
        timeout=240,
        headers=headers
    )
    check['elapsed'] = get_elapsed_time_in_seconds(start_time)
    check['status'] = r.status_code
    print(f"Done: {check['elapsed']} secs, status:  {check['status']}")
    if r.status_code == requests.codes.ok:
        check['ok'] = True
        check['text_len'] = len(str(r.text))
    else:
        check['ok'] = False
        check['text_len'] = None
        return prior_urls, rows
    resp_dict = r.json()
    check['totalResults'] = resp_dict.get('totalResults', 0)
    urls = get_query_urls_from_response_dict(resp_dict, url_min_facet_count=url_min_facet_count)
    check['new_url_count'] = len(urls)
    rows.append(check)
    if not urls or not do_recursive:
        return prior_urls, rows
    for new_url in urls:
        prior_urls, rows = recursive_query_url_fetch(
            url=new_url,
            prior_urls=prior_urls,
            rows=rows,
            url_min_facet_count=url_min_facet_count,
            depth=depth,
            do_recursive=do_recursive,
        )
    return prior_urls, rows


def warm_query_cache(url, url_min_facet_count=URL_MIN_FACET_COUNT):
    _, rows = recursive_query_url_fetch(
        url=url,
        url_min_facet_count=url_min_facet_count,
    )
    df = pd.DataFrame(data=rows)
    df['time'] = pd.to_numeric(df['elapsed'])
    return df