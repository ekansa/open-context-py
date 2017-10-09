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
from opencontext_py.apps.edit.items.itembasic import ItemBasicEdit
from opencontext_py.apps.imports.poggiociv.models import PoggioCiv
from opencontext_py.apps.imports.records.models import ImportCell


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
pcl.update_existing_trench_book_links()


    """

    def __init__(self):
        self.act_import_dir = False
        self.source_id = 'tb-scrape'
        self.pc = PoggioCiv() 
        self.pc_directory = 'mag-data'
        self.trench_book_index_json = 'trench-books-index.json'
        self.unlinked_trench_books = 'unlinked-trench-books.json'
        self.root_index = []
        self.project_uuid = 'DF043419-F23B-41DA-7E4D-EE52AF22F92F'
        self.part_of_pred_uuid = '0BB889F9-54DD-4F70-5B63-F5D82425F0DB'
    
    def load_root_index(self, reset_tb_uuids=False):
        """ loads the trench book index, scrapes
            content recursively
        """
        if len(self.root_index) < 1:
            items = self.pc.load_json_file_os_obj(self.pc.pc_directory,
                                                  self.pc.trench_book_index_json)
            if isinstance(items, list):
                save_change = False
                new_items = []
                for item in items:
                    if 'trench_book_uuid' not in item or reset_tb_uuids:
                        item['trench_book_uuid'] = None
                        item['parent_tb_verified'] = None
                        save_change = True
                    if len(item['trenches']) > 0:
                        new_trenches = []
                        for tr_item in item['trenches']:
                            if 'trench_uuid' not in tr_item:
                                tr_item['trench_uuid'] = None
                                save_change = True
                            if 'unit_year_uuid' not in tr_item:
                                tr_item['unit_year_uuid'] = None
                                save_change = True
                            new_trenches.append(tr_item)
                        item['trenches'] = new_trenches
                    new_items.append(item)
                if save_change:
                    self.pc.save_as_json_file(self.pc.pc_directory,
                                              self.pc.trench_book_index_json,
                                              new_items)
                self.root_index = new_items
    
    def update_existing_trench_book_links(self):
        """ iterate through root items """
        save_change = False
        self.load_root_index()
        new_items = []
        unlinked_items = []
        for item in self.root_index:
            tb_man = None
            tb_label = item['label']
            if item['trench_book_uuid'] is None:
                tb_man_objs = Manifest.objects\
                                      .filter(label=tb_label,
                                              project_uuid=self.project_uuid,
                                              item_type='documents')
                if len(tb_man_objs) == 1:
                    # only 1 match, so easy
                    tb_man = tb_man_objs[0]
                    item['trench_book_uuid'] = tb_man.uuid
                    item['parent_tb_verified'] = 'Single'
                    save_change = True
                elif len(tb_man_objs) > 1:
                    # need to find the version that is the root document
                    for tb_man_test in tb_man_objs:
                        root_asserts = Assertion.objects\
                                                .filter(uuid=tb_man_test.uuid,
                                                        predicate_uuid=self.part_of_pred_uuid,
                                                        object_type='documents')[:1]
                        if len(root_asserts) < 1:
                            # the item is not part of another document
                            tb_man = tb_man_test
                            item['trench_book_uuid'] = tb_man.uuid
                            item['parent_tb_verified'] = 'Mutiple'
                            save_change = True
                else:
                    tb_man = None
            else:
                try:
                    tb_man = Manifest.objects.get(uuid=item['trench_book_uuid'])
                except:
                    tb_man = None
            if tb_man is not None:
                if len(item['trenches']) > 0:
                    new_trenches = []
                    for tr_item in item['trenches']:
                        if tr_item['trench_uuid'] is None:
                            # we need to find the correct trench uuid
                            man_trenches = Manifest.objects\
                                                   .filter(project_uuid=self.project_uuid,
                                                           class_uri='oc-gen:cat-trench',
                                                           label=tr_item['label'])[:1]
                            if len(man_trenches) > 0:
                                # we matched the trench to the appropriate trench already in Open Context
                                tr_item['trench_uuid'] = man_trenches[0].uuid
                                save_change = True
                        new_trenches.append(tr_item)
                    if save_change:
                        item['trenches'] = new_trenches
                    new_trenches = []
                    for tr_item in item['trenches']:
                        if tr_item['trench_uuid'] is not None:
                            if tr_item['unit_year_uuid'] is None:
                                unit_man_obj = self.get_unit_man_obj_by_trench_uuid_year(tr_item['trench_uuid'],
                                                                                         tr_item['year'])
                                if unit_man_obj is not None:
                                    tr_item['unit_year_uuid'] = unit_man_obj.uuid
                                    tr_item['unit_label'] = unit_man_obj.label
                                    save_change = True
                        new_trenches.append(tr_item)
                    if save_change:
                        item['trenches'] = new_trenches
                    unit_uuids = []
                    for tr_item in item['trenches']:
                        if tr_item['unit_year_uuid'] is not None:
                            if tr_item['unit_year_uuid'] not in unit_uuids:
                                unit_uuids.append(tr_item['unit_year_uuid'])
                    if len(unit_uuids) > 0:
                        """
                        self.change_diary_unit_links(tb_man.uuid,
                                                     unit_uuids)
                        """
                    else:
                        # we have an unlinked item!
                        unlinked_items.append(item)
            new_items.append(item)  # so we can save updates to the JSON
        if save_change:
            self.pc.save_as_json_file(self.pc.pc_directory,
                                      self.pc.trench_book_index_json,
                                      new_items)
        if len(unlinked_items) > 0:
            self.pc.save_as_json_file(self.pc.pc_directory,
                                      self.unlinked_trench_books,
                                      unlinked_items)
    
    def change_diary_unit_links(self, root_trench_book_uuid, unit_uuids):
        """ changes the associations between a diary and excavation units """
        # first, get lists of documents and media items related to this root_trench_book
        rel_objects = {
            'media': [],
            'documents': []
        }
        rel_s_assertions = Assertion.objects\
                                    .filter(uuid=root_trench_book_uuid,
                                            object_type__in=['media', 'documents'])
        for rel_assert in rel_s_assertions:
            object_type = rel_assert.object_type
            if rel_assert.object_uuid not in rel_objects[object_type]:
                if rel_assert.object_uuid != root_trench_book_uuid:
                    rel_objects[object_type].append(rel_assert.object_uuid)
        rel_o_assertions = Assertion.objects\
                                    .filter(object_uuid=root_trench_book_uuid,
                                            subject_type__in=['media', 'documents'])
        for rel_assert in rel_o_assertions:
            subject_type = rel_assert.subject_type
            if rel_assert.uuid not in rel_objects[subject_type]:
                if rel_assert.uuid != root_trench_book_uuid:
                    rel_objects[subject_type].append(rel_assert.uuid)
        # start making updates to change existing links to subjects
        # to the new links
        self.fix_bad_related_unit_links(unit_uuids,
                                        [root_trench_book_uuid])
        # now change links for related documents and media resources
        # so they link to the correct main_uuid_uuid
        for item_type, rel_uuids in rel_objects.items():
            self.fix_bad_related_unit_links(unit_uuids,
                                            rel_uuids)
        # now make sure we have new links added
        self.add_related_unit_links(root_trench_book_uuid,
                                    unit_uuids,
                                    rel_objects)
            
        
    def fix_bad_related_unit_links(self, unit_uuids, media_doc_uuids):
        """ updates links to item_type subjects to the main_unit_uuid
            if the current link to item_type subjects is not in the list
            of desired unit_uuids
        """
        unit_s_asserts = Assertion.objects\
                                      .filter(subject_type='subjects',
                                              object_uuid__in=media_doc_uuids)
        for unit_assert in unit_s_asserts:
            if unit_assert.uuid not in unit_uuids:
                # since we've got an invalid link change it to the correct one
                unit_assert.uuid = unit_uuids[0]
                unit_assert.save()
        unit_o_asserts = Assertion.objects\
                                  .filter(object_type='subjects',
                                          uuid__in=media_doc_uuids)
        for unit_assert in unit_o_asserts:
            if unit_assert.object_uuid not in unit_uuids:
                # since we've got an invalid link change it to the correct one
                unit_assert.object_uuid = unit_uuids[0]
                unit_assert.save()
        
    def add_related_unit_links(self,
                               root_trench_book_uuid,
                               unit_uuids,
                               rel_objects):
        """ adds links to desired unit_uuids if they do not
            yet exist
        """
        new_asserts = 0
        if len(unit_uuids) > 1:
            do_reciprocal = True
        else:
            do_reciprocal = False
        i = -1
        for unit_uuid in unit_uuids:
            # first check to see if the root_trench_book_uuid
            # already links to the unit_uuid, if not, add the link
            i += 1
            ex_asserts = Assertion.objects\
                                  .filter(uuid=unit_uuid,
                                          object_uuid=root_trench_book_uuid)[:1]
            if len(ex_asserts) < 1:
                # since this is the root trench book, make the subject
                # of the assertion the excavation unit
                new_ass = Assertion()
                new_ass.uuid = unit_uuid
                new_ass.subject_type = 'subjects'
                new_ass.project_uuid = self.project_uuid
                new_ass.source_id = self.source_id
                new_ass.obs_node = '#obs-1'
                new_ass.obs_num = 1
                new_ass.sort = 100 + (i/1000)
                new_ass.visibility = 1
                new_ass.predicate_uuid = 'oc-3'
                new_ass.object_type = 'documents'
                new_ass.object_uuid = root_trench_book_uuid
                new_ass.save()
                new_asserts += 1
            if do_reciprocal:
                ex_asserts = Assertion.objects\
                                      .filter(uuid=root_trench_book_uuid,
                                              object_uuid=unit_uuid)[:1]
                if len(ex_asserts) < 1:
                    # since this is the root trench book, make the subject
                    # of the assertion the excavation unit
                    new_ass = Assertion()
                    new_ass.uuid = root_trench_book_uuid
                    new_ass.subject_type = 'documents'
                    new_ass.project_uuid = self.project_uuid
                    new_ass.source_id = 'reciprocal-' + self.source_id
                    new_ass.obs_node = '#obs-1'
                    new_ass.obs_num = 1
                    new_ass.sort = 100 + (i/1000)
                    new_ass.visibility = 1
                    new_ass.predicate_uuid = 'oc-3'
                    new_ass.object_type = 'subjects'
                    new_ass.object_uuid = unit_uuid
                    new_ass.save()
                    new_asserts += 1
            # now go through and make sure we have links for the other
            # related media and documents
            for item_type, rel_uuids in rel_objects.items(): 
                for rel_uuid in rel_uuids:
                    ex_asserts = Assertion.objects\
                                          .filter(uuid=rel_uuid,
                                                  object_uuid=unit_uuid)[:1]
                    if len(ex_asserts) < 1 and rel_uuid != root_trench_book_uuid:
                        # since this is a related trench book page or media item
                        # make the OBJECT of the assertion the excavation unit
                        new_ass = Assertion()
                        new_ass.uuid = rel_uuid
                        new_ass.subject_type = item_type
                        new_ass.project_uuid = self.project_uuid
                        new_ass.source_id = 'inferred-' + self.source_id
                        new_ass.obs_node = '#obs-1'
                        new_ass.obs_num = 1
                        new_ass.sort = 100 + (i/1000)
                        new_ass.visibility = 1
                        new_ass.predicate_uuid = 'oc-3'
                        new_ass.object_type = 'subjects'
                        new_ass.object_uuid = unit_uuid
                        new_ass.save()
                        new_asserts += 1
        return new_asserts                
    
    def get_unit_man_obj_by_trench_uuid_year(self, trench_uuid, unit_year):
        """ get the trench unit manifest object by the appropriate year """
        unit_man_obj = None
        tr_contain_asserts = Assertion.objects\
                                      .filter(uuid=trench_uuid,
                                              predicate_uuid=Assertion.PREDICATES_CONTAINS)
        for tr_assert in tr_contain_asserts:
            man_objs = Manifest.objects\
                               .filter(uuid=tr_assert.object_uuid,
                                       class_uri='oc-gen:cat-exc-unit')[:1]
            if len(man_objs) > 0:
                # ok, it's an excavation unit, but does it have the right year?
                man_obj = man_objs[0]
                year_asserts = Assertion.objects\
                                        .filter(uuid=man_obj.uuid,
                                                predicate_uuid='2C7FE888-C431-4FBD-39F4-38B7D969A811',
                                                data_num=unit_year)[:1]
                if len(year_asserts) > 0:
                    # OK! the excavation unit has the correct year!!
                     unit_man_obj = man_obj
        return unit_man_obj
    
    def update_trench_labels(self):
        """ updates trench labels to make them more readable, consistent """
        rep_dict = {
            'Agger': 'Agger ',
            'Civitate A': 'Civitate A ',
            'Civitate B': 'Civitate B ',
            'Civitate C': 'Civitate C ',
            'Civitate D': 'Civitate D ',
            'North Terrace': 'North Terrace ',
            'Tesoro': 'Tesoro ',
            'Tesoro North Flank': 'Tesoro North Flank ',
            'Tesoro Rectangle': 'Tesoro Rectangle ',
            'Tesoro South Flank': 'Tesoro South Flank ',
            
        }
        for bad_prefix, fix_prefix in rep_dict.items():
            man_items = Manifest.objects\
                                .filter(project_uuid=self.project_uuid,
                                        class_uri='oc-gen:cat-trench',
                                        label__startswith=bad_prefix)\
                                .exclude(label__startswith=fix_prefix)
            for man_obj in man_items:
                new_label = man_obj.label.replace(bad_prefix, fix_prefix)
                new_label = new_label.replace('/', ',')
                new_label = new_label.replace('  ', ' ')
                print('Old: ' + man_obj.label + ', new: ' + new_label)
                ibe = ItemBasicEdit(False, False)
                ibe.manifest = man_obj
                ibe.edit_permitted = True
                ibe.update_label(new_label, {})
                