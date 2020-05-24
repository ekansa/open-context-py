#!/usr/bin/env python
###############################################################################
# $Id$
#
# Project:  GDAL2Tiles, Google Summer of Code 2007 & 2008
#           Global Map Tiles Classes
# Purpose:  Convert a raster into TMS tiles, create KML SuperOverlay EPSG:4326,
#           generate a simple HTML viewers based on Google Maps and OpenLayers
# Author:   Klokan Petr Pridal, klokan at klokan dot cz
# Web:      http://www.klokan.cz/projects/gdal2tiles/
#
###############################################################################
# Copyright (c) 2008 Klokan Petr Pridal. All rights reserved.
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
# OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.
###############################################################################

"""
globalmaptiles.py

Global Map Tiles as defined in Tile Map Service (TMS) Profiles
==============================================================

Functions necessary for generation of global tiles used on the web.
It contains classes implementing coordinate conversions for:

  - GlobalMercator (based on EPSG:900913 = EPSG:3785)
       for Google Maps, Yahoo Maps, Microsoft Maps compatible tiles
  - GlobalGeodetic (based on EPSG:4326)
       for OpenLayers Base Map and Google Earth compatible tiles

More info at:

http://wiki.osgeo.org/wiki/Tile_Map_Service_Specification
http://wiki.osgeo.org/wiki/WMS_Tiling_Client_Recommendation
http://msdn.microsoft.com/en-us/library/bb259689.aspx
http://code.google.com/apis/maps/documentation/overlays.html#Google_Maps_Coordinates

Created by Klokan Petr Pridal on 2008-07-03.
Google Summer of Code 2008, project GDAL2Tiles for OSGEO.

In case you use this class in your product, translate it to another language
or find it usefull for your project please let me know.
My email: klokan at klokan dot cz.
I would like to know where it was used.

Class is available under the open-source GDAL license (www.gdal.org).
"""

import math


