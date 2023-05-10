import datetime

from opencontext_py.apps.persistent_ids.ezid.ezid import EZID
from opencontext_py.apps.persistent_ids.ezid.metaark import metaARK
from opencontext_py.apps.persistent_ids.ezid.metadoi import metaDOI

from opencontext_py.apps.all_items.models import (
    AllManifest,
    AllIdentifier,
)
from opencontext_py.apps.all_items.representations import item

"""
Example.


import importlib
from opencontext_py.apps.all_items.models import (
    AllManifest,
    AllIdentifier,
)
from opencontext_py.apps.persistent_ids.ezid import manage
importlib.reload(manage)

ezid_m = manage.EZIDmanage(do_test=True)
meta = ezid_m.make_ark_metadata_by_uuid(uuid='d2bfa1e0-f3f7-4376-8193-869c8b71210f')

ezid_m = manage.EZIDmanage(do_test=True)
ezid_m.uri_replace = ('opencontext.org', 'staging.opencontext.org')
meta = ezid_m.make_ark_metadata_by_uuid(uuid='d2bfa1e0-f3f7-4376-8193-869c8b71210f')



# this actually uses the EZID API
ezid_m = manage.EZIDmanage(do_test=True)
ezid_m.uri_replace = ('opencontext.org', 'staging.opencontext.org')
meta = ezid_m.make_save_ark_by_uuid(uuid='d2bfa1e0-f3f7-4376-8193-869c8b71210f')


# The real deal now.
m_qs = AllManifest.objects.filter(
    project_id='0404c6dc-a467-421e-47b8-d68f7090fbcc',
    item_type__in=['subjects', 'media', 'documents', 'predicates', 'types']
)
id_objs = []
for m_obj in m_qs:
    ezid_m = manage.EZIDmanage(do_test=False)
    id_obj = ezid_m.make_save_ark_by_uuid(uuid=m_obj.uuid)
    id_objs.append(id_obj)

"""


