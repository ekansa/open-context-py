/*
 * This provides interfaces and validation checks on fields for data entry and date eding
 *
 */

function edit_field(){
	
	this.edit_uuid = false;  //uuid of the item being edited
	this.edit_new = false;  //is the item new (true, not created) or false (being edited)
	this.item_type = false;
	this.id = 1;
	this.project_uuid = false;
	this.field_uuid = false;
	this.label = false;
	this.data_type = false;
	this.predicate_uuid = false;
	this.note = false;
	this.oc_required = false;
	this.validation = false;
	this.values_obj = []; // list of values associated with an item
	this.parent_obj_name = false;
	this.obj_name = false;
	this.name = false;
	this.show_predicate_link = true;
	this.invalid_alert_class = "alert alert-warning";
	this.value_del_col_class = 'col-xs-1';
	this.value_sort_col_class = 'col-xs-1';
	this.value_col_class = 'col-xs-6';
	this.valid_col_class = 'col-xs-4';
	this.label_pred_uuid = 'oc-gen:label';
	this.class_pred_uuid = 'oc-gen:class_uri';
	this.context_pred_uuid = 'oc-gen:contained-in';
	this.note_pred_uuid = 'oc-gen:has-note';
	this.add_new_data_row = true;
	// for panel ids
	this.panels = [];
	// entity search object
	this.sobjs = [];
	// tree specific attributes
	this.prepped_trees = false;
	this.prep_field_trees = []; // prepare field trees
	this.field_tree_collapsed = {}; // key is the field ID, boolean value for collapsed state
	
	this.make_field_html = function(){
		
		this.make_name();
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
		
		var html = [
		'<tr>',
		'<td id="f-bu-' + this.id + '">',
      this.make_field_update_buttom_html(this.id),
		'</td>',
		'<td>',
		this.make_pred_label_html(),
		'</td>',
		'<td id="f-vals-' + this.id + '">',
		vals_html,
		note_html,
		'</td>',
		'</tr>'
		].join("\n");
		return html;
	}
	this.postprocess = function(){
		//do these functions after the html is added to the dom
		this.activate_calendars();
		this.activate_expand_collapse();
		this.make_trees();
	}
	
	this.make_vals_html = function(){
		//make the html for the field
		this.make_name();
		var values_obj = this.values_obj;
		if (this.add_new_data_row) {
			// add a data entry row
			var new_value_obj = {'new': true};
			values_obj.push(new_value_obj);	
		}
		var vals_html = [
			'<div class="container-fluid">'
		];
		
		for (var i = 0, length = values_obj.length; i < length; i++) {
			var value_obj = values_obj[i];
			if (this.predicate_uuid == this.label_pred_uuid) {
				var val_html = this.make_label_val_html(i, value_obj);
			}
			else if (this.predicate_uuid == this.class_pred_uuid) {
				var val_html = this.make_category_val_html(i, value_obj);
			}
			else if (this.predicate_uuid == this.context_pred_uuid) {
				var val_html = this.make_context_val_html(i, value_obj);
			}
			else if (this.predicate_uuid == this.note_pred_uuid) {
				var val_html = this.make_note_val_html(i, value_obj);
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
				
				var exp_html = [
					this.make_focal_html(i),
					'<div class="panel-group">',
						'<div class="panel panel-default" style="margin-top:4px;">',
							'<div class="panel-heading">',
								//'<p>',
								button_html,
								' Add a <em>' + this.label + '</em> value',
								//'</p>',
							'</div>',
							'<div id="' +  dom_ids.newrec + '" class="collapse" >',
								'<div class="panel-body">',
								val_html,
								'</div>',
							'</div>',
						'</div>',
					'</div>',
				].join("\n");
				
				if (this.data_type == 'id') {
					var row_html = [
						'<div class="row">',
							'<div class="col-xs-1">',
							button_html,
							'</div>',
							'<div class="col-xs-7">',
							exp_html,
							'</div>',
							'<div class="' + this.valid_col_class + '" id="' + dom_ids.valid + '">',
							'</div>',
						'</div>',
					].join('\n');
					
					var row_html = [
						'<div class="row">',
							'<div class="col-xs-8">',
							exp_html,
							'</div>',
							'<div class="' + this.valid_col_class + '" id="' + dom_ids.valid + '">',
							'</div>',
						'</div>',
					].join('\n');
				}
				else{
					var row_html = [
						'<div class="row">',
							'<div class="col-xs-1">',
							button_html,
							'</div>',
							'<div class="col-xs-1">',
							'</div>',
							'<div class="' + this.value_col_class + '">',
							exp_html,
							'</div>',
							'<div class="' + this.valid_col_class + '" id="' + dom_ids.valid + '">',
							'</div>',
						'</div>',
					].join('\n');
					
					var row_html = [
						'<div class="row">',
							'<div class="col-xs-8">',
							exp_html,
							'</div>',
							'<div class="' + this.valid_col_class + '" id="' + dom_ids.valid + '">',
							'</div>',
						'</div>',
					].join('\n');
				}
			}
			else{
				var row_html = [
					'<div class="row">',
						'<div class="' + this.value_del_col_class + '">',
						'</div>',
						'<div class="' + this.value_sort_col_class + '">',
						'</div>',
						'<div class="' + this.value_col_class + '">',
						val_html,
						'</div>',
						'<div class="' + this.valid_col_class + '" id="' + dom_ids.valid + '">',
						'</div>',
					'</div>',
				].join('\n');
			}
			
			vals_html.push(row_html);
		}
		vals_html.push('</div>');
		return vals_html.join("\n");
	}
	this.make_name = function(){
		// makes the name of the object for called functions
		if (this.parent_obj_name != false) {
			this.name = this.parent_obj_name + '.' + this.obj_name;
		}
		else{
			this.name = this.obj_name;
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
				'onkeydown="' + this.name + '.validateBoolean(\'' + dom_ids.literal + '\');" ',
				'onkeyup="' + this.name + '.validateBoolean(\'' + dom_ids.literal + '\');" ',
				'onchange="' + this.name + '.validateBoolean(\'' + dom_ids.literal + '\');" ',
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
				'<input id="' + dom_ids.literal + '" class="form-control input-sm" ',
				'type="hidden" value="' + bool_value + '" ',
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
					'<input id="' + dom_ids.literal + '" class="form-control input-sm" ',
					'type="text" value="' + display_value + '" ' + placeholder,
					'onkeydown="' + this.name + '.validateDate(\'' + dom_ids.literal + '\');" ',
					'onkeyup="' + this.name + '.validateDate(\'' + dom_ids.literal + '\');" ',
					'onchange="' + this.name + '.validateDate(\'' + dom_ids.literal + '\');" ',
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
			'<input id="' + dom_ids.literal + '" class="form-control input-sm" ',
			'type="text" value="' + display_value +  '" ' + placeholder,
			'onkeydown="' + this.name + '.validateNumber(\'' + dom_ids.literal + '\');" ',
			'onkeyup="' + this.name + '.validateNumber(\'' + dom_ids.literal + '\');" ',
			'/>',
			'</div>',
		].join("\n");
		return html;
	}
	this.make_string_val_html = function(value_num, value_obj){
		var display_value = '';
		var dom_ids = this.make_field_val_domids(value_num);
		var hr_data_type = this.get_human_readable_data_type(this.data_type);
		var placeholder = ' placeholder="Free-form alphanumeric text (including HTML)" ';
		if (value_obj.hasOwnProperty('literal')) {
			display_value = value_obj.literal;
		}
		var html = [
			'<textarea id="' + dom_ids.literal + '" class="form-control input-sm" rows="3" ' + placeholder + ' >',
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
			this.prep_field_tree(value_num, this.predicate_uuid, 'description');
		
			// make an entity search for contexts
			var entityInterfaceHTML = "";
			/* changes global authorSearchObj from entities/entities.js */
			
			var entSearchObj = new searchEntityObj();
			var ent_name = 'sobjs[' + sobj_id + ']';
			entSearchObj.name = ent_name;
			entSearchObj.ultra_compact_display = true;
			entSearchObj.parent_obj_name = this.name;
			entSearchObj.entities_panel_title = "Select a Category for " + this.label;
			entSearchObj.limit_item_type = "types";
			entSearchObj.limit_context_uuid = this.predicate_uuid;
			entSearchObj.limit_project_uuid = "0," + this.project_uuid;
			var entDomID = entSearchObj.make_dom_name_id();
			var afterSelectDone = {
				dom_ids: dom_ids,
				entDomID: entDomID,
				exec: function(){
					var sel_id = document.getElementById(this.entDomID + "-sel-entity-id").value;
					var sel_label = document.getElementById(this.entDomID +  "-sel-entity-label").value;
					document.getElementById(this.dom_ids.label).value = sel_label;
					document.getElementById(this.dom_ids.id).value = sel_id;
				}
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
				'type="text" value="' + display_id + '" />',
				'</div>',
				'<div class="well well-sm small">',
					'<label><u>Option A</u>: Search <em>' + this.label + '</em></label>',
					entityInterfaceHTML,
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
				'</div>',
			].join("\n");
		}
		else{
			var html = this.make_labeled_id_link_html(value_obj.label, value_obj.uuid, dom_ids);
		}
		return html;
	}
	this.make_label_val_html = function(){
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
		'<td id="f-bu-' + this.id + '">',
      this.make_field_update_buttom_html(this.id),
		'</td>',
		'<td>',
			'<div class="form-group">',
			'<label for="f-' + this.id + '">' + this.label + '</label>',
			'<input id="f-' + this.id + '" class="form-control input-sm" ',
			'type="text" value="" ' + label_placeholder,
			'onkeydown="' + this.name + '.validateLabel(\'' + this.id + '\');" ',
			'onkeyup="' + this.name + '.validateLabel(\'' + this.id + '\');" ',
			'/>',
			'</div>',
			'<div class="well well-sm small">',
			'<form class="form-horizontal">',
			'<div class="form-group">',
				'<label for="label-prefix" class="col-sm-5 control-label">ID Part</label>',
				'<div class="col-sm-5">',
				'<input id="label-id-part" class="form-control input-sm" ',
				'type="text" value="" ' + id_part_placeholder,
				//'onkeydown="' + this.name + '.composeLabel(\'' + this.id + '\');" ',
				'onkeyup="' + this.name + '.composeLabel(\'' + this.id + '\');" ',
				'/>',
				'</div>',
			'</div>',
			'<div class="form-group">',
				'<label for="label-prefix" class="col-sm-5 control-label">Label Prefix</label>',
				'<div class="col-sm-5">',
				'<input id="label-prefix" class="form-control input-sm" ',
				'type="text" value="' + this.label_prefix + '" ' + prefix_placeholder,
				'onkeydown="' + this.name + '.composeLabel(\'' + this.id + '\');" ',
				'onkeyup="' + this.name + '.composeLabel(\'' + this.id + '\');" ',
				'/>',
				'</div>',
			'</div>',
			'<div class="form-group">',
				'<label for="label-id-len" class="col-sm-5 control-label">ID Digit Length</label>',
				'<div class="col-sm-3">',
				'<input id="label-id-len" class="form-control input-sm" ',
				'type="text" value="' + digit_len_val + '" ',
				'onkeydown="' + this.name + '.composeLabel(\'' + this.id + '\');" ',
				'onkeyup="' + this.name + '.composeLabel(\'' + this.id + '\');" ',
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
			'<div id="v-' + this.id + '">',
			'</div>',
			'<label>Explanatory Note</label><br/>',
			field.note,
		'</td>',
		'</tr>'
		].join("\n");
		return html;
	}
	this.make_category_val_html = function(){
		// makes special HTML for the (class_uri) category field
		this.prep_field_tree(('oc-gen:' + this.item_type), this.id, 'entities');
		var html = [
		'<tr>',
		'<td id="f-bu-' + this.id + '">',
      this.make_field_update_buttom_html(this.id),
		'</td>',
		'<td>',
			'<div class="form-group">',
			'<label for="f-l-' + this.id + '">' + this.label + ' (Label)</label>',
			'<input id="f-l-' + this.id + '" class="form-control input-sm" ',
			'type="text" value="" disabled="disabled"/>',
			'</div>',
			'<div class="form-group">',
			'<label for="f-id-' + this.id + '">' + this.label + ' (ID)</label>',
			'<input id="f-id-' + this.id + '" class="form-control input-sm" ',
			'type="text" value="" />',
			'</div>',
			'<div class="well well-sm small">',
			'<label>',
			'<a title="Click to expand" role="button" ',
			'id="tx-' + this.id + '" ',
			'onclick="'+ this.name + '.toggleCollapseTree(\''+ this.id + '\');">',
			'<span class="glyphicon glyphicon-cloud-download" aria-hidden="true">',
			'</span>',
			'</a>',
			' Select a General Category Below</label><br/>',
			'<div id="tr-' + this.id + '" class="container-fluid collapse in" aria-expanded="true" >', // where the tree will go
			'</div>',
			'</div>',
		'</td>',
		'<td>',
			'<div id="v-' + this.id + '">',
			'</div>',
			'<label>Explanatory Note</label><br/>',
			field.note,
		'</td>',
		'</tr>'
		].join("\n");
		return html;
	}
	this.make_context_val_html = function(){
		// make a tree list for searching for contexts
		this.prep_field_tree(this.project_uuid, this.id, 'context');
		
		// make an entity search for contexts
		var entityInterfaceHTML = "";
		/* changes global authorSearchObj from entities/entities.js */
		
		var entSearchObj = new searchEntityObj();
		var ent_name = 'sobjs';
		entSearchObj.name = ent_name;
		entSearchObj.compact_display = true;
		entSearchObj.parent_obj_name = this.name;
		entSearchObj.entities_panel_title = "Select a Context";
		entSearchObj.limit_item_type = "subjects";
		entSearchObj.limit_project_uuid = "0," + this.project_uuid;
		var entDomID = entSearchObj.make_dom_name_id();
		var afterSelectDone = {
			// done after the selection is done
			sel_id: document.getElementById(entDomID + "-sel-entity-id").value,
			sel_label: document.getElementById(entDomID +  "-sel-entity-label").value,
			field_id: this.id,
			checkFields: this.checkFields, //needed for checking fields
		   data: this.data, //needed for checking fields
			make_validation_html: this.make_validation_html, //needed for checking fields
			exec: function(){
				document.getElementById('f-l-' + this.field_id).value = this.sel_label;
				document.getElementById('f-id-' + this.field_id).value = this.sel_id;
				//now check the fields
				this.checkFields();
			}
		};
		entSearchObj.afterSelectDone = afterSelectDone;
		this.sobjs = entSearchObj;
		var entityInterfaceHTML = entSearchObj.generateEntitiesInterface();
		
		var html = [
		'<tr>',
		'<td id="f-bu-' + this.id + '">',
      this.make_field_update_buttom_html(this.id),
		'</td>',
		'<td>',
			'<div class="form-group">',
			'<label for="f-l-' + this.id + '">' + this.label + ' (Label)</label>',
			'<input id="f-l-' + this.id + '" class="form-control input-sm" ',
			'type="text" value="" disabled="disabled"/>',
			'</div>',
			'<div class="form-group">',
			'<label for="f-id-' + this.id + '">' + this.label + ' (ID)</label>',
			'<input id="f-id-' + this.id + '" class="form-control input-sm" ',
			'type="text" value="" />',
			'</div>',
			'<div class="well well-sm small">',
			'<label>',
			'<a title="Click to expand" role="button" ',
			'id="tx-' + this.id + '" ',
			'onclick="'+ this.name + '.toggleCollapseTree(\''+ this.id + '\');">',
			'<span class="glyphicon glyphicon-cloud-download" aria-hidden="true">',
			'</span>',
			'</a>',
			' Select a Context Below</label><br/>',
			'<div id="tr-' + this.id + '" class="container-fluid collapse in" aria-expanded="true">', // where the tree will go
			'</div>',
			'</div>',
		'</td>',
		'<td>',
			'<div id="v-' + this.id + '">',
			'</div>',
			'<label>Explanatory Note</label><br/>',
			field.note,
			entityInterfaceHTML,
		'</td>',
		'</tr>'
		].join("\n");
		return html;
	}
	this.make_note_val_html = function(){
		var html = [
		'<tr>',
		'<td id="f-bu-' + this.id + '">',
      this.make_field_update_buttom_html(this.id),
		'</td>',
		'<td>',
			'<div class="form-group">',
			'<label for="f-' + this.id + '">Note</label>',
			'<textarea id="f-' + this.id + '" class="form-control input-sm" rows="3">',
			'</textarea>',
			'</div>',
		'</td>',
		'<td>',
			'<div id="v-' + this.id + '">',
			'</div>',
			'<label>Explanatory Note</label><br/>',
			field.note,
		'</td>',
		'</tr>'
		].join("\n");
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
			var label_id = ' id="' + dom_ids.label + '" ';
			var id_id = ' id="' + dom_ids.id + '" ';
		}
		else{
			var label_id = '';
			var id_id = '';
		}
		var html = [
			'<p ' + label_id + '>',
			label,
			'</p>',
			'<samp class="uri-id small">',
			'<a href="' + this.make_url('/edit/items/' + uuid) + '" target="_blank">',
			'<div ' + id_id + '>' + uuid + '</div> ',
			'<span class="glyphicon glyphicon-new-window"></span>',
			'</a>',
			'</samp>'
		].join("\n");
		return html;
	}
	this.make_field_val_domids = function(value_num){
		// makes dom ids for values
		var dom_ids = {
			literal: (value_num + '-field-' + this.id),
			label: (value_num + '-field-l-' + this.id),
			id: (value_num + '-field-id-' + this.id),
			valid: (value_num + '-field-valid-' + this.id),
			icon: (value_num + '-field-icon-' + this.id),
			datecon: (value_num + '-field-datecon-' + this.id),
			treebut: (value_num + '-field-tx-' + this.id),
			tree: (value_num + '-field-tr-' + this.id),
			newrec: (value_num + '-field-new-' + this.id),
			focal: (value_num + '-field-fcl-' + this.id)
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
	
	/*
	 * VALIDATION FUNCTIONS
	 */
	this.validateNumber = function(literal_id){
		//validates numeric fields
		var is_valid = false;
		var check_val = document.getElementById(literal_id).value;
		var value_num = this.value_num_from_domid(literal_id);
		if (isNaN(check_val)){
			// not a number returned true
			var val_mes = 'Not a numeric ' + this.get_human_readable_data_type(this.data_type) + ' value.';
			this.make_validation_html(val_mes, false, value_num);
		}
		else{
			// numeric result detected, now make sure it fits the specific datatype
			if (data_type == 'xsd:double') {
				check_val = parseFloat(check_val);
				if (this.isFloat(check_val)) {
					is_valid = true;
					var val_mes = 'Valid ' + this.get_human_readable_data_type(data_type) + ' value.';
					this.make_validation_html(val_mes, true, value_num);
				}
				else{
					var val_mes = 'Not a valid ' + this.get_human_readable_data_type(data_type) + ' value.';
					this.make_validation_html(val_mes, false, value_num);
				}
			}
			if (data_type == 'xsd:integer') {
				var check_val = parseFloat(check_val);
				if (this.isInt(check_val)) {
					is_valid = true;
					var val_mes = 'Valid ' + this.get_human_readable_data_type(data_type) + ' value.';
					this.make_validation_html(val_mes, true, value_num);
				}
				else{
					var val_mes = 'Not a valid ' + this.get_human_readable_data_type(data_type) + ' value.';
					this.make_validation_html(val_mes, false, value_num);
				}
			}	
		}
		return is_valid;
	}
	this.validateDate = function(literal_id){
		// validates date fields to a yyyy-mm-dd format
		var str = document.getElementById(literal_id).value;
		var value_num = this.value_num_from_domid(literal_id);
	   var valid_date = this.isValidDate(str);
		if (valid_date) {
			var val_mes = 'Valid calendar date value.';
			this.make_validation_html(val_mes, true, value_num);
		}
		else{
			var val_mes = 'Not a valid calendar date (yyyy-mm-dd) value.';
			this.make_validation_html(val_mes, false, value_num);
		}
		return valid_date;
	}
	this.validateBoolean = function(literal_id){
		// validates date fields to a yyyy-mm-dd format
		var str = document.getElementById(literal_id).value.toLowerCase();
		var value_num = this.value_num_from_domid(literal_id);
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
		return boolean_ok;
	}
	this.parseStrBoolean = function(check_str){
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
		return truth-val;
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
		if (is_valid) {
			var icon_html = '<span class="glyphicon glyphicon-ok-circle" aria-hidden="true"></span>';
			var alert_class = "alert alert-success";
		}
		else{
			var icon_html = '<span class="glyphicon glyphicon-warning-sign" aria-hidden="true"></span>';
			var alert_class = this.invalid_alert_class;
		}
	
		var alert_html = [
				'<div role="alert" class="' + alert_class + '" style="margin-top: 3px;">',
					icon_html,
					message_html,
				'</div>'
			].join('\n');
		
		if (value_num != false) {
			//add this to the dom
			var dom_ids = this.make_field_val_domids(value_num);
			var act_dom = document.getElementById(dom_ids.valid);
			act_dom.innerHTML = alert_html;
		}
		return alert_html;
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
		var value_num = this.value_num_from_domid(tree_dom_id);
		var dom_ids = this.make_field_val_domids(value_num);
		document.getElementById(dom_ids.label).value = label.trim();
		document.getElementById(dom_ids.id).value = id.trim();
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
		console.log(hierarchy_objs);
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
	
	
	
	
	
	
	/*  Post-processing funcitons executed
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
