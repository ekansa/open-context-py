import csv
import uuid as GenUUID
import os
import numpy as np
import pandas as pd
from django.conf import settings
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.ocitems.subjects.models import Subject
from opencontext_py.apps.ldata.linkannotations.models import LinkAnnotation

from opencontext_py.apps.imports.kobotoolbox.dbupdate import load_context_row


SOURCE_ID = 'dinaa-2019-county-counts'
GEONAMES_USE_FIRST_PART = 'http://www.geonames.org/'

ADD_REGIONS = [
    (
        'Minnesota',
        '2d64c58d-744c-468b-a9c8-b059da3134c6',
        'Lake County',
        'fe1e4b89-c5c5-408a-9ef6-31999bbf117b', # new
    ),
    
    (
        'Montana',
        'c16a2e2f-f39a-43ee-8bad-d223723d30e1',
        'Yellowstone National Park',
        'd58b3d02-98ee-4221-a719-9dde70d75d25', # new
    ),
    
    (
        'Washington',
        '65b6be19-2605-4cb7-8f79-083eb781aa66',
        'Colville National Forest',
        '8becf697-5a03-4a0f-a716-2f1608995f04', # new
    ),
    (
        'Washington',
        '65b6be19-2605-4cb7-8f79-083eb781aa66',
        'Gifford Pinchot Forest',
        'be721a1f-b4ea-4d07-9a63-a0d13d24162f', # new
    ),
    (
        'Washington',
        '65b6be19-2605-4cb7-8f79-083eb781aa66',
        'Mt. Baker-Snoqualmie Forest',
        '173d6c15-3036-43c3-8a33-c0db5772bde9', # new
    ),
    (
        'Washington',
        '65b6be19-2605-4cb7-8f79-083eb781aa66',
        'Okanogan Forest',
        'f4d73217-fd27-4d30-912a-70077bcb28fc',  # new
    ),
    (
        'Washington',
        '65b6be19-2605-4cb7-8f79-083eb781aa66',
        'Olympic Forest',
        '13d11560-0b69-453f-946b-f7e2c063960b', # new
    ),
    (
        'Washington',
        '65b6be19-2605-4cb7-8f79-083eb781aa66',
        'Umatilla Forest',
        'e10b6886-f5aa-4f3e-837e-75a369a1a589', # new
    ),
    (
        'Washington',
        '65b6be19-2605-4cb7-8f79-083eb781aa66',
        'Wenatchee Forest',
        '6e98f8e6-0b6c-4168-a04f-914fdce812f3', # new
    ),
    
    (
        'Michigan',
        '1A5FF95A-07E4-4772-B46B-0C9411DD3A40',
        'Isle Royale',
        'a772ff75-7bac-4901-8d3c-4a5627c92cc0', # new
    ),
    (
        'Michigan',
        '1A5FF95A-07E4-4772-B46B-0C9411DD3A40',
        'Detroit River',
        '1aca0f6e-6c85-47a6-8bcb-3a96322a45a9', # new
    ),
    (
        'Michigan',
        '1A5FF95A-07E4-4772-B46B-0C9411DD3A40',
        "St. Mary's River",
        'b87b4ced-9c9a-4231-b565-8559daeb02b3', # new
    ),
    
    (
        'Michigan',
        '1A5FF95A-07E4-4772-B46B-0C9411DD3A40',
        "Lake Superior",
        '986097f6-e73b-4935-8643-f59ecd54b37c', # new
    ),
    (
        'Michigan',
        '1A5FF95A-07E4-4772-B46B-0C9411DD3A40',
        "Lake Huron",
        '0a17ecef-9e1a-4ad4-9172-273d257406ff', # new
    ),
    (
        'Michigan',
        '1A5FF95A-07E4-4772-B46B-0C9411DD3A40',
        "Lake Michigan",
        'e5a292b9-9d02-4551-a956-122d78d49536', # new
    ),
    (
        'Michigan',
        '1A5FF95A-07E4-4772-B46B-0C9411DD3A40',
        "Lake Erie",
        'd80cd530-f381-4174-bf6f-e4a65b12c9a3', # new
    ),
]

# See: https://en.wikipedia.org/wiki/Smithsonian_trinomial
DEFAULT_FORMAT = '{state_num}{county_abbr}{site_num}'
STATE_SPECIAL_FORMAT = {
    'Conneticut': 'CT-{site_num}',
}

