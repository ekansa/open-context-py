import re
import os, sys, shutil
import codecs
import uuid as GenUUID
from time import sleep
from django.db import models
from django.conf import settings
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


class PoggioCivImages():
    """ Class for linking pictures to database records


from opencontext_py.apps.imports.poggiociv.images import PoggioCivImages
pci = PoggioCivImages()
pci.associate_files()



    """

    def __init__(self):
        self.act_import_dir = False
        self.pc = PoggioCiv() 
        self.image_directory = 'copy-pc-mag-photos/full'
        self.root_export_dir = settings.STATIC_EXPORTS_ROOT
        self.project_uuid = 'DF043419-F23B-41DA-7E4D-EE52AF22F92F'
        self.source_id = 'image-link-b-new'
        self.source_ids = ['image-link-new', 'image-link-b-new']
        self.class_uri = False
        self.sub_counts = {}
        self.full_uri_prefix = 'https://artiraq.org/static/opencontext/poggio-civitate/to-2017/full/'
        self.prev_uri_prefix = 'https://artiraq.org/static/opencontext/poggio-civitate/to-2017/preview/'
        self.thumb_uri_prefix = 'https://artiraq.org/static/opencontext/poggio-civitate/to-2017/thumbs/'
        self.obs_num = 1
        self.obs_node = '#obs-' + str(self.obs_num)
        self.pred_image_type = 'B8556EAA-CF52-446B-39FA-AE4798C13A6B'
        self.type_photo = '983b0ba6-0b6a-4b87-94ff-82880e09ecfd'   
    
    def associate_files(self):
        """ gets the pc number from a file name """
        files = self.get_file_list()
        files.sort()
        for filename in files:
            filename = filename.strip()
            id_str = self.get_pc_number(filename)
            if isinstance(id_str, str):
                man_objs = Manifest.objects\
                                   .filter(label=id_str,
                                           item_type='subjects')[:1]
                if len(man_objs) > 0:
                    subj_uuid = man_objs[0].uuid
                    if subj_uuid not in self.sub_counts:
                        self.sub_counts[subj_uuid] = 10
                    else:
                        self.sub_counts[subj_uuid] += 1
                    self.create_media_and_links(subj_uuid, id_str, filename)
                    prev_subj = subj_uuid
    
    def create_media_and_links(self, subj_uuid, id_str, filename):
        """ create database records for the image, associate
            with the subject
        """
        file_label = self.make_image_label(id_str, filename)
        med_man_objs = Manifest.objects\
                               .filter(label=file_label,
                                       source_id=self.source_id,
                                       item_type='media')[:1]
        filename = filename.replace(' ', '-')
        filename = filename.replace('_', '-')
        med_files = Mediafile.objects\
                             .filter(file_uri__icontains=filename)[:1]
        # med_man_objs = [1, 2, 3]
        if len(med_man_objs) < 1 and len(med_files) < 1:
            # now make another media item
            media_uuid = str(GenUUID.uuid4())
            print('Making on: ' + file_label + ' (' + media_uuid +')')
            new_man = Manifest()
            new_man.uuid = media_uuid
            new_man.project_uuid = self.project_uuid
            new_man.source_id = self.source_id
            new_man.item_type = 'media'
            new_man.repo = ''
            new_man.class_uri = 'oc-gen:image'
            new_man.label = file_label
            new_man.des_predicate_uuid = ''
            new_man.views = 0
            new_man.save()
            self.make_media_file_obj(media_uuid,
                                     'oc-gen:fullfile',
                                     (self.full_uri_prefix + filename))
            self.make_media_file_obj(media_uuid,
                                     'oc-gen:preview',
                                     (self.prev_uri_prefix + filename))
            self.make_media_file_obj(media_uuid,
                                     'oc-gen:thumbnail',
                                     (self.thumb_uri_prefix + filename))
            self.add_media_assertions(subj_uuid, media_uuid)

    def add_media_assertions(self, subj_uuid, media_uuid):
        """ add assertions relating the media resource to the subject,
            adding a little metadata
        """
        #update old assertions for media
        if self.sub_counts[subj_uuid] < 2:
            # only update it once, not it we've seen it already
            m_links = Assertion.objects\
                               .filter(uuid=subj_uuid,
                                       object_type='media')\
                               .exclude(source_id__in=self.source_ids)
            for m_link in m_links:
                m_link.sort = m_link.sort + 10
                m_link.save()
        # make a new linking assertion
        new_ass = Assertion()
        new_ass.uuid = subj_uuid
        new_ass.subject_type = 'subjects'
        new_ass.project_uuid = self.project_uuid
        new_ass.source_id = self.source_id
        new_ass.obs_node = self.obs_node
        new_ass.obs_num = self.obs_num
        new_ass.sort = self.sub_counts[subj_uuid]
        new_ass.visibility = 1
        new_ass.predicate_uuid = 'oc-3'
        new_ass.object_type = 'media'
        new_ass.object_uuid = media_uuid
        new_ass.save()
        # make a new description assertion
        new_ass = Assertion()
        new_ass.uuid = media_uuid
        new_ass.subject_type = 'media'
        new_ass.project_uuid = self.project_uuid
        new_ass.source_id = self.source_id
        new_ass.obs_node = self.obs_node
        new_ass.obs_num = self.obs_num
        new_ass.sort = 1
        new_ass.visibility = 1
        new_ass.predicate_uuid = self.pred_image_type
        new_ass.object_type = 'types'
        new_ass.object_uuid = self.type_photo
        new_ass.save()
        
        
    def make_image_label(self, id_str, filename):
        """ makes the label for an image """
        fix_dict = {
            'PROFILE': 'Profile',
            'FRONT': 'Front',
            'HEAD': 'Head',
            'BACK': 'Back',
            'BOTTOM': 'Bottom',
            'DETAIL': 'Detail',
            'TOP': 'Top',
            'EDGE': 'Edge',
            'INSCRIPTION': 'Inscription',
            'BASE': 'Base',
        }
        id_num = id_str.replace('PC ', '')
        file_ex = filename.split('.')
        file_label = file_ex[0]
        for key, val in fix_dict.items():
            file_label = file_label.replace(key, (val + ' '))
        file_label = file_label.replace(id_num, (id_num + ' '))
        file_label = 'Photo ' + file_label
        file_label = file_label.strip()
        file_label = file_label.replace('  ', ' ')
        return file_label

    def make_media_file_obj(self, media_uuid, file_type, file_uri):
        """ makes a new media file object in the database """
        sleep(.1)
        mf = Mediafile()
        mf.uuid = media_uuid
        mf.project_uuid = self.project_uuid
        mf.source_id = self.source_id
        mf.file_type = file_type
        mf.file_uri = file_uri
        mf.filesize = 0
        mf.mime_type_ur = ''
        ok = True
        try:
            mf.save()
        except:
            ok = False
        return ok
    
    def get_pc_number(self, filename):
        """ gets the pc number from a file name
            Example: '19660027.jpg'
        """
        id_str = None
        if isinstance(filename, str):
            f_len = len(filename)
            if f_len > 8:
                f_len = 8
            i = 0
            id_part = True
            id_str = 'PC '
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
    
    def get_file_list(self):
        """ get a list of imag files """
        files = []
        src_dir = self.set_check_directory(self.image_directory)
        for dirpath, dirnames, filenames in os.walk(src_dir):
            for filename in filenames:
                files.append(filename)
        return files
    
    def set_check_directory(self, act_dir):
        """ Prepares a directory to find image files """
        output = False
        if len(act_dir) > 0:
            full_dir = self.root_export_dir + act_dir + '/'
        else:
            full_dir = self.root_export_dir
        if os.path.exists(full_dir):
            output = full_dir
        return output
    
    
    
                