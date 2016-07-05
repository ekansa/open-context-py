#!/usr/bin/env python
from django.conf import settings


class Languages():
    """ Useful methods for Open Context interacctions
        with other APIs
    """

    DEFAULT_LANGUAGE = 'en'  # defaulting to English
    DEFAULT_SCRIPT = 'la'  # defulting to the Latin script

    def __init__(self):
        self.codes = {
            'ar': {
                'label': 'Arabic',
                'localized': 'العَرَبِية',
                'script_code': 'ar',
                'default_key': 'ar'
            },
            'de': {
                'label': 'German',
                'localized': 'Deutsch',
                'script_code': 'la',
                'default_key': 'de'
            },
            'el': {
                'label': 'Greek',
                'localized': 'ελληνικά',
                'script_code': 'el',
                'default_key': 'el'
            },
            'en': {
                'label': 'English',
                'localized': 'English',
                'script_code': 'la',
                'default_key': 'en'
            },
            'es': {
                'label': 'Spanish',
                'localized': 'Español',
                'script_code': 'la',
                'default_key': 'es'
            },
            'fa': {
                'label': 'Persian',
                'localized': 'فارسی',
                'script_code': 'ar',
                'default_key': 'fa'
            },
            'fr': {
                'label': 'French',
                'localized': 'Français',
                'script_code': 'la',
                'default_key': 'en'
            },
            'he': {
                'label': 'Hebrew',
                'localized': 'עברית',
                'script_code': 'he',
                'default_key': 'he'
            },
            'it': {
                'label': 'Italian',
                'localized': 'Italiano',
                'script_code': 'la',
                'default_key': 'it'
            },
            'tr': {
                'label': 'Turkish',
                'localized': 'Türkçe',
                'script_code': 'la',
                'default_key': 'tr'
            },
            'zh': {
                'label': 'Chinese',
                'localized': '中文',
                'script_code': 'zh',
                'default_key': 'zh'
            }}

    def get_language_default_key(self, language):
        """ gets a key for language to
            express in a JSON-LD
            object
        """
        default_key = None
        if language in self.codes:
            default_key = self.codes[language]['default_key']
        return default_key

    def get_language_script_key(self, language, script):
        """ gets a key for language to
            express in a JSON-LD
            object
        """
        key = None
        if language in self.codes:
            l_dict = self.codes[language]
            key = l_dict['default_key']
            if isinstance(script, str):
                if script != l_dict['script_code']:
                    # we're requesting a script that
                    # is not in the normal default for
                    # the language, so needs specification
                    key = language + '-' + script
        return key
