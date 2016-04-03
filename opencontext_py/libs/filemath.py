#!/usr/bin/env python
import re
import numbers


class FileMath():
    """
    Methods to make calculations about files

    """

    MEM_MULTIPLE = 1000
    SUFFIXES = {
        1000: ['KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB'],
        1024: ['KiB', 'MiB', 'GiB', 'TiB', 'PiB', 'EiB', 'ZiB', 'YiB']
    }

    def __init__(self):
        self.mem_multiple = self.MEM_MULTIPLE

    def approximate_size(self, size):
        """
        gets the memory size in human readable format
        """
        output = False
        if size < 0:
            raise ValueError('number must be non-negative')
        if self.mem_multiple not in self.SUFFIXES:
            # revert to the default
            self.mem_multiple = self.MEM_MULTIPLE
        for suffix in self.SUFFIXES[self.mem_multiple]:
            size /= self.mem_multiple
            if size < self.mem_multiple:
                output = '{0:.1f} {1}'.format(size, suffix)
                break
        return output
