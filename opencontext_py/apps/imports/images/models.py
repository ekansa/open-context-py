import os, sys
import codecs
from PIL import Image
from django.db import models
from django.conf import settings
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.ocitems.geospace.models import Geospace
from opencontext_py.apps.ocitems.events.models import Event


class ImageImport():
    """ Imports images

from opencontext_py.apps.imports.images.models import ImageImport
ii = ImageImport()
ii.project_uuid = '5A6DDB94-70BE-43B4-2D5D-35D983B21515'
ii.class_uri = 'oc-gen:cat-feature'
ii.make_thumbnail('', 'PhotoID027.jpg')
    """

    def __init__(self):
        self.root_export_dir = settings.STATIC_EXPORTS_ROOT
        self.project_uuid = False
        self.source_id = False
        self.class_uri = False
        self.load_into_importer = False
        self.props_config = [{'prop': 'FeatureNum',
                              'prefix': 'Feat. ',
                              'data_type': 'xsd:integer'}]

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

    def make_thumbnail(self, act_dir, filename):
        """ Loads a file and parse it into a
            json object
        """
        json_obj = False
        dir_file = self.set_check_directory(act_dir) + filename
        save_file = self.set_check_directory(act_dir) + 'thumb-' + filename
        if os.path.exists(dir_file):
            size = (128, 128)
            try:
                im = Image.open(dir_file)
                im.thumbnail(size)
                im.save(save_file, "JPEG")
            except IOError:
                print("cannot create thumbnail for", dir_file)
