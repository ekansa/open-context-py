import re
import os
import json
import codecs
import requests
import time
from lxml import etree
from bs4 import BeautifulSoup
from bs4.element import Tag
import lxml.html
from lxml.html.clean import Cleaner
from unidecode import unidecode
from django.conf import settings
from django.db import connection
from django.db.models import Q
from django.db.models import Avg, Max, Min
from time import sleep
from django.db.models.functions import Length
from opencontext_py.libs.isoyears import ISOyears
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
from opencontext_py.apps.entities.redirects.manage import RedirectURL

class PoggioCivTrenchBookEntries():
    """ Class for getting data from the legacy Poggio Civitate server

To do:
- Fix associations between trench books and trenches.
- trench-books-index.json has the links between trench books and trenches.
- What needs to change first is the link between the Tr and the parent trench.
- For example Tr-105 should be in Tesoro 21
- several other trench-book associations are also wrong and need to be
- updated using trench-books-index.json



from opencontext_py.apps.imports.poggiociv.tbentries import PoggioCivTrenchBookEntries
pctb = PoggioCivTrenchBookEntries()
pctb.make_tb_index()

from opencontext_py.apps.imports.poggiociv.tbentries import PoggioCivTrenchBookEntries
pctb = PoggioCivTrenchBookEntries()
# pctb.move_by_label_part("Trench Book SJG IV", '1BF95233-46FB-4A57-A802-C55200071858')
pctb.merge_old_into_new_docs()
pctb.file_id_limits = ['10667', '11198', '11187', '10528', '7684', '9171', '3757']
pctb.clean_files()


from opencontext_py.apps.imports.poggiociv.tbentries import PoggioCivTrenchBookEntries
pctb = PoggioCivTrenchBookEntries()
pctb.merge_old_and_new_tb_entry("B99D072E-1B10-4283-E0A3-53EEF19261EC", "9a6ddf36-5033-4d41-af24-cc3b25cf368a")

from opencontext_py.apps.imports.poggiociv.tbentries import PoggioCivTrenchBookEntries
pctb = PoggioCivTrenchBookEntries()
# pctb.file_id_limits = ['10667', '11198', '11187', '10528', '7684', '9171']
pctb.clean_files()

from opencontext_py.apps.imports.poggiociv.tbentries import PoggioCivTrenchBookEntries
pctb = PoggioCivTrenchBookEntries()
pctb.clean_bad_html_content()

from opencontext_py.apps.imports.poggiociv.tbentries import PoggioCivTrenchBookEntries
pctb = PoggioCivTrenchBookEntries()
href = "javascript:openViewer('/catalog/trenchbooks/trenchbookviewer.asp?searchpage=25&tbID=6')"
href = pctb.transform_href(href)
print(href)
    """

    def __init__(self):
        self.file_id_limits = []
        self.act_import_dir = False
        self.json_index = None
        self.pc_directory = 'mag-data-html'
        self.old_docs_source_id = 'z_4_e8169555e'
        self.new_docs_source_id = 'ref:1629617122964'
        self.pc = PoggioCiv()
        self.pc.pc_directory = self.pc_directory
        self.tb_files = None
        self.javascript_links = []
        self.tb_id_pred = 'fa50506c-d1f0-4798-84b2-a7a48c0b4c74'
        self.tb_index_uuid = '9755c2a2-3db0-42a2-b07d-4bf8c4447396'
        self.pred_has_part = 'BD384F1F-FB29-4A9D-7ACA-D8F6B4AF0AF9'
        self.pc_photobox_class = 'pc-photobox'
        self.media_id_manifest = {}
        self.media_src = {}
        self.field_keys = [
            'tbtdid',
            'tbtid',
            'file'
        ]
        self.blacklist_tags = [
            'head',
            'script',
            'style'
        ]
        self.ok_attributes = [
            'href',
            'src',
            'id'
        ]
        self.ok_tags = [
            'p',
            'br',
            'div',
            'a',
            'img',
            'span',
            'table',
            'thead',
            'tbody',
            'th',
            'tr',
            'td',
            'strong',
            'ul',
            'ol',
            'li',
            'em',
            'i',
            'u',
            'b',
            'sup',
            'sub',
            'mark',
            'q',
            'samp',
            'small',
        ]
        self.obj_class_uris = [
            'oc-gen:cat-arch-element',
            'oc-gen:cat-object',
            'oc-gen:cat-pottery',
            'oc-gen:cat-glass',
            'oc-gen:cat-coin'
        ]

    def make_tb_index(self):
        """ Generates some HTML for the Trench Book index """
        tb_index = Manifest.objects.get(uuid=self.tb_index_uuid)
        tb_index_doc = OCdocument.objects.get(uuid=self.tb_index_uuid)
        root = etree.Element('div')
        into_p = etree.SubElement(root, 'p')
        into_txt = 'A "trench book" provides a narrative account of '
        into_txt += 'excavations activities and intial (preliminary) interpretations. '
        into_txt += 'Trench book documentation can provide key information about archaeological context. '
        into_txt += 'To facilitate disovery, access, and use, '
        into_txt += 'the project\'s hand-written trench books have been '
        into_txt += 'transcribed and associated with other data.'
        into_p.text = into_txt
        n_p = etree.SubElement(root, 'p')
        n_p.text = 'The following lists transcribed trench books:'
        ul = etree.SubElement(root, 'ul')
        root_tbs = self.get_root_tbs_by_tbid()
        for root_tb in root_tbs:
            sleep(.3)
            print('Get data for: ' + root_tb.label)
            url = 'http://127.0.0.1:8000/documents/' + root_tb.uuid + '.json'
            r = requests.get(url)
            tb_dict = r.json()
            self.update_tb_parts_authors_links(tb_dict)
            trenches = self.get_update_tb_links_from_index(root_tb)
            trenches = self.make_display_trenches(tb_dict, trenches)
            li = etree.SubElement(ul, 'li')
            a_l = etree.SubElement(li, 'a')
            s_l = etree.SubElement(li, 'span')
            ul_l = etree.SubElement(li, 'ul')
            a_l.set('target', '_blank')
            uri = '../../documents/' + root_tb.uuid
            a_l.set('href', uri)
            a_l.text = root_tb.label
            s_l.text = self.make_authors(tb_dict)
            used_uuids = []
            for trench in trenches:
                if trench['unit_year_uuid'] not in used_uuids:
                    used_uuids.append(trench['unit_year_uuid'])
                    li_ul_l = etree.SubElement(ul_l, 'li')
                    a_li_ul_l = etree.SubElement(li_ul_l, 'a')
                    s_li_ul_l = etree.SubElement(li_ul_l, 'span')
                    a_li_ul_l.set('target', '_blank')
                    tr_uri = '../../subjects/' + trench['unit_year_uuid']
                    a_li_ul_l.set('href', tr_uri)
                    a_li_ul_l.text = trench['label']
                    s_li_ul_l.text = ' [' + str(trench['year']).replace('.0', '') + ']'
        tb_index_doc.content = etree.tostring(root)
        tb_index_doc.save()
    
    def update_tb_parts_authors_links(self, tb_dict):
        """ updates the authorship and links associated with the entries (parts)
            of a trench book
        """
        if 'dc-terms:contributor' in tb_dict:
            contribs = tb_dict['dc-terms:contributor']
        prev_part = None
        for obs in tb_dict['oc-gen:has-obs']:
            for part in obs['oc-pred:24-has-part']:
                part_uuid = part['id'].replace('http://opencontext.org/documents/', '')
                part_man = Manifest.objects.get(uuid=part_uuid)
                if len(contribs) > 0:
                    # remove the old principle analyst assertions
                    rm_old = Assertion.objects\
                                      .filter(uuid=part_uuid,
                                              predicate_uuid='oc-28',
                                              object_type='persons')\
                                      .delete()
                    contrib_sort = 0
                    for contrib in contribs:
                        contrib_sort += 1
                        contrib_uuid = contrib['id'].replace('http://opencontext.org/persons/', '')
                        try:
                            new_ass = Assertion()
                            new_ass.uuid = part_man.uuid
                            new_ass.subject_type = part_man.item_type
                            new_ass.project_uuid = part_man.project_uuid
                            new_ass.source_id = 'tb-metadata'
                            new_ass.obs_node = '#obs-1'
                            new_ass.obs_num = 1
                            new_ass.sort = contrib_sort
                            new_ass.visibility = 1
                            new_ass.predicate_uuid = 'oc-28'
                            new_ass.object_uuid = contrib_uuid
                            new_ass.object_type = 'persons'
                            new_ass.save()
                            new_add = True
                        except:
                            new_add = False
                if prev_part is not None:
                    # now make assertions linking this and the previous item
                    # remove the current -> previous_link -> previous assertion
                    prev_pred = 'fd94db54-c6f8-484b-9aa6-e0aacc9d132d'
                    Assertion.objects\
                             .filter(uuid=part_man.uuid,
                                     predicate_uuid=prev_pred)\
                             .delete()
                    try:
                        # previous entry (current -> prev_part)
                        new_ass = Assertion()
                        new_ass.uuid = part_man.uuid
                        new_ass.subject_type = part_man.item_type
                        new_ass.project_uuid = part_man.project_uuid
                        new_ass.source_id = 'tb-metadata'
                        new_ass.obs_node = '#obs-1'
                        new_ass.obs_num = 1
                        new_ass.sort = contrib_sort
                        new_ass.visibility = 110
                        new_ass.predicate_uuid = prev_pred
                        new_ass.object_uuid = prev_part.uuid
                        new_ass.object_type = prev_part.item_type
                        new_ass.save()
                        new_add = True
                    except:
                        new_add = False
                    # remove the previous -> next_link -> current assertion
                    next_pred = '50472e1c-2825-47cf-a69c-803b78f8891a'
                    Assertion.objects\
                             .filter(uuid=prev_part.uuid,
                                     predicate_uuid=next_pred)\
                             .delete()
                    try:
                        # next entry (prev_part -> current)
                        new_ass = Assertion()
                        new_ass.uuid = prev_part.uuid
                        new_ass.subject_type = prev_part.item_type
                        new_ass.project_uuid = prev_part.project_uuid
                        new_ass.source_id = 'tb-metadata'
                        new_ass.obs_node = '#obs-1'
                        new_ass.obs_num = 1
                        new_ass.sort = 111
                        new_ass.visibility = 1
                        new_ass.predicate_uuid = next_pred
                        new_ass.object_uuid = part_man.uuid
                        new_ass.object_type =  part_man.item_type
                        new_ass.save()
                        new_add = True
                    except:
                        new_add = False
                prev_part = part_man
    
    def make_authors(self, tb_dict):
        """ makes an author list from a tb_dict """
        if 'dc-terms:contributor' in tb_dict:
            contribs = tb_dict['dc-terms:contributor']
            num_contribs = len(contribs)
            authors = ' by trench supervisors '
            if num_contribs == 1:
                authors = ' by trench supervisor '
                authors += contribs[0]['label']
            elif num_contribs == 2:
                authors += contribs[0]['label'] + ' and ' + contribs[1]['label']
            else:
                i = 1
                for contrib in contribs:
                    if i == 1:
                        authors += contrib['label']
                    elif i > 1 and  i < num_contribs:
                        authors += ', ' + contrib['label']
                    else:
                        authors += ' and ' + contrib['label']
                    i += 1
        return authors                     
    
    def make_display_trenches(self, tb_dict, trenches):
        """ makes a list of trenches for display purposes on the trench book index page """
        last_sub = tb_dict['oc-gen:has-linked-context-path']['oc-gen:has-path-items'][-1]
        last_sub['unit_year_uuid'] = last_sub['id'].replace('http://opencontext.org/subjects/', '')
        tr_sub = tb_dict['oc-gen:has-linked-context-path']['oc-gen:has-path-items'][-2]
        found_last = False
        for trench in trenches:
            if trench['unit_year_uuid'] == last_sub['unit_year_uuid']:
                trench['label'] = tr_sub['label']
                found_last = True
        if found_last is False:
            # OK, we can't find the linked year-trench, so get the year info from it
            year_asses = Assertion.objects\
                                  .filter(uuid=last_sub['unit_year_uuid'],
                                          predicate_uuid='2C7FE888-C431-4FBD-39F4-38B7D969A811')[:1]
            if len(year_asses) > 0:
                last_sub['year'] = year_asses[0].data_num
                tr_sub = tb_dict['oc-gen:has-linked-context-path']['oc-gen:has-path-items'][-2]
                last_sub['trench_uuid'] = tr_sub['id'].replace('http://opencontext.org/subjects/', '')
                last_sub['label'] = tr_sub['label']
                trenches.append(last_sub)
        return trenches
            
    def get_update_tb_links_from_index(self, root_tb):
        """ gets and updates trench years and associations """
        trenches = []
        if self.json_index is None:
             self.json_index = self.pc.load_json_file_os_obj('mag-data',
                                                             self.pc.trench_book_index_json)
        if isinstance(self.json_index, list):
            for item in self.json_index:
                if 'trench_book_uuid' in item:
                    if root_tb.uuid == item['trench_book_uuid'] and 'trenches' in item:
                        sorting = 100
                        for tr_dict in item['trenches']:
                            if 'unit_year_uuid' in tr_dict and 'trench_uuid' in tr_dict:
                                try:
                                    tr_dict['yr_man_obj'] = Manifest.objects.get(uuid=tr_dict['unit_year_uuid'])
                                except:
                                    tr_dict['yr_man_obj'] = None
                                try:
                                    tr_dict['tr_man_obj'] = Manifest.objects.get(uuid=tr_dict['trench_uuid'])
                                except:
                                    tr_dict['tr_man_obj'] = None
                                if tr_dict['yr_man_obj'] is not None and tr_dict['tr_man_obj'] is not None:
                                    trenches.append(tr_dict)
                                    exist_links = Assertion.objects\
                                                           .filter(uuid=tr_dict['unit_year_uuid'],
                                                                   object_uuid=root_tb.uuid)[:1]
                                    if len(exist_links) < 1:
                                        sorting += 1
                                        try:
                                            new_ass = Assertion()
                                            new_ass.uuid = tr_dict['yr_man_obj'].uuid
                                            new_ass.subject_type = tr_dict['yr_man_obj'].item_type
                                            new_ass.project_uuid = tr_dict['yr_man_obj'].project_uuid
                                            new_ass.source_id = 'tb-metadata'
                                            new_ass.obs_node = '#obs-1'
                                            new_ass.obs_num = 1
                                            new_ass.sort = sorting
                                            new_ass.visibility = 1
                                            new_ass.predicate_uuid = 'oc-3'
                                            new_ass.object_uuid = root_tb.uuid
                                            new_ass.object_type = root_tb.item_type
                                            new_ass.save()
                                            new_add = True
                                        except:
                                            new_add = False
                                    exist_links = Assertion.objects\
                                                           .filter(object_uuid=tr_dict['unit_year_uuid'],
                                                                   uuid=root_tb.uuid)[:1]
                                    if len(exist_links) < 1:
                                        sorting += 1
                                        try:
                                            new_ass = Assertion()
                                            new_ass.uuid = root_tb.uuid
                                            new_ass.subject_type = root_tb.item_type
                                            new_ass.project_uuid = root_tb.project_uuid
                                            new_ass.source_id = 'tb-metadata'
                                            new_ass.obs_node = '#obs-1'
                                            new_ass.obs_num = 1
                                            new_ass.sort = sorting
                                            new_ass.visibility = 1
                                            new_ass.predicate_uuid = 'oc-3'
                                            new_ass.object_uuid = tr_dict['yr_man_obj'].uuid
                                            new_ass.object_type = tr_dict['yr_man_obj'].item_type
                                            new_ass.save()
                                            new_add = True
                                        except:
                                            new_add = False
        return trenches
                    

    def move_by_label_part(self, label_part, link_subject_uuid):
        """ merges old document items into new ones
            "Trench Book GM II:18-21"
        """
        old_objs = Manifest.objects\
                           .filter(item_type__in=['media', 'documents'],
                                   label__startswith=label_part)\
                           .order_by('sort')
        for old_obj in old_objs:
            print('Moving: ' + old_obj.label + ' ' + old_obj.item_type + ' ' + old_obj.uuid)
            sub_links_o = Assertion.objects\
                                    .filter(uuid=old_obj.uuid,
                                            object_type='subjects')\
                                    .exclude(object_uuid=link_subject_uuid)
            sub_links_s = Assertion.objects\
                                   .filter(object_uuid=old_obj.uuid,
                                           subject_type='subjects')\
                                   .exclude(uuid=link_subject_uuid)
            for old_s in sub_links_s:
                new_ass = old_s
                new_ass.uuid = link_subject_uuid
                new_ass.source_id = 'pc-tb-docs-merge'
                try:
                    ok = True
                    new_ass.save()
                except:
                    ok = False
            for old_o in sub_links_o:
                new_ass = old_o
                new_ass.object_uuid = link_subject_uuid
                new_ass.source_id = 'pc-tb-docs-merge'
                try:
                    ok = True
                    new_ass.save()
                except:
                    ok = False
            # now make sure we have linking relationships to a subject item
            self.add_new_links_to_and_from_subject(old_obj.uuid,
                                                   link_subject_uuid)
            Assertion.objects\
                     .filter(uuid=old_obj.uuid,
                             object_type='subjects')\
                     .exclude(object_uuid=link_subject_uuid)\
                     .delete()
            Assertion.objects\
                     .filter(object_uuid=old_obj.uuid,
                             subject_type='subjects')\
                     .exclude(uuid=link_subject_uuid)\
                     .delete()

    def add_new_links_to_and_from_subject(self, media_uuid, link_to_subj_uuid):
        """ adds new links to and from a subject """
        media_objs = Manifest.objects.filter(uuid=media_uuid)[:1]
        subj_objs = Manifest.objects.filter(uuid=link_to_subj_uuid)[:1]
        if len(media_objs) == 1 and len(subj_objs) == 1:
            m_obj = media_objs[0]
            s_obj = subj_objs[0]
            try:
                new_ass = Assertion()
                new_ass.uuid = m_obj.uuid
                new_ass.subject_type = m_obj.item_type
                new_ass.project_uuid = m_obj.project_uuid
                new_ass.source_id = 'pc-tb-docs-merge'
                new_ass.obs_node = '#obs-1'
                new_ass.obs_num = 1
                new_ass.sort = 1
                new_ass.visibility = 1
                new_ass.predicate_uuid = 'oc-3'
                new_ass.object_uuid = s_obj.uuid
                new_ass.object_type = s_obj.item_type
                new_ass.save()
                new_add = True
            except:
                new_add = False
            if new_add:
                print('added a missing link from item to unit')
            try:
                new_ass = Assertion()
                new_ass.uuid = s_obj.uuid
                new_ass.subject_type = s_obj.item_type
                new_ass.project_uuid = s_obj.project_uuid
                new_ass.source_id = 'pc-tb-docs-merge'
                new_ass.obs_node = '#obs-1'
                new_ass.obs_num = 1
                new_ass.sort = 1
                new_ass.visibility = 1
                new_ass.predicate_uuid = 'oc-3'
                new_ass.object_uuid = m_obj.uuid
                new_ass.object_type = m_obj.item_type
                new_ass.save()
                new_add = True
            except:
                new_add = False
            if new_add:
                print('added a missing link from unit to item')

    def merge_old_into_new_docs(self):
        """ merges old document items into new ones
            "Trench Book GM II:18-21"
        """
        old_docs = Manifest.objects\
                           .filter(item_type='documents',
                                   source_id=self.old_docs_source_id)\
                           .exclude(label__startswith='Trench Book AC Summary V,VI')\
                           .exclude(label__startswith='Trench Book KT II')\
                           .exclude(label__startswith='Trench Book SJG IV')\
                           .order_by('sort')
        for old_doc in old_docs:
            print('')
            print('Process: ' + old_doc.label)
            print('uuid: ' + old_doc.uuid)
            old_label = old_doc.label.replace('Trench Book ', '')
            if ':' in old_label:
                old_ex = old_label.split(':')
                book = old_ex[0].strip()
                pages = old_ex[1].strip()
                book = book + ' '
                pages = ':' + pages + ';'
            else:
                book = old_label.strip()
                pages = None
            if pages is None:
                new_man_objs = Manifest.objects\
                                       .filter(source_id=self.new_docs_source_id,
                                               item_type='documents',
                                               label=book)
            else:
                new_man_objs = Manifest.objects\
                                       .filter(source_id=self.new_docs_source_id,
                                               item_type='documents',
                                               label__contains=book)\
                                       .filter(label__contains=pages)
            if len(new_man_objs) == 1:
                # found a match by page range.
                self.merge_old_and_new_tb_entry(old_doc.uuid,
                                                new_man_objs[0].uuid)
            else:
                 # ok look up common trench book ids
                ass_ids = Assertion.objects\
                                   .filter(uuid=old_doc.uuid,
                                           predicate_uuid='DDE6114E-9BB4-40A4-AD80-55FBEAB6663A')[:1]
                if len(ass_ids) > 0:
                    old_id = ass_ids[0].data_num
                    # print('Check old id: ' + str(old_id))
                    new_ass_ids = Assertion.objects\
                                           .filter(subject_type='documents',
                                                   predicate_uuid='fa50506c-d1f0-4798-84b2-a7a48c0b4c74',
                                                   data_num=old_id)[:1]
                    if len(new_ass_ids) > 0:
                        new_root_doc = Manifest.objects.get(uuid=new_ass_ids[0].uuid)
                        book = new_root_doc.label + ' '
                        print('Matched IDs: ' + str(old_id) + ' ' + old_label + ' -> ' + book )
                # look for match by date
                ass_dates = Assertion.objects\
                                     .filter(uuid=old_doc.uuid,
                                             predicate_uuid='6A359C65-9F07-417A-37F1-881E48669140')[:1]
                if len(ass_dates) > 0:
                    ass_date = str(ass_dates[0].data_date.date().isoformat())
                    print('Check: ' + ass_date )
                    new_man_objs = Manifest.objects\
                                       .filter(source_id=self.new_docs_source_id,
                                               item_type='documents',
                                               label__contains=book)\
                                       .filter(label__contains=ass_date)
                    if len(new_man_objs) == 1:
                        # found a match by page range.
                        self.merge_old_and_new_tb_entry(old_doc.uuid,
                                                        new_man_objs[0].uuid)
                        
    def merge_old_and_new_tb_entry(self, old_uuid, new_uuid):
        """ merge an old and a new trench book entry """
        old_docs = Manifest.objects\
                           .filter(uuid=old_uuid,
                                   item_type='documents')[:1]
        new_docs = Manifest.objects\
                           .filter(uuid=new_uuid,
                                   item_type='documents')[:1]
        if len(old_docs) == 1 and len(new_docs) == 1:
            all_ok = True
            old_doc = old_docs[0]
            new_man = new_docs[0]
            # get the old document object to prep for deletion
            old_doc_obj = OCdocument.objects.get(uuid=old_doc.uuid)
            # get links to related documents and media resoruces to
            # prep for linking to the new document
            old_media_s = Assertion.objects\
                                   .filter(uuid=old_doc.uuid,
                                           object_type__in=['media', 'documents'])
            old_media_o = Assertion.objects\
                                   .filter(object_uuid=old_doc.uuid,
                                           subject_type__in=['media', 'documents'])
            old_label = old_doc.label.replace('Trench Book ', '')
            print('Match: ' + old_label + ' -> ' + new_man.label)
            rel_units = self.get_related_units_by_tb_entry(new_man)
            rel_media = []
            for old_s in old_media_s:
                if old_s.object_uuid not in rel_media:
                    rel_media.append(old_s.object_uuid)
                new_ass = old_s
                new_ass.uuid = new_man.uuid
                new_ass.source_id = 'pc-tb-docs-merge'
                try:
                    ok = True
                    new_ass.save()
                except:
                    ok = False
            for old_o in old_media_o:
                if old_o.uuid not in rel_media:
                    rel_media.append(old_o.uuid)
                new_ass = old_o
                new_ass.object_uuid = new_man.uuid
                new_ass.source_id = 'pc-tb-docs-merge'
                try:
                    ok = True
                    new_ass.save()
                except:
                    ok = False
            if len(rel_media) > 0 and len(rel_units) > 0 and all_ok:
                rel_unit = rel_units[0]
                for m_uuid in rel_media:
                    # now make sure we have linking relationships to a subject item
                    self.add_new_links_to_and_from_subject(m_uuid,
                                                           rel_unit.uuid)
                sub_links_o = Assertion.objects\
                                       .filter(uuid__in=rel_media,
                                               object_type='subjects')\
                                       .exclude(object_uuid=rel_unit.uuid)
                sub_links_s = Assertion.objects\
                                       .filter(object_uuid__in=rel_media,
                                               subject_type='subjects')\
                                       .exclude(uuid=rel_unit.uuid)
                for old_s in sub_links_s:
                    new_ass = old_s
                    new_ass.uuid = rel_unit.uuid
                    new_ass.source_id = 'pc-tb-docs-merge'
                    try:
                        ok = True
                        new_ass.save()
                    except:
                        ok = False
                    if ok is False:
                        old_s.delete()
                        pass
                for old_o in sub_links_o:
                    new_ass = old_o
                    new_ass.object_uuid = rel_unit.uuid
                    new_ass.source_id = 'pc-tb-docs-merge'
                    try:
                        ok = True
                        new_ass.save()
                    except:
                        ok = False
                    if ok is False:
                        old_o.delete()
                        pass
            if all_ok:
                print('Merged: ' + old_label + ' -> ' + new_man.label)
                print('')
                print('')
                r_url = RedirectURL()
                r_url.note = 'Redirect old trenchbook transcriptions to fixed versions'
                r_url.set_redirect_for_type_ids('documents', old_doc.uuid, new_man.uuid)
                old_doc.delete()
                old_doc_obj.delete()
                Assertion.objects\
                         .filter(uuid=old_doc.uuid)\
                         .delete()
                Assertion.objects\
                        .filter(object_uuid=old_doc.uuid)\
                        .delete()
            
    
    def clean_bad_html_content(self):
        """ gets HTML from the old Poggion Civitiate Website
            for a TB entry, and then cleans it to save locally
        """
        url_prefix = 'http://www.poggiocivitate.org/catalog/trenchbooks/viewtrenchbookentry.asp?'
        url_base = 'http://www.poggiocivitate.org/catalog/trenchbooks/viewtrenchbookentry.asp'
        oc_docs = OCdocument.objects\
                            .filter(content__contains='Return to Trench Book Editing')
        for oc_doc in oc_docs:
            act_man_obj = Manifest.objects.get(uuid=oc_doc.uuid)
            clean_html = None
            data = act_man_obj.sup_json
            data_changed = False
            tbtdid = data['tbtdid']
            tbtid = data['tbtid']
            if 'url' not in data:
                tbtdid = data['tbtdid']
                tbtid = data['tbtid']
                data['url'] = url_prefix + 'tbtid=' + str(tbtid) + '&tbtdid=' + str(tbtdid)
                data_changed = True
            if data_changed:
                act_man_obj.sup_json = data
                act_man_obj.save()
            url = data['url']
            act_file = self.pc.compose_filename_from_link(url)
            dir_file = self.pc.define_import_directory_file(self.pc.pc_directory,
                                                            act_file)
            page_str = self.pc.load_file(dir_file)
            if not isinstance(page_str, str):
                sleep(.5)
                print('Cache URL: ' + url + ' filename:' + act_file)
                ok = self.pc.cache_page_locally(url,
                                                {},
                                                self.pc_directory,
                                                act_file)
            page_str = self.pc.load_file(dir_file)
            if isinstance(page_str, str):
                print('Try to clean filename:' + act_file)
                clean_html = self.clean_html(page_str, act_man_obj)
                if isinstance(clean_html, str):
                    clean_html = clean_html.replace('<html>', '')
                    clean_html = clean_html.replace('</html>', '')
                    clean_html = clean_html.replace('<body>', '')
                    clean_html = clean_html.replace('</body>', '')
                    oc_doc.content = clean_html
                    oc_doc.save()
                    print('Updated content for: ' + act_man_obj.label + ' ' + act_man_obj.uuid)
    
    def get_clean_missing_content(self):
        """ gets HTML from the Poggio Civitate website for a document
            that is missing such content
        """
        url_prefix = 'http://www.poggiocivitate.org/catalog/trenchbooks/viewtrenchbookentry.asp?'
        url_base = 'http://www.poggiocivitate.org/catalog/trenchbooks/viewtrenchbookentry.asp'
        pred_tbtid = '1a4514bd-c1ef-4e66-9402-96cb29027891'
        oc_docs = OCdocument.objects\
                            .annotate(text_len=Length('content'))\
                            .filter(text_len__gt=0)\
                            .filter(text_len__lt=10)
        for oc_doc in oc_docs:
            tbtdid = oc_doc.content.strip()
            ass_tbtids = Assertion.objects\
                                  .filter(uuid=oc_doc.uuid,
                                          predicate_uuid=pred_tbtid)[:1]
            if len(ass_tbtids) > 0:
                obj_uuid = ass_tbtids[0].object_uuid
                obj_man = Manifest.objects.get(uuid=obj_uuid)
                tbtid = obj_man.label.strip()
                print('Content (tbtdid): ' + tbtdid + ', tbtid: ' + str(tbtid))
                act_man_obj = Manifest.objects.get(uuid=oc_doc.uuid)
                data_changed = False
                data = act_man_obj.sup_json
                if 'tbtdid' not in data:
                    data['tbtdid'] = int(float(tbtdid))
                    data_changed = True
                if 'tbtid' not in data:
                    data['tbtid'] = int(float(tbtid))
                    data_changed = True
                if 'url' not in data:
                    data['url'] = url_prefix + 'tbtid=' + str(tbtid) + '&tbtdid=' + str(tbtdid)
                    data_changed = True
                url = data['url']
                if 'file' not in data:
                    data['file'] = self.pc.compose_filename_from_link(url)
                    data_changed = True
                act_file = data['file'] 
                if data_changed:
                    act_man_obj.sup_json = data
                    act_man_obj.save()
                clean_html = None
                dir_file = self.pc.define_import_directory_file(self.pc.pc_directory,
                                                                act_file)
                page_str = self.pc.load_file(dir_file)
                if not isinstance(page_str, str):
                    sleep(.5)
                    print('Cache URL: ' + url + ' filename:' + act_file)
                    ok = self.pc.cache_page_locally(url,
                                                    {},
                                                    self.pc_directory,
                                                    act_file)
                page_str = self.pc.load_file(dir_file)
                if isinstance(page_str, str):
                    print('Try to clean filename:' + act_file)
                    clean_html = self.clean_html(page_str, act_man_obj)
                    if isinstance(clean_html, str):
                        oc_doc.content = clean_html
                        oc_doc.save()
                        print('Updated content for: ' + act_man_obj.label + ' ' + act_man_obj.uuid)
                if clean_html is None:
                    oc_doc.content = 'Could not retrieve trench book entry as of August 12, 2017. '
                    oc_doc.content += 'The legacy data source did not have content for this entry.'
                    oc_doc.save()
                
    def clean_files(self):
        """ cleans html """
        self.get_tb_files_list()
        for act_file in self.tb_files:
            if len(self.file_id_limits) > 0:
                clean_ok = False
                for limit_id in self.file_id_limits:
                    if str(limit_id) in act_file:
                        clean_ok = True
            else:
                clean_ok = True
            if clean_ok:
                clean_html = self.clean_file(act_file)
                if isinstance(clean_html, str):
                    new_filename = act_file.replace('viewtrenchbookentry', 'ztbentry')
                    print('Save cleaned file: ' + new_filename)
                    self.pc.save_file(clean_html,
                                      self.pc.pc_directory,
                                      new_filename)
                    act_man_obj = self.get_tb_entry_manifest_obj(act_file)
                    if act_man_obj is not None:
                        print('Save content to: ' + act_man_obj.uuid)
                        doc_obj = OCdocument.objects.get(uuid=act_man_obj.uuid)
                        doc_obj.content = clean_html
                        doc_obj.save()
    
    def clean_file(self, act_file):
        """ cleans a file """
        act_man_obj = self.get_tb_entry_manifest_obj(act_file)
        dir_file = self.pc.define_import_directory_file(self.pc.pc_directory,
                                                        act_file)
        page_str = self.pc.load_file(dir_file)
        if not isinstance(page_str, str) or act_man_obj is None:
            print('failed to open ' + dir_file + ' or cannnot find document item in DB')
            clean_html = None
        else:
            clean_html = self.clean_html(page_str, act_man_obj)
        return clean_html
    
    def clean_file_by_uuid(self, uuid, act_file):
        """ cleans a file by uuid and filename """
        page_str = None
        act_man_obj = None
        try:
            act_man_obj = Manifest.objects.get(uuid=uuid)
            data = self.prep_tb_entry_data(act_file)
            if isinstance(data, dict):
                act_man_obj.sup_json = data
                act_man_obj.save()
        except:
            act_man_obj = None
        dir_file = self.pc.define_import_directory_file(self.pc.pc_directory,
                                                        act_file)
        page_str = self.pc.load_file(dir_file)
        if not isinstance(page_str, str) or act_man_obj is None:
            print('failed to open ' + dir_file + ' or cannnot find document item in DB')
            clean_html = None
        else:
            clean_html = self.clean_html(page_str, act_man_obj)
        if isinstance(clean_html, str):
            oc_doc = OCdocument.objects.get(uuid=uuid)
            clean_html = clean_html.replace('<html>', '')
            clean_html = clean_html.replace('</html>', '')
            clean_html = clean_html.replace('<body>', '')
            clean_html = clean_html.replace('</body>', '')
            oc_doc.content = clean_html
            oc_doc.save()
            print('Updated content for: ' + act_man_obj.label + ' ' + act_man_obj.uuid)
        return clean_html
    
    def clean_html(self,
                   page_str,
                   act_man_obj):
        """ cleans the html of a page string """
        rel_tb_man_objs = self.get_related_tb_entries(act_man_obj)
        rel_loci_man_objs = self.get_related_loci_by_tb_entry(act_man_obj)
        print('Count related loci: ' + str(len(rel_loci_man_objs)))
        clean_html = None
        pb_count = 0
        uuids_in_file = {}
        self.media_id_manifest = {}
        self.media_src = {}
        if not isinstance(page_str, str):
            print('ERROR: the page_str needs to be a string')
        else:
            if isinstance(page_str, bytes):
                page_str = page_str.decode('utf-8')
                print('Convert bytes to string')
            if page_str[0:2] == "b'":
                page_str = page_str[2:]
            page_str = page_str.replace('\\r\\n', '')
            page_str = str(page_str)
            act_page_part = self.get_str_between_start_end(page_str,
                                                           '<a href="trenchbookdaily.asp">Return to Trench Book Logs</a>',
                                                           '</html>')
            if isinstance(act_page_part, str):
                mid_page_part = self.get_str_between_start_end(act_page_part,
                                                               '</table><br>',
                                                               '<table width="100%" cellspacing="0" cellpadding="0" border="0">')
                if not isinstance(mid_page_part, str):
                    mid_page_part = self.get_str_between_start_end(act_page_part,
                                                                   '</table><br>',
                                                                   '>Return to Trench Book Editing</a>')
                if isinstance(mid_page_part, str):
                    act_page_part = mid_page_part
            if isinstance(act_page_part, str):
                first_html = '<html><head></head><body><div id="cleaned-tb-html" class="table-responsive"><p>'
                act_page_part = first_html + act_page_part + '</div></body></html>'
            else:
                act_page_part = page_str
            soup = BeautifulSoup(act_page_part, 'lxml')
            # now go through and find all the images and links
            for tag in soup.findAll():
                if tag.name.lower() == 'a' or tag.name.lower() == 'img':
                    for attrib, val in tag.attrs.items():
                        if attrib == 'href':
                            href = tag['href']
                            if 'viewPhoto' in href:
                                man_obj = self.get_man_obj_from_view_photo(href, None)
                        elif attrib == 'src':
                            src = tag['src']
                            media_file = self.get_oc_mediafile(src, None)
            for tag in soup.findAll():
                id_str = None
                class_str = None
                data_str = None
                title_str = None
                style_str = None
                if tag.name.lower() in self.ok_tags:
                    bad_attribs = []
                    for attrib, val in tag.attrs.items(): 
                        if attrib is not None:
                            if attrib not in self.ok_attributes:
                                bad_attribs.append(attrib)
                            elif attrib == 'href':
                                # do something about links
                                href = tag['href']
                                href_type = self.get_str_between_start_end(href, 'javascript:', '(')
                                if isinstance(href_type, str) and href_type not in self.javascript_links:
                                    self.javascript_links.append(href_type)
                                man_obj = self.get_man_obj_from_href(href,
                                                                     rel_tb_man_objs,
                                                                     rel_loci_man_objs)
                                if man_obj is not None:
                                    if man_obj.uuid not in uuids_in_file:
                                        uuids_in_file[man_obj.uuid] = 1
                                    else:
                                        uuids_in_file[man_obj.uuid] += 1
                                    id_str = 'a--' + man_obj.item_type + '--' + man_obj.uuid + '--' + str(uuids_in_file[man_obj.uuid])
                                    new_href = 'http://opencontext.org/' + man_obj.item_type + '/' + man_obj.uuid
                                    title_str = 'Link to: ' + man_obj.label
                                    tag['href'] = new_href
                                    if man_obj.href > 1 or act_man_obj.uuid == man_obj.uuid:
                                        data_str = href
                                        style_str = 'display:none;'
                                    if man_obj.exact_match is False:
                                        data_str = href
                                else:
                                    data_str = href
                                    title_str = 'Linked item not found'
                                    style_str = 'display:none;'
                                    tag['href'] = '#link-not-found'
                            elif attrib == 'src':
                                # do something about images
                                class_str = 'img-responsive img-thumbnail'
                                src = tag['src']
                                media_file = self.get_oc_mediafile(src)
                                if media_file is not None:
                                    id_str = 'src--' + media_file.uuid
                                    new_src = media_file.file_uri
                                    tag['src'] = new_src
                                    if media_file.src > 1:
                                        data_str = src
                                        style_str = 'display:none;'
                                    if media_file.exact_match is False:
                                        data_str = href
                                else:
                                    title_str = 'Image not found'
                                    style_str = 'display:none;'
                            elif attrib == 'id':
                                tag_id = tag['id']
                                if tag_id == 'righttbphotobox':
                                    pb_count += 1
                                    tag['id'] = 'righttbphotobox-' + str(pb_count)
                                    style_str = 'font-size: 0;'
                                    class_str = self.pc_photobox_class
                                    tag.name = 'div'
                                    brs = tag.find_all('br')
                                    for br in brs:
                                        # get rid of line breaks inside this div
                                        br.extract()
                                    # get rid of the link break adead of this div
                                    p_tag = tag.previous_sibling
                                    if p_tag is not None:
                                        if p_tag.name.lower() == 'br':
                                            # get rid of not used line breaks
                                            p_tag.extract()
                    for attrib in bad_attribs:
                        del tag[attrib]
                    if tag.name.lower() == 'a':
                        tag['target'] = '_blank'
                    if tag.name.lower() == 'table':
                        class_str = 'table table-condensed table-bordered'
                    if isinstance(id_str, str):
                        tag['id'] = id_str
                    if isinstance(class_str, str):
                        tag['class'] = class_str
                    if isinstance(title_str, str):
                        tag['title'] = title_str
                    if isinstance(style_str, str):
                        tag['style'] = style_str
                        if style_str == 'display:none;':
                            p_tag = tag.previous_sibling
                            if isinstance(p_tag, Tag):
                                if p_tag.name.lower() == 'br':
                                    # get rid of not used line breaks
                                    p_tag.extract()
                    if isinstance(data_str, str):
                        tag['data'] = data_str
                elif tag.name.lower() in self.blacklist_tags:
                    tag.extract()
                elif tag.name.lower() == 'font':
                    tag.name = 'span'
                    tag.attrs = []
                else:
                    tag.name = 'div'
                    tag.attrs = []
            clean_html = soup.prettify()
            clean_html = clean_html.replace('<?xml:namespace prefix = "o" ns = "urn:schemas-microsoft-com:office:office" />', '')
            clean_html = clean_html.replace('\\x96', ' ')
            clean_html = clean_html.replace('\\x92', "'")
            clean_html = clean_html.replace("\\'", "'")
            if 'class="table-responsive"' not in clean_html:
                clean_html = '<div class="table-responsive">' + clean_html + '</div>'
            soup = BeautifulSoup(clean_html, 'lxml')
            for tag in soup.findAll():
                self.remove_empty_node(tag)
                self.check_fix_photobox(tag)
            clean_html = soup.prettify()
            clean_html.replace('<html>', '')
            clean_html.replace('</html>', '')
            clean_html.replace('<body>', '')
            clean_html.replace('</body>', '')
        return clean_html
    
    def check_fix_photobox(self, node):
        """ gets rid of empty tags """
        if isinstance(node, Tag):
            if node.get('class') is not None:
                node_clases = node.get('class')
                if node_clases[0] == self.pc_photobox_class:
                    # print('Check: '+ node_clases[0])
                    make_span = False
                    show_img = False
                    img_nodes = node.find_all(['img'])
                    if len(img_nodes) < 1:
                        make_span = True
                    else:
                        for img in img_nodes:
                            # print('img style: ' + str(img.get('style')))
                            if img.get('style') is None:
                                show_img = True
                            else:
                                img_styles = img.get('style')
                                if 'display:none;' in img_styles:
                                    # print('ok img..')
                                    pass
                                else:
                                    # print('crap!')
                                    show_img = True
                        if show_img is False:
                            # print('img ok to span transform')
                            make_span = True
                    if make_span:
                        # print('Span transform')
                        node.name = 'span'                                
    
    def remove_empty_node(self, node):
        """ gets rid of empty tags """
        if isinstance(node, Tag):
            keep_nodes = [
                'img',
                'td',
                'tr',
                'th',
            ]
            if node.name.lower() not in keep_nodes:
                remove_node = False
                no_child_remove_tags = [
                    'a',
                    'img',
                    'th',
                    'tr',
                    'td',
                    'strong',
                    'ul',
                    'ol',
                    'li',
                    'em',
                    'i',
                    'u',
                    'b',
                    'sup',
                    'sub',
                    'mark',
                    'q',
                    'samp',
                    'small'
                ]
                ok_child_nodes = node.find_all(no_child_remove_tags)
                if len(ok_child_nodes) < 1:
                    # ok no images check for text
                    all_string = ''
                    for act_string in node.stripped_strings:
                        all_string += str(act_string)
                    for d_child in node.descendants:
                        if isinstance(d_child, Tag):
                            for act_string in d_child.stripped_strings:
                                all_string += str(act_string)
                    all_string = all_string.strip()
                    # print('Check on: <' + node.name.lower() + '> with: ' + str(all_string))
                    if len(all_string) < 1:
                        remove_node = True
                    if isinstance(node.string, str):
                        n_string = node.string
                        n_string = n_string.strip()
                        if len(n_string) < 1:
                            remove_node = True
                        else:
                            remove_node = False
                if remove_node:
                    # print('Removing a: <' + node.name.lower() + '>')
                    node.extract()
        
    def get_related_tb_entries(self, tb_man_obj):
        """ gets a list of related trench book entries """
        rel_tb_man_objs = []
        if tb_man_obj is not None:
            ass_part_ofs = Assertion.objects\
                                    .filter(uuid=tb_man_obj.uuid,
                                            predicate_uuid='0BB889F9-54DD-4F70-5B63-F5D82425F0DB',
                                            object_type='documents')[:1]
            if len(ass_part_ofs) > 0:
                main_tb_uuid = ass_part_ofs[0].object_uuid
                ass_has_parts = Assertion.objects\
                                         .filter(uuid=main_tb_uuid,
                                                 predicate_uuid='BD384F1F-FB29-4A9D-7ACA-D8F6B4AF0AF9',
                                                 object_type='documents')
                parts_uuids = []
                for ass_has_part in ass_has_parts:
                    parts_uuids.append(ass_has_part.object_uuid)
                rel_tb_man_objs = Manifest.objects.filter(uuid__in=parts_uuids).order_by('sort')
        return rel_tb_man_objs
    
    def get_related_loci_by_tb_entry(self, tb_man_obj):
        """ gets a list of related trench book entries """
        rel_loci_man_objs = []
        if tb_man_obj is not None:
            rel_sub_uuids = []
            ass_rel_subs = Assertion.objects\
                                    .filter(object_uuid=tb_man_obj.uuid,
                                            subject_type='subjects')
            for ass_rel in ass_rel_subs:
                if ass_rel.uuid not in rel_sub_uuids:
                    rel_sub_uuids.append(ass_rel.uuid)
            ass_rel_subs = Assertion.objects\
                                    .filter(uuid=tb_man_obj.uuid,
                                            object_type='subjects')
            for ass_rel in ass_rel_subs:
                if ass_rel.uuid not in rel_sub_uuids:
                    rel_sub_uuids.append(ass_rel.uuid)
            if len(rel_sub_uuids) > 0:
                # now get contained subjects, as these may have the loci
                ass_cont_rel_subs = Assertion.objects\
                                             .filter(uuid__in=rel_sub_uuids,
                                                     predicate_uuid=Assertion.PREDICATES_CONTAINS)
                for ass_cont in ass_cont_rel_subs:
                    if ass_cont.object_uuid not in rel_sub_uuids:
                        rel_sub_uuids.append(ass_cont.object_uuid )
                ass_cont_rel_subs = Assertion.objects\
                                             .filter(object_uuid__in=rel_sub_uuids,
                                                     predicate_uuid=Assertion.PREDICATES_CONTAINS)
                for ass_cont in ass_cont_rel_subs:
                    if ass_cont.uuid not in rel_sub_uuids:
                        rel_sub_uuids.append(ass_cont.uuid)
            # print('Found: ' + str((rel_sub_uuids)))
            if len(rel_sub_uuids) > 0:
                rel_loci_man_objs = Manifest.objects\
                                            .filter(uuid__in=rel_sub_uuids,
                                                    class_uri='oc-gen:cat-locus')\
                                            .order_by('sort')
        return rel_loci_man_objs
    
    def get_related_units_by_tb_entry(self, tb_man_obj):
        """ gets a list of related trench book entries """
        rel_unit_man_objs = []
        if tb_man_obj is not None:
            rel_sub_uuids = []
            ass_rel_subs = Assertion.objects\
                                    .filter(object_uuid=tb_man_obj.uuid,
                                            subject_type='subjects')
            for ass_rel in ass_rel_subs:
                if ass_rel.uuid not in rel_sub_uuids:
                    rel_sub_uuids.append(ass_rel.uuid)
            ass_rel_subs = Assertion.objects\
                                    .filter(uuid=tb_man_obj.uuid,
                                            object_type='subjects')
            for ass_rel in ass_rel_subs:
                if ass_rel.uuid not in rel_sub_uuids:
                    rel_sub_uuids.append(ass_rel.uuid)
            if len(rel_sub_uuids) > 0:
                # now get contained subjects, as these may have the loci
                ass_cont_rel_subs = Assertion.objects\
                                             .filter(uuid__in=rel_sub_uuids,
                                                     predicate_uuid=Assertion.PREDICATES_CONTAINS)
                for ass_cont in ass_cont_rel_subs:
                    if ass_cont.object_uuid not in rel_sub_uuids:
                        rel_sub_uuids.append(ass_cont.object_uuid )
                ass_cont_rel_subs = Assertion.objects\
                                             .filter(object_uuid__in=rel_sub_uuids,
                                                     predicate_uuid=Assertion.PREDICATES_CONTAINS)
                for ass_cont in ass_cont_rel_subs:
                    if ass_cont.uuid not in rel_sub_uuids:
                        rel_sub_uuids.append(ass_cont.uuid)
            # print('Found: ' + str((rel_sub_uuids)))
            if len(rel_sub_uuids) > 0:
                rel_unit_man_objs = Manifest.objects\
                                            .filter(uuid__in=rel_sub_uuids,
                                                    class_uri='oc-gen:cat-exc-unit')\
                                            .order_by('sort')
        return rel_unit_man_objs

    def get_tb_entry_manifest_obj(self, act_file):
        """ gets the manifest object for a trenchboook entry """
        man_obj = None
        data = self.prep_tb_entry_data(act_file)
        if isinstance(data, dict):
            if data['tbtdid'] is not None:
                tbtdid = data['tbtdid']
                cont_val = '"tbtdid":' + str(tbtdid) + ','
                man_objs = Manifest.objects\
                                   .filter(item_type='documents',
                                           sup_json__contains=cont_val)[:1]
                if len(man_objs) > 0:
                    man_obj = man_objs[0]
                    print('Found document manifest object for: ' + man_obj.label)
                else:
                    # can't find a manifest object based on the sup json field
                    oc_docs = OCdocument.objects\
                                        .filter(content=str(tbtdid))[:1]
                    if len(oc_docs) > 0:
                        man_obj = Manifest.objects.get(uuid=oc_docs[0].uuid)
                        man_obj.sup_json = data
                        man_obj.save()
                        print('Saved supplemental json to: ' + man_obj.label)
        return man_obj
                  
    def get_related_trench_book(self, tbid):
        """ gets the related trench book """
        man_obj = None
        asses_tb = Assertion.objects\
                            .filter(subject_type='documents',
                                    predicate_uuid=self.tb_id_pred,
                                    data_num=tbid)[:1]
        if len(asses_tb) > 0:
            man_obj = Manifest.objects.get(uuid=asses_tb[0].uuid)
        return man_obj
    
    def get_man_obj_from_href(self, href, rel_tb_man_objs, rel_loci_man_objs):
        """ gets an object from an href, depending on the javascript used """
        man_obj = None
        if isinstance(href, str):
            if 'viewPhoto' in href:
                man_obj = self.get_man_obj_from_view_photo(href)
            elif 'viewartifactcatalog' in href:
                man_obj = self.get_man_obj_from_catalog(href)
                if man_obj is not None:
                    man_obj.exact_match = True
                    man_obj.href = 0
            elif 'trenchbookviewer' in href or 'viewtrenchbookreference' in href:
                man_obj = self.get_related_tb_entry_man_obj(href, rel_tb_man_objs)
                if man_obj is not None:
                    man_obj.exact_match = True
                    man_obj.href = 0
            elif 'viewlocus' in href:
                man_obj = self.get_related_locus_man_obj(href, rel_loci_man_objs)
                if man_obj is not None:
                    man_obj.exact_match = True
                    man_obj.href = 0
            else:
                man_obj = None
        return man_obj

    def transform_href(self, href):
        """ transforms a href, especially with javascript in it, to a
            URL that can be crawled
        """
        if isinstance(href, str):
            if 'javascript:' in href:
                # print('found some javascript')
                if 'viewPhoto' in href:
                    # javascript:viewPhoto('19850010bt.jpg');
                    # http://www.poggiocivitate.org/photos/enlargements/19850010bt.jpg
                    href_ex = href.split('viewPhoto')
                    if len(href_ex) > 1:
                        href = href_ex[1]
                        href = href.replace("'", '')
                        href = href.replace(")", '')
                        href = href.replace("(", '')
                        href = href.replace(";", '')
                        href = href.replace("\\", '')
                        href = 'http://www.poggiocivitate.org/photos/enlargements/' + href
                elif 'viewartifactcatalog.asp?' in href:
                    href_ex = href.split('viewartifactcatalog.asp?')
                    if len(href_ex) > 1:
                        href = href_ex[1]
                        href = href.replace("'", '')
                        href = href.replace(")", '')
                        href = href.replace("(", '')
                        href = href.replace(";", '')
                        href = href.replace("\\", '')
                        href = 'http://www.poggiocivitate.org/catalog/viewartifactcatalog.asp?' + href
                elif 'trenchbookviewer.asp?' in href:
                    href_ex = href.split('trenchbookviewer.asp?')
                    if len(href_ex) > 1:
                        href = href_ex[1]
                        href = href.replace("'", '')
                        href = href.replace(")", '')
                        href = href.replace("(", '')
                        href = href.replace(";", '')
                        href = href.replace("\\", '')
                        href = 'http://www.poggiocivitate.org/catalog/trenchbooks/trenchbookviewer.asp?' + href
                elif 'viewtrenchbookreference.asp?' in href:
                    href_ex = href.split('viewtrenchbookreference.asp?')
                    if len(href_ex) > 1:
                        href = href_ex[1]
                        href = href.replace("'", '')
                        href = href.replace(")", '')
                        href = href.replace("(", '')
                        href = href.replace(";", '')
                        href = href.replace("\\", '')
                        href = 'http://www.poggiocivitate.org/catalog/trenchbooks/viewtrenchbookreference.asp?' + href
                elif 'viewlocus.asp?' in href:
                    href_ex = href.split('viewlocus.asp?')
                    if len(href_ex) > 1:
                        href = href_ex[1]
                        href = href.replace("'", '')
                        href = href.replace(")", '')
                        href = href.replace("(", '')
                        href = href.replace(";", '')
                        href = href.replace("\\", '')
                        href = 'http://www.poggiocivitate.org/admin/viewlocus.asp?' + href   
        return href
    
    def get_related_locus_man_obj(self, href, rel_loci_man_objs):
        """ gets a related locus manifest object in an href
            javascript:openViewer('viewlocus.asp?locus=1&tbtid=318&tbtdid=##tbtdid##')
        """
        man_obj = None
        if 'locus=' in href and len(rel_loci_man_objs) > 0:
            href_ex = href.split('locus=')
            l_and_junk = href_ex[1]
            i = 0
            len_l_and_j = len(l_and_junk)
            find_locus = ''
            go_on = True
            # print('Working on viewlocus: ' + l_and_junk)
            while i < len_l_and_j and go_on:
                if l_and_junk[i].isdigit():
                    find_locus += l_and_junk[i]
                else:
                    go_on = False
                i += 1
            try:
                find_locus = int(float(find_locus))
            except:
                find_locus = None
            if find_locus is not None:
                find_l_label = 'Locus ' + str(find_locus)
                for l_man_obj in rel_loci_man_objs:
                    # print('Check: ' + find_l_label + ' ' + l_man_obj.label)
                    if find_l_label == l_man_obj.label:
                        man_obj = l_man_obj
                        break
        return man_obj
    
    def get_related_tb_entry_man_obj(self, href, rel_tb_man_objs):
        """ gets a related trench book entry by page in an href """
        man_obj = None
        if 'searchpage=' in href and len(rel_tb_man_objs) > 0:
            href_ex = href.split('searchpage=')
            page_and_junk = href_ex[1]
            i = 0
            len_p_and_j = len(page_and_junk)
            find_page = ''
            go_on = True
            # print('Working on searchpage: ' + page_and_junk)
            while i < len_p_and_j and go_on:
                if page_and_junk[i].isdigit():
                    find_page += page_and_junk[i]
                else:
                    go_on = False
                i += 1
            try:
                find_page = int(float(find_page))
            except:
                find_page = None
            if find_page is not None:
                for tb_man_obj in rel_tb_man_objs:
                    p_range = self.get_page_range_from_tb_entry_label(tb_man_obj.label)
                    # print('Find: ' + str(find_page) + ' in: ' + str(p_range))
                    if len(p_range) > 0:
                        if find_page >= min(p_range) and find_page <= max(p_range):
                            man_obj = tb_man_obj
                            break
        return man_obj
                
    def get_page_range_from_tb_entry_label(self, label):
        """ gets the page range from an trench book entry label """
        p_range = []
        if ':' in label and ';' in label:
            l_ex_a = label.split(':')
            p_part = l_ex_a[1]
            if ';' in p_part:    
                p_part_ex = p_part.split(';')
                pages = p_part_ex[0]
                if '-' in pages:
                    pages_ex = pages.split('-')
                else:
                    pages_ex = [pages]
                for page_str in pages_ex:
                    page = None
                    try:
                        page = int(float(page_str))
                    except:
                        page = None
                    if page is not None:
                       p_range.append(page)
        return p_range
    
    def get_man_obj_from_catalog(self, href):
        """ gets the manifest object from a "viewPhoto" javascript href """
        man_obj = None
        if 'aid=' in href:
            href_ex = href.split('aid=')
            id_part = href_ex[1]
            id_part = id_part.replace('\\', '')
            id_part = id_part.replace('PC', '')
            id_part = id_part.replace('VdM', '')
            id_part = id_part.replace('(', '')
            id_part = id_part.replace(')', '')
            id_part = id_part.replace(';', '')
            id_part = id_part.replace("'", '')
            id_part = id_part.replace('"', '')
            id_part = id_part.replace(' ', '')
            man_objs = Manifest.objects\
                               .filter(label__contains=id_part,
                                       item_type='subjects',
                                       class_uri__in=self.obj_class_uris)[:1]
            if len(man_objs) > 0:
                man_obj = man_objs[0]
        if man_obj is None:
            print('Could not find objects manifest object for: ' + href)
        return man_obj
    
    def get_man_obj_from_view_photo(self, href, use_as='href'):
        """ gets the manifest object from a "viewPhoto" javascript href """
        man_obj = None
        if '(' in href:
            href_ex = href.split('(')
            src = href_ex[1]
            src = src.replace('\\', '')
            src = src.replace('PC', '')
            src = src.replace('VdM', '')
            src = src.replace('(', '')
            src = src.replace(')', '')
            src = src.replace(';', '')
            src = src.replace("'", '')
            src = src.replace('"', '')
            src = src.replace(' ', '')
            media_file = self.get_oc_mediafile(src, use_as)
            if media_file is not None:
                man_obj = Manifest.objects.get(uuid=media_file.uuid)
                man_obj.exact_match = media_file.exact_match
                man_obj.href = media_file.href
                man_obj.src= media_file.src
        if man_obj is None:
            pass
            # print('Could not find media manifest object for: ' + href)
        return man_obj
    
    def get_oc_mediafile(self, src, use_as='src'):
        """ gets the related oc media file object for a an image src attribute """
        media_file = None
        if isinstance(src, str):
            if '/' in src:
                src_ex = src.split('/')
                src_img = src_ex[-1]
            else:
                src_img = src
            id_str = self.get_pc_number(src_img)
            if isinstance(id_str, str):
                if id_str not in self.media_id_manifest:
                    # ok we don't have a manifest list yet for this id_str
                    media_man_objs = Manifest.objects\
                                             .filter(item_type='media',
                                                     label__contains=id_str)\
                                             .order_by('sort')
                    self.media_id_manifest[id_str] = media_man_objs
                # self.media_src_exact = {}
                # self.media_src_rel = {}
                if src_img not in self.media_src:
                    # we haven't checked for an exact match yet
                    # for this src_img
                    m_uuids = []
                    for man_obj in self.media_id_manifest[id_str]:
                        m_uuids.append(man_obj.uuid)
                    media_files = Mediafile.objects\
                                           .filter(uuid__in=m_uuids,
                                                   file_uri__icontains=src_img,
                                                   file_type='oc-gen:thumbnail')[:1]
                    if len(media_files) > 0:
                        media_file = media_files[0]
                        media_file.exact_match = True
                        media_file.href = 0
                        media_file.src = 0
                        self.media_src[src_img] = media_file
                        new_media_src = self.media_src
                        for ch_src, check_media in self.media_src.items():
                            if ch_src != src_img and check_media is not None:
                                if check_media.uuid == media_file.uuid:
                                    # we have a non exact match in use for this
                                    # item, so remove it.
                                    new_media_src[ch_src] = None
                        self.media_src = new_media_src
                    else:
                        self.media_src[src_img] = None
                if self.media_src[src_img] is None:
                    # we don't have an exact match, so let's check for an
                    # imperfect match
                    for man_obj in self.media_id_manifest[id_str]:
                        not_exact_ok = True
                        for ch_src, check_media in self.media_src.items():
                            if src_img != ch_src and check_media is not None:
                                if check_media.uuid == man_obj.uuid:
                                    # we're already using this, so don't use it
                                    # again
                                    not_exact_ok = False
                        if not_exact_ok:
                            media_files = Mediafile.objects\
                                                   .filter(uuid=man_obj.uuid,
                                                           file_type='oc-gen:thumbnail')[:1]
                            if len(media_files) > 0:
                                media_file = media_files[0]
                                media_file.exact_match = False
                                media_file.href = 0
                                media_file.src = 0
                                self.media_src[src_img] = media_file
                media_file = self.media_src[src_img]
        if media_file is not None:
            if use_as == 'src':
                media_file.src += 1
            elif use_as == 'href':
                media_file.href += 1
            self.media_src[src_img] = media_file
        return media_file
        
    def prep_tb_entry_data(self, act_file):
        """ gets parameters from the trench book entry page """
        data = LastUpdatedOrderedDict()
        for field_key in self.field_keys:
            data[field_key] = None
        act_file = act_file.replace('.html', '')
        if '---' in act_file:
            p_ex_a = act_file.split('---')
            params_str = p_ex_a[1]
            if '--' in params_str:
                params_vals = params_str.split('--')
            else:
                params_vals = [params_str]
            for param_val in params_vals:
                val_num = None
                val_int = None
                p_v_ex = param_val.split('-')
                if len(p_v_ex) > 1:
                    key = p_v_ex[0]
                    val = p_v_ex[1]
                    try:
                        val_num = float(val)
                    except:
                        val_num = None
                    if val_num is not None:
                        try:
                            val_int = int(val_num)
                        except:
                            val_int = None
                    if val_int is not None:
                        val = val_int
                    elif val_num is not None:
                        val = val_num
                    data[key] = val
        data['file'] = act_file
        return data
    
    def get_tb_files_list(self):
        """ loads the trench book index, scrapes
            content recursively
        """
        if self.tb_files is None:
            files = self.pc.get_directory_files(self.pc.pc_directory)
            if isinstance(files, list):
                self.tb_files = []
                for act_file in files:
                    # print('check: ' + act_file)
                    if 'viewtrenchbookentry' in act_file:
                        self.tb_files.append(act_file)
        return self.tb_files
    
    def get_root_tbs_by_tbid(self):
        """ gets the root trench books by trench book ids """
        root_uuids = []
        ass_roots = Assertion.objects\
                             .filter(predicate_uuid=self.tb_id_pred)
        for ass_root in ass_roots:
            root_uuids.append(ass_root.uuid)
        root_tbs = Manifest.objects\
                           .filter(uuid__in=root_uuids)\
                           .order_by('label', 'sort')
        return root_tbs
    
    def get_part_of_manifest_objs(self, root_tb_uuid):
        """ gets and updates manifest objects for trench
            book entries that are part of a root trench book uuid
        """
        part_man_objs = []
        ass_parts = Assertion.objects\
                             .filter(uuid=root_tb_uuid,
                                     predicate_uuid=self.pred_has_part,
                                     object_type='documents')\
                             .order_by('sort')
        for ass_part in ass_parts:
            try:
                part_man_obj = Manifest.objects.get(uuid=ass_part.object_uuid)
            except:
                part_man_obj = None
            if part_man_obj is not None:
                part_man_objs.append(part_man_obj)
        return part_man_objs
    
    def get_pc_number(self, filename):
        """ gets the pc number from a media file name """
        id_str = None
        if isinstance(filename, str):
            f_len = len(filename)
            i = 0
            id_part = True
            id_str = ''
            while i < f_len:
                if id_part:
                    if filename[i].isdigit():
                        id_str += str(filename[i])
                    else:
                        id_part = False
                if id_part is False and i <= 4:
                    id_str = None
                i += 1
        return id_str
    
    def get_str_between_start_end(self, act_str, start_str, end_str):
        """ gets a string value between 1 part and another part of a string """
        output = None
        if len(start_str) < 1 and len(end_str) > 0 and end_str in act_str:
            # we want the start of a string before a delimiter
            end_parts = act_str.split(end_str)
            output = end_parts[0]
        elif len(end_str) < 1 and len(start_str) > 0 and start_str in act_str:
            # we eant the end of a string, after a delimiter
            start_parts = act_str.split(start_str)
            if len(start_parts) > 0:
                output = start_parts[1]
        elif len(start_str) > 0 and len(end_str) > 0:
            if start_str in act_str:
                act_parts = act_str.split(start_str)
                if len(act_parts) > 0:
                    act_part = act_parts[1]
                    if end_str in act_part:
                        end_parts = act_part.split(end_str)
                        output = end_parts[0]
                    else:
                        print('Cannot find end: ' + end_str + ' in it!')
            else:
                print('Cannot find start: ' + start_str + ' in it!')
        if isinstance(output, str):
            output = output.replace('\\r', '')
            output = output.replace('\\n', '')
            output = output.replace('\\t', '')
        return output
    
    
    
                