class GlobalMercator(object):
    """
    TMS Global Mercator Profile
    ---------------------------

    Functions necessary for generation of tiles in Spherical Mercator projection,
    EPSG:900913 (EPSG:gOOglE, Google Maps Global Mercator), EPSG:3785, OSGEO:41001.

    Such tiles are compatible with Google Maps, Microsoft Virtual Earth, Yahoo Maps,
    UK Ordnance Survey OpenSpace API, ...
    and you can overlay them on top of base maps of those web mapping applications.

    Pixel and tile coordinates are in TMS notation (origin [0,0] in bottom-left).

    What coordinate conversions do we need for TMS Global Mercator tiles::

         LatLon      <->       Meters      <->     Pixels    <->       Tile

     WGS84 coordinates   Spherical Mercator  Pixels in pyramid  Tiles in pyramid
         lat/lon            XY in metres     XY pixels Z zoom      XYZ from TMS
        EPSG:4326           EPSG:900913
         .----.              ---------               --                TMS
        /      \     <->     |       |     <->     /----/    <->      Google
        \      /             |       |           /--------/          QuadTree
         -----               ---------         /------------/
       KML, public         WebMapService         Web Clients      TileMapService

    What is the coordinate extent of Earth in EPSG:900913?

      [-20037508.342789244, -20037508.342789244, 20037508.342789244, 20037508.342789244]
      Constant 20037508.342789244 comes from the circumference of the Earth in meters,
      which is 40 thousand kilometers, the coordinate origin is in the middle of extent.
      In fact you can calculate the constant as: 2 * math.pi * 6378137 / 2.0
      $ echo 180 85 | gdaltransform -s_srs EPSG:4326 -t_srs EPSG:900913
      Polar areas with abs(latitude) bigger then 85.05112878 are clipped off.

    What are zoom level constants (pixels/meter) for pyramid with EPSG:900913?

      whole region is on top of pyramid (zoom=0) covered by 256x256 pixels tile,
      every lower zoom level resolution is always divided by two
      initialResolution = 20037508.342789244 * 2 / 256 = 156543.03392804062

    What is the difference between TMS and Google Maps/QuadTree tile name convention?

      The tile raster itself is the same (equal extent, projection, pixel size),
      there is just different identification of the same raster tile.
      Tiles in TMS are counted from [0,0] in the bottom-left corner, id is XYZ.
      Google placed the origin [0,0] to the top-left corner, reference is XYZ.
      Microsoft is referencing tiles by a QuadTree name, defined on the website:
      http://msdn2.microsoft.com/en-us/library/bb259689.aspx

    The lat/lon coordinates are using WGS84 datum, yeh?

      Yes, all lat/lon we are mentioning should use WGS84 Geodetic Datum.
      Well, the web clients like Google Maps are projecting those coordinates by
      Spherical Mercator, so in fact lat/lon coordinates on sphere are treated as if
      the were on the WGS84 ellipsoid.

      From MSDN documentation:
      To simplify the calculations, we use the spherical form of projection, not
      the ellipsoidal form. Since the projection is used only for map display,
      and not for displaying numeric coordinates, we don't need the extra precision
      of an ellipsoidal projection. The spherical projection causes approximately
      0.33 percent scale distortion in the Y direction, which is not visually noticable.

    How do I create a raster in EPSG:900913 and convert coordinates with PROJ.4?

      You can use standard GIS tools like gdalwarp, cs2cs or gdaltransform.
      All of the tools supports -t_srs 'epsg:900913'.

      For other GIS programs check the exact definition of the projection:
      More info at http://spatialreference.org/ref/user/google-projection/
      The same projection is degined as EPSG:3785. WKT definition is in the official
      EPSG database.

      Proj4 Text:
        +proj=merc +a=6378137 +b=6378137 +lat_ts=0.0 +lon_0=0.0 +x_0=0.0 +y_0=0
        +k=1.0 +units=m +nadgrids=@null +no_defs

      Human readable WKT format of EPGS:900913:
         PROJCS["Google Maps Global Mercator",
             GEOGCS["WGS 84",
                 DATUM["WGS_1984",
                     SPHEROID["WGS 84",6378137,298.2572235630016,
                         AUTHORITY["EPSG","7030"]],
                     AUTHORITY["EPSG","6326"]],
                 PRIMEM["Greenwich",0],
                 UNIT["degree",0.0174532925199433],
                 AUTHORITY["EPSG","4326"]],
             PROJECTION["Mercator_1SP"],
             PARAMETER["central_meridian",0],
             PARAMETER["scale_factor",1],
             PARAMETER["false_easting",0],
             PARAMETER["false_northing",0],
             UNIT["metre",1,
                 AUTHORITY["EPSG","9001"]]]
    """

    def __init__(self, tileSize=256):
        "Initialize the TMS Global Mercator pyramid"
        self.tileSize = tileSize
        self.initialResolution = 2 * math.pi * 6378137 / self.tileSize
        # 156543.03392804062 for tileSize 256 pixels
        self.originShift = 2 * math.pi * 6378137 / 2.0
        # 20037508.342789244
        self.MAX_ZOOM = 20

    def LatLonToMeters(self, lat, lon):
        "Converts given lat/lon in WGS84 Datum to XY in Spherical Mercator EPSG:900913"
        mx = lon * self.originShift / 180.0
        my = math.log(math.tan((90 + lat) * math.pi / 360.0)) / (math.pi / 180.0)
        my = my * self.originShift / 180.0
        return mx, my

    def MetersToLatLon(self, mx, my):
        "Converts XY point from Spherical Mercator EPSG:900913 to lat/lon in WGS84 Datum"
        lon = (mx / self.originShift) * 180.0
        lat = (my / self.originShift) * 180.0

        lat = 180 / math.pi * (2 * math.atan(math.exp(lat * math.pi / 180.0)) - math.pi / 2.0)
        return lat, lon

    def PixelsToMeters(self, px, py, zoom):
        "Converts pixel coordinates in given zoom level of pyramid to EPSG:900913"

        res = self.Resolution(zoom)
        mx = px * res - self.originShift
        my = py * res - self.originShift
        return mx, my

    def MetersToPixels(self, mx, my, zoom):
        "Converts EPSG:900913 to pyramid pixel coordinates in given zoom level"
        res = self.Resolution(zoom)
        px = (mx + self.originShift) / res
        py = (my + self.originShift) / res
        return px, py

    def PixelsToTile(self, px, py):
        "Returns a tile covering region in given pixel coordinates"

        tx = int(math.ceil(px / float(self.tileSize)) - 1)
        ty = int(math.ceil(py / float(self.tileSize)) - 1)
        return tx, ty

    def PixelsToRaster(self, px, py, zoom):
        "Move the origin of pixel coordinates to top-left corner"
        mapSize = self.tileSize << zoom
        return px, mapSize - py

    def MetersToTile(self, mx, my, zoom):
        "Returns tile for given mercator coordinates"
        px, py = self.MetersToPixels(mx, my, zoom)
        return self.PixelsToTile(px, py)

    def TileBounds(self, tx, ty, zoom):
        "Returns bounds of the given tile in EPSG:900913 coordinates"
        minx, miny = self.PixelsToMeters(tx*self.tileSize, ty*self.tileSize, zoom)
        maxx, maxy = self.PixelsToMeters((tx+1)*self.tileSize, (ty+1)*self.tileSize, zoom)
        return (minx, miny, maxx, maxy)

    def TileLatLonBounds(self, tx, ty, zoom):
        "Returns bounds of the given tile in latutude/longitude using WGS84 datum"
        bounds = self.TileBounds(tx, ty, zoom)
        minLat, minLon = self.MetersToLatLon(bounds[0], bounds[1])
        maxLat, maxLon = self.MetersToLatLon(bounds[2], bounds[3])
        return (minLat, minLon, maxLat, maxLon)

    def Resolution(self, zoom):
        "Resolution (meters/pixel) for given zoom level (measured at Equator)"
        # return (2 * math.pi * 6378137) / (self.tileSize * 2**zoom)
        return self.initialResolution / (2**zoom)

    def ZoomForPixelSize(self, pixelSize):
        "Maximal scaledown zoom of the pyramid closest to the pixelSize."
        for i in range(30):
            if pixelSize > self.Resolution(i):
                return i-1 if i != 0 else 0  # We don't want to scale up

    def GoogleTile(self, tx, ty, zoom):
        "Converts TMS tile coordinates to Google Tile coordinates"
        # coordinate origin is moved from bottom-left to top-left corner of the extent
        return tx, (2**zoom - 1) - ty

    def QuadTree(self, tx, ty, zoom):
        "Converts TMS tile coordinates to Microsoft QuadTree"
        quadKey = ""
        ty = (2**zoom - 1) - ty
        for i in range(zoom, 0, -1):
            digit = 0
            mask = 1 << (i-1)
            if (tx & mask) != 0:
                digit += 1
            if (ty & mask) != 0:
                digit += 2
            quadKey += str(digit)
        return quadKey

    def quadtree_to_tile(self, quadtree, zoom):
        """
        Added by Eric Kansa by porting code from PHP version of Open Context
        Converts a quadtree to a tile, as an intermediary step in making lat/lon bounds
        """
        tx = 0
        ty = 0
        i = zoom
        while(i >= 1):
            ch = quadtree[zoom - i]
            mask = 1 << (i-1)
            digit = int(ch)
            if(digit & 1):
                tx += mask
            if(digit & 2):
                ty += mask
            i -= 1
        ty = ((1 << zoom) - 1) - ty
        return tx, ty

    def geojson_coords_to_quadtree(self, coords, zoom=False):
        """
        Added by Eric Kansa to make it easier to get
        a quad tree from GeoJSON point coordinates
        """
        if zoom is False:
            zoom = self.MAX_ZOOM
        return self.lat_lon_to_quadtree(coords[1], coords[0], zoom)

    def lat_lon_to_quadtree(self, lat, lon, zoom=False):
        """
        Added by Eric Kansa by porting code from PHP version of Open Context
        Converts latitude longitude coordinates to a quadtree tile
        """
        if zoom is False:
            zoom = self.MAX_ZOOM
        lat = float(lat)
        lon = float(lon)
        mx, my = self.LatLonToMeters(lat, lon)
        tx, ty = self.MetersToTile(mx, my, zoom)
        return self.QuadTree(tx, ty, zoom)

    def quadtree_to_lat_lon(self, quadtree):
        """
        Added by Eric Kansa by porting code from PHP version of Open Context
        Converts a quadtree tile to bounding latitude and longitude coordinates
        """
        zoom = len(quadtree)
        tx, ty = self.quadtree_to_tile(quadtree, zoom)
        return self.TileLatLonBounds(tx, ty, zoom)
    
    def quadtree_to_geojson_lon_lat(self, quadtree):
        """
        Makes a pair of lon, lat points in the GeoJSON order.
        """
        bounds = self.quadtree_to_lat_lon(quadtree)
        center_lon = (bounds[1] + bounds[3]) / 2
        center_lat = (bounds[0] + bounds[2]) / 2
        return [center_lon, center_lat]

    def quadtree_to_geojson_poly_coords(self, quadtree):
        """
        Transforms a quadree into a set of coordinates for
        a GeoJSON polygon region.

        Added by Eric Kansa
        """
        coords = []
        outer_coords = []
        bounds = self.quadtree_to_lat_lon(quadtree)
        # right hand rule, counter clockwise outside
        outer_coords.append([bounds[1], bounds[0]])
        outer_coords.append([bounds[3], bounds[0]])
        outer_coords.append([bounds[3], bounds[2]])
        outer_coords.append([bounds[1], bounds[2]])
        outer_coords.append([bounds[1], bounds[0]])
        coords.append(outer_coords)
        return coords

    def validate_geo_coordinate(self, coordinate, coord_type):
        """ validates a geo-spatial coordinate """
        is_valid = False
        try:
            fl_coord = float(coordinate)
        except ValueError:
            fl_coord = False
        if fl_coord is not False:
            if 'lat' in coord_type:
                if fl_coord <= 90 and\
                   fl_coord >= -90:
                    is_valid = True
            elif 'lon' in coord_type:
                if fl_coord <= 180 and\
                   fl_coord >= -180:
                    is_valid = True
        return is_valid

    def distance_on_unit_sphere(self, lat1, long1, lat2, long2):
        """ computes KM distances on a sphere
            From: http://gis.stackexchange.com/questions/163785/
            using-python-to-compute-the-distance-
            between-coordinates-lat-long-using-havers
        """
        # Converts lat & long to spherical coordinates in radians.
        if lat1 != lat2 or long1 != long2:
            degrees_to_radians = math.pi/180.0
            # phi = 90 - latitude
            phi1 = (90.0 - lat1)*degrees_to_radians
            phi2 = (90.0 - lat2)*degrees_to_radians
            # theta = longitude
            theta1 = long1*degrees_to_radians
            theta2 = long2*degrees_to_radians
            # Compute the spherical distance from spherical coordinates.
            # For two locations in spherical coordinates:
            # (1, theta, phi) and (1, theta', phi')cosine( arc length ) =
            # sin phi sin phi' cos(theta-theta') + cos phi cos phi' distance = rho * arc    length
            cos = (math.sin(phi1)*math.sin(phi2)*math.cos(theta1 - theta2) + \
                   math.cos(phi1)*math.cos(phi2))
            arc = math.acos(cos)*6371  # radius of the earth in km
        else:
            arc = 0
        return arc

    def get_point_by_distance_from_point(self, lat, lon, dist_km, bearing_deg=90):
        """ finds a lat, lon point (as a dict), givem a lat lon point,
            a km distance and a bearning
        """
        earth_radius = 6371
        bearing_r = bearing_deg * (math.pi /180.0)
        lat_r = math.radians(lat)
        lon_r = math.radians(lon)
        out_lat_r = math.asin(
            math.sin(lat_r) * math.cos(dist_km / earth_radius) \
            + math.cos(lat_r) * math.sin(dist_km / earth_radius) \
            * math.cos(bearing_r)
        )
        out_lon_r = lon_r + (
            math.atan2(math.sin(bearing_r) * math.sin(dist_km / earth_radius) \
                * math.cos(lat_r), math.cos(dist_km / earth_radius) \
                - math.sin(lat_r) * math.sin(out_lat_r)
            )
        )
        output = {
            'lat': math.degrees(out_lat_r),
            'lon': math.degrees(out_lon_r)
        }
        return output