"""Helpers for resolving inherited geospatial + chronology data via SQL."""
from __future__ import annotations

from typing import Dict, Iterable, Optional
from uuid import UUID

from opencontext_py.apps.all_items.models import ManifestBestSpacetime


BestSpacetime = Dict[str, Optional[Dict[str, object]]]


def _normalize_uuid_list(manifest_ids: Iterable[UUID | str]) -> list[str]:
    """Normalizes UUID inputs for use with SQL array parameters."""
    normalized = []
    for value in manifest_ids:
        if value is None:
            continue
        if isinstance(value, UUID):
            normalized.append(str(value))
        else:
            normalized.append(str(value))
    # Preserve order while removing duplicates to avoid redundant SQL work.
    deduped = list(dict.fromkeys(normalized))
    return deduped


def fetch_best_spacetime_for_manifest_ids(manifest_ids: Iterable[UUID | str]) -> Dict[str, Dict[str, Optional[Dict[str, object]]]]:
    """Gets the best available geometry + chronology info for manifest IDs.

    Results rely on PostgreSQL helpers created in
    ``0002_manifest_spacetime_sql``. The function returns a dictionary keyed
    by manifest UUID (as a string). Each value is a dictionary with ``geo``
    and ``chrono`` keys pointing to the selected source metadata or ``None``
    if no suitable data was found anywhere in the context chain.
    """
    uuid_list = _normalize_uuid_list(manifest_ids)
    if not uuid_list:
        return {}

    rows = (
        ManifestBestSpacetime.objects.filter(item_id__in=uuid_list)
        .values(
            'item_id',
            'geo_source_uuid',
            'geo_spacetime_uuid',
            'geo_depth',
            'geometry_type',
            'geometry',
            'latitude',
            'longitude',
            'geo_specificity',
            'chrono_source_uuid',
            'chrono_spacetime_uuid',
            'chrono_depth',
            'earliest',
            'start',
            'stop',
            'latest',
        )
    )

    results: Dict[str, Dict[str, Optional[Dict[str, object]]]] = {
        item_uuid: {'geo': None, 'chrono': None} for item_uuid in uuid_list
    }
    for row in rows:
        item_key = str(row['item_id'])
        geo_source_uuid = row['geo_source_uuid']
        geo_spacetime_uuid = row['geo_spacetime_uuid']
        geo_depth = row['geo_depth']
        geometry_type = row['geometry_type']
        geometry = row['geometry']
        latitude = row['latitude']
        longitude = row['longitude']
        geo_specificity = row['geo_specificity']
        chrono_source_uuid = row['chrono_source_uuid']
        chrono_spacetime_uuid = row['chrono_spacetime_uuid']
        chrono_depth = row['chrono_depth']
        earliest = row['earliest']
        start = row['start']
        stop = row['stop']
        latest = row['latest']
        geo_payload = None
        if geo_spacetime_uuid:
            geo_payload = {
                'source_uuid': str(geo_source_uuid) if geo_source_uuid else None,
                'spacetime_uuid': str(geo_spacetime_uuid),
                'depth': geo_depth,
                'geometry_type': geometry_type,
                'geometry': geometry,
                'latitude': latitude,
                'longitude': longitude,
                'geo_specificity': geo_specificity,
            }
        chrono_payload = None
        if chrono_spacetime_uuid:
            chrono_payload = {
                'source_uuid': str(chrono_source_uuid) if chrono_source_uuid else None,
                'spacetime_uuid': str(chrono_spacetime_uuid),
                'depth': chrono_depth,
                'earliest': earliest,
                'start': start,
                'stop': stop,
                'latest': latest,
            }
        results[item_key] = {
            'geo': geo_payload,
            'chrono': chrono_payload,
        }

    return results


def fetch_best_spacetime_for_manifest(manifest_id: UUID | str) -> Dict[str, Optional[Dict[str, object]]]:
    """Convenience wrapper for a single manifest UUID."""
    data = fetch_best_spacetime_for_manifest_ids([manifest_id])
    return data.get(str(manifest_id), {'geo': None, 'chrono': None})

