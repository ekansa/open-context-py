import fnmatch
from time import sleep
import uuid as GenUUID
import os, sys, shutil
import codecs
from PIL import Image, ImageFile
from django.db import models
from django.conf import settings
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.ocitems.mediafiles.models import Mediafile
from opencontext_py.apps.imports.records.models import ImportCell
from opencontext_py.apps.ocitems.assertions.models import Assertion
from opencontext_py.apps.imports.poggiociv.tbentries import PoggioCivTrenchBookEntries

class PoggioCivTrenchBookImages():
    """ Imports images

from opencontext_py.apps.imports.poggiociv.tbimages import PoggioCivTrenchBookImages
pctbi = PoggioCivTrenchBookImages()
pctbi.project_uuid = 'DF043419-F23B-41DA-7E4D-EE52AF22F92F'
pctbi.process_tb_roots_and_parts()
pctbi.make_image_versions('pc-mag-photos')


from opencontext_py.apps.ocitems.assertions.models import Assertion
tb_asses = Assertion.objects\
                    .filter(item_type='documents',
                            source_id='ref:2273537509089',
                            object_type='media')
for tb_ass in tb_asses:
    tb_ppl = Assertion.objects\
                      .filter(uuid=tb_ass.uuid,
                              object_type='persons')
    for tb_p in tb_ppl:
        m_p = tb_p
        m_p.hash_id = None
        m_p.source_id = 'ref:2273537509089'
        m_p.uuid = tb_ass.object_uuid
        m_p.subject_type = tb_ass.object_type
        try:
            m_p.save()
        except:
            pass


    """

    def __init__(self):
        self.root_export_dir = settings.STATIC_EXPORTS_ROOT
        self.origin_dir = 'trenchbookimages'
        self.used_dir = 'tb-scans-2017'
        self.project_uuid = 'DF043419-F23B-41DA-7E4D-EE52AF22F92F'
        self.source_id = 'tb-scans-2017'
        self.class_uri = 'oc-gen:image'
        self.thumbnail_width_height = 150
        self.preview_width = 650
        self.full_dir = 'full'
        self.preview_dir = 'preview'
        self.thumbs_dir = 'thumbs'
        self.errors = []
        self.pctb = PoggioCivTrenchBookEntries()
        self.pred_tb_id = 'fa50506c-d1f0-4798-84b2-a7a48c0b4c74'
        self.pred_has_part = 'BD384F1F-FB29-4A9D-7ACA-D8F6B4AF0AF9'
        self.tb_img_source_id = 'ref:1778641593891'
        self.base_url = 'https://artiraq.org/static/opencontext/poggio-civitate/tb-scans-2017/'

    def process_tb_roots_and_parts(self):
        """ process trench book roots and parts """
        dirs = self.make_directories()
        root_tbs = self.get_root_tbs_by_tbid()
        for root_tb_uuid, tb_id in root_tbs.items():
            parts = self.get_update_part_of_manifest_objs(root_tb_uuid,
                                                          tb_id)
            for tb_part in parts:
                ass_rel_media = Assertion.objects\
                                         .filter(uuid=tb_part.uuid,
                                                 object_type='media')[:1]
                if len(ass_rel_media) < 1:
                    # print('-----------------------------------')
                    print('Find TB scan for: ' + tb_part.label + ' ' + tb_part.uuid)
                    page_range = self.pctb.get_page_range_from_tb_entry_label(tb_part.label)
                    # print('Page range: ' + str(page_range))
                    imp_rows = ImportCell.objects\
                                         .filter(source_id=self.tb_img_source_id,
                                                 field_num=1,
                                                 record=tb_id)
                    rows = []
                    for imp_row in imp_rows:
                        rows.append(imp_row.row_num)
                    imp_files = ImportCell.objects\
                                          .filter(source_id=self.tb_img_source_id,
                                                  field_num=4,
                                                  row_num__in=rows)
                    for imp_file in imp_files:
                        im_p_range = self.get_image_page_range_from_filename(imp_file.record)
                        # print('Check TB scan ' + str(im_p_range) + ' with : ' + tb_part.label)
                        if len(im_p_range) > 0 and len(page_range) > 0:
                            if (min(im_p_range) >= min(page_range) \
                               and max(im_p_range) <= max(page_range)) \
                               or \
                               (min(im_p_range) == min(page_range)) \
                               or \
                               (min(im_p_range) == max(page_range)) \
                               or \
                               (max(im_p_range) == min(page_range)) \
                               or \
                               (max(im_p_range) == max(page_range)):
                                # print('Found matching scan: ' + imp_file.record)
                                full_file = os.path.join(dirs['full'], imp_file.record)
                                if not os.path.exists(full_file):
                                    print('Need to prepare: ' + imp_file.record)
                                    files_prepped = self.make_in_use_tb_files(dirs,
                                                                              imp_file)
                                if os.path.exists(full_file):
                                    pass
                                    print('Make and link: ' + imp_file.record + ' with : ' + tb_part.label)
                                    self.make_link_tb_media(root_tb_uuid,
                                                            tb_part,
                                                            im_p_range,
                                                            imp_file)
                                else:
                                    print('Cannot find: ' + full_file)
                    # print('-----------------------------------')
    
    def make_link_tb_media(self, root_tb_uuid, tb_part, im_p_range, imp_file):
        """ makes and links a tb scan media resource """
        tb_scan_label = self.make_tb_scan_media_label(tb_part.label,
                                                      im_p_range)
        exists_tbs = Manifest.objects\
                             .filter(label=tb_scan_label,
                                     item_type='media')[:1]
        if len(exists_tbs) < 1:
            # this item doesn't exist yet, so make it.
            print('New scan label: ' + tb_scan_label)
            scan_uuid = str(GenUUID.uuid4())
            new_man = Manifest()
            new_man.uuid = scan_uuid
            new_man.project_uuid = self.project_uuid
            new_man.source_id = self.source_id
            new_man.item_type = 'media'
            new_man.repo = ''
            new_man.class_uri = self.class_uri
            new_man.label = tb_scan_label
            new_man.des_predicate_uuid = ''
            new_man.views = 0
            new_man.save()
            self.make_media_file(scan_uuid,
                                 'oc-gen:fullfile',
                                 'full',
                                 imp_file.record)
            self.make_media_file(scan_uuid,
                                 'oc-gen:preview',
                                 'preview',
                                 imp_file.record)
            self.make_media_file(scan_uuid,
                                 'oc-gen:thumbnail',
                                 'preview',
                                 imp_file.record)
        else:
            print('Media Image already exists: ' + exists_tbs[0].label )
            scan_uuid = exists_tbs[0].uuid
        self.make_media_links(scan_uuid,
                              root_tb_uuid,
                              tb_part,
                              im_p_range)
    
    def make_media_links(self, scan_uuid, root_tb_uuid, tb_part, im_p_range):
        """ makes linking relationships for the media item """
        sub_asses = Assertion.objects\
                             .filter(subject_type='subjects',
                                     object_uuid=root_tb_uuid)[:1]
        if len(sub_asses) > 0:
            subject_uuid = sub_asses[0].uuid
            try:
                new_ass = Assertion()
                new_ass.uuid = subject_uuid
                new_ass.subject_type = 'subjects'
                new_ass.project_uuid = self.project_uuid
                new_ass.source_id = self.source_id
                new_ass.obs_node = '#obs-1'
                new_ass.obs_num = 1
                new_ass.sort = 1
                new_ass.visibility = 1
                new_ass.predicate_uuid = 'oc-3'
                new_ass.object_uuid = scan_uuid
                new_ass.object_type = 'media'
                new_ass.save()
                new_add = True
            except:
                new_add = False
        try:
            new_ass = Assertion()
            new_ass.uuid = tb_part.uuid
            new_ass.subject_type = tb_part.item_type
            new_ass.project_uuid = self.project_uuid
            new_ass.source_id = self.source_id
            new_ass.obs_node = '#obs-1'
            new_ass.obs_num = 1
            new_ass.sort = 1
            new_ass.visibility = 1
            new_ass.predicate_uuid = 'oc-3'
            new_ass.object_uuid = scan_uuid
            new_ass.object_type = 'media'
            new_ass.save()
            new_add = True
        except:
            new_add = False
        try:
            new_ass = Assertion()
            new_ass.uuid = scan_uuid
            new_ass.subject_type = 'media'
            new_ass.project_uuid = self.project_uuid
            new_ass.source_id = self.source_id
            new_ass.obs_node = '#obs-1'
            new_ass.obs_num = 1
            new_ass.sort = 1
            new_ass.visibility = 1
            new_ass.predicate_uuid = 'oc-3'
            new_ass.object_uuid = tb_part.item_type
            new_ass.object_type = 'media'
            new_ass.save()
            new_add = True
        except:
            new_add = False
        try:
            # trench book scan image type
            new_ass = Assertion()
            new_ass.uuid = scan_uuid
            new_ass.subject_type = 'media'
            new_ass.project_uuid = self.project_uuid
            new_ass.source_id = self.source_id
            new_ass.obs_node = '#obs-1'
            new_ass.obs_num = 1
            new_ass.sort = 1
            new_ass.visibility = 1
            new_ass.predicate_uuid = 'B8556EAA-CF52-446B-39FA-AE4798C13A6B'
            new_ass.object_uuid = '6623B3D2-4A74-4B0B-6DDE-54802FCBF732'
            new_ass.object_type = 'types'
            new_ass.save()
            new_add = True
        except:
            new_add = False
            
    
    def make_media_file(self, scan_uuid, file_type, url_dir, filename):
        """ makes a media file for a uuid, of the appropriate file_type
            directory and file name
        """
        sleep(.3)
        file_uri = self.base_url + url_dir + '/' + filename
        mf = Mediafile()
        mf.uuid = scan_uuid
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
    
    def make_in_use_tb_files(self, dirs, imp_file):
        """ makes an image file that is in use """
        ok = False
        use_row = imp_file.row_num
        imp_same_files = ImportCell.objects\
                                   .filter(source_id=self.tb_img_source_id,
                                           field_num=4,
                                           record=imp_file.record)
        if len(imp_same_files) > 1:
            # we have multiple files of the same name, so try to privilage the
            # non cropped version
            rows = []
            for imp_same_file in imp_same_files:
                rows.append(imp_same_file.row_num)
            imp_check_dirs = ImportCell.objects\
                                       .filter(source_id=self.tb_img_source_id,
                                               field_num=2,
                                               row_num__in=rows)
            act_row = None
            for imp_check_dir in imp_check_dirs:
                if act_row is None or imp_check_dir.record != 'uncropped':
                    # prioritize a verion that's NOT in the uncropped dir
                    act_row = imp_check_dir.row_num
        imp_dirs = ImportCell.objects\
                             .filter(source_id=self.tb_img_source_id,
                                     field_num=2,
                                     row_num=use_row)[:1]
        imp_ofiles = ImportCell.objects\
                               .filter(source_id=self.tb_img_source_id,
                                       field_num=3,
                                       row_num=use_row)[:1]
        if len(imp_dirs) > 0 and len(imp_ofiles) > 0:
            src_file = dirs['src'] + imp_dirs[0].record + '/' + imp_ofiles[0].record
            if not os.path.exists(src_file):
                fuzzy_name = imp_ofiles[0].record.replace('.JPG', '*.JPG')
                fuzzy_found = False
                for dirpath, dirnames, filenames in os.walk(dirs['src']):
                    for filename in filenames:
                        if fnmatch.fnmatch(filename, fuzzy_name ):
                            f_check = filename.replace('.JPG', '')
                            f_check = f_check.replace('.jpg', '')
                            if not f_check[-1].isdigit():
                                # make sure we're not matching against something
                                # that has a number, otherwise we might have a common
                                # page number
                                src_file = os.path.join(dirpath, filename)
                                print('Found by FUZZY MATCH:' + filename)
                                fuzzy_found = True
                                break
                    if fuzzy_found:
                        break
            if os.path.exists(src_file):
                ok = True
                print('Prepare: ' + src_file)
                full_file = os.path.join(dirs['full'], imp_file.record)
                prev_file = os.path.join(dirs['preview'], imp_file.record)
                thumb_file = os.path.join(dirs['thumbs'], imp_file.record)
                # its the full size file, just copy it without modification
                if not os.path.exists(full_file):
                    shutil.copy2(src_file, full_file)
                if not os.path.exists(prev_file):
                    self.make_preview_file(src_file, prev_file)
                if not os.path.exists(thumb_file):
                    self.make_thumbnail_file(src_file, thumb_file)
            else:
                ok = False
                print('CANNOT FIND: ' + src_file)
        return ok

    def make_directories(self):
        """ make directories for the preparing files """
        dirs = {
            'src': self.set_check_directory(self.origin_dir),
            'dest':  self.set_check_directory(self.used_dir),
            'full': self.set_check_directory(self.used_dir + '/full'),
            'preview': self.set_check_directory(self.used_dir + '/preview'),
            'thumbs': self.set_check_directory(self.used_dir + '/thumbs')
        }
        return dirs
    
    def get_update_part_of_manifest_objs(self, root_tb_uuid, tb_id):
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
                print('DAMN!! Cannot find: ' + str(ass_part.object_uuid) + ' in ' + str(ass_part.uuid))
                ass_part.delete()
            if part_man_obj is not None:
                data = part_man_obj.sup_json
                do_change = False
                if 'tb_id' not in data:
                    data['tb_id'] = int(float(tb_id))
                    do_change = True
                if do_change:
                    part_man_obj.sup_json = data
                    part_man_obj.save()
                part_man_objs.append(part_man_obj)
        return part_man_objs

    def get_root_tbs_by_tbid(self):
        """ gets the root trench books by trench book ids """
        root_tbs = {}
        ass_roots = Assertion.objects\
                             .filter(predicate_uuid=self.pred_tb_id)
        for ass_root in ass_roots:
            obj_man = Manifest.objects.get(uuid=ass_root.object_uuid)
            tb_id = obj_man.label.strip()
            act_man_obj = Manifest.objects.get(uuid=ass_root.uuid)
            data = act_man_obj.sup_json
            do_change = False
            if 'tb_id' not in data:
                data['tb_id'] = int(float(tb_id))
                do_change = True
            if do_change:
                act_man_obj.sup_json = data
                act_man_obj.save()
            root_tbs[ass_root.uuid] = tb_id
        return root_tbs

    def make_tb_scan_media_label(self, tb_label, im_p_range):
        """ maes a tb_scan label from the tb_label and the filename """
        tb_l_ex = tb_label.split('(')
        tb_scan_label = 'Trench Book ' + tb_l_ex[0].strip()
        p_prefix = ':'
        for page in im_p_range:
            tb_scan_label += p_prefix + str(page)
            p_prefix = '-'
        return tb_scan_label

    def get_image_page_range_from_filename(self, filename):
        """ makes a page range from an image filename """
        p_range = []
        if '.' in filename and '--' in filename:
            f_ex = filename.split('.')
            name = f_ex[0]
            name_ex = name.split('--')
            page_part = name_ex[1]
            if '-' in page_part:
                pages = page_part.split('-')
            else:
                pages = [page_part]
            for page_str in pages:
                page = None
                try:
                    page = int(float(page_str))
                except:
                    page = None
                if page is not None:
                    p_range.append(page)
        return p_range

    def make_image_versions(self, src):
        """ Copies a directory structure
            and makes thumbnail and preview files
        """
        src_dir = self.set_check_directory(self.origin_dir)
        dest_dir = self.set_check_directory(self.origin_dir)
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
