import re
import os
import json
import codecs
import requests
from lxml import etree
import lxml.html
from unidecode import unidecode
from django.conf import settings
from django.db import connection
from django.db.models import Q
from django.db.models import Avg, Max, Min
from time import sleep
from django.utils.http import urlquote, quote_plus, urlquote_plus
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.libs.generalapi import GeneralAPI
from opencontext_py.apps.ldata.linkannotations.models import LinkAnnotation as LinkAnnotation
from opencontext_py.apps.ldata.linkentities.models import LinkEntity as LinkEntity
from opencontext_py.apps.ocitems.assertions.models import Assertion
from opencontext_py.apps.ocitems.manifest.models import Manifest as Manifest
from opencontext_py.apps.ocitems.subjects.models import Subject
from opencontext_py.apps.ocitems.mediafiles.models import Mediafile as Mediafile
from opencontext_py.apps.ocitems.persons.models import Person as Person
from opencontext_py.apps.ocitems.projects.models import Project as Project
from opencontext_py.apps.ocitems.documents.models import OCdocument as OCdocument
from opencontext_py.apps.ocitems.strings.models import OCstring as OCstring
from opencontext_py.apps.ocitems.octypes.models import OCtype as OCtype
from opencontext_py.apps.ocitems.predicates.models import Predicate as Predicate
from opencontext_py.apps.ocitems.projects.models import Project as Project
from opencontext_py.apps.ocitems.geospace.models import Geospace
from opencontext_py.apps.ocitems.events.models import Event
from opencontext_py.apps.ocitems.identifiers.models import StableIdentifer
from opencontext_py.apps.ocitems.obsmetadata.models import ObsMetadata
from opencontext_py.apps.imports.poggiociv.models import PoggioCiv


class PoggioCivLinking():
    """ Class for getting data from the legacy Poggio Civitate server

from opencontext_py.apps.imports.poggiociv.linking import PoggioCivLinking
pcl = PoggioCivLinking()

    """

    def __init__(self):
        self.act_import_dir = False
        self.pc = PoggioCiv() 
        self.pc_directory = 'mag-data'
        self.trench_book_index_json = 'trench-books-index.json'
        self.root_index = []
    
    def load_root_index(self):
        """ loads the trench book index, scrapes
            content recursively
        """
        items = self.pc.load_json_file_os_obj(pc.pc_directory
                                              self.pc.trench_book_index_json)
        if isinstance(items, list):
            self.root_index = items
    
    def process_root_items(self):
        """ iterate through root items """
        for item in self.root_index:
            # make a link so as to get the first item's filename
            link = item['page']
            param_sep = '?'
            param_keys = []
            for param_key, param_val in item['params'].items():
                param_keys.append(param_key)
            param_keys.sort()
            for param_key in param_keys:
                param_val = item['params'][param_key]
                link += param_sep + str(param_key) + '=' + str(param_val)
                param_sep = '&'
            filename = self.pc.compose_filename_from_link(link)
   