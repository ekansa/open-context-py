/*
 * Functions to edit multiple language strings
 */
function multilingual(){
	this.language_label = 'English';
	this.language_localized = 'English';
	this.language_code = 'en';
	this.script_label = 'Latin';
	this.script_localized = 'Latin';
	this.script_code = 'la';
	this.languages = {
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
		}
	}
}