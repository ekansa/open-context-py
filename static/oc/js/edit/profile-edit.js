/*
 * Functions to edit a profile
 */

function profile(uuid){
	this.act_dom_id = "profile-data";
	this.name = "act_profile";
	this.uuid = uuid;
	this.data = false;
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
			html += this.make_profile_meta_html(data, 1);
			html += this.make_required_fields(data, 2);
			act_dom.innerHTML = html;
		}
	}
	this.make_profile_meta_html = function(data, panel_num){
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
		'<label>Actions</label><br/>',
		'<button class="btn btn-info col-xs-5" onclick="' + this.name + '.editProfile();">',
		'<span class="glyphicon glyphicon-edit" aria-hidden="true"></span>',
		' Update',
		'</button>',
		'</div>',
		'<div class="col-xs-8" id="edit-profile-exp-container">',
		'<p><small>A data entry profile defines a set of descriptive fields and data validation rules ',
		'for manually creating data. You should try to make simple clear labels to make data entry easier. ',
		'The <em>note</em> field should provide simple instructions to users who will do data entry tasks. ',
		'</small></p>',
		'</div>',
		'</div>',
		'<div class="row">',
		'<div class="col-xs-4">',
		'<button class="btn btn-danger col-xs-5" onclick="' + this.name + '.deleteProfile();">',
		'<span class="glyphicon glyphicon-remove-sign" aria-hidden="true"></span>',
		' Delete',
		'</button>',
		'</div>',
		'<div class="col-xs-8">',
		'</div>',
		'</div>',
		'</div>'
		].join('\n');
		var meta_panel = new panel(panel_num);
		meta_panel.title_html = title_html;
		meta_panel.body_html = body_html;
		return meta_panel.make_html();
	}
	this.editProfile = function(){
		// sends AJAX request to edit an item
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
	this.make_required_fields = function(data, panel_num){
		// makes HTML for profile metadata viewing and editing
		var class_html = "";
		var label_html = [
			'<div class="row">',
			'<div class="col-xs-4">',
			'<label>Item Label</label>',
			'<p><small>Every item is required to have an identifying label. A label is a more ',
			'"human-readable" identifier than a UUID that is automatically created for each record. ',
			'While UUIDs are used by the software, labels are meant for people. It is generally ',
			'best practice to make labels unique within your project.',
			'</small></p>',
			'</div>',
			'<div class="col-xs-8">',
			'<label>Options</label>',
			'<p>None selected</p>',
			'</div>',
			'</div>'
		].join("\n");
		if (data.item_type == 'subjects') {
			// subjects need to be contained in a parent
			// and have a class_uri (category)
			class_html = [
			'<div class="row">',
			'<div class="col-xs-4">',
			'<label>Basic Category</label>',
			'<p><small>Subjects of observation need to have a basic classification. This profile can ',
			'have a default classification value, or you can have different interface options for ',
			'users to classify a record created with this profile.</small></p>',
			'</div>',
			'<div class="col-xs-8">',
			'<label>Options</label>',
			'<p>None selected</p>',
			'</div>',
			'</div>'
			].join('\n');
		}
		var body_html = [
		'<div>',
		label_html,
		class_html,
		'</div>'
		].join('\n');
		var title_html = "Edit Required Fields Rules for: " + data.label;
		var meta_panel = new panel(panel_num);
		meta_panel.title_html = title_html;
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
			var src = this.make_url('/static/oc/images/ui/waiting.gif');
			var title_html = 'Loading Data Entry Profile "' + item_label + '"';
			var body_html = [
			'<div class="row">',
			'<div class="col-sm-1">',
			'<img alt="loading..." src="' + src + '" />',
			'</div>',
			'<div class="col-sm-11">',
			'Loading...',
			'</div>',
			'</div>'
			].join('\n');
			loading_panel = new panel(0);
			loading_panel.title_html = title_html;
			loading_panel.body_html = body_html;
			loading_panel.collapsing = false;
			var html = loading_panel.make_html();
			act_dom.innerHTML = html;
		}
	}
}