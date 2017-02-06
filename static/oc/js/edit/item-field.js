/*
 * This provides interfaces and validation checks on fields for data entry and date eding
 *
 */

function edit_field(){
	
	this.localize_dom_id = 'localize-modal';
	this.localize_title_dom_id = 'localize-title';
	this.localize_inter_dom_id = 'localize-interface';
	this.edit_uuid = false;  //uuid of the item being edited
	this.edit_new = false;  //is the item new (true, not created) or false (being edited)
	this.item_type = false;
	
	// used for required fields
	this.oc_required = false;
	this.item_label = false; // the current label value (for an edit_field for a label)
	this.item_altlabel = null; // SKOS alt-labels. if exists, is a dictionary object with language codes as keys
	this.label_prefix = ''; // for composing new labels
	this.label_id_len = false; //for composing new labels
	this.passed_value = false; // for label validation
	this.preset_label = false; // for presetting a label
	this.class_uri = false;
	this.class_label = false;
	this.context_uuid = false; // the parent context uuid
	this.context_label = false; // the parent context label
	
	this.id = 1;
	this.project_uuid = false;
	this.profile_uuid = false; //using an input profile if not false.
	this.field_uuid = false;
	this.label = false;
	this.pred_type = 'variable';
	this.data_type = false;
	this.predicate_uuid = false;
	this.sort = false;
	this.draft_sort = false;
	this.obs_num = false;
	this.obs_node = false;
	this.note = false;
	this.note_below_pred = false;
	this.validation = false;
	this.after_validation_done = false;
	this.value_num_validations = {};
	
	this.values_modified = false;
	this.values_obj = []; // list of values associated with an item
	this.multilingual = {}; // objects for creating, editing, validating multilingual texts.
	this.parent_obj_name = false;
	this.obj_name = false;
	this.name = false;
	this.show_predicate_link = true;
	this.invalid_alert_class = "alert alert-warning";
	this.value_del_col_class = 'col-xs-1';
	this.value_sort_col_class = 'col-xs-1';
	this.value_col_class = 'col-xs-6';
	this.valid_col_class = 'col-xs-4';
	this.simple_label_types = [
		'projects',
	    'persons',
		'tables'
	]; // item types that do NOT get elaborate label composition
	this.label_pred_uuid = 'oc-gen:label';
	this.class_pred_uuid = 'oc-gen:class_uri';
	this.context_pred_uuid = 'oc-gen:contained-in';
	this.note_pred_uuid = 'oc-gen:has-note';
	this.content_pred_uuid = 'oc-gen:content';  // for document contents, via profiles
	this.subs_link_pred_uuid = 'oc-gen:subjects-link';  // for linking to subjects, via profiles
	this.textarea_rows = 3;  // number of rows for a text area input
	this.textarea_rows_content = 20; // number of rows for text-area input of document content
	this.html_validation = false;
	this.values_dom_id = false;
	this.single_value_preds = [
		this.label_pred_uuid,
		this.class_pred_uuid,
		this.context_pred_uuid];
	this.class_vocab_uri = 'http://opencontext.org/vocabularies/oc-general/';
	this.add_new_data_row = true;
	this.add_field_sort_buttons = true;
	this.initialized = false;
	this.single_value_only = false;
	// for checking on IDs being valid
	this.value_nums_hash_ids = {}; //value_num is the key, hash_id is the value
	this.ids_validation = {};
	this.active_value_num = false; //used to handle results of AJAX validation requests
	// for panel ids
	this.panels = [];
	// entity search object
	this.sobjs = [];
	// tree specific attributes
	this.prepped_trees = false;
	this.prep_field_trees = []; // prepare field trees
	this.field_tree_collapsed = {}; // key is the field ID, boolean value for collapsed state
	
	this.make_field_html = function(){
		
		this.initialize();
		if (this.predicate_uuid == this.note_pred_uuid){
			// don't show a link to a standard link field
			this.show_predicate_link = false;
			this.data_type = 'xsd:string';
			this.class_uri = 'variable';
		}
		if (this.predicate_uuid == this.content_pred_uuid){
			// document text content, don't show a link to a standard link field
			// only used with creating documents via a profile
			this.single_value_only = true;
			this.show_predicate_link = false;
			this.data_type = 'xsd:string';
			this.class_uri = 'variable';
			this.textarea_rows = this.textarea_rows_content;
		}
		if (this.predicate_uuid == this.subs_link_pred_uuid){
			// for linking a media item or document to a subjects item
			// only used with creating documents via a profile
			this.show_predicate_link = false;
			this.data_type = 'id';
		}
		if (this.profile_uuid != false) {
			//we're using this field in an input profile
			var html = this.make_field_profile_html();
		}
		else{
			var html = this.make_field_edit_html();
		}
		return html;
	}
	this.make_basic_edit_field_html = function(){
		//special function to make html for an item label, in edit mode (not create)
		this.initialize();
		var dom_ids = this.make_field_val_domids(0);
		var val_html = '';
		if (this.predicate_uuid == this.label_pred_uuid) {
			var val_html = this.make_label_val_html(0, {});
		}
		else if (this.predicate_uuid == this.class_pred_uuid) {
			var val_html = this.make_category_val_html(0, {});
		}
		else if (this.predicate_uuid == this.context_pred_uuid) {
			var val_html = this.make_context_val_html(0, {});
		}
		var note_html = '';
		if (this.note != false) {
			if (this.note.length > 0) {
				var note_html = [
					'<label>Note</label>',
					'<p class="small">',
						this.note,
					'</p>'
				].join("\n");
			}
		}
		var html = [
			'<div class="row">',
				'<div class="col-sm-6">',
					val_html,
				'</div>',
				'<div class="col-sm-3">',
					'<div id="' + dom_ids.submitcon + '" style="padding-top: 12px;">',
					'</div>',
					'<div id="' + dom_ids.respncon + '">',
					'</div>',
					'<div id="' + dom_ids.valid + '">',
					'</div>',
				'</div>',
				'<div class="col-sm-3">',
					note_html,
				'</div>',
			'</div>'
		].join('\n');
		return html;
	}
	this.make_field_edit_html = function(){
		var vals_html = this.make_vals_html();
		var note_html = '';
		if (this.note != false) {
			if (this.note.length > 0) {
				var note_html = [
					'<div class="well well-sm">',
						'<label>Explanatory Note</label><br/>',
						this.note,
					'<div>'
				].join("\n");
			}
		}
		if (this.note_below_pred) {
			var after_pred_note = note_html;
			note_html = '';
		}
		else{
			var after_pred_note = '';
		}		
		var html = [
		'<td>',
			this.make_pred_label_html(),
			after_pred_note,
		'</td>',
		'<td>',
			'<div id="'+ this.values_dom_id + '">',
				vals_html,
			'</div>',
			note_html,
		'</td>',
		].join("\n");
		return html;
	}
	this.make_field_profile_html = function(){
		var vals_html = this.make_vals_html();
		var note_html = '';
		if (this.note != false) {
			if (this.note.length > 0) {
				var note_html = [
					'<p class="small">',
						this.note,
					'</p>'
				].join("\n");
			}
		}

		var html = [
		'<td>',
			this.label,
			note_html,
		'</td>',
		'<td>',
			'<div id="'+ this.values_dom_id + '">',
				vals_html,
			'</div>',
		'</td>',
		].join("\n");
		return html;
	}
	
	this.postprocess = function(){
		//do these functions after the html is added to the dom
		this.activate_calendars();
		this.activate_expand_collapse();
		this.make_trees();
		this.default_preset_label();
		return true;
	}
	this.default_preset_label = function(){
		// sets suggested default label for an item
		// based on passed arguments
		if (this.predicate_uuid == this.label_pred_uuid) {
			// this is a label predicate
			if (this.label_prefix.lenghth > 0 || this.label_id_len != false) {
				// compose a preset default label
				this.presetLabel(0);
			}
		}
	}
	this.make_vals_html = function(){
		this.initialize();
		var values_obj = this.values_obj;
		if (this.add_new_data_row) {
			// add a data entry row
			var new_value_obj = {'new': true};
			values_obj.push(new_value_obj);
			this.add_new_data_row = false;
		}
		var vals_html = [
			'<div class="container-fluid" id="' + this.values_dom_id + '">'
		];
		
		for (var i = 0, length = values_obj.length; i < length; i++) {
			var value_obj = values_obj[i];
			if (this.predicate_uuid == this.label_pred_uuid) {
				// makes edit interface for item labels
				var val_html = this.make_label_val_html(i, value_obj);
			}
			else if (this.predicate_uuid == this.class_pred_uuid) {
				// makes edit interface for item category / class
				var val_html = this.make_category_val_html(i, value_obj);
			}
			else if (this.predicate_uuid == this.context_pred_uuid) {
				// makes edit interface for item context
				var val_html = this.make_context_val_html(i, value_obj);
			}
			else if (this.predicate_uuid == this.subs_link_pred_uuid) {
				// makes edit interface for item subjects link
				var val_html = this.make_subjects_link_val_html(i, value_obj);
			}
			else if (this.predicate_uuid == this.note_pred_uuid) {
				// makes edit interfce for item note fields
				var val_html = this.make_string_val_html(i, value_obj);
			}
			else if (this.predicate_uuid == this.content_pred_uuid) {
				// makes edit interface for document item text content
				var val_html = this.make_string_val_html(i, value_obj);
			}
			else{
				if (this.data_type == 'id') {
					var val_html = this.make_id_val_html(i, value_obj);
				}
				else if (this.data_type == 'xsd:integer' || this.data_type == 'xsd:double') {
					var val_html = this.make_num_val_html(i, value_obj);
				}
				else if (this.data_type == 'xsd:date') {
					var val_html = this.make_date_val_html(i, value_obj);
				}
				else if (this.data_type == 'xsd:string') {
					var val_html = this.make_string_val_html(i, value_obj);
				}
				else if (this.data_type == 'xsd:boolean') {
					var val_html = this.make_boolean_val_html(i, value_obj);
				}
				else{
					var val_html = '';	
				}
			}
			var dom_ids = this.make_field_val_domids(i);
			
			if (value_obj.hasOwnProperty('new')) {
				var button_html = [
					'<button title="Click to expand" role="button" ',
					'class="btn btn-default btn-xs" ',
					'onclick="'+ this.name + '.expandNewRecord(\''+ dom_ids.newrec + '\');">',
					'<span class="glyphicon glyphicon-resize-vertical" aria-hidden="true">',
					'</span>',
					'</button>'].join("\n");
				
				if (this.single_value_only && i > 0) {
					var action = ' Change the <em>' + this.label + '</em> value';
				}
				else{
					if (this.single_value_preds.indexOf(this.predicate_uuid) >= 0) {
						var action = ' Edit <em>' + this.label + '</em>';
					}
					else{
						var action = ' Add a <em>' + this.label + '</em> value';
					}
				}
				
				var exp_html = [
					this.make_focal_html(i),
					'<div class="panel-group">',
						'<div class="panel panel-default" style="margin-top:4px;">',
							'<div class="panel-heading">',
								button_html,
								action,
							'</div>',
							'<div id="' +  dom_ids.newrec + '" class="collapse" >',
								'<div class="panel-body">',
									'<div class="row">',
										'<div class="col-xs-8">',
										val_html,
										'</div>',
										'<div class="col-xs-4">',
											'<div id="' + dom_ids.valid + '">',
											'</div>',
											'<div id="' + dom_ids.submitcon + '">',
											'</div>',
											'<div id="' + dom_ids.respncon + '">',
											'</div>',
										'</div>',
									'</div>',
								'</div>',
							'</div>',
						'</div>',
					'</div>',
				].join("\n");
				
				var row_html = [
					'<div class="row">',
						'<div class="col-xs-12">',
						exp_html,
						'</div>',
					'</div>',
				].join('\n');
			}
			else{
				// we're dealing with existing values, probably
				// already added to an item
				// default to believing them to be valid
				this.value_num_validations[i] = true;
				
				if (length > 2 ) {
					// add sort buttons for multi value fields
					var sort_buttons = this.make_val_sort_button_html(i, -1);
					sort_buttons += this.make_val_sort_button_html(i, 1);
				}
				else{
					var sort_buttons = '';
				}
				
				var row_html = [
					'<div class="panel panel-default">',
						'<div class="panel-body">',
							'<div class="row">',
								'<div class="' + this.value_del_col_class + '">',
								this.make_val_delete_button_html(i),
								this.make_val_translate_button_html(i),
								'</div>',
								'<div class="' + this.value_sort_col_class + '">',
								sort_buttons,
								'</div>',
								'<div class="' + this.value_col_class + '">',
								val_html,
								'</div>',
								'<div class="' + this.valid_col_class + '">',
									'<div id="' + dom_ids.valid + '">',
									'</div>',
									'<div id="' + dom_ids.submitcon + '">',
									'</div>',
									'<div id="' + dom_ids.respncon + '">',
									'</div>',
								'</div>',
							'</div>',
						'</div>',
					'</div>',
				].join('\n');
			}
			
			vals_html.push(row_html);
		}
		vals_html.push('</div>');
		return vals_html.join("\n");
	}
	this.initialize = function(){
		// makes the name of the object for called functions
		if (this.initialized == false) {
			// only do this if it hasn't been done yet
			this.values_dom_id = 'field-values-' + this.id;
			if (this.parent_obj_name != false) {
				this.name = this.parent_obj_name + '.' + this.obj_name;
			}
			else{
				this.name = this.obj_name;
			}
			if (this.single_value_preds.indexOf(this.predicate_uuid) >= 0) {
				//this predicate can only have single values
				this.single_value_only = true;
			}
			if (this.data_type == 'xsd:boolean') {
				//only allow a single value for boolean fields
				this.single_value_only = true;
			}
			if (this.project_uuid == false){
				this.project_uuid = '0'; // default project
			}
			this.initialized = true;
		}
	}
	
	this.make_boolean_val_html = function(value_num, value_obj){
		var dom_ids = this.make_field_val_domids(value_num);
		
		if (value_obj.hasOwnProperty('new')) {
			
			var hr_data_type = this.get_human_readable_data_type(this.data_type);
			var placeholder = ' placeholder="' + hr_data_type + ' values" ';
			
			var html = [
				'<div class="form-group">',
				'<input id="' + dom_ids.literal + '" class="form-control input-sm" ',
				'type="text" value="" ' + placeholder,
				'onkeydown="' + this.name + '.validateBoolean(\'' + value_num + '\');" ',
				'onkeyup="' + this.name + '.validateBoolean(\'' + value_num + '\');" ',
				'onchange="' + this.name + '.validateBoolean(\'' + value_num + '\');" ',
				'/>',
				'</div>',
				'<label class="radio-inline">',
				'<input type="radio" name="boolean-tf" id="f-tf-t-' + this.id + '" ',
				'value="true" onclick="' + this.name + '.booleanSelect(1, \'' + dom_ids.literal + '\');">',
				'True</label>',
				'<label class="radio-inline">',
				'<input type="radio" name="boolean-tf" id="f-tf-f-' + this.id + '" ',
				'value="false" onclick="' + this.name + '.booleanSelect(0, \'' + dom_ids.literal + '\');">',
				'False</label>',
			].join("\n");
		}
		else{
			var true_checked = '';
			var false_checked = '';
			var bool_value = this.parseStrBoolean(value_obj.literal);
			if (bool_value != null) {
				if (bool_value) {
					var true_checked = ' checked="checked" ';
				}
				else{
					var false_checked = ' checked="checked" ';
				}
			}
			else{
				this.make_validation_html('Cannot interpret "' + value_obj.literal + '" as a boolean (true/false) value.', false, value_num);
			}
			var html = [
				this.make_hash_id_hidden_html(value_num, value_obj),
				'<input id="' + value_obj.literal + '" class="form-control input-sm" ',
				'type="text" value="' + bool_value + '" ',
				'/>',
				'</div>',
				'<label class="radio-inline">',
				'<input type="radio" name="boolean-tf" id="f-tf-t-' + this.id + '" ',
				'value="true" onclick="' + this.name + '.booleanSelect(1, \'' + dom_ids.literal + '\');" ' + true_checked + ' />',
				'True</label>',
				'<label class="radio-inline">',
				'<input type="radio" name="boolean-tf" id="f-tf-f-' + this.id + '" ',
				'value="false" onclick="' + this.name + '.booleanSelect(0, \'' + dom_ids.literal + '\');" ' + false_checked + ' />',
				'False</label>',
			].join("\n");
		}
		return html;
	}
	this.make_date_val_html = function(value_num, value_obj){
		var dom_ids = this.make_field_val_domids(value_num);
		var hr_data_type = this.get_human_readable_data_type(this.data_type);
		var placeholder = ' placeholder="' + hr_data_type + ' values" ';
		var display_value = '';
		if (value_obj.hasOwnProperty('literal')) {
			display_value = value_obj.literal;
		}
		var html = [
			'<div class="form-group">',
				'<div class="input-group date" id="' + dom_ids.datecon + '">',
					this.make_hash_id_hidden_html(value_num, value_obj),
					'<input id="' + dom_ids.literal + '" class="form-control input-sm" ',
					'type="text" value="' + display_value + '" ' + placeholder,
					'onkeydown="' + this.name + '.validateDate(\'' + value_num + '\');" ',
					'onkeyup="' + this.name + '.validateDate(\'' + value_num + '\');" ',
					'onchange="' + this.name + '.validateDate(\'' + value_num + '\');" ',
					'aria-describedby="' + dom_ids.icon + '" />',
					'<span class="input-group-addon" id="' + dom_ids.icon + '">',
						'<span class="glyphicon glyphicon-calendar" aria-hidden="true"></span>',
					'</span>',
				'</div>',
			'</div>',
		].join("\n");
		return html;
	}
	this.make_num_val_html = function(value_num, value_obj){
		var dom_ids = this.make_field_val_domids(value_num);
		var hr_data_type = this.get_human_readable_data_type(this.data_type);
		var placeholder = ' placeholder="' + hr_data_type + ' values" ';
		var display_value = '';
		if (value_obj.hasOwnProperty('literal')) {
			display_value = value_obj.literal;
		}
		var html = [
			'<div class="form-group">',
			this.make_hash_id_hidden_html(value_num, value_obj),
			'<input id="' + dom_ids.literal + '" class="form-control input-sm" ',
			'type="text" value="' + display_value +  '" ' + placeholder,
			'onkeydown="' + this.name + '.validateNumber(\'' + value_num + '\');" ',
			'onkeyup="' + this.name + '.validateNumber(\'' + value_num + '\');" ',
			'/>',
			'</div>',
		].join("\n");
		return html;
	}
	this.make_string_val_html = function(value_num, value_obj){
		var display_value = '';
		var display_id = '';
		var dom_ids = this.make_field_val_domids(value_num);
		var hr_data_type = this.get_human_readable_data_type(this.data_type);
		var placeholder = ' placeholder="Free-form alphanumeric text (including HTML)" ';
		if (value_obj.hasOwnProperty('literal')) {
			display_value = value_obj.literal;
		}
		if (value_obj.hasOwnProperty('uuid')) {
			display_id = value_obj.uuid;
		}
		var html = [
			this.make_hash_id_hidden_html(value_num, value_obj),
			'<input id="' + dom_ids.id + '" ',
			'type="hidden" value="' + display_id + '" />',
			'<textarea id="' + dom_ids.literal + '" ',
			'onchange="' + this.name + '.validateHTML(\'' + value_num + '\');" ',
			'class="form-control input-sm" rows="' + this.textarea_rows,
			'" ' + placeholder + ' >',
			display_value,
			'</textarea>'
		].join("\n");
		return html;
	}
	this.make_id_val_html = function(value_num, value_obj){

		var dom_ids = this.make_field_val_domids(value_num);
		var display_label = '';
		var display_id = '';
		if (value_obj.hasOwnProperty('new')) {
			var sobj_id = this.sobjs.length;
			if (this.pred_type == 'variable') {
				// only prepare a search tree if this is a variable
				this.prep_field_tree(value_num, this.predicate_uuid, 'description');
				var limit_item_type = "types";
				var entities_panel_title = "Select a Category for " + this.label;
				var search_sup_html = [
					'<br/>',
					'<label>',
					'<u>Option B</u>: Select a Category Below ',
					'(<a title="Click to expand" role="button" ',
					'id="' + dom_ids.treebut + '" ',
					'onclick="'+ this.name + '.toggleCollapseTree(\''+ value_num + '\');">',
					'<span class="glyphicon glyphicon-cloud-download" aria-hidden="true">',
					'</span></a>)',
					'</label><br/>',
					'<div id="' + dom_ids.tree + '" class="container-fluid collapse in" aria-expanded="true" >', // where the tree will go
					'</div>',
					'<p><small>',
					'<a title="Add a new category" role="button" ',
					'onclick="createTypeForPredicate(\''+ this.label + '\', \''+ this.predicate_uuid + '\');">',
					'<span class="glyphicon glyphicon-plus-sign" aria-hidden="true">',
					'</span>',
					' Add another category for ' + this.label,
					'</a>',
					'</small></p>',
				].join("\n");
			}
			else{
				var limit_item_type = "*";
				var entities_panel_title = "Select a <em>" + this.label + "</em> linked item";
				var search_sup_html = [
					'<div class="radio">',
						'<label>',
							'<input type="radio" ',
							'value="*" ',
							'checked>',
							'All item types',
						'</label>',
					'</div>'
				].join("\n");
				search_sup_html = '';
			}
		
			// make an entity search for items in the id field
			var entityInterfaceHTML = "";
			/* changes global authorSearchObj from entities/entities.js */
			
			var entSearchObj = new searchEntityObj();
			var ent_name = 'sobjs[' + sobj_id + ']';
			entSearchObj.name = ent_name;
			entSearchObj.ultra_compact_display = true;
			entSearchObj.parent_obj_name = this.name;
			entSearchObj.entities_panel_title = entities_panel_title;
			entSearchObj.limit_item_type = limit_item_type;
			entSearchObj.limit_context_uuid = this.predicate_uuid;
			entSearchObj.limit_project_uuid = "0," + this.project_uuid;
			var entDomID = entSearchObj.make_dom_name_id();
			var afterSelectDone = this.make_afterSelectDone_obj(value_num, entDomID);
			afterSelectDone.exec = function(){
				var sel_id = document.getElementById(this.entDomID + "-sel-entity-id").value;
				var sel_label = document.getElementById(this.entDomID +  "-sel-entity-label").value;
				document.getElementById(this.dom_ids.label).value = sel_label;
				document.getElementById(this.dom_ids.id).value = sel_id;
				this.ids_validation[sel_id] = {label: sel_label,
														 item_type: 'types',
														 vocab_uri: false};
				var val_mes = 'Valid category selected.';
				this.validation_id_response(true, this.value_num);
				// this.make_submit_button(true, this.value_num);
			};
			entSearchObj.afterSelectDone = afterSelectDone;
			this.sobjs.push(entSearchObj);
			var entityInterfaceHTML = entSearchObj.generateEntitiesInterface();
			
			var html = [
				'<div class="form-group">',
				'<label for="' + dom_ids.label + '">' + this.label + ' (Label)</label>',
				'<input id="' + dom_ids.label + '" class="form-control input-sm" ',
				'type="text" value="' + display_label + '" disabled="disabled"/>',
				'</div>',
				'<div class="form-group">',
				'<label for="' + dom_ids.id + '">' + this.label + ' (ID)</label>',
				'<input id="' + dom_ids.id + '" class="form-control input-sm" ',
				//'onkeydown="' + this.name + '.validateID(\'' + value_num + '\');" ',
				//'onkeyup="' + this.name + '.validateID(\'' + value_num + '\');" ',
				'onchange="' + this.name + '.validateID(\'' + value_num + '\');" ',
				'type="text" value="' + display_id + '" />',
				'</div>',
				'<div class="well well-sm small">',
					'<label><u>Option A</u>: Search <em>' + this.label + '</em></label>',
					entityInterfaceHTML,
					search_sup_html,
				'</div>',
			].join("\n");
		}
		else{
			var html = [
				this.make_hash_id_hidden_html(value_num, value_obj),
				'<input id="' + dom_ids.label + '" ',
				'type="hidden" value="' + value_obj.label + '" />',
				'<input id="' + dom_ids.id + '" ',
				'type="hidden" value="' + value_obj.uuid + '" />',
				this.make_labeled_id_link_html(value_obj.label, value_obj.uuid, dom_ids)
			].join("\n");
		}
		return html;
	}
	
	this.make_hash_id_hidden_html = function(value_num, value_obj){
		var html = '';
		if (value_obj.hasOwnProperty('hash_id')) {
			if (value_obj.hash_id != null) {
				if (value_obj.hash_id.length > 0) {
					var dom_ids = this.make_field_val_domids(value_num);
					html = '<input id="' + dom_ids.hash_id + '" type="hidden" value="' + value_obj.hash_id + '" />';
					this.value_nums_hash_ids[value_num] = value_obj.hash_id;
				}
			}
		}
		return html;
	}
	this.make_label_val_html = function(value_num, value_obj){
		// makes special HTML for the label field
		var dom_ids = this.make_field_val_domids(value_num);
		var display_label = '';
		if (this.item_label != false) {
			display_label = this.item_label;
			//default to accepting a current value as valid
			this.value_num_validations[0] = true;
		}
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
		
		if (this.simple_label_types.indexOf(this.item_type) >= 0) {
			var display_label_compose_outer = ''
			var display_label_compose = 'display:none;';
		}
		else{
			var display_label_compose = '';
			var display_label_compose_outer = '';
		}
		
		var html = [
			'<div class="form-group">',
				'<label for="' + dom_ids.literal + '">' + this.label + '</label>',
				'<input id="' + dom_ids.literal + '" class="form-control input-sm" ',
				'type="text" value="' + display_label + '" ' + label_placeholder,
				'onkeydown="' + this.name + '.validateLabel(' + value_num + ');" ',
				'onkeyup="' + this.name + '.validateLabel(' + value_num + ');" ',
				'/>',
			'</div>',
			'<div style="' + display_label_compose_outer +'">',
				'<div class="well well-sm small" style="' + display_label_compose + '">',
					'<form class="form-horizontal">',
					'<div class="form-group">',
						'<label for="' + dom_ids.id_part + '" class="col-sm-5 control-label">ID Part</label>',
						'<div class="col-sm-5">',
							'<input id="' + dom_ids.id_part + '" class="form-control input-sm" ',
							'type="text" value="" ' + id_part_placeholder,
							//'onkeydown="' + this.name + '.composeLabel(\'' + this.id + '\');" ',
							'onkeyup="' + this.name + '.composeLabel(' + value_num + ');" ',
							'/>',
						'</div>',
					'</div>',
					'<div class="form-group">',
						'<label for="' + dom_ids.label_prefix + '" class="col-sm-5 control-label">Label Prefix</label>',
						'<div class="col-sm-5">',
							'<input id="' + dom_ids.label_prefix + '" class="form-control input-sm" ',
							'type="text" value="' + this.label_prefix + '" ' + prefix_placeholder,
							'onkeydown="' + this.name + '.composeLabel(' + value_num + ');" ',
							'onkeyup="' + this.name + '.composeLabel(' + value_num + ');" ',
							'/>',
						'</div>',
					'</div>',
					'<div class="form-group">',
						'<label for="' + dom_ids.id_len + '" class="col-sm-5 control-label">ID Digit Length</label>',
						'<div class="col-sm-3">',
							'<input id="' + dom_ids.id_len + '" class="form-control input-sm" ',
							'type="text" value="' + digit_len_val + '" ',
							'onkeydown="' + this.name + '.composeLabel(' + value_num + ');" ',
							'onkeyup="' + this.name + '.composeLabel(' + value_num + ');" ',
							'/>',
						'</div>',
					'</div>',
					'<div class="row">',
						'<div class="col-sm-5 text-right">',
							'<label>Translate</label>',
						'</div>',
						'<div class="col-sm-3">',
							this.make_val_translate_button_html(value_num, null),
						'</div>',
					'</div>',
					'</form>',
					/*  Hidden, since we're not using this yet */
					'<div class="form-group" style="display:none;">',
						'<label>Label Unique within:</label><br/>',
						'<label class="radio-inline">',
						'<input type="radio" name="label-unique" ',
						'class="label-unique" value="project" checked="checked" >',
						'Entire project</label>',
						'<label class="radio-inline">',
						'<input type="radio" name="label-unique" ',
						'class="label-unique" value="context" >',
						'Immediate Context</label>',
					'</div>',
				'</div>',
			'</div>'
		].join("\n");
		return html;
	}
	this.make_category_val_html = function(value_num, value_obj){
		// makes special HTML for the (class_uri) category field
		var dom_ids = this.make_field_val_domids(value_num);
		var display_label = '';
		var display_id = '';
		if (this.class_label != false) {
			display_label = this.class_label;
		}
		if (this.class_uri != false) {
			display_id = this.class_uri;
			//default to accepting a current value as valid
			this.value_num_validations[0] = true;
		}
		
		var tree_root_node_id = 'oc-gen:' + this.item_type;
		this.prep_field_tree(value_num, tree_root_node_id, 'entities');
		var limit_item_type = "types";
		var entities_panel_title = "Select a Category for " + this.label;
		var search_sup_html = [
			'<label>',
			'Select a Category Below ',
			'(<a title="Click to expand" role="button" ',
			'id="' + dom_ids.treebut + '" ',
			'onclick="'+ this.name + '.toggleCollapseTree(\''+ value_num + '\');">',
			'<span class="glyphicon glyphicon-cloud-download" aria-hidden="true">',
			'</span></a>)',
			'</label><br/>',
			'<div id="' + dom_ids.tree + '" class="container-fluid collapse in" aria-expanded="true" >', // where the tree will go
			'</div>',
		].join("\n");
		
		var html = [
			'<div class="form-group">',
			'<label for="' + dom_ids.label + '">' + this.label + ' (Label)</label>',
			'<input id="' + dom_ids.label + '" class="form-control input-sm" ',
			'type="text" value="' + display_label + '" disabled="disabled"/>',
			'</div>',
			'<div class="form-group">',
			'<label for="' + dom_ids.id + '">' + this.label + ' (ID)</label>',
			'<input id="' + dom_ids.id + '" class="form-control input-sm" ',
			//'onkeydown="' + this.name + '.validateID(\'' + value_num + '\');" ',
			//'onkeyup="' + this.name + '.validateID(\'' + value_num + '\');" ',
			'onchange="' + this.name + '.validateID(\'' + value_num + '\');" ',
			'type="text" value="' + display_id + '" />',
			'</div>',
			'<div class="well well-sm small">',
				search_sup_html,
			'</div>',
		].join("\n");
		
		return html;
	}
	this.make_context_val_html = function(value_num, value_obj){
		// make a tree list for searching for contexts
		var html = this.make_subs_links_or_contexts_html(
			value_num,
			value_obj,
			'Context',
			'Select a Context Below'
		);
		return html;
	}
	this.make_subjects_link_val_html = function(value_num, value_obj){
		var html = this.make_subs_links_or_contexts_html(
			value_num,
			value_obj,
			'Linked Subjects (Locations or Objects)',
			'Select a Location or Object ("subjects")'
		);
		return html;
	}
	this.make_subs_links_or_contexts_html = function(
		value_num,
		value_obj,
		entities_panel_title,
		option_b_title){
		
		// make a tree list for searching for contexts
		var dom_ids = this.make_field_val_domids(value_num);
		var display_label = '';
		var display_id = '';
		if (this.context_label != false) {
			display_label = this.context_label;
		}
		if (this.context_uuid != false) {
			display_id = this.context_uuid;
			//default to accepting a current value as valid
			this.value_num_validations[0] = true;
		}
		
		this.prep_field_tree(value_num, this.project_uuid, 'context');

		var search_sup_html = [
			'<br/>',
			'<label>',
			'<u>Option B</u>: ' + option_b_title,
			'(<a title="Click to expand" role="button" ',
			'id="' + dom_ids.treebut + '" ',
			'onclick="'+ this.name + '.toggleCollapseTree(\''+ value_num + '\');">',
			'<span class="glyphicon glyphicon-cloud-download" aria-hidden="true">',
			'</span></a>)',
			'</label><br/>',
			'<div id="' + dom_ids.tree + '" class="container-fluid collapse in" ',
			'aria-expanded="true" >', // where the tree will go
			'</div>',
		].join("\n");
		
		
		// make an entity search for items in the id field
		var entityInterfaceHTML = "";
		/* changes global authorSearchObj from entities/entities.js */
		var sobj_id = this.sobjs.length;
		var entSearchObj = new searchEntityObj();
		var ent_name = 'sobjs[' + sobj_id + ']';
		entSearchObj.name = ent_name;
		entSearchObj.ultra_compact_display = true;
		entSearchObj.parent_obj_name = this.name;
		entSearchObj.entities_panel_title = entities_panel_title;
		entSearchObj.limit_item_type = 'subjects';
		entSearchObj.limit_project_uuid = "0," + this.project_uuid;
		var entDomID = entSearchObj.make_dom_name_id();
		var afterSelectDone = this.make_afterSelectDone_obj(value_num, entDomID);
		afterSelectDone.exec = function(){
			var sel_id = document.getElementById(this.entDomID + "-sel-entity-id").value;
			var sel_label = document.getElementById(this.entDomID +  "-sel-entity-label").value;
			document.getElementById(this.dom_ids.label).value = sel_label;
			document.getElementById(this.dom_ids.id).value = sel_id;
			this.ids_validation[sel_id] = {
				label: sel_label,
				item_type: 'subjects',
			vocab_uri: false};
			var val_mes = 'Valid location or object ("subjects" item) selected.';
			this.validation_id_response(true, this.value_num);
			// console.log(this);
		};
		entSearchObj.afterSelectDone = afterSelectDone;
		this.sobjs.push(entSearchObj);
		var entityInterfaceHTML = entSearchObj.generateEntitiesInterface();
		
		var html = [
			'<div class="form-group">',
			'<label for="' + dom_ids.label + '">' + this.label + ' (Label)</label>',
			'<input id="' + dom_ids.label + '" class="form-control input-sm" ',
			'type="text" value="' + display_label + '" disabled="disabled"/>',
			'</div>',
			'<div class="form-group">',
			'<label for="' + dom_ids.id + '">' + this.label + ' (ID)</label>',
			'<input id="' + dom_ids.id + '" class="form-control input-sm" ',
			//'onkeydown="' + this.name + '.validateID(\'' + value_num + '\');" ',
			//'onkeyup="' + this.name + '.validateID(\'' + value_num + '\');" ',
			'onchange="' + this.name + '.validateID(\'' + value_num + '\');" ',
			'type="text" value="' + display_id + '" />',
			'</div>',
			'<div class="well well-sm small">',
				'<label><u>Option A</u>: Search <em>' + this.label + '</em></label>',
				entityInterfaceHTML,
				search_sup_html,
			'</div>',
		].join("\n");
		
		return html;
	}
	this.make_note_val_html = function(){
		var html = '';
		return html;
	}
	this.make_field_update_buttom_html = function(field_id){
		// makes an update button for user to upload data when data entry is done
		if (this.edit_new) {
			// disabled button because it's a new item that is not yet saved
			var button_html = [
			
			].join('\n');
		}
		else{
			// active button because each individual field can now be updated independently
			var button_html = [
			'<div style="margin-top: 22px;">',
			'<button class="btn btn-default" onclick="' + this.name + '.updateField(\'' + field_id + '\');">',
			'<span class="glyphicon glyphicon-cloud-upload" aria-hidden="true"></span>',
			//' Delete',
			'</button>',
			'</div>'
			].join('\n');
		}
		return button_html;
	}
	this.make_val_translate_button_html = function(value_num){
		// makes button HTML in appropriate cases
		var button_html = ''; // default to no button
		if (this.predicate_uuid == this.label_pred_uuid) {
			var make_translate_button = true;
			var style = ' style="margin-top: -2px;" ';
		}
		else if (this.data_type == 'xsd:string') {
			var make_translate_button = true;
			var style = ' style="margin-top: 5px;" ';
		}
		else{
			var make_translate_button = false;
		}
		if (make_translate_button) {
			// we need a translation button
			var title = 'Translate / localize this text';
			var button_html = [
				'<div ' + style + ' >',
				'<button title="' + title + '" ',
				'class="btn btn-info btn-xs" ',
				// below, the "return false;" part stops the page from reloading after onlick is done
				'onclick="' + this.name + '.localizeInterface(\'' + value_num + '\'); return false;">',
				'<span class="glyphicon glyphicon-flag"></span>',
				'</button>',
				'</div>',
				].join('\n');
		}
		return button_html;
	}
	this.localizeInterface = function(value_num){
		// creates a localization object if not already present for this value_num
		// then opens its interface
		if (value_num in this.multilingual) {
			// we already have a multilingual object for this field and this value
			var act_ml = this.multilingual[value_num];
		}
		else{
			var dom_ids = this.make_field_val_domids(value_num);
			var act_ml = new multilingual();
			act_ml.value_num = value_num;
		    act_ml.parent_obj_name = this.name;
			act_ml.obj_name = 'multilingual[' + value_num + ']';
			act_ml.dom_ids = dom_ids;
			if (this.predicate_uuid == this.label_pred_uuid) {
				// editing translations for label field
				act_ml.label = this.item_label;
				act_ml.localization = this.item_altlabel;
				act_ml.edit_type = 'label';
				act_ml.edit_uuid = this.edit_uuid;
			}
			else if (this.data_type == 'xsd:string') {
				// eding translattions for string field value
				act_ml.label = this.label;
				act_ml.edit_type = 'xsd:string';
				if (document.getElementById(dom_ids.id)) {
					act_ml.edit_uuid = document.getElementById(dom_ids.id).value;	
				}
				if (value_num < this.values_obj.length) {
					var value_obj = this.values_obj[value_num];
					if ('localization' in value_obj) {
						act_ml.localization = value_obj.localization;
					}
				}
			}
			else{
				alert('Something went wrong, you should not see this');
			}
			act_ml.initialize();
			this.multilingual[value_num] = act_ml;
		}
		act_ml.localizeInterface();
		return false;
	}
	
	this.make_val_delete_button_html = function(value_num){
		if (this.single_value_preds.indexOf(this.predicate_uuid) >= 0) {
			// no delete button for single value predicates
			var button_html = '';
		}
		else{
			var style = ' style="margin-top: 5px;" ';
			var title = 'Delete this value';
			var button_html = [
				'<div ' + style + ' >',
				'<button title="' + title + '" ',
				'class="btn btn btn-danger btn-xs" ',
				'onclick="' + this.name + '.deleteFieldValue(\'' + value_num + '\');">',
				'<span class="glyphicon glyphicon-remove-sign"></span>',
				'</button>',
				'</div>',
				].join('\n');
		}
		return button_html;
	}
	this.make_val_sort_button_html = function(value_num, sort_change){
		if (sort_change < 0) {
			var icon = '<span class="glyphicon glyphicon-arrow-up"></span>';
			var title = 'Higher rank in sort order';
			var style = 'style="margin-top:5px;"';
		}
		else{
			var icon = '<span class="glyphicon glyphicon-arrow-down"></span>';
			var title = 'Lower rank in sort order';
			var style = 'style="margin-top:2px;"';
		}
		var button_html = [
			'<div ' + style + ' >',
			'<button title="' + title + '" ',
			'class="btn btn btn-info btn-xs" ',
			'onclick="' + this.name + '.rankFieldValue(\'' + value_num + '\', ' + sort_change + ');">',
			icon,
			'</button>',
			'</div>',
			].join('\n');
		return button_html;
	}
	this.make_pred_label_html = function(){
		// makes a label and a link to the ID for the predicate
		if (this.show_predicate_link) {
			var html = this.make_labeled_id_link_html(this.label, this.predicate_uuid, false);
		}
		else{
			var html = [
				'<label>',
				this.label,
				'</label>',
			].join("\n");
		}
		return html;
	}
	this.make_labeled_id_link_html = function(label, uuid, dom_ids){
		if (dom_ids != false) {
			var label_id = ' id="' + dom_ids.label_dis + '" ';
			var id_id = ' id="' + dom_ids.id_dis + '" ';
		}
		else{
			var label_id = '';
			var id_id = '';
		}
		var html = [
			'<span ' + label_id + '>',
			label,
			'</span>',
			'<br/>',
			'<samp class="uri-id small">',
			'<a href="' + this.make_url('/edit/items/' + uuid) + '" target="_blank">',
			'<span ' + id_id + '>' + uuid + '</span>',
			'<span class="glyphicon glyphicon-new-window"></span>',
			'</a>',
			'</samp>'
		].join("\n");
		return html;
	}
	this.make_field_val_domids = function(value_num){
		// makes dom ids for values
		var dom_ids = {
			hash_id: (value_num + '-field-hash-' + this.id), //id for hash-id for an individual assertion
			literal: (value_num + '-field-' + this.id), //id for input element of literals
			label: (value_num + '-field-l-' + this.id), //label for ID value fields
			id: (value_num + '-field-id-' + this.id), //id value field
			label_dis: (value_num + '-field-l-dis-' + this.id), //label for ID value fields, for display only
			id_dis: (value_num + '-field-id-dis-' + this.id), //id value field, for display only
			valid: (value_num + '-field-valid-' + this.id), //container ID for validation feedback
			valid_val: (value_num + '-field-valid-val-' + this.id), //hidden input field for value validation results
			submitcon: (value_num + '-field-sbcon-' + this.id), //container ID for submitt button
			respncon: (value_num + '-field-respcon-' + this.id), //container ID for submission response
			icon: (value_num + '-field-icon-' + this.id), //for calendar icon, used with date picker
			datecon: (value_num + '-field-datecon-' + this.id), //containers for dates, needed to activate calender date picker
			treebut: (value_num + '-field-tx-' + this.id), //button for making parents
			tree: (value_num + '-field-tr-' + this.id), //parent for the tree
			newrec: (value_num + '-field-new-' + this.id), //for the new record collapse panel
			label_prefix: (value_num + '-field-label-prefix-' + this.id), //for label comosition, label prefix
			id_part: (value_num + '-field-id-part-' + this.id), //for label composition, numeric id part
			id_len: (value_num + '-field-id-len-' + this.id), //for label comosition, id length
			sug_alert: (value_num + '-field-sug-alert-' + this.id), //for label comosition, id length
			sug_label: (value_num + '-field-sug-label-' + this.id), //suggested label
			focal: (value_num + '-field-fcl-' + this.id),  //for scrolling to a part of the page
			lang_out: (value_num + '-field-fcl-' + this.id),  //for language adding options
			lang_sel: (value_num + '-field-lang-sel-' + this.id),  //for language selection input
			lang_literal: (value_num + '-field-lang-lit-' + this.id),  //for language text literal
			lang_valid: (value_num + '-field-lang-valid-' + this.id), //container ID for language validation feedback
			lang_valid_val: (value_num + '-field-lang-valid-val-' + this.id), //hidden input field for language value validation results
			lang_submitcon: (value_num + '-field-lang-sbcon-' + this.id), //container ID for language submitt button
			lang_respncon: (value_num + '-field-lang-respcon-' + this.id), //container ID for language submission response
		};
		return dom_ids;	
	}
	this.value_num_from_domid = function(dom_id){
		// gets the value number from a dom_id
		var domid_ex = dom_id.split('-');
		return domid_ex[0];
	}
	this.expandNewRecord = function(dom_id){
		var value_num = this.value_num_from_domid(dom_id);
		var dom_ids = this.make_field_val_domids(value_num);
		$('#' + dom_id).on('shown.bs.collapse', function () {
			// triggered on shown
			if (document.getElementById(dom_ids.focal)) {
				document.getElementById(dom_ids.focal).scrollIntoView();
				document.body.scrollTop -= 125;
			}
		});
		$('#' + dom_id).collapse('toggle');
	}
	this.make_focal_html = function(value_num){
		var dom_ids = this.make_field_val_domids(value_num);
		//makes a blank div to focus on when the new record is opened
		var html = [
			'<div id="' + dom_ids.focal + '">',
			'</div>'
		].join("\n");
		return html;
	}
	this.make_afterSelectDone_obj = function(value_num, entDomID){
		// starts an object that will include a function to be executed
		// after a user has selected an item in the entity search object
		// result list
		var dom_ids = this.make_field_val_domids(value_num);
		var afterSelectDone = {
			dom_ids: dom_ids,
			entDomID: entDomID,
			value_num: value_num,
			id: this.id,
			name: this.name,
			edit_new: this.edit_new,
			make_field_val_domids: this.make_field_val_domids,
			make_validation_html: this.make_validation_html,
			make_submit_button: this.make_submit_button,
			ids_validation: this.ids_validation,
			value_num_validations: this.value_num_validations,
			pred_type: this.pred_type,
			predicate_uuid: this.predicate_uuid,
			class_pred_uuid: this.class_pred_uuid,
			class_vocab_uri: this.class_vocab_uri,
			context_pred_uuid: this.context_pred_uuid,
			oc_required: this.oc_required,
			after_validation_done: this.after_validation_done,
			after_validation_function: this.after_validation_function,
			values_modified: this.values_modified,
			validation_id_response: this.validation_id_response,
			exec: false
		}
		return afterSelectDone;
	}
	
	/*
	 * AJAX DATA CREATION, EDITING, DELETE FUNCTIONS
	 */
	this.make_field_submission_obj = function(replace_all){
      // make an object for submitting the data
		var values_list = this.get_valid_field_values();
		var act_field = {
			id: this.id,
			label: this.label,
			field_uuid: this.field_uuid,
			predicate_uuid: this.predicate_uuid,
			edit_uuid: this.edit_uuid,
			obs_num: this.obs_num,
			replace_all: replace_all,
			values: values_list
		};
		return act_field;
	}
	this.get_valid_field_values = function(){
		// gets valid values for this field
		var value_num = 0;
		var more = true;
		var value_list = [];
		while (more){
			var act_value = null;
			if (value_num in this.value_num_validations) {
				if (this.value_num_validations[value_num]) {
					var act_value = this.get_field_value(value_num);
				}
			}
			else{
				var dom_ids = this.make_field_val_domids(value_num);
				if (document.getElementById(dom_ids.valid_val)) {
					if (document.getElementById(dom_ids.valid_val).value == '1') {
						var act_value = this.get_field_value(value_num);
					}
				}
			}
			if (act_value != null) {
				value_list.push(act_value);
				value_num += 1;
			}
			else{
				more = false;
			}
		}
		return value_list;
	}
	
	this.addUpdateValue = function(value_num){
		// updates a value if the hash_id is not null
		// adds a new value if the hash_id is null
		var values_list = [];
		var field_val =  this.get_field_value(value_num);
		console.log(field_val);
		if (field_val != null) {
			var is_valid = this.validateValue(value_num);
			if (is_valid) {
				values_list.push(field_val);
			}
			else{
				if (this.data_type == 'xsd:string') {
					// submit string data anyway
					values_list.push(field_val);
				}
			}
		}
		if (values_list.length > 0) {
			var dom_ids = this.make_field_val_domids(value_num);
			if (document.getElementById(dom_ids.valid)) {
				document.getElementById(dom_ids.valid).innerHTML = this.make_loading_gif('Submitting data...');
			}
			if (document.getElementById(dom_ids.submitcon)) {
				document.getElementById(dom_ids.valid).innerHTML = '';
			}
			this.active_value_num = value_num;
			this.ajax_add_update_values(values_list, false);
		}
	}
	this.ajax_add_update_values = function(values_list, replace_all){
		// sends an ajax request to create or update assertion values
		var data = {
			csrfmiddlewaretoken: csrftoken};
		var act_field = {
			id: this.id,
			label: this.label,
			predicate_uuid: this.predicate_uuid,
			obs_num: this.obs_num,
			replace_all: replace_all,
			values: values_list
		};
		if (this.sort != false) {
			act_field.sort = this.sort;
		}
		if (this.draft_sort != false) {
			act_field.draft_sort = this.draft_sort;
		}
		var field_key = this.id;
		field_data = {};
		field_data[field_key] = act_field;
		data['field_data'] = JSON.stringify(field_data, null, 2);
		if (this.profile_uuid == false) {
			if (this.predicate_uuid == this.context_pred_uuid) {
				//changing a containment relationship
				var url = this.make_url("/edit/add-edit-item-containment/");
				url += encodeURIComponent(this.edit_uuid);	
			}
			else{
				var url = this.make_url("/edit/add-edit-item-assertion/");
				url += encodeURIComponent(this.edit_uuid);	
			}
		}
		else{
			var url = this.make_url("/edit/inputs/create-update-profile-item/");
			url += encodeURIComponent(this.profile_uuid);
			url += '/' + encodeURIComponent(this.edit_uuid);
		}
		if (this.predicate_uuid != this.context_pred_uuid) {
			// updates that do not reload the whole item
			return $.ajax({
				type: "POST",
				url: url,
				dataType: "json",
				context: this,
				data: data,
				success: this.ajax_add_update_valuesDone,
				error: function (request, status, error) {
					alert('Data submission failed, sadly. Status: ' + request.status);
				} 
			});
		}
		else{
			// updates that DO reload the whole item
			return $.ajax({
					type: "POST",
					url: url,
					dataType: "json",
					context: this,
					data: data,
					success: this.ajax_add_update_values_reloadDone,
					error: function (request, status, error) {
						alert('Data submission failed, sadly. Status: ' + request.status);
					} 
				});
		}
	}
	this.ajax_add_update_values_reloadDone = function(data){
		console.log(data);
		// too many things to change, so reload the whole page
		location.reload(true);
	}
	this.ajax_add_update_valuesDone = function(data){
		console.log(data);
		if (data.ok) {
			if (this.id in data.data) {
				this.values_obj = data.data[this.id];
				if (document.getElementById(this.values_dom_id)) {
					// data successfully updated, added new values so add them to the dom
					this.prepped_trees = false;
					this.prep_field_trees = []; // prepare field trees
					document.getElementById(this.values_dom_id).innerHTML = this.make_vals_html();
					this.postprocess();
					this.active_value_num = false;
				}
			}
			if (this.single_value_preds.indexOf(this.predicate_uuid) >= 0) {
				//single value
				var dom_ids = this.make_field_val_domids(0);
				var html = [
					'<div style="margin-top: 10px;">',
						'<div class="alert alert-success small" role="alert">',
							'<span class="glyphicon glyphicon-ok-circle" aria-hidden="true"></span>',
							'<span class="sr-only">Success:</span>',
							'Update done.',
						'</div>',
					'</div>'
				].join('\n');
				var act_dom = document.getElementById(dom_ids.respncon);
				act_dom.innerHTML = html;
				setTimeout(function() {
					// display an OK message for a short time
					act_dom.innerHTML = '';
				}, 4500);
			}
		}
		else{
			if (data.hasOwnProperty('additions')) {
				if (this.id in data.additions) {
					for (var i = 0, length = data.additions[this.id].length; i <= length; i++) {
						var val_result = data.additions[this.id][i];
						if (typeof val_result != "undefined") {
							if (val_result.valid == false) {
								this.make_validation_html(val_result.errors, false, val_result.value_num);
							}
						}
					}
				}
			}
			this.active_value_num = false;
		}
	}
	this.deleteFieldValue = function(value_num){
		var dom_ids = this.make_field_val_domids(value_num);
		if (document.getElementById(dom_ids.hash_id)) {
			var hash_id = document.getElementById(dom_ids.hash_id).value;
			this.ajax_delete_value(hash_id);
		}
	}
	this.ajax_delete_value = function(hash_id){
		// sends an ajax request to delete a value
		var data = {
			hash_id: hash_id,
			id: this.id,
			predicate_uuid: this.predicate_uuid,
			obs_num: this.obs_num,
			csrfmiddlewaretoken: csrftoken};
		var url = this.make_url("/edit/delete-item-assertion/");
		url += encodeURIComponent(this.edit_uuid);
		return $.ajax({
				type: "POST",
				url: url,
				dataType: "json",
				context: this,
				data: data,
				success: this.ajax_delete_valueDone,
				error: function (request, status, error) {
					alert('Data deletetion failed, sadly. Status: ' + request.status);
				} 
			});
	}
	this.ajax_delete_valueDone = function(data){
		console.log(data);
		if (data.ok) {
			if (this.id in data.data) {
				this.values_obj = data.data[this.id];
				if (document.getElementById(this.values_dom_id)) {
					// data successfully updated, added new values so add them to the dom
					this.prepped_trees = false;
					this.prep_field_trees = []; // prepare field trees
					document.getElementById(this.values_dom_id).innerHTML = this.make_vals_html();
					this.postprocess();
					this.active_value_num = false;
				}
			}
		}
	}
	this.rankFieldValue = function(value_num, sort_change){
		var dom_ids = this.make_field_val_domids(value_num);
		if (document.getElementById(dom_ids.hash_id)) {
			var hash_id = document.getElementById(dom_ids.hash_id).value;
			this.ajax_sort_value(hash_id, sort_change);
		}
	}
	this.ajax_sort_value = function(hash_id, sort_change){
		// sends an ajax request to delete a value
		var data = {
			hash_id: hash_id,
			sort_change: sort_change,
			id: this.id,
			predicate_uuid: this.predicate_uuid,
			obs_num: this.obs_num,
			csrfmiddlewaretoken: csrftoken};
		var url = this.make_url("/edit/sort-item-assertion/");
		url += encodeURIComponent(this.edit_uuid);
		return $.ajax({
				type: "POST",
				url: url,
				dataType: "json",
				context: this,
				data: data,
				success: this.ajax_sort_valueDone,
				error: function (request, status, error) {
					alert('Data sort change failed, sadly. Status: ' + request.status);
				} 
			});
	}
	this.ajax_sort_valueDone = function(data){
		console.log(data);
		if (data.ok) {
			if (this.id in data.data) {
				this.values_obj = data.data[this.id];
				if (document.getElementById(this.values_dom_id)) {
					// data successfully updated, added new values so add them to the dom
					this.prepped_trees = false;
					this.prep_field_trees = []; // prepare field trees
					document.getElementById(this.values_dom_id).innerHTML = this.make_vals_html();
					this.postprocess();
					this.active_value_num = false;
				}
			}
		}
	}
	this.makeAllValuesList = function(){
		//makes a list of values for a field
		var values_list = [];
		for (var i = 0, length = this.values_obj.length; i <= length; i++) {
			// get all of the values, even the last added one, hence the <= in the line above
			var field_val = this.get_field_value(i);
			if (field_val != null) {
				var is_valid = this.validateValue(i);
				if (is_valid) {
					values_list.push(field_val);
				}
			}
		}
		return values_list;
	}
	this.get_field_value = function(value_num){
		// get the value for submitting
		var field_val = null;
		var literal_val = null;
		var id_val = null;
		var hash_id = null;
		var dom_ids = this.make_field_val_domids(value_num);
		if (document.getElementById(dom_ids.literal)) {
			if (document.getElementById(dom_ids.literal).value.length > 0){
				literal_val = document.getElementById(dom_ids.literal).value;
			}
		}
		if (document.getElementById(dom_ids.id)) {
			if (document.getElementById(dom_ids.id).value.length > 0){
				id_val = document.getElementById(dom_ids.id).value;
			}
		}
		if (document.getElementById(dom_ids.hash_id)) {
			if (document.getElementById(dom_ids.hash_id).value.length > 0){
				hash_id = document.getElementById(dom_ids.hash_id).value;
			}
		}
		if (document.getElementById(dom_ids.valid_val)) {
			// check to see if value_num has a hidden input element
			// that has validation information
			if (document.getElementById(dom_ids.valid_val).value == '1') {
				this.value_num_validations[value_num] = true;
				this.values_modified = true;
			}
			else{
				this.value_num_validations[value_num] = false;
				this.values_modified = true;
			}
		}
		if (literal_val != null || id_val != null) {
			var field_val = {
				'hash_id': hash_id,
				'id': id_val,
				'literal': literal_val,
				'value_num': value_num};
		}
		return field_val;
	}
	
	/*
	 * VALIDATION FUNCTIONS
	 */
	this.validateValue = function(value_num){
		// chooses the appropriate validation method, returns a validation result
		if (this.predicate_uuid == this.label_pred_uuid) {
			var is_valid = this.validateLabel(value_num)
		}
		else if (this.predicate_uuid == this.class_pred_uuid) {
			var is_valid  = this.validateID(value_num);
		}
		else if (this.predicate_uuid == this.context_pred_uuid) {
			var is_valid = this.validateID(value_num);
		}
		else if (this.predicate_uuid == this.note_pred_uuid) {
			var is_valid = this.validateHTML(value_num);
		}
		else{
			if (this.data_type == 'id') {
				var is_valid = this.validateID(value_num);
			}
			else if (this.data_type == 'xsd:integer' || this.data_type == 'xsd:double') {
				var is_valid = this.validateNumber(value_num);
			}
			else if (this.data_type == 'xsd:date') {
				var is_valid = this.validateDate(value_num);
			}
			else if (this.data_type == 'xsd:boolean') {
				var is_valid = this.validateBoolean(value_num);
 			}
			else if (this.data_type == 'xsd:string') {
				var is_valid = this.validateHTML(value_num);
			}
			else{
				var is_valid = false;	
			}
		}
		return is_valid;
	}
	this.after_validation_function = function(){
		if (this.after_validation_done != false && this.oc_required) {
			// execute function after validation
			if (typeof(this.after_validation_done.exec) !== 'undefined') {
				console.log('Do after validation done...' + this.label);
				this.after_validation_done.exec();
			}
		}
	}
	this.validateID = function(value_num){

		var is_valid = this.check_cached_id_valid(value_num);

		if (is_valid) {
			this.validation_id_response(is_valid, value_num);
			return is_valid;
		}
		else{
			// the item is not yet known to be valid (either null or false)
			// so make an AJAX request to check
			return this.ajax_validate_id(value_num);
		}
	}
	this.validateButtonID = function(value_num){
        // validates and leaves a submit button to use
		var is_valid = this.check_cached_id_valid(value_num);

		if (is_valid) {
			this.validation_id_response(is_valid, value_num);
		}
		else{
			// the item is not yet known to be valid (either null or false)
			// so make an AJAX request to check
			this.ajax_validate_id(value_num);
		}
		this.make_submit_button(is_valid, value_num);
		return is_valid;
	}
	this.check_cached_id_valid = function(value_num){
		var is_valid = null; //not cached
		var dom_ids = this.make_field_val_domids(value_num);
		if (document.getElementById(dom_ids.id)) {
			var item_id = document.getElementById(dom_ids.id).value;
			var item = false;
			if (item_id in this.ids_validation) {
				var item = this.ids_validation[item_id];
			}
			if (item != false) {
				is_valid = false;
				if (document.getElementById(dom_ids.label)) {
					document.getElementById(dom_ids.label).value = item.label;
				}
				if (this.predicate_uuid == this.class_pred_uuid) {
					if (item.vocab_uri == this.class_vocab_uri) {
						is_valid = true;
					}
				}
				else if (this.predicate_uuid == this.context_pred_uuid)  {
					if (item.item_type == 'subjects') {
						is_valid = true;
					}
				}
				else{
					if (this.pred_type == 'variable') {
						if (item.item_type == 'types') {
							is_valid = true;
						}
					}
					else{
						is_valid = true;	
					}
				}
			}
			else{
				is_valid = false;
				if (this.predicate_uuid == this.context_pred_uuid){
					// we've got a containment item. check to see if it is a root item
					if (item_id == 'ROOT'){
						if (document.getElementById(dom_ids.label)) {
							document.getElementById(dom_ids.label).value = 'Global Root';
						}
						is_valid = true;
					}
				}
			}
		}
		return is_valid;
	}
	this.ajax_validate_id = function(value_num){
		this.active_value_num = value_num;
		var dom_ids = this.make_field_val_domids(value_num);
		var item_id = false;
		if (document.getElementById(dom_ids.id)) {
			var item_id = document.getElementById(dom_ids.id).value;
		}
		if (item_id == false) {
			return false;
		}
		else{
			var url = this.make_url("/entities/id-summary/" + encodeURIComponent(item_id));
			return $.ajax({
				type: "GET",
				url: url,
				dataType: "json",
				context: this,
				success: this.ajax_validate_idDone,
				error: function (request, status, error) {
					this.ids_validation[item_id] = false;
					this.validation_id_response(false, value_num);
				}
			});
		}
	}
	this.ajax_validate_idDone = function(data){
		var is_valid = false;
		var value_num = this.active_value_num;
		var dom_ids = this.make_field_val_domids(value_num);
		this.active_value_num = false;
		if (document.getElementById(dom_ids.id)) {
			var item_id = document.getElementById(dom_ids.id).value;
			this.ids_validation[item_id] = data;
			var is_valid = this.check_cached_id_valid(value_num);
		}
		this.validation_id_response(is_valid, value_num);
		this.values_modified = true; // a value was modified
		return is_valid;
	}
	this.validation_id_response = function(is_valid, value_num){
		//console.log(this.pred_type);
		var dom_ids = this.make_field_val_domids(value_num);
		if (is_valid) {
			if (this.predicate_uuid == this.class_pred_uuid) {
				var val_mes = 'Valid classification input.'; 
			}
			else if (this.predicate_uuid == this.context_pred_uuid) {
				var val_mes = 'Valid context input.';
			}
			else{
				if (this.pred_type == 'variable') {
					var val_mes = 'Valid category input.';
				}
				else{
					var val_mes = 'Valid linked item input.';
				}
			}
		}
		else{
			if (this.predicate_uuid == this.class_pred_uuid) {
				var val_mes = 'Classification input not valid Open Context class'; 
			}
			else if (this.predicate_uuid == this.context_pred_uuid) {
				var val_mes = 'Context input not a recognized subject item';
			}
			else{
				if (this.pred_type == 'variable') {
					var val_mes = 'Category input not a recognized type item';
				}
				else{
					var val_mes = 'Linked item not recognized';
				}
			}
		}
		this.make_validation_html(val_mes, is_valid, value_num);
		this.value_num_validations[value_num] = is_valid;
		this.values_modified = true;
		this.after_validation_function();
	}
	this.validateHTML = function(value_num){
		// calls a function to make an ajax request to validate HTML
		this.ajax_validate_html(value_num);
	}
	this.ajax_validate_html = function(value_num){
		// AJAX request to validate HTML
		this.html_validation = true;
		this.active_value_num = value_num;
		var dom_ids = this.make_field_val_domids(value_num);
		if (document.getElementById(dom_ids.literal)) {
			var text = document.getElementById(dom_ids.literal).value;
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
				success: this.ajax_validate_htmlDone,
				error: function (request, status, error) {
					alert('Request to validate HTML failed, sadly. Status: ' + request.status);
				}
			});
		}
		else{
			return false;
		}
	}
	this.ajax_validate_htmlDone = function(data){
		var value_num = this.active_value_num;
		var dom_ids = this.make_field_val_domids(value_num);
		this.active_value_num = false;
		if (data.ok) {
			var val_mes = 'Input text OK to use as HTML';
			this.make_validation_html(val_mes, true, value_num);
			this.make_submit_button(true, value_num);
		}
		else{
			var val_mes = data.errors.html;
			this.make_validation_html(val_mes, false, value_num);
			this.make_submit_button(false, value_num);
		}
		this.html_validation = false;
		this.value_num_validations[value_num] = data.ok;
		this.values_modified = true; // a value was modified
		this.after_validation_function();
	}
	this.validateNumber = function(value_num){
		//validates numeric fields
		var is_valid = false;
		var dom_ids = this.make_field_val_domids(value_num);
		var check_val = document.getElementById(dom_ids.literal).value;
		if (isNaN(check_val)){
			// not a number returned true
			var val_mes = 'Not a numeric ' + this.get_human_readable_data_type(this.data_type) + ' value.';
			this.make_validation_html(val_mes, false, value_num);
		}
		else{
			// numeric result detected, now make sure it fits the specific datatype
			if (this.data_type == 'xsd:double') {
				check_val = parseFloat(check_val);
				if (this.isFloat(check_val)) {
					is_valid = true;
					var val_mes = 'Valid ' + this.get_human_readable_data_type(this.data_type) + ' value.';
					this.make_validation_html(val_mes, true, value_num);
				}
				else{
					var val_mes = 'Not a valid ' + this.get_human_readable_data_type(this.data_type) + ' value.';
					this.make_validation_html(val_mes, false, value_num);
				}
			}
			if (this.data_type == 'xsd:integer') {
				var check_val = parseFloat(check_val);
				if (this.isInt(check_val)) {
					is_valid = true;
					var val_mes = 'Valid ' + this.get_human_readable_data_type(this.data_type) + ' value.';
					this.make_validation_html(val_mes, true, value_num);
				}
				else{
					var val_mes = 'Not a valid ' + this.get_human_readable_data_type(this.data_type) + ' value.';
					this.make_validation_html(val_mes, false, value_num);
				}
			}	
		}
		this.value_num_validations[value_num] = is_valid;
		this.values_modified = true; // a value was modified
		return is_valid;
	}
	this.validateDate = function(value_num){
		// validates date fields to a yyyy-mm-dd format
		var dom_ids = this.make_field_val_domids(value_num);
		var str = document.getElementById(dom_ids.literal).value;
	   var valid_date = this.isValidDate(str);
		if (valid_date) {
			var val_mes = 'Valid calendar date value.';
			this.make_validation_html(val_mes, true, value_num);
		}
		else{
			var val_mes = 'Not a valid calendar date (yyyy-mm-dd) value.';
			this.make_validation_html(val_mes, false, value_num);
		}
		this.value_num_validations[value_num] = valid_date;
		this.values_modified = true; // a value was modified
		return valid_date;
	}
	this.validateBoolean = function(value_num){
		// validates date fields to a yyyy-mm-dd format
		var dom_ids = this.make_field_val_domids(value_num);
		var str = document.getElementById(dom_ids.literal).value.toLowerCase();
		var parsed_boolean = this.parseStrBoolean(str);
	   if (parsed_boolean != null) {
			var boolean_ok = true;
			if (parsed_boolean) {
				var val_mes = 'Valid <strong>True</strong> value indicated.';	
			}
			else{
				var val_mes = 'Valid <strong>False</strong> value indicated.';
			}
			this.make_validation_html(val_mes, true, value_num);
		}
		else{
			var boolean_ok = false;
			var val_mes = 'Cannot be understood as a Boolean (True/False) value.';
			this.make_validation_html(val_mes, false, value_num);
		}
		this.value_num_validations[value_num] = boolean_ok;
		this.values_modified = true; // a value was modified
		return boolean_ok;
	}
	this.parseStrBoolean = function(check_str){
		check_str = check_str + '';
		var str = check_str.toLowerCase();
		var ok_values = {	'n': false,
								'no': false,
								'none': false,
								'absent': false,
								'a': false,
								'false': false,
								'f': false,
								'0': false,
								'y': true,
								'yes': true,
								'present': true,
								'p': true,
								'true': true,
								't': true}
		if (str in ok_values) {
			var boolean_ok = true;
			var truth_val = ok_values[str];
		}
		else{
			var truth_val = null;
		}
		return truth_val;
	}
	this.booleanSelect = function(bool_num, literal_id){
		if (bool_num == 1) {
			document.getElementById(literal_id).value = 'True';
		}
		else{
			document.getElementById(literal_id).value = 'False';
		}
	}
	this.make_validation_html = function(message_html, is_valid, value_num){
		var dom_ids = this.make_field_val_domids(value_num);
		if (is_valid) {
			var icon_html = '<span class="glyphicon glyphicon-ok-circle" aria-hidden="true"></span>';
			var alert_class = "alert alert-success";
			var val_status = '<input id="' + dom_ids.valid_val + '" type="hidden" value="1" />';
		}
		else{
			var icon_html = '<span class="glyphicon glyphicon-warning-sign" aria-hidden="true"></span>';
			var alert_class = this.invalid_alert_class;
			var val_status = '<input id="' + dom_ids.valid_val + '" type="hidden" value="0" />';
		}
		var alert_html = [
				'<div role="alert" class="' + alert_class + '" >',
					icon_html,
					message_html,
					val_status,
				'</div>'
			].join('\n');
		
		if (document.getElementById(dom_ids.valid)) {
			var act_dom = document.getElementById(dom_ids.valid);
			act_dom.innerHTML = alert_html;
		}
		else{
			alert("cannot find " + dom_ids.valid);
		}
		this.make_submit_button(is_valid, value_num);
		return alert_html;
	}
	this.make_submit_button = function(is_valid, value_num){
		// console.log('Making that button, again for ' + value_num);
		var dom_ids = this.make_field_val_domids(value_num);
		
		if (is_valid) {
			var button_html = [
				'<div style="margin-top: 10px;">',
					'<button class="btn btn-success btn-block" onclick="' + this.name + '.addUpdateValue(\'' + value_num + '\');">',
					'<span class="glyphicon glyphicon-cloud-upload" aria-hidden="true"></span>',
					' Submit',
					'</button>',
				'</div>'
			].join('\n');
		}
		else if (is_valid == false && this.html_validation) {
			
			if (document.getElementById(dom_ids.valid_val)) {
				document.getElementById(dom_ids.valid_val).value = '1';
			}
			
			//code allow submission of bad HTML
			var button_html = [
				'<div style="margin-top: 10px;">',
					'<button class="btn btn-warning btn-block" onclick="' + this.name + '.addUpdateValue(\'' + value_num + '\');">',
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
				'</div>'
			].join('\n');
			button_html = '';
		}
		if (this.edit_new == false) {
			// only add the button if edit_new is false
			if (document.getElementById(dom_ids.submitcon)) {
				document.getElementById(dom_ids.submitcon).innerHTML = button_html;
			}
		}
		return button_html;
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
	this.validateTranslationHTML = function(value_num){
		// calls a function to make an ajax request to validate translation HTML
		this.ajax_validate_translation_html(value_num);
	}
	this.ajax_validate_translation_html = function(value_num){
		// AJAX request to validate HTML
		this.active_value_num = value_num;
		var dom_ids = this.make_field_val_domids(value_num);
		if (document.getElementById(dom_ids.lang_literal)) {
			var text = document.getElementById(dom_ids.lang_literal).value;
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
		var value_num = this.active_value_num;
		var dom_ids = this.make_field_val_domids(value_num);
		this.active_value_num = false;
		if (data.ok) {
			var val_mes = 'Input text OK to use as HTML';
			this.make_translation_submit_button(true, value_num);
			this.make_translation_validation_html(val_mes, true, value_num);
		}
		else{
			var val_mes = data.errors.html;
			this.make_translation_submit_button(false, value_num);
			this.make_translation_validation_html(val_mes, false, value_num);
		}
	}
	this.make_translation_submit_button = function(is_valid, value_num){
		//makes a submission button for translation
		var dom_ids = this.make_field_val_domids(value_num);
		var language_code = null;
		if (document.getElementById(dom_ids.lang_sel)) {
			var select_dom = document.getElementById(dom_ids.lang_sel);
			var language_code = select_dom.value;
		}
		if (is_valid && language_code != null) {
			var button_html = [
				'<div style="margin-top: 10px;">',
					'<button class="btn btn-success btn-block" onclick="' + this.name + '.addEditStringTranslation(\'' + value_num + '\');">',
					'<span class="glyphicon glyphicon-cloud-upload" aria-hidden="true"></span>',
					' Submit',
					'</button>',
				'</div>'
			].join('\n');
		}
		else if (is_valid == false && language_code != null) {
			
			if (document.getElementById(dom_ids.lang_valid_val)) {
				document.getElementById(dom_ids.lang_valid_val).value = '1';
			}
			
			//code allow submission of bad HTML
			var button_html = [
				'<div style="margin-top: 10px;">',
					'<button class="btn btn-warning btn-block" onclick="' + this.name + '.addEditStringTranslation(\'' + value_num + '\');">',
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
		if (document.getElementById(dom_ids.lang_submitcon)) {
			document.getElementById(dom_ids.lang_submitcon).innerHTML = button_html;
		}
		return button_html;
	}
	this.make_translation_validation_html = function(message_html, is_valid, value_num){
		var dom_ids = this.make_field_val_domids(value_num);
		if (is_valid) {
			var icon_html = '<span class="glyphicon glyphicon-ok-circle" aria-hidden="true"></span>';
			var alert_class = "alert alert-success";
			var val_status = '<input id="' + dom_ids.lang_valid_val + '" type="hidden" value="1" />';
		}
		else{
			var icon_html = '<span class="glyphicon glyphicon-warning-sign" aria-hidden="true"></span>';
			var alert_class = this.invalid_alert_class;
			var val_status = '<input id="' + dom_ids.lang_valid_val + '" type="hidden" value="0" />';
		}
		var alert_html = [
				'<div role="alert" class="' + alert_class + '" >',
					icon_html,
					message_html,
					val_status,
				'</div>'
			].join('\n');
		
		if (document.getElementById(dom_ids.lang_valid)) {
			var act_dom = document.getElementById(dom_ids.lang_valid);
			act_dom.innerHTML = alert_html;
		}
		else{
			alert("cannot find " + dom_ids.lang_valid);
		}
	}
	
	/* ---------------------------------------
	 * User interaction functions
	 *
	 * for item labels
	 * ---------------------------------------
	 */
	this.composeLabel = function(value_num){
		var dom_ids = this.make_field_val_domids(value_num);
		var id_part = document.getElementById(dom_ids.id_part).value.trim();
		var prefix = document.getElementById(dom_ids.label_prefix).value;
		var id_len = parseInt(document.getElementById(dom_ids.id_len).value);
		if (!this.isInt(id_len)) {
			document.getElementById(dom_ids.id_len).value = '';
			id_len = '';
			var id_part = id_part.replace(prefix, '');
		}
		else{
			var id_part = id_part.replace(prefix, '');
			id_part =  this.prepend_zeros(id_part, id_len);
		}
		var label = prefix + id_part;
		document.getElementById(dom_ids.literal).value = label.trim();
		if (id_part.length > 0) {
			if (id_part != ' ') {
				// the ID part has some values, so one can validate it
				// with an AJAX request
				this.passed_value = label;
				this.validateLabel(value_num);
			}
		}
		
	}
	this.validateLabel = function(value_num){
		var dom_ids = this.make_field_val_domids(value_num);
		this.active_value_num = value_num; // so as to remember what we are validating
		var url = this.make_url('/edit/inputs/item-label-check/' + encodeURIComponent(this.project_uuid));
		var data = {
			item_type: this.item_type,
		    uuid: this.edit_uuid
		};
		
		var id_len = parseInt(document.getElementById(dom_ids.id_len).value);
		if (this.isInt(id_len)) {
			data.id_len = id_len;
			this.label_id_len = id_len; // to pass to the profile object, if used
		}
		if (this.passed_value == false) {
			var label = document.getElementById(dom_ids.literal).value;
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
		
		var prefix = document.getElementById(dom_ids.label_prefix).value;
		if (prefix.length > 0) {
			data.prefix = prefix;
			this.label_prefix = prefix;  // to pass to the profile object, if used
		}
		if (this.context_uuid != false) {
			data.context_uuid = this.context_uuid;
		}
		var act_dom = document.getElementById(dom_ids.valid);
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
   
	this.presetLabel = function(value_num){
		// same as validate, just use the preset_label flag
		this.preset_label = true;
		return this.validateLabel(value_num);	
	}
	this.validateLabelDone = function(data){
		var value_num = this.active_value_num;
		this.active_value_num = false;
		var dom_ids = this.make_field_val_domids(value_num); 
		
		var act_dom = document.getElementById(dom_ids.valid);
		var is_valid = false;
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
			is_valid = true;
			var icon_html = '<span class="glyphicon glyphicon-ok-circle" aria-hidden="true"></span>';
			if (data.checked == data.suggested) {
				// checked label is the same as the suggested
				var message_html = [
					'The label "' + data.checked + '" is valid.',
				].join('\n');	
			}
			else{
				var message_html = [
					'The label "' + data.checked + '" is not yet in use.',
				].join('\n');	
			}
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
				' role="button" onclick="' + this.name + '.useSuggestedLabel(' + value_num + ');" '
			].join(' ');
			if (document.getElementById(dom_ids.literal).value != data.suggested) {
				var suggest_hint = ' (Click to use)';
			}
			else{
				var suggest_hint = '';
			}
			
			var suggest_html = [
			'<div ' + div_start + '>',
			'<div role="alert" class="' + alert_class + '" id="' + dom_ids.sug_alert + '">',
			'Suggested Label' + suggest_hint + ': ',
			'<a title="Use suggested link" ' + suggested_link + ' >',
			'<span class="glyphicon glyphicon-circle-arrow-left"></span>',
			'</a> ',
			'<a title="Use suggested link" ' + suggested_link + ' >',
			'<samp class="uri-id" id="' + dom_ids.sug_label + '" style="font-weight:bold;">',
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
		
		if (is_valid) {
			var val_status = '<input id="' + dom_ids.valid_val + '" type="hidden" value="1" />';
		}
		else{
			var val_status = '<input id="' + dom_ids.valid_val + '" type="hidden" value="0" />';
		}
		
		var html = [
			'<div style="margin-top: 3px;">',
			alert_html,
			val_status,
			suggest_html,
			'</div>'
		].join("\n");
		act_dom.innerHTML = html;
		this.make_submit_button(is_valid, value_num);
		this.value_num_validations[value_num] = is_valid;
		this.values_modified = true; // a value was modified
		
		// do this with the preset_label function
		if (this.preset_label) {
			//we wanted to use data.suggested to preset the label
			this.preset_label = false;
			document.getElementById(dom_ids.literal).value = data.suggested;
			this.useSuggestedLabel(value_num);
		}
		
		this.after_validation_function();
	}
	this.useSuggestedLabel = function(value_num){
		// copies the suggested label into the label field
		var dom_ids = this.make_field_val_domids(value_num); 
		var label = document.getElementById(dom_ids.sug_label).innerHTML;
		document.getElementById(dom_ids.literal).value = label.trim();
		document.getElementById(dom_ids.sug_alert).innerHTML = "Using suggested label: " + label;
		this.passed_value = label.trim();
		this.validateLabel(value_num);
	}
	
	
	
	/* ---------------------------------------
	 * Functions
	 * related to tree interfaces for selecting values
	 * for nominal (id) fields, categories (class_uri),
	 * or spatial contexts (subjects)
	 * ---------------------------------------
	 */
	this.selectTreeItem = function(id, label, item_type, tree_dom_id){
		// this is the function called in onclick events when
		// a user has selected an item from a tree to be used
		// to populate a value for a field
		id = id.trim();
		var value_num = this.value_num_from_domid(tree_dom_id);
		var dom_ids = this.make_field_val_domids(value_num);
		document.getElementById(dom_ids.label).value = label.trim();
		document.getElementById(dom_ids.id).value = id;
		this.ids_validation[id] = {label: label.trim(),
											item_type: item_type,
											vocab_uri: false};
		this.validation_id_response(true, value_num);
	}
	this.prep_field_tree = function(value_num, root_node_id, tree_type){
		// adds an object to a list to prepare for creating trees
		// with values to be used to populate fields
		var tree_item = {
			value_num: value_num,
			root_node_id: root_node_id,
		   tree_type: tree_type
		};
		this.prep_field_trees.push(tree_item);
	}
	this.make_trees = function(){
		// goes throough the list of preped tree items to actually
		// generate the tree HTML
		if (this.prepped_trees == false) {
			this.prepped_trees = true;
			for (var i = 0, length = this.prep_field_trees.length; i < length; i++) {
				var tree_item = this.prep_field_trees[i];
				this.make_field_tree_html(tree_item.value_num,
												  tree_item.root_node_id,
												  tree_item.tree_type);
			}
		}
		
	}
	this.make_field_tree_html = function(value_num, root_node_id, tree_type){
		// makes the actual tree interface based on parameters passed
		// is useful for:
		// categories (class_uri),
		// descriptions (predicates + types),
		// and contexts (subjects / locations / objects)
		var dom_ids = this.make_field_val_domids(value_num);
		var parent_dom_id = dom_ids.tree;
		var tree = new hierarchy(root_node_id, parent_dom_id);
		if (this.field_uuid != false) {
			var tree_id = value_num + '-fuuid-' + this.field_uuid;
		}
		else{
			var tree_id = value_num + '-preduuid-' + this.predicate_uuid.replace(':','-');	
		}
		tree.root_node = true;  //root node of this tree
		tree.collapse_root = true;
		tree.object_prefix = 'tree-' + tree_id;
		tree.exec_primary_onclick = this.name + '.selectTreeItem'; // name of the function to use onclicking a tree item
		tree.exec_primary_passed_val = dom_ids.tree; //value to pass in the onclick function.
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
	
		// tree.get_data().then(this.showTree(value_num));
		tree.get_data().then(this.collapseTree(value_num));
		var tree_key = tree.object_prefix; 
		hierarchy_objs[tree_key] = tree;
		//this.collapseTree(value_num);
		//console.log(hierarchy_objs);
	}
	this.collapseTree = function(value_num){
		var dom_ids = this.make_field_val_domids(value_num);
		$('#' + dom_ids.tree).collapse('hide');
		this.field_tree_collapsed[value_num] = true;
		if (document.getElementById(dom_ids.treebut)) {
			var a_link = document.getElementById(dom_ids.treebut);
			a_link.innerHTML = '<span class="hierarchy-tog glyphicon glyphicon-plus" aria-hidden="true"></span>';
		}
		//console.log(this.field_tree_collapsed);
	}
	this.showTree = function(value_num){
		var dom_ids = this.make_field_val_domids(value_num);
		$('#' + dom_ids.tree).collapse('show');
		this.field_tree_collapsed[value_num] = true;
		if (document.getElementById(dom_ids.treebut)) {
			var a_link = document.getElementById(dom_ids.treebut);
			a_link.innerHTML = '<span class="hierarchy-tog glyphicon glyphicon-minus" aria-hidden="true"></span>';
		}
		//console.log(this.field_tree_collapsed);
	}
	this.toggleCollapseTree = function(value_num){
		var dom_ids = this.make_field_val_domids(value_num);
		if (value_num in this.field_tree_collapsed) {
			var collapsed = this.field_tree_collapsed[value_num];
		}
		else{
			var collapsed = false; // start out with assumption the tree is not collapsed
		}
		if (collapsed) {
			this.make_trees();
			$('#' + dom_ids.tree).collapse('show');
			this.field_tree_collapsed[value_num] = false;
			if (document.getElementById(dom_ids.treebut)) {
				var a_link = document.getElementById(dom_ids.treebut);
				a_link.innerHTML = '<span class="hierarchy-tog glyphicon glyphicon-minus" aria-hidden="true"></span>';
			}
		}
		else{
			$('#' + dom_ids.tree).collapse('hide');
			this.field_tree_collapsed[value_num] = true;
			if (document.getElementById(dom_ids.treebut)) {
				var a_link = document.getElementById(dom_ids.treebut);
				a_link.innerHTML = '<span class="hierarchy-tog glyphicon glyphicon-plus" aria-hidden="true"></span>';
			}
		}
		//console.log(this.field_tree_collapsed);
	}
	
	
	
	
	
	
	/*  Post-processing functions executed
	 *  the fields have been added to the DOM
	 */
	
	this.activate_calendars = function(){
		if (this.data_type == 'xsd:date') {
			for (var i = 0, length = this.values_obj.length; i <= length; i++) {
				var dom_ids = this.make_field_val_domids(i);
				if (document.getElementById(dom_ids.datecon)) {
					$("#" + dom_ids.datecon).datepicker({
						format: "yyyy-mm-dd",
						todayHighlight: true,
						forceParse: false
					});
				}
			}
		}
	}
	this.activate_expand_collapse = function(){
		var value_num = this.values_obj.length;
		var dom_ids = this.make_field_val_domids(value_num);
		if (document.getElementById(dom_ids.newrec)) {
			$('#' + dom_ids.newrec).collapse({
				toggle: false
			});
			$('#' + dom_ids.newrec).collapse('hide');
		}
		if (document.getElementById(dom_ids.tree)) {
			$('#' + dom_ids.tree).collapse({
				toggle: false
			});
			$('#' + dom_ids.tree).collapse('hide');
		}
		if (this.prep_field_trees.length > 0) {
			for (var i = 0, length = this.prep_field_trees.length; i < length; i++) {
				var prep_tree = this.prep_field_trees[i];
				// this.collapseTree(prep_tree.value_num);
			}
		}
	}
	
	/*
	 * Supplemental Functions (used throughout)
	 */ 
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
	
} // end of the edit_field_object
