
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
# NOTE: These functions bring together mainly Dublin Core assertions
# to make citation information that is simple to express in an HTML
# template
# ---------------------------------------------------------------------


def make_citation_dict(rep_dict):
    """Makes a citation dict from an Open Context rep_dict
    
    :param dict rep_dict: An Open Context representation dict
        that still lacks JSON-LD
    """

    part_of_list = rep_dict.get('dc-terms:isPartOf', [{}])

    citation_dict = {
        'title': rep_dict.get('dc-terms:title'),
        'date_published': rep_dict.get('dc-terms:issued'),
        'date_modified': rep_dict.get('dc-terms:modified'),
        'publisher': configs.OPEN_CONTEXT_PROJ_LABEL,
        'part_of_label': part_of_list[0].get('label'),
        'part_of_uri': part_of_list[0].get('id'),
        'uri': rep_dict.get('id'),
    }

    # Add persistent IDs to the citation dict.
    for scheme_key, scheme_conf in AllIdentifier.SCHEME_CONFIGS.items():
        citation_dict[scheme_key] = None
        url_part = scheme_conf.get('url_root')
        if not url_part:
            continue
        for act_id in rep_dict.get('owl:sameAs', []):
            if url_part in act_id:
                citation_dict[scheme_key] = act_id
    return citation_dict