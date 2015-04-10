import json
import requests
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.libs.generalapi import GeneralAPI


class PeriodoAPI():
    """ Interacts with Periodo """
    DEFAULT_DATA_URL = 'http://n2t.net/ark:/99152/p0d.jsonld'

    def __init__(self):
        self.data_url = self.DEFAULT_DATA_URL
        self.periodo_data = False

    def get_periodo_data(self):
        """
        gets json-ld data from Periodo
        """
        url = self.data_url
        try:
            gapi = GeneralAPI()
            r = requests.get(url,
                             timeout=240,
                             headers=gapi.client_headers)
            r.raise_for_status()
            json_r = r.json()
        except:
            json_r = False
        self.periodo_data = json_r
        return json_r
