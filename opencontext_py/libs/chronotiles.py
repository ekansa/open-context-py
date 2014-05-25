#!/usr/bin/env python
import re
import numbers


class ChronoTile():
    """
    Time ranges can be hard to present in hierarchic faceted search
    since ranges do not usually fit into standard buckets.

    To solve this problem, Open Context will start to organize time-spans using a hierarchy of 'tiles,'
    similar to the map tiles in the globalmaptiles.py class

    """

    def __init__(self):
        self.DEFAULT_MAXIMUM_BP = 10000000  # 10 million years ago
        self.MAX_TILE_DEPTH = 30
        self.MIN_INTERVAL_SPAN = .5
        self.PREFIX_DELIM = '-'
        self.block_latest = 0
        self.block_earliest = DEFAULT_MAXIMUM_BP
        self.path_max_bp = DEFAULT_MAXIMUM_BP

    def encode_path(self, latest_bp, earliest_bp, new_path=''):
        bp_list = [latest_bp, earliest_bp]
        bp_list.sort()
        latest_bp = bp_list[0]
        earliest_bp = bp_list[1]
        level_interval = self.decode_path(new_path)
        if(level_interval > self.MIN_INTERVAL_SPAN):
            half_interval = level_iterval / 2
            if(earlist_bp > self.path_max_bp):
                # out of bound date, too early
                return False
            if(latest_bp < (self.block_latest + half_interval)):
                n_path = '0'
                if(earliest_bp >= (self.block_earliest - half_interval)):
                    n_path = '1'
            else:
                n_path = '2'
                if(earliest_bp >= (self.block_earliest - half_interval)):
                    n_path = '3'
            new_path += n_path
            if(self.raw_path_depth(new_path) < self.MAX_TILE_DEPTH):
                new_path = self.encode_path(latest_bp, earliest_bp, new_path)
        return new_path

    def decode_path(self, raw_path):
        """
        decodes a path to return start and end dates
        """
        if(self.PREFIX_DELIM in raw_path):
            path_ex = raw_path.split(self.PREFIX_DELIM)
            prefix = path_ex[0]
            self.get_prefix_maximum(prefix)
            path = path_ex[1]
        else:
            path = raw_path
        if(len(path) < 1):
            # the path is empty, return the maximum BP value
            return self.path_max_bp
        else:
            t_path = re.sub('[^0-3]', '', path)
            if(t_path != path):
                # path contains invalid characters, return False
                return False
            else:
                return self.get_path_interval(path)
    
    def get_path_interval(self, path):
        """
        converts a path to a time interval
        """
        path_depth = len(path)
        self.block_latest = 0
        self.block_eariest = self.path_max_bp
        level_interval = self.path_max_bp
        i = 0
        while(i < path_depth):
            level_interval = level_interval / 2
            act_path_square = path[i]
            if(act_path_square == '0'):
                self.block_eariest -= level_interval
            elif(act_path_square == '1'):
                # nothing happens
            
            elif(act_path_square == '2'):
                self.block_latest += level_interval
                self.block_earliest -= level_interval
            elif(act_path_square == '3'):
                self.block_latest += level_interval
            else:
                # wildy wrong character
                return False
            i += 1
        return level_interval

    def get_prefix_maximum(self, prefix):
        """
        gets the maximum BP from a path prefix
        """
        exp_dict = {'k': 3,
                    'm': 6,
                    'g': 9}
        exp_char = prefix[-1:]
        if(exp_char is not None):
            exp_char = exp_char.lower()
        numeric_prefix = self.number_cast(prefix)
        print(str(exp_char) + " " + str(numeric_prefix))
        if(isinstance(numeric_prefix, (int, float, numbers.Number))):
            # print('\n oh yeah \n')
            if(exp_char in exp_dict):
                self.path_max_bp = numeric_prefix * pow(10, exp_dict[exp_char])
            else:
                self.path_max_bp = numeric_prefix
        return self.path_max_bp
    
    def raw_path_depth(self, raw_path):
        """
        gets the depth of a raw_path string
        """
        if(self.PREFIX_DELIM in raw_path):
            path_ex = raw_path.split(self.PREFIX_DELIM)
            prefix = path_ex[0]
            self.get_prefix_maximum(prefix)
            return len(path_ex[1])
        else:
            return len(raw_path)
    
    def number_cast(self, test_string):
        """
        Spits out a number from a string if numeric characters returned
        """
        t_number = re.sub('[^0-9.]', '', test_string)
        if(t_number is not None):
            try:
                return int(t_number)
            except ValueError:
                return float(t_number)
        else:
            return None
