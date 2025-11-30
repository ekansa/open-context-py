from __future__ import annotations

from decimal import Decimal
import uuid

import pytest

from opencontext_py.apps.all_items import configs, spacetime_resolver
from opencontext_py.apps.all_items.models import AllManifest, AllSpaceTime
from opencontext_py.apps.all_items.representations.geojson import (
    get_spacetime_geo_and_chronos,
)


def _ensure_manifest(
    *,
    uuid_value: str,
    item_type: str,
    label: str,
    project: AllManifest | None,
    context: AllManifest | None,
    publisher: AllManifest | None,
) -> AllManifest:
    defaults = {
        'source_id': f'default-{uuid_value}',
        'item_type': item_type,
        'label': label,
        'project': project,
        'context': context,
        'publisher': publisher,
        'meta_json': {},
        'uri': f'{configs.OC_URI_ROOT}/{uuid_value}',
    }
    obj, _ = AllManifest.objects.get_or_create(
        uuid=uuid_value,
        defaults=defaults,
    )
    return obj


@pytest.fixture
def core_manifests(db):
    publisher = _ensure_manifest(
        uuid_value=configs.OPEN_CONTEXT_PUB_UUID,
        item_type='publishers',
        label='OC Publisher',
        project=None,
        context=None,
        publisher=None,
    )
    project_root = _ensure_manifest(
        uuid_value=configs.OPEN_CONTEXT_PROJ_UUID,
        item_type='projects',
        label='OC Project',
        project=None,
        context=None,
        publisher=publisher,
    )
    subject_root = _ensure_manifest(
        uuid_value=configs.DEFAULT_SUBJECTS_ROOT_UUID,
        item_type='subjects',
        label='World',
        project=project_root,
        context=None,
        publisher=publisher,
    )
    default_event = _ensure_manifest(
        uuid_value=configs.DEFAULT_EVENT_UUID,
        item_type='events',
        label='Default Event',
        project=project_root,
        context=subject_root,
        publisher=publisher,
    )
    return {
        'publisher': publisher,
        'project': project_root,
        'subject_root': subject_root,
        'event': default_event,
    }


@pytest.fixture
def manifest_factory(core_manifests):
    project = core_manifests['project']
    subject_root = core_manifests['subject_root']
    publisher = core_manifests['publisher']

    def factory(label: str, *, context: AllManifest | None = None) -> AllManifest:
        return AllManifest.objects.create(
            source_id=f'source-{uuid.uuid4()}',
            item_type='projects',
            label=label,
            project=project,
            context=context or subject_root,
            publisher=publisher,
            meta_json={},
        )

    return factory


@pytest.fixture
def spacetime_factory(core_manifests):
    publisher = core_manifests['publisher']
    project = core_manifests['project']
    event = core_manifests['event']

    def factory(
        *,
        item: AllManifest,
        geometry_type: str | None = None,
        geometry: dict | None = None,
        latitude: Decimal | None = None,
        longitude: Decimal | None = None,
        geo_specificity: int | None = None,
        earliest: Decimal | None = None,
        latest: Decimal | None = None,
    ) -> AllSpaceTime:
        return AllSpaceTime.objects.create(
            source_id=f'st-source-{uuid.uuid4()}',
            publisher=publisher,
            project=project,
            item=item,
            event=event,
            geometry_type=geometry_type,
            geometry=geometry,
            latitude=latitude,
            longitude=longitude,
            geo_specificity=geo_specificity,
            earliest=earliest,
            start=earliest,
            stop=latest,
            latest=latest,
        )

    return factory


def _manifest_depth(descendant: AllManifest, ancestor: AllManifest | None) -> int | None:
    if ancestor is None:
        return None
    depth = 0
    current = descendant
    visited: set[uuid.UUID] = set()
    while current:
        if current.uuid == ancestor.uuid:
            return depth
        if not current.context_id or current.context_id in visited:
            break
        visited.add(current.uuid)
        current = current.context
        depth += 1
    raise AssertionError("Ancestor not found in context chain")


