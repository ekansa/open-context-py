import os
from io import StringIO, BytesIO
from os import listdir
from os.path import isfile, join
from lxml import etree
import requests
from time import sleep
import datetime
from dateutil.parser import parse
from collections import OrderedDict
from django.db import models
from django.conf import settings
from django.db.models import Avg, Max, Min
from opencontext_py.apps.ldata.linkannotations.models import LinkAnnotation as LinkAnnotation
from opencontext_py.apps.ldata.linkentities.models import LinkEntity as LinkEntity
from opencontext_py.apps.ocitems.manifest.models import Manifest as Manifest
from opencontext_py.apps.ocitems.mediafiles.models import Mediafile as Mediafile
from opencontext_py.apps.ocitems.persons.models import Person as Person
from opencontext_py.apps.ocitems.projects.models import Project as Project
from opencontext_py.apps.ocitems.documents.models import OCdocument as OCdocument
from opencontext_py.apps.ocitems.strings.models import OCstring as OCstring
from opencontext_py.apps.ocitems.strings.manage import StringManagement
from opencontext_py.apps.ocitems.octypes.models import OCtype as OCtype
from opencontext_py.apps.ocitems.octypes.manage import TypeManagement
from opencontext_py.apps.ocitems.predicates.models import Predicate as Predicate
from opencontext_py.apps.ocitems.projects.models import Project as Project
from opencontext_py.apps.ocitems.geospace.models import Geospace
from opencontext_py.apps.ocitems.events.models import Event
from opencontext_py.apps.ocitems.identifiers.models import StableIdentifer
from opencontext_py.apps.ocitems.obsmetadata.models import ObsMetadata
from opencontext_py.apps.ocitems.assertions.models import Assertion


