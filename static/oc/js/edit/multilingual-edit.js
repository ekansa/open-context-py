/*
 * Functions to edit multiple language strings
 */
function multilingual(){
	this.modal_dom_id = 'localize-modal';
	this.modal_title_dom_id = 'localize-title';
	this.modal_inter_dom_id = 'localize-interface';
	this.invalid_alert_class = 'alert alert-warning';
	this.parent_obj_name = false;
	this.value_num = 0;
	this.obj_name = 'multilingual';
	this.name = false;
	this.label = 'Label for text to translate';
	this.language_label = 'English';
	this.language_localized = 'English';
	this.language_code = 'en';
	this.script_label = 'Latin';
	this.script_localized = 'Latin';
	this.script_code = 'la';
	this.text_box_rows = 3;  // number of rows in the default text-box
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
		}
	}
	this.dom_ids = null;
	this.edit_uuid = null;
	this.edit_type = false;
	this.content_type = 'content'; // default content type for content translation
	this.localization = null;
	this.initialize = function(){
		if (this.parent_obj_name != false) {
			this.name = this.parent_obj_name + '.' + this.obj_name;
		}
		else{
			this.name = this.obj_name;
		}
		if (this.dom_ids == null) {
			this.dom_ids = this.default_domids(this.value_num, 'default-ml');
		}
	}
	this.default_domids = function(value_num, suffix){
		var dom_ids = {
			lang_out: (value_num + '-field-fcl-' + suffix),  //for language adding options
			lang_sel: (value_num + '-field-lang-sel-' + suffix),  //for language selection input
			lang_literal: (value_num + '-field-lang-lit-' + suffix),  //for language text literal
			lang_valid: (value_num + '-field-lang-valid-' + suffix), //container ID for language validation feedback
			lang_valid_val: (value_num + '-field-lang-valid-val-' + suffix), //hidden input field for language value validation results
			lang_submitcon: (value_num + '-field-lang-sbcon-' + suffix), //container ID for language submitt button
			lang_respncon: (value_num + '-field-lang-respcon-' + suffix), //container ID for language submission response
		}
		this.dom_ids = dom_ids;
		return dom_ids;
	}
	/*************************************************
	 * Functions to generate interface HTML
	 * ***********************************************
	 */
	this.localizeInterface = function(){
		var inter_dom = document.getElementById(this.modal_inter_dom_id);
		var title_dom = document.getElementById(this.modal_title_dom_id);
		if (this.edit_type == 'label') {
			// translate a label for an item
			title_dom.innerHTML = 'Add Translation for <em>' + this.label + '</em>';
			var interface_html = this.make_localize_label_interface_html(null);
			inter_dom.innerHTML = interface_html;
		}
		else {
			// translate a string from an string field
			title_dom.innerHTML = 'Add Translation for <em>' + this.label + '</em>';
			var interface_html = this.make_localize_string_interface_html(null);
			inter_dom.innerHTML = interface_html;
		}
		var modal_id = "#" + this.modal_dom_id;
		$(modal_id).modal('show');
	}
	this.make_localize_label_interface_html = function(language_code){
		// makes localizaton interface HTML for label data
		var placeholder = 'placeholder="Enter translation, and select a language above."';
		var translate_text = '';
		if (language_code != null){
			// we have a requested language_code designated
			placeholder = 'placeholder="Enter translation in the selected language."';
			if (this.localization != null) {
				if (language_code in this.localization) {
					// we have a text for this selected language
					translate_text = this.localization[language_code];
					placeholder = '';
				}
			}
		}
		var html = [
			'<div class="row">',
				'<div class="col-xs-5">',
				this.make_localize_selection_html(language_code),
				'</div>',
				'<div class="col-xs-7" style="padding-top: 5px;">',
				'<small>Select the language of the translation</small>',
				'</div>',
			'</div>',
			'<div class="row" style="margin-top:20px;">',
				'<div class="col-xs-8">',
					'<label>Translation Text</label><br/>',
					'<input id="' + this.dom_ids.lang_literal + '" ',
					'class="form-control input-sm" ',
				    'type="text" value="' + translate_text + '" ' + placeholder + ' >',
					'<p class="small">Submit blank text to delete a translation for a selected language.</p>',
				'</div>',
				'<div class="col-xs-4">',
					'<div id="' + this.dom_ids.lang_valid + '">',
					'</div>',
					'<div id="' + this.dom_ids.lang_submitcon + '">',
					'</div>',
					'<div id="' + this.dom_ids.lang_respncon + '">',
					'</div>',
				'</div>',
			'</div>',
		].join('\n');
		return html;
	}
	this.make_localize_string_interface_html = function(language_code){
		// makes localizaton interface HTML for string data 
		var placeholder = 'placeholder="Enter translation text here, and select a language above."';
		var translate_text = '';
		if (language_code != null){
			// we have a requested language_code designated
			placeholder = 'placeholder="Enter translation in the selected language."';
			if (this.localization != null) {
				if (language_code in this.localization) {
					// we have a text for this selected language
					translate_text = this.localization[language_code];
					placeholder = '';
				}
			}
		}
		var html = [
			'<div class="row">',
				'<div class="col-xs-5">',
				this.make_localize_selection_html(language_code),
				'</div>',
				'<div class="col-xs-7" style="padding-top: 5px;">',
				'<small>Select the language of the translation</small>',
				'</div>',
			'</div>',
			'<div class="row" style="margin-top:20px;">',
				'<div class="col-xs-8">',
					'<label>Translation Text</label><br/>',
					'<textarea id="' + this.dom_ids.lang_literal + '" ',
					'onchange="' + this.name + '.validateTranslationHTML();" ',
					'class="form-control input-sm" rows="' + this.text_box_rows + '" ' + placeholder + ' >',
					translate_text,
					'</textarea>',
					'<p class="small">Submit blank text to delete a translation for a selected language.</p>',
				'</div>',
				'<div class="col-xs-4">',
					'<div id="' + this.dom_ids.lang_valid + '">',
					'</div>',
					'<div id="' + this.dom_ids.lang_submitcon + '">',
					'</div>',
					'<div id="' + this.dom_ids.lang_respncon + '">',
					'</div>',
				'</div>',
			'</div>',
		].join('\n');
		return html;
	}
	this.make_localize_selection_html = function(language_code){
		// makes the selection for lanugages html
		var html_list = [];
		var sel_html = '<select id="' + this.dom_ids.lang_sel
		sel_html += '" onchange="' + this.name + '.selectLocalization();" ';
		sel_html += ' class="form-control">';
		html_list.push(sel_html);
		for (var key in this.languages) {
			if (this.languages.hasOwnProperty(key)) {
				var item = this.languages[key];
				var opt_html = '<option value="' + key + '" ';
				if (language_code != null) {
					if (language_code == key) {
						// this is the selected value
						opt_html += ' selected="selected" ';
					}
				}
				opt_html += '>';
				opt_html += item['localized'];
				opt_html += ' (' + item['label'] + ')';
				opt_html += '</option>';
				html_list.push(opt_html);
			}
		}
		html_list.push('</select>');
		var html = html_list.join('\n');
		return html;
	}
	
	/*************************************************
	 * Interface and validation functions
	 * 
	 ************************************************
	 */
	this.selectLocalization = function(){
		// run this onchange event for a selection of a language for translation
		var select_dom = document.getElementById(this.dom_ids.lang_sel);
		var language_code = select_dom.value;
		var inter_dom = document.getElementById(this.modal_inter_dom_id);
		if (this.edit_type == 'label') {
			// translate a label for an item
			var interface_html = this.make_localize_label_interface_html(language_code);
			inter_dom.innerHTML = interface_html;
			this.make_translation_submit_button(true);
		}
		else{
			//update the string translation interface
			var interface_html = this.make_localize_string_interface_html(language_code);
			inter_dom.innerHTML = interface_html;
		}
	}
	this.general_submit_processes = function(){
		// do this for all types of submits
		if (document.getElementById(this.dom_ids.lang_valid)) {
			document.getElementById(this.dom_ids.lang_valid).innerHTML = this.make_loading_gif('Submitting data...');
		}
		if (document.getElementById(this.dom_ids.lang_submitcon)) {
			document.getElementById(this.dom_ids.lang_valid).innerHTML = '';
		}
		var language_code = null;
		if (document.getElementById(this.dom_ids.lang_sel)) {
			var select_dom = document.getElementById(this.dom_ids.lang_sel);
			var language_code = select_dom.value;
		}
		var text = '';
		if (document.getElementById(this.dom_ids.lang_literal)) {
			var text = document.getElementById(this.dom_ids.lang_literal).value;
		}
		if (language_code != null){
			// we have a requested language_code designated
			if (this.localization == null) {
				this.localization = {};
			}
			this.localization[language_code] = text;
		}
	}
	this.addEditLabelTranslation = function(){
		this.general_submit_processes();
		this.ajax_add_edit_label_translation();
	}
	this.addEditContentTranslation = function(){
		this.general_submit_processes();
		this.ajax_add_edit_content_translation();
	}
	this.addEditStringTranslation = function(){
		this.general_submit_processes();
		this.ajax_add_edit_string_translation();
	}
	this.validateTranslationHTML = function(){
		// calls a function to make an ajax request to validate translation HTML
		this.ajax_validate_translation_html();
	}
	
	/*************************************************
	 * AJAX FUNCTIONS FOR ADDING, EDITING, VALIDATING TRANSLATION TEXTS
	 * ***********************************************
	 */
	this.ajax_add_edit_label_translation = function(){
		// sends an ajax request to update a label translation value
		var language_code = null;
		if (document.getElementById(this.dom_ids.lang_sel)) {
			var select_dom = document.getElementById(this.dom_ids.lang_sel);
			var language_code = select_dom.value;
		}
		var text = '';
		if (document.getElementById(this.dom_ids.lang_literal)) {
			var text = document.getElementById(this.dom_ids.lang_literal).value;
		}
		var data = {
			language: language_code,
			label: text, // the translated text for the label
			csrfmiddlewaretoken: csrftoken};	
		var url = this.make_url("/edit/update-item-basics/");
		url += encodeURIComponent(this.edit_uuid); // the edit_uuid is the item_uuid in the manifest
		return $.ajax({
				type: "POST",
				url: url,
				dataType: "json",
				context: this,
				data: data,
				success: this.ajax_add_edit_translationDone,
				error: function (request, status, error) {
					alert('Translation adding or update failed, sadly. Status: ' + request.status);
				} 
			});
	}
	this.ajax_add_edit_content_translation = function(){
		// sends an ajax request to update a label translation value for a content field
		// such as an abstract, short description, document content, or a skos:note
		var language_code = null;
		if (document.getElementById(this.dom_ids.lang_sel)) {
			var select_dom = document.getElementById(this.dom_ids.lang_sel);
			var language_code = select_dom.value;
		}
		var text = '';
		if (document.getElementById(this.dom_ids.lang_literal)) {
			var text = document.getElementById(this.dom_ids.lang_literal).value;
		}
		var data = {
			language: language_code,
			content: text, // the translated text for the content
			content_type: this.content_type,
			csrfmiddlewaretoken: csrftoken};	
		var url = this.make_url("/edit/update-item-basics/");
		url += encodeURIComponent(this.edit_uuid); // the edit_uuid is the item_uuid in the manifest
		return $.ajax({
				type: "POST",
				url: url,
				dataType: "json",
				context: this,
				data: data,
				success: this.ajax_add_edit_translationDone,
				error: function (request, status, error) {
					alert('Translation adding or update failed, sadly. Status: ' + request.status);
				} 
			});
	}
	this.ajax_add_edit_string_translation = function(){
		// sends an ajax request to update a string translation value for a string field
		var language_code = null;
		if (document.getElementById(this.dom_ids.lang_sel)) {
			var select_dom = document.getElementById(this.dom_ids.lang_sel);
			var language_code = select_dom.value;
		}
		var text = '';
		if (document.getElementById(this.dom_ids.lang_literal)) {
			var text = document.getElementById(this.dom_ids.lang_literal).value;
		}
		var data = {
			language: language_code,
			content: text,
			csrfmiddlewaretoken: csrftoken};	
		var url = this.make_url("/edit/add-edit-string-translation/");
		url += encodeURIComponent(this.edit_uuid); // the edit_uuid is the string_uuid
		return $.ajax({
				type: "POST",
				url: url,
				dataType: "json",
				context: this,
				data: data,
				success: this.ajax_add_edit_translationDone,
				error: function (request, status, error) {
					alert('Translation adding or update failed, sadly. Status: ' + request.status);
				} 
			});
	}
	this.ajax_add_edit_translationDone = function(data){
		// handle responses to adding, editing string translations
		if (data.ok) {
			// success
			var html = [
				'<div style="margin-top: 10px;">',
					'<div class="alert alert-success small" role="alert">',
						'<span class="glyphicon glyphicon-ok-circle" aria-hidden="true"></span>',
						'<span class="sr-only">Success:</span>',
						'Update done.',
					'</div>',
				'</div>'
			].join('\n');
			if (document.getElementById(this.dom_ids.lang_respncon)) {
				var act_dom = document.getElementById(this.dom_ids.lang_respncon);
				act_dom.innerHTML = html;
				setTimeout(function() {
					// display an OK message for a short time
					act_dom.innerHTML = '';
				}, 4500);
			}
		}
		else{
			// failure
			var html = [
				'<div style="margin-top: 10px;">',
					'<div class="alert alert-danger small" role="alert">',
						'<span class="glyphicon glyphicon-ok-circle" aria-hidden="true"></span>',
						'<span class="sr-only">Problem:</span>',
						'Update failed.',
					'</div>',
				'</div>'
			].join('\n');
			if (document.getElementById(this.dom_ids.lang_respncon)) {
				var act_dom = document.getElementById(this.dom_ids.lang_respncon);
				act_dom.innerHTML = html;
				setTimeout(function() {
					// display an OK message for a short time
					act_dom.innerHTML = '';
				}, 4500);
			}
		}
	}
    this.ajax_validate_translation_html = function(){
		// AJAX request to validate HTML of translation text
		if (document.getElementById(this.dom_ids.lang_literal)) {
			var text = document.getElementById(this.dom_ids.lang_literal).value;
			var url = this.make_url('/edit/html-validate/');
			var data = {
				text: text,
				csrfmiddlewaretoken: csrftoken};
			return $.ajax({
				type: "POST",
				url: url,
				dataType: "json",
				context: this,
				data: data,
				success: this.ajax_validate_translation_htmlDone,
				error: function (request, status, error) {
					alert('Request to validate translation HTML failed, sadly. Status: ' + request.status);
				}
			});
		}
		else{
			return false;
		}
	}
	this.ajax_validate_translation_htmlDone = function(data){
		//after a successful translation response
		if (data.ok) {
			var val_mes = 'Input text OK to use as HTML';
			this.make_translation_submit_button(true);
			this.make_translation_validation_html(val_mes, true);
		}
		else{
			var val_mes = data.errors.html;
			this.make_translation_submit_button(false);
			this.make_translation_validation_html(val_mes, false);
		}
	}
	/***************************************************************
	 * Code for Making Responses to Validation, Submission buttons
	 ***************************************************************
	 */
	this.make_translation_submit_button = function(is_valid){
		//makes a submission button for translation
		var language_code = null;
		if (document.getElementById(this.dom_ids.lang_sel)) {
			var select_dom = document.getElementById(this.dom_ids.lang_sel);
			var language_code = select_dom.value;
		}
		if (this.edit_type == 'label') {
			var sub_function = this.name + '.addEditLabelTranslation();';
		}
		else if (this.edit_type == 'content') {
			var sub_function = this.name + '.addEditContentTranslation();';
		}	
		else{
			var sub_function = this.name + '.addEditStringTranslation();';
		}
		if (is_valid && language_code != null) {
			var button_html = [
				'<div style="margin-top: 10px;">',
					'<button class="btn btn-success btn-block" onclick="' + sub_function + ' return false;">',
					'<span class="glyphicon glyphicon-cloud-upload" aria-hidden="true"></span>',
					' Submit',
					'</button>',
				'</div>'
			].join('\n');
		}
		else if (is_valid == false && language_code != null) {
			
			if (document.getElementById(this.dom_ids.lang_valid_val)) {
				document.getElementById(this.dom_ids.lang_valid_val).value = '1';
			}
			
			//code allow submission of bad HTML
			var button_html = [
				'<div style="margin-top: 10px;">',
					'<button class="btn btn-warning btn-block" onclick="' + sub_function + ' return false;">',
					'<span class="glyphicon glyphicon-cloud-upload" aria-hidden="true"></span>',
					' Submit Anyway',
					'</button>',
				'</div>'
			].join('\n');
		}
		else{
			var button_html = [
				'<div style="margin-top: 10px;">',
					'<button class="btn btn-warning btn-block" disabled="disbled">',
					'<span class="glyphicon glyphicon-cloud-upload" aria-hidden="true"></span>',
					' Submit',
					'</button>',
					'<p class="small">Be sure to select a language</p>',
				'</div>'
			].join('\n');
			button_html = '';
		}
		if (document.getElementById(this.dom_ids.lang_submitcon)) {
			document.getElementById(this.dom_ids.lang_submitcon).innerHTML = button_html;
		}
		return button_html;
	}
	this.make_translation_validation_html = function(message_html, is_valid){
		if (is_valid) {
			var icon_html = '<span class="glyphicon glyphicon-ok-circle" aria-hidden="true"></span>';
			var alert_class = "alert alert-success";
			var val_status = '<input id="' + this.dom_ids.lang_valid_val + '" type="hidden" value="1" />';
		}
		else{
			var icon_html = '<span class="glyphicon glyphicon-warning-sign" aria-hidden="true"></span>';
			var alert_class = this.invalid_alert_class;
			var val_status = '<input id="' + this.dom_ids.lang_valid_val + '" type="hidden" value="0" />';
		}
		var alert_html = [
				'<div role="alert" class="' + alert_class + '" >',
					icon_html,
					message_html,
					val_status,
				'</div>'
			].join('\n');
		
		if (document.getElementById(this.dom_ids.lang_valid)) {
			var act_dom = document.getElementById(this.dom_ids.lang_valid);
			act_dom.innerHTML = alert_html;
		}
		else{
			alert("cannot find " + this.dom_ids.lang_valid);
		}
	}
	
	/*
	 * Supplemental Functions (used throughout)
	 */ 
	this.make_url = function(relative_url){
	//makes a URL for requests, checking if the base_url is set	
		 //makes a URL for requests, checking if the base_url is set
		var rel_first = relative_url.charAt(0);
		if (typeof base_url != "undefined") {
			var base_url_last = base_url.charAt(-1);
			if (base_url_last == '/' && rel_first == '/') {
				return base_url + relative_url.substring(1);
			}
			else{
				return base_url + relative_url;
			}
		}
		else{
			if (rel_first == '/') {
				return '../..' + relative_url;
			}
			else{
				return '../../' + relative_url;
			}
		}
	}
	this.make_loading_gif = function(message){
		var src = this.make_url('/static/oc/images/ui/waiting.gif');
		var html = [
			'<div class="row">',
			'<div class="col-sm-1">',
			'<img alt="loading..." src="' + src + '" />',
			'</div>',
			'<div class="col-sm-11">',
			message,
			'</div>',
			'</div>'
			].join('\n');
		return html;
	}
}