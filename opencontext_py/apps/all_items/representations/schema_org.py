
import copy
import hashlib
import uuid as GenUUID

from django.core.cache import caches
from django.db.models import OuterRef, Subquery

from opencontext_py.libs.general import LastUpdatedOrderedDict

from opencontext_py.apps.all_items import configs
from opencontext_py.apps.all_items.models import (
    AllManifest,
    AllAssertion,
    AllHistory,
    AllResource,
    AllIdentifier,
    AllSpaceTime,
)
from opencontext_py.apps.all_items import utilities
from opencontext_py.apps.all_items.representations import rep_utils


# ---------------------------------------------------------------------
# NOTE: These functions generate Schema.org JSON-LD metadata for an
# Open Context item
# ---------------------------------------------------------------------
CC_DEFAULT_LICENSE_CC_BY_SCHEMA_DICT  = {
    'id': configs.CC_DEFAULT_LICENSE_CC_BY_URI
}

MAINTAINER_PUBLISHER_DICT = {
    '@id': f'https://{configs.OC_URI_ROOT}',
    'url': f'https://{configs.OC_URI_ROOT}',
    '@type': 'Organization',
    'name': 'Open Context',
    'nonprofitStatus': 'Nonprofit501c3',
    'ethicsPolicy': 'https://opencontext.org/about/terms',
    'brand': ['Open Context', 'Alexandria Archive Institute'],
}


def make_schema_org_org_person_dict(oc_dict):
    """Makes a Schema.org Organization or Person dict from Open Context dict"""
    schema_dict = {
        '@id': oc_dict.get('id'),
        'identifier': oc_dict.get('id'),
        'name': oc_dict.get('label'),
    }
    if oc_dict.get('type', '').endswith('Person'):
        schema_dict['@type'] = 'Person'
    else:
        schema_dict['@type'] = 'Organization'
    return schema_dict


def make_schema_org_json_ld(rep_dict):
    """Makes Schema.org JSON-LD from an Open Context rep_dict
    
    :param dict rep_dict: An Open Context representation dict
        that still lacks JSON-LD
    """
    item_type = utilities.get_oc_item_type_from_uri(rep_dict.get('id'))
    if not item_type:
        return None
    
    description = f'An Open Context "{item_type}" item'
    for des_dict in rep_dict.get('dc-terms:description', [])[:1]:
        for _, v in des_dict.items():
            description = v

    identifiers = [rep_dict.get('id')]
    identifiers += [s_dict.get('id') for s_dict in rep_dict.get('owl:sameAs', [])]

    creators = [
        make_schema_org_org_person_dict(p) 
        for p in rep_dict.get('dc-terms:creator', rep_dict.get('dc-terms:contributor', []))
    ]
    if not len(creators):
        creators = MAINTAINER_PUBLISHER_DICT.copy()

    schema = {
        '@context': 'http://schema.org/',
        '@type': 'Dataset',
        '@id': '#schema-org',
        'name': rep_dict.get('dc-terms:title'),
        'description': description,
        'creator': creators,
        'datePublished': rep_dict.get('dc-terms:issued'),
        'dateModified': rep_dict.get('dc-terms:modified'),
        'license': rep_dict.get(
            'dc-terms:license', 
            [CC_DEFAULT_LICENSE_CC_BY_SCHEMA_DICT]
        )[0].get('id'),
        'maintainer': MAINTAINER_PUBLISHER_DICT.copy(),
        'publisher': MAINTAINER_PUBLISHER_DICT.copy(),
        'identifier': identifiers,
    }
    return schema