import os
import requests
from io import BytesIO
from time import sleep
from internetarchive import get_session, get_item
from django.conf import settings
from django.utils.http import urlquote, quote_plus, urlquote_plus
from opencontext_py.libs.generalapi import GeneralAPI
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.apps.entities.uri.models import URImanagement
from opencontext_py.apps.entities.entity.models import Entity
from opencontext_py.apps.ldata.linkannotations.licensing import Licensing
from opencontext_py.apps.ocitems.identifiers.models import StableIdentifer
from opencontext_py.apps.ocitems.mediafiles.models import Mediafile, ManageMediafiles
from opencontext_py.apps.ocitems.projects.models import Project
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.ocitems.ocitem.models import OCitem


class InternetArchiveMedia():
    """
    This class has useful methods for updating
    media files, particularly putting items into the
    Internet Archive           


from opencontext_py.apps.ocitems.mediafiles.models import Mediafile
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.ocitems.mediafiles.internetarchive import InternetArchiveMedia
ia_m = InternetArchiveMedia()
ia_m.noindex = False
ia_m.save_db = True
ia_m.remote_uri_sub = 'https://artiraq.org/static/opencontext/poggio-civitate/'
ia_m.local_uri_sub = 'http://127.0.0.1:8000/static/exports/poggio-civitate/'
ia_m.project_uuids.append('DF043419-F23B-41DA-7E4D-EE52AF22F92F')
ia_m.archive_image_media_items()
ia_m.errors

from opencontext_py.apps.ocitems.mediafiles.models import Mediafile
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.ocitems.mediafiles.internetarchive import InternetArchiveMedia
ia_m = InternetArchiveMedia()
ia_m.noindex = False
ia_m.save_db = True
# ia_m.remote_uri_sub = 'http://artiraq.org/static/opencontext/poggio-civitate/'
# ia_m.local_uri_sub = 'http://127.0.0.1:8000/static/exports/images-artiraq/poggio-civitate/'
ims = ia_m.get_public_image_uuids_by_size(0)
# ims = ia_m.get_public_image_uuids_by_size_temp(0)
len(ia_m.image_uuids)
ia_m.archive_image_media_items()

med_files = Mediafile.objects\
                     .filter(file_type='oc-gen:archive',
                             file_uri__startswith='http://artiraq')\
                     .exclude(file_uri__contains='merritt.cdlib.org')\
                     .order_by('-filesize')
for med_full in med_files:
    med_ia_files = Mediafile.objects.filter(uuid=med_full.uuid, file_type='oc-gen:ia-fullfile')
    for med_ia_file in med_ia_files:
        print('Make ' + med_full.file_uri + ' now ' + med_ia_file.file_uri)
        med_full.file_uri = med_ia_file.file_uri
        med_full.save()
        
        
med_files = Mediafile.objects\
                     .filter(file_type='oc-gen:fullfile',
                             file_uri__startswith='http://artiraq')\
                     .exclude(file_uri__contains='merritt.cdlib.org')\
                     .order_by('-filesize')
for med_full in med_files:
    med_ia_files = Mediafile.objects.filter(uuid=med_full.uuid, file_type='oc-gen:ia-fullfile')
    for med_ia_file in med_ia_files:
        print('Make ' + med_full.file_uri + ' now ' + med_ia_file.file_uri)
        med_full.file_uri = med_ia_file.file_uri
        med_full.save()

from opencontext_py.apps.ocitems.mediafiles.models import Mediafile
med_files = Mediafile.objects\
                     .filter(file_type='oc-gen:preview',
                             file_uri__startswith='http://www.')\
                     .exclude(file_uri__contains='merritt.cdlib.org')\
                     .order_by('-filesize')
for med_full in med_files:
    med_ia_files = Mediafile.objects.filter(uuid=med_full.uuid, file_type='oc-gen:iiif')
    for med_ia_file in med_ia_files:
        size_uri =  med_ia_file.file_uri.replace('/info.json', '/full/650,/0/default.jpg')
        print('Make ' + med_full.file_uri + ' now ' + size_uri)
        med_full.file_uri = size_uri
        med_full.save()

    """

    IA_FILE_TYPE = 'oc-gen:ia-fullfile'
    IIIF_FILE_TYPE = 'oc-gen:iiif'
    SLEEP_TIME = 1
    
    def __init__(self):
        self.root_export_dir = settings.STATIC_EXPORTS_ROOT
        self.cache_file_dir = 'internet-archive'
        # self.ia_collection = 'opensource_media'
        self.ia_collection = 'opencontext'
        self.id_prefix = 'opencontext'
        self.ia_uri_prefix = 'https://archive.org/download/'
        self.iiif_uri_prefix = 'https://iiif.archivelab.org/iiif/'
        self.session = None
        self.project_uuids = []
        self.image_uuids = []
        self.proj_licenses = {}
        self.mem_cache_entities = {}
        self.delay_before_request = self.SLEEP_TIME
        self.noindex = True
        self.save_db = False
        self.remote_uri_sub = None  # substitution for a remote uri
        self.local_uri_sub = None  # local substitution uri prefix, so no retrieval from remote
        self.pref_tiff_archive = True
        self.errors = []
    
    def archive_image_media_items(self):
        """ archives a list of media items """
        image_manifest_list = self.get_image_media_items()
        print('Starting upload of: ' + str(len(image_manifest_list)) + ' items...')
        for man_obj in image_manifest_list:
            print('Working on: ' + man_obj.slug + ' uuid: ' + man_obj.uuid)
            # self.update_image_metadata(man_obj)
            self.archive_image(man_obj)
    
    def get_public_image_uuids_by_size_temp(self, file_size):
        """ gets uuids for full-files over a certain size """
        file_types = ['oc-gen:fullfile',
                      'oc-gen:archive']
        ok_uuid_list = []
        public_project_uuids = self.get_public_projects()
        if isinstance(self.remote_uri_sub, str):
            if file_size > 0:
                med_files = Mediafile.objects\
                                     .filter(file_type__in=file_types,
                                             project_uuid__in=public_project_uuids,
                                             file_uri__startswith=self.remote_uri_sub,
                                             filesize__gt=file_size)\
                                      .exclude(file_uri__contains='merritt.cdlib.org')\
                                      .order_by('-filesize')
            else:
                 med_files = Mediafile.objects\
                                     .filter(file_type__in=file_types,
                                             project_uuid__in=public_project_uuids,
                                             file_uri__startswith=self.remote_uri_sub)\
                                      .exclude(file_uri__contains='merritt.cdlib.org')\
                                      .order_by('-filesize')
        else:
            if file_size > 0:
                med_files = Mediafile.objects\
                                     .filter(file_type__in=file_types,
                                             project_uuid__in=public_project_uuids,
                                             filesize__gt=file_size)\
                                      .exclude(file_uri__contains='merritt.cdlib.org')\
                                      .order_by('-filesize')
            else:
                 med_files = Mediafile.objects\
                                     .filter(file_type__in=file_types,
                                             project_uuid__in=public_project_uuids)\
                                      .exclude(file_uri__contains='merritt.cdlib.org')\
                                      .order_by('-filesize')
        for med_file in med_files:
            ch_iiif = Mediafile.objects\
                               .filter(uuid=med_file.uuid,
                                       file_type=self.IIIF_FILE_TYPE)[:1]
            if len(ch_iiif) < 1:
                # OK! we're good to make a IIIF file type for this item
                self.image_uuids.append(med_file.uuid)
        return self.image_uuids
    
    def get_public_image_uuids_by_size(self, file_size):
        """ gets uuids for full-files over a certain size """
        ok_uuid_list = []
        public_project_uuids = self.get_public_projects()
        med_files = Mediafile.objects\
                             .filter(file_type='oc-gen:fullfile',
                                     project_uuid__in=public_project_uuids,
                                     filesize__gt=file_size)\
                             .exclude(file_uri__contains='/www.alexandriaarchive.org/')\
                             .order_by('-filesize')
        for med_file in med_files:
            ch_iiif = Mediafile.objects\
                               .filter(uuid=med_file.uuid,
                                       file_type=self.IIIF_FILE_TYPE)[:1]
            if len(ch_iiif) < 1:
                # OK! we're good to make a IIIF file type for this item
                self.image_uuids.append(med_file.uuid)
        return self.image_uuids
    
    def get_public_projects(self):
        """ makes a list of project_uuids for public projects """
        public_project_uuids = []
        projs = Project.objects.all()
        for proj in projs:
            public = True
            if proj.view_group_id is not None:
                if proj.view_group_id > 0:
                    public = False
            if public:
                public_project_uuids.append(proj.uuid)
        return public_project_uuids
    
    def get_image_media_items(self):
        """ gets list of image media not yet in the Internet Archive """
        image_manifest_list = []
        if len(self.image_uuids) > 0: 
            man_images = Manifest.objects\
                                 .filter(item_type='media',
                                         class_uri='oc-gen:image',
                                         uuid__in=self.image_uuids)
        elif len(self.project_uuids) > 0: 
            man_images = Manifest.objects\
                                 .filter(item_type='media',
                                         # class_uri='oc-gen:image',
                                         project_uuid__in=self.project_uuids)\
                                 .order_by('sort')
        else:
            man_images = Manifest.objects\
                                 .filter(item_type='media',
                                         class_uri='oc-gen:image')\
                                 .order_by('sort')
        print('Checking media items: ' + str(len(man_images)))
        for man_obj in man_images:
            ch_iiif = Mediafile.objects\
                               .filter(uuid=man_obj.uuid,
                                       file_type=self.IIIF_FILE_TYPE)[:1]
            if len(ch_iiif) < 1:
                # OK! we're good to make a IIIF file type for this item
                image_manifest_list.append(man_obj)
        return image_manifest_list

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
                dir = self.set_check_directory(self.cache_file_dir)
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

    def make_ia_image_uri(self, item_id, file_name):
        """ makes a URI for the Internet Archive full version of the image """
        uri = self.ia_uri_prefix + item_id + '/' + file_name
        return uri

    def make_ia_iiif_image_uri(self, item_id, file_name):
        """ makes a URI for the iiif version of the image """
        suffix = 'jpg'
        if '.' in file_name:
            ex_f = file_name.split('.')
            suffix = ex_f[-1]
        uri = self.iiif_uri_prefix + item_id + '/info.json'
        return uri
    
    def add_file_to_archive(self, man_obj, file_name, cache_dir=None):
        """ adds another file to an existing archive item. No metadata modification
        """
        ia_file_uri = None
        json_ld = self.make_oc_item(man_obj)
        if isinstance(json_ld, dict):
            # cache the remote file locally to upload it
            item_id = self.id_prefix + '-' + json_ld['slug']
            if not isinstance(cache_dir, str):
                cache_dir = self.cache_file_dir
            dir = self.set_check_directory(cache_dir)
            path = os.path.join(dir, file_name)
            if not os.path.exists(path):
                print('Cannot find the cached file: ' +  path + ' !')
            else:
                sleep(self.delay_before_request)
                print('Ready to upload: ' + file_name)
                # start an internet archive session
                s = self.start_ia_session()
                # get or make an item
                item = get_item(item_id,
                                archive_session=s,
                                debug=True)
                # now upload file
                if not isinstance(cache_dir, str):
                    cache_dir = self.cache_file_dir
                dir = self.set_check_directory(cache_dir)
                path = os.path.join(dir, file_name)
                r = item.upload_file(path,
                                     key=file_name,
                                     metadata=metadata)
                # set the uri for the media item just uploaded
                if r.status_code == requests.codes.ok or self.save_db:
                    ia_file_uri = self.make_ia_image_uri(item_id, file_name)
        return ia_file_uri

    def make_metadata_dict(self, json_ld, man_obj):
        """ makes the metadata dict for the current item """
        metadata = LastUpdatedOrderedDict()
        metadata['uri'] = json_ld['id']
        metadata['title'] = self.make_title(json_ld, man_obj)
        metadata['partof'] = self.make_partof_metadata(json_ld, man_obj)
        metadata['publisher'] = 'Open Context (http://opencontext.org)'
        metadata['description'] = self.make_simple_description(json_ld, man_obj)
        metadata['licenseurl'] = self.get_license_uri(json_ld, man_obj)
        if self.noindex:
            # add a noindex key so it does not show up in
            metadata['noindex'] = True
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
    
    def get_cache_full_file(self, json_ld, man_obj):
        """ gets and caches the fill file, saving temporarily to a local directory """
        file_name = None
        slug = man_obj.slug
        file_uri = self.get_archive_fileuri(json_ld)
        if isinstance(file_uri, str):
            # we have a file
            if isinstance(self.local_uri_sub, str) and isinstance(self.remote_uri_sub, str):
                # get a local copy of the file, not a remote copy
                file_uri = file_uri.replace(self.remote_uri_sub, self.local_uri_sub)
                if 'https://' in self.remote_uri_sub:
                    # so we also replace the https or http version of the remote with a local
                    alt_remote_sub = self.remote_uri_sub.replace('https://', 'http://')
                    file_uri = file_uri.replace(alt_remote_sub, self.local_uri_sub)
            if '.' in file_uri:
                file_ex = file_uri.split('.')
                file_name = slug + '.' + file_ex[-1]
            else:
                file_name = slug
            file_ok = self.get_cache_remote_file_content(file_name, file_uri)
            if file_ok is False:
                file_name = False
                error_msg = 'UUID: ' + man_obj.uuid + ' file_uri: ' + file_uri
                error_msg += ' file caching error.'
                self.errors.append(error_msg)
        return file_name
            
    def get_full_fileuri(self, json_ld):
        """ gets the full file uri """
        file_uri = None
        if 'oc-gen:has-files' in json_ld:
            for f_obj in json_ld['oc-gen:has-files']:
                if f_obj['type'] == 'oc-gen:fullfile':
                    file_uri = f_obj['id']
                    break
        return file_uri
    
    def get_archive_fileuri(self, json_ld):
        """ gets the full file uri """
        file_uri = None
        if 'oc-gen:has-files' in json_ld:
            for f_obj in json_ld['oc-gen:has-files']:
                if self.pref_tiff_archive:
                    if f_obj['type'] == 'oc-gen:archive':
                        file_uri = f_obj['id']
                        break
            if file_uri is None:
                # no TIFF archive file found, so use the full-file
                for f_obj in json_ld['oc-gen:has-files']:
                    if f_obj['type'] == 'oc-gen:fullfile':
                        file_uri = f_obj['id']
                        break
        return file_uri
                
    def get_cache_remote_file_content(self, file_name, file_uri):
        """ gets the content of a remote file,
            saves it to cache with the filename 'file_name'
        """
        ok = False
        dir = self.set_check_directory(self.cache_file_dir)
        path = os.path.join(dir, file_name)
        if os.path.exists(path):
            # the file already exists, no need to download it again
            print('Already cached: ' + path)
            ok = True
        else:
            print('Cannot find: ' + path)
            print('Need to download: ' + file_uri)
            if not isinstance(self.local_uri_sub, str):
                # only delay if we're not looking locally for the file
                sleep(self.delay_before_request)
            r = requests.get(file_uri, stream=True)
            if r.status_code == 200:
                with open(path, 'wb') as f:
                    for chunk in r.iter_content(1024):
                        f.write(chunk)
                f.close()
                ok = True
            else:
                # try with different capitalization
                if '.JPG' in file_uri:
                    new_file_uri = file_uri.replace('.JPG', '.jpg')
                elif '.jpg' in file_uri:
                    new_file_uri = file_uri.replace('.jpg', '.JPG')
                else:
                    new_file_uri = None
                if new_file_uri is not None:
                    print('Now trying with different capitalization: ' + new_file_uri)
                    if not isinstance(self.local_uri_sub, str):
                        # only delay if we're not looking locally for the file
                        sleep(self.delay_before_request)
                    r = requests.get(new_file_uri, stream=True)
                    if r.status_code == 200:
                        with open(path, 'wb') as f:
                            for chunk in r.iter_content(1024):
                                f.write(chunk)
                        f.close()
                        ok = True
        return ok
    
    def make_oc_item(self, man_obj):
        """ makes an open context item for the image,
            so as to gather up all the needed metadata
        """
        ocitem = OCitem()
        ocitem.get_item(man_obj.uuid)
        json_ld = ocitem.json_ld
        return json_ld 

    def make_title(self, json_ld, man_obj):
        """ makes a title from the item label and the project label """
        if 'dc-terms:title' in json_ld:
            title = json_ld['dc-terms:title']
        else:
            title = man_obj.label
            project_ent = self.get_entity(man_obj.project_uuid)
            if project_ent is not False:
                title += ' an image from the data publication '
                title += '"' + project_ent.label + '"'
        return title

    def make_simple_description(self, json_ld, man_obj):
        """ makes a simple description for metadata documentation of the resource """
        
        uri = json_ld['id']
        project_ent = self.get_entity(man_obj.project_uuid)
        description = '<div>Image: "' + man_obj.label + '" '
        description += ', published by Open Context at: '
        description += '<a href="' + uri + '">' + uri + '</a>'
        if project_ent is not False:
            description += '; as part of the '
            description += '"<a href="' + project_ent.uri + '">' + project_ent.label
            description += '</a>" data publication.'
        description += '</div>'
        return description
    
    def get_license_uri(self, json_ld, man_obj):
        """ gets the copyright license for the resource """
        license_uri = None
        if 'dc-terms:license' in json_ld:
            license_uri = json_ld['dc-terms:license'][0]['id']
        else:
            lic_obj = Licensing()
            license_uri = lic_obj.get_license_by_uuid(man_obj.uuid)
            if not isinstance(license_uri, str):
                if man_obj.project_uuid in self.proj_licenses:
                    # use the project default license, as kept in a dict
                    license_uri = self.proj_licenses[man_obj.project_uuid]
                else:
                    # get the license for the project, and cache it in memory
                    lic_obj = Licensing()
                    license_uri = lic_obj.get_license(man_obj.project_uuid,
                                                      man_obj.project_uuid)
                    self.proj_licenses[man_obj.project_uuid] = license_uri
        return license_uri
    
    def make_partof_metadata(self, json_ld, man_obj):
        """ makes the partOf metadata """
        if 'dc-terms:isPartOf' in json_ld:
            part_of = json_ld['dc-terms:isPartOf'][0]['id']
        else:
            project_ent = self.get_entity(man_obj.project_uuid)
            if project_ent is not False:
                part_of = project_ent.uri
            else:
                part_of = 'http://opencontext.org'
        return part_of
    
    def test_upload(self):
        s = self.start_ia_session()
        item = get_item('opencontext-test-item',
                        archive_session=s,
                        debug=True)
        r = item.upload('https://artiraq.org/static/opencontext/abydos-looting/full/fig001.jpg')
        return r
    
    def start_ia_session(self):
        """ starts an internet archive session """
        config = dict(s3=dict(acccess=settings.INTERNET_ARCHIVE_ACCESS_KEY,
                              secret=settings.INTERNET_ARCHIVE_SECRET_KEY))
        s = get_session(config=config,
                        debug=True)
        s.access_key = settings.INTERNET_ARCHIVE_ACCESS_KEY
        s.secret_key = settings.INTERNET_ARCHIVE_SECRET_KEY
        return s

    def get_entity(self, identifier):
        """ gets entities, but checkes first if they are in memory """
        output = False
        if identifier in self.mem_cache_entities:
            output = self.mem_cache_entities[identifier]
        else:
            ent = Entity()
            found = ent.dereference(identifier)
            if found:
                output = ent
                self.mem_cache_entities[identifier] = ent
        return output
    
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
    
    def get_directory_files(self, act_dir):
        """ Gets a list of files from a directory """
        files = False
        path = self.set_check_directory(act_dir)
        if os.path.exists(path):
            for dirpath, dirnames, filenames in os.walk(path):
                files = sorted(filenames)
        else:
            print('Cannot find: ' + path)
        return files