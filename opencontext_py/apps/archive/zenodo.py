import json
import os
import requests
from time import sleep
from django.conf import settings
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.libs.generalapi import GeneralAPI


class ArchiveZenodo():
    """
    Methods to interact with Zenodo to archive
    project data, and associated binary files
    
    """
    
    def __init__(self, do_testing=False):
        self.ACCESS_TOKEN = settings.ZENODO_ACCESS_TOKEN
        self.delay_before_request = .5
        if do_testing:
            self.url_prefix = 'https://sandbox.zenodo.org'
            self.ACCESS_TOKEN = settings.ZENODO_SANDBOX_TOKEN
        else:
            self.url_prefix = 'https://zenodo.org'
        
    
    def upload_file(self, deposition_id, filename, dir_file):
        """ uploads a file of filename, stored at dir_file
            into a Zenodo deposit with deposition_id
        """
        output = None
        gapi = GeneralAPI()
        headers = gapi.client_headers
        headers['Content-Type'] = 'application/json'
        if not os.path.exists(dir_file):
            # can't find the file to upload!
            output = False
        else:
            # we found the file to upload
            if self.delay_before_request > 0:
                # default to sleep BEFORE a request is sent, to
                # give the remote service a break.
                sleep(self.delay_before_request)
            data = {
                'filename': filename
            }
            files = {
                'file': open(dir_file, 'rb')
            }
            url = self.url_prefix + '/api/deposit/depositions/%s/files' % deposition_id
            try:
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
        return output
    
    def create_empty_deposition(self):
        """ makes a new empty deposition containter
            to recieve files and metadata
        """
        output = None
        gapi = GeneralAPI()
        headers = gapi.client_headers
        headers['Content-Type'] = 'application/json'
        url = self.url_prefix + '/api/deposit/depositions'
        if self.delay_before_request > 0:
            # default to sleep BEFORE a request is sent, to
            # give the remote service a break.
            sleep(self.delay_before_request)
        try:
            r = requests.post(url,
                              timeout=240,
                              headers=headers,
                              params={'access_token': self.ACCESS_TOKEN},
                              json={})
            r.raise_for_status()
            print('Status code: ' + str(r.status_code))
            output = r.json()
        except:
            print('FAIL with Status code: ' + str(r.status_code))
            print(str(r.json()))
            output = False
        return output