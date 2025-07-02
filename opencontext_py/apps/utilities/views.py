import json
import pyproj
import uuid as GenUUID

from django.conf import settings
from django.http import HttpResponse

from opencontext_py.libs.reprojection import ReprojectUtilities
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.libs.globalmaptiles import GlobalMercator

from opencontext_py.apps.all_items.legacy_all import update_old_id
from opencontext_py.apps.all_items.models import (
    AllManifest,
)

from opencontext_py.apps.etl.importer import utilities as etl_utils

from opencontext_py.apps.utilities import geospace_contains

from opencontext_py.apps.linkdata.geonames.api import GeonamesAPI
from opencontext_py.apps.linkdata.geonames.data import (
    validate_normalize_geonames_url,
    convert_geonames_bbox_to_geo_json,
)

from django.views.decorators.cache import cache_control
from django.views.decorators.cache import never_cache


API_MAX_ZOOM = 25



@cache_control(no_cache=True)
@never_cache
def geospace_outliers_within(request):
    """Checks if contain relationships for spatial geometries of manifest objects"""
    item_id = request.GET.get('item_id')
    path = request.GET.get('path')
    output = geospace_contains.report_child_coordinate_outliers(
        item_id=item_id,
        path=path,
    )
    if not output:
        return HttpResponse(
            f'Cannot find item_id: "{item_id}" or path: "{path}"',
            status=404,
        )
    return HttpResponse(
        json.dumps(
            output,
            ensure_ascii=False,
            indent=4,
        ),
        content_type='application/json; charset=utf8',
    )


@cache_control(no_cache=True)
@never_cache
def check_geospace_contains(request):
    """Checks if contain relationships for spatial geometries of manifest objects"""
    lat = request.GET.get('lat')
    lon = request.GET.get('lon')
    big_item_id = request.GET.get('big_item_id')
    small_item_id = request.GET.get('small_item_id')
    if request.GET.get('centroid'):
        centroid = True
    else:
        centroid = False
    output = {}
    if big_item_id and lat and lon:
        output = geospace_contains.check_lat_lon_within_item_geometries(
            latitude=lat,
            longitude=lon,
            item_id=big_item_id,
        )
    elif small_item_id:
        output = geospace_contains.check_item_geometries_within_other_item_geometries(
            small_item_id=small_item_id,
            big_item_id=big_item_id,
            centroid=centroid,
        )
    else:
        output = {'errors': ['Must have a big_item_id and either a small_item_id or lat/lon params']}
        return HttpResponse(
            json.dumps(
                output,
                ensure_ascii=False,
                indent=4,
            ),
            content_type='application/json; charset=utf8',
            status=400,
        )
    return HttpResponse(
        json.dumps(
            output,
            ensure_ascii=False,
            indent=4,
        ),
        content_type='application/json; charset=utf8',
    )




@cache_control(no_cache=True)
@never_cache
def uuid(request):
    """Responds with a plain text UUID, optionally deterministically based
    on an id parameter
    """
    id = request.GET.get('id')
    if not id:
        # Make a random new UUID
        uuid = str(GenUUID.uuid4())
    else:
        _, uuid = update_old_id(id)
    return HttpResponse(
        uuid,
        content_type='text/plain; charset=utf8'
    )


@cache_control(no_cache=True)
@never_cache
def human_remains_ok(request):
    """ toggles if the user opts-in or opts-out
        to view human remains
        for this user's session
    """
    prev_opt_in = request.session.get('human_remains_ok')
    if prev_opt_in:
        request.session['human_remains_ok'] = False
    else:
        request.session['human_remains_ok'] = True
    output = LastUpdatedOrderedDict()
    output['previous_opt_in'] = prev_opt_in
    output['new_opt_in'] = request.session['human_remains_ok']
    return HttpResponse(json.dumps(output,
                                   ensure_ascii=False,
                                   indent=4),
                        content_type='application/json; charset=utf8')

def meters_to_lat_lon(request):
    """ Converts Web mercator meters to WGS-84 lat / lon """
    gm = GlobalMercator()
    mx = None
    my = None
    if request.GET.get('mx') is not None:
        mx = request.GET['mx']
    if request.GET.get('my') is not None:
        my = request.GET['my']
    try:
        mx = float(mx)
    except:
        mx = False
    try:
        my = float(my)
    except:
        my = False
    if isinstance(mx, float) and isinstance(my, float):
        lat_lon = gm.MetersToLatLon(mx, my)
        output = LastUpdatedOrderedDict()
        if len(lat_lon) > 0:
            output['lat'] = lat_lon[0]
            output['lon'] = lat_lon[1]
        else:
            output['error'] = 'Stange error, invalid numbers?'
        return HttpResponse(json.dumps(output,
                                       ensure_ascii=False,
                                       indent=4),
                            content_type='application/json; charset=utf8')
    else:
        return HttpResponse('mx and my paramaters must be numbers',
                            status=406)


