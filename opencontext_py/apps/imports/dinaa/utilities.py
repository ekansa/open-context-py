import csv
import uuid as GenUUID
import os
import numpy as np
import pandas as pd
from django.conf import settings
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.ocitems.subjects.models import Subject
from opencontext_py.apps.ocitems.projects.models import Project
from opencontext_py.apps.ocitems.assertions.models import Assertion
from opencontext_py.apps.ocitems.strings.models import OCstring

from opencontext_py.apps.ldata.linkannotations.models import LinkAnnotation
from opencontext_py.apps.ldata.linkentities.models import LinkEntity
from opencontext_py.apps.ldata.geonames.api import GeonamesAPI

from opencontext_py.apps.imports.kobotoolbox.dbupdate import (
    load_context_row,
    load_attribute_df_into_importer,
    load_attribute_data_into_oc,
)

from opencontext_py.apps.imports.sources.unimport import UnImport

DINAA_ROOT_PROJECT_UUID = '416A274C-CF88-4471-3E31-93DB825E9E4A'
SUB_PROJECT_UUID = 'e0ea772b-a64f-4758-93aa-8db3b07564a3'
SOURCE_ID = 'dinaa-2019-state-aggs'
GEONAMES_USE_FIRST_PART = 'http://www.geonames.org/'

ADD_REGIONS = [
    
    (
        'Arkansas',
        '46E8F36C-B3C1-447D-9EBE-559F41F2F8FE',
        'Saline County',
        '7fd16d6f-e247-488c-90dc-1506ae9bbc2b', # new
        'http://www.geonames.org/4130035',
    ),
    
    (
        'Minnesota',
        '2d64c58d-744c-468b-a9c8-b059da3134c6',
        'Lake County',
        'fe1e4b89-c5c5-408a-9ef6-31999bbf117b', # new
        'http://www.geonames.org/5033738',
    ),
    
    (
        'Montana',
        'c16a2e2f-f39a-43ee-8bad-d223723d30e1',
        'Yellowstone National Park',
        'd58b3d02-98ee-4221-a719-9dde70d75d25', # new
        'http://www.geonames.org/5687468',
    ),
    
    (
        'Washington',
        '65b6be19-2605-4cb7-8f79-083eb781aa66',
        'Colville National Forest',
        '8becf697-5a03-4a0f-a716-2f1608995f04', # new
        'http://www.geonames.org/5790670',
    ),
    (
        'Washington',
        '65b6be19-2605-4cb7-8f79-083eb781aa66',
        'Gifford Pinchot Forest',
        'be721a1f-b4ea-4d07-9a63-a0d13d24162f', # new
        'http://www.geonames.org/5795439',
    ),
    (
        'Washington',
        '65b6be19-2605-4cb7-8f79-083eb781aa66',
        'Mt. Baker-Snoqualmie Forest',
        '173d6c15-3036-43c3-8a33-c0db5772bde9', # new
        'http://www.geonames.org/5804063',
    ),
    (
        'Washington',
        '65b6be19-2605-4cb7-8f79-083eb781aa66',
        'Okanogan Forest',
        'f4d73217-fd27-4d30-912a-70077bcb28fc',  # new
        'http://www.geonames.org/5805559',
    ),
    (
        'Washington',
        '65b6be19-2605-4cb7-8f79-083eb781aa66',
        'Olympic Forest',
        '13d11560-0b69-453f-946b-f7e2c063960b', # new
        'http://www.geonames.org/5805711',
    ),
    (
        'Washington',
        '65b6be19-2605-4cb7-8f79-083eb781aa66',
        'Umatilla Forest',
        'e10b6886-f5aa-4f3e-837e-75a369a1a589', # new
        'http://www.geonames.org/5758067',
    ),
    (
        'Washington',
        '65b6be19-2605-4cb7-8f79-083eb781aa66',
        'Wenatchee Forest',
        '6e98f8e6-0b6c-4168-a04f-914fdce812f3', # new
        'http://www.geonames.org/5815358',
    ),
    
    (
        'Michigan',
        '1A5FF95A-07E4-4772-B46B-0C9411DD3A40',
        'Isle Royale',
        'a772ff75-7bac-4901-8d3c-4a5627c92cc0', # new
        'http://www.geonames.org/4997341',
    ),
    (
        'Michigan',
        '1A5FF95A-07E4-4772-B46B-0C9411DD3A40',
        'Detroit River',
        '1aca0f6e-6c85-47a6-8bcb-3a96322a45a9', # new
        'http://www.geonames.org/8095848',
    ),
    (
        'Michigan',
        '1A5FF95A-07E4-4772-B46B-0C9411DD3A40',
        "St. Mary's River",
        'b87b4ced-9c9a-4231-b565-8559daeb02b3', # new
        'http://www.geonames.org/5008518',
    ),
    
    (
        'Michigan',
        '1A5FF95A-07E4-4772-B46B-0C9411DD3A40',
        "Lake Superior",
        '986097f6-e73b-4935-8643-f59ecd54b37c', # new
        'http://www.geonames.org/5011627',
    ),
    (
        'Michigan',
        '1A5FF95A-07E4-4772-B46B-0C9411DD3A40',
        "Lake Huron",
        '0a17ecef-9e1a-4ad4-9172-273d257406ff', # new
        'http://www.geonames.org/4996884',
    ),
    (
        'Michigan',
        '1A5FF95A-07E4-4772-B46B-0C9411DD3A40',
        "Lake Michigan",
        'e5a292b9-9d02-4551-a956-122d78d49536', # new
        'http://www.geonames.org/5001835',
    ),
    (
        'Michigan',
        '1A5FF95A-07E4-4772-B46B-0C9411DD3A40',
        "Lake Erie",
        'd80cd530-f381-4174-bf6f-e4a65b12c9a3', # new
        'http://www.geonames.org/5153380',
    ),
]

