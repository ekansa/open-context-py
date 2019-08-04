import json
import csv
import os
import numpy as np
import pandas as pd
import re
import uuid as GenUUID
from django.conf import settings

from opencontext_py.apps.edit.dinaa.trinomials.manage import TrinomialManage
from opencontext_py.apps.ldata.federalregistry.api import FederalRegistryAPI

TRINOMIAL_PATTERNS = [
    "(\b([0-9]{1,2}[A-Z]{2,}[0-9]{1,})\b)",
]

"""
import csv
import pandas as pd
from django.conf import settings
from opencontext_py.apps.ldata.federalregistry.trinomialsearch import (
    make_trinomial_instances_df,
    add_file_metadata
)

doc_dir = settings.STATIC_IMPORTS_ROOT + '/federal-reg-docs'
metadata_dir = settings.STATIC_IMPORTS_ROOT + '/federal-reg-search'
output_path = settings.STATIC_IMPORTS_ROOT + '/dinaa-2019/federal-register-trinomials.csv'
df = make_trinomial_instances_df(doc_dir)
df.to_csv(output_path, index=False, quoting=csv.QUOTE_NONNUMERIC)
df = pd.read_csv(output_path)
df = add_file_metadata(df, metadata_dir)
df.to_csv(output_path, index=False, quoting=csv.QUOTE_NONNUMERIC)

"""

def make_trinomial_instances_df(doc_dir):
    tri_man = TrinomialManage()
    tri_man.remove_prepended_zeros = True
    df = pd.DataFrame(
        columns=[
            'filename',
            'pos_trinomial',
            'state_num',
            'region_abbr',
            'site_number'
        ]
    )
    i = 0
    for subdir, dirs, files in os.walk(doc_dir):
        for file in files:
            if not file.endswith('.txt'):
                continue
            filepath = os.path.join(subdir, file)
            with open(filepath, 'r') as file_obj:
                content = file_obj.read()
            trinomials = re.findall(r'(\b([0-9]{1,2}[A-Z]{2,}[0-9]{1,})\b)', content)
            trinomials = set(trinomials)
            for t_tup in trinomials:
                t_tup = set(t_tup)
                for trinomial in t_tup:
                    if trinomial.startswith('0'):
                        # not a trinomial
                        continue
                    tri_parts = tri_man.parse_trinomial(trinomial)
                    state = int(tri_parts['state'])
                    if state < 1 or state > 50:
                        # not a state, skip
                        continue
                    df.loc[i] = [
                        file,
                        trinomial,
                        state,
                        tri_parts['county'],
                        tri_parts['site']
                    ]
                    i += 1
                    print('[{}] Found {} in {} ({}, {}, {})'.format(
                            i,
                            trinomial,
                            file,
                            state,
                            tri_parts['county'],
                            tri_parts['site'],
                        )
                    )
    return df

def add_file_metadata(df, metadata_dir):
    """Adds file metadata to the dataframe"""
    df['title'] = np.nan
    df['url'] = np.nan
    for subdir, dirs, files in os.walk(metadata_dir):
        for file in files:
            if not file.endswith('.json'):
                continue
            search_obj = None
            filepath = os.path.join(subdir, file)
            with open(filepath, 'r') as file_obj:
                try:
                    search_obj = json.load(file_obj)
                except:
                    search_obj = None
            if not search_obj:
                continue
            if not 'results' in search_obj:
                continue
            for result in search_obj['results']:
                doc_id = result.get('document_number')
                if not doc_id:
                    continue
                filename ='{}.txt'.format(doc_id)
                indx = (df['filename'] == filename)
                if df[indx].empty:
                    continue
                print('Update metadata on {}'.format(filename))
                df.loc[indx, 'title'] = result.get('title')
                df.loc[indx, 'url'] = result.get('html_url')
    return df