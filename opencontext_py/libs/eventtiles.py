#!/usr/bin/env python
import re
import numbers
import math
from opencontext_py.libs.chronotiles import ChronoTile
from opencontext_py.libs.globalmaptiles import GlobalMercator


class EventTile():
    """
    Time ranges can be hard to present in hierarchic faceted search
    since ranges do not usually fit into standard buckets.

    To solve this problem, Open Context will start to organize time-spans using a hierarchy of 'tiles,'
    similar to the map tiles in the globalmaptiles.py class

    The EventTile represents an experiment to use time range (chrono-tiles) and geo-spatial tiles
    together to define hierarchic "Event tiles" (events are bounded in space + time)

    EventTiles would allow for hiearchic indexing of space/time bound event entities

    """

    def __init__(self):
        self.CHRONO_TILE_DEPTH = ChronoTile().MAX_TILE_DEPTH
        self.GEO_TILE_DEPTH = GlobalMercator().MAX_ZOOM
        self.LEVEL_DELIM = '-'  # so as not to get confused with the chrono-path '-' prefix
        self.CHRONO_PREFIX_EVENT_SEP = 'e-'

    def encode_path_from_geo_chrono(self,
                                    lat,
                                    lon,
                                    latest_bce_ce,
                                    earliest_bce_ce,
                                    chrono_prefix=''):
        """ encodes an event path from numeric lat, lon, and date values """
        gm = GlobalMercator()
        geo_path = gm.lat_lon_to_quadtree(lat, lon)
        ch = ChronoTile()
        chrono_path = ch.encode_path_from_bce_ce(latest_bce_ce, earliest_bce_ce, chrono_prefix)
        return self.encode_path_from_geo_chrono_paths(geo_path, chrono_path)

    def encode_path_from_geo_chrono_paths(self, geo_path, chrono_path):
        """
        encodes a path bringing together a geo_path and a chrono_path
        """
        chrono_prefix = ''
        if ChronoTile().PREFIX_DELIM in chrono_path:
            # get the range prefix for the chrono_path,
            # and remove it from the path
            cpathex = chrono_path.split(ChronoTile().PREFIX_DELIM)
            chrono_prefix = cpathex[0]
            chrono_prefix += ChronoTile().PREFIX_DELIM
            chrono_path = cpathex[1]
        c_path_len = len(chrono_path)
        g_path_len = len(geo_path)
        event_levels = c_path_len/2
        if event_levels < g_path_len:
            event_levels = g_path_len
        event_path_list = []
        chrono_i = 0
        geo_i = 0
        while len(event_path_list) < event_levels:
            if chrono_i < c_path_len:
                ctile_a = chrono_path[chrono_i]
            else:
                ctile_a = '0'
            if (chrono_i + 1) < c_path_len:
                ctile_b = chrono_path[chrono_i + 1]
            else:
                ctile_b = '0'
            chrono_i += 2
            if geo_i < g_path_len:
                geo_tile = geo_path[geo_i]
            else:
                geo_tile = '0'
            geo_i += 1
            event_tile = ctile_a + ctile_b + geo_tile
            event_path_list.append(event_tile)
        event_path = chrono_prefix + self.CHRONO_PREFIX_EVENT_SEP + self.LEVEL_DELIM.join(event_path_list)
        return event_path

    def reduce_path_precision_level(self, event_path, new_precision=11):
        """ returns a path with a reduced level of precision from the
            input path
        """
        new_path = event_path
        chrono_prefix = False
        if self.CHRONO_PREFIX_EVENT_SEP in event_path:
            event_ex = event_path.split(self.CHRONO_PREFIX_EVENT_SEP)
            chrono_prefix = event_ex[0]
            event_path = event_ex[1]
        else:
            event_path = event_path
        event_path_list = event_path.split(self.LEVEL_DELIM)
        if len(event_path_list) > new_precision:
            new_path_list = event_path_list[0:new_precision]
            new_path = self.LEVEL_DELIM.join(new_path_list)
            if chrono_prefix is not False:
                new_path = chrono_prefix + self.CHRONO_PREFIX_EVENT_SEP + new_path
        return new_path

    def base_four_to_dec(self, base_four):
        """ Converts a base 4 string to a decimal value """
        str_len = len(base_four)
        i = str_len - 1
        multiple = 1
        decimal = 0
        while i >= 0:
            act_digit = int(float(base_four[i]))
            decimal += act_digit * multiple
            i = i - 1
            multiple = multiple * 4
        return decimal

    def decode_event_path(self, event_path):
        """ decodes an event path, with
            chrono_path tiles as the first
            two characters of each level, with
            the geo tile as the last character
        """
        chrono_prefix = ''
        if self.CHRONO_PREFIX_EVENT_SEP in event_path:
            event_ex = event_path.split(self.CHRONO_PREFIX_EVENT_SEP)
            chrono_prefix = event_ex[0]
            event_path = event_ex[1]
        event_path_list = event_path.split(self.LEVEL_DELIM)
        chrono_path = ''
        geo_path = ''
        for event_tile in event_path_list:
            chrono_path = self.add_to_path(event_tile[0],
                                           chrono_path,
                                           self.CHRONO_TILE_DEPTH)
            chrono_path = self.add_to_path(event_tile[1],
                                           chrono_path,
                                           self.CHRONO_TILE_DEPTH)
            geo_path = self.add_to_path(event_tile[2],
                                        geo_path,
                                        self.GEO_TILE_DEPTH)
        chrono_path = chrono_prefix + chrono_path
        ch = ChronoTile()
        gm = GlobalMercator()
        output = {'chrono_path': chrono_path,
                  'chrono': ch.decode_path_dates(chrono_path),
                  'geo_path': geo_path,
                  'geo': gm.quadtree_to_lat_lon(geo_path)}
        return output

    def add_to_path(self, character, path, max_path_len):
        """ adds a character to a path if
            less than the maximum desired length """
        if len(path) < max_path_len:
            path += character
        return path
