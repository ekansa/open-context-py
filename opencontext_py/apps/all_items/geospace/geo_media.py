from opencontext_py.apps.all_items.models import (
    AllManifest,
)

from opencontext_py.apps.all_items import permissions
from opencontext_py.apps.all_items.editorial.item import updater_spacetime

from opencontext_py.apps.all_items.geospace import utilities as geo_utils

"""

# To add a space-time geometry to a media overlay image:

from opencontext_py.apps.all_items.geospace.geo_media import add_media_overlay_spacetime_objs

request_list = [{'item_id': '6c89e96d-d97e-4dba-acbe-e822fc1f87e7'},]
add_media_overlay_spacetime_objs(request_list)

"""


DEFAULT_SOURCE_ID = 'geospace-media'


def add_media_overlay_spacetime_objs(request_list, request=None, source_id=DEFAULT_SOURCE_ID):
    """Add AllSpaceTime and from a client request JSON"""
    errors = []
    
    if not isinstance(request_list, list):
        errors.append('Request json must be a list of dictionaries to update')
        return [], errors

    add_list = []
    for item_add in request_list:
        man_obj = None
        if item_add.get('item_id'):
            man_obj = AllManifest.objects.filter(
                uuid=item_add.get('item_id')
            ).first()

        if not man_obj:
            errors.append(f'Cannot find manifest object for location/chronology {str(item_add)}')
            continue

        if man_obj.item_type != 'media':
            errors.append(f'Must be a media item to location/chronology {str(item_add)}')
            continue
        
        coordinates = man_obj.meta_json.get('leaflet', {}).get('bounds')
        if not coordinates:
            coordinates = man_obj.meta_json.get('Leaflet', {}).get('bounds')
        if not coordinates:
            errors.append(f'Could not find leaflet bounds coordinates {str(item_add)}')
            continue

        _, ok_edit = permissions.get_request_user_permissions(
            request, 
            man_obj, 
            null_request_ok=True
        )
        if not ok_edit:
            errors.append(f'Need permission to edit manifest object {man_obj}')
            continue

        geometry = geo_utils.convert_leaflet_overlay_coords_to_geojson_polygon(coordinates)
        
        if geometry is None:
            errors.append(f'Could not make geometry of leaflet bounds from {man_obj}')
            continue
        
        item_add['geometry_type'] = geometry.get('type')
        item_add['geometry'] = geometry
        item_add['meta_json'] = {
            'function': 'geo_utils.convert_leaflet_overlay_coords_to_geojson_polygon',
        }
        add_list.append(item_add)
    
    # Now add all of these results to the database!
    added, new_errors = updater_spacetime.add_spacetime_objs(
        add_list,
        request=None,
        source_id=source_id,
    )
    return added, (errors + new_errors)