# See: https://en.wikipedia.org/wiki/Smithsonian_trinomial
DEFAULT_FORMAT = '{state_num}{county_abbr}{site_num}'
STATE_SPECIAL_FORMAT = {
    
}

DEFAULT_ATTRIBUTE_SOURCE_TYPE = 'site-trinomials'

DF_ATTRIBUTE_CONFIGS = [
    
    {
        'source-column': 'label',
        'sources': [DEFAULT_ATTRIBUTE_SOURCE_TYPE,],
        'match_type': 'exact',
        'field_args': {
            'label': 'Site Label',
            'is_keycell': True,
            'field_type': 'subjects',
            'field_value_cat': 'oc-gen:cat-site'
        },
        'subject_pk': True,
    },
    
    {
        'source-column': 'Record Source',
        'sources': [DEFAULT_ATTRIBUTE_SOURCE_TYPE,],
        'match_type': 'exact',
        'field_args': {
            'label': 'Record Source',
            'f_uuid': 'a8972087-80ae-415c-a115-400574790ef0',
            'field_type': 'description',
            'field_data_type': 'id',
        },
    },
    
    {
        'source-column': 'Smithsonian Trinomial Identifier',
        'sources': [DEFAULT_ATTRIBUTE_SOURCE_TYPE,],
        'match_type': 'exact',
        'field_args': {
            'label': 'Smithsonian Trinomial Identifier',
            'f_uuid': 'a5c308c3-52f8-4076-b315-d3258d485572',
            'field_type': 'description',
            'field_data_type': 'xsd:string',
        },
    },
    
    {
        'source-column': 'Sortable Trinomial',
        'sources': [DEFAULT_ATTRIBUTE_SOURCE_TYPE,],
        'match_type': 'exact',
        'field_args': {
            'label': 'Sortable Trinomial',
            'f_uuid': '69f0e92d-77a4-4524-a8d0-befceddbbbe5',
            'field_type': 'description',
            'field_data_type': 'xsd:string',
        },
    },
    
    {
        'source-column': 'Variant Trinomial Expression(s)',
        'sources': [DEFAULT_ATTRIBUTE_SOURCE_TYPE,],
        'match_type': 'startswith',
        'field_args': {
            'label': 'Variant Trinomial Expression(s)',
            'f_uuid': 'fb0f90e5-c0fe-4744-b631-d32635f77ae1',
            'field_type': 'description',
            'field_data_type': 'xsd:string',
        },
    },
]


