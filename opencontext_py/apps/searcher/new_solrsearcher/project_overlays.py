import copy
import logging




# Imports directly related to Solr search and response prep.
from opencontext_py.apps.searcher.new_solrsearcher import configs
from opencontext_py.apps.searcher.new_solrsearcher import db_entities


logger = logging.getLogger(__name__)


def get_project_slugs_from_facets(result_json):
    """Makes a list of project slugs from facets

    :param dict result_json: The GeoJSON-LD result JSON
        generated from the solr_json
    """
    project_slugs = []
    for filter in result_json.get("oc-api:active-filters", []):
        if not 'Project' in filter.get("oc-api:filter", ""):
            continue
        project_slugs.append(filter.get("oc-api:filter-slug"))
    for facet in result_json.get("oc-api:has-facets", []):
        if not facet.get("oc-api:has-id-options"):
            continue
        if facet.get("type") != "oc-api:facet-project":
            continue
        for option in facet.get("oc-api:has-id-options"):
            if not option.get("slug"):
                continue
            project_slugs.append(option.get("slug"))
    project_slugs = list(set(project_slugs))
    return project_slugs


def add_project_image_overlays(
    result_json, 
    max_project_count=configs.MAX_PROJECTS_FOR_OVERLAYS
):
    """Adds project image overlay JSON

    :param dict result_json: The GeoJSON-LD result JSON
        generated from the solr_json
    :param int max_project_count: Maximum number of projects
        to return for image overlays
    """
    project_slugs = get_project_slugs_from_facets(result_json)
    if not project_slugs:
        return None
    if len(project_slugs) > max_project_count:
        # Too many projects to ask for image overlays
        return None
    proj_overlay_qs = db_entities.get_project_overlay_qs(
        project_slugs=project_slugs
    )
    print(f'project_slugs has {len(proj_overlay_qs)} overlays')
    overlay_dicts = []
    for act_ass in proj_overlay_qs:
        raw_leaflet = act_ass.object.meta_json.get('leaflet')
        if not raw_leaflet:
            raw_leaflet = act_ass.object.meta_json.get('Leaflet')
        if not raw_leaflet:
            print('no leaflet')
            continue
        leaflet = copy.deepcopy(raw_leaflet)
        leaflet['id'] = f'proj-image-overlay-{act_ass.object.slug}'
        # Use the label in the leaflet object, otherwise default to the 
        # overlay image manifest object's label 
        label = leaflet.get('label', act_ass.object.label)
        if not leaflet.get('opacity'):
            leaflet['opacity'] = configs.GEO_OVERLAY_OPACITY_DEFAULT
        if not leaflet.get('visible'):
            leaflet['visible'] = True
        leaflet['url'] = f"https://{act_ass.object_geo_overlay}"
        leaflet['attribution'] = (
            f'See: <a href="https://{act_ass.object.uri}">{act_ass.object.label}</a>'
        )
        overlay = {
            "id": f"https://{act_ass.object.uri}",
            "label": label,
            "slug": act_ass.object.slug,
            "type": "oc-gen:image",
            "oc-api:leaflet": leaflet,
        }
        overlay_dicts.append(overlay)
    return overlay_dicts