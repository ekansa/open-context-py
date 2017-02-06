import os
import csv
import json
import requests
import roman
import codecs
from unidecode import unidecode
from io import BytesIO
from time import sleep
from internetarchive import get_session, get_item
from django.conf import settings
from django.utils.http import urlquote, quote_plus, urlquote_plus
from opencontext_py.libs.generalapi import GeneralAPI
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.apps.entities.uri.models import URImanagement
from opencontext_py.apps.imports.records.models import ImportCell


class InternetArchiveIrma():
    """
    This class has useful methods archving National Parks service IRMA data into the
    Internet Archive

from opencontext_py.apps.ocitems.mediafiles.iairma import InternetArchiveIrma
ia_irma = InternetArchiveIrma()
ia_irma.get_cache_archive_records()


    """


    SLEEP_TIME = 5
    
    def __init__(self):
        self.root_export_dir = settings.STATIC_EXPORTS_ROOT
        self.cach_file_dir = 'internet-archive-irma'
        # self.ia_collection = 'opensource_media'
        self.ia_collection = 'opencontext'
        self.id_prefix = 'nps-irma'
        self.ia_uri_prefix = 'https://archive.org/download/'
        self.session = None
        self.delay_before_request = self.SLEEP_TIME
        self.errors = []
        self.source_id = 'ref:1551357748608'
        self.fields = {
            1: 'page_url',
            2: 'json_url',
            3: 'json_str',
            4: 'code',
            5: 'type',
            6: 'cite',
            7: 'title'
        }
    
    def get_cache_archive_records(self):
        """ gets and caches archive record files """
        items = self.get_archive_records()
        # make the column names for the CSV output
        first_row = []
        for key, val in items[0].items():
            if key not in ['json_str', 'json_files']:
                first_row.append(key)
        file_dict = items[0]['json_files'][0]
        for fkey, fval in file_dict.items():
            first_row.append('File-' + fkey)
        first_row.append('File-Downloaded')
        # now make the rows for the CSV file
        row_items = []
        for item in items:
            i = 0
            pre_row_item = LastUpdatedOrderedDict()
            for key in first_row:
                if key in item:
                    pre_row_item[key] = item[key]
                else:
                    pre_row_item[key] = ''
            if isinstance(item['json_files'], list):
                for file_dict in item['json_files']:
                    i += 1
                    file_uri = file_dict['Url']
                    if 'FileDescription' in file_dict:
                        file_name = file_dict['FileDescription']
                    else:
                        file_name = item['code'] + '-' + str(i)
                    if not isinstance(file_name, str):
                        file_name = item['code'] + '-' + str(i)
                    ok = self.get_cache_remote_file_content(file_name, file_uri)
                    row_item = pre_row_item
                    for fkey, fval in file_dict.items():
                        fkey = 'File-' + fkey
                        row_item[fkey] = fval
                    row_item['File-Downloaded'] = ok
                    row_items.append(row_item)
            if i == 0:
                # no file rows created, so only add the pre_row_item
                row_items.append(pre_row_item)
        dir = self.set_check_directory(self.cach_file_dir)
        path = os.path.join(dir, 'irma-manifest.csv')       
        f = codecs.open(path, 'w', encoding='utf-8')
        writer = csv.writer(f, dialect=csv.excel, quoting=csv.QUOTE_ALL)
        writer.writerow(first_row)
        for row_item in row_items:
            row = []
            for key, val in row_item.items():
                row.append(val)
            writer.writerow(row)
        f.closed
                        
    
    def get_archive_records(self):
        """ gets list of items to archive """
        recs = ImportCell.objects\
                         .filter(source_id=self.source_id)\
                         .order_by('row_num', 'field_num')
        row_nums = []
        items = []
        last_row = 0
        for rec in recs:
            if rec.row_num not in row_nums:
                act_row = rec.row_num
                row_nums.append(act_row)
                item = LastUpdatedOrderedDict()
                item_recs = ImportCell.objects\
                         .filter(source_id=self.source_id,
                                 row_num=act_row)\
                         .order_by('field_num')
                for item_rec in item_recs:
                    rec = str(item_rec.record)
                    key = self.fields[item_rec.field_num]
                    item[key] = rec
                    if key == 'json_str':
                        item['json_files'] = json.loads(rec)
                items.append(item)
        return items
              
    def update_image_metadata(self, man_obj, json_ld=None, item=None):
        """ updates an items metadata """
        meta_ok = False
        if json_ld is None:
            json_ld = self.make_oc_item(man_obj)
        if isinstance(json_ld, dict):
            # cache the remote file locally to upload it
            item_id = self.id_prefix + '-' + json_ld['slug']
            if item is None:
                s = self.start_ia_session()
                # get or make an item
                item = get_item(item_id,
                                archive_session=s,
                                debug=True)
            # now add the metadata
            print('Update metadata for ' + item_id)
            meta_ok = self.update_item_metadata(json_ld,
                                                man_obj,
                                                item_id,
                                                item)
        return meta_ok
    
    def make_item_metadata(self):
        """ makes a dict of item metadata to start the item """
        item_metadata = {'collection': self.ia_collection}
        return item_metadata

    def archive_image(self, man_obj):
        """ does the work of archiving an image,
            1. gets the image from a remote server, makes a local file
            2. makes metadata
            3. saves the file
        """
        ok = False
        json_ld = self.make_oc_item(man_obj)
        if isinstance(json_ld, dict):
            # cache the remote file locally to upload it
            item_id = self.id_prefix + '-' + json_ld['slug']
            file_name = self.get_cache_full_file(json_ld, man_obj)
            if not isinstance(file_name, str):
                print('Failed to cache file!')
            else:
                sleep(self.delay_before_request)
                print('Ready to upload: ' + file_name)
                # start an internet archive session
                s = self.start_ia_session()
                # get or make an item
                item = get_item(item_id,
                                archive_session=s,
                                debug=True)
                # now make some metadata for the first item to be uploaded
                metadata = self.make_metadata_dict(json_ld, man_obj)
                metadata['collection'] = self.ia_collection
                metadata['mediatype'] = 'image'
                # now upload the image file
                dir = self.set_check_directory(self.cach_file_dir)
                path = os.path.join(dir, file_name)
                r = item.upload_file(path,
                                     key=file_name,
                                     metadata=metadata)
                # set the uri for the media item just uploaded
                if r.status_code == requests.codes.ok or self.save_db:
                    ia_file_uri = self.make_ia_image_uri(item_id, file_name)
                    iiif_file_uri = self.make_ia_iiif_image_uri(item_id, file_name)
                    # now save the link to the IA full file
                    mf = Mediafile()
                    mf.uuid = man_obj.uuid
                    mf.project_uuid = man_obj.project_uuid
                    mf.source_id = man_obj.source_id
                    mf.file_type = self.IA_FILE_TYPE
                    mf.file_uri = ia_file_uri
                    mf.filesize = 0
                    try:
                        mf.save()
                        ok = True
                    except:
                        error_msg = 'UUID: ' + man_obj.uuid + ' item_id: ' + item_id
                        error_msg += ' Cannot save oc_mediafile for ia-fullfile'
                        self.errors.append(error_msg)
                        ok = False
                    # save the link to the IIIF version
                    mf_b = Mediafile()
                    mf_b.uuid = man_obj.uuid
                    mf_b.project_uuid = man_obj.project_uuid
                    mf_b.source_id = man_obj.source_id
                    mf_b.file_type = self.IIIF_FILE_TYPE
                    mf_b.file_uri = iiif_file_uri
                    mf_b.filesize = 0
                    try:
                        mf_b.save()
                        ok = True
                    except:
                        error_msg = 'UUID: ' + man_obj.uuid + ' item_id: ' + item_id
                        error_msg += ' Cannot save oc_mediafile for ia-iiif'
                        self.errors.append(error_msg)
                        ok = False
        return ok


    def make_metadata_dict(self, item_id, title, cite):
        """ makes the metadata dict for the current item """
        metadata = LastUpdatedOrderedDict()
        metadata['uri'] = json_ld['id']
        metadata['title'] = self.make_title(json_ld, man_obj)
        metadata['partof'] = self.make_partof_metadata(json_ld, man_obj)
        metadata['publisher'] = 'Open Context (http://opencontext.org)'
        metadata['description'] = self.make_simple_description(json_ld, man_obj)
        metadata['licenseurl'] = self.get_license_uri(json_ld, man_obj)
        return metadata
    
    def update_item_metadata(self, json_ld, man_obj, item_id, item=None):
        """ creates and updates the item metadata """
        ok = False
        metadata = self.make_metadata_dict(json_ld, man_obj)
        if item is None:
            s = self.start_ia_session()
            item = get_item(item_id,
                            archive_session=s,
                            debug=True)
        r = item.modify_metadata(metadata)
        print(str(r))
        if r.status_code == requests.codes.ok:
            ok = True
        else:
            ok = False
            error_msg = 'UUID: ' + man_obj.uuid + ' item_id: ' + item_id
            error_msg += ' Metadata update error: ' + str(r.status_code)
            self.errors.append(error_msg)
        return ok
                
    def get_cache_remote_file_content(self, file_name, file_uri):
        """ gets the content of a remote file,
            saves it to cache with the filename 'file_name'
        """
        ok = False
        dir = self.set_check_directory(self.cach_file_dir)
        path = os.path.join(dir, file_name)
        pr_file_uri = str(unidecode(file_uri))
        pr_path = str(unidecode(path))
        if os.path.exists(path):
            # the file already exists, no need to download it again
            print('Already cached: ' + pr_path)
            ok = True
        else:
            ok = False
        if ok is None:
            print('Cannot find: ' + pr_path)
            print('Need to download: ' + pr_file_uri)
            sleep(self.delay_before_request)
            try:
                ok = False
                r = requests.get(file_uri, stream=True, timeout=5)
                if r.status_code == 200:
                    with open(path, 'wb') as f:
                        for chunk in r.iter_content(1024):
                            f.write(chunk)
                    f.close()
                    ok = True
            except:
                ok = False
            if ok is False:
                # try again
                new_file_uri = file_uri
                print('2nd try to download: ' + pr_file_uri)
                sleep(self.delay_before_request * 2)
                try:
                    r = requests.get(new_file_uri, stream=True, timeout=5)
                    if r.status_code == 200:
                        with open(path, 'wb') as f:
                            for chunk in r.iter_content(1024):
                                f.write(chunk)
                        f.close()
                        ok = True
                except:
                    ok = False
        return ok

    def make_simple_description(self, item):
        """ makes a simple description for metadata documentation of the resource """
        
        des = '<div>'
        des += '<h2>' + item['title'] + '</h2>'
        des += '<h4>' + item['type'] + ' (Item ID: ' + item['code'] + ')</h4>'
        des += '<h4>National Parks Service (NPS) - IRMA Resource</h4>'
        des += '<p>Originally published by the NPS and hosted at: '
        des += '<a id="nps-irma-item-url" href="' + item['page_url'] + '">' + item['page_url'] + '</a>'
        des += '</p>'
        if isinstance(item['json_files'], list):
            des += '<p>This item includes the following files, with JSON-formatted metadata obtained from:</p>'
            des += '<p><a id="nps-irma-json-file-metadata" href="' + item['json_url'] + '">' + item['json_url']  + '</a>'
            des += '</p><br/>'
            for file_item in item['json_files']:
                 des += '<ul style="margin-top: 20px;">'
                 for key, val in file_item.items():
                    des +=  self.make_file_meta_html(key, file_item)
                 des += '</ul>'
            des += '<br/><br/>'
        des += '</div>'
        return des
    
    def make_file_meta_html(self, file_item, key):
        """ makes html for file metadata """
        if key in file_item:
            content = str(file_item[key]).strip()
            if len(content) > 0:
                if len(content) > 7:
                    if content[0:7] == 'http://' or \
                       content[0:8] == 'https://':
                        content = '<a href="' + content + '">' + content + '</a>'
                html = '<li><em>' + key + '</em>: ' + content + '</li>'
            else:
                html = ''
        else:
            html = ''
        return html
    
    def get_license_uri(self, json_ld, man_obj):
        """ gets the copyright license for the resource """
        license_uri = 'https://creativecommons.org/publicdomain/zero/1.0/'
        return license_uri
    
    def start_ia_session(self):
        """ starts an internet archive session """
        config = dict(s3=dict(acccess=settings.INTERNET_ARCHIVE_ACCESS_KEY,
                              secret=settings.INTERNET_ARCHIVE_SECRET_KEY))
        s = get_session(config=config,
                        debug=True)
        s.access_key = settings.INTERNET_ARCHIVE_ACCESS_KEY
        s.secret_key = settings.INTERNET_ARCHIVE_SECRET_KEY
        return s
    
    def check_exists(self, file_name, act_dir):
        """ checks to see if a file exists """
        path = self.prep_directory(act_dir)
        dir_file = path + file_name
        if os.path.exists(dir_file):
            output = True
        else:
            # print('Cannot find: ' + dir_file)
            output = False
        return output

    def set_check_directory(self, act_dir):
        """ Prepares a directory to find import GeoJSON files """
        output = False
        if len(act_dir) > 0:
            full_dir = self.root_export_dir + act_dir + '/'
        else:
            full_dir = self.root_export_dir
        if not os.path.exists(full_dir):
            os.makedirs(full_dir)
        if os.path.exists(full_dir):
            output = full_dir
        return output