"""
import csv
import pandas as pd
from django.conf import settings
from opencontext_py.apps.imports.sources.unimport import UnImport
from opencontext_py.apps.imports.dinaa.utilities import (
    SUB_PROJECT_UUID,
    SOURCE_ID,
    DEFAULT_ATTRIBUTE_SOURCE_TYPE,
    DF_ATTRIBUTE_CONFIGS,
    add_missing_containing_regions,
    add_county_uuids,
    create_inferred_sites,
    load_all_states_sites_attributes,
)


act_dir = settings.STATIC_IMPORTS_ROOT + 'dinaa-2019/'

if False:
    add_missing_containing_regions()
    df = pd.read_csv(
        (act_dir + 'state-count-trinomial-counts-raw.csv')
    )
    df = add_county_uuids(df)
    df.to_csv(
        (act_dir + 'state-count-trinomial-counts-uuids.csv'),
        index=False,
        quoting=csv.QUOTE_NONNUMERIC
    )
if False:
    create_inferred_sites(
        df=df,
        save_path=act_dir,
        project_uuid=SUB_PROJECT_UUID,
        source_id=SOURCE_ID,
        only_in_states=ONLY_IN_STATES 
    )

load_all_states_sites_attributes(
    act_dir,
    'state-count-trinomial-counts-uuids.csv'
)



"""


# ---------------------------------------------------------------------
# These functions below are for initial creation of new site records
# as follows:
#
# (1) Create new containing regions (counties, parks) if needed.
# (2) Auto generate a sequence for trinomial IDs for each region
#     based on reported totals
# (3) Check to see if each given generated trinomial ID is already
#     in Open Context, and if so, use the existing uuid and note
#     the record is existing. If new, then create the new site
#     record in the oc_subjects and oc_manifest with a containment
#     relation in oc_assertions.
# (4) Output the generated trinomials (and the few already existing)
#     to a CSV file
# ---------------------------------------------------------------------

def add_missing_containing_regions(project_uuid='0', source_id=SOURCE_ID):
    """Adds missing containing regions that have site counts"""
    for state, state_uuid, new_region, new_uuid, geonames_uri in ADD_REGIONS:
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
        ent_exists = LinkEntity.objects.filter(uri=geonames_uri).first()
        if not ent_exists:
            ent = LinkEntity()
            ent.uri = geonames_uri
            ent.label = new_region
            ent.alt_label = new_region
            ent.vocab_uri = GeonamesAPI().VOCAB_URI
            ent.ent_type = 'class'
            ent.save()
        la_exists = LinkAnnotation.objects.filter(
            subject=new_uuid,
            object_uri=geonames_uri
        ).first()
        if not la_exists:
            new_la = LinkAnnotation()
            new_la.subject = new_uuid
            new_la.subject_type = 'subjects'
            new_la.project_uuid = project_uuid
            new_la.source_id = source_id
            new_la.predicate_uri = 'skos:closeMatch'
            new_la.object_uri = geonames_uri
            new_la.creator_uuid = ''
            new_la.save()


def clean_geonames_uri(geonames_uri):
    """Normalizes a GeoNames URI to match normal OC expectations"""
    geo_parts = str(geonames_uri).split('geonames.org/')
    geo_id = geo_parts[-1].split('/')[0]
    return GEONAMES_USE_FIRST_PART + str(geo_id)


def db_lookup_county_uuid(state, county, geonames_uri):
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


def db_lookup_dinaa_project_uuids():
    """Looks up all of the DINAA related project uuids"""
    dps = Project.objects.filter(project_uuid=DINAA_ROOT_PROJECT_UUID)
    dp_project_uuids = [p.uuid for p in dps]
    if DINAA_ROOT_PROJECT_UUID not in dp_project_uuids:
        dp_project_uuids.append(DINAA_ROOT_PROJECT_UUID)
    return dp_project_uuids

    