def lat_lon_to_quadtree(request):
    """ Converts WGS-84 lat / lon to a quadtree tile of a given zoom level """
    gm = GlobalMercator()
    gm.MAX_ZOOM = API_MAX_ZOOM
    lat = None
    lon = None
    rand = None
    lat_ok = False
    lon_ok = False
    zoom = gm.MAX_ZOOM
    if request.GET.get('lat') is not None:
        lat = request.GET['lat']
        lat_ok = gm.validate_geo_coordinate(lat, 'lat')
    if request.GET.get('lon') is not None:
        lon = request.GET['lon']
        lon_ok = gm.validate_geo_coordinate(lon, 'lon')
    if request.GET.get('zoom') is not None:
        check_zoom = request.GET['zoom']
        zoom = etl_utils.validate_transform_data_type_value(
            check_zoom,
            data_type='xsd:integer',
        )
        if zoom is not None:
            # zoom is valid
            if zoom > gm.MAX_ZOOM:
                zoom = gm.MAX_ZOOM
            elif zoom < 1:
                zoom = 1
    if request.GET.get('rand') is not None:
        rand = etl_utils.validate_transform_data_type_value(
            request.GET['rand'],
            data_type='xsd:double',
        )
    if lat_ok and lon_ok and zoom is not None:
        output = gm.lat_lon_to_quadtree(lat, lon, zoom)
        return HttpResponse(
            output,
            content_type='text/plain; charset=utf8',
        )
    else:
        message = 'ERROR: "lat" and "lon" parameters must be valid WGS-84 decimal degrees'
        if zoom is None:
            message += ', "zoom" parameter needs to be an integer between 1 and ' + str(gm.MAX_ZOOM) + '.'
        return HttpResponse(
            message,
            content_type='text/plain; charset=utf8',
            status=406,
        )


def quadtree_to_lat_lon(request):
    """ Converts a quadtree tile to WGS-84 lat / lon coordinates in different formats """
    lat_lon = None
    poly_coords = None
    gm = GlobalMercator()
    gm.MAX_ZOOM = API_MAX_ZOOM
    tile = request.GET.get('tile')
    if tile:
        if request.GET.get('type') == 'Polygon':
            try:
                poly_coords = gm.quadtree_to_geojson_poly_coords(tile)
            except:
                poly_coords = None
        else:
            try:
                lat_lon = gm.quadtree_to_lat_lon(tile)
            except:
                lat_lon = None
    if not lat_lon and not poly_coords:
        message = 'ERROR: "tile" must be a valid quadtree geospatial tile (string composed of digits ranging from 0-3)'
        return HttpResponse(
            message,
            content_type='text/plain; charset=utf8',
            status=406
        )
    content_type='application/json; charset=utf8'

    if poly_coords:
        # Special case where we want polygon coordinates.
        geometry = {
            'type': 'Polygon',
            'coordinates': poly_coords,
        }
        output = json.dumps(
            geometry,
            ensure_ascii=False,
            indent=4,
        )
        return HttpResponse(
            output,
            content_type=content_type,
        )

    # default to json format with lat, lon dictionary object
    lat_lon_dict = LastUpdatedOrderedDict()
    lat_lon_dict['lat'] = lat_lon[0]
    lat_lon_dict['lon'] = lat_lon[1]
    output = json.dumps(
        lat_lon_dict,
        ensure_ascii=False,
        indent=4,
    )
    content_type='application/json; charset=utf8'
    # client requested another format, give it if recognized
    if request.GET.get('format') == 'geojson':
        # geojson format, with longitude then latitude
        output = json.dumps(
            ([lat_lon[1], lat_lon[0]]),
            ensure_ascii=False,
            indent=4,
        )
        content_type='application/json; charset=utf8'
    elif request.GET.get('format') == 'lat,lon':
        # text format, with lat, comma lon coordinates
        output = str(lat_lon[0]) + ',' + str(lat_lon[1])
        content_type='text/plain; charset=utf8'
    return HttpResponse(
        output,
        content_type=content_type,
    )
    


