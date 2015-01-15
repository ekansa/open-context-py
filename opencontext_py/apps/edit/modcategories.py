import os
import codecs
from django.conf import settings
from django.db import models
from django.db.models import Q
from opencontext_py.apps.entities.uri.models import URImanagement
from opencontext_py.apps.ldata.linkentities.models import LinkEntity
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.ldata.linkannotations.models import LinkAnnotation


# This class is used for the mass editing of category data
class ModifyCategories():

    PREFIXING = {'db-prefix': 'oc-gen:',
                 'file-prefix': '&oc-general;'}

    REVISION_LIST = [
        {'new': 'oc-gen:cat-object', 'old': 'oc-gen:cat-0008'},
        {'new': 'oc-gen:cat-coin', 'old': 'oc-gen:cat-0009'},
        {'new': 'oc-gen:cat-pottery', 'old': 'oc-gen:cat-0010'},
        {'new': 'oc-gen:cat-glass', 'old': 'oc-gen:cat-0011'},
        {'new': 'oc-gen:cat-groundstone', 'old': 'oc-gen:cat-0012'},
        {'new': 'oc-gen:cat-arch-element', 'old': 'oc-gen:cat-0013'},
        {'new': 'oc-gen:cat-bio-subj-ecofact', 'old': 'oc-gen:cat-0014'},
        {'new': 'oc-gen:cat-animal-bone', 'old': 'oc-gen:cat-0015'},
        {'new': 'oc-gen:cat-shell', 'old': 'oc-gen:cat-0016'},
        {'new': 'oc-gen:cat-non-diag-bone', 'old': 'oc-gen:cat-0017'},
        {'new': 'oc-gen:cat-human-bone', 'old': 'oc-gen:cat-0018'},
        {'new': 'oc-gen:cat-plant-remains', 'old': 'oc-gen:cat-0019'},
        {'new': 'oc-gen:cat-loc-or-context', 'old': 'oc-gen:cat-0020'},
        {'new': 'oc-gen:cat-survey-unit', 'old': 'oc-gen:cat-0021'},
        {'new': 'oc-gen:cat-site', 'old': 'oc-gen:cat-0022'},
        {'new': 'oc-gen:cat-site-area', 'old': 'oc-gen:cat-0023'},
        {'new': 'oc-gen:cat-context', 'old': 'oc-gen:cat-0024'},
        {'new': 'oc-gen:cat-feature', 'old': 'oc-gen:cat-0025'},
        {'new': 'oc-gen:cat-exc-unit', 'old': 'oc-gen:cat-0026'},
        {'new': 'oc-gen:cat-locus', 'old': 'oc-gen:cat-0027'},
        {'new': 'oc-gen:cat-lot', 'old': 'oc-gen:cat-0028'},
        {'new': 'oc-gen:cat-basket', 'old': 'oc-gen:cat-0029'},
        {'new': 'oc-gen:cat-area', 'old': 'oc-gen:cat-0030'},
        {'new': 'oc-gen:cat-trench', 'old': 'oc-gen:cat-0031'},
        {'new': 'oc-gen:cat-operation', 'old': 'oc-gen:cat-0032'},
        {'new': 'oc-gen:cat-field-proj', 'old': 'oc-gen:cat-0033'},
        {'new': 'oc-gen:cat-square', 'old': 'oc-gen:cat-0034'},
        {'new': 'oc-gen:cat-unit', 'old': 'oc-gen:cat-0035'},
        {'new': 'oc-gen:cat-sequence', 'old': 'oc-gen:cat-0036'},
        {'new': 'oc-gen:cat-human-subj', 'old': 'oc-gen:cat-0037'},
        {'new': 'oc-gen:cat-stratum', 'old': 'oc-gen:cat-0038'},
        {'new': 'oc-gen:cat-phase', 'old': 'oc-gen:cat-0039'},
        {'new': 'oc-gen:cat-hospital', 'old': 'oc-gen:cat-0040'},
        {'new': 'oc-gen:cat-mound', 'old': 'oc-gen:cat-0041'},
        {'new': 'oc-gen:cat-sculpture', 'old': 'oc-gen:cat-0042'},
        {'new': 'oc-gen:cat-sample', 'old': 'oc-gen:cat-0043'},
        {'new': 'oc-gen:cat-sample-col', 'old': 'oc-gen:cat-0044'},
        {'new': 'oc-gen:cat-ref-col', 'old': 'oc-gen:cat-0045'},
        {'new': 'oc-gen:cat-region', 'old': 'oc-gen:cat-0046'},
        {'new': 'oc-gen:cat-figurine', 'old': 'oc-gen:cat-0047'}
    ]

    def __init__(self):
        self.root_export_dir = settings.STATIC_EXPORTS_ROOT + 'categories'

    def mass_revise_category_uris(self):
        """ Revises category uris in a mass edit
        """
        for revision in self.REVISION_LIST:
            search_old_db = revision['old']
            replace_db = revision['new']
            old_uri = URImanagement.convert_prefix_to_full_uri(search_old_db)
            new_uri = URImanagement.convert_prefix_to_full_uri(replace_db)
            Manifest.objects\
                    .filter(class_uri=search_old_db)\
                    .update(class_uri=replace_db)
            LinkAnnotation.objects\
                          .filter(subject=search_old_db)\
                          .update(subject=replace_db)
            LinkAnnotation.objects\
                          .filter(subject=old_uri)\
                          .update(subject=new_uri)
            LinkAnnotation.objects\
                          .filter(object_uri=search_old_db)\
                          .update(object_uri=replace_db)
            LinkAnnotation.objects\
                          .filter(object_uri=old_uri)\
                          .update(object_uri=new_uri)
            LinkEntity.objects\
                      .filter(uri=old_uri)\
                      .update(uri=new_uri)

    def update_ontology_doc(self, filename):
        """ Changes categories in the ontology document
        """
        filepath = self.root_export_dir + '/' + filename
        newfilepath = self.root_export_dir + '/rev-' + filename
        if os.path.isfile(filepath):
            print('Found: ' + filepath)
            with open(filepath, 'r') as myfile:
                data = myfile.read()
            for revision in self.REVISION_LIST:
                search_old_db = revision['old']
                search_old_file = search_old_db.replace(self.PREFIXING['db-prefix'],
                                                        self.PREFIXING['file-prefix'])
                replace_db = revision['new']
                replace_file = replace_db.replace(self.PREFIXING['db-prefix'],
                                                  self.PREFIXING['file-prefix'])
                data = data.replace(search_old_file, replace_file)
                old_uri = URImanagement.convert_prefix_to_full_uri(search_old_db)
                new_uri = URImanagement.convert_prefix_to_full_uri(replace_db)
                data = data.replace(old_uri, new_uri)
            file = codecs.open(newfilepath, 'w', 'utf-8')
            file.write(data)
            file.close()
        else:
            print('Ouch! Cannot find: '+ filepath)