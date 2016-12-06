import os
import codecs
import uuid as GenUUID
import re
import datetime
import json
import html
from dateutil.parser import parse
from lxml import etree
from django.db import models
from django.conf import settings
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.ocitems.geospace.models import Geospace
from opencontext_py.apps.ocitems.events.models import Event
from opencontext_py.apps.imports.fields.datatypeclass import DescriptionDataType
from opencontext_py.apps.imports.faims.files import FileManage


class AttributesImport():
    """ Loads attributes.xml files for import

from opencontext_py.apps.imports.faims.attributes import AttributesImport
faims_attribs = AttributesImport()
faims_attribs.gen_config('faims-survey')


    """

    def __init__(self):
        self.tree = None
        self.project_uuid = False
        self.source_id = False
        self.attributes = None
        self.oc_config_attributes = 'oc-attributes'
        self.oc_config_types = 'oc-types'
        self.fm = FileManage()

    def gen_config(self, act_dir, filename='attributes.xml'):
        """ processes the attributes XML file """
        self.tree = self.fm.load_xml_file(act_dir, filename)
        if self.tree is not False:
            ok = self.load_or_classify_attributes(act_dir)

    def load_or_classify_attributes(self, act_dir):
        """ loads or classifies attributes in a tree """
        ok = False
        key = self.oc_config_attributes
        self.attributes = self.fm.get_dict_from_file(key, act_dir)
        if self.attributes is None:
            print('Need to 1st generate an attributes file from the ArchEnts!')
            ok = False
        else:
            # we have JSON with dictionary for the attributes
            ok = True
            self.classify_xml_tree_attributes()
            self.fm.save_serialized_json(key,
                                         act_dir,
                                         self.attributes)
        return ok

    def classify_xml_tree_attributes(self):
        """ classifies attributes in a tree """
        if self.tree is not False and self.attributes is not None:
            attribs = self.tree.xpath('/attributes/attribute')
            for attrib in attribs:
                prop_name = attrib.xpath('AttributeName')[0].text
                prop_id = attrib.xpath('AttributeID')[0].text
                if prop_id in self.attributes:
                    cont_vocabs = attrib.xpath('controlledVocabs/vocabulary')
                    if len(cont_vocabs) > 0:
                        self.attributes[prop_id]['data_type'] = 'id'
                        self.attributes[prop_id]['vocabs_count'] = len(cont_vocabs)
                        oc_types = self.classify_xml_attributes_to_types(cont_vocabs)
                        self.attributes[prop_id]['oc_types'] = oc_types
    
    def classify_xml_attributes_to_types(self, cont_vocabs, predicate_uuid=None):
        """ classifies open context types used with each attribute """
        oc_types = LastUpdatedOrderedDict()
        for vocab in cont_vocabs:
            vocab_id = vocab.xpath('VocabID')[0].text
            oc_type = LastUpdatedOrderedDict()
            oc_type['id'] = vocab_id
            oc_type['label'] = vocab.xpath('Arch16n')[0].text
            oc_type['uuid'] = None
            oc_type['predicate_uuid'] = predicate_uuid
            oc_type['faims_attrib_id'] = vocab.xpath('AttributeID')[0].text
            oc_type['faims_internal_str'] = vocab.xpath('VocabName')[0].text
            sort_str = vocab.xpath('VocabCountOrder')[0].text
            try:
                oc_type['sort'] = float(sort_str)
            except:
                oc_type['sort'] = 0
            oc_type['note'] = None
            notes = vocab.xpath('VocabDescription')
            for act_note_node in notes:
                act_note = act_note_node.text
                if '&lt;' in act_note and '&gt;' in act_note:
                    # has escaped HTML, unescape it
                    oc_type['note'] = act_note.unescape(act_note)
                else:
                    oc_type['note'] = act_note
            oc_types[vocab_id] = oc_type
        return oc_types
            