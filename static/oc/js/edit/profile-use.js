/*
 * Functions to edit a profile
 */

function useProfile(profile_uuid, edit_uuid, edit_new){
	this.act_dom_id = "profile-data";
	this.name = "act_profile";
	this.profile_uuid = profile_uuid;
	this.edit_uuid = edit_uuid;
	this.edit_new = edit_new;
	this.label_prefix = '';
	this.label_id_len = false;
	this.data = false;
	this.act_fgroup_uuid = false;
	this.entitySearchObj = false
	this.panel_nums = [0]; // id number for the input profile panel, used for making a panel dom ID 
	this.get_data = function(){
		//AJAX request to get data about a profile
		this.show_loading();
		var url = this.make_url("/edit/inputs/profiles/") + encodeURIComponent(this.profile_uuid) + ".json";
		return $.ajax({
			type: "GET",
			url: url,
			dataType: "json",
			context: this,
			success: this.get_dataDone,
			error: function (request, status, error) {
				alert('Data entry profile retrieval failed, sadly. Status: ' + request.status);
			} 
		});
	}
	this.get_dataDone = function(data){
		this.data = data;
		if (document.getElementById(this.act_dom_id)) {
			var act_dom = document.getElementById(this.act_dom_id);
			var html = "";
		    // creates metadata edit interface in a collapsable panel, id=1
			html += this.make_profile_meta_html(data);
			html += '<div id="field-groups">';
			html += this.make_field_groups_html(data);
			html += '</div>';
			act_dom.innerHTML = html;
		}
	}
	this.get_fieldgroups_data = function(){
		// gets field data for displaying field groups
		var url = this.make_url("/edit/inputs/profiles/") + encodeURIComponent(this.profile_uuid) + ".json";
		return $.ajax({
			type: "GET",
			url: url,
			dataType: "json",
			context: this,
			success: this.get_fieldgroups_dataDone,
			error: function (request, status, error) {
				alert('Data entry profile retrieval failed, sadly. Status: ' + request.status);
			} 
		});
	}
	this.get_fieldgroups_dataDone = function(data){
		// this updates only a portion of the
		// page
		$("#myModal").modal('hide');
		$("#smallModal").modal('hide');
		this.data = data;
		var done = false;
		if (this.act_fgroup_uuid != false) {
			if (document.getElementById(this.act_fgroup_uuid)) {
				var fgroup = this.get_fieldgroup_obj(this.act_fgroup_uuid);
				if (fgroup != false) {
					// now update the HTML for this particular field group
					var act_dom = document.getElementById(fgroup.id);
					act_dom.innerHTML = this.make_field_group_html(fgroup);
					done = true;
				}
			}
			// now set it back to false after we used it
			this.act_fgroup_uuid = false;
		}
		if (done == false) {	
			if (document.getElementById("field-groups")) {
				// just update the field groups
				var act_dom = document.getElementById("field-groups");
				act_dom.innerHTML = this.make_field_groups_html(data);
			}
			else{
				// regenerate the whole profile
				this.get_dataDone(data);
			}
		}
	}
	
	/* ---------------------------------------
	 * Profile Update, Delete
	 * functions
	 * ---------------------------------------
	 */
	
	this.make_profile_meta_html = function(data){
		// makes HTML for profile metadata viewing and editing
		var num_fields = 0;
		for (var i = 0, length = data.fgroups.length; i < length; i++) {
			var fgroup = data.fgroups[i];
			num_fields += fgroup.fields.length; 
		}
		var title_html = "About Profile: " + data.label;
		var body_html = [
		'<div>',
		'<div class="row">',
		'<div class="col-xs-4">',
			'<dl>',
			'<dt>Item Type</dt>',
			'<dd>' + this.describe_item_type_html(data.item_type) + '</dd>',
			'<dt>Fields</dt>',
			'<dd>' + num_fields + ' fields in ' + data.fgroups.length + ' groups</dd>',
			'</dl>',
		'</div>',
		'<div class="col-xs-8">',
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
		'</div>',
		].join('\n');
		var panel_num = this.get_next_panel_num();
		var meta_panel = new panel(panel_num);
		meta_panel.title_html = title_html;
		meta_panel.body_html = body_html;
		return meta_panel.make_html();
	}
	
	
	
	
	/* ---------------------------------------
	 * Field Group Create, Update, Delete
	 * functions
	 * ---------------------------------------
	 */
	this.make_field_groups_html = function(data){
		// makes HTML for all of the field groups, each one in a panel
		var html = ""
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
		for (var i = 0, length = fgroup.fields.length; i < length; i++) {
			var field = fgroup.fields[i];
			field_html += '<tr><td>';
			if (field.predicate_uuid == 'oc-gen:label') {
				field_html += this.make_label_field_html(field);
			}
			else{
				field_html += this.make_field_html(field);
			}
			field_html += '</td></tr>';
		}
		var body_html = [
			'<table class="table table-striped">',
			'<tbody>',
			field_html,
			'</tbody>',
			'</table>'
		].join("\n");
		var panel_num = this.get_next_panel_num();
		var meta_panel = new panel(panel_num);
		meta_panel.title_html = fgroup.label;
		meta_panel.body_html = body_html;
		return meta_panel.make_html();
	}
	this.make_field_html = function(field){
		
		var html = [
		'<div class="row">',
		'<div class="col-xs-1">',
      this.make_field_update_buttom(field.id),
		'</div>',
		'<div class="col-xs-5">',
		'<div class="form-group">',
		'<label for="f-' + field.id + '">' + field.label + '</label>',
		'<input id="f-' + field.id + '" class="form-control input-sm" ',
		'type="text" value="" />',
		'</div>',
		'</div>',
		'<div class="col-xs-6">',
		field.note,
		'</div>',
		'</div>'
		].join("\n");
		return html;
	}
	this.make_label_field_html = function(field){
		// makes special HTML for the label field
		if (this.edit_new) {
			var label_placeholder = ' placeholder="Type a label for this item" ';
		}
		else{
			var label_placeholder = '';
		}
		if (this.label_prefix.length > 0) {
			var prefix_placeholder = '';
		}
		else{
			var prefix_placeholder = ' placeholder="Labeling prefix" ';
		}
		if (!this.label_id_len) {
			var digit_len_val = '';
		}
		else{
			var digit_len_val = this.label_id_len;
		}
		var html = [
		'<div class="row">',
		'<div class="col-xs-1">',
      this.make_field_update_buttom(field.id),
		'</div>',
		'<div class="col-xs-5">',
			'<div class="form-group">',
			'<label for="f-' + field.id + '">' + field.label + '</label>',
			'<input id="f-' + field.id + '" class="form-control input-sm" ',
			'type="text" value="" ' + label_placeholder,
			'onkeydown="' + this.name + '.checkLabel(\'' + field.id + '\');" />',
			'</div>',
			'<div class="well well-sm">',
			'<form class="form-horizontal">',
			'<div class="form-group">',
				'<label for="label-prefix" class="col-sm-5 control-label">Label Prefix</label>',
				'<div class="col-sm-5">',
				'<input id="label-prefix" class="form-control input-sm" ',
				'type="text" value="' + this.label_prefix + '" ' + prefix_placeholder,
				'onkeydown="' + this.name + '.checkLabel(\'' + field.id + '\');" />',
				'</div>',
			'</div>',
			'<div class="form-group">',
				'<label for="label-prefix" class="col-sm-5 control-label">ID Digit Length</label>',
				'<div class="col-sm-3">',
				'<input id="label-prefix" class="form-control input-sm" ',
				'type="text" value="' + digit_len_val + '" ',
				'onkeydown="' + this.name + '.checkLabel(\'' + field.id + '\');" />',
				'</div>',
			'</div>',
			'</form>',
			'<div class="form-group">',
			'<label>Label Unique within:</label><br/>',
			'<label class="radio-inline">',
			'<input type="radio" name="label-unique" id="label-unique-p" ',
			'class="label-unique" value="project" checked="checked" >',
			'Entire project</label>',
			'<label class="radio-inline">',
			'<input type="radio" name="label-unique" id="label-unique-c" ',
			'class="label-unique" value="context" >',
			'Immediate Context</label>',
			'</div>',
			'</div>',
		'</div>',
		'<div class="col-xs-6">',
		field.note,
		'</div>',
		'</div>'
		].join("\n");
		return html;
	}
	this.make_field_update_buttom = function(field_uuid){
		
		var button_html = [
		'<label>Update</label>',
		'<button class="btn btn-default" onclick="' + this.name + '.updateField(\'' + field_uuid + '\');">',
		'<span class="glyphicon glyphicon-cloud-upload" aria-hidden="true"></span>',
		//' Delete',
		'</button>',
		].join('\n');

		return button_html;
	}
	this.checkLabel = function(field_uuid){
		
	}
	
	/* ---------------------------------------
	 * Helper functions
	 * used throughout
	 * ---------------------------------------
	 */
	this.get_fieldgroup_obj = function(fgroup_uuid){
		// looks through the list of fieldgroups from the downloaded
		// data kept in memory to find an object for the
		// field group with the right UUID
		var output_fgroup = false;
		for (var i = 0, length = this.data.fgroups.length; i < length; i++) {
			var fgroup = this.data.fgroups[i];
			if (fgroup.id == fgroup_uuid){
				output_fgroup = fgroup;
				break;
			}
		}
		return output_fgroup; 
	}
	this.get_field_obj_in_fieldgroup = function(fgroup, field_uuid){
		// looks for a field in a field group
		var output_field = false;
		for (var i = 0, length = fgroup.fields.length; i < length; i++) {
			var field = fgroup.fields[i];
			if (field.id == field_uuuid) {
				output_field = field;
				break;
			}
		}
		return output_field;
	}
	this.get_field_obj = function(field_uuid){
		// looks through the list of fieldgroups from the downloaded
		// data kept in memory to find an object for the
		// field group with the right UUID
		var output_field = false;
		for (var i = 0, length = this.data.fgroups.length; i < length; i++) {
			var fgroup = this.data.fgroups[i];
			var field = this.get_field_obj_in_fieldgroup(fgroup, field_uuid);
			if (field != false) {
				output_field = field;
				break;
			}
		}
		return output_field; 
	}
	this.cancelDelete = function(){
		$("#smallModal").modal('hide');
	}
	this.get_human_readable_data_type = function(data_type){
		// gets the human readable version of a data-type
		var data_types = {
			'id': 'URI identified categories/types',
			'xsd:double': 'Decimal',
			'xsd:integer': 'Integer',
			'xsd:boolean': 'True/false (Boolean)',
			'xsd:date': 'Calendar date / datetime',
			'xsd:string': 'Alphanumeric text'
		};
		if (data_type in data_types) {
			return data_types[data_type];
		}
		else{
			return '[Unknown: ' + data_type + ']';
		}
	}
	this.make_url = function(relative_url){
	//makes a URL for requests, checking if the base_url is set	
		if (typeof base_url != "undefined") {
			return base_url + relative_url;
		}
		else{
			return '../../' + relative_url;
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
}