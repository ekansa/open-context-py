import os
import json
import codecs
from django.db import models
from django.conf import settings
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.ocitems.ocitem.models import OCitem


# Stores data about fields for research
class JSONexport():

    def __init__(self):
        self.root_export_dir = settings.STATIC_EXPORTS_ROOT

    def prep_directory(self, act_dir):
        """ Prepares a directory to receive export files """
        output = False
        full_dir = self.root_export_dir + act_dir + '/'
        if not os.path.exists(full_dir):
            os.makedirs(full_dir)
        if os.path.exists(full_dir):
            output = full_dir
        return output

    def export_project_meta(self):
        """ Exports projects """
        man_projs = Manifest.objects.filter(item_type='projects')
        for man_proj in man_projs:
            uuid = man_proj.uuid
            slug = man_proj.slug
            # proj_dir = self.prep_directory(slug)
            # proj_file = proj_dir + slug + '.json'
            proj_dir = self.prep_directory('draft-project-json-ld')
            proj_file = proj_dir + uuid + '.json'
            ocitem = OCitem()
            ocitem.get_item(uuid)
            json_output = json.dumps(ocitem.json_ld,
                                     indent=4,
                                     ensure_ascii=False)
            file = codecs.open(proj_file, 'w', 'utf-8')
            file.write(json_output)
            file.close()
