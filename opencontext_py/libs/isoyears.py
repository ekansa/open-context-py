#!/usr/bin/env python
import re
import numbers


class ISOyears():
    """
    GeoJSON-LD expects dates expressed as ISO 8601 strings
    
    This class has methods to convert back and forth between these
    strings and numeric dates

    """

    def __init__(self):
        self.zero_year_convert = True  # convert the year '0000' to 1 BCE

    def make_iso_from_float(self, float_year):
        """ makes an ISO 8601 year from a float year """
        if float_year > 0:
            iso_year = str(int(float_year))
            iso_year = self.prepend_zeros(iso_year)
        elif float_year == 0:
            iso_year = '0001'
        elif float_year == -1:
            iso_year = '0000'
        else:
            bce_year = abs(float_year) - 1
            iso_year = str(int(bce_year))
            # make sure it's at least 4 digits long
            iso_year = self.prepend_zeros(iso_year)
            iso_year = '-' + iso_year
        return iso_year

    def make_float_from_iso(self, iso_year):
        """ makes a float year from an ISO year"""
        if '-' in iso_year:
            # we've got a time BCE
            float_year = float(iso_year) - 1
        elif iso_year == '0000' or \
             iso_year == '+0000':
            float_year = -1; # 1 BCE
        else:
            float_year = float(iso_year)
        return float_year
    
    def bce_ce_suffix(self, float_year):
        """ Adds a BCE / CE suffix to a float year """
        if float_year < 1:
            output = str(abs(float_year)) + ' BCE'
        else:
            output = str(float_year) + ' CE'
        return output
    
    def prepend_zeros(self, date_string, total_len=4):
        """ prepends zeros for a site
            with a total digit length
        """
        while(len(date_string) < total_len):
            date_string = '0' + date_string
        return date_string
    
    def test(self):
        """ iterates to check this works,
            the nonsense year 0 BCE? CE?
            is the only exception
        """ 
        ok = True
        year = -10001
        while year < 2015:
            iso = self.make_iso_from_float(year)
            year_out = self.make_float_from_iso(iso)
            if year_out != year \
               and not (year_out == 1 and year == 0):
                ok = False
                error = 'Problem, Year: ' + str(year)
                error += ' ISO: ' + iso
                error += ' Year-again: ' + str(year_out)
                print(error)
            year += 1
        return ok
        
        