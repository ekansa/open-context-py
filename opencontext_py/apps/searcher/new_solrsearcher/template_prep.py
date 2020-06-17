import copy
import json
import logging
import re
import time
from datetime import datetime

from django.utils.html import strip_tags

from django.conf import settings

from opencontext_py.libs.rootpath import RootPath
from opencontext_py.libs.general import LastUpdatedOrderedDict



class SearchTemplate():
    """ methods use Open Context JSON-LD
        search results and turn them into a
        user interface
    """

    def __init__(self, result):
        self.result = None
        if isinstance(result, dict):
            self.result = result
    
