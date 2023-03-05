import copy
import time
import datetime
import json
import requests
from lxml import etree

from django.conf import settings
from django.db.models import Min

from opencontext_py.libs.rootpath import RootPath







OAI_PMH_NS = 'http://www.openarchives.org/OAI/2.0/'
XSI_NS = 'http://www.w3.org/2001/XMLSchema-instance'
SL_NS = 'http://www.openarchives.org/OAI/2.0/ http://www.openarchives.org/OAI/2.0/OAI-PMH.xsd'
METADATA_FORMATS = [
    {
        'prefix': 'oai_dc',
        'schema': 'http://www.openarchives.org/OAI/2.0/oai_dc.xsd',
        'ns': 'http://www.openarchives.org/OAI/2.0/oai_dc/',
        'schemaLocation': 'http://www.openarchives.org/OAI/2.0/oai_dc/ http://www.openarchives.org/OAI/2.0/oai_dc.xsd',
        'label': 'OAI Dublin Core',
    },
    {
        'prefix': 'oai_datacite',
        'schema': 'http://schema.datacite.org/oai/oai-1.0/oai.xsd',
        'ns': 'http://schema.datacite.org/oai/oai-1.0/',
        'schemaLocation': 'http://schema.datacite.org/oai/oai-1.0/ http://schema.datacite.org/oai/oai-1.0/oai.xsd',
        'label': 'OAI DataCite',
    },
    {
        'prefix': 'datacite',
        'schema': 'http://schema.datacite.org/meta/nonexistant/nonexistant.xsd',
        'ns': 'http://datacite.org/schema/nonexistant',
        'schemaLocation': 'http://datacite.org/schema/kernel-2.1 http://schema.datacite.org/meta/kernel-2.1/metadata.xsd',
        'label': 'DataCite',
    },
]

DATACITE_RESOURCE = {
    'ns': 'http://datacite.org/schema/kernel-2.1',
    'schemaLocation': 'http://datacite.org/schema/kernel-2.1 http://schema.datacite.org/meta/kernel-2.1/metadata.xsd'
}

TYPICAL_MIMETYPES = [
    'text/html',
    'application/json',
    'application/geo+json',
    'application/ld+json',
]

DC_FORMATS = {
    'subjects': TYPICAL_MIMETYPES.copy(),
    'media': TYPICAL_MIMETYPES.copy(),
    'documents': TYPICAL_MIMETYPES.copy(),
    'projects': TYPICAL_MIMETYPES.copy(),
    'other': [
        'text/html',
        'application/json',
        'application/ld+json',
    ],
}

DATACITE_RESOURCE_TYPES = {
    'subjects': {
        'ResourceTypeGeneral': 'InteractiveResource',
        'oc': 'Data Record',
    },
    'media': {
        'ResourceTypeGeneral': 'InteractiveResource',
        'oc': 'Media resource',
    },
    'projects': {
        'ResourceTypeGeneral': 'Dataset',
        'oc': 'Data publication project',
    },
    'documents': {
        'ResourceTypeGeneral': 'Text',
        'oc': 'Document, diary, or notes',
    },
    'types': {
        'ResourceTypeGeneral': 'InteractiveResource',
        'oc': 'Vocabulary category or concept',
    },
    'predicates': {
        'ResourceTypeGeneral': 'InteractiveResource',
        'oc': 'Predicate, property or relation',
    },
    'other': {
        'ResourceTypeGeneral': 'InteractiveResource',
        'oc': 'Resource',
    },
}

BASE_SETS = {
    'subjects': {
        'params': {'type': 'subjects'},
        'label': 'Data Records',
    },
    'media': {
        'params': {'type': 'media'},
        'label': 'Media resources',
    },
    'documents': {
        'params': {'type': 'documents'},
        'label': 'Documents, Diaries, and Notes',
    },
    'projects':  {
        'params': {'type': 'projects'},
        'label': 'Data Publication Projects',
    },
    'types': {
        'params': {'type': 'types'},
        'label': 'Vocabulary Categories and Concepts',
    },
    'predicates': {
        'params': {'type': 'predicates'},
        'label': 'Predicates, Properties and Relations',
    },
}

# Verbs that are valid for OAI-PMH
VALID_OAI_PMH_VERBS = [
    'Identify',
    'ListMetadataFormats',
    'ListIdentifiers',
    'ListRecords',
    'ListSets',
    'GetRecord',
]

# Parameters required by OAI-PMH 'resumption' requests
REQUIRES_RESUMPTION_TOKEN_PARAS = [
    'start',
    'rows',
    'sort',
    'published',
]
