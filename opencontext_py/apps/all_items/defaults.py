
import uuid as GenUUID

from opencontext_py.apps.all_items.models import (
    AllManifest,
    AllString,
    AllAssertion,
    AllHistory,
)

DEFAULT_SOURCE_ID = 'default-open-context'

# The "core" Open Context identifiers.
OPEN_CONTEXT_PROJ_UUID = '252e7a5f-d17c-458e-b244-748b774f47ce'
OPEN_CONTEXT_PUB_UUID = 'aa88bc27-e082-44b5-b51b-73a3f268f939'
OC_GEN_VOCAB_UUID = 'ffc80191-069c-4248-98b7-0a7c0d765b7e'

# Default observation and component
DEFAULT_OBS_UUID = 'bbb19786-548e-494b-8a46-f1f1e39cc9c7'
DEFAULT_ATTRIBUTE_GROUP_UUID = 'ccd1fec5-1172-4393-b805-50095c7e7861'

# Identifiers to core linked data vocabularies.
RDF_VOCAB_UUID = '7ff4bee3-30ce-4c0f-84ec-c3b33eeef5d3'
RDFS_VOCAB_UUID = '609f463f-29e7-41cd-a1d0-d432eac70ccd'
XSD_VOCAB_UUID = '90efec10-9474-4973-af9c-3fa976ce7ae9'
SKOS_VOCAB_UUID = '0159bdec-ef08-4f25-a3bc-d37db4f78663'
OWL_VOCAB_UUID = '62a21dba-47a2-42d1-bcc5-c4304834da46'
DCTERMS_VOCAB_UUID = '583dd1ed-eda8-47e3-be37-f9f772289493'

# Identifiers to other important vocabularies.
DCMI_VOCAB_UUID = '995b4d1e-c2a7-4d3c-a898-775e03e9db28'
BIBO_VOCAB_UUID = '086342f0-81b9-4191-970a-a4f12c65b80c'
FOAF_VOCAB_UUID = '4bf36671-afe7-46d9-ab10-495697242138'
CIDOC_VOCAB_UUID =  '28c5c3c1-737e-46aa-8b0c-b53be37642ef'
DCAT_VOCAB_UUID = 'cc7dad6b-3536-4198-b078-8f6b7e8f49ed'
GEOJSON_VOCAB_UUID = '02116809-f03f-42f5-9e4c-ba0d6453cc91'
CC_VOCAB_UUID = 'b40364f0-292c-4da0-92c2-784ad12d4612'

DEFAULT_MANIFESTS = [
    {
        'uuid': OPEN_CONTEXT_PROJ_UUID,
        'publisher_uuid': OPEN_CONTEXT_PUB_UUID,
        'project_uuid': OPEN_CONTEXT_PROJ_UUID,
        'item_class': None,
        'source_id': DEFAULT_SOURCE_ID,
        'item_type': 'projects',
        'data_type': 'id',
        'slug': 'open-context',
        'label': 'Open Context',
        'sort': '',
        'views': 0,
        'uri': 'opecontext.org/projects/open-context',
        'context_uuid': OPEN_CONTEXT_PROJ_UUID,
        'identifiers': ['0'],
    },
    {
        'uuid': OPEN_CONTEXT_PUB_UUID,
        'publisher': OPEN_CONTEXT_PUB_UUID,
        'project': OPEN_CONTEXT_PROJ_UUID,
        'item_class': None,
        'source_id': DEFAULT_SOURCE_ID,
        'item_type': 'publishers',
        'data_type': 'id',
        'slug': 'open-context-org',
        'label': 'Open Context: Publishing research data on the Web',
        'sort': '',
        'views': 0,
        'uri': 'opecontext.org',
    },
    {
        'uuid': OC_GEN_VOCAB_UUID,
        'publisher': OPEN_CONTEXT_PUB_UUID,
        'project': OPEN_CONTEXT_PROJ_UUID,
        'item_class': None,
        'source_id': DEFAULT_SOURCE_ID,
        'item_type': 'vocabularies',
        'data_type': 'id',
        'slug': 'oc-general',
        'label': 'Open Context Concepts',
        'sort': '',
        'views': 0,
        'uri': 'opencontext.org/vocabularies/oc-general',
        'item_key': 'oc-gen',
        'identifiers': [
            'https://raw.githubusercontent.com/ekansa/oc-ontologies/master/vocabularies/oc-general.owl'
        ],
    },
    {
        'uuid': DEFAULT_OBS_UUID,
        'publisher': OPEN_CONTEXT_PUB_UUID,
        'project': OPEN_CONTEXT_PROJ_UUID,
        'item_class': None,
        'source_id': DEFAULT_SOURCE_ID,
        'item_type': 'observations',
        'data_type': 'id',
        'slug': 'oc-default-obs',
        'label': 'Main Observation',
        'sort': '',
        'views': 0,
        'uri': 'opencontext.org/vocabularies/oc-general/observations#obs-1',
        'item_key': '#obs-1',
    },
    {
        'uuid': DEFAULT_ATTRIBUTE_GROUP_UUID,
        'publisher': OPEN_CONTEXT_PUB_UUID,
        'project': OPEN_CONTEXT_PROJ_UUID,
        'item_class': None,
        'source_id': DEFAULT_SOURCE_ID,
        'item_type': 'attribute-groups',
        'data_type': 'id',
        'slug': 'oc-default-obs',
        'label': 'Default (Single) Attribute Group',
        'sort': '',
        'views': 0,
        'uri': 'opencontext.org/vocabularies/oc-general/attribute-group#group-1',
    }
]

def load_default_manifest(dict_list=DEFAULT_MANIFESTS):
    for man_dict in dict_list:
        uuid = man_dict['uuid']
        m, _ = AllManifest.objects.get_or_create(
            uuid=uuid,
            defaults=man_dict
        )
        print('Item {}, {} ready'.format(m.uuid, m.label))