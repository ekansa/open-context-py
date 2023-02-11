import logging

from opencontext_py.libs.rootpath import RootPath
from opencontext_py.apps.searcher.new_solrsearcher import db_entities

logger = logging.getLogger(__name__)


# Keys for different result_json key values to copy over to the new project
# geo_json dict
PROJ_GEO_JSON_KEYS = [
    "@context",
    "dcmi:modified",
    "dcmi:created",
    "oai-pmh:earliestDatestamp",
    "totalResults",
]


def get_project_facet_options(result_json):
    """Makes a list of projects from facets

    :param dict result_json: The GeoJSON-LD result JSON
        generated from the solr_json
    """
    project_dicts = []
    for facet in result_json.get("oc-api:has-facets", []):
        if not facet.get("oc-api:has-id-options"):
            continue
        if facet.get("type") != "oc-api:facet-project":
            continue
        for option in facet.get("oc-api:has-id-options"):
            if not option.get("slug"):
                continue
            count = option.get("count", 0)
            if count < 2:
                continue
            project_dicts.append(option)
    return project_dicts


def get_banner_url_by_slug(proj_banner_qs, slug):
    """Gets the banner image url for a slug"""
    if not proj_banner_qs:
        return None
    if not slug:
        return None
    for man_obj in proj_banner_qs:
        if man_obj.slug != slug:
            continue
        if man_obj.item_hero_hero:
            return man_obj.item_hero_hero
        elif man_obj.proj_hero:
            return man_obj.proj_hero
        elif man_obj.proj_proj_hero:
            return man_obj.proj_proj_hero
        else:
            return None
    return None


def make_project_geojson_features(
    result_json,
):
    """Adds project image overlay JSON

    :param dict result_json: The GeoJSON-LD result JSON
        generated from the solr_json

    """
    project_dicts = get_project_facet_options(result_json)
    if not project_dicts:
        return None
    rp = RootPath()
    base_url = rp.get_baseurl()
    project_slugs = [proj_dict.get('slug') for proj_dict in project_dicts]
    proj_geo_qs = db_entities.get_proj_geo_by_slugs(project_slugs)
    proj_banner_qs = db_entities.get_project_banner_qs(project_slugs=project_slugs)
    features = []
    for proj_dict in project_dicts:
        hero_banner_url = get_banner_url_by_slug(
            proj_banner_qs,
            proj_dict.get('slug', '')
        )
        for p_obj in proj_geo_qs:
            if proj_dict.get('slug') != p_obj.item.slug:
                continue
            feature = {
                'type': 'Feature',
                'count': proj_dict.get('count'),
                'id': f'#proj-map-feature-{p_obj.feature_id}-{p_obj.item.slug}',
                'geometry': {
                    'id': f'#proj-map-geo-{p_obj.feature_id}-{p_obj.item.slug}',
                    'type': 'Point',
                    'coordinates': [
                        float(p_obj.longitude),
                        float(p_obj.latitude)
                    ]
                },
                'properties': {
                    'id': f'#proj-map-props-{p_obj.item.slug}',
                    'label': p_obj.item.label,
                    'description': p_obj.description,
                    'count': proj_dict.get('count'),
                    'href': f'{base_url}/{p_obj.item.item_type}/{p_obj.item.uuid}',
                    'query_link': proj_dict.get('id'),
                },
            }
            if hero_banner_url:
                feature['properties']['hero_banner_url'] = f'https://{hero_banner_url}'
            features.append(feature)
            break
    return features


def make_map_project_geojson(
    result_json,
):
    """Adds project image overlay JSON

    :param dict result_json: The GeoJSON-LD result JSON
        generated from the solr_json
    :param int max_project_count: Maximum number of projects
        to return for image overlays
    """
    rp = RootPath()
    base_url = rp.get_baseurl()
    geo_json = {
        key: result_json.get(key) for key in PROJ_GEO_JSON_KEYS if result_json.get(key)
    }
    geo_json['id'] = f'{base_url}/map-projects.json'
    geo_json['type'] = 'FeatureCollection'
    geo_json['features'] = make_project_geojson_features(result_json)
    return geo_json