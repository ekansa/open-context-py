#!/usr/bin/env python
import json
import pyproj

from pyproj import Proj, transform

from django.conf import settings
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.libs.validategeojson import ValidateGeoJson


class ReprojectUtilities():
    """
    Useful utilitis to reproject coordinates, package them in GeoJSON
    """

    def __init__(self):
        self.input_crs = None
        self.output_crs = None
        pass
    
    def set_in_out_crs(self, input_crs_id, output_crs_id):
        """Sets the input and output CRS by passing CRS ids. """
        try:
            self.input_crs = Proj('+init=' + input_crs_id)
            self.output_crs = Proj('+init=' + output_crs_id)
        except:
            raise ValueError('Could not set input and output projections.')
        return True
    
    def reproject_coordinates(self, in_x_vals, in_y_vals):
        """Returns lists of reprojected x and y coordinate values. """
        out_x, out_y = pyproj.transform(self.input_crs,
                                        self.output_crs,
                                        in_x_vals,
                                        in_y_vals)
        return out_x, out_y
    
    def list_coordinates(self, out_x, out_y):
        """Lists coordinates of x,y tuples"""
        return [(x, out_y[i]) for i, x in enumerate(out_x)]
    
    def package_coordinates(self, out_x, out_y, geometry_type=None):
        """Packages coordinates into tuples, lists or list of list objects useful for
        generating GeoJSON features """
        coords = self.list_coordinates(out_x, out_y)
        if len(coords) == 1:
            return coords[0]
        if geometry_type == 'Polygon':
            coords.append(coords[0])  # add the first coordinate to the end to close loop
            coordinates = [coords]  # put the coordinates inside a list to make an outer ring.
            v_geojson = ValidateGeoJson()
            c_ok = v_geojson.validate_all_geometry_coordinates(geometry_type,
                                                               coordinates)
            if not c_ok:
                coordinates = v_geojson.fix_geometry_rings_dir(geometry_type,
                                                               coordinates)
            return coordinates
        return coords
    