# This imports some data from the old Open Context XML
class OldXML():
    """
    Imports old Open Context XML to the new Postgres datastore

from opencontext_py.apps.imports.oldxml.migrate import OldXML
oldxml = OldXML()
oldxml.load_data_from_xml_files('mentese')
oldxml.add_properties_from_xml_file('mentese', '00AA33E0-E4FD-414E-E889-CFC21B73C7A8.xml')
    """

    NAMESPACES = {'arch': 'http://ochre.lib.uchicago.edu/schema/SpatialUnit/SpatialUnit.xsd',
                  'oc': 'http://opencontext.org/schema/space_schema_v1.xsd',
                  'xhtml': 'http://www.w3.org/1999/xhtml'}

    PRED_TYPE_MAPPINGS = {
        'nominal': 'id',
        'decimal': 'xsd:double',
        'integer': 'xsd:integer',
        'boolean': 'xsd:boolean',
        'calendric': 'xsd:date',
        'calendar': 'xsd:date',
        'calender': 'xsd:date'
    }

    def __init__(self):
        self.root_import_dir = settings.STATIC_IMPORTS_ROOT
        self.table_id_list = []
        self.table_dir = 'oc-tabs'  # CSV files from more recent open context downloads
        self.abs_path = 'C:\\GitHub\\open-context-py\\static\\imports\\'
        self.predicates = []
        self.types = []
        self.item_uuid = False
        self.item_man = False
        self.project_uuid = False
        self.source_id = 'ArchaeoML (XML)'

    def load_data_from_xml_files(self, act_dir):
        """ loads data from the entire directory ! """
        files = self.get_xml_file_list(act_dir)
        i = 0
        num_files = len(files)
        for filename in files:
            i += 1
            print('Working (' + str(i) + ' of ' + str(num_files) + '): ' + filename)
            self.add_properties_from_xml_file(act_dir, filename)

    def add_properties_from_xml_file(self, act_dir, filename):
        """ gets properties from an xml file """
        tree = self.parse_xml_file(act_dir, filename)
        if tree is not False:
            self.get_item_info(tree)
            try:
                man = Manifest.objects.get(uuid=self.item_uuid)
            except Manifest.DoesNotExist:
                man = False
                print('ACK cannot find: ' + self.item_uuid)
            if man is not False:
                self.item_man = man
                r_obs = self.get_observations_from_tree(tree)
                if len(r_obs) > 0:
                    for obs_tree in r_obs:
                        r_obs_num = obs_tree.xpath('@obsNumber',
                                                   namespaces=self.NAMESPACES)
                        if len(r_obs_num) > 0:
                            obs_num = int(float(r_obs_num[0]))
                        else:
                            obs_num = 1
                        self.add_properties_from_obs(obs_tree, obs_num)
        self.item_uuid = False
        self.item_man = False

    def get_item_info(self, tree):
        """ gets basic item info """
        r_uuid = tree.xpath('@UUID',
                            namespaces=self.NAMESPACES)
        self.item_uuid = str(r_uuid[0])
        r_project_uuid = tree.xpath('@ownedBy',
                                    namespaces=self.NAMESPACES)
        self.project_uuid = str(r_project_uuid[0])

    def get_observations_from_tree(self, tree):
        """ gets observations from a tree """
        r_obs = tree.xpath('//arch:observations/arch:observation',
                           namespaces=self.NAMESPACES)
        return r_obs

    def add_properties_from_obs(self, obs_tree, obs_num=1):
        """ gets a list of variables, values, and properties from
            an XML file
        """
        assert_sort = (obs_num * 10) - 1
        props = []
        r = obs_tree.xpath('//arch:properties/arch:property',
                           namespaces=self.NAMESPACES)
        for prop_xml in r:
            assert_sort += 1
            r_var_id = prop_xml.xpath('arch:variableID',
                                      namespaces=self.NAMESPACES)
            predicate_uuid = r_var_id[0].text
            r_var_label = prop_xml.xpath('oc:var_label',
                                         namespaces=self.NAMESPACES)
            predicate_label = r_var_label[0].text
            r_var_type = prop_xml.xpath('oc:var_label/@type',
                                        namespaces=self.NAMESPACES)
            var_type = str(r_var_type[0]).lower()
            if var_type in self.PRED_TYPE_MAPPINGS:
                data_type = self.PRED_TYPE_MAPPINGS[var_type]
            else:
                data_type = 'xsd:string'
            # print(' '.join([predicate_uuid, predicate_label, var_type, data_type]))
            r_val_id = prop_xml.xpath('arch:valueID',
                                      namespaces=self.NAMESPACES)
            if len(r_val_id) > 0:
                string_uuid = r_val_id[0].text
            else:
                string_uuid = None
            val_number = None
            r_val_num = prop_xml.xpath('arch:integer',
                                       namespaces=self.NAMESPACES)
            if len(r_val_num) > 0:
                val_number = r_val_num[0].text
            r_val_num = prop_xml.xpath('arch:decimal',
                                       namespaces=self.NAMESPACES)
            if len(r_val_num) > 0:
                val_number = r_val_num[0].text
            r_prop_id = prop_xml.xpath('oc:propid',
                                       namespaces=self.NAMESPACES)
            if len(r_prop_id) > 0 and data_type == 'id':
                type_uuid = r_prop_id[0].text
                object_type = 'types'
            else:
                type_uuid = None
                object_type = data_type
            r_val_str = prop_xml.xpath('oc:show_val',
                                       namespaces=self.NAMESPACES)
            if len(r_val_str) > 0:
                val_str = r_val_str[0].text
            else:
                val_str = None
            # print(' '.join([str(string_uuid), str(type_uuid), val_str]))
            self.add_predicate(predicate_uuid, predicate_label, data_type)
            if val_str is not None:
                save_ass = False
                new_ass = self.prepare_new_assertion(obs_num, assert_sort)
                new_ass.predicate_uuid = predicate_uuid
                new_ass.object_type = object_type
                if type_uuid is not None \
                   and string_uuid is not None \
                   and object_type == 'types':
                    type_obj = self.add_type(predicate_uuid,
                                             type_uuid,
                                             string_uuid,
                                             val_str)
                    new_ass.object_uuid = type_obj.uuid
                    save_ass = True
                elif string_uuid is not None and object_type == 'xsd:string':
                    str_obj = self.get_make_string_w_suggested_uuid(val_str, string_uuid)
                    new_ass.object_uuid = str_obj.uuid
                    save_ass = True
                elif val_number is not None:
                    new_ass.data_num = float(val_number)
                    save_ass = True
                elif object_type == 'xsd:boolean':
                    new_ass.data_num = self.validate_convert_boolean(val_str)
                    save_ass = True
                elif object_type == 'xsd:date':
                    try:
                        date_obj = parse(val_str)
                        new_ass.data_date = date_obj
                        save_ass = True
                    except:
                        new_ass.data_date = None
                if save_ass:
                    try:
                        new_ass.save()
                    except:
                        print('Problem saving: ' + predicate_label + ' for ' + self.item_uuid)
        r = obs_tree.xpath('//arch:notes/arch:note/arch:string/xhtml:div',
                           namespaces=self.NAMESPACES)
        for note_xml in r:
            assert_sort += 1
            note = etree.tostring(note_xml,
                                  xml_declaration=False,
                                  pretty_print=True,
                                  encoding='utf-8')
            note = str(note)
            note = self.remove_attributes_in_first_tag(note, '<div>')
            note = note.replace('\\n', '')
            new_ass = self.prepare_new_assertion(obs_num, assert_sort)
            new_ass.predicate_uuid = Assertion.PREDICATES_NOTE
            new_ass.object_type = 'xsd:string'
            str_obj = self.get_make_string_w_suggested_uuid(note, False)
            new_ass.object_uuid = str_obj.uuid
            try:
                new_ass.save()
            except:
                print('Already saved this note for ' + self.item_uuid)

    def prepare_new_assertion(self, obs_num, assert_sort):
        """ sets up a new assertion object """
        new_ass = Assertion()
        new_ass.uuid = self.item_man.uuid
        new_ass.subject_type = self.item_man.item_type
        new_ass.project_uuid = self.project_uuid
        new_ass.source_id = self.source_id
        new_ass.obs_node = '#obs-' + str(obs_num)
        new_ass.obs_num = obs_num
        new_ass.sort = assert_sort
        new_ass.visibility = 1
        new_ass.certainty = 0
        return new_ass

    def add_predicate(self, predicate_uuid, label, data_type):
        """ adds the predicate """
        if predicate_uuid not in self.predicates:
            self.predicates.append(predicate_uuid)
            pred_exists = self.check_manifest_exists(predicate_uuid)
            if pred_exists is False:
                print('New predicate: ' + label + ' ' + predicate_uuid)
                preds = Predicate.objects\
                                 .filter(project_uuid=self.project_uuid)
                sort = len(preds) + 1
                man = Manifest()
                man.uuid = predicate_uuid
                man.label = label
                man.project_uuid = self.project_uuid
                man.source_id = self.source_id
                man.item_type = 'predicates'
                man.class_uri = 'variable'
                man.save()
                pred = Predicate()
                pred.uuid = predicate_uuid
                pred.project_uuid = self.project_uuid
                pred.source_id = self.source_id
                pred.data_type = data_type
                pred.sort = sort
                pred.save()

    def add_type(self, predicate_uuid, type_uuid, string_uuid, label):
        """ adds the predicate """
        tm = TypeManagement()
        tm.source_id = self.source_id
        tm.project_uuid = self.project_uuid
        tm.suggested_uuid = type_uuid
        tm.suggested_content_uuid = string_uuid
        type_obj = tm.get_make_type_within_pred_uuid(predicate_uuid, label)
        return type_obj

    def check_manifest_exists(self, uuid):
        """ checks to see if a manifest item exists """
        output = False
        try:
            man_exists = Manifest.objects.get(uuid=uuid)
            output = True
        except Manifest.DoesNotExist:
            man_exists = False
            output = False
        return output

    def get_make_string_w_suggested_uuid(self, content, string_uuid=False):
        """ makes a string with a suggested uuid if it does not exist """
        str_man = StringManagement()
        str_man.project_uuid = self.project_uuid
        str_man.source_id = self.source_id
        str_man.suggested_uuid = string_uuid
        str_obj = str_man.get_make_string(content)
        return str_obj

    def remove_attributes_in_first_tag(self, xml_string, tag):
        """ removes attributes in the first tag of an xml string
            useful for cleaning namespaces in XML. this is a hack.
        """
        add_to_new = False
        new_string = ''
        for i, char in enumerate(xml_string):
            if add_to_new:
                new_string += char
            else:
                if char == '>':
                    add_to_new = True
        return tag + new_string

    def validate_convert_boolean(self, record):
        """ Validates boolean values for a record
            returns a boolean 0 or 1 if
        """
        output = None
        record = record.lower()
        booleans = {'n': 0,
                    'no': 0,
                    'none': 0,
                    'absent': 0,
                    'a': 0,
                    'false': 0,
                    'f': 0,
                    '0': 0,
                    '0.0': 0,
                    'y': 1,
                    'yes': 1,
                    'present': 1,
                    'true': 1,
                    'p': 1,
                    't': 1,
                    '1': 1,
                    '1.0': 1}
        if record in booleans:
            output = booleans[record]
        return output

    def parse_xml_file(self, act_dir, filename):
        """ parses an xml file """
        tree = False
        dir_file = self.set_check_directory(act_dir) + filename
        if os.path.exists(dir_file):
            tree = etree.parse(dir_file)
        return tree

    def get_xml_file_list(self, act_dir):
        """ gets a list of XML files from the act_dir """
        files = []
        directory = self.set_check_directory(act_dir)
        for filename in os.listdir(directory):
            if filename.endswith('.xml'):
                files.append(filename)
        return files

    def set_check_directory(self, act_dir):
        """ Prepares a directory to find import files """
        output = False
        full_dir = self.root_import_dir + act_dir + '/'
        if os.path.exists(full_dir):
            output = full_dir
        if output is False:
            output = self.abs_path + act_dir + '\\'
        return output