"""
Don't forget to:

%autoindent

So this can copy and paste OK.
"""
import json
import requests

import numpy as np
import pandas as pd

from django.conf import settings

from django.db.models import Q, OuterRef, Subquery

from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.ldata.linkannotations.models import LinkAnnotation
from opencontext_py.apps.ldata.linkentities.models import LinkEntity

from opencontext_py.apps.imports.sources.models import ImportSource
from opencontext_py.apps.imports.fields.models import ImportField
from opencontext_py.apps.imports.fieldannotations.models import ImportFieldAnnotation
from opencontext_py.apps.imports.records.models import ImportCell


VOCAB_URL= 'http://portal.hearstmuseum.berkeley.edu/catalog/'
PROJECT_UUID = '9cc85c77-e2c3-4534-bbe9-3fef64de7bc2'


HEARST_ENTS = [
    ('5486e629-a11e-4b59-89c6-0883b3229734', 'https://n2t.net/ark:/21549/hm21060014304a', 'Pendant', '6-14304a', ),
    ('5486e629-a11e-4b59-89c6-0883b3229734', 'https://n2t.net/ark:/21549/hm21060014304b', 'Pendant', '6-14304b', ),
    ('5486e629-a11e-4b59-89c6-0883b3229734', 'https://n2t.net/ark:/21549/hm21060014304c', 'Pendant', '6-14304c', ),
]


def get_hearst_item_final_url(ark_url, pref_url_prefix=VOCAB_URL):
    r = requests.get(ark_url, allow_redirects=True)
    final_url = ark_url
    if r.history:
        for resp in r.history:
            print(resp.url)
            final_url = resp.url
            if final_url.startswith(pref_url_prefix):
                return final_url
    return final_url


def get_hearst_stuff(oc_uuid):
    r = requests.get(f'http://127.0.0.1:8000/subjects/{oc_uuid}.json')
    item = r.json()
    obs_list = item.get("oc-gen:has-obs", [])
    if not obs_list:
        return None, None, None
    obs = obs_list[0]
    ark_url = None
    for pred_dict in obs.get("oc-pred:149-museum-persistent-url", []):
        ark_url = pred_dict.get("xsd:string")
        if not ark_url:
            continue
        ark_url = ark_url.split('>https://')[-1]
        ark_url = ark_url.split('</a>')[0]
        ark_url = "https://" + ark_url
    if not ark_url:
        return None, None, None
    item_name = None
    for pred_dict in obs.get("oc-pred:149-item-name", []):
        item_name = pred_dict.get("xsd:string")
    obj_number = None
    for pred_dict in obs.get("oc-pred:149-object-number", []):
        obj_number = pred_dict.get("xsd:string")
    return ark_url, item_name, obj_number


def make_linked_entity(ark_url, item_name, obj_number):
    le = LinkEntity.objects.filter(uri=ark_url).first()
    if le:
        return le
    print(f'New le: {ark_url} {item_name} {obj_number}')
    le = LinkEntity()
    le.uri = ark_url
    le.label = f'{item_name} (ID: {obj_number})'
    le.alt_label = obj_number
    le.vocab_uri = VOCAB_URL
    le.save()
    return le


def make_link_annotation(oc_uuid, le, predicate_uri='dc-terms:references'):
    la = LinkAnnotation.objects.filter(subject=oc_uuid, predicate_uri=predicate_uri, object_uri=le.uri).first()
    if la:
        return la
    print(f'New la: {oc_uuid} -> {predicate_uri} -> {le.uri}')
    la = LinkAnnotation()
    la.subject = oc_uuid
    la.subject_type = 'subjects'
    la.project_uuid = PROJECT_UUID
    la.source_id = 'manual-scripted-2020-12-04'
    la.predicate_uri = predicate_uri
    la.object_uri = le.uri
    la.save()
    return la

def create_and_add_hearst_links():
    exclude_uuids = [u for u, _, _, _ in HEARST_ENTS]
    m_qs = Manifest.objects.filter(
        project_uuid=PROJECT_UUID, 
        class_uri__contains='object',
    ).exclude(uuid__in=exclude_uuids)
    hearst_ents = [] + HEARST_ENTS
    for m in m_qs:
        ark_url, item_name, obj_number = get_hearst_stuff(m.uuid)
        if not ark_url:
            continue
        hearst_ents.append(
            (m.uuid, ark_url, item_name, obj_number,)
        )
    print(f'Process {len(hearst_ents)} links')
    for oc_uuid, ark_url, item_name, obj_number in hearst_ents:
        le = make_linked_entity(ark_url, item_name, obj_number)
        if not le:
            continue
        la = make_link_annotation(oc_uuid, le)