def add_county_uuids(df):
    """Adds county uuids to the dataframe"""
    df['County_UUID'] = np.nan
    for i, row in df.iterrows():
        county_uuid = db_lookup_county_uuid(
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

def db_lookup_county_content_site_uuids(county_uuid, dinaa_proj_uuids):
    """Looks up existing sites within a county uuid"""
    cont_asses = Assertion.objects.filter(
        uuid=county_uuid,
        predicate_uuid=Assertion.PREDICATES_CONTAINS
    )
    child_uuids = [a.object_uuid for a in cont_asses]
    if not child_uuids:
        return []
    site_mans = Manifest.objects.filter(
        uuid__in=child_uuids,
        item_type='subjects',
        class_uri='oc-gen:cat-site',
    )
    uuids = [m.uuid for m in site_mans]
    return uuids

def db_lookup_dinaa_site_uuid(site_label, state_county_site_uuids):
    """Looks up an existing UUID for a DINAA site by matching labels"""
    if not state_county_site_uuids:
        return np.nan, None
    man_obj = Manifest.objects.filter(
        uuid__in=state_county_site_uuids,
        label=site_label
    ).first()
    if man_obj:
        # We found the site by a direct match to the manifest item label.
        # this is the happiest and fastest scenario.
        return man_obj.uuid, man_obj.source_id
    # Now we do the slower and less ideal lookups.
    site_str_asses = Assertion.objects.filter(
        uuid__in=state_county_site_uuids,
        object_type='xsd:string'
    )
    str_to_sites = {a.object_uuid:a.uuid for a in site_str_asses}
    str_uuids = list(str_to_sites.keys())
    label_str = OCstring.objects.filter(
        uuid__in=str_uuids,
        content=site_label
    ).first()
    if not label_str:
        return np.nan, None
    return str_to_sites[label_str.uuid], None


def db_add_new_site(county_uuid, new_uuid, label, project_uuid=SUB_PROJECT_UUID, source_id=SOURCE_ID):
    """Adds missing containing regions that have site counts"""
    row = {
        'parent_uuid': county_uuid,
        'context_uuid': new_uuid,
        'label': label,
        'class_uri': 'oc-gen:cat-site',
    }
    load_context_row(
        project_uuid=project_uuid,
        source_id=source_id,
        row=row
    )

def create_inferred_sites(df, save_path, project_uuid='skip', source_id=SOURCE_ID, only_in_states=None):
    """Uses a dataframe to make site records inferred from counts"""
    if not 'County_UUID' in df.columns:
        # get the uuids for the counties, we need these
        df = add_county_uuids(df)
    dinaa_proj_uuids = db_lookup_dinaa_project_uuids()
    site_cols = [
        'state',
        'state_prefix',
        'county_region',
        'county_abbr',
        'parent_uuid',
        'label',
        'countext_uuid',
        'source_uuid',
        'Record Source',
        'Smithsonian Trinomial Identifier',
        'Sortable Trinomial',
        'Variant Trinomial Expression(s)/1',
        'Variant Trinomial Expression(s)/2',
        '_uuid',  # For loading into the importer
    ]
    states = df['State'].unique().tolist()
    for state in states:
        if state == 'Connecticut':
            # Connecticut is weird, not assigned to counties.
            continue
        if only_in_states is not None and not state in only_in_states:
            # We want to limit processing to only a few states.
            continue
        # defaults to '{state_num}{county_abbr}{site_num}'
        site_format_template = STATE_SPECIAL_FORMAT.get(state, DEFAULT_FORMAT)
        df_sites = []
        for _, row in df[df['State']==state].iterrows():
            state_num = row['STATE SMITHSONIAN PREFIX 1-50']
            if state_num > 0:
                state_num = int(row['STATE SMITHSONIAN PREFIX 1-50'])
            df_site = pd.DataFrame(columns=site_cols)
            state_county_site_uuids = db_lookup_county_content_site_uuids(
                row['County_UUID'], dinaa_proj_uuids
            )
            for i in range(0, row['Number of Sites']):
                site_num = i + 1
                label = site_format_template.format(
                    state_num=state_num,
                    county_abbr=row['COUNTY SMITHSONIAN ABBREVIATION'],
                    site_num=site_num
                )
                lead_zero_site = '{:05d}'.format(site_num)
                site_uuid, existing_source = db_lookup_dinaa_site_uuid(label, state_county_site_uuids)
                if isinstance(site_uuid, str) and existing_source != source_id:
                    source_uuid = 'existing'
                    record_source = ''
                elif isinstance(site_uuid, str) and existing_source == source_id:
                    # We already imported this site from this SAME data,
                    # so do not report it as existing, it is new, but do
                    # not just create it again.
                    source_uuid = 'new'
                    record_source = 'State reported aggregate'
                else:
                    site_uuid = GenUUID.uuid4()
                    source_uuid = 'new'
                    record_source = 'State reported aggregate'
                    # Actually add the site record.
                    db_add_new_site(
                        county_uuid=row['County_UUID'],
                        new_uuid=site_uuid,
                        label=label
                    )
                df_site.loc[i] = [
                    state,
                    state_num,
                    row['COUNTY NAME'],
                    row['COUNTY SMITHSONIAN ABBREVIATION'],
                    row['County_UUID'],
                    label,
                    site_uuid,
                    source_uuid,
                    record_source,
                    '{state_num}{county_abbr}{site_num}'.format(
                        state_num=state_num,
                        county_abbr=row['COUNTY SMITHSONIAN ABBREVIATION'],
                        site_num=site_num
                    ),
                    '{state_num}{county_abbr}{site_num}'.format(
                        state_num=state_num,
                        county_abbr=row['COUNTY SMITHSONIAN ABBREVIATION'],
                        site_num=lead_zero_site
                    ),
                    '{state_num}-{county_abbr}-{site_num}'.format(
                        state_num=state_num,
                        county_abbr=row['COUNTY SMITHSONIAN ABBREVIATION'],
                        site_num=site_num
                    ),
                    '{state_num}-{county_abbr}-{site_num}'.format(
                        state_num=state_num,
                        county_abbr=row['COUNTY SMITHSONIAN ABBREVIATION'],
                        site_num=lead_zero_site
                    ),
                    site_uuid,
                ]
            df_sites.append(df_site)
        df_all_sites = pd.concat(df_sites)
        df_all_sites.to_csv(
            (
                save_path + 'trinomials--{}.csv'.format(
                    state.lower().replace(' ', '-')
                )
            ),
            index=False,
            quoting=csv.QUOTE_NONNUMERIC
        )

# ---------------------------------------------------------------------
# These functions below are for adding some attribute data to the
# new site records created with the function above:
#
# ---------------------------------------------------------------------

def load_all_states_sites_attributes(
    act_dir,
    all_states_file_name,
    project_uuid=SUB_PROJECT_UUID,
    prefix_source_id=(SOURCE_ID + '-'),
    attribute_col_configs=DF_ATTRIBUTE_CONFIGS,
    source_type=DEFAULT_ATTRIBUTE_SOURCE_TYPE,
):
    """Loads all the state site attribute data"""
    df_all = pd.read_csv(
        (act_dir + all_states_file_name)
    )
    states = df_all['State'].unique().tolist()
    for state in states:
        source_id = prefix_source_id + state.lower().replace(' ', '-')
        state_file = (
            act_dir + 'trinomials--{}.csv'.format(
                state.lower().replace(' ', '-')
            )
        )
        try:
            df = pd.read_csv(state_file)
        except:
            df = None
        if df is None:
            # This state file does not exist
            continue
        print('Load attribute data from {} as source_id {}'.format(
            state_file, source_id
            )
        )
        load_attribute_df_into_importer(
            project_uuid=project_uuid,
            source_id=source_id,
            source_type=source_type,
            source_label=source_id,
            df=df,
            attribute_col_configs=attribute_col_configs
        )
        load_attribute_data_into_oc(
            project_uuid=project_uuid,
            source_id=source_id,
        )