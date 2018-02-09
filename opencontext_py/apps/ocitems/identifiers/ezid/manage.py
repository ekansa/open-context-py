import datetime
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.apps.entities.entity.models import Entity
from opencontext_py.apps.entities.uri.models import URImanagement
from opencontext_py.apps.ocitems.identifiers.ezid.ezid import EZID
from opencontext_py.apps.ocitems.identifiers.ezid.metaark import metaARK
from opencontext_py.apps.ocitems.identifiers.models import StableIdentifer
from opencontext_py.apps.ocitems.ocitem.generation import OCitem


class EZIDmanage():
    """
        Methods to mint EZID identifiers and
        add them to the database
    """
   
    def __init__(self, do_test=False):
        self.ezid = EZID()
        if do_test:
            self.ezid.ark_shoulder = EZID.ARK_TEST_SHOULDER
    
    def make_save_ark_by_uuid(self, uuid, metadata=None):
        """ makes an saves an ARK identifier by a uuid """
        ok = False
        oc_uri = None
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
                        try:
                            ok = True
                            new_stable = StableIdentifer()
                            new_stable.stable_id = stable_id
                            new_stable.stable_type = 'ark'
                            new_stable.uuid = oc_item.manifest.uuid
                            new_stable.project_uuid = oc_item.manifest.project_uuid
                            new_stable.item_type = oc_item.manifest.item_type
                            new_stable.save()
                        except:
                            ok = False
                            note = 'Identifier already in use'
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