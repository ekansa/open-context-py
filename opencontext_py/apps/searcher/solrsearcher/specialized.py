import json
import requests
from unidecode import unidecode
from time import sleep
from django.conf import settings
from opencontext_py.libs.generalapi import GeneralAPI


class SpecialSearches():
    """ Methods to check for
        query parameters asking for specialized searches.
    """

    def __init__(self):
        pass
