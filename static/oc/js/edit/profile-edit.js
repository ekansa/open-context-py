/*
 * Functions to edit a profile
 */

function profile(uuid){
	this.act_dom_id = "profile-data";
	this.name = "act_profile";
	this.uuid = uuid;
	this.data = false;
	this.act_fgroup_uuid = false;
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
				for (var i = 0, length = data.fgroups.length; i < length; i++) {
					var fgroup = data.fgroups[i];
					if (fgroup.id == this.act_fgroup_uuid) {
						// now update the HTML for this particular field group
						var act_dom = document.getElementById(fgroup.id);
						act_dom.innerHTML = this.make_field_group_html(fgroup);
						done = true;
					}
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
		'<div class="col-xs-4">',
		'<button class="btn btn-default col-xs-7" onclick="' + this.name + '.addFieldGroup();">',
		'<span class="glyphicon glyphicon-plus-sign" aria-hidden="true"></span>',
		' Add Group of Fields',
		'</button>',
		'</div>',
		'<div class="col-xs-4">',
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
	this.cancelDelete = function(){
		$("#smallModal").modal('hide');
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
		for (var i = 0, length = this.data.fgroups.length; i < length; i++) {
			var fgroup = this.data.fgroups[i];
			if (fgroup.id == fgroup_uuid){
				this.act_fgroup_uuid = fgroup_uuid; 
				var body_html = this.make_field_group_edit_html(fgroup_uuid, fgroup.visibility, fgroup.label, fgroup.note);
				break;
			}
		}
		title_dom.innerHTML = 'Edit this Field Group: "' + fgroup.label + '"';
		body_dom.innerHTML = body_html;
		$("#myModal").modal('show');
	}
	this.deleteFieldGroup = function(fgroup_uuid){
		var main_modal_title_domID = "smallModalLabel";
		var main_modal_body_domID = "smallModalBody";
		var title_dom = document.getElementById(main_modal_title_domID);
		var body_dom = document.getElementById(main_modal_body_domID);
		var label = "";
		for (var i = 0, length = this.data.fgroups.length; i < length; i++) {
			var fgroup = this.data.fgroups[i];
			if (fgroup.id == fgroup_uuid){
				var label = fgroup.label;
				break;
			}
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
		for (var i = 0, length = this.data.fgroups.length; i < length; i++) {
			var fgroup = this.data.fgroups[i];
			if (fgroup.id == fgroup_uuid){
				var label = fgroup.label;
				break;
			}
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
				'onclick="' + this.name + '.rankField(\'' + field.id + '\', -1);" ',
				'title="Higher rank in sort order">',
				'<span class="glyphicon glyphicon-arrow-up"></span>',
				'</button>',
				'</div>',
				'<div style="margin-top: 2px;">',
				'<button class="btn btn btn-info btn-xs" ',
				'onclick="' + this.name + '.rankField(\'' + field.id + '\', 1);" ',
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
				'onclick="' + this.name + '.deleteField(\'' + field.id + '\');" title="Delete this field">',
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
			'<p><strong>Field Group Metadata</strong></p>',
			'<div class="row">',
			'<div class="col-xs-1">',
				'<div style="margin-top: 15px;">',
					'<button class="btn btn-default btn-xs" ',
					'onclick="' + this.name + '.editFieldGroup(\'' + fgroup.id + '\', -1);" ',
					'title="Edit this field group">',
					'<span class="glyphicon glyphicon-edit"></span>',
					'</button>',
				'</div>',
			'</div>',
			'<div class="col-xs-1">',
				'<div style="margin-top: 15px;">',
					'<button class="btn btn-danger btn-xs" ',
					'onclick="' + this.name + '.deleteFieldGroup(\'' + fgroup.id + '\', 1);" ',
					'title="Delete this field group">',
					'<span class="glyphicon glyphicon-remove-sign" aria-hidden="true"></span>',
					'</button>',
				'</div>',
			'</div>',
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
			'<div class="col-xs-9">',
				'<ul>',
				'<li>' + fgroup.visibility.toUpperCase() + ': ' + fgroup.vis_note + '</li>',
				'<li>' + note + '</li>',
				'</ul>',
			'</div>',
			'</div>',
			'</div>',
			'<div class="well well-sm">',
			'<p><strong>Fields (' + fgroup.fields.length + ')</strong></p>',
			table_html,
			'</div>'
		].join("\n");
		
		
		var panel_num = this.get_next_panel_num();
		var meta_panel = new panel(panel_num);
		meta_panel.title_html = fgroup.label;
		meta_panel.body_html = body_html;
		return meta_panel.make_html();
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