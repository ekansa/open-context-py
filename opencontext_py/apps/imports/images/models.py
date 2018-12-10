import os, sys, shutil
import codecs
from PIL import Image, ImageFile, ImageFilter
from django.db import models
from django.conf import settings
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.ocitems.geospace.models import Geospace
from opencontext_py.apps.ocitems.events.models import Event


class ImageImport():
    """ Imports images

from opencontext_py.apps.imports.images.models import ImageImport
ii = ImageImport()
ii.force_dashes = True
ii.project_uuid = 'DF043419-F23B-41DA-7E4D-EE52AF22F92F'
ii.gaussian_blur_radius = 2
ii.make_image_versions('giza-seeds')
ii.walk_directory('OB_Illustrations')
ii.make_thumbnail('', 'PhotoID027.jpg')
    """

    def __init__(self):
        self.root_export_dir = settings.STATIC_EXPORTS_ROOT
        self.project_uuid = False
        self.source_id = False
        self.class_uri = False
        self.gaussian_blur_radius = None
        self.thumbnail_width_height = 150
        self.preview_width = 650
        self.full_dir = 'full'
        self.preview_dir = 'preview'
        self.thumbs_dir = 'thumbs'
        self.force_dashes = False  # make sure the new filenames have dashes, not spaces or underscores
        self.errors = []
        self.max_image_size = 35000000000
        self.single_size_limit = 250000000  # break up if the image has more than this number of pixel

    def make_image_versions(self, src):
        """ Copies a directory structure
            and makes thumbnail and preview files
        """
        src_dir = self.set_check_directory(src)
        print('Working on :' + src_dir)
        new_root_dir = self.set_check_directory('copy-' + src)
        new_dirs = [self.full_dir,
                    self.preview_dir,
                    self.thumbs_dir]
        for new_dir in new_dirs:
            dst_dir = new_root_dir + new_dir
            if not os.path.exists(dst_dir):
                for dirpath, dirnames, filenames in os.walk(src_dir):
                    trim_dirpath = dirpath[len(src_dir):]
                    if len(trim_dirpath) > 1:
                        if trim_dirpath[0] == '/' or trim_dirpath[0] == '\\':
                            trim_dirpath = dirpath[1+len(src_dir):]
                    """
                    act_dir = os.path.join(dst_dir,
                                           dirpath[1+len(src_dir):])
                    """
                    act_dir = os.path.join(dst_dir, trim_dirpath)
                    os.mkdir(act_dir)
                    for filename in filenames:
                        src_file = os.path.join(dirpath, filename)
                        print('Working on src_file: ' + src_file)
                        if self.force_dashes:
                            # make sure the new filenames have dashes, not spaces or underscores
                            filename = filename.replace(' ', '-')
                            filename = filename.replace('_', '-')
                        if new_dir == self.full_dir:
                            new_file = os.path.join(act_dir, filename)
                            # its the full size file, just copy it without modification
                            print('Copy full: ' + new_file)
                            shutil.copy2(src_file, new_file)
                        else:
                            # we need to modify the image
                            file_no_ext = os.path.splitext(filename)[0]
                            filename_jpg = file_no_ext + '.jpg'
                            new_file = os.path.join(act_dir, filename_jpg)
                            try:
                                Image.MAX_IMAGE_PIXELS = self.max_image_size
                                im = Image.open(src_file)
                            except:
                                print('Cannot use as image: ' + src_file)
                                im = False
                            if im is not False:
                                ratio = 1  # default to same size
                                if new_dir == self.preview_dir:
                                    print('Make preview: ' + new_file)
                                    self.make_preview_file(src_file, new_file)
                                elif new_dir == self.thumbs_dir:
                                    print('Make thumbnail: ' + new_file)
                                    self.make_thumbnail_file(src_file, new_file)

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
                Image.MAX_IMAGE_PIXELS = self.max_image_size
                ImageFile.LOAD_TRUNCATED_IMAGES = True
                try:
                    im = Image.open(src_file)
                    im.LOAD_TRUNCATED_IMAGES = True
                except:
                    print('Cannot use as image: ' + src_file)
                    im = False
                if im is not False:
                    print('Source width: ' + str(im.width) + ', height: ' + str(im.height))
                    if (im.width * im.height) >= self.single_size_limit:
                        pass
                        # the image is too big to for 32 bit python
                    if isinstance(self.gaussian_blur_radius, int) \
                       and im.mode != "RGB":
                        # use a gaussian blur first!
                        print('Converting and blurring image mode: ' + im.mode)
                        im_rgba = im.convert("RGB")
                        im = None
                        blurred_image = im_rgba.filter(ImageFilter.GaussianBlur(radius=self.gaussian_blur_radius))
                        im = blurred_image
                        blurred_image = None
                if im is not False:
                    ratio = 1  # default to same size
                    if im.width > self.preview_width:
                        new_width = self.preview_width
                        ratio = im.width / self.preview_width
                    else:
                        new_width = im.width
                    new_height = int(round((im.height * ratio), 0))
                    size = (new_width, new_height)
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
                            im.convert("RGB")
                            im.thumbnail(size, Image.ANTIALIAS)
                            try:
                                im.save(new_file, "JPEG", quality=100)
                                output = new_file
                            except:
                                print('cannot save the preview file: ' + new_file)
                    im.close()
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
                Image.MAX_IMAGE_PIXELS = self.max_image_size
                ImageFile.LOAD_TRUNCATED_IMAGES = True
                try:
                    im = Image.open(src_file)
                    im.LOAD_TRUNCATED_IMAGES = True
                except:
                    print('Cannot use as image: ' + src_file)
                    im = False
                if im is not False:
                    print('Source width: ' + str(im.width) + ', height: ' + str(im.height))
                    if (im.width * im.height) >= self.single_size_limit:
                        pass
                        # the image is too big to for 32 bit python
                    if isinstance(self.gaussian_blur_radius, int) \
                       and im.mode != "RGB":
                        # use a gaussian blur first!
                        print('Converting and blurring image mode: ' + im.mode)
                        im_rgba = im.convert("RGB")
                        im = None
                        blurred_image = im_rgba.filter(ImageFilter.GaussianBlur(radius=self.gaussian_blur_radius))
                        im = blurred_image
                        blurred_image = None
                if im is not False:
                    size = (self.thumbnail_width_height,
                            self.thumbnail_width_height)
                    rescale_ok = False
                    rescale_ok = True
                    """
                    try:
                        im.load()
                        rescale_ok = True
                    except IOError:
                        rescale_ok = False
                        print('Problem rescaling image for: ' + new_file)
                        self.errors.append(new_file)
                    """
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
                            im.convert("RGB")
                            im.thumbnail(size, Image.ANTIALIAS)
                            try:
                                im.save(new_file, "JPEG", quality=100)
                                output = new_file
                            except:
                                print('cannot save the preview file: ' + new_file)
                    im.close()
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
