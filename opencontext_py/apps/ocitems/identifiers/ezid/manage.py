import datetime
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.apps.entities.entity.models import Entity
from opencontext_py.apps.entities.uri.models import URImanagement
from opencontext_py.apps.ocitems.identifiers.ezid.ezid import EZID
from opencontext_py.apps.ocitems.identifiers.ezid.metaark import metaARK
from opencontext_py.apps.ocitems.identifiers.ezid.metadoi import metaDOI
from opencontext_py.apps.ocitems.identifiers.models import StableIdentifer
from opencontext_py.apps.ocitems.ocitem.generation import OCitem


class EZIDmanage():
    """
        Methods to mint EZID identifiers and
        add them to the database
    """
   
    def __init__(self, do_test=False):
        self.ezid = EZID()
        self.do_test = do_test
        if self.do_test:
            self.ezid.ark_shoulder = EZID.ARK_TEST_SHOULDER
            self.ezid.doi_shoulder = EZID.DOI_TEST_SHOULDER
    
    def make_save_ark_by_uuid(self, uuid, metadata=None):
        """ makes an saves an ARK identifier by a uuid """
        ok = False
        oc_uri = None
        arks = StableIdentifer.objects.filter(uuid=uuid,
                                              stable_type='ark')[:1]
        if len(arks) < 1:
            # the item doesn't yet have an ARK id, so make one!
            oc_item = OCitem()
            exists = oc_item.check_exists(uuid)
            if oc_item.exists:
                if metadata is None:
                    metadata = self.make_ark_metadata_by_uuid(uuid, oc_item)
                if isinstance(metadata, dict):
                    if '_target' in metadata:
                        oc_uri = metadata['_target']
                    else:
                        oc_uri = URImanagement.make_oc_uri(oc_item.manifest.uuid,
                                                           oc_item.item_type)
                    if isinstance(oc_uri, str):
                        print('Make ARK id for: ' + oc_uri)
                        ark_id = self.ezid.mint_identifier(oc_uri, metadata, 'ark')
                        if isinstance(ark_id, str):
                            # success! we have an ARK id!
                            stable_id = ark_id.replace('ark:/', '')
                            ok = self.save_oc_item_stable_id(oc_item,
                                                             stable_id,
                                                             'ark')
        return ok           
    
    def make_ark_metadata_by_uuid(self, uuid, oc_item=None):
        """ makes metadata for an ARK id """
        metadata = None
        if oc_item is None:
            oc_item = OCitem()
            exists = oc_item.check_exists(uuid)
        if oc_item.exists:
            oc_item.generate_json_ld()
            meta_ark = metaARK()
            if 'dc-terms:title' in oc_item.json_ld:
                meta_ark.what = oc_item.json_ld['dc-terms:title']
            if 'dc-terms:issued' in oc_item.json_ld:
                meta_ark.when = oc_item.json_ld['dc-terms:issued']
            elif 'dc-terms:modified' in oc_item.json_ld:
                meta_ark.when = oc_item.json_ld['dc-terms:modified']
            else:
                meta_ark.when = str(datetime.datetime.now().year)
            who_list = []
            if 'dc-terms:contributor' in oc_item.json_ld:
                for who_item in oc_item.json_ld['dc-terms:contributor']:
                    who_list.append(str(who_item['label']))
            if 'dc-terms:creator' in oc_item.json_ld and len(who_list) < 1:
                for who_item in oc_item.json_ld['dc-terms:creator']:
                    who_list.append(str(who_item['label']))
            meta_ark.make_who_list(who_list)
            metadata = meta_ark.make_metadata_dict()
            metadata['_target'] = oc_item.json_ld['id']
        return metadata
    
    def make_save_doi_by_uuid(self, uuid, metadata=None):
        """ makes an saves an DOI identifier by a uuid """
        ok = False
        oc_uri = None
        dois = StableIdentifer.objects.filter(uuid=uuid,
                                              stable_type='doi')[:1]
        if len(dois) < 1:
            # the item doesn't yet have an ARK id, so make one!
            oc_item = OCitem()
            exists = oc_item.check_exists(uuid)
            if oc_item.exists:
                if metadata is None:
                    metadata = self.make_doi_metadata_by_uuid(uuid, oc_item)
                if isinstance(metadata, dict):
                    if '_target' in metadata:
                        oc_uri = metadata['_target']
                    else:
                        oc_uri = URImanagement.make_oc_uri(oc_item.manifest.uuid,
                                                           oc_item.item_type)
                    if isinstance(oc_uri, str):
                        print('Make DOI id for: ' + oc_uri)
                        ezid_response = self.ezid.mint_identifier(oc_uri, metadata, 'doi')
                        if self.do_test:
                            print('EZID response: ' + str(ezid_response))
                        if isinstance(ezid_response, str):
                            if '|' in ezid_response:
                                resp_ex = ezid_response.split('|')
                                for resp_id in resp_ex:
                                    if 'doi:' in resp_id:
                                        ok = self.save_oc_item_stable_id(oc_item, resp_id, 'doi')
                                    else:
                                        pass
                            else:
                                ok = self.save_oc_item_stable_id(oc_item, ezid_response, 'doi')
        return ok           
    
    def save_oc_item_stable_id(self, oc_item, stable_id, stable_type='ark'):
        """ saves stable_id for an oc_item object """
        stable_id = stable_id.strip()
        if 'doi:' in stable_id:
            stable_type = 'doi'
            stable_id = stable_id.replace('doi:', '')
        elif 'ark:/' in stable_id:
            stable_type = 'ark'
            stable_id = stable_id.replace('ark:/', '')
        print('Try to save ' + stable_type + ': ' + stable_id)
        try:
            ok = True
            new_stable = StableIdentifer()
            new_stable.stable_id = stable_id
            new_stable.stable_type = stable_type
            new_stable.uuid = oc_item.manifest.uuid
            new_stable.project_uuid = oc_item.manifest.project_uuid
            new_stable.item_type = oc_item.manifest.item_type
            new_stable.save()
        except:
            ok = False
            note = 'Identifier of type [' + stable_type + '] already exists.'
        return ok
    
    def make_doi_metadata_by_uuid(self, uuid, oc_item=None):
        """ makes metadata for an ARK id """
        metadata = None
        if oc_item is None:
            oc_item = OCitem()
            exists = oc_item.check_exists(uuid)
        if oc_item.exists:
            oc_item.generate_json_ld()
            meta_doi = metaDOI()
            if 'dc-terms:title' in oc_item.json_ld:
                meta_doi.title = oc_item.json_ld['dc-terms:title']
            if 'dc-terms:issued' in oc_item.json_ld:
                meta_doi.publicationyear = oc_item.json_ld['dc-terms:issued']
            elif 'dc-terms:modified' in oc_item.json_ld:
                meta_doi.publicationyear = oc_item.json_ld['dc-terms:modified']
            else:
                meta_doi.publicationyear = str(datetime.datetime.now().year)
            creator_list = []
            if 'dc-terms:contributor' in oc_item.json_ld:
                for dc_item in oc_item.json_ld['dc-terms:contributor']:
                    creator_list.append(str(dc_item['label']))
            if 'dc-terms:creator' in oc_item.json_ld and len(creator_list) < 1:
                for dc_item in oc_item.json_ld['dc-terms:creator']:
                    creator_list.append(str(dc_item['label']))
            meta_doi.make_creator_list(creator_list)
            metadata = meta_doi.make_metadata_dict()
            metadata['_target'] = oc_item.json_ld['id']
        return metadata