import fnmatch
from time import sleep
import uuid as GenUUID
import os, sys, shutil
import codecs
from PIL import Image, ImageFile
from django.db import models
from django.db.models import Q
from django.conf import settings
from opencontext_py.apps.imports.records.models import ImportCell
from opencontext_py.apps.imports.fields.models import ImportField 

class KoboImages():
    """ Prepares images from a kobotool box dataset for
        import.
        
        This means moving them from their nested directory
        into an easier managed directory, and updating filenames if
        desired.
        

from opencontext_py.apps.imports.kobotoolbox.images import KoboImages
kbi = KoboImages()
kbi.consider_uuid_field = False
kbi.overwrite_versions = False
kbi.origin_dir = 'catalog-v-1-3_2017_08_28_19_57_58'
kbi.destination_dir = '2017-media'
kbi.new_old_field_nums = [
    {'old': 143, 'new': 144},
    {'old': 154, 'new': 155}
]
kbi.source_id = 'ref:2333310354954'
kbi.make_new_images()

    """

    def __init__(self):
        self.root_export_dir = settings.STATIC_EXPORTS_ROOT
        self.origin_dir = ''
        self.destination_dir = ''
        self.source_id = ''
        self.consider_uuid_field = True
        self.uuid_field_num = None
        self.thumbnail_width_height = 150
        self.preview_width = 650
        self.full_dir = 'full'
        self.preview_dir = 'preview'
        self.thumbs_dir = 'thumbs'
        self.overwrite_versions = False
        self.new_old_field_nums = []
        
    def make_new_images(self):
        """ makes new image versions with new file names
            by walking the directory to find image files
        """
        if len(self.new_old_field_nums) > 0:
            # we know the field
            dirs = self.get_make_directories()
            if dirs is not None:
                for dirpath, dirnames, filenames in os.walk(dirs['src']):
                    for filename in filenames:
                        src_file = os.path.join(dirpath, filename)
                        src_rec = self.get_source_rec_from_dirfile(dirpath,
                                                                   filename)
                        if isinstance(src_rec, ImportCell):
                            new_file_name = self.get_new_filename_from_src_rec(src_rec)
                            self.make_image_versions_src_and_new_file(dirs,
                                                                      src_file,
                                                                      new_file_name)
                        else:
                            print('No DB record for: ' + filename + ' from: ' + dirpath)

    def get_new_filename_from_src_rec(self, src_rec):
        """ gets a new filename associated with a src_rec (ImportCell object)
            Defaults to the current filename
        """
        filename = src_rec.record
        for new_old_dict in self.new_old_field_nums:
            if new_old_dict['old'] == src_rec.field_num:
                # the field_num matches the old. see if we have
                # a new field to relate
                if 'new' in new_old_dict:
                    if isinstance(new_old_dict['new'], int):
                        new_recs = ImportCell.objects\
                                             .filter(source_id=self.source_id,
                                                     field_num=new_old_dict['new'],
                                                     row_num=src_rec.row_num)[:1]
                        if len(new_recs) > 0:
                            filename = new_recs[0].record
                            if len(filename) < 3:
                                filename = src_rec.record
        return filename 
        
    def get_source_rec_from_dirfile(self,
                                    dirpath,
                                    filename):
        """ gets a row number for a filename in a dirpath. validates
            a uuid if a uuid field exists
        """
        output_rec = None
        old_file_field_nums = []
        for new_old_dict in self.new_old_field_nums:
            old_file_field_nums.append(new_old_dict['old'])
        file_recs = ImportCell.objects\
                              .filter(source_id=self.source_id,
                                      field_num__in=old_file_field_nums,
                                      record=filename)
        for file_rec in file_recs:
            rec_uuid = self.get_uuid_for_a_row(file_rec.row_num)
            if rec_uuid is not None:
                if rec_uuid in dirpath:
                    # the uuid is present in the dipath
                    output_rec = file_rec
                    break
        if output_rec is None and not isinstance(self.uuid_field_num, int):
            # we didn't find the row_num, and we don't have a UUID field
            # so only match if there's only 1 record that matches this
            # filename
            if len(file_recs) == 1:
                output_rec = file_recs[0]
        return output_rec
                    
    def get_uuid_for_a_row(self, act_row):
        """ gets a uuid string for a row in the imported table """
        uuid = None
        self.get_uuid_field_num()
        if isinstance(self.uuid_field_num, int):
            # OK there is a UUID field
            uuid_recs = ImportCell.objects\
                                  .filter(source_id=self.source_id,
                                          field_num=self.uuid_field_num,
                                          row_num=act_row)[:1]
            if len(uuid_recs) > 0:
                uuid = uuid_recs[0].record
        return uuid

    def get_uuid_field_num(self):
        """ gets the uuid field num if it is None """
        if self.uuid_field_num is None and self.consider_uuid_field:
            label = '_uuid'
            uuid_fields = ImportField.objects\
                                     .filter(Q(label=label) | Q(ref_name=label) | Q(ref_orig_name=label),
                                             source_id=self.source_id)[:1]
            if len(uuid_fields) > 0:
                self.uuid_field_num = uuid_fields[0].field_num
            else:
                self.uuid_field_num = False
        if self.consider_uuid_field is False:
            self.uuid_field_num = None
    
    def make_image_versions_from_files(self, dirs, old_file_name, new_file_name):
        """ makes image versions in the appropriate directories
             with a new file name and an old file name
        """
        src_file = os.path.join(dirs['src'], old_file_name)
        self.make_image_versions_src_and_new_file(dirs,
                                                  src_file,
                                                  new_file_name)
    
    def make_image_versions_src_and_new_file(self,
                                             dirs,
                                             src_file,
                                             new_file_name):
        if os.path.exists(src_file):
            full_file = os.path.join(dirs['full'], new_file_name)
            prev_file = os.path.join(dirs['preview'], new_file_name)
            thumb_file = os.path.join(dirs['thumbs'], new_file_name)
            if self.overwrite_versions or not os.path.exists(full_file):
                shutil.copy2(src_file, full_file)
            if self.overwrite_versions or not os.path.exists(prev_file):
                self.make_preview_file(src_file, prev_file)
            if self.overwrite_versions or not os.path.exists(thumb_file):
                self.make_thumbnail_file(src_file, thumb_file)

    def get_make_directories(self):
        """ gets and make directories for the preparing files """
        if len(self.origin_dir) > 0 and len(self.destination_dir) > 0:
            dirs = {
                'src': self.set_check_directory(self.origin_dir),
                'dest':  self.set_check_directory(self.destination_dir),
                'full': self.set_check_directory(self.destination_dir + '/full'),
                'preview': self.set_check_directory(self.destination_dir + '/preview'),
                'thumbs': self.set_check_directory(self.destination_dir + '/thumbs')
            }
        else:
            dirs = None
        return dirs
    
    def make_preview_file(self, src_file, new_file):
        """ Makes preview images. This preserves the orginal
            aspect ratio. The height can be greater than the width,
            so we're not just going to use the thumbnail
            method
        """
        output = False
        png = False
        if '.png' in src_file or '.PNG' in src_file:
            png = True
        if src_file != new_file:
            if os.path.exists(src_file):
                # print('Getting: ' + src_file)
                ImageFile.LOAD_TRUNCATED_IMAGES = True
                try:
                    im = Image.open(src_file)
                    im.LOAD_TRUNCATED_IMAGES = True
                except:
                    print('Cannot use as image: ' + src_file)
                    im = False
                if im is not False:
                    ratio = 1  # default to same size
                    if im.width > self.preview_width:
                        new_width = self.preview_width
                        ratio = im.width / self.preview_width
                    else:
                        new_width = im.width
                    new_neight = int(round((im.height * ratio), 0))
                    size = (new_width, new_neight)
                    rescale_ok = False
                    try:
                        im.load()
                        rescale_ok = True
                    except IOError:
                        rescale_ok = False
                        print('Problem rescaling image for: ' + new_file)
                        self.errors.append(new_file)
                    if rescale_ok:
                        if png:
                            im.thumbnail(size, Image.ANTIALIAS)
                            background = Image.new("RGB", im.size, (255, 255, 255))
                            try:
                                background.paste(im, mask=im.split()[3]) # 3 is the alpha channel
                                background.save(new_file, "JPEG", quality=100)
                                output = new_file
                            except:
                                png = False
                                print('cannot save the preview file: ' + new_file)
                            del background
                        if png is False:
                            im.thumbnail(size, Image.ANTIALIAS)
                            try:
                                im.save(new_file, "JPEG", quality=100)
                                output = new_file
                            except:
                                print('cannot save the preview file: ' + new_file)
                    del im
        return output

    def make_thumbnail_file(self, src_file, new_file):
        """ This makes a thumbnail file. It is a little more
            simple, since it uses the default thumbnail method,
            meaning it has a max height and a max width
        """
        output = False
        png = False
        if '.png' in src_file or '.PNG' in src_file:
            png = True
        if src_file != new_file:
            if os.path.exists(src_file):
                # print('Getting: ' + src_file)
                ImageFile.LOAD_TRUNCATED_IMAGES = True
                try:
                    im = Image.open(src_file)
                    im.LOAD_TRUNCATED_IMAGES = True
                except:
                    print('Cannot use as image: ' + src_file)
                    im = False
                if im is not False:
                    size = (self.thumbnail_width_height,
                            self.thumbnail_width_height)
                    rescale_ok = False
                    try:
                        im.load()
                        rescale_ok = True
                    except IOError:
                        rescale_ok = False
                        print('Problem rescaling image for: ' + new_file)
                        self.errors.append(new_file)
                    if rescale_ok:
                        if png:
                            im.thumbnail(size, Image.ANTIALIAS)
                            background = Image.new("RGB", im.size, (255, 255, 255))
                            try:
                                background.paste(im, mask=im.split()[3]) # 3 is the alpha channel
                                background.save(new_file, "JPEG", quality=100)
                                output = new_file
                            except:
                                png = False
                                print('cannot save the preview file: ' + new_file)
                            del background
                        if png is False:
                            im.thumbnail(size, Image.ANTIALIAS)
                            try:
                                im.save(new_file, "JPEG", quality=100)
                                output = new_file
                            except:
                                print('cannot save the preview file: ' + new_file)
                    del im
        return output

    def copy_dir_not_files(self, src, dst):
        """ Copies only a directory structure """
        src_dir = self.set_check_directory(src)
        dst_dir = self.root_export_dir + dst
        if not os.path.exists(dst_dir):
            for dirpath, dirnames, filenames in os.walk(src_dir):
                act_dir = os.path.join(dst_dir,
                                       dirpath[1+len(src_dir):])
                os.mkdir(act_dir)
                for filename in filenames:
                    src_file = os.path.join(dirpath, filename)
                    new_file = os.path.join(act_dir, filename)

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