class EZIDmanage():
    """
        Methods to mint EZID identifiers and
        add them to the database
    """

    def __init__(self, do_test=False):
        self.ezid = EZID()
        self.do_test = do_test
        # URI replace is useful for when you want to substitute a
        # cannonical Open Context URI for another URI, like the staging
        # URI.
        self.uri_replace = None
        if self.do_test:
            self.ezid.ark_shoulder = EZID.ARK_TEST_SHOULDER
            self.ezid.doi_shoulder = EZID.DOI_TEST_SHOULDER


    def make_metadata_authors_list(self, rep_dict):
        """Makes a list of unique contributor and creator names"""
        who_list = []
        for who_key in ['dc-terms:contributor', 'dc-terms:creator']:
            for who_item in rep_dict.get(who_key, []):
                person_label = who_item.get('label')
                if not person_label:
                    continue
                if person_label in who_list:
                    continue
                who_list.append(person_label)
        return who_list


    def make_ark_metadata_by_uuid(self, uuid=None, rep_dict=None):
        """Makes ARK metadata for an Open Context record"""
        metadata = None
        if uuid and rep_dict is None:
            # the item doesn't yet have an ARK id, so make one!
            man_obj, rep_dict = item.make_representation_dict(subject_id=uuid)
            if not man_obj:
                # The item doesn't exist
                return None
        if not rep_dict:
            # Don't have an item representation dict, so skip out.
            return None
        meta_ark = metaARK()
        meta_ark.what = rep_dict.get(
            'dc-terms:title',
            rep_dict.get('label', f'Unlabeled Open Context item {uuid}')
        )
        meta_ark.when = rep_dict.get('dc-terms:issued')
        if not meta_ark.when:
            meta_ark.when = rep_dict.get('dc-terms:modified')
        if not meta_ark.when:
            meta_ark.when = str(datetime.datetime.now().year)
        who_list = self.make_metadata_authors_list(rep_dict)
        meta_ark.make_who_list(who_list)
        metadata = meta_ark.make_metadata_dict()
        metadata['_target'] = rep_dict['id']
        if self.uri_replace and not self.uri_replace[1] in metadata['_target']:
            metadata['_target'] = metadata['_target'].replace(self.uri_replace[0], self.uri_replace[1])
        return metadata


    def make_doi_metadata_by_uuid(self, uuid=None, rep_dict=None):
        """Makes DOI metadata for an Open Context record """
        metadata = None
        if uuid and rep_dict is None:
            # the item doesn't yet have an ARK id, so make one!
            man_obj, rep_dict = item.make_representation_dict(subject_id=uuid)
            if not man_obj:
                # The item doesn't exist
                return None
        if not rep_dict:
            # Don't have an item representation dict, so skip out.
            return None

        meta_doi = metaDOI()
        meta_doi.title = rep_dict.get(
            'dc-terms:title',
            rep_dict.get('label', f'Unlabeled Open Context item {uuid}')
        )

        meta_doi.publicationyear = rep_dict.get('dc-terms:issued')
        if not meta_doi.publicationyear:
            meta_doi.publicationyear = rep_dict.get('dc-terms:modified')
        if not meta_doi.publicationyear:
            meta_doi.publicationyear = str(datetime.datetime.now().year)

        who_list = self.make_metadata_authors_list(rep_dict)
        meta_doi.make_creator_list(who_list)
        metadata = meta_doi.make_metadata_dict()
        metadata['_target'] = rep_dict['id']
        if self.uri_replace and not self.uri_replace[1] in metadata['_target']:
            metadata['_target'] = metadata['_target'].replace(self.uri_replace[0], self.uri_replace[1])
        return metadata


    def save_man_obj_stable_id(self, man_obj, stable_id, scheme='ark',):
        """ saves stable_id for an AllManifest object """
        stable_id = stable_id.strip()
        if 'doi:' in stable_id:
            scheme = 'doi'
            stable_id = stable_id.replace('doi:', '')
        elif 'ark:/' in stable_id:
            scheme = 'ark'
            stable_id = stable_id.replace('ark:/', '')
        # Get the ID rank. An item can have more than 1 stable id of a given
        # scheme, and they get sorted in order of preference by rank.
        id_rank = AllIdentifier.objects.filter(
            item=man_obj,
            scheme=scheme,
        ).exclude(
            id=stable_id
        ).count()
        id_uuid = AllIdentifier().primary_key_create(
            item_id=man_obj.uuid,
            scheme=scheme,
            rank=id_rank,
        )
        id_obj, c = AllIdentifier.objects.get_or_create(
            uuid=id_uuid,
            defaults={
                'item': man_obj,
                'scheme': scheme,
                'id': stable_id,
                'rank': id_rank,
            }
        )
        print(
            f'ID obj {id_obj.uuid}: '
            f'{id_obj.item.label} ({id_obj.item.uuid}) -> '
            f'{id_obj.id} ({id_obj.scheme}) created {str(c)}'
        )
        return id_obj


    def make_save_ark_by_uuid(self, uuid, metadata=None):
        """ makes an saves an ARK identifier by a uuid """
        ok = None
        ark_count = AllIdentifier.objects.filter(
            item_id=uuid,
            scheme='ark'
        ).count()
        if ark_count > 0:
            return True
        # the item doesn't yet have an ARK id, so make one!
        man_obj, rep_dict = item.make_representation_dict(subject_id=uuid)
        if not man_obj:
            # The item doesn't exist
            return None
        if metadata is None:
            metadata = self.make_ark_metadata_by_uuid(uuid, rep_dict)
        if not isinstance(metadata, dict):
            # We don't have good metadata for this
            return None
        if '_target' in metadata:
            oc_uri = metadata['_target']
        else:
            oc_uri = f'https://{man_obj.uri}'

        if self.uri_replace and not self.uri_replace[1] in oc_uri:
            oc_uri = oc_uri.replace(self.uri_replace[0], self.uri_replace[1])

        print(f'Make ARK id for: {oc_uri}')
        ark_id = self.ezid.mint_identifier(oc_uri, metadata, 'ark')
        if not ark_id:
            print(f'EZID failed to mint ARK id for: {oc_uri}')
            return False
        stable_id = ark_id.replace('ark:/', '')
        id_obj = self.save_man_obj_stable_id(
            man_obj=man_obj,
            stable_id=stable_id,
            scheme='ark'
        )
        return id_obj


    def make_save_doi_by_uuid(self, uuid, metadata=None):
        """ makes an saves an DOI identifier by a uuid """
        ok = None
        ark_count = AllIdentifier.objects.filter(
            item_id=uuid,
            scheme='ark'
        ).count()
        if ark_count > 0:
            return True
        # the item doesn't yet have an ARK id, so make one!
        man_obj, rep_dict = item.make_representation_dict(subject_id=uuid)
        if not man_obj:
            # The item doesn't exist
            return None
        if metadata is None:
            metadata = self.make_doi_metadata_by_uuid(uuid, rep_dict=rep_dict)
        if '_target' in metadata:
            oc_uri = metadata['_target']
        else:
            oc_uri = f'https://{man_obj.uri}'

        if self.uri_replace and not self.uri_replace[1] in oc_uri:
            oc_uri = oc_uri.replace(self.uri_replace[0], self.uri_replace[1])
        print(f'Make DOI id for: {oc_uri}')
        ezid_response = self.ezid.mint_identifier(oc_uri, metadata, 'doi')
        if self.do_test:
            print(f'EZID response: {str(ezid_response)}')
        if not ezid_response:
            print(f'No response from EZID when minting a DOI for {man_obj.label} ({str(man_obj.uuid)})')
            return False
        if not '|' in ezid_response:
            print(f'Cannot parse {ezid_response} from EZID when minting a DOI for {man_obj.label} ({str(man_obj.uuid)})')
            return False
        resp_ex = ezid_response.split('|')
        stable_id = None
        for resp_id in resp_ex:
            if not 'doi:' in resp_id:
                continue
            resp_id_ex = resp_id.split('doi:')
            if len(resp_id_ex) < 2:
                continue
            stable_id = resp_id_ex[-1].strip()
        if not stable_id:
            print(f'Could not get DOI from EZID response {ezid_response} when minting a DOI for {man_obj.label} ({str(man_obj.uuid)})')
            return False
        id_obj = self.save_man_obj_stable_id(
            man_obj=man_obj,
            stable_id=stable_id,
            scheme='doi'
        )
        return id_obj