def _select_chrono_source(spacetime_obj):
    inherit_chrono = getattr(spacetime_obj, 'inherit_chrono', None)
    if not inherit_chrono:
        return spacetime_obj
    if inherit_chrono.earliest is None or inherit_chrono.latest is None:
        return spacetime_obj
    sp_context_order = getattr(spacetime_obj, 'context_order', None)
    inherit_context_order = getattr(inherit_chrono, 'context_order', None)
    if (
        spacetime_obj.earliest is None
        or spacetime_obj.latest is None
        or (
            inherit_context_order is not None
            and (sp_context_order is None or sp_context_order > inherit_context_order)
        )
    ):
        return inherit_chrono
    return spacetime_obj


def _geo_payload(manifest: AllManifest, spacetime_obj: AllSpaceTime | None):
    if not spacetime_obj:
        return None
    return {
        'source_uuid': str(spacetime_obj.item.uuid),
        'spacetime_uuid': str(spacetime_obj.uuid),
        'depth': _manifest_depth(manifest, spacetime_obj.item),
        'geometry_type': spacetime_obj.geometry_type,
        'geometry': spacetime_obj.geometry,
        'latitude': spacetime_obj.latitude,
        'longitude': spacetime_obj.longitude,
        'geo_specificity': spacetime_obj.geo_specificity,
    }


def _chrono_payload(manifest: AllManifest, spacetime_obj: AllSpaceTime | None):
    if not spacetime_obj:
        return None
    return {
        'source_uuid': str(spacetime_obj.item.uuid),
        'spacetime_uuid': str(spacetime_obj.uuid),
        'depth': _manifest_depth(manifest, spacetime_obj.item),
        'earliest': spacetime_obj.earliest,
        'start': spacetime_obj.start,
        'stop': spacetime_obj.stop,
        'latest': spacetime_obj.latest,
    }


def _best_from_geojson(manifest: AllManifest, *, require_geo: bool = True):
    features = get_spacetime_geo_and_chronos(manifest, require_geo=require_geo)
    if not features:
        return {'geo': None, 'chrono': None}
    primary = features[0]
    geo_obj = primary if primary.geometry_type else getattr(primary, 'inherit_geometry', None)
    chrono_obj = _select_chrono_source(primary)
    geo_payload = _geo_payload(manifest, geo_obj)
    chrono_payload = None
    if chrono_obj and chrono_obj.earliest is not None and chrono_obj.latest is not None:
        chrono_payload = _chrono_payload(manifest, chrono_obj)
    return {'geo': geo_payload, 'chrono': chrono_payload}


@pytest.mark.django_db
def test_best_spacetime_matches_geojson_for_direct_data(
    core_manifests,
    manifest_factory,
    spacetime_factory,
):
    item = manifest_factory('Direct Feature')
    spacetime_factory(
        item=item,
        geometry_type='Point',
        geometry={'type': 'Point', 'coordinates': [1.0, 2.0]},
        latitude=Decimal('2.0'),
        longitude=Decimal('1.0'),
        geo_specificity=5,
        earliest=Decimal('-100.0'),
        latest=Decimal('-50.0'),
    )

    expected = _best_from_geojson(item)
    result = spacetime_resolver.fetch_best_spacetime_for_manifest(item.uuid)
    assert result == expected


@pytest.mark.django_db
def test_best_spacetime_uses_independent_sources(
    core_manifests,
    manifest_factory,
    spacetime_factory,
):
    parent = manifest_factory('Parent Feature')
    child = manifest_factory('Child Feature', context=parent)

    spacetime_factory(
        item=child,
        geometry_type='Point',
        geometry={'type': 'Point', 'coordinates': [10.0, 20.0]},
        latitude=Decimal('20.0'),
        longitude=Decimal('10.0'),
        geo_specificity=2,
    )
    spacetime_factory(
        item=parent,
        earliest=Decimal('-500.0'),
        latest=Decimal('-100.0'),
    )

    expected = _best_from_geojson(child)
    result = spacetime_resolver.fetch_best_spacetime_for_manifest(child.uuid)
    assert result == expected


@pytest.mark.django_db
def test_best_spacetime_returns_chrono_without_geo(
    core_manifests,
    manifest_factory,
    spacetime_factory,
):
    parent = manifest_factory('Chrono Parent')
    child = manifest_factory('Chrono Child', context=parent)

    spacetime_factory(
        item=parent,
        earliest=Decimal('100.0'),
        latest=Decimal('200.0'),
    )

    expected = _best_from_geojson(child, require_geo=False)
    result = spacetime_resolver.fetch_best_spacetime_for_manifest(child.uuid)
    assert result == expected
