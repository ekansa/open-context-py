import time
import datetime
from django.conf import settings
from opencontext_py.libs.rootpath import RootPath
from opencontext_py.libs.isoyears import ISOyears
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.apps.entities.entity.models import Entity
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.ocitems.persons.models import Person
from opencontext_py.apps.ocitems.projects.models import Project


class ArchiveMetadata():
    """
    Methods to make archive metadata objects
    
    """
    
    def __init__(self):
        self.proj_upload_type = 'publication'
        self.proj_pub_type = 'other'
        self.proj_binary_upload_type = 'publication'
        self.proj_binary_pub_type = 'other'
        self.access_right = 'open'
        self.proj_binary_keywords = [
            'Open Context',
            'Data Publication',
            'Media Files'
        ]
        self.proj_keywords = [
            'Open Context',
            'Data Publication',
            'Structured Data',
            'GeoJSON',
            'JSON-LD'
        ]
        self.community_ids = [
            'opencontext',
            'archaeology'
        ]
        self.default_subjects = [
            {'term': 'Archaeology',
             'identifier': 'http://id.loc.gov/authorities/subjects/sh85006507'}
        ]
    
    def make_zenodo_proj_media_files_metadata(self, proj_dict, dir_dict, dir_content_file_json):
        """ makes a zendo metadata object for a deposition
            of media files from an Open Context project
        """
        meta = None
        if isinstance(proj_dict, dict) and isinstance(dir_dict, dict):
            rp = RootPath()
            meta = LastUpdatedOrderedDict()
            meta['title'] = (
                '' + proj_dict['dc-terms:title'] + ' '
                '[Aggregated Media Files (' +  str( dir_dict['partion-number'] ) + ') from Open Context]'
            )
            if 'dc-terms:modified' in proj_dict:
                # date of last modification
                meta['publication_date'] = proj_dict['dc-terms:modified']
            else:
                # default to today
                today = datetime.date.today()
                meta['publication_date'] = today.isoformat()
            meta['license'] = self.make_zenodo_license_abrev(dir_dict)
            meta['upload_type'] = self.proj_upload_type
            if meta['upload_type'] == 'publication':
                meta['publication_type'] = self.proj_binary_pub_type
            meta['creators'] = self.make_zenodo_creator_list(dir_dict)
            meta['keywords'] = self.proj_binary_keywords \
                               + self.make_zendo_keywords_for_media_files(dir_dict)
            meta['subjects'] = self.make_zenodo_subjects_list(proj_dict)
            meta['related_identifiers'] = self.make_zenodo_related_list(proj_dict)
            if 'description' in proj_dict:
                project_des = proj_dict['description']
            else:
                project_des = '[No additional description provided]'
            meta['communities'] = []
            for community_id in self.community_ids:
                zenodo_obj = {
                    'identifier': community_id
                }
                meta['communities'].append(zenodo_obj)
            meta['description'] = (
                '<p>This archives media files associated with the <em>'
                '<a href="' + proj_dict['id'] + '">' + proj_dict['label'] + '</a></em> project published by '
                '<a href="' + rp.cannonical_host + '">Open Context</a>.</p>'
                '<p>The included JSON file "' + dir_content_file_json + '" describes links between the various files '
                'in this archival deposit and their associated Open Context media resources (identified by URI). '
                'These linked Open Context media resource items provide additional context and descriptive metadata '
                'for the files archived here.</p>'
                '<br/>'
                '<p><strong>Brief Description of this Project</strong>'
                '<br/>' + project_des + '</p>'
            )
        return meta
    
    def make_zenodo_license_abrev(self, meta_dict):
        """ zenodo wants an abbreviated license, not a full URI
            this is annoying, but it is what it wants
        """
        zendo_license = None
        if 'dc-terms:license' in meta_dict:
            lic_uri = meta_dict['dc-terms:license']
            if 'publicdomain' in lic_uri:
                zendo_license = 'cc-zero'
            elif 'licenses/' in lic_uri:
                lic_ex = lic_uri.split('licenses/')
                lic_part = lic_ex[-1]
                if '/' in lic_part:
                    lic_part_ex = lic_part.split('/')
                    zendo_license = 'cc-' + lic_part_ex[0]
                else:
                    zendo_license = 'cc-' + lic_part
        return zendo_license
    
    def make_zenodo_subjects_list(self, proj_dict):
        """ makes a list of subjects that conform to the Zenodo model """
        id_list = []
        zenodo_list = []
        for zenodo_obj in self.default_subjects:
            if zenodo_obj['identifier'] not in id_list:
                id_list.append(zenodo_obj['identifier'])
                zenodo_list.append(zenodo_obj)
        sub_preds = [
            'dc-terms:subject',
            'dc-terms:spatial',
            'dc-terms:temporal',
            'dc-terms:coverage'
        ]
        for sub_pred in sub_preds:
            if sub_pred in proj_dict:
                if isinstance(proj_dict[sub_pred], list):
                    for obj_dict in proj_dict[sub_pred]:
                        if obj_dict['id'] not in id_list:
                            id_list.append(obj_dict['id'])
                            zenodo_obj = LastUpdatedOrderedDict()
                            zenodo_obj['term'] = obj_dict['label']
                            zenodo_obj['identifier'] = obj_dict['id']
                            zenodo_list.append(zenodo_obj)
        return zenodo_list
    
    def make_zendo_keywords_for_media_files(self, dir_dict):
        """ makes a list of keywords based on categories from the dir_dict """
        zenodo_list = []
        if 'category' in dir_dict:
            if isinstance(dir_dict['category'], list):
                for obj_dict in dir_dict['category']:
                    ent = Entity()
                    found = ent.dereference(obj_dict['id'])
                    if found:
                        if ent.label not in zenodo_list:
                            zenodo_list.append(ent.label)
        return zenodo_list
    
    def make_zenodo_related_list(self, proj_dict):
        """ makes a list of related identifiers that
            conform to the Zenodo model.
            
            These related identifiers describe how a
            deposition relates to Open Context
            and an Open Context project
        """
        rp = RootPath()
        zenodo_list = []
        # make relation to Open Context, the compiler of the deposition
        zenodo_obj = LastUpdatedOrderedDict()
        zenodo_obj['relation'] = 'isCompiledBy'
        zenodo_obj['identifier'] =  rp.cannonical_host
        zenodo_list.append(zenodo_obj)
        # make relation to the Open Context, project
        # this deposition will be part of the project
        # and it will compile the project
        proj_rels = [
            'isPartOf',
            'compiles'
        ]
        for proj_rel in proj_rels:
            zenodo_obj = LastUpdatedOrderedDict()
            zenodo_obj['relation'] = proj_rel
            zenodo_obj['identifier'] =  proj_dict['id']
            zenodo_list.append(zenodo_obj)
            if 'owl:sameAs' in proj_dict:
                if isinstance(proj_dict['owl:sameAs'], list):
                    for obj_dict in proj_dict['owl:sameAs']:
                        zenodo_obj = LastUpdatedOrderedDict()
                        zenodo_obj['relation'] = proj_rel
                        zenodo_obj['identifier'] =  obj_dict['id']
                        zenodo_list.append(zenodo_obj)
        # make relation to a parent Open Context project, if it applicable
        if 'dc-terms:isPartOf' in proj_dict:
            if isinstance(proj_dict['dc-terms:isPartOf'], list):
                for obj_dict in proj_dict['dc-terms:isPartOf']:
                    zenodo_obj = LastUpdatedOrderedDict()
                    zenodo_obj['relation'] = 'isPartOf'
                    zenodo_obj['identifier'] =  obj_dict['id']
                    zenodo_list.append(zenodo_obj)
        return zenodo_list
    
    def make_zenodo_creator_list(self, meta_dict):
        """ makes a list of creators that conform to the Zenodo model """
        zenodo_list = []
        id_list = []
        objs_w_order = []
        cite_preds = [
            'dc-terms:contributor',
            'dc-terms:creator',
        ]
        all_order = 0
        list_order = 0
        max_count = 1
        for cite_pred in cite_preds:
            if cite_pred in meta_dict:
                for obj_dict in meta_dict[cite_pred]:
                    if 'count' in obj_dict:
                        if obj_dict['count'] > max_count:
                            max_count = obj_dict['count']
        pred_adder = 0
        for cite_pred in cite_preds:
            pred_adder += 1
            if cite_pred in meta_dict:
                for obj_dict in meta_dict[cite_pred]:
                    act_id = obj_dict['id']
                    if act_id not in id_list:
                        id_list.append(act_id)
                        list_order = (len(id_list)) + pred_adder
                        if 'count' in obj_dict:
                            # count is useful for bulk uploads of several media items
                            # these may have many creators, so the creaters referenced
                            # the most frequently will appear hgi
                            all_order = list_order + (max_count - obj_dict['count'])
                        else:
                            all_order = list_order
                        obj_w_order = (obj_dict, all_order)
                        objs_w_order.append(obj_w_order)
        ordered_objs = sorted(objs_w_order, key=lambda x: x[1])
        for obj_w_order in ordered_objs:
            obj_dict = obj_w_order[0]
            obj_dict = self.add_person_names_to_obj(obj_dict)
            zenodo_obj = {}
            zenodo_obj['name'] = obj_dict['family_given_name']
            if 'foaf:isPrimaryTopicOf' in obj_dict:
                if 'orcid.org' in obj_dict['foaf:isPrimaryTopicOf']:
                    id_ex = obj_dict['foaf:isPrimaryTopicOf'].split('/')
                    zenodo_obj['orcid'] = id_ex [-1]  # the last part of the ORCID, not the full URI
            else:
                pass
                # zenodo_obj['affiliation'] = 'Open Context URI: ' + obj_dict['id']
            zenodo_list.append(zenodo_obj)
        return zenodo_list
    
    def add_person_names_to_obj(self, obj_dict, default_to_label=True):
        """ adds person names to a JSON-LD object dict """
        obj_dict['family_given_name'] = None
        if 'id' in obj_dict:
            act_id = obj_dict['id']
        elif '@id' in obj_dict:
            act_id = obj_dict['@id']
        else:
            act_id = None
        if default_to_label:
            if 'label' in obj_dict:
                if isinstance(obj_dict['label'], str):
                     obj_dict['family_given_name'] = obj_dict['label']
        if isinstance(act_id, str):
            ent = Entity()
            found = ent.dereference(act_id)
            if found:
                obj_dict['family_given_name'] = ent.label
                if ent.item_type == 'persons':
                    surname = ''
                    given_name = ''
                    try:
                        pers = Person.objects.get(uuid=ent.uuid)
                    except Person.DoesNotExist:
                        pers = None
                    if pers is not None:
                        if isinstance(pers.surname, str):
                            if len(pers.surname.strip()) > 0:
                                surname = pers.surname.strip()
                                if isinstance(pers.given_name, str):
                                    if len(pers.given_name.strip()) > 0:
                                        given_name = pers.given_name.strip()
                                        obj_dict['family_given_name'] = surname + ', ' + given_name
                                        if isinstance(pers.mid_init, str):
                                            if len(pers.mid_init.strip()) > 0:
                                                obj_dict['family_given_name'] += ' ' + pers.mid_init.strip()
        return obj_dict
                    
        def make_zendo_keywords_for_media_files(self, dir_dict):
            """ makes zenodo keywords from a directory
                contents object
            """
            zenodo_keywords = []
            if 'category' in dir_dict:
                if instance(dir_dict['category'], list):
                    for cat_obj in dir_dict['category']:
                        ent = Entity()
                        found = ent.dereference(cat_obj['id'])
                        if found:
                            zenodo_keywords.append(ent.label)
            return zenodo_keywords