"""
import csv
import pandas as pd
from django.conf import settings
from opencontext_py.apps.imports.dinaa.utilities import (
    add_missing_containing_regions,
    add_county_uuids,
    create_inferred_sites,
)
act_dir = settings.STATIC_IMPORTS_ROOT + 'dinaa-2019/'
# add_missing_containing_regions()
df = pd.read_csv(
    (act_dir + 'state-count-trinomial-counts-raw.csv')
)
df = add_county_uuids(df)
df.to_csv(
    (act_dir + 'state-count-trinomial-counts-uuids.csv'),
    index=False,
    quoting=csv.QUOTE_NONNUMERIC
)
create_inferred_sites(df, act_dir)


"""

def add_missing_containing_regions(project_uuid='0', source_id=SOURCE_ID):
    """Adds missing containing regions that have site counts"""
    for state, state_uuid, new_region, new_uuid in ADD_REGIONS:
        row = {
            'parent_uuid': state_uuid,
            'context_uuid': new_uuid,
            'label': new_region,
            'class_uri': 'oc-gen:cat-region',
        }
        load_context_row(
            project_uuid=project_uuid,
            source_id=source_id,
            row=row
        )


def clean_geonames_uri(geonames_uri):
    """Normalizes a GeoNames URI to match normal OC expectations"""
    geo_parts = str(geonames_uri).split('geonames.org/')
    geo_id = geo_parts[-1].split('/')[0]
    return GEONAMES_USE_FIRST_PART + str(geo_id)


def lookup_county_uuid(state, county, geonames_uri):
    """Looks up a county uuid in Open Context."""
    contexts = [
        'United States/{}/{}'.format(state, county),
        'United States/{}/{} County'.format(state, county),
    ]
    sub_obj = Subject.objects.filter(
        context__in=contexts
    ).first()
    if sub_obj:
        # Found a subject item.
        return sub_obj.uuid
    geonames_uri = clean_geonames_uri(geonames_uri)
    la = LinkAnnotation.objects.filter(
        subject_type='subjects',
        object_uri=geonames_uri
    ).first()
    if la:
        # Found a subject of a linking relation with a geonames
        # URI.
        return la.subject
    # Found NOTHING.
    return None
    
def add_county_uuids(df):
    """Adds county uuids to the dataframe"""
    df['County_UUID'] = np.nan
    for i, row in df.iterrows():
        county_uuid = lookup_county_uuid(
            state=row['State'],
            county=row['COUNTY NAME'],
            geonames_uri=row['County Geonames URI']
        )
        if not county_uuid:
            continue
        cnty_indx = (
            (df['State'] == row['State'])
            & (df['COUNTY NAME'] == row['COUNTY NAME'])
        )
        df.loc[cnty_indx, 'County_UUID'] = county_uuid
    return df

def create_inferred_sites(df, save_path, project_uuid='skip', source_id=SOURCE_ID):
    """Uses a dataframe to make site records inferred from counts"""
    if not 'County_UUID' in df.columns:
        # get the uuids for the counties, we need these
        df = add_county_uuids(df)
    
    site_cols = [
        'state',
        'state_prefix',
        'county_region',
        'county_abbr',
        'parent_uuid',
        'label',
        'countext_uuid',
    ]
    states = df['State'].unique().tolist()
    for state in states:
        # defaults to '{state_num}{county_abbr}{site_num}'
        site_format_template = STATE_SPECIAL_FORMAT.get(state, DEFAULT_FORMAT)
        df_sites = []
        for _, row in df[df['State']==state].iterrows():
            state_num = row['STATE SMITHSONIAN PREFIX 1-50']
            if state_num > 0:
                state_num = int(row['STATE SMITHSONIAN PREFIX 1-50'])
            df_site = pd.DataFrame(columns=site_cols)
            for i in range(0, row['Number of Sites']):
                site_num = i + 1
                label = site_format_template.format(
                    state_num=state_num,
                    county_abbr=row['COUNTY SMITHSONIAN ABBREVIATION'],
                    site_num=site_num
                )
                df_site.loc[i] = [
                    state,
                    state_num,
                    row['COUNTY NAME'],
                    row['COUNTY SMITHSONIAN ABBREVIATION'],
                    row['County_UUID'],
                    label,
                    np.nan,
                ]
            df_sites.append(df_site)
        df_all_sites = pd.concat(df_sites)
        df_all_sites.to_csv(
            (save_path + 'trinomials-{}.csv'.format(state)),
            index=False,
            quoting=csv.QUOTE_NONNUMERIC
        )

