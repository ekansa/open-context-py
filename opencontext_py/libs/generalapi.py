#!/usr/bin/env python
from django.conf import settings


class GeneralAPI():
    """ Useful methods for Open Context interacctions
        with other APIs
    """

    DEFAULT_CLIENT_HEADERS = {
        'User-Agent': 'Open Context API-Client'
    }

    def __init__(self):
        self.client_headers = self.DEFAULT_CLIENT_HEADERS