def reproject(request):
    """
http://127.0.0.1:8000/utilities/reproject?format=geojson&geometry=Point&input-proj=poggio-civitate&output-proj=EPSG:4326&x=103.08&y=-60.79

http://127.0.0.1:8000/utilities/reproject?format=geojson&geometry=Point&input-proj=EPSG:3003&output-proj=EPSG:4326&x=169613.07889640043&y=-477999.93973334756
    """


    """ Converts a quadtree tile to WGS-84 lat / lon coordinates in different formats """
    if not (request.GET.get('input-proj') and request.GET.get('output-proj')):
        return HttpResponse('Need input-proj and output-proj parameters to specify projections.',
                            content_type='text/plain; charset=utf8',
                            status=406)
    if not (request.GET.get('x') and request.GET.get('y')):
        return HttpResponse('Need x (Longitude) and y (Latitude) parameters.',
                            content_type='text/plain; charset=utf8',
                            status=406)
    raw_proj_x_vals = request.GET.get('x').split(',')
    raw_proj_y_vals = request.GET.get('y').split(',')
    if len(raw_proj_x_vals) != len(raw_proj_y_vals):
        return HttpResponse('Need the same number of x (Longitude) and y (Latitude) values.',
                            content_type='text/plain; charset=utf8',
                            status=406)
    try:
        proj_x_vals = [(lambda x: float(x.strip()))(x) for x in raw_proj_x_vals]
        proj_y_vals = [(lambda y: float(y.strip()))(y) for y in raw_proj_y_vals]
    except:
        return HttpResponse('All x (Longitude) and y (Latitude) values must be numbers.',
                            content_type='text/plain; charset=utf8',
                            status=406)
    reproj = ReprojectUtilities()
    input_proj = request.GET.get('input-proj')
    if input_proj in ReprojectUtilities.MURLO_PRE_TRANSFORMS:
        # the request uses a Murlo Project local coordinate system
        # we can transform it to global, by first changing the values
        # of the x and y coordinates.
        proj_x_vals, proj_y_vals = reproj.murlo_pre_transform(proj_x_vals,
                                                              proj_y_vals,
                                                              input_proj)
        # now set the input projection to the correct
        input_proj = ReprojectUtilities.MURLO_PRE_TRANSFORMS[input_proj]
    try:
        reproj.set_in_out_crs(input_proj, request.GET.get('output-proj'))
    except:
        return HttpResponse('Could not recognize input and/or output CRS.',
                            content_type='text/plain; charset=utf8',
                            status=406)
    try:
        out_x, out_y = reproj.reproject_coordinates(proj_x_vals, proj_y_vals)
    except:
        return HttpResponse('Transformation failure.',
                            content_type='text/plain; charset=utf8',
                            status=406)
    coords = reproj.package_coordinates(out_x, out_y, request.GET.get('geometry'))
    if (request.GET.get('format') == 'geojson' and
        request.GET.get('geometry')):
        geo = LastUpdatedOrderedDict()
        geo['type'] = request.GET.get('geometry')
        if len(out_x) == 1:
            # always make a Point for single coordinate pairs
            geo['type'] = 'Point'
        geo['coordinates'] = coords
        output = json.dumps(
            geo,
            ensure_ascii=False,
            indent=4,
        )
    else:
        output = json.dumps(
            coords,
            ensure_ascii=False,
            indent=4,
        )
    content_type='application/json; charset=utf8'
    return HttpResponse(
        output,
        content_type=content_type,
    )


def geonames_geojson(request, geonames_uri):
    """Get a geojson object for a geonames item"""
    if not settings.DEBUG:
        return HttpResponse(
            f'Unauthorized, only allow {settings.DEBUG}',
            status=401,
        )
    if 'http' in geonames_uri:
        geonames_uri = validate_normalize_geonames_url(geonames_uri)
    api = GeonamesAPI()
    json_data = api.get_json_for_geonames_uri(geonames_uri)
    geometry = convert_geonames_bbox_to_geo_json(json_data)
    content_type='application/json; charset=utf8'
    if not geometry:
        lat = None
        lon = None
        if json_data.get('lat'):
            lat = float(json_data['lat'])
        if json_data.get('lng'):
            lon = float(json_data['lng'])
        if lat is None or lon is None:
            json_data['oc_note'] = 'bad'
            output = json.dumps(
                json_data,
                ensure_ascii=False,
                indent=4,
            )
            return HttpResponse(
                output,
                status=400,
                content_type=content_type,
            ) 
        geometry = {
            'type': 'Point',
            'coordinates': [
                lon,
                lat,
            ],
        }
    output = json.dumps(
        geometry,
        ensure_ascii=False,
        indent=4,
    )
    content_type='application/json; charset=utf8'
    return HttpResponse(
        output,
        content_type=content_type,
    )