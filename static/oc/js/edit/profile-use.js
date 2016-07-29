/*
 * Functions to create or edit an item using an input a profile
 */

function useProfile(profile_uuid, edit_uuid, edit_item_type, edit_new){
	this.act_dom_id = "profile-data";
	this.act_meta_dom_id = "profile-meta";
	this.obj_name = "profile_obj";
	this.project_uuid = project_uuid;
	this.profile_uuid = profile_uuid;
	this.edit_uuid = edit_uuid;
	this.item_type = edit_item_type;
	this.edit_new = edit_new;
	this.label_prefix = ''; // for composing new labels
	this.label_id_len = false; //for composing new labels
	this.context_uuid = false; //for creating a new item
	this.item_json_ld_obj = false;
	this.profile_data = false;
	this.panel_nums = [0]; // id number for the input profile panel, used for making a panel dom ID
	this.fields = []; // list of field objects used for data entry
	this.submit_all_dom_id = 'submit-all-fields-outer';
	this.fields_complete_dom_id = 'fields-complete-message-outer';
	this.profile_items_dom_id = 'recent-profile-items-outer';
	
	this.get_all_data = function(){
		//AJAX request to get data about a profile
		this.show_loading();
		if (this.edit_new) {
			// we've got a new item, so don't look for existing JSON-LD data
            this.get_profile_data().then(this.getProfileItems);
		}
		else{
			// we've got an existing item, so look for existing JSON-LD data first
			this.getItemJSON().then(this.get_profile_data).then(this.getProfileItems);
		}
	}
	this.getItemJSON = function(){
		/* gets the item JSON-LD from the server */
		this.item_json_ld_obj = new item_object(this.item_type, this.edit_uuid);
		var url = this.make_url("/" + this.item_type + "/" + encodeURIComponent(this.item_json_ld_obj.uuid) + ".json");
		// so as to get hashes for individual assertions, keep things easy
		var data = {hashes: true};
		return $.ajax({
			type: "GET",
			url: url,
			context: this,
			dataType: "json",
			data: data,
			success: this.getItemJSONDone,
			error: function (request, status, error) {
				alert('Item JSON retrieval failed, sadly. Status: ' + request.status);
			}
		});
	}
	this.getItemJSONDone = function(data){
		/* the JSON-LD becomes this object's data */
		this.item_json_ld_obj.data = data;
	}
	this.get_profile_data = function(){
		// AJAX request to get data about a profile
		var url = this.make_url("/edit/inputs/profiles/") + encodeURIComponent(this.profile_uuid) + ".json";
		return $.ajax({
			type: "GET",
			url: url,
			dataType: "json",
			context: this,
			success: this.get_profile_dataDone,
			error: function (request, status, error) {
				alert('Data entry profile retrieval failed, sadly. Status: ' + request.status);
			} 
		});
	}
	this.get_profile_dataDone = function(data){
		this.profile_data = data;		
		// console.log(this.item_json_ld_obj);
		// console.log(this.profile_data);
		this.item_type = data.item_type;
		this.display_profile_data();
	}
	this.getProfileItems = function(){
		
		var act_dom = document.getElementById(this.profile_items_dom_id);
		act_dom.innerHTML = this.make_loading_gif('Listing related items...');
		
		var url = this.make_url('/edit/inputs/profile-item-list/' + encodeURIComponent(this.profile_uuid));
		var data = {sort: '-label,-revised'};
		return $.ajax({
			type: "GET",
			url: url,
			context: this,
			dataType: "json",
			data: data,
			success: this.getProfileItemsDone,
			error: function (request, status, error) {
				alert('Profile created items retrieval failed, sadly. Status: ' + request.status);
			}
		});
	}
	
	
	/*******************************************
	 * Initial display of the profile and data (if not creating a new item)
	 *
	 * ****************************************/
	this.display_profile_data = function(){
		if (document.getElementById(this.act_meta_dom_id)) {
			// make metadata about the profile
			// and put into the right dom id
			var act_dom = document.getElementById(this.act_meta_dom_id);
			var meta_html = this.make_profile_meta_html();
			act_dom.innerHTML = meta_html;
		}
		if (document.getElementById(this.act_dom_id)) {
			//put the field groups into the right dom ID
			var act_dom = document.getElementById(this.act_dom_id);
			var html = "";
			html += '<div id="field-groups">';
			html += this.make_field_groups_html();
			html += '</div>';
			act_dom.innerHTML = html;
			this.postprocess_fields();
		}
	}
	this.getProfileItemsDone = function(data){
		// handle results of displaying the profile
		console.log('Profiles items data');
		console.log(data);
		var act_dom = document.getElementById(this.profile_items_dom_id);
		act_dom.innerHTML = '';
		if (data.count > 0) {
			var html_l = ['<ul class="list-unstyled">'];
			for (var i = 0, length = data.items.length; i < length; i++) {
				var item = data.items[i];
				var url = this.make_url('/' + item.item_type + '/' + encodeURIComponent(item.uuid));
				var rec = [
					'<li>',
						'<a href="' + url + '" target="_blank">',
						'<span class="glyphicon glyphicon-new-window" aria-hidden="true"></span> ',
						item.label,
						'</a>',
					'</li>',
				].join('\n');
				html_l.push(rec);
			}
			html_l.push('</ul>');
			act_dom.innerHTML = html_l.join('\n');
		}
		else{
			act_dom.innerHTML = 'No items with this profile.';
		}
		
	}
	
	
	/* ---------------------------------------
	 * Profile HTML display
	 * functions
	 * ---------------------------------------
	 */
	this.make_profile_meta_html = function(){
		// makes HTML for profile metadata viewing and editing
		var num_fields = 0;
		var data = this.profile_data;
		for (var i = 0, length = data.fgroups.length; i < length; i++) {
			var fgroup = data.fgroups[i];
			num_fields += fgroup.fields.length; 
		}
		var title_html = "About: " + data.label;
		var body_html = [
		'<div>',
			'<div class="row">',
				'<div class="col-xs-12" id="' + this.submit_all_dom_id + '">',
				'</div>',
			'</div>',
			'<div class="row">',
				'<div class="col-xs-12" id="' + this.fields_complete_dom_id + '">',
				'</div>',
			'</div>',
			'<div class="row">',
				'<div class="col-xs-5">',
					'<dl>',
					'<dt>Item Type</dt>',
					'<dd>' + this.describe_item_type_html(data.item_type) + '</dd>',
					'<dt>Fields</dt>',
					'<dd>' + num_fields + ' fields in ' + data.fgroups.length + ' groups</dd>',
					'</dl>',
				'</div>',
				'<div class="col-xs-7">',
					'<label>Recent Items</label>',
					'<div id="' + this.profile_items_dom_id + '">',
					'</div>',
				'</div>',
			'</div>',
			'<div class="row">',
				'<div class="col-xs-12">',
					'<dl>',
					'<dt>Explanatory Note</dt>',
					'<dd>' + data.note + '</dd>',
					'<dt>Edit Profile</dt>',
					'<dd>',
					'<a title="Edit this Input Profile" target="_blank" ',
					'href="' + this.make_url('/edit/inputs/profiles/' +  encodeURIComponent(data.id) + '/edit') + '">',
					'<span class="glyphicon glyphicon-edit" aria-hidden="true"></span> Edit',
					'</a>',
					'</dd>',
					'</dl>',
				'</div>',
			'</div>',
		// '<div class="row">',
		// '<div class="col-xs-12" id="profile-items">',
		// '</div>',
		// '</div>',
		'</div>',
		].join('\n');
		var panel_num = this.get_next_panel_num();
		var meta_panel = new panel(panel_num);
		meta_panel.title_html = title_html;
		meta_panel.body_html = body_html;
		return meta_panel.make_html();
	}
	
	
	
	/* ---------------------------------------
	 * Validation and New Item Creation or mass Update 
	 * ---------------------------------------
	 */
	this.prep_all_create_update = function(){
		// prepares a general creation or update button
		var submit_ok = false;
		var required_valid = this.check_valid_oc_required();
		if (required_valid.all) {
			// all the required fields are valid
			submit_ok = true;
			var button_html = this.make_valid_submit_all_button_html();
			var message_html = this.make_submit_all_validation_message_html(true, '');
		}
		else{
			// some missing validation fields
			var error_html = 'Still needed:';
			error_html += '<ul>';
			for (var i = 0, length = required_valid.missing.length; i < length; i++) {
				error_html += '<li>' + required_valid.missing[i] + '</li>';
			}
			error_html += '</ul>';
			var message_html = this.make_submit_all_validation_message_html(false, error_html);
			
			var button_html = [
				'<div style="margin-top: 22px;">',
				'<button class="btn large btn-default btn-block" disabled="disabled">',
				'<span class="glyphicon glyphicon-cloud-upload" aria-hidden="true"></span> Submit',
				//' Delete',
				'</button>',
				'</div>'
			].join('\n');
			
			if (document.getElementById(this.submit_all_dom_id)) {
				document.getElementById(this.submit_all_dom_id).innerHTML = button_html;
			}
		}
		
		return submit_ok;
	}
	this.make_valid_submit_all_button_html = function(){
		// makes a submit_all button when fields are valid
		var button_html = [
			'<div>',
			'<button class="btn large btn-primary btn-block" onclick="' + this.obj_name + '.submitAll();">',
			'<span class="glyphicon glyphicon-cloud-upload" aria-hidden="true"></span> Submit',
			//' Delete',
			'</button>',
			'</div>'
		].join('\n');
		
		if (document.getElementById(this.submit_all_dom_id)) {
			document.getElementById(this.submit_all_dom_id).innerHTML = button_html;
		}
		
		return button_html;
	}
	this.make_submit_all_validation_message_html = function(is_valid, error_text){
		// makes a validation message for
		if (is_valid) {
			var icon_html = '<span class="glyphicon glyphicon-ok-circle" aria-hidden="true"></span>';
			var alert_class = "alert alert-success";
			if (this.edit_new) {
				var message_text = 'Ready to create the item.';
			}
			else{
				var message_text = 'Ready to update the item.';
			}
		}
		else{
			var icon_html = '<span class="glyphicon glyphicon-warning-sign" aria-hidden="true"></span>';
			var alert_class = "alert alert-warning";
			var message_text = error_text;
		}
		var message_html = [
			'<div role="alert" class="' + alert_class + '" style="margin-top: 5px;">',
				icon_html,
				message_text,
			'</div>'
		].join('\n');
		
		if (document.getElementById(this.fields_complete_dom_id)) {
			document.getElementById(this.fields_complete_dom_id).innerHTML = message_html;
		}
		return message_html;
	}
	this.check_valid_oc_required = function(){
		// checks to see if oc_required fields are valid
		var required_valid = {all: true,
		                      missing: []};
		for (var i = 0, length = this.fields.length; i < length; i++) {
			var field = this.fields[i];
			if (field.oc_required) {
				console.log('Checking: ' + field.label);
				if (field.predicate_uuid == field.label_pred_uuid) {
					// we have a label field! use the prefix, and id_len to set to
					// this object's label prefix and id_len
					this.label_id_len = field.label_id_len;
					this.label_prefix = field.label_prefix;
				}
				if (0 in field.value_num_validations) {
					//checks if the first, or value_num 0 value
					var is_valid = field.value_num_validations[0];
					if (is_valid == false) {
						// we have an invalid required field value!!!
						required_valid.all = false;
						required_valid.missing.push(field.label);
					}
					console.log('OC-req-0-found: ' + field.label);
					// console.log(required_valid);
				}
				else{
					required_valid.all = false;
					required_valid.missing.push(field.label);
					console.log('OC-req-0-not-found: ' + field.label);
				}
			}
		}
		return required_valid;
	}
	this.submitAll = function(){
		var submit_ok = this.prep_all_create_update();
		if (submit_ok) {
			// runs the AJAX request to submit all,
			// then gets recent profile items
			this.ajax_submit_all().then(this.getProfileItems);
		}
	}
	this.ajax_submit_all = function(){
		// executes the AJAX request for submitting all
		var data = {csrfmiddlewaretoken: csrftoken};
		var field_key = this.id;
		field_data = {};
		for (var i = 0, length = this.fields.length; i < length; i++) {
			var field = this.fields[i];
			var act_field = field.make_field_submission_obj(true);
			var field_key = act_field.field_uuid;
			if (act_field.values.length > 0 && field.values_modified) {
				field_data[field_key] = act_field;
			}
		}
		console.log(field_data);
		data['field_data'] = JSON.stringify(field_data, null, 2);
		var url = this.make_url("/edit/inputs/create-update-profile-item/");
		url += encodeURIComponent(this.profile_uuid);
		url += '/' + encodeURIComponent(this.edit_uuid);
		return $.ajax({
			type: "POST",
			url: url,
			dataType: "json",
			context: this,
			data: data,
			success: this.submitDataDone,
			error: function (request, status, error) {
				alert('Data submission failed, sadly. Status: ' + request.status);
			} 
		});
	}
	this.submitDataDone = function(data){
		if (data.ok) {
			// the request was OK
			var relative_url = '/edit/inputs/profiles/' + this.profile_uuid + '/new';
			if (this.label_prefix != '' || this.label_id_len != false) {
				// we should pass parameters to make a default label for the next item
				// in this profile
				var params = {};
				if (this.label_prefix != ''){
					params['prefix'] = this.label_prefix;
				}
				if (this.label_id_len != false){
					if(this.label_id_len > 0){
						params['id_len'] = this.label_id_len;
					}
				}
				var next_url = this.make_url_params(relative_url, params);
			}
			else{
				var next_url = this.make_url(relative_url);
			}
			
			// url for the item created or updated
			var edited_url = this.make_url('/' + data.change.item_type + '/' + data.change.uuid);
			
			if (this.edit_new) {
				// we succeeded in creating a new item
				var mess = [
					'<p><strong>Item successfully created!</strong></p>',
				    '<p>Options:</p>',
					'<ul>',
						'<li>',
							'<a href="' + next_url + '">',
							'Create another ' + this.profile_data.label + ' item',
							'</a>',
						'</li>',
						'<li>',
							'View new item: <a href="' + edited_url + '" target="_blank">',
							'<span class="glyphicon glyphicon-new-window" aria-hidden="true"></span> ',
							data.change.label,
							'</a>',
						'</li>',
						'<li>Stay and edit this item</li>',
					'</ul>',
				].join('\n');
				this.edit_new = false;
				
			}
			else{
				var mess = [
					'<p><strong>Item successfully updated!</strong></p>',
				    '<p>Options:</p>',
					'<ul>',
						'<li>',
							'<a href="' + next_url + '">',
							'Create another ' + this.profile_data.label + ' item',
							'</a>',
						'</li>',
						'<li>',
							'View edited item: <a href="' + edited_url + '" target="_blank">',
							'<span class="glyphicon glyphicon-new-window" aria-hidden="true"></span> ',
							data.change.label,
							'</a>',
						'</li>',
						'<li>Stay and edit this item</li>',
					'</ul>',
				].join('\n');
				this.edit_new = false;
			}
			if ('errors' in data) {
				var found_errors = false;
				var error_html = '<ul class="small">';
				var errors = data.errors;
				for (var k in errors) {
					if (errors.hasOwnProperty(k)) {
						error_html += '<li>' + errors[k] + '</li>';
						found_errors = true;
					}
				}
				error_html += '</ul>';
				if (found_errors) {
					mess += ' But there are some problems:';
					mess += error_html;
				}
				mess += error_html;
			}
			var alert_html = this.make_validation_html(mess, true);
		}
		else{
			if (this.edit_new) {
				// we succeeded in creating a new item
				var mess = 'Item creation failed! ';
			}
			else{
				var mess = 'Item updated failed. ';
			}
			if ('errors' in data) {
				var error_html = '<ul class="small">';
				var errors = data.errors;
				for (var k in errors) {
					if (errors.hasOwnProperty(k)) {
						error_html += '<li>' + errors[k] + '</li>';
					}
				}
				error_html += '</ul>';
				mess += error_html;
			}
			var alert_html = this.make_validation_html(mess, false);
		}
		if (document.getElementById(this.fields_complete_dom_id)) {
			document.getElementById(this.fields_complete_dom_id).innerHTML = alert_html;
		}
	}
	this.make_validation_html = function(message_html, is_valid){
		if (is_valid) {
			var icon_html = '<span class="glyphicon glyphicon-ok-circle" aria-hidden="true"></span>';
			var alert_class = "alert alert-success";
		}
		else{
			var icon_html = '<span class="glyphicon glyphicon-warning-sign" aria-hidden="true"></span>';
			var alert_class = this.invalid_alert_class;
		}
		var alert_html = [
				'<div role="alert" class="' + alert_class + '" >',
					icon_html,
					message_html,
				'</div>'
			].join('\n');
		return alert_html;
	}
	
	
	/* ---------------------------------------
	 * Field Group and Field HTML 
	 * ---------------------------------------
	 */
	this.make_field_groups_html = function(){
		// makes HTML for all of the field groups, each one in a panel
		var data = this.profile_data;
		var html = "";
		for (var i = 0, length = data.fgroups.length; i < length; i++) {
			var fgroup = data.fgroups[i];
			html += '<div id="' + fgroup.id + '">';
			html += this.make_field_group_html(fgroup);
			html += '</div>';
		}
		return html;
	}
	this.make_field_group_html = function(fgroup){
		// makes the HTML for a panel that contains a field group
		var field_html = '';
		var obs_num =  fgroup.obs_num;
		var raw_obs_num = obs_num - 1;
		if (raw_obs_num < 0) {
			raw_obs_num = 0;
		}
		var fields_html = [];
		for (var i = 0, length = fgroup.fields.length; i < length; i++) {
			var profile_field = fgroup.fields[i];
			var field = new edit_field();
			field.id = this.fields.length;
			field.project_uuid = this.project_uuid;
			field.profile_uuid = this.profile_uuid;
			field.field_uuid = profile_field.id;
			field.note = profile_field.note;
			field.oc_required = profile_field.oc_required;
			field.label_prefix = this.label_prefix; // for composing new labels
			field.label_id_len = this.label_id_len; //for composing new labels
			field.context_uuid = this.context_uuid; //for creating a new item
			field.pred_type = 'variable';
			field.parent_obj_name = this.obj_name;
			field.obj_name = 'fields[' + field.id + ']';
			field.add_new_data_row = true;
			field.edit_new = this.edit_new;
			field.edit_uuid = this.edit_uuid;
			field.item_type = this.item_type;
			field.label = profile_field.label;
			field.predicate_uuid = profile_field.predicate_uuid;
			field.draft_sort = this.fields.length + 1;
			field.obs_num = obs_num;
			field.obs_node = '#obs-' + obs_num;
			field.data_type = profile_field.data_type;
			field = this.add_oc_require_validation_function(field);
			if (this.item_json_ld_obj != false) {
				// show existing data for this predicate
				field.values_obj = [];
				if (profile_field.predicate_uuid == field.label_pred_uuid) {
					// we have a field for the label
					field.item_label = this.item_json_ld_obj.data.label;
				}
				else if (profile_field.predicate_uuid == field.class_pred_uuid) {
					// we have a field for class_uri
					var categories = this.item_json_ld_obj.getItemCategories();
					if (categories.length > 0) {
						field.class_uri = categories[0].id;
						field.class_label = categories[0].label;
					}
				}
				else if (profile_field.predicate_uuid == field.context_pred_uuid) {
					// we have a field for context
					var context = this.item_json_ld_obj.getParent();
					field.data_type = 'id';
					field.context_label = context.label;
					field.context_uuid = context.uuid;
					field.values_obj = [
						context
					];
				}
				else{
					var values_obj = this.item_json_ld_obj.getObsValuesByPredicateUUID(raw_obs_num, profile_field.predicate_uuid);
					console.log(values_obj);
					field.values_obj = values_obj;
				}
			}
			else{
				field.values_obj = [];
			}
			field.initialize();
			var field_html = '<tr>' + field.make_field_html() + '</tr>';
			fields_html.push(field_html);
			this.fields.push(field);
		}
		var body_html = [
			'<table class="table table-striped">',
			'<thead>',
			'<tr>',
			'<th class="col-xs-2">Field</th>',
			'<th class="col-xs-8">Values</th>',
			'</th>',
			'</tr>',
			'</thead>',
			'<tbody>',
			fields_html.join('\n'),
			'</tbody>',
			'</table>'
		].join("\n");
		var panel_num = this.get_next_panel_num();
		var meta_panel = new panel(panel_num);
		meta_panel.title_html = fgroup.label;
		meta_panel.body_html = body_html;
		return meta_panel.make_html();
	}
	this.add_oc_require_validation_function = function(field){
		// adds a function to oc_require fields. this executes when
		// a user input is validated on a value for a require field
		
		// execute this after validation is completed for required fields
		var after_validation_done = {
			obj_name: this.obj_name,
			submit_all_dom_id: this.submit_all_dom_id,
			fields_complete_dom_id: this.fields_complete_dom_id,
			fields: this.fields,
			check_valid_oc_required: this.check_valid_oc_required,
			prep_all_create_update: this.prep_all_create_update,
			make_valid_submit_all_button_html: this.make_valid_submit_all_button_html,
			make_submit_all_validation_message_html: this.make_submit_all_validation_message_html,
			exec: function(){
				this.prep_all_create_update();
			}
		};
		
		if (field.oc_required) {
			//this field is required, so add the validation function
			field.after_validation_done = after_validation_done;
		}
		return field;
	}
	this.postprocess_fields = function(){
		// activates hiearchy trees + other post-processing functions
		// than need to happen after fields are addded to the DOM
		
		for (var i = 0, length = this.fields.length; i < length; i++) {
			var field = this.fields[i];
			field.postprocess();
		}
		
		//now validate for preparing for all fields submissions
		this.prep_all_create_update(); 
	}
	
	
	
	/*
	 * GENERAL FUNCTIONS
	 */
	this.make_url_params = function(relative_url, key_values){
		// makes a url with parameters from a dict
		var url = this.make_url(relative_url);
		var new_param_chr = '?';
		for (var parameter_key in key_values) {
			if (key_values.hasOwnProperty(parameter_key)) {
				var val = key_values[parameter_key]; 
				url += new_param_chr + parameter_key + '=' + encodeURIComponent(val);
				new_param_chr = '&';
			}
		}
		return url;
	}
	this.make_url = function(relative_url){
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
	this.show_loading = function(){
		//display a spinning gif for loading
		if (document.getElementById(this.act_dom_id)) {
			var act_dom = document.getElementById(this.act_dom_id);
			var title_html = 'Loading Data Entry Profile "' + item_label + '"';
			var body_html = this.make_loading_gif('Loading...');
			loading_panel = new panel(0);
			loading_panel.title_html = title_html;
			loading_panel.body_html = body_html;
			loading_panel.collapsing = false;
			var html = loading_panel.make_html();
			act_dom.innerHTML = html;
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
	this.get_next_panel_num = function(){
		var next_panel_num = Math.max.apply(Math, this.panel_nums) + 1;
		this.panel_nums.push(next_panel_num);
		return next_panel_num;
	}
	this.describe_item_type_html = function(item_type){
		var des_type = this.describe_item_type(item_type);
		if (des_type != false) {
			var html = [
			'<span title="' + des_type.note + '">' + des_type.sup_label + '</span>',
			'<br/><samp class="uri-id">' + item_type+ '</samp>',		
			].join('\n');
		}
		else{
			var html = '<samp class="uri-id">(' + item_type + ')</samp>';		
		}
		return html;
	}
	this.describe_item_type = function(item_type){
		types = {'subjects': {'sup_label': 'Locations, objects', 'note': 'Primary records of locations, contexts, objects + ecofacts'},
		         'media': {'sup_label': 'Media', 'note': 'Media files (images, videos, 3D files, PDFs, etc.) that help document subjects items'},
					'documents': {'sup_label': 'Documents', 'note': 'Text documents HTML text records of notes, diaries, logs, and other forms of narrative'},
					'persons': {'sup_label': 'Persons, organizations', 'note': 'Persons or organizations that have some role in the project'}
					}
		var output = false;
		if (item_type in types) {
			output = types[item_type];
		}
		return output;
	}
	this.addSecs = function(d, s) {return new Date(d.valueOf()+s*1000);}
}
