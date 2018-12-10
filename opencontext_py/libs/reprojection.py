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
    
    MURLO_PRE_TRANSFORMS = {
        'poggio-civitate': 'EPSG:3003',
        'vescovado-di-murlo': 'EPSG:3003',
    }

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
    
    def make_coordinate_list(self, x_list, y_list):
        """Lists coordinates of x,y tuples"""
        return [(x, y_list[i]) for i, x in enumerate(x_list)]
    
    def package_coordinates(self, out_x, out_y, geometry_type=None):
        """Packages coordinates into tuples, lists or list of list objects useful for
        generating GeoJSON features """
        coords = self.make_coordinate_list(out_x, out_y)
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
    
    def murlo_pre_transform(self, x_list, y_list, local_grid):
        """Transforms Poggio Civitate local coordinates into the EPSG: 3003 projection."""
        coords = self.make_coordinate_list(x_list, y_list)
        epsg3003_x = []
        epsg3003_y = []
        for coord in coords:
            x = coord[0]
            y = coord[1]
            if local_grid == 'poggio-civitate':
                # transform by Taylor Oshan
                epsg3003_x.append(x * 0.999221692962 + y * 0.0447248683267 + 1695135.19719)
                epsg3003_y.append(x * -0.0439247185204 + y * 0.999281902346 + 4780651.43589)
            elif local_grid == 'vescovado-di-murlo':
                # transform by Taylor Oshan
                epsg3003_x.append(x * 0.87120992587 + y * 0.486029300286 + 1694396.08449)
                epsg3003_y.append(x * -0.487297729938 + y * 0.873675651295 + 4782618.57257)
            else:
                # what the hell?
                pass
        print('Local grid transformed: ' + local_grid)
        print('EPSG:3003 x' + str(epsg3003_x))
        print('EPSG:3003 y' + str(epsg3003_y))
        return epsg3003_x, epsg3003_y
    
    def reproject_coordinate_pair(self, c_pair):
        """Reprojects a coordinate pair. """
        if (not isinstance(c_pair, list) or
            not len(c_pair) == 2):
            return None
        if (not isinstance(c_pair[0], float) or
            not isinstance(c_pair[1], float)):
            return None
        x_in = [c_pair[0]]
        y_in = [c_pair[1]]
        # Do the transformation
        x_list, y_list = self.reproject_coordinates(x_in, y_in)
        return [x_list[0], y_list[0]]
    
    def reproject_coordinate_ring(self, ring_list):
        """Reprojects a ring of coorindates"""
        new_ring_list = []
        for c_pair in ring_list:
            new_c_pair = self.reproject_coordinate_pair(c_pair)
            if new_c_pair is not None:
                new_ring_list.append(new_c_pair)
        if new_ring_list[0] != new_ring_list[-1]:
            # Close the ring because the last coordinate needs to
            # be the same as the first.
            new_ring_list.append(new_ring_list[0])
        return new_ring_list
    
    def reproject_mulipolygon(self, coordinates, geometry_type='MultiPolygon'):
        """Reprojects coordinates for a GeoJSON MultiPolygon geometry"""
        new_coordinates = []
        for poly_coordinates in coordinates:
            new_poly_coords = []
            for ring_list in poly_coordinates:
                new_ring_list = self.reproject_coordinate_ring(ring_list)
                new_poly_coords.append(new_ring_list)
            new_coordinates.append(new_poly_coords)
        v_geojson = ValidateGeoJson()
        c_ok = v_geojson.validate_all_geometry_coordinates(geometry_type,
                                                           new_coordinates)
        if not c_ok:
            new_coordinates = v_geojson.fix_geometry_rings_dir(geometry_type,
                                                               new_coordinates)
        return new_coordinates
                
    def reproject_polygon(self, coordinates, geometry_type='Polygon'):
        """Reprojects coordinates for a GeoJSON polygon"""
        new_coordinates = []
        for ring_list in coordinates:
            new_ring_list = self.reproject_coordinate_ring(ring_list)
            new_coordinates.append(new_ring_list)
        v_geojson = ValidateGeoJson()
        c_ok = v_geojson.validate_all_geometry_coordinates(geometry_type,
                                                           new_coordinates)
        if not c_ok:
            new_coordinates = v_geojson.fix_geometry_rings_dir(geometry_type,
                                                               new_coordinates)
        return new_coordinates
    
    def reproject_multi_or_polygon(self, coordinates, geometry_type):
        """Reprojects GeoJSON Polygon or MultiPolygon coordinates"""
        if geometry_type == 'Polygon':
            return self.reproject_polygon(coordinates, geometry_type)
        elif geometry_type == 'MultiPolygon':
            return self.reproject_mulipolygon(coordinates, geometry_type)
        return None