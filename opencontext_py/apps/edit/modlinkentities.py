import os
import codecs
from django.conf import settings
from django.db import models
from django.db.models import Q
from opencontext_py.apps.entities.uri.models import URImanagement
from opencontext_py.apps.ldata.linkentities.models import LinkEntity
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.ldata.linkannotations.models import LinkAnnotation
from opencontext_py.apps.ldata.linkannotations.manage import LinkAnnoManagement


# This class is used for the mass editing of category data
class ModifyLinkEntities():

    REVISION_LIST = [
        {'new': 'oc-zoo:B', 'old': 'oc-zoo:zoo-0001'},
        {'new': 'oc-zoo:BF', 'old': 'oc-zoo:zoo-0002'},
        {'new': 'oc-zoo:BFd', 'old': 'oc-zoo:zoo-0003'},
        {'new': 'oc-zoo:BFp', 'old': 'oc-zoo:zoo-0004'},
        {'new': 'oc-zoo:BG', 'old': 'oc-zoo:zoo-0005'},
        {'new': 'oc-zoo:BPC', 'old': 'oc-zoo:zoo-0006'},
        {'new': 'oc-zoo:BT', 'old': 'oc-zoo:zoo-0007'},
        {'new': 'oc-zoo:BTr', 'old': 'oc-zoo:zoo-0008'},
        {'new': 'oc-zoo:Bd', 'old': 'oc-zoo:zoo-0009'},
        {'new': 'oc-zoo:Bp', 'old': 'oc-zoo:zoo-0010'},
        {'new': 'oc-zoo:CD', 'old': 'oc-zoo:zoo-0011'},
        {'new': 'oc-zoo:DC', 'old': 'oc-zoo:zoo-0012'},
        {'new': 'oc-zoo:DD', 'old': 'oc-zoo:zoo-0013'},
        {'new': 'oc-zoo:DHA', 'old': 'oc-zoo:zoo-0014'},
        {'new': 'oc-zoo:DLS', 'old': 'oc-zoo:zoo-0015'},
        {'new': 'oc-zoo:DPA', 'old': 'oc-zoo:zoo-0016'},
        {'new': 'oc-zoo:Dd', 'old': 'oc-zoo:zoo-0017'},
        {'new': 'oc-zoo:Dl', 'old': 'oc-zoo:zoo-0018'},
        {'new': 'oc-zoo:Dm', 'old': 'oc-zoo:zoo-0019'},
        {'new': 'oc-zoo:Dp', 'old': 'oc-zoo:zoo-0020'},
        {'new': 'oc-zoo:GB', 'old': 'oc-zoo:zoo-0021'},
        {'new': 'oc-zoo:GBA', 'old': 'oc-zoo:zoo-0022'},
        {'new': 'oc-zoo:GBTc', 'old': 'oc-zoo:zoo-0023'},
        {'new': 'oc-zoo:GBTi', 'old': 'oc-zoo:zoo-0024'},
        {'new': 'oc-zoo:GH', 'old': 'oc-zoo:zoo-0025'},
        {'new': 'oc-zoo:GL', 'old': 'oc-zoo:zoo-0026'},
        {'new': 'oc-zoo:GLC', 'old': 'oc-zoo:zoo-0027'},
        {'new': 'oc-zoo:GLP', 'old': 'oc-zoo:zoo-0028'},
        {'new': 'oc-zoo:GLl', 'old': 'oc-zoo:zoo-0029'},
        {'new': 'oc-zoo:GLm', 'old': 'oc-zoo:zoo-0030'},
        {'new': 'oc-zoo:GLpe', 'old': 'oc-zoo:zoo-0031'},
        {'new': 'oc-zoo:HP', 'old': 'oc-zoo:zoo-0032'},
        {'new': 'oc-zoo:HS', 'old': 'oc-zoo:zoo-0033'},
        {'new': 'oc-zoo:LA', 'old': 'oc-zoo:zoo-0034'},
        {'new': 'oc-zoo:LAR', 'old': 'oc-zoo:zoo-0035'},
        {'new': 'oc-zoo:LF', 'old': 'oc-zoo:zoo-0036'},
        {'new': 'oc-zoo:LFo', 'old': 'oc-zoo:zoo-0037'},
        {'new': 'oc-zoo:LG', 'old': 'oc-zoo:zoo-0038'},
        {'new': 'oc-zoo:LO', 'old': 'oc-zoo:zoo-0039'},
        {'new': 'oc-zoo:LS', 'old': 'oc-zoo:zoo-0040'},
        {'new': 'oc-zoo:Ld', 'old': 'oc-zoo:zoo-0041'},
        {'new': 'oc-zoo:LeP', 'old': 'oc-zoo:zoo-0042'},
        {'new': 'oc-zoo:Ll', 'old': 'oc-zoo:zoo-0043'},
        {'new': 'oc-zoo:LmT', 'old': 'oc-zoo:zoo-0044'},
        {'new': 'oc-zoo:MBS', 'old': 'oc-zoo:zoo-0045'},
        {'new': 'oc-zoo:PL', 'old': 'oc-zoo:zoo-0046'},
        {'new': 'oc-zoo:SB', 'old': 'oc-zoo:zoo-0047'},
        {'new': 'oc-zoo:SBI', 'old': 'oc-zoo:zoo-0048'},
        {'new': 'oc-zoo:SC', 'old': 'oc-zoo:zoo-0049'},
        {'new': 'oc-zoo:SD', 'old': 'oc-zoo:zoo-0050'},
        {'new': 'oc-zoo:SDO', 'old': 'oc-zoo:zoo-0051'},
        {'new': 'oc-zoo:SH', 'old': 'oc-zoo:zoo-0052'},
        {'new': 'oc-zoo:SLC', 'old': 'oc-zoo:zoo-0053'},
        {'new': 'oc-zoo:anatomical-meas', 'old': 'oc-zoo:zoo-0054'},
        {'new': 'oc-zoo:astragalus-talus-meas', 'old': 'oc-zoo:zoo-0055'},
        {'new': 'oc-zoo:calcaneus-meas', 'old': 'oc-zoo:zoo-0056'},
        {'new': 'oc-zoo:dist-epi-fused', 'old': 'oc-zoo:zoo-0057'},
        {'new': 'oc-zoo:dist-epi-unfused', 'old': 'oc-zoo:zoo-0058'},
        {'new': 'oc-zoo:dist-epi-fusing', 'old': 'oc-zoo:zoo-0059'},
        {'new': 'oc-zoo:femur-meas', 'old': 'oc-zoo:zoo-0060'},
        {'new': 'oc-zoo:fusion-characterization', 'old': 'oc-zoo:zoo-0061'},
        {'new': 'oc-zoo:humerus-meas', 'old': 'oc-zoo:zoo-0062'},
        {'new': 'oc-zoo:von-den-driesch-bone-meas', 'old': 'oc-zoo:zoo-0063'},
        {'new': 'oc-zoo:metapodial-meas', 'old': 'oc-zoo:zoo-0064'},
        {'new': 'oc-zoo:pelvis-meas', 'old': 'oc-zoo:zoo-0065'},
        {'new': 'oc-zoo:phalanx-1-meas', 'old': 'oc-zoo:zoo-0066'},
        {'new': 'oc-zoo:phalanx-2-meas', 'old': 'oc-zoo:zoo-0067'},
        {'new': 'oc-zoo:phalanx-3-meas', 'old': 'oc-zoo:zoo-0068'},
        {'new': 'oc-zoo:prox-epi-fused', 'old': 'oc-zoo:zoo-0069'},
        {'new': 'oc-zoo:prox-epi-unfused', 'old': 'oc-zoo:zoo-0070'},
        {'new': 'oc-zoo:prox-epi-fusing', 'old': 'oc-zoo:zoo-0071'},
        {'new': 'oc-zoo:radius-meas', 'old': 'oc-zoo:zoo-0072'},
        {'new': 'oc-zoo:scapula-meas', 'old': 'oc-zoo:zoo-0073'},
        {'new': 'oc-zoo:tarsal-meas', 'old': 'oc-zoo:zoo-0074'},
        {'new': 'oc-zoo:tibia-meas', 'old': 'oc-zoo:zoo-0075'},
        {'new': 'oc-zoo:ulna-meas', 'old': 'oc-zoo:zoo-0076'},
        {'new': 'oc-zoo:has-fusion-char', 'old': 'oc-zoo:zoo-0077'},
        {'new': 'oc-zoo:has-phys-sex-det', 'old': 'oc-zoo:zoo-0078'},
        {'new': 'oc-zoo:has-anat-id', 'old': 'oc-zoo:zoo-0079'},
        {'new': 'oc-zoo:tibiotarsus-meas', 'old': 'oc-zoo:zoo-0080'},
        {'new': 'oc-zoo:Dip', 'old': 'oc-zoo:zoo-0081'},
        {'new': 'oc-zoo:Dic', 'old': 'oc-zoo:zoo-0082'},
        {'new': 'oc-zoo:malleolus-meas', 'old': 'oc-zoo:zoo-0083'},
        {'new': 'oc-zoo:GD', 'old': 'oc-zoo:zoo-0084'},
        {'new': 'oc-zoo:axis-meas', 'old': 'oc-zoo:zoo-0085'},
        {'new': 'oc-zoo:SBV', 'old': 'oc-zoo:zoo-0086'},
        {'new': 'oc-zoo:other-meas', 'old': 'oc-zoo:zoo-0087'},
        {'new': 'oc-zoo:HT', 'old': 'oc-zoo:zoo-0088'},
        {'new': 'oc-zoo:humerus-meas', 'old': 'oc-zoo:zoo-0089'},
        {'new': 'oc-zoo:HT', 'old': 'oc-zoo:zoo-0090'},
        {'new': 'oc-zoo:H', 'old': 'oc-zoo:zoo-0092'},
        {'new': 'oc-zoo:LCDe', 'old': 'oc-zoo:zoo-0093'},
        {'new': 'oc-zoo:LAPa', 'old': 'oc-zoo:zoo-0094'},
        {'new': 'oc-zoo:atlas-meas', 'old': 'oc-zoo:zoo-0095'},
        {'new': 'oc-zoo:BFcr', 'old': 'oc-zoo:zoo-0096'},
        {'new': 'oc-zoo:BFcd', 'old': 'oc-zoo:zoo-0097'},
        {'new': 'oc-zoo:LAd', 'old': 'oc-zoo:zoo-0098'},
        {'new': 'oc-zoo:BPacd', 'old': 'oc-zoo:zoo-0099'},
        {'new': 'oc-zoo:BPtr', 'old': 'oc-zoo:zoo-0100'},
        {'new': 'oc-zoo:has-anat-id', 'old': 'oc-zoo:zoo-0079'},
        {'new': 'oc-zoo:Dip', 'old': 'oc-zoo:zoo-0081'},
        {'new': 'oc-zoo:Dic', 'old': 'oc-zoo:zoo-0082'},
        {'new': 'oc-zoo:GD', 'old': 'oc-zoo:zoo-0084'},
        {'new': 'oc-zoo:SBV', 'old': 'oc-zoo:zoo-0086'},
        {'new': 'oc-zoo:HT', 'old': 'oc-zoo:zoo-0088'},
        {'new': 'oc-zoo:HT', 'old': 'oc-zoo:zoo-0090'},
        {'new': 'oc-zoo:H', 'old': 'oc-zoo:zoo-0092'},
        {'new': 'oc-zoo:LCDe', 'old': 'oc-zoo:zoo-0093'},
        {'new': 'oc-zoo:LAPa', 'old': 'oc-zoo:zoo-0094'},
        {'new': 'oc-zoo:BFcr', 'old': 'oc-zoo:zoo-0096'},
        {'new': 'oc-zoo:BPacd', 'old': 'oc-zoo:zoo-0099'},
        {'new': 'oc-zoo:BPtr', 'old': 'oc-zoo:zoo-0100'}
    ]

    def __init__(self):
        self.root_export_dir = settings.STATIC_EXPORTS_ROOT + 'categories'
        self.temp_prefix = 'oc-zoo:'
        self.root_uri = 'http://opencontext.org/vocabularies/open-context-zooarch/'

    def validate_revisions(self):
        """ checks to make sure revisions lead to unique uris """
        valid = True
        old_uris = []
        unique_uris = []
        for revision in self.REVISION_LIST:
            old_short = revision['old']
            replace_short = revision['new']
            old_uri = old_short.replace(self.temp_prefix, self.root_uri)
            new_uri = replace_short.replace(self.temp_prefix, self.root_uri)
            if old_uri not in old_uris:
                old_uris.append(old_uri)
                if new_uri not in unique_uris:
                    unique_uris.append(new_uri)
                else:
                    new_uri += '-2'
                    if new_uri not in unique_uris:
                        unique_uris.append(new_uri)
                    else:
                        print('Crap! Too many: ' + replace_short)
        return valid

    def mass_revise_uris(self):
        """ Revises category uris in a mass edit
        """
        old_uris = []
        unique_uris = []
        for revision in self.REVISION_LIST:
            ok = False
            old_short = revision['old']
            replace_short = revision['new']
            old_uri = old_short.replace(self.temp_prefix, self.root_uri)
            new_uri = replace_short.replace(self.temp_prefix, self.root_uri)
            if old_uri not in old_uris:
                old_uris.append(old_uri)
                ok = True
            if ok:
                lam = LinkAnnoManagement()
                lam.replace_object_uri(old_uri, new_uri)
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
                old_short = revision['old']
                replace_short = revision['new']
                old_uri = old_short.replace(self.temp_prefix, self.root_uri)
                new_uri = replace_short.replace(self.temp_prefix, self.root_uri)
                data = data.replace(old_uri, new_uri)
            file = codecs.open(newfilepath, 'w', 'utf-8')
            file.write(data)
            file.close()
        else:
            print('Ouch! Cannot find: '+ filepath)
