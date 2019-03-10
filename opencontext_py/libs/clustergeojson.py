#!/usr/bin/env python
import json
import math
import numpy as np
from numpy import vstack, array
from scipy.cluster.vq import kmeans,vq
from math import radians, cos, sin, asin, sqrt
from django.conf import settings
from shapely.geometry import shape, mapping 
from shapely.ops import cascaded_union, unary_union
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.libs.validategeojson import ValidateGeoJson


class ClusterGeoJson():
    """
    Code to group geojson features into clusters
    """
    def __init__(self):
        self.number_clusters = 20
        self.simplify_tolerance = 0.075
        self.buffer_tolerance = 0.00000000000001
        self.idx = None
        self.data = None
        self.centroids = None
        self.sorted_centroids = None
        self.lon_lats = [] # list of all longitude and latitude pairs
        self.cluster_index_prop = 'lon-lat-cluster-index'
        self.cluster_property = 'lon-lat-cluster'
        self.cluster_num_features_prop = 'lon-lat-cluster-num-features'
        self.raw_features = {}
        
    def extact_lon_lat_data_from_geojson(self, geojson_obj):
        """Gets centroids or lon_lat coordinates from geojson features """
        for feat in geojson_obj['features']:
            if 'properties' not in feat:
                feat['properties'] = LastUpdatedOrderedDict()
            lon_lat = self.get_feature_centroid(feat['geometry'])
            feat['properties'][self.cluster_index_prop] = len(self.lon_lats)
            self.lon_lats.append(lon_lat)
        return geojson_obj
    
    def cluster_lon_lats(self):
        """Clusters the list of lon_lats into groups """
        np_lon_lats = []
        for lon_lat in self.lon_lats:
            dpoint = np.fromiter(lon_lat, np.dtype('float'))
            np_lon_lats.append(dpoint)
        data = array(np_lon_lats)
        centroids, _ = kmeans(data, self.number_clusters)
        idx, _ = vq(data, centroids)
        self.idx = idx
        self.data = data
        self.centroids = centroids
        # Sort the centroids by lon, then lat
        sc = centroids[centroids[:,1].argsort()]
        sc = sc[sc[:,0].argsort()]
        self.sorted_centroids = sc.tolist()
    
    def get_cluster_group(self, lon_lat_index):
        """Gets the cluster group based, where the group number is
           determined by the order of the sorted index """
        raw_centroid_index = self.idx[lon_lat_index]
        act_centroid = self.centroids[raw_centroid_index]
        act_l_centroid = act_centroid.tolist()
        # The cluster group is the index number of the sorted list of
        # cluster centroids plus 1 (so we don't have a group 0).
        return self.sorted_centroids.index(act_l_centroid) + 1
        
    
    def add_cluster_property_to_geojson(self, geojson_obj):
        """Adds cluster information to geojson features"""
        i = 0
        for feat in geojson_obj['features']:
            if 'properties' not in feat:
                feat['properties'] = LastUpdatedOrderedDict()
            if self.cluster_index_prop in feat['properties']:
                lon_lat_index = feat['properties'][self.cluster_index_prop]
            else:
                lon_lat_index = i
            # The makes a more human readable cluster group number (no 0).
            # The group numnber is predictable, based on the location of
            # the group's centroid.
            cluster_group = self.get_cluster_group(lon_lat_index)
            feat['properties'][self.cluster_property] = cluster_group
            if cluster_group not in self.raw_features:
                self.raw_features[cluster_group] = []
            self.raw_features[cluster_group].append(feat['geometry'])
            i += 1

        return geojson_obj
            
            
    def make_clusters_geojson(self):
        """Makes a feature collection of aggregated feature geometries """
        geojson = LastUpdatedOrderedDict()
        geojson['type'] = 'FeatureCollection'
        geojson['features'] = []
        for cluster_group, feat_geoms in self.raw_features.items():
            geoms = []
            for feat_geometry in feat_geoms:
                geom_raw = shape(feat_geometry)
                geom = geom_raw.buffer(self.buffer_tolerance)
                if geom.is_valid:
                    geoms.append(geom)
            if len(geoms) < 1:
                # No valid geometries for this cluster, so skip
                continue
            union_geom = unary_union(geoms)
            poly_union = union_geom.convex_hull
            poly_union_simple = poly_union.simplify(self.simplify_tolerance)
            feat = LastUpdatedOrderedDict()
            feat['type'] = 'Feature'
            feat['properties'] = LastUpdatedOrderedDict()
            feat['properties'][self.cluster_property] = cluster_group
            feat['properties'][self.cluster_num_features_prop] = len(geoms)
            feat['geometry'] = LastUpdatedOrderedDict()
            geometry_type = poly_union_simple.geom_type
            coordinates = [list(poly_union_simple.exterior.coords)]
            v_geojson = ValidateGeoJson()
            c_ok = v_geojson.validate_all_geometry_coordinates(geometry_type,
                                                               coordinates)
            if not c_ok:
                coordinates = v_geojson.fix_geometry_rings_dir(geometry_type, coordinates)
            feat['geometry']['type'] = geometry_type
            feat['geometry']['coordinates'] = coordinates
            centroid = self.get_feature_centroid(feat['geometry'])
            feat['properties']['latitude'] = centroid[1]
            feat['properties']['longitude'] = centroid[0]
            geojson['features'].append(feat)
        return geojson
    
    def get_feature_centroid(self, feature_geometry):
        """Gets the centroid from a feature's geometry"""
        if feature_geometry['type'].lower() == 'point':
            return feature_geometry['coordinates']
        else:
            geom = shape(feature_geometry)
            g_centroid = geom.centroid
            centroid = mapping(g_centroid)
            return centroid['coordinates']