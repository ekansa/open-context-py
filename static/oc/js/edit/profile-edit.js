/*
 * Functions to edit a profile
 */

function profile(uuid){
	this.act_dom_id = "profile-data";
	this.name = "act_profile";
	this.uuid = uuid;
	this.data = false;
	this.act_fgroup_uuid = false;
	this.entitySearchObj = false
	this.panel_nums = [0]; // id number for the input profile panel, used for making a panel dom ID 
	this.get_data = function(){
		//AJAX request to get data about a profile
		this.show_loading();
		var url = this.make_url("/edit/inputs/profiles/") + encodeURIComponent(this.uuid) + ".json";
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
		var url = this.make_url("/edit/inputs/profiles/") + encodeURIComponent(this.uuid) + ".json";
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
		var item_types = ['subjects',
						  'media',
						  'documents',
						  'persons'];
		var type_checked_html = {}
		for (var i = 0, length = item_types.length; i < length; i++) {
			//default HTML for each type as not checked
			type_checked_html[item_types[i]] = "";
		}
		if (data.item_type in type_checked_html) {
			// no make the active item_type checked in the type_checked_html
			type_checked_html[data.item_type] = 'checked="checked"';
		}
		var title_html = "Edit Metadata for: " + data.label;
		var body_html = [
		'<div>',
		'<div class="row">',
		'<div class="col-xs-12" style="margin-bottom:10px;">',
			'<label>Profile Item Type</label><br/>',
			'<label class="radio-inline">',
			'<input type="radio" name="edit-profile-item-type" id="edit-profile-item-type-s" ',
			'class="edit-profile-item-type" value="subjects" ' + type_checked_html['subjects'] + ' >',
			'Subjects (Locations, objects, etc.) </label>',
			'<label class="radio-inline">',
			'<input type="radio" name="edit-profile-item-type" id="edit-profile-item-type-m" ',
			'class="edit-profile-item-type" value="media" ' + type_checked_html['media'] + ' >',
			'Media (images, videos, etc.)</label>',
			'<label class="radio-inline">',
			'<input type="radio" name="edit-profile-item-type" id="edit-profile-item-type-d" ',
			'class="edit-profile-item-type" value="documents" ' + type_checked_html['documents'] + ' >',
			'Documents (text diaries, logs, etc.)</label>',
		'</div>',
		'</div>',
		'<div class="form-group">',
		'<label for="edit-item-label">Profile Label</label>',
		'<input id="edit-item-label" class="form-control input-sm" ',
		'type="text" value="' + data.label + '" />',
		'</div>',
		'<div class="form-group">',
		'<label for="edit-item-note">Explanatory Note</label>',
		'<textarea id="edit-item-note" class="form-control input-sm" rows="4">',
		data.note,
		'</textarea>',
		'</div>',
		'<div class="row">',
		'<div class="col-xs-4" id="edit-profile-button-container">',
		//'<label>Actions</label><br/>',
		'<button class="btn btn-info col-xs-5" onclick="' + this.name + '.editProfile();">',
		'<span class="glyphicon glyphicon-edit" aria-hidden="true"></span>',
		' Update',
		'</button>',
		'</div>',
		'<div class="col-xs-7" id="edit-profile-exp-container">',
		//'<label>About Data Entry Profiles</label>',
		'<p><small>A data entry profile defines a set of descriptive fields and data validation rules ',
		'for manually creating data. You should try to make simple clear labels to make data entry easier. ',
		'The <em>note</em> field should provide simple instructions to users who will do data entry tasks. ',
		'</small></p>',
		'</div>',
		'<div class="col-xs-1">',
		'</div>',
		'</div>',
		'<div class="row">',
		'<div class="col-xs-4">',
		'<button class="btn btn-danger col-xs-5" onclick="' + this.name + '.deleteProfile();">',
		'<span class="glyphicon glyphicon-remove-sign" aria-hidden="true"></span>',
		' Delete',
		'</button>',
		'</div>',
		'<div class="col-xs-7">',
		'<button class="btn btn-default" onclick="' + this.name + '.addFieldGroup();">',
		'<span class="glyphicon glyphicon-plus-sign" aria-hidden="true"></span>',
		' Add Group of Fields',
		'</button>',
		'</div>',
		'<div class="col-xs-1">',
		'</div>',
		'</div>',
		'</div>'
		].join('\n');
		var panel_num = this.get_next_panel_num();
		var meta_panel = new panel(panel_num);
		meta_panel.title_html = title_html;
		meta_panel.body_html = body_html;
		return meta_panel.make_html();
	}
	this.editProfile = function(){
		// sends AJAX request to edit a profile item
		var label = document.getElementById("edit-item-label").value;
		var note = document.getElementById("edit-item-note").value;
		var p_types = document.getElementsByClassName("edit-profile-item-type");
		for (var i = 0, length = p_types.length; i < length; i++) {
			if (p_types[i].checked) {
				var item_type = p_types[i].value;
			}
		}
		var url = this.make_url("/edit/inputs/update-profile/") + encodeURIComponent(this.uuid);
		if (label.length > 1) {
			return $.ajax({
			type: "POST",
			url: url,
			dataType: "json",
			context: this,
			data: {
				project_uuid: project_uuid,
				item_type: item_type,
				label: label,
				note: note,
				csrfmiddlewaretoken: csrftoken},
			success: this.editProfileDone,
			error: function (request, status, error) {
				alert('Data entry profile edit failed, sadly. Status: ' + request.status);
			} 
			});
		}
		else{
			alert('Please provide a label for this profile');
		}
	}
	this.editProfileDone = function(data){
		// reloads the whole page after edit to profile metadata
		//console.log(data);
		location.reload(true);
	}
	this.deleteProfile = function(){
		var main_modal_title_domID = "smallModalLabel";
		var main_modal_body_domID = "smallModalBody";
		var title_dom = document.getElementById(main_modal_title_domID);
		var body_dom = document.getElementById(main_modal_body_domID);
		var body_html = [
		'<div>',
		'<p>Do you want to delete: <strong>' + item_label + '</strong> ?</p>',
		'<div class="row">',
		'<div class="col-xs-6">',
		'<button class="btn btn-danger col-xs-8" onclick="' + this.name + '.execDeleteProfile();">',
		'<span class="glyphicon glyphicon-remove-sign" aria-hidden="true"></span>',
		' Delete',
		'</button>',
		'</div>',
		'<div class="col-xs-6">',
		'<button class="btn btn-default col-xs-8" onclick="' + this.name + '.cancelDelete();">',
		' Cancel',
		'</button>',
		'</div>',
		'</div>',
		'</div>',
		'</div>'
		].join('\n');
		title_dom.innerHTML = "Confirm Delete?";
		body_dom.innerHTML = body_html;
		$("#smallModal").modal('show');
	}
	this.execDeleteProfile = function(){
		// actually executes the delete of a profile
		var main_modal_body_domID = "smallModalBody";
		var body_dom = document.getElementById(main_modal_body_domID);
		var body_html = [
		'<div>',
		'<p>Attempting to delete "' + item_label + '" now...</p>',
		'</div>'
		].join('\n');
		body_dom.innerHTML = body_html;
		var url = this.make_url("/edit/inputs/delete-profile/") + encodeURIComponent(this.uuid);
		return $.ajax({
			type: "POST",
			url: url,
			dataType: "json",
			context: this,
			data: {
				project_uuid: project_uuid,
				csrfmiddlewaretoken: csrftoken},
			success: this.execDeleteProfileDone,
			error: function (request, status, error) {
				alert('Data entry profile edit failed, sadly. Status: ' + request.status);
			} 
			});
	}
	this.execDeleteProfileDone = function(data){
		$("#smallModal").modal('hide');
		alert('Data entry profile "' + item_label + '" deleted');
		window.location = make_url('/edit/projects/' + project_uuid);
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
		var table_html = '<table class="table table-condensed table-hover table-striped">';
		table_html += '<tbody>';
		for (var i = 0, length = fgroup.fields.length; i < length; i++) {
			var field = fgroup.fields[i];
			var sort_buttons_html = "";
			if (length > 1) {
				var sort_buttons_html = [
				'<div style="margin-top: 5px;">',
				'<button class="btn btn btn-info btn-xs" ',
				'onclick="' + this.name + '.rankField(\'' + fgroup.id + '\', \'' + field.id + '\', -1);" ',
				'title="Higher rank in sort order">',
				'<span class="glyphicon glyphicon-arrow-up"></span>',
				'</button>',
				'</div>',
				'<div style="margin-top: 2px;">',
				'<button class="btn btn btn-info btn-xs" ',
				'onclick="' + this.name + '.rankField(\'' + fgroup.id + '\', \'' + field.id + '\', 1);" ',
				'title="Lower rank in sort order">',
				'<span class="glyphicon glyphicon-arrow-down"></span>',
				'</button>',
				'</div>'
				].join("\n");
			}
			if (field.oc_required) {
				var pred_link_html = "<em>Open Context required field</em>";
				var delete_button_html = [
				'<div style="margin-top: 10px;">',
				'<button class="btn btn-danger btn-xs" ',
				'disabled="disabled" title="Delete disabled for this field">',
				'<span class="glyphicon glyphicon-remove-sign"></span>',
				'</button>',
				'</div>'
				].join('\n');
			}
			else{
				var pred_link_html = [
				'<a target="_blank" href="' + this.make_url("/predicates/" + field.predicate_uuid) + '">',
				'http://opencontext.org/predicates/' +  field.predicate_uuid + ' ',
				'<span class="glyphicon glyphicon-new-window"></span></a>'
				].join(' ');
				var delete_button_html = [
				'<div style="margin-top: 10px;">',
				'<button class="btn btn-danger btn-xs" ',
				'onclick="' + this.name + '.deleteField(\'' + fgroup.id + '\', \'' + field.id + '\');" title="Delete this field">',
				'<span class="glyphicon glyphicon-remove-sign"></span>',
				'</button>',
				'</div>'
				].join('\n');
			}
			var pred_html = [
			'<div style="padding-bottom: 15px;">',
			field.label,
			'<br/>',
			'<samp class="uri-id">',
			pred_link_html,
			'</samp>',
			'</div>'
			].join("\n");
			
			var field_html = [
			'<tr>',
			'<td class="col-xs-1">',
			delete_button_html,
			'</td>',
			'<td class="col-xs-1">',
			sort_buttons_html,
			'</td>',
			'<td class="col-xs-10">',
			pred_html,
			'</td>',
			'</tr>'
			].join('\n');
			table_html += field_html;
		}
		table_html += '</tbody>';
		table_html += '</table>';
		
		if (fgroup.note.length < 2) {
			var note = '[No explanatory note provided]';
		}
		else{
			var note = fgroup.note;
		}
		
		var body_html = [
			'<div class="well well-sm">',
			'<p><strong>',
			'<button class="btn btn-default btn-xs" ',
			'onclick="' + this.name + '.editFieldGroup(\'' + fgroup.id + '\', -1);" ',
			'title="Edit this field group">',
			'<span class="glyphicon glyphicon-edit"></span>',
			'</button>',
			'<button class="btn btn-danger btn-xs" ',
			'onclick="' + this.name + '.deleteFieldGroup(\'' + fgroup.id + '\', 1);" ',
			'title="Delete this field group">',
			'<span class="glyphicon glyphicon-remove-sign" aria-hidden="true"></span>',
			'</button>',
			'Field Group Metadata</strong></p>',
			'<div class="row">',
			'<div class="col-xs-1">',
				'<div style="margin-top: 5px;">',
					'<button class="btn btn btn-info btn-xs" ',
					'onclick="' + this.name + '.rankFieldGroup(\'' + fgroup.id + '\', -1);" ',
					'title="Higher rank in sort order">',
					'<span class="glyphicon glyphicon-arrow-up"></span>',
					'</button>',
					'</div>',
					'<div style="margin-top: 2px;">',
					'<button class="btn btn btn-info btn-xs" ',
					'onclick="' + this.name + '.rankFieldGroup(\'' + fgroup.id + '\', 1);" ',
					'title="Lower rank in sort order">',
					'<span class="glyphicon glyphicon-arrow-down"></span>',
					'</button>',
				'</div>',
			'</div>',
			'<div class="col-xs-4">',
			'<dl>',
			'<dt>Interface Visibility</dt>',
			'<dd>' + fgroup.visibility.toUpperCase() + ': ' + fgroup.vis_note + '</dd>',
			'</dl>',
			'</div>',
			'<div class="col-xs-7">',
			'<dl>',
			'<dt>Explanatory Note</dt>',
			'<dd>' + note + '</dd>',
			'</dl>',
			'</div>',
			'</div>',
			'</div>',
			'<div class="well well-sm">',
			'<p><strong>',
			'<button class="btn btn-primary btn-xs" ',
			'onclick="' + this.name + '.addField(\'' + fgroup.id + '\', -1);" ',
			'title="Add a field to this Field Group">',
			'<span class="glyphicon glyphicon-plus-sign"></span>',
			'</button>',
			' Fields (' + fgroup.fields.length + ')</strong></p>',
			table_html,
			'</div>'
		].join("\n");
		
		
		var panel_num = this.get_next_panel_num();
		var meta_panel = new panel(panel_num);
		meta_panel.title_html = fgroup.label;
		meta_panel.body_html = body_html;
		return meta_panel.make_html();
	}
	this.addFieldGroup = function(){
		var main_modal_title_domID = "myModalLabel";
		var main_modal_body_domID = "myModalBody";
		var title_dom = document.getElementById(main_modal_title_domID);
		var body_dom = document.getElementById(main_modal_body_domID);
		var body_html = this.make_field_group_edit_html(false, 'open', 'New Field Group', '');
		title_dom.innerHTML = "Create a New Group of Fields";
		body_dom.innerHTML = body_html;
		$("#myModal").modal('show');
	}
	this.editFieldGroup = function(fgroup_uuid){
		var main_modal_title_domID = "myModalLabel";
		var main_modal_body_domID = "myModalBody";
		var title_dom = document.getElementById(main_modal_title_domID);
		var body_dom = document.getElementById(main_modal_body_domID);
		var body_html = false;
		var fgroup = this.get_fieldgroup_obj(fgroup_uuid);
		if (fgroup != false) {
			this.act_fgroup_uuid = fgroup_uuid; 
			var body_html = this.make_field_group_edit_html(fgroup_uuid, fgroup.visibility, fgroup.label, fgroup.note);
			title_dom.innerHTML = 'Edit this Field Group: "' + fgroup.label + '"';
			body_dom.innerHTML = body_html;
			$("#myModal").modal('show');
		}
	}
	this.deleteFieldGroup = function(fgroup_uuid){
		var main_modal_title_domID = "smallModalLabel";
		var main_modal_body_domID = "smallModalBody";
		var title_dom = document.getElementById(main_modal_title_domID);
		var body_dom = document.getElementById(main_modal_body_domID);
		var label = "";
		var fgroup = this.get_fieldgroup_obj(fgroup_uuid);
		if (fgroup != false) {
			label = fgroup.label;
		}
		var body_html = [
		'<div>',
		'<p>Do you want to delete the Field Group: <strong>' + label + '</strong> ?</p>',
		'<div class="row">',
		'<div class="col-xs-6">',
		'<button class="btn btn-danger col-xs-8" onclick="' + this.name + '.confirmDeleteFieldGroup(\'' + fgroup_uuid + '\');">',
		'<span class="glyphicon glyphicon-remove-sign" aria-hidden="true"></span>',
		' Delete',
		'</button>',
		'</div>',
		'<div class="col-xs-6">',
		'<button class="btn btn-default col-xs-8" onclick="' + this.name + '.cancelDelete();">',
		' Cancel',
		'</button>',
		'</div>',
		'</div>',
		'</div>',
		'</div>'
		].join('\n');
		title_dom.innerHTML = "Confirm Delete?";
		body_dom.innerHTML = body_html;
		$("#smallModal").modal('show');
	}
	this.confirmDeleteFieldGroup = function(fgroup_uuid){
		var label = "";
		var fgroup = this.get_fieldgroup_obj(fgroup_uuid);
		if (fgroup != false) {
			label = fgroup.label;
		}
		var main_modal_body_domID = "smallModalBody";
		var body_dom = document.getElementById(main_modal_body_domID);
		var body_html = [
		'<div>',
		'<p>Attempting to delete "' + label + '" now...</p>',
		'</div>'
		].join('\n');
		body_dom.innerHTML = body_html;
		this.act_fgroup_uuid = false;
		this.exec_deleteFieldGroup(fgroup_uuid).then(this.get_fieldgroups_data);
	}
	this.exec_deleteFieldGroup = function(fgroup_uuid){
		// actually executes the delete of a profile
		var url = this.make_url("/edit/inputs/delete-field-group/") + encodeURIComponent(fgroup_uuid);
		return $.ajax({
			type: "POST",
			url: url,
			dataType: "json",
			context: this,
			data: {
				csrfmiddlewaretoken: csrftoken},
			success: this.execDeleteFieldGroupDone,
			error: function (request, status, error) {
				alert('Data entry profile edit failed, sadly. Status: ' + request.status);
			} 
			});
	}
	this.execDeleteFieldGroupDone = function(data){
		$("#smallModal").modal('hide');
	}
	this.make_field_group_edit_html = function(fgroup_uuid, visibility, label, note){
		
		var i = 0;
		var vis_radios_html = "";
		for (var vis_type_key in field_group_vis) {
			i += 1;
			if (vis_type_key == visibility) {
				var type_checked_html = ' checked="checked" ';
			}
			else{
				var type_checked_html = '';
			}
			var radio_html = [
				'<label class="radio-inline">',
				'<input type="radio" name="fgroup-vis-type" id="fgroup-vis-type-' + i + '" ',
				'class="fgroup-vis-type" value="' + vis_type_key + '" ' + type_checked_html + ' >',
				vis_type_key.toUpperCase() + ' ',
				'<span title="' + field_group_vis[vis_type_key] + '" class="glyphicon glyphicon-question-sign" aria-hidden="true"></span>',
				'</label>'
			].join("\n");
			vis_radios_html += radio_html;
		}
		var vis_type_html = [
			'<div class="row">',
			'<div class="col-xs-12" style="margin-bottom:10px;">',
			'<label>Field Group Visibility</label><br/>',
			vis_radios_html,
			'</div>',
			'</div>',
		].join("\n");
		
		if (fgroup_uuid == false) {
			// fgroup_uuid is false, meaning we're making an interface for
			// creating a new group of fields
			var placelabel = ' placeholder="Add a label for this group of fields" ';
			label = '';
			var controls_html = [
			'<div class="row">',
			'<div class="col-xs-4">',
			'<button class="btn btn-default" id="fgroup-button" ',
			'onclick="' + this.name + '.createUpdateFieldGroup();">',
			'<span class="glyphicon glyphicon-plus-sign" aria-hidden="true"></span>',
			' Create',
			'</button>',
			'</div>',
			'<div class="col-xs-8" id="fgroup-messaage">',
			'<p><small>A "Field Group" organizes related descriptive fields ',
			'together to make data entry easier and more understandable.',
			'</small></p>',
			'</div>',
			'</div>'
			].join("\n");
		}
		else{
			// fgroup_uuid is not false, meaning we're making an interface for
			// editing a field group
			var placelabel = '';
			var controls_html = [
			'<div class="row">',
			'<div class="col-xs-4">',
			'<button class="btn btn-default" id="fgroup-button" ',
			'onclick="' + this.name + '.createUpdateFieldGroup();">',
			'<span class="glyphicon glyphicon-edit" aria-hidden="true"></span>',
			' Update',
			'</button>',
			'</div>',
			'<div class="col-xs-8" id="fgroup-messaage">',
			'<p><small>A "Field Group" organizes related descriptive fields ',
			'together to make data entry easier and more understandable.',
			'</small></p>',
			'</div>',
			'</div>'
			].join("\n");
		}
		var html = [
		'<div>',
		vis_type_html,
		'<div class="row">',
		'<div class="col-xs-12">',
		'<input id="fgroup-uuid" type="hidden" value="' + fgroup_uuid + '" />',
		'<div class="form-group">',
		'<label for="fgroup-label">Field Group Label</label>',
		'<input id="fgroup-label" class="form-control input-sm" ',
		'type="text" value="' + label + '" ' + placelabel + ' />',
		'</div>',
		'<div class="form-group">',
		'<label for="fgroup-note">Explanatory Note</label>',
		'<textarea id="fgroup-note" class="form-control input-sm" rows="3">',
		note,
		'</textarea>',
		'</div>',
		'</div>',
		'</div>',
		controls_html,
		'</div>'
		].join("\n");
		return html;
	}
	this.createUpdateFieldGroup = function(){
		// sends AJAX request to create or edit a field group item
		var fgroup_button = document.getElementById("fgroup-button");
		fgroup_button.disabled = 'disabled';
		var mess_dom = document.getElementById("fgroup-messaage");
		mess_dom.innerHTML = this.make_loading_gif('Processing request...');
		this.exec_createUpdateFieldGroup().then(this.get_fieldgroups_data);
	}
	this.exec_createUpdateFieldGroup = function(){
		// sends AJAX request to create or edit a field group item
		var fgroup_uuid = document.getElementById("fgroup-uuid").value;
		var label = document.getElementById("fgroup-label").value;
		var note = document.getElementById("fgroup-note").value;
		var p_types = document.getElementsByClassName("fgroup-vis-type");
		for (var i = 0, length = p_types.length; i < length; i++) {
			if (p_types[i].checked) {
				var visibility = p_types[i].value;
			}
		}
		if (fgroup_uuid == "false") {
			fgroup_uuid = false;
		}
		if (fgroup_uuid == false) {
			//creating a new field group
			var url = this.make_url("/edit/inputs/create-field-group/") + encodeURIComponent(this.uuid);
		}
		else{
			//updating an existing field group
			var url = this.make_url("/edit/inputs/update-field-group/") + encodeURIComponent(fgroup_uuid);
		}
		if (label.length > 1) {
			return $.ajax({
			type: "POST",
			url: url,
			dataType: "json",
			context: this,
			data: {
				fgroup_uuid: fgroup_uuid,
				profile_uuid: this.uuid,
				project_uuid: project_uuid,
				visibility: visibility,
				label: label,
				note: note,
				csrfmiddlewaretoken: csrftoken},
			success: this.createUpdateFieldGroupDone,
			error: function (request, status, error) {
				alert('Field group creation or updated failed, sadly. Status: ' + request.status);
			} 
			});
		}
		else{
			alert('Please provide a label for this profile');
		}
	}
	this.createUpdateFieldGroupDone = function(data){
		var mess_dom = document.getElementById("fgroup-messaage");
		var html = [
		'<div class="alert alert-success" role="alert">',
		data.change.note,
		'</div>'
		].join("\n");
		mess_dom.innerHTML = html;
	}
	
	
	/* ---------------------------------------
	 * Field-Group and Field Sorting
	 * ---------------------------------------
	 */
	this.rankFieldGroup = function(fgroup_uuid, sort_change){
		// resorts a field group
		this.exec_sort_change(fgroup_uuid, sort_change).then(this.get_fieldgroups_data);
	}
	this.rankField = function(fgroup_uuid, field_uuid, sort_change){
		// resorts a field
		// set the active field group, so we only redraw this group when done
		this.act_fgroup_uuid = fgroup_uuid;
		this.exec_sort_change(field_uuid, sort_change).then(this.get_fieldgroups_data);
	}
	this.exec_sort_change = function(uuid, sort_change){
		// actually executes the resorting of the Field Group or the Field item
		var url = this.make_url("/edit/inputs/reorder-item/") + encodeURIComponent(uuid);
		return $.ajax({
			type: "POST",
			url: url,
			dataType: "json",
			context: this,
			data: {
				sort_change: sort_change,
				csrfmiddlewaretoken: csrftoken},
			success: this.exec_sort_changeDone,
			error: function (request, status, error) {
				alert('Resorting failed, sadly. Status: ' + request.status);
			} 
		});
	}
	this.exec_sort_changeDone = function(data){
		return true;
	}
	/* ---------------------------------------
	 * Field Create, Update, Delete
	 * functions
	 * ---------------------------------------
	 */
	this.addField = function(fgroup_uuid){
		//builds an interface to add a field to a group
		var fgroup = this.get_fieldgroup_obj(fgroup_uuid);
		if (fgroup != false) {
			var main_modal_title_domID = "myModalLabel";
			var main_modal_body_domID = "myModalBody";
			var title_dom = document.getElementById(main_modal_title_domID);
			var body_dom = document.getElementById(main_modal_body_domID);
			var body_html = this.create_edit_field_html(fgroup_uuid, false);
			title_dom.innerHTML = 'Add a Field to Group: "' + fgroup.label + '"';
			body_dom.innerHTML = body_html;
			$("#myModal").modal('show');
		}
	}
	this.createField = function(){
		// command to create the new field in a field-group
		// the reload the data, displaying the field group with added field
		this.exec_createField().then(this.get_fieldgroups_data);
	}
	this.exec_createField = function(){
		// command to actually create it
		var label = document.getElementById('field-label').value;
		var predicate_uuid = document.getElementById('field-pred-id').value;
		var note = document.getElementById('field-note').value;
		// url is to make the field in the active field-group
		var url = this.make_url("/edit/inputs/create-field/") + encodeURIComponent(this.act_fgroup_uuid);
		return $.ajax({
			type: "POST",
			url: url,
			dataType: "json",
			context: this,
			data: {
				label: label,
				predicate_uuid: predicate_uuid,
				note: note,
				csrfmiddlewaretoken: csrftoken},
			success: this.exec_createFieldDone,
			error: function (request, status, error) {
				alert('Creating the field failed, sadly. Status: ' + request.status);
			} 
		}); 
	}
	this.exec_createFieldDone = function(data){
		return true;
	}
	this.deleteField = function(fgroup_uuid, field_uuid){
		//set the active field group so as to only
		//re-render the current field group panel after the change
		this.act_fgroup_uuid = fgroup_uuid;
		this.exec_deleteField(field_uuid).then(this.get_fieldgroups_data);
	}
	this.exec_deleteField = function(field_uuid){
		var url = this.make_url("/edit/inputs/delete-field/") + encodeURIComponent(field_uuid);
		return $.ajax({
			type: "POST",
			url: url,
			dataType: "json",
			context: this,
			data: {
				csrfmiddlewaretoken: csrftoken},
			success: this.exec_deleteFieldDone,
			error: function (request, status, error) {
				alert('Deleting the field failed, sadly. Status: ' + request.status);
			} 
		}); 
	}
	this.exec_deleteFieldDone = function(data){
		return true;
	}
	this.selectPredicate = function(){
		var pred = this.entitySearchObj.selected_entity;
		document.getElementById('field-label').value = pred.label;
		document.getElementById('field-pred-id').value = pred.id;
		document.getElementById('field-data-type').value = this.get_human_readable_data_type(pred.data_type);
		var button_html = [
		'<button class="btn btn-default" id="field-button" ',
		'onclick="' + this.name + '.createField();">',
		'<span class="glyphicon glyphicon-plus-sign" aria-hidden="true"></span>',
		' Create',
		'</button>'
		].join(' ');
		document.getElementById('field-button-area').innerHTML = button_html;
	}
	this.create_edit_field_html = function(fgroup_uuid, field_uuid){
		this.act_fgroup_uuid = fgroup_uuid;
		var field = false;
		if (field_uuid != false){
			var label_placeholder = '';
			var pred_id_placeholder = '';
			field = this.get_field_obj(field_uuid);
			var human_field_uuid = field_uuid;
			var human_data_type = this.get_human_readable_data_type(field.data_type);
		}
		if (field == false) {
			//code for making a brand new field
			var label_placeholder = ' placeholder="Data entry label for field" ';
			var pred_id_placeholder = ' placeholder="UUID for the predicate" ';
			var human_data_type = '';
			var human_field_uuid = '[New field]';
			field = {'id': false,
					 'label': '',
			         'note': '',
					 'predicate_uuid': '',
					 'data_type': ''};
		}
		/* changes global contextSearchObj from entities/entities.js */
		var predicateSearchObj = new searchEntityObj();
		predicateSearchObj.name = this.name + ".entitySearchObj";
		predicateSearchObj.entities_panel_title = "Select Descriptive Field";
		predicateSearchObj.limit_item_type = "predicates";
		predicateSearchObj.limit_project_uuid = "0," + project_uuid;
		var afterSelectDone = {
			exec: function(){
					return act_profile.selectPredicate();
				}
			};
		predicateSearchObj.afterSelectDone = afterSelectDone;
		var entityInterfaceHTML = predicateSearchObj.generateEntitiesInterface();
		console.log(predicateSearchObj);
		this.entitySearchObj = predicateSearchObj; 
		
		var html = [
		'<div>',
		'<div class="row">',
		'<div class="col-xs-6">',
			'<div class="form-group">',
			'<label for="field-label">Field Label</label>',
			'<input id="field-label" class="form-control input-sm" ',
			'type="text" value="' + field.label + '" ' + label_placeholder + ' />',
			'</div>',
			'<div class="form-group">',
			'<label for="field-pred-id">Predicate UUID</label>',
			'<input id="field-pred-id" class="form-control input-sm" ',
			'type="text" value="' + field.predicate_uuid + '" ' + pred_id_placeholder + ' />',
			'</div>',
			'<div class="form-group">',
			'<label for="field-data-type">Data Type</label>',
			'<input id="field-data-type" class="form-control input-sm" ',
			'type="text" value="' + human_data_type + '" readonly />',
			'</div>',
			'<div class="form-group">',
			'<label for="field-note">Explanatory Note</label>',
			'<textarea id="field-note" class="form-control input-sm" rows="3">',
			field.note,
			'</textarea>',
			'</div>',
			'<div class="form-group">',
			'<input id="field-id" type="hidden" value="' + field.id + '" />',
			'<label for="field-id-hr">Field ID</label>',
			'<input id="field-id-hr" class="form-control input-sm" ',
			'type="text" value="' + human_field_uuid + '" readonly />',
			'<p class="small">ID for the field in this profile. Is different ',
			'from the Predicate UUID, because a given predicate maybe used more ',
			'than once in a data entry form.</p>',
			'</div>',
			'<div id="field-button-area">',
			'</div>',
		'</div>',
		'<div class="col-xs-6">',
		entityInterfaceHTML,
		'</div>',
		'</div>',
		'</div>'
		].join("\n");
		return html;
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
}