/*
 * Functions to edit multiple language strings
 */
function multilingualEdit(){
	this.project_uuid = project_uuid;
	this.item_uuid = item_uuid;
	this.item_type = item_type;
	this.predicate = false;
	this.parent_obj_name = false;
	this.obj_name = 'multilingual';
	this.name = this.obj_name;
	this.item_json_ld_obj = false;
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
			'script_code': 'ar'
		},
		'de': {
			'label': 'German',
			'localized': 'Deutsch',
			'script_code': 'la'
		},
		'en': {
			'label': 'English',
			'localized': 'English',
			'script_code': 'la'
		},
		'es': {
			'label': 'Spanish',
			'localized': 'Español',
			'script_code': 'la'
		},
		'fa': {
			'label': 'Persian',
			'localized': 'فارسی',
			'script_code': 'ar'
		},
		'fr': {
			'label': 'French',
			'localized': 'Français'
		},
		'he': {
			'label': 'Hebrew',
			'localized': 'עברית',
			'script_code': 'he'
		},
		'it': {
			'label': 'Italian',
			'localized': 'Italiano',
			'script_code': 'la'
		},
		'tr': {
			'label': 'Turkish',
			'localized': 'Türkçe',
			'script_code': 'la'
		},
		'zh': {
			'label': 'Chinese',
			'localized': '中文',
			'script_code': 'zh'
		}
	}
	
}