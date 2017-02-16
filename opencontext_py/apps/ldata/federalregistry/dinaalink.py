import re
import json
import os
import codecs
import requests
import feedparser
import hashlib
from time import sleep
from django.conf import settings
from django.db import connection
from django.db import models
from django.utils.http import urlquote, quote_plus, urlquote_plus
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.libs.generalapi import GeneralAPI
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.ocitems.assertions.models import Assertion
from opencontext_py.apps.ocitems.strings.models import OCstring
from opencontext_py.apps.ldata.federalregistry.api import FederalRegistryAPI
from opencontext_py.apps.ldata.linkannotations.models import LinkAnnotation
from opencontext_py.apps.ldata.linkannotations.manage import LinkAnnoManagement
from opencontext_py.apps.ldata.linkentities.models import LinkEntity
from opencontext_py.apps.indexer.reindex import SolrReIndex


class FedDinaaLink():
    """ Interacts with the Federal Registry API
        Fo relate DINAA trinomials with
        Federal Registry documents
        
from opencontext_py.apps.ldata.federalregistry.dinaalink import FedDinaaLink
from opencontext_py.apps.indexer.reindex import SolrReIndex
fed_link = FedDinaaLink()
url = 'http://127.0.0.1:8000/subjects-search/United+States.json?response=uuid&rows=2000&linked=dinaa-cross-ref&proj=52-digital-index-of-north-american-archaeology-dinaa&prop=dc-terms-isreferencedby'
sri = SolrReIndex()
fed_link.uuids = sri.get_uuids_oc_url(url)
# fed_link.project_uuids = ['F9970276-8636-478D-A3F0-08CC7EFEAD4F', '5F2D4172-D823-4F7F-D3A8-4BD68ED1369D']
fed_link.get_save_dinaa_linked_docs()
fed_link.add_parent_links()
fed_link.make_dinaa_link_assertions()
fed_link.index_linked_dinaa_sites()

    """

    FEDERAL_REG_URI = 'http://www.federalregister.gov/'
    FEDERAL_REG_LABEL = 'Federal Register'
    DC_TERMS_REF_BY = 'dc-terms:isReferencedBy'
    
    def __init__(self):
        self.request_error = False
        self.request_url = False
        self.results = False
        self.project_uuids = None
        self.uuids = None
        self.source_id = 'fed-reg-api-lookup'
        self.all_docs_lists_key = 'all-document-list'
        self.dinaa_matches_key = 'dinaa-matches'
        self.checked_docs_key = 'all-docs-checked'
        self.tri_predicate = 'a5c308c3-52f8-4076-b315-d3258d485572'
        self.matched_trinomials = []
    
    def add_parent_links(self):
        """ makes the federal registry a "parent" item
            of documents from the federal registry
        """
        self.make_fed_reg_vocab_entity()
        les = LinkEntity.objects\
                        .filter(vocab_uri=self.FEDERAL_REG_URI)\
                        .exclude(uri='http://www.federalregister.gov/')
        for le in les:
            lam = LinkAnnoManagement()
            parent_uri = 'http://www.federalregister.gov/'
            child_uri = le.uri
            print('Make hiearchy: ' + child_uri)
            lam.add_skos_hierarachy(parent_uri, child_uri)
    
    def index_linked_dinaa_sites(self):
        """ indexes DINAA sites liked to the federal
            registry
        """
        uuids = []
        links = LinkAnnotation.objects\
                              .filter(source_id=self.source_id,
                                      subject_type='subjects')
        for link in links:
            if link.subject not in uuids:
                uuids.append(link.subject)
        # reindex those links
        sri = SolrReIndex()
        sri.reindex_uuids(uuids)
    
    def make_dinaa_link_assertions(self):
        """ makes assertions to relate DINAA URIs with federal
            registry documents
        """
        self.make_fed_reg_vocab_entity()
        fed_api = FederalRegistryAPI()
        search_key_list = fed_api.get_list_cached_keyword_searches()
        dinaa_matches = fed_api.get_dict_from_file(self.dinaa_matches_key)
        for s_key in search_key_list:
            s_json = fed_api.get_dict_from_file(s_key)
            if 'results' in s_json:
                for match in dinaa_matches:
                    for s_result in s_json['results']:
                        if s_result['document_number'] == match['doc']:
                            print('Found match for ' + match['doc'])
                            man_obj = False
                            try:
                                man_obj = Manifest.objects.get(uuid=match['uuid'])
                            except Manifest.DoesNotExist:
                                man_obj = False
                            if man_obj is not False:
                                fed_uri = s_result['html_url']
                                le_check = False
                                try:
                                    le_check = LinkEntity.objects.get(uri=fed_uri)
                                except LinkEntity.DoesNotExist:
                                    le_check = False
                                if le_check is False:
                                    print('Saving entity: ' + s_result['title'])
                                    title = s_result['title']
                                    if len(title) > 175:
                                        title = title[0:175] + '...'
                                    le = LinkEntity()
                                    le.uri = fed_uri
                                    le.label = title
                                    le.alt_label = s_result['document_number']
                                    le.vocab_uri = self.FEDERAL_REG_URI
                                    le.ent_type = 'instance'
                                    le.slug = 'fed-reg-docs-' + s_result['document_number']
                                    le.save()
                                # Now save the link annotation
                                print('Adding ref link to ' + man_obj.label)
                                la = LinkAnnotation()
                                la.subject = man_obj.uuid
                                la.subject_type = man_obj.item_type
                                la.project_uuid = man_obj.project_uuid
                                la.source_id = self.source_id
                                la.predicate_uri = self.DC_TERMS_REF_BY
                                la.object_uri = fed_uri
                                try:
                                    la.save()
                                except:
                                    pass
    
    def make_fed_reg_vocab_entity(self):
        """ makes a vocabulary entity for the federal registry """
        try:
            le_check = LinkEntity.objects.get(uri=self.FEDERAL_REG_URI)
        except LinkEntity.DoesNotExist:
            le_check = False
        if le_check is False:
            le = LinkEntity()
            le.uri = self.FEDERAL_REG_URI
            le.label = self.FEDERAL_REG_LABEL
            le.alt_label = self.FEDERAL_REG_LABEL
            le.vocab_uri = self.FEDERAL_REG_URI
            le.ent_type = 'vocabulary'
            le.slug = 'fed-reg'
            le.save()
    
    def get_save_dinaa_linked_docs(self):
        """ finds DINAA trinomials in cached federal documents """
        fed_api = FederalRegistryAPI()
        checked_docs = fed_api.get_dict_from_file(self.checked_docs_key)
        if not isinstance(checked_docs, list):
            checked_docs = []
        lists = fed_api.get_dict_from_file(self.all_docs_lists_key)
        trinomials = self.get_dinaa_trinomials()
        print('Reviewing ' + str(len(trinomials)) + ' trinomials.')
        i = 0
        doc_cnt = len(lists['raw'])
        url_list = lists['raw']
        url_list.sort()
        for raw_url in url_list:
            i += 1
            text = None
            url_ex = raw_url.split('/')
            file_name = url_ex[-1]
            if file_name not in checked_docs:
                # have not looked at this yet
                exists = fed_api.check_exists(file_name, fed_api.working_doc_dir)
                if exists:
                    text = fed_api.get_string_from_file(file_name, fed_api.working_doc_dir)
                else:
                    # try to get it remotely again
                    # print('Try again for remote file: ' + raw_url)
                    exists = fed_api.get_cache_raw_doc_text(raw_url)
                    if exists:
                        text = fed_api.get_string_from_file(file_name, fed_api.working_doc_dir)
                if isinstance(text, str):
                    print('Checking [' + str(i) + ' of ' + str(doc_cnt) + ']: ' + file_name)
                    for row in trinomials:
                        if row['trinomial'] in text and len(row['trinomial']) >= 4:
                            print('Possible match for: ' + row['trinomial'])
                            # pad with spaces before and after, so we do not get false hits on partially matching
                            # trinomials
                            sp_trinomial = ' ' + row['trinomial'] + ' '
                            # replace all line breaks, and non alphanumeric charachers with spaces
                            sub_text = re.sub(r"\r", " ", text)
                            sub_text = re.sub(r"\n", " ", sub_text)
                            sub_text = re.sub('[^0-9a-zA-Z ]+', ' ',  sub_text)
                            if sp_trinomial in sub_text:
                                row['doc'] = file_name.replace('.txt', '')
                                self.matched_trinomials.append(row)
                                print('! Found ' + row['trinomial'])
                                print('! Found matches: ' + str(len(self.matched_trinomials)))
                                # a = 1/0
                                fed_api.save_serialized_json(self.dinaa_matches_key,
                                                             self.matched_trinomials)
                    # save a record we checked this document
                    checked_docs.append(file_name)
                    fed_api.save_serialized_json(self.checked_docs_key,
                                                 checked_docs)
    
    def get_dinaa_trinomials(self):
        """ gets trinomials for DINAA """
        if self.project_uuids is not None:
            # limit by a project
            proj_sql = self.add_or_field_sql('a.project_uuid', self.project_uuids)
            query = ('SELECT a.uuid AS uuid, s.content AS trinomial '
                     'FROM oc_assertions AS a '
                     'JOIN oc_strings AS s ON a.object_uuid = s.uuid '
                     'WHERE a.predicate_uuid = \'' + self.tri_predicate + '\' '
                     'AND ' + proj_sql + ' ; ')
        elif self.uuids is not None:
            uuids_sql = self.add_or_field_sql('a.uuid', self.uuids)
            query = ('SELECT a.uuid AS uuid, s.content AS trinomial '
                     'FROM oc_assertions AS a '
                     'JOIN oc_strings AS s ON a.object_uuid = s.uuid '
                     'WHERE a.predicate_uuid = \'' + self.tri_predicate + '\' '
                     'AND ' + uuids_sql + ' ; ')
        else:
            query = ('SELECT a.uuid AS uuid, s.content AS trinomial '
                     'FROM oc_assertions AS a '
                     'JOIN oc_strings AS s ON a.object_uuid = s.uuid '
                     'WHERE a.predicate_uuid = \'' + self.tri_predicate + '\'; ')
        cursor = connection.cursor()
        cursor.execute(query)
        rows = self.dictfetchall(cursor)
        return rows
    
    def add_or_field_sql(self, field, or_list):
        """ makes a string for an or term in sql """
        if not isinstance(or_list, list):
            or_list = [or_list]
        sql = '('
        or_term = field + ' ='
        for or_item in or_list:
             sql += or_term + ' \'' + or_item + '\' '
             or_term = ' OR ' + field + ' ='
        sql += ') '
        return sql
    
    def dictfetchall(self, cursor):
        """ Return all rows from a cursor as a dict """
        columns = [col[0] for col in cursor.description]
        return [
            dict(zip(columns, row))
            for row in cursor.fetchall()
        ]