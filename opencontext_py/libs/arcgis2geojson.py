#!/usr/bin/env python
import json
import os
import codecs
from django.db import models
from django.conf import settings
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.ocitems.geospace.models import Geospace, GeospaceGeneration


class Arcgis2geojson():
    """
arcgis2geojson is a derivative work of ESRI's arcgis-to-geojson-utils:
https://github.com/Esri/arcgis-to-geojson-utils/
Original code is Copyright 2015 by Esri and was licensed under
the Apache License, Version 2.0: http://www.apache.org/licenses/LICENSE-2.0
Ported to Python in 2016 by Chris Shaw.
arcgis2geojson is made available under the MIT License.

import json
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.ocitems.geospace.models import Geospace, GeospaceGeneration
from opencontext_py.libs.arcgis2geojson import Arcgis2geojson
arc_geojson = Arcgis2geojson()
class_uri = 'oc-gen:cat-unit'
project_uuid = '3585b372-8d2d-436c-9a4c-b5c10fce3ccd'
arc_geojson.act_export_dir = 'gabii-gis'
geojson = arc_geojson.get_dict_from_file('gabii_areaB_published_reproj')
new_geojson = LastUpdatedOrderedDict()
new_geojson['type'] = 'FeatureCollection'
new_geojson['features'] = []
uuid_geos = {}
no_reverse_object_ids = [
    26888
]
for feat in geojson['features']:
    su_id = str(feat['properties']['SU'])
    object_id = feat['properties']['OBJECTID']
    label = 'Unit ' + su_id
    man_objs = Manifest.objects.filter(label=label, class_uri=class_uri, project_uuid=project_uuid)[:1]
    if len(man_objs) > 0:
        man_obj = man_objs[0]
        geometry = feat['geometry']
        coords = geometry['coordinates']
        new_coord_rings = []
        for ring in coords:
            n_sub_rings = []
            for sub_ring in ring:
                if object_id in no_reverse_object_ids:
                    r_n_sub_ring = sub_ring[::-1]
                else:
                    r_n_sub_ring = sub_ring[::-1]
                n_sub_rings.append(r_n_sub_ring)
            new_coord_rings.append(n_sub_rings)
        if man_obj.uuid not in uuid_geos:
            uuid_dict = {
                'man_obj': man_obj,
                'type': geometry['type'],
                'cnt': 0,
                'coord_list': []
            }
        else:
            uuid_dict = uuid_geos[man_obj.uuid]
        uuid_dict['cnt'] += 1
        uuid_dict['coord_list'].append(new_coord_rings)
        uuid_geos[man_obj.uuid] = uuid_dict
        new_feat = feat
        new_feat['properties']['uri'] = 'http://opencontext.org/subjects/' + man_obj.uuid
        new_feat['geometry']['coordinates'] = new_coord_rings
        if len(new_geojson['features']) < 20000:
            new_geojson['features'].append(new_feat)
            # print(label + ' is ' + man_obj.uuid + ', found: ' + str(uuid_dict['cnt']))
    else:
        print(label + ' is NOT FOUND!! ')
arc_geojson.save_serialized_json('gabii-areaB-published-reproj-oc-linked', new_geojson)
for uuid, uuid_dict in uuid_geos.items():
    man_obj = uuid_dict['man_obj']
    f_num = 0
    for coords in uuid_dict['coord_list']:
        f_num += 1
        geo_fs = Geospace.objects.filter(uuid=uuid, feature_id=f_num)[:1]
        if len(geo_fs) < 1:
            coord_str =  json.dumps(coords,
                                    indent=4,
                                    ensure_ascii=False)
            gg = GeospaceGeneration()
            try:
                lonlat = gg.get_centroid_lonlat_coordinates(coord_str)
            except:
                lonlat = False
            if lonlat is False:
                # try within the string
                s_coord_str = json.dumps(coords[0],
                                         indent=4,
                                         ensure_ascii=False)
                try:
                    lonlat = gg.get_centroid_lonlat_coordinates(s_coord_str)
                except:
                    lonlat = False
            print(man_obj.label + ' is ' + man_obj.uuid + ', at: ' + str(lonlat))
            if lonlat is not False:
                geo = Geospace()
                geo.uuid = str(man_obj.uuid)
                geo.project_uuid = man_obj.project_uuid
                geo.source_id = 'gabii-areaB-published-oc-linked'
                geo.item_type = 'subjects'
                geo.feature_id = f_num
                geo.meta_type = 'oc-gen:discovey-location'
                geo.ftype = uuid_dict['type']
                geo.latitude = lonlat[1]
                geo.longitude = lonlat[0]
                geo.specificity = 0
                # dump coordinates as json string
                geo.coordinates = coord_str
                try:
                    geo.save()
                except:
                    print('Did not like ' + str(uuid) + ' with ' + str(uuid_dict))
    """

    def __init__(self):
        self.root_export_dir = settings.STATIC_EXPORTS_ROOT
        self.act_export_dir = False
    
    def convert_save_to_geojson(self, file_name):
        """ loads an ESRI json file, converts, saves as GeoJSON """
        arcgis = self.get_dict_from_file(file_name)
        if arcgis is not False:
            geojson = LastUpdatedOrderedDict()
            if 'features' in arcgis:
                geojson['features'] = []
                for arc_feat in arcgis['features']:
                    geojson_f = self.arcgis2geojson(arc_feat)
                    geojson['features'].append(geojson_f)
            else:
                geojson = self.arcgis2geojson(arcgis)
            self.save_serialized_json(file_name, geojson)
    
    def check_exists(self, file_name):
        """ checks to see if a file exists """
        if '.json' not in file_name:
            file_name = file_name + '.json'
        path = self.prep_directory(self.act_export_dir)
        dir_file = path + file_name
        if os.path.exists(dir_file):
            output = True
        else:
            print('Cannot find: ' + path)
            output = False
        return output
    
    def save_serialized_json(self, key, dict_obj):
        """ saves a data in the appropriate path + file """
        if '.json' not in key:
            file_name = key + '.json'
        file_name = 'geojson-' + file_name
        path = self.prep_directory(self.act_export_dir)
        dir_file = path + file_name
        print('save to path: ' + dir_file)
        json_output = json.dumps(dict_obj,
                                 indent=4,
                                 ensure_ascii=False)
        file = codecs.open(dir_file, 'w', 'utf-8')
        file.write(json_output)
        file.close()
    
    def get_dict_from_file(self, key):
        """ gets the file string
            if the file exists,
        """
        if '.json' not in key:
            file_name = key + '.json'
        json_obj = None
        ok = self.check_exists(file_name)
        if ok:
            path = self.prep_directory(self.act_export_dir)
            dir_file = path + file_name
            try:
                json_obj = json.load(codecs.open(dir_file,
                                                 'r',
                                                 'utf-8-sig'))
            except:
                print('Cannot parse as JSON: ' + dir_file)
                json_obj = False
        return json_obj

    def pointsEqual(self, a, b):
        """
        checks if 2 [x, y] points are equal
        """
        for i in range(0, len(a)):
            if a[i] != b[i]:
                return False
        return True
    
    
    def closeRing(self, coordinates):
        """
        checks if the first and last points of a ring are equal and closes the ring
        """
        if not self.pointsEqual(coordinates[0], coordinates[len(coordinates) - 1]):
            coordinates.append(coordinates[0])
        return coordinates
    
    
    def ringIsClockwise(self, ringToTest):
        """
        determine if polygon ring coordinates are clockwise. clockwise signifies
        outer ring, counter-clockwise an inner ring or hole.
        """
    
        total = 0
        i = 0
        rLength = len(ringToTest)
        pt1 = ringToTest[i]
        pt2 = None
        for i in range(0, rLength - 1):
            pt2 = ringToTest[i + 1]
            total += (pt2[0] - pt1[0]) * (pt2[1] + pt1[1])
            pt1 = pt2
    
        return (total >= 0)
    
    
    def vertexIntersectsVertex(self, a1, a2, b1, b2):
        uaT = (b2[0] - b1[0]) * (a1[1] - b1[1]) - (b2[1] - b1[1]) * (a1[0] - b1[0])
        ubT = (a2[0] - a1[0]) * (a1[1] - b1[1]) - (a2[1] - a1[1]) * (a1[0] - b1[0])
        uB = (b2[1] - b1[1]) * (a2[0] - a1[0]) - (b2[0] - b1[0]) * (a2[1] - a1[1])
    
        if uB != 0:
            ua = uaT / uB
            ub = ubT / uB
    
            if ua >= 0 and ua <= 1 and ub >= 0 and ub <= 1:
                return True
    
        return False
    
    
    def arrayIntersectsArray(self, a, b):
        for i in range(0, len(a)-1):
            for j in range(0, len(b)-1):
                if self.vertexIntersectsVertex(a[i], a[i + 1], b[j], b[j + 1]):
                    return True
    
        return False
    
    
    def coordinatesContainPoint(self, coordinates, point):
    
        contains = False
        l = len(coordinates)
        i = -1
        j = l - 1
        while ((i + 1) < l):
            i = i + 1
            ci = coordinates[i]
            cj = coordinates[j]
            if ((ci[1] <= point[1] and point[1] < cj[1]) or (cj[1] <= point[1] and point[1] < ci[1])) and\
               (point[0] < (cj[0] - ci[0]) * (point[1] - ci[1]) / (cj[1] - ci[1]) + ci[0]):
                contains = not contains
            j = i
        return contains
    
    
    def coordinatesContainCoordinates(self, outer, inner):
        intersects = self.arrayIntersectsArray(outer, inner)
        contains = self.coordinatesContainPoint(outer, inner[0])
        if not intersects and contains:
            return True
        return False
    
    
    def convertRingsToGeoJSON(self, rings):
        """
        do any polygons in this array contain any other polygons in this array?
        used for checking for holes in arcgis rings
        """
    
        outerRings = []
        holes = []
        x = None  # iterator
        outerRing = None  # current outer ring being evaluated
        hole = None  # current hole being evaluated
    
        # for each ring
        for r in range(0, len(rings)):
            ring = self.closeRing(rings[r])
            if len(ring) < 4:
                continue
    
            # is this ring an outer ring? is it clockwise?
            if self.ringIsClockwise(ring):
                polygon = [ring]
                outerRings.append(polygon)  # push to outer rings
            else:
                holes.append(ring)  # counterclockwise push to holes
    
        uncontainedHoles = []
    
        # while there are holes left...
        while len(holes):
            # pop a hole off out stack
            hole = holes.pop()
    
            # loop over all outer rings and see if they contain our hole.
            contained = False
            x = len(outerRings) - 1
            while (x >= 0):
                outerRing = outerRings[x][0]
                if self.coordinatesContainCoordinates(outerRing, hole):
                    # the hole is contained push it into our polygon
                    outerRings[x].append(hole)
                    contained = True
                    break
                x = x-1
    
            # ring is not contained in any outer ring
            # sometimes this happens https://github.com/Esri/esri-leaflet/issues/320
            if not contained:
                uncontainedHoles.append(hole)
    
        # if we couldn't match any holes using contains we can try intersects...
        while len(uncontainedHoles):
            # pop a hole off out stack
            hole = uncontainedHoles.pop()
    
            # loop over all outer rings and see if any intersect our hole.
            intersects = False
            x = len(outerRings) - 1
            while (x >= 0):
                outerRing = outerRings[x][0]
                if arrayIntersectsArray(outerRing, hole):
                    # the hole is contained push it into our polygon
                    outerRings[x].append(hole)
                    intersects = True
                    break
                x = x-1
    
            if not intersects:
                outerRings.append([hole[::-1]])
    
        if len(outerRings) == 1:
            return {
                'type': 'Polygon',
                'coordinates': outerRings[0]
            }
        else:
            return {
                'type': 'MultiPolygon',
                'coordinates': outerRings
            }
    
    
    def arcgis2geojson(self, arcgis, idAttribute=None):
        """
        Convert an ArcGIS JSON object to a GeoJSON object
        """
    
        geojson = LastUpdatedOrderedDict()
    
        if 'x' in arcgis and 'y' in arcgis:
            geojson['type'] = 'Point'
            geojson['coordinates'] = [arcgis['x'], arcgis['y']]
    
        if 'points' in arcgis:
            geojson['type'] = 'MultiPoint'
            geojson['coordinates'] = arcgis['points']
    
        if 'paths' in arcgis:
            if len(arcgis['paths']) == 1:
                geojson['type'] = 'LineString'
                geojson['coordinates'] = arcgis['paths'][0]
            else:
                geojson['type'] = 'MultiLineString'
                geojson['coordinates'] = arcgis['paths']
    
        if 'rings' in arcgis:
            geojson = self.convertRingsToGeoJSON(arcgis['rings'])
    
        if 'geometry' in arcgis or 'attributes' in arcgis:
            geojson['type'] = 'Feature'
            if 'geometry' in arcgis:
                geojson['geometry'] = self.arcgis2geojson(arcgis['geometry'])
            else:
                geojson['geometry'] = None
    
            if 'attributes' in arcgis:
                geojson['properties'] = arcgis['attributes']
                if idAttribute in arcgis['attributes']:
                    geojson['id'] = arcgis['attributes'][idAttribute]
                elif 'OBJECTID' in arcgis['attributes']:
                    geojson['id'] = arcgis['attributes']['OBJECTID']
                elif 'FID' in arcgis['attributes']:
                    geojson['id'] = arcgis['attributes']['FID']
            else:
                geojson['properties'] = None
    
        return geojson

    def prep_directory(self, act_dir):
        """ Prepares a directory to receive export files """
        output = False
        full_dir = self.root_export_dir
        if self.act_export_dir is not False:
            full_dir = self.root_export_dir + act_dir + '/'
        full_dir.replace('//', '/')
        if not os.path.exists(full_dir):
            print('Prepared directory: ' + str(full_dir))
            os.makedirs(full_dir)
        if os.path.exists(full_dir):
            output = full_dir
        if output[-1] != '/':
            output += '/'
        return output
