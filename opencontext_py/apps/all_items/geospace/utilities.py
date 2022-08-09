


from shapely.geometry import mapping, shape

from opencontext_py.apps.all_items import configs
from opencontext_py.apps.all_items.models import (
    AllManifest,
    AllSpaceTime,
    AllAssertion,
)


"""
# testing

import importlib
import pandas as pd
import random
from opencontext_py.apps.all_items.models import (
    AllManifest,
    AllSpaceTime,
)
from opencontext_py.apps.all_items.geospace import aggregate as geo_agg
importlib.reload(geo_agg)


data = {
    'longitude': (
        [(random.randint(30, 50) + random.random()) for _ in range(50) ] 
        + [(random.randint(55, 65) + random.random()) for _ in range(20)]
        + [(random.randint(20, 25) + random.random()) for _ in range(50)]
    ),
    'latitude': (
        [(random.randint(30, 50) + random.random()) for _ in range(50)] 
        + [(random.randint(20, 25) + random.random()) for _ in range(20)]
        + [(random.randint(20, 25) + random.random()) for _ in range(50)]
    ), 
}
df = pd.DataFrame(data=data)
r_l = geo_agg.cluster_geo_centroids(df)

"""


def get_centroid_of_coord_box(bbox_coordinates):
    """Gets a centroid tuple from a coordinate box
    
    :param list bbox_coordinates: A list of coordinate
        lists that meet GeoJSON geometry.coordinates expectations

    returns tuple(longitude, latitude)
    """
    geometry = {
        'type': 'Polygon',
        'coordinates': bbox_coordinates,
    }
    s = shape(geometry)
    coords = s.centroid.coords[0]
    # Longitude, Latitude order
    return coords[0], coords[1]


def make_geojson_coord_box(min_lon, min_lat, max_lon, max_lat):
    """ Makes geojson coordinates list for a bounding feature """
    bbox_coordinates = []
    outer_coords = []
    # Right hand rule, counter clockwise outside
    outer_coords.append([min_lon, min_lat])
    outer_coords.append([max_lon, min_lat])
    outer_coords.append([max_lon, max_lat])
    outer_coords.append([min_lon, max_lat])
    outer_coords.append([min_lon, min_lat])
    bbox_coordinates.append(outer_coords)
    return bbox_coordinates


def convert_leaflet_overlay_coords_to_geojson_polygon(coordinates):
    """Converts a list of leaflet overlay coordinate pairs into a geojson 
    polygon geomentry
    
    :param list coordinates: A list of coordinate pairs that
        that Leaflet image overlay coordinates expectations 
        [[upper_right_lat, upper_right_lon], [lower_left_lat, lower_left_lon]]
    
    returns dict (A GeoJSON polygon dict)
    """
    if not isinstance(coordinates, list):
        return None
    try:
        lons = [cpair[1] for cpair in coordinates]
        lats = [cpair[0] for cpair in coordinates]
    except Exception as e:
        print('FAILED to process coordinates')
        print(f'Error {e}')
        raise(ValueError(f'{str(coordinates)}'))
    bbox_coordinates = make_geojson_coord_box(
        min_lon=min(lons), 
        min_lat=min(lats), 
        max_lon=max(lons),
        max_lat=max(lats),
    )
    return {
        'type': 'Polygon',
        'coordinates': bbox_coordinates,
    }