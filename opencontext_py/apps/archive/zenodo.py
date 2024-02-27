import json
import os
import requests
from time import sleep
from django.conf import settings
from opencontext_py.libs.generalapi import GeneralAPI

SANDBOX_ZENODO_URL = 'https://sandbox.zenodo.org'
PRODUCTION_ZENODO_URL = 'https://zenodo.org'

OC_COMMUNITY_UUID = 'e16d1141-54be-4ec5-82ab-c576234868be'


class ArchiveZenodo():
    """
    Methods to interact with Zenodo to archive
    project data, and associated binary files

    """

    def __init__(self, do_testing=False):
        self.ACCESS_TOKEN = settings.ZENODO_ACCESS_TOKEN
        self.delay_before_request = 0.5
        if do_testing:
            self.url_prefix = SANDBOX_ZENODO_URL
            self.ACCESS_TOKEN = settings.ZENODO_SANDBOX_TOKEN
        else:
            self.url_prefix = PRODUCTION_ZENODO_URL

    def update_metadata(self, deposition_id, metadata_dict):
        """ updates metadata for a deposition """
        output = None
        gapi = GeneralAPI()
        headers = gapi.client_headers
        headers['Content-Type'] = 'application/json'
        deposition_id = str(deposition_id)
        url = f'{self.url_prefix}/api/deposit/depositions/{deposition_id}'
        data = {
            'metadata': metadata_dict
        }
        if self.delay_before_request > 0:
            # default to sleep BEFORE a request is sent, to
            # give the remote service a break.
            sleep(self.delay_before_request)
        try:
            r = requests.put(
                url,
                timeout=240,
                headers=headers,
                params={'access_token': self.ACCESS_TOKEN},
                data=json.dumps(data)
            )
            r.raise_for_status()
            output = r.status_code
        except:
            print('FAIL to update metadata with status code: ' + str(r.status_code))
            print(str(r.json()))
            output = False
        return output

    def get_all_depositions_list(self, params=None):
        """ Gets a list of depositions for our Zenodo account via a GET
            request for a JSON object from Zenodo
        """
        gapi = GeneralAPI()
        headers = gapi.client_headers
        headers['Content-Type'] = 'application/json'
        if self.delay_before_request > 0:
            # default to sleep BEFORE a request is sent, to
            # give the remote service a break.
            sleep(self.delay_before_request)
        url = f'{self.url_prefix}/api/deposit/depositions'
        if not params:
            params = {}
        params['access_token'] = self.ACCESS_TOKEN
        try:
            r = requests.get(
                url,
                timeout=240,
                headers=headers,
                params=params,
            )
            r.raise_for_status()
            output = r.json()
        except:
            output = False
            print(f'FAIL with Status code: {r.status_code}')
            print(str(r.json()))
            print(f'URL: {url}')
        return output

    def get_deposition_meta_by_id(self, deposition_id):
        """ gets a deposition metadata object via a
            request for a JSON object from Zenodo
        """
        gapi = GeneralAPI()
        headers = gapi.client_headers
        headers['Content-Type'] = 'application/json'
        if self.delay_before_request > 0:
            # default to sleep BEFORE a request is sent, to
            # give the remote service a break.
            sleep(self.delay_before_request)
        deposition_id = str(deposition_id)
        url = f'{self.url_prefix}/api/deposit/depositions/{deposition_id}'
        try:
            r = requests.get(
                url,
                timeout=240,
                headers=headers,
                params={'access_token': self.ACCESS_TOKEN}
            )
            r.raise_for_status()
            output = r.json()
        except:
            output = False
            print(f'FAIL with Status code: {r.status_code}')
            print(str(r.json()))
            print(f'URL: {url}')
        return output

    def get_remote_deposition_bucket_url(self, deposition_id):
        """ gets the bucket_url for PUT method requests to upload large files
        """
        deposition_dict = self.get_deposition_meta_by_id(deposition_id)
        return self.get_bucket_url_from_metadata(deposition_dict)

    def upload_file_by_put(
            self,
            bucket_url,
            full_path_file,
            filename,
        ):
        """ uploads a file of filename, stored at full_path_file
            into a Zenodo deposit at location bucket_url
        """
        output = None
        if not os.path.exists(full_path_file):
            # can't find the file to upload!
            return None
        # we found the file to upload
        if self.delay_before_request > 0:
            # default to sleep BEFORE a request is sent, to
            # give the remote service a break.
            sleep(self.delay_before_request)
        url = f'{bucket_url}/{filename}'
        try:
            # for bigger files, use this PUT method
            # Adapted from: https://github.com/zenodo/zenodo/issues/833#issuecomment-324760423
            files = {
                'file': open(full_path_file, 'rb')
            }
            gapi = GeneralAPI()
            headers = gapi.client_headers
            headers['Accept'] = 'application/json'
            headers['Authorization'] = 'Bearer ' + self.ACCESS_TOKEN
            headers['Content-Type'] = 'application/octet-stream'
            r = requests.put(
                url,
                headers=headers,
                data=open(full_path_file, 'rb')
            )
            r.raise_for_status()
            output = r.json()
        except:
            output = False
            print(f'FAIL with Status code: {r.status_code}')
            print(str(r.json()))
            print(f'URL: {url}')
        return output

    def upload_file_by_post(
            self,
            deposition_id,
            filename,
            full_path_file,
            ok_if_exists=True,
        ):
        """ uploads a file of filename, stored at full_path_file
            into a Zenodo deposit with deposition_id

            will respond with an OK if it already exists

            This works by POST and is NOT the preferred method
        """
        output = None
        if not os.path.exists(full_path_file):
            # can't find the file to upload!
            return None

        # we found the file to upload
        gapi = GeneralAPI()
        headers = gapi.client_headers
        if self.delay_before_request > 0:
            # default to sleep BEFORE a request is sent, to
            # give the remote service a break.
            sleep(self.delay_before_request)
        data = {
            'filename': filename
        }
        deposition_id = str(deposition_id)
        url = f'{self.url_prefix}/api/deposit/depositions/{deposition_id}/files'
        try:
            # for bigger files, this will not work routinely
            # See fix at: https://github.com/zenodo/zenodo/issues/833
            with open(full_path_file, 'rb') as f:
                # stream the upload of the files, which can be really big!
                files = {
                    'file': f
                }
                r = requests.post(url,
                                    timeout=240,
                                    headers=headers,
                                    params={'access_token': self.ACCESS_TOKEN},
                                    data=data,
                                    files=files)
                r.raise_for_status()
                output = r.json()
        except:
            output = False
            if ok_if_exists and 'message' in r.json():
                if r.json()['message'] == 'Filename already exists.':
                    print('File already exists, with status code: ' + str(r.status_code))
                    output = True
            if output is False:
                print(f'FAIL with Status code: {r.status_code}')
                print(str(r.json()))
                print(f'URL: {url}')
        return output

    def create_empty_deposition(self):
        """ makes a new empty deposition container
            to receive files and metadata
        """
        output = None
        gapi = GeneralAPI()
        headers = gapi.client_headers
        headers['Content-Type'] = 'application/json'
        headers['Authorization'] = 'Bearer ' + self.ACCESS_TOKEN
        url = f'{self.url_prefix}/api/deposit/depositions'
        if self.delay_before_request > 0:
            # default to sleep BEFORE a request is sent, to
            # give the remote service a break.
            sleep(self.delay_before_request)
        try:
            r = requests.post(url,
                timeout=240,
                headers=headers,
                params={'access_token': self.ACCESS_TOKEN},
                json={}
            )
            r.raise_for_status()
            print('Status code: ' + str(r.status_code))
            output = r.json()
        except:
            output = False
            print(f'FAIL with Status code: {r.status_code}')
            print(str(r.json()))
            print(f'URL: {url}')
        return output

    def get_deposition_id_from_metadata(self, deposition_dict):
        """ gets the deposition id from a deposition_dict object """
        deposition_id = None
        if isinstance(deposition_dict, dict):
            deposition_id = deposition_dict.get('id', None)
        return deposition_id

    def get_bucket_url_from_metadata(self, deposition_dict):
        """ Gets the bucket url from deposition metadata
            We need a bucket URL for PUT requests to upload files
        """
        bucket_url = None
        if isinstance(deposition_dict, dict):
            bucket_url = deposition_dict.get('links', {}).get('bucket', None)
        return bucket_url