import csv
import requests
from time import sleep
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.libs.generalapi import GeneralAPI


class csvAPI():
    """ Interacts with Periodo """
    SLEEP_TIME = .5

    def __init__(self):
        self.request_error = False
        self.csv_data = False
        self.delay_before_request = self.SLEEP_TIME

    def get_read_csv(self, url):
        """
        gets json daa from a geonames_uri
        """
        if self.delay_before_request > 0:
            # default to sleep BEFORE a request is sent, to
            # give the remote service a break.
            sleep(self.delay_before_request)
        try:
            gapi = GeneralAPI()
            r = requests.get(url,
                             timeout=240,
                             headers=gapi.client_headers)
            r.raise_for_status()
            csvfile = r.text.split('\n')
            self.csv_data = csv.reader(csvfile)
        except:
            self.csv_data = False
        return self.csv_data
