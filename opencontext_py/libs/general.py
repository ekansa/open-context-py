#!/usr/bin/env python
from collections import OrderedDict


class LastUpdatedOrderedDict(OrderedDict):
    """
    Stores items in the order the keys were last added
    """
    def __setitem__(self, key, value):
        if key in self:
            del self[key]
        OrderedDict.__setitem__(self, key, value)