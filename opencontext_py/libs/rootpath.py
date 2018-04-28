#!/usr/bin/env python
from django.conf import settings


class RootPath():
    """
    Makes the root path for URLs in this deployment
    """
    def __init__(self):
        self.cannonical_host = settings.CANONICAL_HOST

    def get_baseurl(self):
        """ get the base url for this instance
            of Open Context
        """
        if settings.CANONICAL_HOST != settings.DEPLOYED_HOST:
            if settings.DEBUG:
                base_url = 'http://127.0.0.1:8000'
            else:
                base_url = settings.DEPLOYED_HOST
        else:
            base_url = settings.CANONICAL_HOST
        if settings.DEFAULT_HTTPS and 'https://' not in base_url:
            base_url = base_url.replace('http://', 'https://')
        return base_url

    def convert_local_url(self, url):
        """ makes a local url from a
            url
        """
        base_url = self.get_baseurl()
        if settings.CANONICAL_HOST != base_url:
            url = url.replace(settings.CANONICAL_HOST, base_url)
        return url

    def convert_to_https(self, url):
        """ converts a URL to an HTTPS url """
        if settings.DEFAULT_HTTPS:
            url = url.replace('http://', 'https://')
        return url
