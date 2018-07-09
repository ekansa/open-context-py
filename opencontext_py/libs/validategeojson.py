#!/usr/bin/env python
import math
from django.db import models
from django.conf import settings
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.ocitems.geospace.models import Geospace


class ValidateGeoJson():
    """
    Code to validate GeoJSON and make it conform to the "right hand rule"
    
    This code was inspired and adapted from the MapBox created
    geojson-rewind repo here:
    
    https://github.com/mapbox/geojson-rewind 
    
    The test_good and test_bad coordinate lists
    are provided for testing.
    """

    WGS84_RADIUS = 6378137
    WGS84_FLATTENING = 1/298.257223563
    WGS84_POLAR_RADIUS = 6356752.3142

    def __init__(self):
        # testing good, valid coordinates
        self.test_good = [
                    [
                        [
                            78.09974670410156,
                            9.549969014000085
                        ],
                        [
                            78.10009002685545,
                            9.549969014000085
                        ],
                        [
                            78.10009002685545,
                            9.55030757857335
                        ],
                        [
                            78.09974670410156,
                            9.55030757857335
                        ],
                        [
                            78.09974670410156,
                            9.549969014000085
                        ]
                    ]
                ]
        # testing bad coordinates listed in the wrong direction
        self.test_bad = [
                    [
                        [
                            31.13746345405887,
                            29.975203341460883
                        ],
                        [
                            31.1374668398092,
                            29.9751112230538
                        ],
                        [
                            31.137198093520578,
                            29.975172011251605
                        ],
                        [
                            31.137196168430933,
                            29.975292096585992
                        ],
                        [
                            31.13730958971869,
                            29.975293360313724
                        ],
                        [
                            31.137304125266812,
                            29.975283862123206
                        ],
                        [
                            31.137301269522542,
                            29.975270727601224
                        ],
                        [
                            31.137302412179583,
                            29.97525816424525
                        ],
                        [
                            31.13730812276983,
                            29.97524445855201
                        ],
                        [
                            31.137319543950362,
                            29.97522961052095
                        ],
                        [
                            31.137334962633908,
                            29.975218188717694
                        ],
                        [
                            31.1373480978,
                            29.97520848041729
                        ],
                        [
                            31.13736751398653,
                            29.975203341460883
                        ],
                        [
                            31.137376911262734,
                            29.975204253462266
                        ],
                        [
                            31.13739773151606,
                            29.975201042003434
                        ],
                        [
                            31.137420834388546,
                            29.975200053742565
                        ],
                        [
                            31.137438232060635,
                            29.975200794549117
                        ],
                        [
                            31.13745506020086,
                            29.975203018525235
                        ],
                        [
                            31.13746345405887,
                            29.975203341460883
                        ]
                    ]
                ]
    
    def fix_geometry_rings_dir(self, geometry_type, coordinates):
        """ fixes the directions of rings of coordinates for
            a MultiPolygon or Polygon geometry
        """
        if geometry_type == 'MultiPolygon':
            # a MultiPoylgon will be a list of Polygons
            fixed_coords = []
            for poly_coordinates in coordinates:
                fixed_poly_coords = self.fix_poly_rings_dir(poly_coordinates)
                fixed_coords.append(fixed_poly_coords)
        elif geometry_type == 'Polygon':
            # is a simple polygon
            fixed_coords = self.fix_poly_rings_dir(coordinates)
        else:
            # don't mess with coordinates we don't understand
            fixed_coords = coordinates
        return fixed_coords
    
    def validate_all_geometry_coordinates(self, geometry_type, coordinates):
        """ Validates the directions of rings of coordinates for
            a MultiPolygon or Polygon geometry
            
            Returns True if all rings are valid, False if 1 or more rings
            are not valid (in terms of direction)
        """
        valid = True
        if geometry_type == 'MultiPolygon':
            # a MultiPoylgon will be a list of Polygons
            for poly_coordinates in coordinates:
                rings_ok = self.validate_poly_rings_dir(poly_coordinates)
                for ring_ok in rings_ok:
                    if ring_ok is False:
                        valid = False
        elif geometry_type == 'Polygon':
            # is a simple polygon
            rings_ok = self.validate_poly_rings_dir(coordinates)
            for ring_ok in rings_ok:
                if ring_ok is False:
                    valid = False
        else:
            # don't mess with coordinates we don't understand
            pass
        return valid 
    
    def fix_poly_rings_dir(self, coordinates):
        """ makes new coordinates with valid directions
            for a polygon geometry
        """
        fixed_coords = []
        rings_ok = self.validate_poly_rings_dir(coordinates)
        len_coords = len(coordinates)
        for i in range(0, len_coords):
            if rings_ok[i]:
                # this ring is valid, so add as is
                fixed_coords.append(coordinates[i])
            else:
                # this ring is not valid, so reverse it
                rev_ring = coordinates[i][::-1]
                fixed_coords.append(rev_ring)
        return fixed_coords
    
    def validate_poly_rings_dir(self, coordinates):
        """
        Makes a list of True or False (Valid / Invalid) values
        for rings of coordinates in a polygon geometry
        
        (1) The exterior ring should be counterclockwise. This
            means ring_area calculatations are NEGATIVE
        (2) Interior rings should be clockwise. This means
            ring_area calculations should be POSITIVE
            
        See more at: https://stackoverflow.com/questions/1165647/how-to-determine-if-a-list-of-polygon-points-are-in-clockwise-order/1165943#1165943
        """
        rings_ok = []
        len_coords = len(coordinates)
        if len_coords > 0:
            for i in range(0, len_coords):
                area = self.ring_area(coordinates[i])
                if i == 0:
                    if area < 0:
                        # exterior ring area less than 0, so VALID
                        rings_ok.append(True)
                    else:
                        # not a valid exterior ring
                        rings_ok.append(False)
                else:
                    if area < 0:
                        # negative interiror ring area, so not valid
                        rings_ok.append(False)
                    else:
                        # positive interior ring area, so valid
                        rings_ok.append(True)
        return rings_ok
    
    def polygon_area(self, coordinates):
        """ calculates the area of a polygon, 
            works by subtracting the area of interior
            'donut hole' rings
        """
        area = 0
        len_coords = len(coordinates)
        if len_coords > 0:
            area += abs(self.ring_area(coordinates[0]))
            for i in range(1, len_coords):
                # now subtract the area defined by interior rings
                area -= abs(self.ring_area(coordinates[i]))
        return area
    
    def ring_area(self, coordinates):
        """ calculates the area of a ring of coordinates """
        area = 0
        len_coords = len(coordinates)
        if len_coords > 2:
            for i in range(0, (len_coords - 1)):
                p_a = coordinates[i]
                p_b = coordinates[(i + 1)]
                area += self.rad(p_b[0] - p_a[0]) \
                        * (2 + math.sin(self.rad(p_a[1])) \
                           + math.sin(self.rad(p_b[1])))
            area = area * self.WGS84_RADIUS * self.WGS84_RADIUS / 2
        return area
    
    def rad(self, val):
        output = val * (math.pi / 180)
        return output

    """

# testing
# 
from opencontext_py.libs.validategeojson import ValidateGeoJson
v_geojson = ValidateGeoJson()
bad = v_geojson.validate_poly_rings_dir(v_geojson.test_bad)
good = v_geojson.validate_poly_rings_dir(v_geojson.test_good)
fix_bad_coords = v_geojson.fix_poly_rings_dir(v_geojson.test_bad)
fix_bad = v_geojson.validate_poly_rings_dir(fix_bad_coords)

    """