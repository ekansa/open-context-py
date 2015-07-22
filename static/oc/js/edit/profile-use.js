/*
 * Functions to edit a profile
 */

function useProfile(profile_uuid, edit_uuid, edit_new){
	this.act_dom_id = "profile-data";
	this.act_meta_dom_id = "profile-meta";
	this.name = "act_profile";
	this.project_uuid = project_uuid;
	this.profile_uuid = profile_uuid;
	this.edit_uuid = edit_uuid;
	this.edit_new = edit_new;
	this.label_prefix = '';
	this.label_id_len = false;
	this.item_type = false;
	this.context_uuid = false;
	this.data = false;
	this.act_fgroup_uuid = false;
	this.act_field_uuid = false;
	this.passed_value = false; // used to send data for AJAX requests when using the DOM is less reliable
	this.preset_label = false;
	this.label_pred_uuid = 'oc-gen:label';
	this.class_pred_uuid = 'oc-gen:class_uri';
	this.context_pred_uuid = 'oc-gen:contained-in';
	this.field_trees = []; // user interface trees to be populated for selecting items 
	this.entitySearchObj = false
	this.panel_nums = [0]; // id number for the input profile panel, used for making a panel dom ID
	this.search_nums = [0]; // id number for search entiity interface, used for making a dom ID
	this.sobjs = {}; // search objects
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
		this.field_trees = []; // reset all of the hiearchy trees
		this.data = data;
		this.item_type = data.item_type;
		if (document.getElementById(this.act_dom_id)) {
			// make metadata about the profile
			// and put into the right dom id
			var act_dom = document.getElementById(this.act_meta_dom_id);
			var meta_html = this.make_profile_meta_html(data);
			act_dom.innerHTML = meta_html;
		}
		if (document.getElementById(this.act_dom_id)) {
			//put the field groups into the right dom ID
			var act_dom = document.getElementById(this.act_dom_id);
			var html = "";
			html += '<div id="field-groups">';
			html += this.make_field_groups_html(data);
			html += '</div>';
			act_dom.innerHTML = html;
			this.make_trees();
		}
	}
	
	
	/* ---------------------------------------
	 * Profile HTML display
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
		var title_html = "About: " + data.label;
		var body_html = [
		'<div>',
		'<div class="row">',
		'<div class="col-xs-12">',
			'<dl>',
			'<dt>Item Type</dt>',
			'<dd>' + this.describe_item_type_html(data.item_type) + '</dd>',
			'<dt>Fields</dt>',
			'<dd>' + num_fields + ' fields in ' + data.fgroups.length + ' groups</dd>',
			'</dl>',
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
		'</div>',
		].join('\n');
		var panel_num = this.get_next_panel_num();
		var meta_panel = new panel(panel_num);
		meta_panel.title_html = title_html;
		meta_panel.body_html = body_html;
		return meta_panel.make_html();
	}
	
	
	
	
	/* ---------------------------------------
	 * Field Group and Field HTML 
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
			if (field.predicate_uuid == this.label_pred_uuid) {
				field_html += this.make_label_field_html(field);
			}
			else if (field.predicate_uuid == this.class_pred_uuid) {
				field_html += this.make_category_field_html(field);
			}
			else if (field.predicate_uuid == this.context_pred_uuid) {
				field_html += this.make_context_field_html(field);
			}
			else{
				if (field.data_type == 'id') {
					field_html += this.make_id_field_html(field);
				}
				else if (field.data_type == 'xsd:integer' || field.data_type == 'xsd:double') {
					field_html += this.make_num_field_html(field);
				}
				else if (field.data_type == 'xsd:string') {
					field_html += this.make_string_field_html(field);
				}
				else{
				   field_html += this.make_field_html(field);	
				}
			}
		}
		var body_html = [
			'<table class="table table-striped">',
			'<thead>',
			'<tr>',
			'<th class="col-xs-1">Update</th>',
			'<th class="col-xs-5">Field</th>',
			'<th class="col-xs-6">About</th>',
			'</th>',
			'</tr>',
			'</thead>',
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
		'<tr>',
		'<td>',
      this.make_field_update_buttom(field.id),
		'</td>',
		'<td>',
			'<div class="form-group">',
			'<label for="f-' + field.id + '">' + field.label + '</label>',
			'<input id="f-' + field.id + '" class="form-control input-sm" ',
			'type="text" value="" />',
			'</div>',
		'</td>',
		'<td>',
			'<div id="v-' + field.id + '">',
			'</div>',
			'<label>Explanatory Note</label><br/>',
			field.note,
		'</td>',
		'</tr>'
		].join("\n");
		return html;
	}
	this.make_num_field_html = function(field){
		var hr_data_type = this.get_human_readable_data_type(field.data_type);
		var placeholder = ' placeholder="' + hr_data_type + ' values" ';
		var html = [
		'<tr>',
		'<td>',
      this.make_field_update_buttom(field.id),
		'</td>',
		'<td>',
			'<div class="form-group">',
			'<label for="f-' + field.id + '">' + field.label + '</label>',
			'<input id="f-' + field.id + '" class="form-control input-sm" ',
			'type="text" value="" ' + placeholder,
			'onkeydown="' + this.name + '.validateNumber(\'' + field.id + '\', \'' + field.data_type + '\');" ',
			'onkeyup="' + this.name + '.validateNumber(\'' + field.id + '\', \'' + field.data_type + '\');" ',
			'/>',
			'</div>',
		'</td>',
		'<td>',
			'<div id="v-' + field.id + '">',
			'</div>',
			'<label>Explanatory Note</label><br/>',
			field.note,
		'</td>',
		'</tr>'
		].join("\n");
		return html;
	}
	this.make_string_field_html = function(field){
		var html = [
		'<tr>',
		'<td>',
      this.make_field_update_buttom(field.id),
		'</td>',
		'<td>',
			'<div class="form-group">',
			'<label for="f-' + field.id + '">' + field.label + '</label>',
			'<textarea id="f-' + field.id + '" class="form-control input-sm" rows="3">',
			'</textarea>',
			'</div>',
		'</td>',
		'<td>',
			'<div id="v-' + field.id + '">',
			'</div>',
			'<label>Explanatory Note</label><br/>',
			field.note,
		'</td>',
		'</tr>'
		].join("\n");
		return html;
	}
	this.make_id_field_html = function(field){
		this.prep_field_tree(field.predicate_uuid, field.id, 'description');
		
		// make an entity search for contexts
		var entityInterfaceHTML = "";
		/* changes global authorSearchObj from entities/entities.js */
		var ent_num = this.get_next_search_num();
		var entSearchObj = new searchEntityObj();
		var ent_name = 'sobjs[' + ent_num + ']';
		entSearchObj.name = ent_name;
		entSearchObj.parent_obj_name = this.name;
		entSearchObj.entities_panel_title = "Select a Category for " + field.label;
		entSearchObj.limit_item_type = "types";
		entSearchObj.limit_project_uuid = "0," + this.project_uuid;
		var entDomID = entSearchObj.make_dom_name_id();
		var afterSelectDone = {
			name: ent_name,
			field_uuid: field.id,
			exec: function(){
				var sel_id = document.getElementById(entDomID + "-sel-entity-id").value;
				var sel_label = document.getElementById(entDomID +  "-sel-entity-label").value;
				document.getElementById('f-l-' + this.field_uuid).value = sel_label;
				document.getElementById('f-id-' + this.field_uuid).value = sel_id;
			}
		};
		entSearchObj.afterSelectDone = afterSelectDone;
		this.sobjs[ent_num] = entSearchObj;
		var entityInterfaceHTML = entSearchObj.generateEntitiesInterface();
		
		var html = [
		'<tr>',
		'<td>',
      this.make_field_update_buttom(field.id),
		'</td>',
		'<td>',
			'<div class="form-group">',
			'<label for="f-l-' + field.id + '">' + field.label + ' (Label)</label>',
			'<input id="f-l-' + field.id + '" class="form-control input-sm" ',
			'type="text" value="" disabled="disabled"/>',
			'</div>',
			'<div class="form-group">',
			'<label for="f-id-' + field.id + '">' + field.label + ' (ID)</label>',
			'<input id="f-id-' + field.id + '" class="form-control input-sm" ',
			'type="text" value="" />',
			'</div>',
			'<div class="well well-sm small">',
			'<label>Select a Category or Type Below</label><br/>',
			'<div id="tr-' + field.id + '" class="container-fluid">', // where the tree will go
			'</div>',
			'</div>',
		'</td>',
		'<td>',
			'<div id="v-' + field.id + '">',
			'</div>',
			'<label>Explanatory Note</label><br/>',
			field.note,
			entityInterfaceHTML,
		'</td>',
		'</tr>'
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
		var id_part_placeholder = ' placeholder="ID number" ';
		
		var html = [
		'<tr>',
		'<td>',
      this.make_field_update_buttom(field.id),
		'</td>',
		'<td>',
			'<div class="form-group">',
			'<label for="f-' + field.id + '">' + field.label + '</label>',
			'<input id="f-' + field.id + '" class="form-control input-sm" ',
			'type="text" value="" ' + label_placeholder,
			'onkeydown="' + this.name + '.validateLabel(\'' + field.id + '\');" ',
			'onkeyup="' + this.name + '.validateLabel(\'' + field.id + '\');" ',
			'/>',
			'</div>',
			'<div class="well well-sm small">',
			'<form class="form-horizontal">',
			'<div class="form-group">',
				'<label for="label-prefix" class="col-sm-5 control-label">ID Part</label>',
				'<div class="col-sm-5">',
				'<input id="label-id-part" class="form-control input-sm" ',
				'type="text" value="" ' + id_part_placeholder,
				//'onkeydown="' + this.name + '.composeLabel(\'' + field.id + '\');" ',
				'onkeyup="' + this.name + '.composeLabel(\'' + field.id + '\');" ',
				'/>',
				'</div>',
			'</div>',
			'<div class="form-group">',
				'<label for="label-prefix" class="col-sm-5 control-label">Label Prefix</label>',
				'<div class="col-sm-5">',
				'<input id="label-prefix" class="form-control input-sm" ',
				'type="text" value="' + this.label_prefix + '" ' + prefix_placeholder,
				'onkeydown="' + this.name + '.composeLabel(\'' + field.id + '\');" ',
				'onkeyup="' + this.name + '.composeLabel(\'' + field.id + '\');" ',
				'/>',
				'</div>',
			'</div>',
			'<div class="form-group">',
				'<label for="label-id-len" class="col-sm-5 control-label">ID Digit Length</label>',
				'<div class="col-sm-3">',
				'<input id="label-id-len" class="form-control input-sm" ',
				'type="text" value="' + digit_len_val + '" ',
				'onkeydown="' + this.name + '.composeLabel(\'' + field.id + '\');" ',
				'onkeyup="' + this.name + '.composeLabel(\'' + field.id + '\');" ',
				'/>',
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
		'</td>',
		'<td>',
			'<div id="v-' + field.id + '">',
			'</div>',
			'<label>Explanatory Note</label><br/>',
			field.note,
		'</td>',
		'</tr>'
		].join("\n");
		return html;
	}
	this.make_category_field_html = function(field){
		// makes special HTML for the (class_uri) category field
		this.prep_field_tree(('oc-gen:' + this.item_type), field.id, 'entities');
		var html = [
		'<tr>',
		'<td>',
      this.make_field_update_buttom(field.id),
		'</td>',
		'<td>',
			'<div class="form-group">',
			'<label for="f-l-' + field.id + '">' + field.label + ' (Label)</label>',
			'<input id="f-l-' + field.id + '" class="form-control input-sm" ',
			'type="text" value="" disabled="disabled"/>',
			'</div>',
			'<div class="form-group">',
			'<label for="f-id-' + field.id + '">' + field.label + ' (ID)</label>',
			'<input id="f-id-' + field.id + '" class="form-control input-sm" ',
			'type="text" value="" />',
			'</div>',
			'<div class="well well-sm small">',
			'<label>Select a General Category Below</label><br/>',
			'<div id="tr-' + field.id + '" class="container-fluid">', // where the tree will go
			'</div>',
			'</div>',
		'</td>',
		'<td>',
			'<div id="v-' + field.id + '">',
			'</div>',
			'<label>Explanatory Note</label><br/>',
			field.note,
		'</td>',
		'</tr>'
		].join("\n");
		return html;
	}
	this.make_context_field_html = function(field){
		// make a tree list for searching for contexts
		this.prep_field_tree(this.project_uuid, field.id, 'context');
		
		// make an entity search for contexts
		var entityInterfaceHTML = "";
		/* changes global authorSearchObj from entities/entities.js */
		var ent_num = this.get_next_search_num();
		var entSearchObj = new searchEntityObj();
		var ent_name = 'sobjs[' + ent_num + ']';
		entSearchObj.name = ent_name;
		entSearchObj.parent_obj_name = this.name;
		entSearchObj.entities_panel_title = "Select a Context";
		entSearchObj.limit_item_type = "subjects";
		entSearchObj.limit_project_uuid = "0," + this.project_uuid;
		var entDomID = entSearchObj.make_dom_name_id();
		var afterSelectDone = {
			name: ent_name,
			field_uuid: field.id,
			exec: function(){
				var sel_id = document.getElementById(entDomID + "-sel-entity-id").value;
				var sel_label = document.getElementById(entDomID +  "-sel-entity-label").value;
				document.getElementById('f-l-' + this.field_uuid).value = sel_label;
				document.getElementById('f-id-' + this.field_uuid).value = sel_id;
			}
		};
		entSearchObj.afterSelectDone = afterSelectDone;
		this.sobjs[ent_num] = entSearchObj;
		var entityInterfaceHTML = entSearchObj.generateEntitiesInterface();
		
		var html = [
		'<tr>',
		'<td>',
      this.make_field_update_buttom(field.id),
		'</td>',
		'<td>',
			'<div class="form-group">',
			'<label for="f-l-' + field.id + '">' + field.label + ' (Label)</label>',
			'<input id="f-l-' + field.id + '" class="form-control input-sm" ',
			'type="text" value="" disabled="disabled"/>',
			'</div>',
			'<div class="form-group">',
			'<label for="f-id-' + field.id + '">' + field.label + ' (ID)</label>',
			'<input id="f-id-' + field.id + '" class="form-control input-sm" ',
			'type="text" value="" />',
			'</div>',
			'<div class="well well-sm small">',
			'<label>Select a Context Below</label><br/>',
			'<div id="tr-' + field.id + '" class="container-fluid">', // where the tree will go
			'</div>',
			'</div>',
		'</td>',
		'<td>',
			'<div id="v-' + field.id + '">',
			'</div>',
			'<label>Explanatory Note</label><br/>',
			field.note,
			entityInterfaceHTML,
		'</td>',
		'</tr>'
		].join("\n");
		return html;
	}
	this.make_field_update_buttom = function(field_uuid){
		// makes an update button for user to upload data when data entry is done
		var button_html = [
		'<div style="margin-top: 22px;">',
		'<button class="btn btn-default" onclick="' + this.name + '.updateField(\'' + field_uuid + '\');">',
		'<span class="glyphicon glyphicon-cloud-upload" aria-hidden="true"></span>',
		//' Delete',
		'</button>',
		'</div>'
		].join('\n');

		return button_html;
	}
	
	
	
	/* ---------------------------------------
	 * User interaction functions
	 *
	 * for item labels
	 * ---------------------------------------
	 */
	this.composeLabel = function(field_uuid){
		
		var id_part = document.getElementById('label-id-part').value.trim();
		var prefix = document.getElementById('label-prefix').value.trim();
		var id_len = parseInt(document.getElementById('label-id-len').value);
		if (!this.isInt(id_len)) {
			document.getElementById('label-id-len').value = '';
			id_len = '';
			var id_part = id_part.replace(prefix, '');
		}
		else{
			var id_part = id_part.replace(prefix, '');
			id_part =  this.prepend_zeros(id_part, id_len);
		}
		var label = prefix + id_part;
		document.getElementById('f-' + field_uuid).value = label.trim();
		if (id_part.length > 0) {
			if (id_part != ' ') {
				// the ID part has some values, so one can validate it
				// with an AJAX request
				this.passed_value = label;
				this.validateLabel(field_uuid);
			}
		}
		
	}
	this.validateLabel = function(field_uuid){
		
		this.act_field_uuid = field_uuid; // so as to remember what field we're validating
		var url = this.make_url('/edit/inputs/item-label-check/' + encodeURIComponent(this.project_uuid));
		var data = {item_type: this.item_type};
		
		var id_len = parseInt(document.getElementById('label-id-len').value);
		if (this.isInt(id_len)) {
			data.id_len = id_len;
		}
		if (this.passed_value == false) {
			var label = document.getElementById('f-' + field_uuid).value;
			if (label.length > 0) {
				data.label = label.trim();
			}
		}
		else{
			var label = this.passed_value;
			this.passed_value = false;
			if (label.length > 0) {
				data.label = label.trim();
			}
		}
		
		var prefix = document.getElementById('label-prefix').value;
		if (prefix.length > 0) {
			data.prefix = prefix;
		}
		if (this.context_uuid != false) {
			data.context_uuid = this.context_uuid;
		}
		var act_dom = document.getElementById('v-' + field_uuid);
		act_dom.innerHTML = this.make_loading_gif('Checking label...');
		return $.ajax({
			type: "GET",
			url: url,
			dataType: "json",
			context: this,
			data: data,
			async: false,
			success: this.validateLabelDone,
			error: function (request, status, error) {
				alert('Item Label validation failed, sadly. Status: ' + request.status);
			} 
		});
	}
   
	this.presetLabel = function(){
		var field = this.get_field_obj_by_predicate_uuid(this.label_pred_uuid);
		if (field != false) {
			this.act_field_uuid = field.id; // so as to remember what field we're validating
			var url = this.make_url('/edit/inputs/item-label-check/' + encodeURIComponent(this.project_uuid));
			var data = {
				item_type: this.item_type,
			   prefix: this.label_prefix,
				id_len: this.label_id_len
			};
			var act_dom = document.getElementById('v-' + field.id);
			act_dom.innerHTML = this.make_loading_gif('Suggesting label...');
			return $.ajax({
				type: "GET",
				url: url,
				dataType: "json",
				context: this,
				data: data,
				async: true,
				success: this.validateLabelDone,
				error: function (request, status, error) {
					alert('Item Label suggestion failed, sadly. Status: ' + request.status);
				} 
			});
		}
	}
	this.validateLabelDone = function(data){
		var field_uuid = this.act_field_uuid;
		this.act_field_uuid = false;
		
		if (this.preset_label) {
			//we wanted to use data.suggested to preset the label
			document.getElementById('f-' + field_uuid).value = data.suggested.trim();
			this.preset_label = false;
		}
		
		var act_dom = document.getElementById('v-' + field_uuid);
		if (data.exists == true) {
			var icon_html = '<span class="glyphicon glyphicon-warning-sign" aria-hidden="true"></span>';
			var message_html = [
				'The label "' + data.checked + '"',
				'<a href="' + this.make_url('/edit/items/' +  encodeURIComponent(data.exists_uuid)) + '" target="_blank">',
				'<span class="glyphicon glyphicon-edit" aria-hidden="true"></span>',
				'</a> ',
				'already exists.',
			].join('\n');
			var alert_class = "alert alert-danger";
			var alert_html = [
				'<div role="alert" class="' + alert_class + '">',
					icon_html,
					message_html,
				'</div>'
			].join('\n');
		}
		else if (data.exists == false){
			var icon_html = '<span class="glyphicon glyphicon-ok-circle" aria-hidden="true"></span>';
			var message_html = [
				'The label "' + data.checked + '" is not yet in use.',
			].join('\n');
			var alert_class = "alert alert-success";
			var alert_html = [
				'<div role="alert" class="' + alert_class + '">',
					icon_html,
					message_html,
				'</div>'
			].join('\n');
		}
		else{
			var alert_html = '';
		}
		if (data.suggested != data.checked) {
			var alert_class = "alert alert-info";
			if (alert_html.length > 5) {
				var div_start = ' style="margin-top:-25px;" ';
			}
			else{
				var div_start = '';
			}
			var suggested_link = [
				' role="button" onclick="' + this.name + '.useSuggestedLabel(\'' + field_uuid + '\');" '
			].join(' ');
			if (document.getElementById('f-' + field_uuid).value != data.suggested) {
				var suggest_hint = ' (Click to use)';
			}
			else{
				var suggest_hint = '';
			}
			
			var suggest_html = [
			'<div ' + div_start + '>',
			'<div role="alert" class="' + alert_class + '" id="suggested-alert">',
			'Suggested Label' + suggest_hint + ': ',
			'<a title="Use suggested link" ' + suggested_link + ' >',
			'<span class="glyphicon glyphicon-circle-arrow-left"></span>',
			'</a> ',
			'<a title="Use suggested link" ' + suggested_link + ' >',
			'<samp class="uri-id" id="suggested-label" style="font-weight:bold;">',
			data.suggested,
			'</samp>',
			'</a>',
			'</div>',
			'</div>'
			].join('\n');
		}
		else{
			var suggest_html = '';
		}
		
		var html = [
			'<div style="margin-top: 3px;">',
			alert_html,
			suggest_html,
			'</div>'
		].join("\n");
		act_dom.innerHTML = html;
	}
	this.useSuggestedLabel = function(field_uuid){
		// copies the suggested label into the label field
		var label = document.getElementById('suggested-label').innerHTML;
		document.getElementById('f-' + field_uuid).value = label.trim();
		document.getElementById('suggested-alert').innerHTML = "Using suggested label: " + label;
		this.passed_value = label.trim();
		this.validateLabel(field_uuid);
	}
	
	/* ---------------------------------------
	 * Functions
	 * related to tree interfaces for selecting values
	 * for nominal (id) fields, categories (class_uri),
	 * or spatial contexts (subjects)
	 * ---------------------------------------
	 */
	this.selectTreeItem = function(id, label, item_type, field_uuid){
		// this is the function called in onclick events when
		// a user has selected an item from a tree to be used
		// to populate a value for a field
		document.getElementById('f-l-' + field_uuid).value = label.trim();
		document.getElementById('f-id-' + field_uuid).value = id.trim();
	}
	this.prep_field_tree = function(root_node_id, field_uuid, tree_type){
		// adds an object to a list to prepare for creating trees
		// with values to be used to populate fields
		var tree_item = {
			root_node_id: root_node_id,
			field_uuid: field_uuid,
		   tree_type: tree_type
		};
		this.field_trees.push(tree_item);
	}
	this.make_trees = function(){
		// goes throough the list of preped tree items to actually
		// generate the tree HTML
		for (var i = 0, length = this.field_trees.length; i < length; i++) {
			var tree_item = this.field_trees[i];
			this.make_field_tree_html(tree_item.root_node_id, tree_item.field_uuid, tree_item.tree_type, i);
		}
	}
	this.make_field_tree_html = function(root_node_id, field_uuid, tree_type, tree_id){
		// makes the actual tree interface based on parameters passed
		// is useful for:
		// categories (class_uri),
		// descriptions (predicates + types),
		// and contexts (subjects / locations / objects)
		var parent_dom_id = 'tr-' + field_uuid;
		var tree = new hierarchy(root_node_id, parent_dom_id);
		tree.root_node = true;  //root node of this tree
		tree.object_prefix = 'tree-' + tree_id;
		tree.exec_primary_onclick = this.name + '.selectTreeItem'; // name of the function to use onclicking a tree item
		tree.exec_primary_passed_val = field_uuid; //value to pass in the onclick function.
		if (tree_type == 'description') {
			// useful for predicates and types
			tree.exec_primary_title = 'Click to select this description';
			tree.do_description_tree();
		}
		else if (tree_type == 'entities') {
			// useful for linked data, and also Open Context categories use in 'class_uri'
			tree.exec_primary_title = 'Click to select this category';
			tree.do_entity_hierarchy_tree();
		}
		else{
			// it's a spatial tree
			tree.exec_primary_title = 'Click to select this context';
		}
	
		tree.get_data();
		var tree_key = tree.object_prefix; 
		hierarchy_objs[tree_key] = tree;
	}
	
	
	/* ---------------------------------------
	 * Field Validation functions
	 * used throughout
	 * ---------------------------------------
	 */
	this.validateNumber = function(field_uuid, data_type){
		//validates numeric fields
		var is_valid = false;
		var check_val = document.getElementById('f-' + field_uuid).value;
		if (isNaN(check_val)){
			// not a number returned true
			var val_mes = 'Not a numeric ' + this.get_human_readable_data_type(data_type) + ' value.';
			this.make_validation_html(val_mes, false, field_uuid);
		}
		else{
			// numeric result detected, now make sure it fits the specific datatype
			if (data_type == 'xsd:double') {
				check_val = parseFloat(check_val);
				if (this.isFloat(check_val)) {
					var val_mes = 'Valid ' + this.get_human_readable_data_type(data_type) + ' value.';
					this.make_validation_html(val_mes, true, field_uuid);
				}
				else{
					var val_mes = 'Not a valid ' + this.get_human_readable_data_type(data_type) + ' value.';
					this.make_validation_html(val_mes, false, field_uuid);
				}
			}
			if (data_type == 'xsd:integer') {
				var check_val = parseFloat(check_val);
				if (this.isInt(check_val)) {
					var val_mes = 'Valid ' + this.get_human_readable_data_type(data_type) + ' value.';
					this.make_validation_html(val_mes, true, field_uuid);
				}
				else{
					var val_mes = 'Not a valid ' + this.get_human_readable_data_type(data_type) + ' value.';
					this.make_validation_html(val_mes, false, field_uuid);
				}
			}	
		}
		
	}
	this.validateDate = function(field_uuid){
		// validates date fields to a yyyy-mm-dd format
		var str = document.getElementById('f-' + field_uuid).value;
	   var valid_date = this.isValidDate(str);
		if (valid_date) {
			var val_mes = 'Valid calendar date value.';
			this.make_validation_html(val_mes, true, field_uuid);
		}
		else{
			var val_mes = 'Not a valid calendar date (yyyy-mm-dd) value.';
			this.make_validation_html(val_mes, false, field_uuid);
		}
	}
	
	
	/* ---------------------------------------
	 * Helper functions
	 * used throughout
	 * ---------------------------------------
	 */
	this.make_validation_html = function(message_html, is_valid, field_uuid){
		if (is_valid) {
			var icon_html = '<span class="glyphicon glyphicon-ok-circle" aria-hidden="true"></span>';
			var alert_class = "alert alert-success";
		}
		else{
			var icon_html = '<span class="glyphicon glyphicon-warning-sign" aria-hidden="true"></span>';
			var alert_class = "alert alert-danger";
		}
	
		var alert_html = [
				'<div role="alert" class="' + alert_class + '">',
					icon_html,
					message_html,
				'</div>'
			].join('\n');
		
		if (field_uuid != false) {
			//add this to the dom
			var act_dom = document.getElementById('v-' + field_uuid);
			act_dom.innerHTML = alert_html;
		}
		return alert_html;
	}
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
	this.get_field_obj_by_predicate_uuid = function(predicate_uuid){
		// gets the first field object with a given predicate_uuid
		var output = false;
		for (var i = 0, length = this.data.fgroups.length; i < length; i++) {
			var fgroup = this.data.fgroups[i];
			for (var f_i = 0, f_length = fgroup.fields.length; f_i < f_length; f_i++) {
				var field = fgroup.fields[f_i];
				if (field.predicate_uuid == predicate_uuid) {
					output = field;
					break;
				}
			}
		}
		return output;
	}
	this.cancelDelete = function(){
		$("#smallModal").modal('hide');
	}
	this.prepend_zeros = function(id_part, digit_length){
		// prepends zeros to an appropriate digit length
		if (this.isInt(digit_length)) {
			//yes the digit_length is an integer
			while (id_part.length < (digit_length)) {
				// prepend a zero
				id_part = '0' + id_part;
		   }
		}
		return id_part;
	}
	this.isInt = function(x){
        return (typeof x === 'number') && (x % 1 === 0);
   }
	this.isFloat = function(n){
		//checks if something is a float
		return (typeof n === 'number');
	}
	this.isValidDate = function(str){
		// checks to see if a string is a valid yyyy-mm-dd date
		if(str=="" || str==null){return false;}								
	
		// m[1] is year 'YYYY' * m[2] is month 'MM' * m[3] is day 'DD'					
		var m = str.match(/(\d{4})-(\d{2})-(\d{2})/);
		
		// STR IS NOT FIT m IS NOT OBJECT
		if( m === null || typeof m !== 'object'){return false;}				
		
		// CHECK m TYPE
		if (typeof m !== 'object' && m !== null && m.size!==3){return false;}
					
		var ret = true; //RETURN VALUE						
		var thisYear = new Date().getFullYear(); //YEAR NOW
		var minYear = 0; //MIN YEAR
		
		// YEAR CHECK
		if( (m[1].length < 4) || m[1] < minYear || m[1] > thisYear){ret = false;}
		// MONTH CHECK			
		if( (m[1].length < 2) || m[2] < 1 || m[2] > 12){ret = false;}
		// DAY CHECK
		if( (m[1].length < 2) || m[3] < 1 || m[3] > 31){ret = false;}
		
		return ret;	
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
	this.get_next_search_num = function(){
		var next_search_num = Math.max.apply(Math, this.search_nums) + 1;
		this.search_nums.push(next_search_num);
		return next_search_num;
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
