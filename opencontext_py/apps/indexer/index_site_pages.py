import copy
import datetime
from datetime import timezone
import logging
import requests
from unidecode import unidecode

from lxml import html

from re import U
import time

from itertools import islice
from opencontext_py.libs.rootpath import RootPath

from django.conf import settings
from django.core.cache import caches
from django.template.defaultfilters import slugify

from opencontext_py.apps.all_items import configs
from opencontext_py.apps.all_items.models import AllManifest
from opencontext_py.apps.all_items.legacy_all import update_old_id

from opencontext_py.apps.indexer import solr_utils
from opencontext_py.apps.indexer.solrdocument_new_schema import LOW_RESOLUTION_GEOTILE_LENGTH

from opencontext_py.libs.globalmaptiles import GlobalMercator

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
from opencontext_py.apps.indexer import index_site_pages as isp

importlib.reload(isp)
solr_docs = isp.make_site_pages_solr_docs()

"""


logger = logging.getLogger(__name__)


# Based on when our original templates finally got more ore less settled.
CREATED_TIME = '2018-05-30T00:00:00Z'


SITE_KEY_WORDS = {
    '/': [
        'faceted',
        'visualization',
        'comparative collections',
        'data tables',
        'citation',
        'identifiers',
        'vocabularies',
        'typologies',
        'DOI',
        'Creative Commons',
        'Linked Open Data',
        'licenses',
        'museum',
        'reuse',
        'media',
        'maps',
        'pricing',
        'small project',
        'medium project',
        'large project',
        'custom project',
        'estimate cost',
        'cost estimate',
    ],
    '/about/': [
        'video',
        'data cleaning',
        'annotate',
        'linked data',
        'URI',
        'digital archiving',
        'California Digital Library',
        'collaboration',
        'interoperable',
    ],
    '/about/uses': [
        'comparanda',
        'cite',
        'metadata',
        'researchers',
        'CSV',
        'Uniform Resource Identifier',
        'standards',
        'API',
        'interfaces',
        'controlled vocabularies',
    ],
    '/about/publishing': [
        'editorial team',
        'structured data',
        'relational database',
        'files',
        'PDF',
        'copyright',
        'public domain',
        'open access',
        'intellectual property',
        'peer review',
        'dataset',
    ],
    '/about/estimate': [
        'data management plan',
        'DMP',
        'archiving',
        'costs',
        'dissertation',
        'complexity',
        'GIS',
        'form',
    ],
    '/about/technology': [
        'Python',
        'PostgreSQL',
        'database',
        'server',
        'Web',
        'Github',
        'ontologies',
        'RDF',
        'open source',
        'version control',
    ],
    '/about/services': [
        'API',
        'GeoJSON',
        'JSON',
        'queries',
        'query',
        'geospatial',
        'chronological',
    ],
    '/about/recipes': [
        'download',
        'site security',
        'Excel',
        'spreadsheet',
    ],
    '/about/intellectual-property': [
        'indigenous',
        'stakeholder',
        'communities',
        'ethics',
        'CARE data',
        'FAIR data'
        'cultural heritage',
        'intellectual property',
        'privacy',
        'descendent communities',
        'collaboration',
    ],
    '/about/people': [
        'Sarah Whitcher Kansa',
        'Eric Kansa',
        'Editorial Board',
    ],
    '/about/sponsors': [
        'grants',
        'preservation',
    ],
    '/about/bibliography': [
        'Advances in Archaeological Practice',
        'Antiquity',
        'Proceedings of the National Academy of Sciences',
        'PNAS',
        'Digital Applications in Archaeology and Cultural Heritage',
        'PLOS ONE',
        'Journal of Archaeological Method and Theory',
        'International Journal of Digital Curation',
        'The Digital Press at the University of North Dakota',
        'Journal of Eastern Mediterranean Archaeology and Heritage Studies',
        'SAA Archaeological Record',
        'Data Science Journal',
        'World Archaeology',
        'preprint',
    ],
    '/about/terms': [
        'terms and conditions',
        'terms of use',
        'human remains',
        'copyright',
        'cookies',
        'privacy',
        'do not track',
        'IP address',
        'colonialism',
    ],
}

PROJ_MAN_OBJ = AllManifest.objects.get(
    uuid=configs.OPEN_CONTEXT_PROJ_UUID
)
PROJ_SOLR_STR = solr_utils.make_obj_or_dict_solr_entity_str(
    PROJ_MAN_OBJ
)
WORLD_MAN_OBJ = AllManifest.objects.get(
    uuid=configs.DEFAULT_SUBJECTS_ROOT_UUID
)
WORLD_SOLR_STR = solr_utils.make_obj_or_dict_solr_entity_str(
    WORLD_MAN_OBJ
)
OFF_WORLD_MAN_OBJ = AllManifest.objects.get(
    uuid=configs.DEFAULT_SUBJECTS_OFF_WORLD_UUID
)
OFF_WORLD_SOLR_STR = solr_utils.make_obj_or_dict_solr_entity_str(
    OFF_WORLD_MAN_OBJ
)

# Inside San Francisco Bay
PAGE_LAT = 37.857236
PAGE_LON = -122.382545
PAGE_GEO_PRECISION = 10
gm = GlobalMercator()
TILE = gm.lat_lon_to_quadtree(
    PAGE_LAT,
    PAGE_LON,
    PAGE_GEO_PRECISION
)
GEO_SOURCE = f"{PROJ_MAN_OBJ.slug.replace('_', '-')}___id___{PROJ_MAN_OBJ.uri}___{PROJ_MAN_OBJ.label}"

DEFAULT_SITE_PAGE_SOLR_DICT = {
    "published": CREATED_TIME,
    "interest_score": 20000,  # Site content should have a high interest score.
    "human_remains": False,
    "image_media_count": 0,
    "three_d_media_count": 0,
    "gis_media_count": 0,
    "other_binary_media_count": 0,
    "documents_count": 1,
    "subjects_children_count": 0,
    "subjects_count": 0,
    "persons_count": 0,
    "tables_count": 0,
    "project_uuid": configs.OPEN_CONTEXT_PROJ_UUID,
    "project_label": configs.OPEN_CONTEXT_PROJ_LABEL,
    "item_type": "documents",
    "item_class": configs.CLASS_OC_SITE_DOCUMENTATION_LABEL,
    "obj_all___project_id": [PROJ_SOLR_STR],
    "root___project_id": [PROJ_SOLR_STR],
    "root___context_id": [WORLD_SOLR_STR, OFF_WORLD_SOLR_STR],
    "obj_all___context_id": [WORLD_SOLR_STR, OFF_WORLD_SOLR_STR],
    "context_path": "",
    "ld___pred_id": [
        "schema_org_text___string___schema.org/text___Text",
    ],
    "schema_org_text___pred_string": [],
    "join_uuids": [
        configs.DEFAULT_SUBJECTS_ROOT_UUID,
        configs.DEFAULT_SUBJECTS_OFF_WORLD_UUID,
    ],
    "all_events___geo_count": 1,
    "all_events___geo_location": f"{PAGE_LAT},{PAGE_LON}",
    "all_events___geo_location_rpt": f"{PAGE_LAT},{PAGE_LON}",
    "all_events___geo_tile": [
        TILE
    ],
    "all_events___lr_geo_tile": [
        TILE[:LOW_RESOLUTION_GEOTILE_LENGTH]
    ],
    "event_class_slugs": [
        "oc_gen_general_time_space"
    ],
    "all_events___geo_source": GEO_SOURCE,
    "all_events___geo_precision_factor": PAGE_GEO_PRECISION,
    "oc_gen_general_time_space___geo_count": 1,
    "oc_gen_general_time_space___geo_location": f"{PAGE_LAT},{PAGE_LON}",
    "oc_gen_general_time_space___geo_location_rpt": f"{PAGE_LAT},{PAGE_LON}",
    "oc_gen_general_time_space___geo_tile": [
        TILE
    ],
    "oc_gen_general_time_space___lr_geo_tile": [
        TILE[:LOW_RESOLUTION_GEOTILE_LENGTH]
    ],
    "oc_gen_general_time_space___geo_source": GEO_SOURCE,
    "oc_gen_general_time_space___geo_precision_factor": PAGE_GEO_PRECISION,
}


def make_site_page_solr_doc(i, link, title, modified_solr_time_str, content):
    solr_doc = copy.deepcopy(DEFAULT_SITE_PAGE_SOLR_DICT)
    slug_title = title.replace('Open Context', '').strip()
    raw_slug = slugify(unidecode(slug_title[:60]))
    solr_slug = 'oc_site_docs_' + raw_slug.replace('-', '_')
    _, uuid = update_old_id(solr_slug)
    solr_doc['uuid'] = uuid
    solr_doc['updated'] = modified_solr_time_str
    solr_doc['sort_score'] = 0 + (i / 100)
    solr_doc['keywords'] = [
        solr_utils.ensure_text_solr_ok(s) for s in SITE_KEY_WORDS.get(link, [])
    ]
    solr_doc['schema_org_text___pred_string'] = [
        solr_utils.ensure_text_solr_ok(content),
    ]
    base_url = AllManifest().clean_uri(settings.CANONICAL_HOST)
    solr_doc['slug_type_uri_label'] = f'{solr_slug}___id___{base_url}{link}___{title}'
    solr_doc['text'] = solr_utils.ensure_text_solr_ok(
        f'{link}\n {title}\n {content}'
    )
    return solr_doc


def make_site_pages_solr_docs():
    rp = RootPath()
    base_url = rp.get_baseurl()
    urls = [
        {
            'display': 'Home Page',
            'link': '/',
        },
    ]
    for nav_root in settings.NAV_ITEMS:
        if nav_root.get('key') != 'about':
            continue
        urls += nav_root.get('urls', [])
    solr_docs = []
    i = 0
    for url_dict in urls:
        i += 1
        label =  url_dict.get('display', 'Open Context Webpage')
        link = url_dict.get('link', '/')
        url = base_url + link
        root = html.parse(url).getroot()
        title_node = root.find(".//title")
        if not len(title_node):
            title = label
        else:
            title = title_node.text_content()
            title = str(title).strip()
        for drop_e in ['style', 'script']:
            drop_nodes = root.findall(f".//{drop_e}")
            if not drop_nodes:
                continue
            for drop_node in drop_nodes:
                drop_node.drop_tree()
        modified_solr_time_str = datetime.datetime.utcnow().strftime(
            '%Y-%m-%dT%H:%M:%SZ'
        )
        try:
            meta_modified = root.get_element_by_id('page_dc_terms_modified')
            if meta_modified is not None:
                modified_solr_time_str = meta_modified.get('content')
                # print(f'Found modified date in HTML: {modified_solr_time_str}')
        except:
            print(f'failed to get modified time from {link}')
            pass
        content_tree = root.get_element_by_id('page')
        content = content_tree.text_content()
        content = str(content).strip()
        content_ex = [s for s in content.split('\n') if len(s.strip())]
        content = '\n'.join(content_ex)
        # print(f'Got content for {label}, {url}, title: {title}')
        # print(content[:250])
        solr_doc = make_site_page_solr_doc(i, link, title, modified_solr_time_str, content)
        solr_docs.append(solr_doc)
    return solr_docs