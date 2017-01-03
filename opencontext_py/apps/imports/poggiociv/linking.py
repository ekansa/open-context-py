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

To do:
- Fix associations between trench books and trenches.
- trench-books-index.json has the links between trench books and trenches.
- What needs to change first is the link between the Tr and the parent trench.
- For example Tr-105 should be in Tesoro 21
- several other trench-book associations are also wrong and need to be
- updated using trench-books-index.json


from opencontext_py.apps.imports.poggiociv.linking import PoggioCivLinking
pcl = PoggioCivLinking()
pcl.update_trench_book_links()


    """

    def __init__(self):
        self.act_import_dir = False
        self.pc = PoggioCiv() 
        self.pc_directory = 'mag-data'
        self.trench_book_index_json = 'trench-books-index.json'
        self.root_index = []
        self.project_uuid = 'DF043419-F23B-41DA-7E4D-EE52AF22F92F'
    
    def load_root_index(self):
        """ loads the trench book index, scrapes
            content recursively
        """
        if len(self.root_index) < 1:
            items = self.pc.load_json_file_os_obj(self.pc.pc_directory,
                                                  self.pc.trench_book_index_json)
            if isinstance(items, list):
                self.root_index = items
    
    def update_trench_book_links(self):
        """ iterate through root items """
        self.load_root_index() 
        for item in self.root_index:
            if 'tbtid' in item:
                tr_id = item['tbtid']
                tr_label = 'Tr-ID ' + str(tr_id)
                man_objs = Manifest.objects\
                                   .filter(label=tr_label,
                                           project_uuid=self.project_uuid,
                                           class_uri='oc-gen:cat-exc-unit')[:1]
                if len(man_objs) > 0:
                    tr_man = man_objs[0]
                    print('Found: ' + tr_man.label + ' ' + tr_man.uuid)
                else:
                    print('------------------------')
                    print('CANNOT FIND: ' + tr_label)
   