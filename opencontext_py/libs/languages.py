#!/usr/bin/env python
from django.conf import settings
from opencontext_py.libs.general import LastUpdatedOrderedDict


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
                'default_key': 'fr'
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

    def modify_localization_json(self, localized_json, key, translation):
        """ updates localization json with new text, or removes
            a language key of the text is blank
        """
        translation = translation.strip()
        if not isinstance(localized_json, dict):
            localized_json = LastUpdatedOrderedDict()
        if key != self.DEFAULT_LANGUAGE:
            # we will only modify localizations if the key is not
            # the same as the default language
            if len(translation) > 1:
                # we have non-blank translation text
                localized_json[key] = translation
            else:
                if key in localized_json:
                    # we're deleting the translation, since
                    # the translation text is blank
                    localized_json.pop(key, None)
        return localized_json

    def make_json_ld_value_obj(self, default_content, localized_json):
        """ makes an value object for json_ld, which is either
            just a string or is a dict object (container) for
            localized_json
        """
        output = default_content
        if isinstance(localized_json, dict):
            # ok, we have dict
            if self.DEFAULT_LANGUAGE in localized_json:
                # we do not allow the default language in the
                # localized array
                localized_json.pop(self.DEFAULT_LANGUAGE, None)
            if len(localized_json) > 0:
                # we have a non-empty dict
                output = LastUpdatedOrderedDict()
                # now add the default content to this dict
                # the first key will always be the default language
                output[self.DEFAULT_LANGUAGE] = default_content
                # add the other content
                for key, value in localized_json.items():
                    output[key] = value
        return output

    def get_default_value_str(self, value_obj):
        """ gets the default value string from a
            value object found in JSON-LD
        """
        output = value_obj
        if isinstance(value_obj, dict):
            # ok, we have dict
            if self.DEFAULT_LANGUAGE in value_obj:
                output = value_obj[self.DEFAULT_LANGUAGE]
        return output
    
    def get_other_values_dict(self, value_obj):
        """ gets a dictionary object for all the
            non-default localized / translated languges
            as a key => value dict.
        """
        output = None
        if isinstance(value_obj, dict):
            # ok, we have dict
            output = LastUpdatedOrderedDict()
            for lang_code, value in value_obj.items(): 
                if lang_code != self.DEFAULT_LANGUAGE:
                    output[lang_code] = value
        return output

    def get_all_value_str(self, value_obj, delim=' \n '):
        """ gets and concatenates all the localization values in
            a value string or a value dict object found in JSON-LD
        """
        output = value_obj
        if isinstance(value_obj, dict):
            # ok, we have dict
            vals_list = []
            for key, value in value_obj.items():
                vals_list.append(value)
            output = delim.join(vals_list)
        return output

