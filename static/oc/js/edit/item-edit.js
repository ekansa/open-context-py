/*
 * Functions to edit an item
 */
function itemEdit(item_type, item_uuid){
	this.super_user = false;
	this.project_uuid = project_uuid;
	this.item_uuid = item_uuid;
	this.item_alt_id = false;  // an alternative identifier
	this.item_type = item_type;
	this.label_field = false; // the field object for the item label
	this.class_field = false; // the field object for the item class
	this.context_field = false; // the field object for the item context
	this.fields = [];  // list of field objects for other descriptive fields (in the item observations)
	this.multilingual = {}; // objects for creating, editing, validating multilingual texts.
	this.obj_name = 'edit_item';
	this.panels = [];
	this.obs_fields = {};
	this.observations = {};
	this.searchObject = false;
	this.active_search_entity = false;
	this.active_obs_num = false;
	this.class_item_types = ['subjects', 'media'];
	this.label_note = [
		"A label is the primary name used for people to identify an item. ",
		"This differs from an item's UUID and URI, both of which are ",
		"universally unique identifiers used by software. ",
		"Changing an item's label does not change the item's UUID or URI, ",
		"nor does it change an item's relationships with other items."
		].join('\n');
	this.class_note = [
		"General categories help organize data and media for easier ",
		"search and browsing.",
	].join('/n');
	this.edit_status_levels = {
		'0': {icon: '&#9675;&#9675;&#9675;&#9675;&#9675;',
			  text: 'In preparation, draft-stage'},
		'1': {icon: '&#9679;&#9675;&#9675;&#9675;&#9675;',
		      text: 'Demonstration, Minimal editorial acceptance'},
		'2': {icon: '&#9679;&#9679;&#9675;&#9675;&#9675;',
		      text: 'Minimal editorial acceptance'},
		'3': {icon: '&#9679;&#9679;&#9679;&#9675;&#9675;',
		      text: 'Managing editor reviewed'},
		'4': {icon: '&#9679;&#9679;&#9679;&#9679;&#9675;',
		      text: 'Editorial board reviewed'},
		'5': {icon: '&#9679;&#9679;&#9679;&#9679;&#9679;',
		      text: 'Peer-reviewed'}
	};
	this.parent_proj_search = false;
	this.getItemJSON = function(){
		/* gets the item JSON-LD from the server */
		this.item_json_ld_obj = new item_object(this.item_type, this.item_uuid);
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
		this.show_existing_data();
		// console.log(this.fields);
	}
	this.show_existing_data = function(){
		if (this.item_json_ld_obj != false) {
			if (this.item_json_ld_obj.data != false) {
				// show link to the public presentation view
				this.show_public_display_link();
				// get and prepare basic fields
				this.prepare_basics();
				this.show_basic_fields();
				//get observation data
				this.prepare_fields();
				this.show_observation_data();
				this.fields_postprocess();
				if (typeof edit_geoevents !=  "undefined") {
					// prep geospatial interface if interface object exists
					edit_geoevents.show_existing_data()
				}
				if (this.item_type == 'predicates') {
					// display predicate specifics
					this.display_predicate_edits();
				}
				if (this.item_type == 'types') {
					// display person specifics
					this.display_type_edits();
				}
				if (this.item_type == 'media') {
					// display media specifics
					this.display_media_edits();
				}
				if (this.item_type == 'documents') {
					// display document specifics
					this.display_document_edits();
				}
				if (this.item_type == 'projects') {
					// display project specifics
					this.display_project_edits();
				}
				if (this.item_type == 'persons') {
					// display person specifics
					this.display_person_edits();
				}
				if (this.item_type == 'tables') {
					// display table specifics
					if (this.item_json_ld_obj.data.hasOwnProperty('dc-terms:identifier')) {
						// the table's alternative identifier
						this.item_alt_id = this.item_json_ld_obj.data['dc-terms:identifier'];
					}
					this.display_table_edits();
				}
			}
		}
	}
	this.show_basic_fields = function(){
		
		// all items have labels, so put the label edit here
		var label_field_html = this.label_field.make_basic_edit_field_html();
		document.getElementById('edit-item-label-field').innerHTML = label_field_html;
		
		// only certain items have classes so put it here
		if (this.class_field != false) {
			var class_field_html = this.class_field.make_basic_edit_field_html();
			document.getElementById('edit-item-class-field').innerHTML = class_field_html;
		}
		
		if (this.context_field != false) {
			// we've got a context field!
			var context_field_html = this.context_field.make_basic_edit_field_html();
			document.getElementById('edit-item-context').innerHTML = context_field_html;
		}
		
	}
	this.show_public_display_link = function(){
		var url = this.make_url("/" + this.item_type + "/" + encodeURIComponent(this.item_json_ld_obj.uuid));
		var html = [
			'<div style="margin-top: 5px; font-size:150%;">',
				'<a href="' + url + '" title="Go to presentation view">',
				'<span class="glyphicon glyphicon-globe"></span> ',
				'</a>',
			'</div>'
		].join('\n');
		if (document.getElementById('edit-item-public-view')) {
			document.getElementById('edit-item-public-view').innerHTML = html;
		}
	}
	this.show_observation_data = function(){
		// first get information on the predicates from the JSON-LD context
		console.log(this.fields);
		//this.item_json_ld_obj.getPredicates();
		var observations = this.item_json_ld_obj.getObservations();
		var number_obs = observations.length;
		if (number_obs < 1) {
			number_obs = 1;
			this.observations[1] = {id: 1};
		}
		var obs_html_list = [];
		for (var raw_obs_num = 0; raw_obs_num < number_obs; raw_obs_num++) {
			var obs_num = raw_obs_num + 1;
			var obs = this.observations[obs_num];
			var dom_ids = this.make_obs_dom_ids(obs_num);
			var fields_html = [
				'<table class="table table-condensed table-hover table-striped">',
					'<thead>',
					   '<tr>',
						  '<th class="col-sm-1">Options</th>',
						  '<th class="col-sm-1">Sort</th>',
						  '<th class="col-sm-2">Property</th>',
						  '<th class="col-sm-8">Values</th>',
					   '</tr>',
					'</thead>',
					'<tbody id="' + dom_ids.fields + '">',
						this.make_obs_fields_html(obs_num),
					'</tbody>',
				'</table>',
				this.make_add_buttons(obs_num),
			].join("\n");
			
			if (fields_html.length > 10) {
				if (number_obs > 1) {
					// we have multiple observations, so put them into collapsable panels
					var panel_num = this.panels.length;
					var obs_panel = new panel(panel_num);
					if (obs.hasOwnProperty('label')) {
						obs_panel.title_html = obs.label;
					}
					else{
						obs_panel.title_html = obs.id;
						if (obs.id == '#obs-1') {
							//first observation, the main description
							obs_panel.title_html = 'Main Description';
						}
					}
					
					obs_panel.body_html = fields_html;
					var observation_html = obs_panel.make_html();
					obs_html_list.push(observation_html);
				}
				else{
					obs_html_list.push(fields_html);
				}
			}// end case with an observation with data
		}//end loop through observations
		if (obs_html_list.length > 0) {
			// we have observation data, now fix to the appropriate dom element.
			document.getElementById('obs-descriptions').innerHTML = obs_html_list.join("\n");
		}
	}//end function for observation data
	this.make_obs_fields_html = function(obs_num){
		//returns HTML for fields in an observation
		var row_list = [];
		for (var i = 0, length = this.fields.length; i < length; i++) {
			var field = this.fields[i];
			if (field.obs_num == obs_num) {
				// add fields to the currect obs
				var field_html = [
					'<tr>',
					'<td>',
					this.make_field_more_options_button_html(field.id),
					'</td>',
					'<td>',
					this.make_field_sort_button_html(field.id, -1),
					this.make_field_sort_button_html(field.id, 1),
					'</td>',
					field.make_field_html(),
					'</tr>'
				].join("\n");
				row_list.push(field_html);
			}
		}
		var html = row_list.join('\n');
		return html;
	}
	this.make_obs_dom_ids = function(obs_num){
		var dom_ids = {
			fields: (obs_num + '-obs-fields'),
		};
		return dom_ids;
	}
	this.make_add_buttons = function(obs_num){
		var dom_ids = this.make_obs_dom_ids(obs_num);
		var html = [
			'<div class="row">',
			'<div class="col-xs-6">',
			'<button title="Add another descriptive property to this observation" ',
			'class="btn btn-default" ',
			'onclick="' + this.obj_name + '.showAddPredicate(\'' + obs_num + '\');">',
			'<span class="glyphicon glyphicon-stats"></span> Describe with another Property',
			'</button>',
			'</div>',
			'<div class="col-xs-6">',
			'<button title="Add another observation (group of descriptions)" ',
			'class="btn btn-default" ',
			'onclick="' + this.obj_name + '.showAddObservation(\'' + obs_num + '\');">',
			'<span class="glyphicon glyphicon-eye-open"></span> Add new observation',
			'</button>',
			'</div>',
			'</div>',
		].join("\n");
		return html;
	}
	this.showAddPredicate = function(obs_num){
		this.active_search_entity = false;
		var title = 'Add Descriptive Property to Observation: ' + obs_num;
		var obs_name = 'Observation [' + obs_num + ']';
		if (obs_num in this.observations) {
			var obs = this.observations[obs_num];
			if (obs.hasOwnProperty('label')) {
				var obs_name = obs.label + ' [' + obs_num + ']';;
				var title = 'Add Descriptive Property to Observation <em>' + obs.label + '</em>';
			}
		}
		
		var entSearchObj = new searchEntityObj();
		var ent_name = 'searchObject';
		entSearchObj.name = ent_name;
		entSearchObj.compact_display = true;
		entSearchObj.parent_obj_name = this.obj_name;
		entSearchObj.entities_panel_title = "Search for a Predicate to Add";
		entSearchObj.limit_item_type = 'predicates';
		entSearchObj.limit_project_uuid = "0," + this.project_uuid;
		var entDomID = entSearchObj.make_dom_name_id();
		var afterSelectDone = {
			entDomID: entDomID,
			parent: this,
			obs_num: obs_num,
			obj_name: this.obj_name,
			make_add_field_button: this.make_add_field_button,
			exec: function(){
				this.parent.active_search_entity = this.selected_entity;
				var sel_id = document.getElementById(this.entDomID + "-sel-entity-id").value;
				var sel_label = document.getElementById(this.entDomID +  "-sel-entity-label").value;
				document.getElementById("act-label").value = sel_label;
				document.getElementById("act-id").value = sel_id;
				if (this.selected_entity.hasOwnProperty('data_type')) {
					var data_type = this.selected_entity.data_type;
					var fobj = new edit_field();
					var human_data_type = fobj.get_human_readable_data_type(data_type);
					document.getElementById("act-data-type").value = human_data_type;
				}
				this.parent.make_add_field_button(this.obs_num);
			}
		};
		entSearchObj.afterSelectDone = afterSelectDone;
		var entityInterfaceHTML = entSearchObj.generateEntitiesInterface();
		this.searchObject = entSearchObj;
		
		var body_html = [
			'<div>',
				'<div class="row">',
					'<div class="col-xs-6">',
						'<div class="form-group">',
						'<label for="act-label">Label of Property to Add</label>',
						'<input id="act-label" class="form-control input-sm" ',
						'type="text" value="" disabled="disabled"/>',
						'</div>',
						'<div class="form-group">',
						'<label for="act-data-type">Data-Type of Property to Add</label>',
						'<input id="act-data-type" class="form-control input-sm" ',
						'type="text" value="" disabled="disabled"/>',
						'</div>',
						'<div class="form-group">',
						'<label for="act-id">ID of Property to Add</label>',
						'<input id="act-id" class="form-control input-sm" ',
						'onchange="' + this.obj_name + '.getActiveSeachEntity(\'act-id\', \'' + obs_num + '\');" ',
						'type="text" value="" />',
						'</div>',
					'</div>',
					'<div class="col-xs-6">',
						entityInterfaceHTML,
					'</div>',
				'</div>',
				'<div class="row">',
					'<div class="col-xs-6" id="act-button">',
						'<label>Add Note (Below), or Search Fields (Right):</label>',
						'<br/>',
						'<button type="button" class="btn btn-default" aria-label="Left Align" ',
						' onclick="' + this.obj_name + '.addNoteField(\'' + obs_num + '\')" >',
						'<span class="glyphicon glyphicon-pencil" aria-hidden="true"></span>',
						' Add a Note',
						'</button>',
					'</div>',
					'<div class="col-xs-6">',
					'<p><small>',
					'Use this interface to add a descriptive property (predicate) to ' + obs_name,
					' of this item. The property will only be saved after you have added a value to it.',
					'</small></p>',
					'</div>',
				'</div>',
			'</div>',
		].join('\n');
		var main_modal_title_domID = "myModalLabel";
		var main_modal_body_domID = "myModalBody";
		var title_dom = document.getElementById(main_modal_title_domID);
		var body_dom = document.getElementById(main_modal_body_domID);
		title_dom.innerHTML = title;
		body_dom.innerHTML = body_html;
		$("#myModal").modal('show');
	}
	this.addNoteField = function(obs_num){
		var note_pred ={
			label: 'Note',
			data_type: 'xsd:string',
			uuid: 'oc-gen:has-note',
			class_uri: 'variable'
		}
		if (document.getElementById('act-label')) {
			document.getElementById('act-label').value = note_pred.label;
		}
		if (document.getElementById('act-data-type')) {
			document.getElementById('act-data-type').value = note_pred.data_type;
		}
		if (document.getElementById('act-id')) {
			document.getElementById('act-id').value = note_pred.uuid;
		}
		this.addField_exec(obs_num,
						   note_pred.uuid,
						   note_pred.label,
						   note_pred.class_uri,
						   note_pred.data_type);
		$("#myModal").modal('hide');
	}
	this.make_add_field_button = function(obs_num){
		if (this.active_search_entity != false) {
			if (document.getElementById('act-button')) {
				var html = [
					'<button title="Add this property" ',
					'class="btn btn-primary" ',
					'onclick="' + this.obj_name + '.addField(\'' + obs_num + '\');">',
					'<span class="glyphicon glyphicon-plus-sign"></span> Submit',
					'</button>',
				].join('\n');
				document.getElementById('act-button').innerHTML = html;
			}
		}
	}
	this.addField = function(obs_num){
		if (this.active_search_entity != false) {
			// we have a search entity to use
			var predicate_uuid = false;
			if (this.active_search_entity.hasOwnProperty('uuid')) {
				var predicate_uuid = this.active_search_entity.uuid;
			}
			else if (this.active_search_entity.hasOwnProperty('id')) {
				var predicate_uuid = this.active_search_entity.id;
			}
			else{
				
			}
			this.addField_exec(obs_num,
							   predicate_uuid,
							   this.active_search_entity.label,
							   this.active_search_entity.class_uri,
							   this.active_search_entity.data_type);
			//now hide the modal interface
			$("#myModal").modal('hide');
		}	
		else{
			alert('no active field');
		}
	}
	this.addField_exec = function(obs_num, predicate_uuid, label, class_uri, data_type){
		var dom_ids = this.make_obs_dom_ids(obs_num);
		var obs = this.observations[obs_num];
		var field = new edit_field();
		field.id = this.fields.length;
		field.project_uuid = this.project_uuid;
		field.pred_type = class_uri;
		field.parent_obj_name = this.obj_name;
		field.obj_name = 'fields[' + field.id + ']';
		field.add_new_data_row = true;
		field.edit_new = false;
		field.edit_uuid = this.item_uuid;
		field.item_type = this.item_type;
		field.label = label;
		field.predicate_uuid = predicate_uuid;
		field.draft_sort = this.fields.length + 1;
		field.obs_num = obs_num;
		field.obs_node = obs['id'];
		field.data_type = data_type;
		field.values_obj = [];
		field.initialize();
		this.fields.push(field);
		if (document.getElementById(dom_ids.fields)) {
			var obs_field_dom = document.getElementById(dom_ids.fields);
			var obs_field_html = obs_field_dom.innerHTML;
			var field_html = [
				'<tr>',
				'<td>',
				this.make_field_more_options_button_html(field.id),
				'</td>',
				'<td>',
				this.make_field_sort_button_html(field.id, -1),
				this.make_field_sort_button_html(field.id, 1),
				'</td>',
				field.make_field_html(),
				'</tr>'
			].join("\n");
			obs_field_html += field_html;
			obs_field_dom.innerHTML = obs_field_html;
			field.postprocess();
		}
	}
	this.make_field_sort_button_html = function(field_id, sort_change){
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
			'onclick="' + this.obj_name + '.rankField(\'' + field_id + '\', ' + sort_change + ');">',
			icon,
			'</button>',
			'</div>',
			].join('\n');
		return button_html;
	}
	this.make_field_more_options_button_html = function(field_id){
		var title = 'More options for this field';
		var style = 'style="margin-top:10px;"';
		var icon =  '<span class="glyphicon glyphicon-wrench"></span>';
		var button_html = [
			'<div ' + style + ' >',
			'<button title="' + title + '" ',
			'class="btn btn btn-default btn-xs" ',
			'onclick="' + this.obj_name + '.moreOptions(\'' + field_id + '\');">',
			icon,
			'</button>',
			'</div>',
			].join('\n');
		return button_html;
	}
	this.moreOptions = function(field_id){
		return field_id;
	}
	this.prepare_basics = function(){
		// prepare the label field
		var field = new edit_field();
		field.id = 10000;
		field.project_uuid = this.project_uuid;
		field.parent_obj_name = this.obj_name;
		field.obj_name = 'label_field';
		field.add_new_data_row = false;
		field.edit_new = false;
		field.edit_uuid = this.item_uuid;
		field.item_type = this.item_type;
		field.label = 'Item Label';
		field.item_label = this.item_json_ld_obj.data.label;
		field.item_altlabel = this.item_json_ld_obj.getAltLabel();
		field.predicate_uuid = field.label_pred_uuid;
		field.draft_sort = 10000;
		field.data_type = 'xsd:string';
		field.note = this.label_note;
		field.note_below_pred = true;
		field.values_obj = [
			{}
		];
		field.initialize();
		this.label_field = field;
		if (this.class_item_types.indexOf(this.item_type) >= 0) {
			// we have an item type that needs to have a class
			var cats = this.item_json_ld_obj.getItemCategories();
			var field = new edit_field();
			field.id = 20000;
			field.project_uuid = this.project_uuid;
			field.parent_obj_name = this.obj_name;
			field.obj_name = 'class_field';
			field.add_new_data_row = false;
			field.edit_new = false;
			field.edit_uuid = this.item_uuid;
			field.item_type = this.item_type;
			field.label = 'Item Category';
			field.item_label = this.item_json_ld_obj.data.label;
			field.class_uri = cats[0].id;
			field.class_label = cats[0].label;
			field.predicate_uuid = field.class_pred_uuid;
			field.draft_sort = 10000;
			field.data_type = 'id';
			field.values_obj = cats;
			field.note = this.class_note;
			field.initialize();
			this.class_field = field;
		}
		if (this.item_type == 'subjects') {
			// we have a subjects item, so get spatial context
			var context = this.item_json_ld_obj.getParent();
			var field = new edit_field();
			field.id = 30000;
			field.project_uuid = this.project_uuid;
			field.parent_obj_name = this.obj_name;
			field.obj_name = 'context_field';
			field.add_new_data_row = false;
			field.edit_new = false;
			field.edit_uuid = this.item_uuid;
			field.item_type = this.item_type;
			field.label = 'Item Context';
			field.item_label = this.item_json_ld_obj.data.label;
			field.predicate_uuid = field.context_pred_uuid;
			field.context_label = context.label;
			field.context_uuid = context.uuid;
			field.draft_sort = 10000;
			field.data_type = 'id';
			field.values_obj = [
				context
			];
			field.initialize();
			this.context_field = field;
		}
	}
	this.prepare_fields = function(){
		//prepares fields of observation data
		this.fields = [];
		this.item_json_ld_obj.getPredicates();
		var observations = this.item_json_ld_obj.getObservations();
		var number_obs = observations.length;
		for (var raw_obs_num = 0; raw_obs_num < number_obs; raw_obs_num++) {
			var obs_num = raw_obs_num + 1;
			var obs = observations[raw_obs_num];
			this.observations[obs_num] = obs;
			for (var predicate_uuid in this.item_json_ld_obj.predicates_by_uuid) {
				var pred_item = this.item_json_ld_obj.predicates_by_uuid[predicate_uuid];
				var values_obj = this.item_json_ld_obj.getObsValuesByPredicateUUID(raw_obs_num, predicate_uuid);
				if (values_obj.length > 0) {
					// this particular observation has a predicate with values
					var field = new edit_field();
					field.id = this.fields.length;
					field.project_uuid = this.project_uuid;
					field.pred_type = pred_item.pred_type;
					field.parent_obj_name = this.obj_name;
					field.obj_name = 'fields[' + field.id + ']';
					field.add_new_data_row = true;
					field.edit_new = false;
					field.edit_uuid = this.item_uuid;
					field.item_type = this.item_type;
					field.label = pred_item.label;
					field.predicate_uuid = predicate_uuid;
					field.draft_sort = this.fields.length + 1;
					field.obs_num = obs_num;
					field.obs_node = obs['id'];
					field.data_type = pred_item.data_type;
					field.values_obj = this.item_json_ld_obj.getValuesByPredicateUUID(predicate_uuid);
					field.initialize();
					this.fields.push(field);
				}
			}
		}
	}
	this.fields_postprocess = function(){
		//set up trees, calendars, etc. all the functions
		//that need to be done after the fields have been added ot the DOM
		for (var i = 0, length = this.fields.length; i < length; i++) {
			var field = this.fields[i];
			if (field.data_type == 'id' && length > 10) {
				// take a break before requesting tree information
				// otherwise the server can get MAD
				setTimeout(function(){
					field.postprocess();
				}, 500);
			}
			else{
				field.postprocess();
			}
			
		}
		// now post-process the basic fields
		this.label_field.postprocess();
		if (this.class_field != false) {
			this.class_field.postprocess();
		}
		if (this.context_field != false) {
			this.context_field.postprocess();
		}
	}
	this.getActiveSeachEntity = function(act_dom_id, obs_num){
		if (this.active_search_entity == false) {
			this.active_obs_num = obs_num;
			if (document.getElementById(act_dom_id)) {
				var identifier = document.getElementById(act_dom_id).value;
				this.ajax_get_active_id(identifier).then(
					function(){
						this.display_active_search_entity_attributes();
						this.make_add_field_button(this.active_obs_num);
					}
				);
			}
		}
	}
	this.display_active_search_entity_attributes = function(){
		if (this.active_search_entity != false) {
			if (this.active_search_entity.hasOwnProperty('label')) {
				document.getElementById("act-label").value = this.active_search_entity.label;
			}
			if (this.active_search_entity.hasOwnProperty('data_type')) {
				var data_type = this.active_search_entity.data_type;
				var fobj = new edit_field();
				var human_data_type = fobj.get_human_readable_data_type(data_type);
				document.getElementById("act-data-type").value = human_data_type;
			}
		}
		return true;
	}
	this.ajax_get_active_id = function(identifier){
		var url = this.make_url("/entities/id-summary/" + encodeURIComponent(identifier));
		return $.ajax({
			type: "GET",
			url: url,
			dataType: "json",
			context: this,
			success: this.ajax_get_active_idDone,
			error: function (request, status, error) {
				alert('Cannot resolve: ' + identifier);
			}
		});
	}
	this.ajax_get_active_idDone = function(data){
		this.active_search_entity = data;
	}
	/**************************************************************
	 * LINKED DATA - ANNOTATIONS RELATED FUNCTIONS
	 *
	 *************************************************************/
	
	
	
	/**************************************************************
	 * PREDICATE RELATED FUNCTIONS
	 *
	 *************************************************************/
	this.display_predicate_edits = function(){
		this.display_predicate_sort();
		this.display_skos_note();	
	}
	this.display_predicate_sort = function(){
		// interface for changing the sort order of a predicate
		// globally for an entire project
		
		if (this.item_json_ld_obj.data.hasOwnProperty('oc-gen:default-sort-order')) {
			var sort_value = this.item_json_ld_obj.data['oc-gen:default-sort-order'];
		}
		else{
			var sort_value = '';
		}
		if (sort_value != '') {
			var placeholder = '';
		}
		else{
			var placeholder = 'placeholder="Sort order for whole project"';
		}
		
		
		var button_html = [
			'<button type="button" ',
			'class="btn btn-primary" ',
			'onclick="' + this.obj_name + '.updatePredicateSort();">',
			'Update',
			'</button>'
		].join('\n');
		
		var html = [
			'<div class="row">',
				'<div class="col-sm-9">',
					'<div class="form-group">',
                        '<label for="pred-sort">Sort Value (Integer)</label>',
                        '<input id="pred-sort" ',
						'class="form-control input-sm" type="text" ',
						'value="' + sort_value + '" ',
						placeholder,
						' />',
                    '</div>', 
				'</div>',
				'<div class="col-sm-3">',
					'<div id="pred-sort-submitcon" style="padding-top: 24px;">',
					button_html,
					'</div>',
					'<div id="pred-sort-respncon" style="padding-top: 10px;">',
					'</div>',
					'<div id="pred-sort-valid">',
					'</div>',
					'<div>',
						'<label>Note</label>',
						'<p class="small">',
						'Changing the sort value changes the order this predicate will ',
						'be displayed when used to describe items. Changes here apply to the entire ',
						'project. If you want to change sort orders for just a single item, ',
						'please edit that item instead. ',
						'</p>',
					'</div>',
				'</div>',
			'</div>'
		].join('\n');
		document.getElementById("edit-pred-sort").innerHTML = html;
	}
	this.updatePredicateSort = function() {
		/* updates the skos-note for the item
		*/
		var act_domID = "pred-sort";
		var sort_value = document.getElementById(act_domID).value;
		var url = this.make_url("/edit/update-predicate-sort-order/") + encodeURIComponent(this.item_uuid);
		var act_icon = document.getElementById('pred-sort');
		act_icon.innerHTML = '';
		var act_note = document.getElementById('pred-sort');
		act_note.innerHTML = 'Uploading and validating...';
		var req = $.ajax({
			type: "POST",
			url: url,
			dataType: "json",
			data: {
				sort_value: sort_value,
				csrfmiddlewaretoken: csrftoken},
			context: this,
			success: this.updatePredicateSortDone,
			error: function (request, status, error) {
				alert('Problem updating predicate sort: ' + status);
			}
		});
	}
	this.updatePredicateSortDone = function(data){
		// handles response of predicate sorting update
		var act_icon = document.getElementById('pred-sort-respncon');
		act_icon.innerHTML = '';
		var act_note = document.getElementById('pred-sort-valid');
		act_note.innerHTML = '';
		if (data.ok) {
			this.make_temp_update_note_html('pred-sort-respncon');
		}
	}
	
	/**************************************************************
	 * TYPE RELATED FUNCTIONS
	 *
	 *************************************************************/
	this.display_type_edits = function(){
		this.display_skos_note();	
	}
	
	/**************************************************************
	 * SKOS-NOTE RELATED FUNCTIONS
	 *
	 *************************************************************/
	this.display_skos_note = function(){
		// inferface for editing skos notes for predicates and types
		var act_pred = 'skos:note';
		var skos_note = this.item_json_ld_obj.predGetDefaultString(act_pred);
		if (skos_note == false) {
			var skos_note = '';
		}
		if (skos_note.length > 0) {
			var placeholder = '';
		}
		else{
			var placeholder = 'placeholder="A note defining this concept."';
		}
		
		var button_html = [
			'<button type="button" ',
			'class="btn btn-primary" ',
			'onclick="' + this.obj_name + '.updateSkosNote();">',
			'Update',
			'</button>'
		].join('\n');
		
		var html = [
			'<div class="row">',
				'<div class="col-sm-9">',
					'<div class="form-group">',
                        '<label for="skos-note">',
						'Definition Note (skos:note)</label>',
                        '<textarea id="skos-note" ',
						'class="form-control" rows="24" ',
						placeholder + '>',
						skos_note,
						'</textarea>',
                    '</div>', 
				'</div>',
				'<div class="col-sm-3">',
					'<div id="skos-note-submitcon" style="padding-top: 24px;">',
					button_html,
					'</div>',
					'<div id="skos-note-respncon" style="padding-top: 10px;">',
					'</div>',
					'<div id="skos-note-valid">',
					'</div>',
					this.make_localize_row_html(act_pred, 'content', 'Definition or Note (skos:note)'),
					'<div>',
						'<label>Note</label>',
						'<p class="small">',
						'An note should use HMTL tags for formatting, including images, ',
						'hyperlinks, and may even include some javascript for dynamic ',
						'interactions. The content of the note should include ',
						'information needed to understand and reuse this concept. ',
						'</p>',
						'<p class="small">',
						'The note should validate as HTML. Upon submission or update, Open ',
						'Context will check and validate the HTML. It will accept bad HTML, but bad ',
						'HTML may cause severe formatting or other problems. Please use the W3C ',
						'HTML <a href="https://validator.w3.org/" targer="_blank">validation services</a> ',
						'to help debug your HTML.',
						'</p>',
					'</div>',
				'</div>',
			'</div>'
		].join('\n');
		document.getElementById("edit-skos-note").innerHTML = html;
		
	}
	this.updateSkosNote = function() {
		/* updates the skos-note for the item
		*/
		var act_domID = "skos-note";
		var content = document.getElementById(act_domID).value;
		var url = this.make_url("/edit/update-item-basics/") + encodeURIComponent(this.item_uuid);
		var act_icon = document.getElementById('skos-note-respncon');
		act_icon.innerHTML = '';
		var act_note = document.getElementById('skos-note-valid');
		act_note.innerHTML = 'Uploading and validating...';
		var req = $.ajax({
			type: "POST",
			url: url,
			dataType: "json",
			data: {
				content: content,
				content_type: 'content',
				csrfmiddlewaretoken: csrftoken},
			context: this,
			success: this.updateSkosNoteDone,
			error: function (request, status, error) {
				alert('Problem updating the skos-note: ' + status);
			}
		});
	}
	this.updateSkosNoteDone = function(data){
		// handles successful result of skos-note updates
		var act_icon = document.getElementById('skos-note-respncon');
		act_icon.innerHTML = '';
		var act_note = document.getElementById('skos-note-valid');
		act_note.innerHTML = '';
		if (data.ok) {
			this.make_temp_update_note_html('skos-note-respncon');
		}
		this.make_html_valid_note_html(data, 'skos-note-valid');
	}
	
	
	/**************************************************************
	 * MEDIA RELATED FUNCTIONS
	 *
	 *************************************************************/
	this.display_media_edits = function(){
		//displays project edit fields
		var file_list = this.item_json_ld_obj.getMediaFiles();
		this.display_media_files(file_list, false);
	}
	this.display_media_files = function(file_list, list_note){
		var empty_obj = {'id': '',
						 'type': false,
		                 'dcat:size': 0,
						 'type': false,
						 'dc-terms:hasFormat': ''};
		var thumb_obj = {'id': '',
						 'type': false,
		                 'dcat:size': 0,
						 'type': 'oc-gen:thumbnail',
						 'dc-terms:hasFormat': ''};
		var preview_obj = {'id': '',
						 'type': false,
		                 'dcat:size': 0,
						 'type': 'oc-gen:preview',
						 'dc-terms:hasFormat': ''};
		var full_obj = {'id': '',
						 'type': false,
		                 'dcat:size': 0,
						 'type': 'oc-gen:fullfile',
						 'dc-terms:hasFormat': ''};
		
		if (file_list != false) {
			// found media files, update the empty objects
			// with data about the appropriate file of a given type
			for (var i = 0, length = file_list.length; i < length; i++) {
				var f_obj = file_list[i];
				if (f_obj['type'] == 'oc-gen:thumbnail') {
					thumb_obj = f_obj;
				}
				if (f_obj['type'] == 'oc-gen:preview') {
					preview_obj = f_obj;
				}
				if (f_obj['type'] == 'oc-gen:fullfile') {
					full_obj = f_obj;
				}
			}
		}
		// now we've got file data and or empty
		// data for each file type
		var display_files = [thumb_obj,
							 preview_obj,
							 full_obj];
		var html_list = [
			'<table class="table table-bordered">',
				'<thead>',
					'<tr>',
						'<th class="col-xs-2">',
							'File Type',
						'</th>',
						'<th class="col-xs-6">',
							'File URI',
						'</th>',
						'<th class="col-xs-2">',
							'Size',
						'</th>',
						'<th class="col-xs-2">',
							'Update',
						'</th>',
					'</tr>',
				'</thead>',
				'<tbody>',
		];
		for (var i = 0, length = display_files.length; i < length; i++) {
			var f_obj = display_files[i];
			var button_html = [
				'<button type="button" ',
				'class="btn btn-primary" ',
				'onclick="' + this.obj_name + '.updateMediaFile(' + i + ', \'' + f_obj['type'] + '\');">',
				'Update',
				'</button>'
			].join('\n');
			if (f_obj['id'] == '') {
				var placeholder = ' placeholder="Web URI / URL to the file" ';
			}
			else{
				var placeholder = '';
			}
			if (f_obj['dcat:size'] < 1) {
				var size_class = 'warning';
				var size_html = [
					'<span class="glyphicon glyphicon-alert" aria-hidden="true"></span>',
					'Bad Link',
				].join('\n');
			}
			else{
				var size_class = 'success';
				var size_html = f_obj['dcat:size'];
			}
			var row =[
				'<tr>',
					'<td>',
						f_obj['type'],
					'</td>',
					'<td>',
						'<input id="media-file-uri-' + i + '" ',
						'class="form-control input-sm" type="text" ',
						'value="' + f_obj['id'] + '" ' + placeholder,
						' />',
					'</td>',
					'<td class="small ' + size_class + '">',
						size_html,
					'</td>',
					'<td>',
						'<div id="media-file-uri-submitcon-' + i + '">',
						button_html,
						'</div>',
					'</td>',
				'</tr>'
			].join('\n');
			html_list.push(row);
		}// end loop through display files
		
		html_list.push('</tbody>');
		html_list.push('</table>');
		if (list_note == false) {
			var note = '<div class="well well-sm">';
			note += '<label>Note</label>';
			note += '<p class="small">Provide a Web link to the file of the appropriate type ';
			note += '(thumbnail, preview, full) for this media item.';
			note += '</p>';
			note += '</div>';
		}
		else{
			var note = '<div class="alert alert-warning" role="alert">';
			note += '<label>Note</label>';
			note += list_note;
			note += '</div>';
		}
		html_list.push(note);
		var html = html_list.join('\n');
		document.getElementById("edit-media-files").innerHTML = html;
	}
	this.updateMediaFile = function(i, file_type){
		var act_domID = "media-file-uri-" + i;
		var file_uri = document.getElementById(act_domID).value;
		var but_cont_domID = "media-file-uri-submitcon-" + i;
		document.getElementById(but_cont_domID).innerHTML = 'Updating...';
		var url = this.make_url("/edit/update-media-file/") + encodeURIComponent(this.item_uuid);
		var req = $.ajax({
			type: "POST",
			url: url,
			dataType: "json",
			data: {
				file_type: file_type,
				file_uri: file_uri,
				source_id: 'web-form',
				csrfmiddlewaretoken: csrftoken},
			context: this,
			success: this.updateMediaFileDone,
			error: function (request, status, error) {
				alert('Problem updating the media file: ' + status);
			}
		});
	}
	this.updateMediaFileDone = function(data){
		// handle respones to updating media files.
		if (data.ok) {
			var list_note = false;
		}
		else{
			var list_note = data['change']['note'];
		}
		this.display_media_files(data.file_list, list_note);
	}
	
	/**************************************************************
	 * PROJECT RELATED FUNCTIONS
	 *
	 *************************************************************/
	this.display_project_edits = function(){
		//displays project edit fields
		this.display_proj_short_des();	
		this.display_proj_abstract();
		this.display_proj_hero_images();
		this.display_proj_edit_status();
		this.display_proj_parent();
	}
	this.display_proj_short_des = function(){
		// inferface for editing short project description
		var act_pred = 'description';
		var placeholder = '';
		var short_des = this.item_json_ld_obj.predGetDefaultString(act_pred);
		if (short_des == false) {
			var short_des = '';
			var placeholder = 'placeholder="Short Tweet length description"';
		}
		var button_html = [
			'<button type="button" ',
			'class="btn btn-primary" ',
			'onclick="' + this.obj_name + '.updateShortDes();">',
			'Update',
			'</button>'
		].join('\n');
		
		var html = [
			'<div class="row">',
				'<div class="col-sm-6">',
					'<div class="form-group">',
                        '<label for="proj-short-des">',
						'Short Description / Summary</label>',
                        '<textarea id="proj-short-des" ',
						'class="form-control" rows="3" ',
						placeholder + '>',
						short_des,
						'</textarea>',
                    '</div>', 
				'</div>',
				'<div class="col-sm-3">',
					'<div id="proj-short-des-submitcon" style="padding-top: 24px;">',
					button_html,
					'</div>',
					'<div id="proj-short-des-respncon" style="padding-top: 10px;">',
					'</div>',
					'<div id="proj-short-des-valid">',
					'</div>',
					this.make_localize_row_html(act_pred, 'short_des', 'Short Description'),
				'</div>',
				'<div class="col-sm-3">',
					'<label>Note</label>',
					'<p class="small">',
					'A short "Tweetable" (140 character) or so text description',
					'</p>',
				'</div>',
			'</div>',
		].join('\n');
		document.getElementById("edit-proj-short-des").innerHTML = html;
	}
	
	this.updateShortDes = function() {
		/* updates the short description of a project item
		*/
		var act_domID = "proj-short-des";
		var content = document.getElementById(act_domID).value;
		var url = this.make_url("/edit/update-item-basics/") + encodeURIComponent(this.item_uuid);
		var act_icon = document.getElementById('proj-short-des-respncon');
		act_icon.innerHTML = '';
		var act_note = document.getElementById('proj-short-des-valid');
		act_note.innerHTML = 'Uploading and validating...';
		var req = $.ajax({
			type: "POST",
			url: url,
			dataType: "json",
			data: {
				content: content,
				content_type: 'short_des',
				csrfmiddlewaretoken: csrftoken},
			context: this,
			success: this.updateShortDesDone,
			error: function (request, status, error) {
				alert('Problem updating short description: ' + status);
			}
		});
	}
	this.updateShortDesDone = function(data){
		// handles successful result of short description updates
		var act_icon = document.getElementById('proj-short-des-respncon');
		act_icon.innerHTML = '';
		var act_note = document.getElementById('proj-short-des-valid');
		act_note.innerHTML = '';
		if (data.ok) {
			this.make_temp_update_note_html('proj-short-des-respncon');
		}
		this.make_html_valid_note_html(data, 'proj-short-des-valid');
	}
	
	this.display_proj_abstract = function(){
		// inferface for editing abstract / long project description
		var html = this.make_abstract_edit_html();
		document.getElementById("edit-proj-abstract").innerHTML = html;
	}

	
	
	this.display_proj_hero_images = function(){
		var hero_list = this.item_json_ld_obj.getProjectHeros();
		if (hero_list != false) {
			var file_uri = hero_list[0]['id'];
			var placeholder = '';
		}
		else{
			var file_uri = '';
			var placeholder = 'placeholder="URL to an image file"';
		}
		
		var button_html = [
			'<button type="button" ',
			'class="btn btn-primary" ',
			'onclick="' + this.obj_name + '.updateProjectHero();">',
			'Update',
			'</button>'
		].join('\n');
		
		var html = [
			'<div class="row">',
				'<div class="col-sm-6">',
					'<div class="form-group">',
                        '<label for="proj-hero-uri">Main Project Illustration Image</label>',
                        '<input id="proj-hero-uri" ',
						'class="form-control input-sm" type="text" ',
						'value="' + file_uri + '" ' + placeholder,
						' />',
                    '</div>', 
				'</div>',
				'<div class="col-sm-3">',
					'<div id="proj-hero-uri-submitcon" style="padding-top: 24px;">',
					button_html,
					'</div>',
					'<div id="proj-hero-uri-respncon" style="padding-top: 10px;">',
					'</div>',
					'<div id="proj-hero-uri-valid">',
					'</div>',
				'</div>',
				'<div class="col-sm-3">',
					'<label>Note</label>',
					'<p class="small">',
					'Provide a link to an 1200 pixel wide X 350 pixel high image file. ',
					'This image will serve as the main illustrative image for a project page.',
					'</p>',
				'</div>',
			'</div>'
		].join('\n');
		document.getElementById("edit-proj-hero").innerHTML = html;
	}
	this.updateProjectHero = function() {
		/* updates the short description of a project item
		*/
		var act_domID = "proj-hero-uri";
		var file_uri = document.getElementById(act_domID).value;
		var url = this.make_url("/edit/update-project-hero/") + encodeURIComponent(this.item_uuid);
		var act_icon = document.getElementById('proj-hero-uri-respncon');
		act_icon.innerHTML = '';
		var act_note = document.getElementById('proj-hero-uri-valid');
		act_note.innerHTML = 'Updating project image...';
		var req = $.ajax({
			type: "POST",
			url: url,
			dataType: "json",
			data: {
				file_uri: file_uri,
				source_id: 'web-form',
				content_type: 'content',
				csrfmiddlewaretoken: csrftoken},
			context: this,
			success: this.updateProjectHeroDone,
			error: function (request, status, error) {
				alert('Problem updating the project image: ' + status);
			}
		});
	}
	this.updateProjectHeroDone = function(data){
		// handles successful result of short description updates
		var act_icon = document.getElementById('proj-hero-uri-respncon');
		act_icon.innerHTML = '';
		var act_note = document.getElementById('proj-hero-uri-valid');
		act_note.innerHTML = '';
		if (data.ok) {
			this.make_temp_update_note_html('proj-hero-uri-respncon');
		}
	}
	
	this.display_proj_edit_status = function(){
		if (this.super_user) {
			// only super users can change editorial status
			var button_html = [
				'<button type="button" ',
				'class="btn btn-primary" ',
				'onclick="' + this.obj_name + '.updateEditorialStatus();">',
				'Update',
				'</button>'
			].join('\n');
			
			var status_obj = this.item_json_ld_obj.getEditorialStatus();
			if (status_obj != false) {
				var edit_status = status_obj['edit_status'];
			}
			else{
				var edit_status = '0';	
			}
			var status_html_list = [];
			for (var status_key in this.edit_status_levels) {
				var act_status = this.edit_status_levels[status_key];
				if (status_key == edit_status) {
					var checked = 'checked="checked"';
				}
				else{
					var checked = '';
				}
				var status_html = [
					'<li class="list-group-item">',
					'<div class="row">',
						'<div class="col-sm-1" style="padding-top: 0px; text-align:right;">',
							'<input type="radio" name="edit-status" ',
							'class="proj-edit-status" value="' + status_key + '" ',
							checked + '/>',
						'</div>',
						'<div class="col-sm-10">',
							act_status.icon + '<br/>',
							act_status.text,
						'</div>',
					'</div>',
					'</li>'
				].join('\n');
				status_html_list.push(status_html);
			}
			var status_list_items_html = status_html_list.join('\n');
			var html = [
				'<div class="row">',
					'<div class="col-sm-1">',
					'</div>',
					'<div class="col-sm-5">',
						'<label>Project Editorial Status</label>',
						'<ul class="list-unstyled">',
							status_list_items_html,
						'</ul>',
					'</div>',
					'<div class="col-sm-3">',
						'<div id="proj-edit-status-submitcon" style="padding-top: 24px;">',
						button_html,
						'</div>',
						'<div id="proj-edit-status-respncon" style="padding-top: 10px;">',
						'</div>',
						'<div id="proj-edit-status-valid">',
						'</div>',
					'</div>',
					'<div class="col-sm-3">',
						'<label>Note</label>',
						'<p class="small">',
						'Change the editorial status to relfect the level of ',
						'scrutiny and evaluation that the project has received from ',
						'different members of the professional community',
						'</p>',
					'</div>',
				'</div>'
			].join('\n');
			document.getElementById("edit-proj-edit-status").innerHTML = html;
		}
	}
	this.updateEditorialStatus = function(){
		var edit_status = this.get_checked_radio_value_by_class('proj-edit-status');
		if (edit_status != null) {
			var act_icon = document.getElementById('proj-edit-status-respncon');
			act_icon.innerHTML = '';
			var act_note = document.getElementById('proj-edit-status-valid');
			act_note.innerHTML = 'Updating editorial status...';
			var url = this.make_url("/edit/update-item-basics/") + encodeURIComponent(this.item_uuid);
			return $.ajax({
				type: "POST",
				url: url,
				dataType: "json",
				context: this,
				data: {
					edit_status: edit_status,
					csrfmiddlewaretoken: csrftoken},
				success: this.updateEditorialStatusDone,
				error: function (request, status, error) {
					alert('Problem updating editorial status: ' + status);
				}
			});
		}
		else{
			return false;
		}
	}
	this.updateEditorialStatusDone = function(data){
		// too many things to change, so reload the whole page
		location.reload(true);
	}
	
	
	this.display_proj_parent = function(){
		if (this.super_user) {
			// only super users can change parent projects
			
			var entSearchObj = new searchEntityObj();
			var ent_name = 'parent_proj_search';
			entSearchObj.name = ent_name;
			// entSearchObj.ultra_compact_display = true;
			entSearchObj.parent_obj_name = this.obj_name;
			entSearchObj.entities_panel_title = 'Search for Parent Project';
			entSearchObj.limit_item_type = 'projects';
			var entDomID = entSearchObj.make_dom_name_id();
			var afterSelectDone = {
				entDomID: entDomID
			};
			afterSelectDone.exec = function(){
				var sel_id = document.getElementById(this.entDomID + "-sel-entity-id").value;
				var sel_label = document.getElementById(this.entDomID + "-sel-entity-label").value;
				document.getElementById('parent-project-label-outer').innerHTML = sel_label;
				var act_dom = document.getElementById('parent-project-input-outer');
				var html = [
					'<input type="radio" name="parent-project-uuid" ',
					'class="parent-project-uuid" ',
					'value="' + sel_id + '" ',
					'/>',
				].join('\n');
				act_dom.innerHTML = html;
			};
			entSearchObj.afterSelectDone = afterSelectDone;
			this.parent_proj_search = entSearchObj;
			var entityInterfaceHTML = entSearchObj.generateEntitiesInterface();
			
			var button_html = [
				'<button type="button" ',
				'class="btn btn-primary" ',
				'onclick="' + this.obj_name + '.updateParentProject();">',
				'Update',
				'</button>'
			].join('\n');
			
			var parent_obj = this.item_json_ld_obj.getParentProject();
			if (parent_obj == false) {
				var parent_obj = {uuid: this.item_uuid,
				                  label: 'Independent project'};
			}
			
			if (this.item_uuid == parent_obj['uuid']) {
				// the item is an independed project
				var ind_checked = 'checked="checked"';
				var sub_checked = '';
				var sub_disabled = 'disabled="disabled"';
				var parent_label = 'Use search box on left to select';
			}
			else{
				// the item is part of another project
				var ind_checked = '';
				var sub_checked = 'checked="checked"';
				var sub_disabled = '';
				var parent_label = parent_obj.label;
			}
			
			var radio_html = [
				'<li class="list-group-item">',
					'<div class="row">',
						'<div class="col-sm-1" style="padding-top: 0px; text-align:right;">',
							'<input type="radio" name="parent-project-uuid" ',
							'class="parent-project-uuid" value="' + this.item_uuid + '" ',
							ind_checked + '/>',
						'</div>',
						'<div class="col-sm-10">',
							'Independent Project (not part of another)',
						'</div>',
					'</div>',
				'</li>',
				'<li class="list-group-item">',
					'<div class="row">',
						'<div class="col-sm-1" style="padding-top: 0px; text-align:right;" id="parent-project-input-outer">',
							'<input type="radio" name="parent-project-uuid" ',
							'class="parent-project-uuid" value="' + parent_obj['uuid'] + '" ',
							sub_disabled + ' ',
							sub_checked + ' />',
						'</div>',
						'<div class="col-sm-10" id="parent-project-label-outer">',
							parent_label,
						'</div>',
					'</div>',
				'</li>'
			].join('\n');
				
			var html = [
				'<div class="row">',
					'<div class="col-sm-5">',
						entityInterfaceHTML,
					'</div>',
					'<div class="col-sm-4">',
						'<label>Project Part-Of Another Project?</label>',
						'<ul class="list-unstyled">',
							radio_html,
						'</ul>',
					'</div>',
					'<div class="col-sm-3">',
						'<div id="proj-edit-status-submitcon" style="padding-top: 24px;">',
						button_html,
						'</div>',
						'<div id="proj-edit-status-respncon" style="padding-top: 10px;">',
						'</div>',
						'<div id="proj-edit-status-valid">',
						'</div>',
						'<label>Note</label>',
						'<p class="small">',
						'A project can be independent, meaning it is not part of a ',
						'larger work in Open Context, or a project can be a ',
						'sub-project that is part of a larger project.',
						'</p>',
					'</div>',
				'</div>'
			].join('\n');
			document.getElementById("edit-proj-parent").innerHTML = html;
		}
	}
	
	this.updateParentProject = function(){
		// updates the parent project uuid based on radio input
		var parent_project_uuid = this.get_checked_radio_value_by_class('parent-project-uuid');
		if (parent_project_uuid != null) {
			var act_icon = document.getElementById('proj-edit-status-respncon');
			act_icon.innerHTML = '';
			var act_note = document.getElementById('proj-edit-status-valid');
			act_note.innerHTML = 'Updating project parent...';
			var url = this.make_url("/edit/update-item-basics/") + encodeURIComponent(this.item_uuid);
			return $.ajax({
				type: "POST",
				url: url,
				dataType: "json",
				context: this,
				data: {
					project_uuid: parent_project_uuid,
					csrfmiddlewaretoken: csrftoken},
				success: this.updateParentProjectDone,
				error: function (request, status, error) {
					alert('Problem updating parent project: ' + status);
				}
			});
		}
		else{
			return false;
		}
	}
	this.updateParentProjectDone = function(data){
		// too many things to change, so reload the whole page
		location.reload(true);
	}

	
	
	/******************************************************
	 * Person Related Fields
	 * ***************************************************/
	this.display_person_edits = function(){
		//displays project edit fields
		this.display_person_names();
		this.display_person_foaf_types();
	}
	
	this.display_person_names = function(){
		var person_obj = this.item_json_ld_obj.getPersonData();
		
		var jscript = [
		 ' onkeydown="' + this.obj_name + '.compose_combined_name();" ',
		 ' onkeyup="' + this.obj_name + '.compose_combined_name();" '
		].join(' ');
		
		var inputs = {
			combined_name: {label: 'Full Name', html: '', len: '', js: ''},
			given_name: {label: 'Given Name', html: '', len: '', js: jscript},
			surname: {label: 'Surname', html: '', len: '', js:jscript},
			initials: {label: 'Initials', html: '', len: ' length="5" ', js: ''},
			mid_init: {label: 'Middle Initial', html: '', len: ' length="3" ', js: jscript}
		};
		
		for (var key in inputs) {
			
			var html = [
				'<div class="form-group">',
					'<label for="proj-input-' + key + '">' + inputs[key].label + '</label>',
					'<input id="proj-input-' + key + '" ',
					'class="form-control input-sm" type="text" ',
					'value="' + person_obj[key] + '" ' + inputs[key].len + inputs[key].js,
					' />',
				'</div>'
			].join('\n');
		    inputs[key].html = html;
		}
		
		var button_html = [
			'<button type="button" ',
			'class="btn btn-primary" ',
			'onclick="' + this.obj_name + '.updatePersonNames();">',
			'Update',
			'</button>'
		].join('\n');
		
		var html = [
			'<div class="row">',
				'<div class="col-sm-6">',
					inputs.combined_name.html,
					inputs.given_name.html,
					inputs.surname.html,
					'<div class="row">',
						'<div class="col-sm-6">',
							inputs.mid_init.html,
						'</div>',
						'<div class="col-sm-6">',
							inputs.initials.html,
						'</div>',
					'</div>',
				'</div>',
				'<div class="col-sm-3">',
					'<div id="proj-person-names-submitcon" style="padding-top: 24px;">',
					button_html,
					'</div>',
					'<div id="proj-person-names-respncon" style="padding-top: 10px;">',
					'</div>',
					'<div id="proj-person-names-valid">',
					'</div>',
				'</div>',
				'<div class="col-sm-3">',
					'<label>Note</label>',
					'<p class="small">',
					'Use this interface to modify personal (or organizational) names. ',
					'</p>',
				'</div>',
			'</div>'
		].join('\n');
		document.getElementById("edit-person-names").innerHTML = html;
	}
	this.compose_combined_name = function(){
		// composes a person's combined name based on inputs
		// to given_name, mid_init, and surname
		var given_name = document.getElementById('proj-input-given_name').value;
		var surname = document.getElementById('proj-input-surname').value;
		var mid_init = document.getElementById('proj-input-mid_init').value;
		var act_dom = document.getElementById('proj-input-combined_name');
		var all_list = [];
		if (given_name.length > 0) {
			all_list.push(given_name);
		}
		if (mid_init.length > 0) {
			mid_init += '.'
			all_list.push(mid_init);
		}
		if (surname.length > 0) {
			all_list.push(surname);
		}
		var combined_name = all_list.join(' ');
		act_dom.value = combined_name;
	}
	
	this.updatePersonNames = function(){
		// sends an AJAX request to update a person name
		var combined_name = document.getElementById('proj-input-combined_name').value;
		var given_name = document.getElementById('proj-input-given_name').value;
		var surname = document.getElementById('proj-input-surname').value;
		var mid_init = document.getElementById('proj-input-mid_init').value;
		var initials = document.getElementById('proj-input-initials').value;
		if (combined_name.length > 0) {
			var act_icon = document.getElementById('proj-person-names-respncon');
			act_icon.innerHTML = '';
			var act_note = document.getElementById('proj-person-names-valid');
			act_note.innerHTML = 'Updating names...';
			var url = this.make_url("/edit/update-item-basics/") + encodeURIComponent(this.item_uuid);
			return $.ajax({
				type: "POST",
				url: url,
				dataType: "json",
				context: this,
				data: {
					label: combined_name,
					combined_name: combined_name,
					given_name: given_name,
					surname: surname,
					initials: initials,
					mid_init: mid_init,
					csrfmiddlewaretoken: csrftoken},
				success: this.updatePersonNamesDone,
				error: function (request, status, error) {
					alert('Problem updating person/organization names: ' + status);
				}
			});
		}
		else{
			alert('Cannot have a blank value for a full name.');
			return false;
		}
	}
	this.updatePersonNamesDone = function(data){
		// too many things to change, so reload the whole page
		location.reload(true);
	}
	
	
	
	this.display_person_foaf_types = function(){
		var person_obj = this.item_json_ld_obj.getPersonData();
		
		var button_html = [
			'<button type="button" ',
			'class="btn btn-primary" ',
			'onclick="' + this.obj_name + '.updatePersonType();">',
			'Update',
			'</button>'
		].join('\n');
		
		if (person_obj.foaf_type == 'foaf:Person') {
			var pers_checked = ' checked="checked" ';
			var org_checked = '';
		}
		else{
			var org_checked = ' checked="checked" ';
			var pers_checked = '';
		}
		
		var radio_html = [
			'<li class="list-group-item">',
				'<div class="row">',
					'<div class="col-sm-1" style="padding-top: 0px; text-align:right;">',
						'<input type="radio" name="person-foaf-type" ',
						'class="person-foaf-type" value="foaf:Person" ',
						pers_checked + '/>',
					'</div>',
					'<div class="col-sm-10">',
						'Individual Person',
					'</div>',
				'</div>',
			'</li>',
			'<li class="list-group-item">',
				'<div class="row">',
					'<div class="col-sm-1" style="padding-top: 0px; text-align:right;">',
						'<input type="radio" name="person-foaf-type" ',
						'class="person-foaf-type" value="foaf:Organization" ',
						org_checked + ' />',
					'</div>',
					'<div class="col-sm-10" id="parent-project-label-outer">',
						'Organization',
					'</div>',
				'</div>',
			'</li>'
		].join('\n');
		
		
		var html = [
			'<div class="row">',
				'<div class="col-sm-2">',
				'</div>',
				'<div class="col-sm-4">',
				    '<label>Person or Organization Type</label>',
					radio_html,
				'</div>',
				'<div class="col-sm-3">',
					'<div id="person-foaf-type-submitcon" style="padding-top: 24px;">',
					button_html,
					'</div>',
					'<div id="person-foaf-type-respncon" style="padding-top: 10px;">',
					'</div>',
					'<div id="person-foaf-type-valid">',
					'</div>',
				'</div>',
				'<div class="col-sm-3">',
					'<label>Note</label>',
					'<p class="small">',
					'Does this record describe a person or an organization? ',
					'</p>',
				'</div>',
			'</div>'
		].join('\n');
		document.getElementById("edit-person-type").innerHTML = html;
	}
	this.updatePersonType = function(){
		var foaf_type = this.get_checked_radio_value_by_class('person-foaf-type');
		if (foaf_type != null) {
			var act_icon = document.getElementById('person-foaf-type-respncon');
			act_icon.innerHTML = '';
			var act_note = document.getElementById('person-foaf-type-valid');
			act_note.innerHTML = 'Updating type...';
			
			var url = this.make_url("/edit/update-item-basics/") + encodeURIComponent(uuid);
			return $.ajax({
				type: "POST",
				url: url,
				dataType: "json",
				context: this,
				data: {
					class_uri: foaf_type,
					csrfmiddlewaretoken: csrftoken},
				success: this.updatePersonTypeDone,
				error: function (request, status, error) {
					alert('Problem updating person/organization type: ' + status);
				}
			});
			
			
		}
		else{
			return false;
		}
	}
	this.updatePersonTypeDone = function(data){
		var act_icon = document.getElementById('person-foaf-type-respncon');
		act_icon.innerHTML = '';
		var act_note = document.getElementById('person-foaf-type-valid');
		act_note.innerHTML = '';
		if (data.ok) {
			this.make_temp_update_note_html('person-foaf-type-respncon');
		}
	}
	
	
	/******************************************************
	 * Tables Editing functions
	 * ***************************************************/
	this.display_table_edits = function(){
		//displays table edit fields
		this.display_table_abstract();
	}
	this.display_table_abstract = function(){
		// inferface for editing abstract / long table description
		var html = this.make_abstract_edit_html();
		document.getElementById("edit-table-abstract").innerHTML = html;
	}
	
	
	/******************************************************
	 * Documents Editing functions
	 * ***************************************************/
	this.display_document_edits = function(){
		//displays table edit fields
		this.display_document_content();
	}
	this.display_document_content = function(){
		// inferface for editing document HTML
		var act_pred = 'rdf:HTML';
		var doc_html = this.item_json_ld_obj.predGetDefaultString(act_pred);
		if (doc_html == false) {
			var doc_html = '';
			var placeholder = 'placeholder="A note defining this concept."';
		}
		else {
			var placeholder = '';
		}
		
		var button_html = [
			'<button type="button" ',
			'class="btn btn-primary" ',
			'onclick="' + this.obj_name + '.updateDocumentHTML();">',
			'Update',
			'</button>'
		].join('\n');
		
		var html = [
			'<div class="row">',
				'<div class="col-sm-9">',
					'<div class="form-group">',
                        '<label for="document-note">',
						'Document Content (HTML)</label>',
                        '<textarea id="document-note" ',
						'class="form-control" rows="24" ',
						placeholder + '>',
						doc_html,
						'</textarea>',
                    '</div>', 
				'</div>',
				'<div class="col-sm-3">',
					'<div id="document-note-submitcon" style="padding-top: 24px;">',
					button_html,
					'</div>',
					'<div id="document-note-respncon" style="padding-top: 10px;">',
					'</div>',
					'<div id="document-note-valid">',
					'</div>',
					this.make_localize_row_html(act_pred, 'content', 'Document Content'),
					'<div>',
						'<label>Note</label>',
						'<p class="small">',
						'An note should use HMTL tags for formatting, including images, ',
						'hyperlinks, and may even include some javascript for dynamic ',
						'interactions. The content of the note should include ',
						'information needed to understand and reuse this concept. ',
						'</p>',
						'<p class="small">',
						'The note should validate as HTML. Upon submission or update, Open ',
						'Context will check and validate the HTML. It will accept bad HTML, but bad ',
						'HTML may cause severe formatting or other problems. Please use the W3C ',
						'HTML <a href="https://validator.w3.org/" targer="_blank">validation services</a> ',
						'to help debug your HTML.',
						'</p>',
					'</div>',
				'</div>',
			'</div>'
		].join('\n');
		document.getElementById("edit-document-content").innerHTML = html;
		
	}
	this.updateDocumentHTML = function() {
		/* updates the document html content for the item
		*/
		var act_domID = "document-note";
		var content = document.getElementById(act_domID).value;
		var url = this.make_url("/edit/update-item-basics/") + encodeURIComponent(this.item_uuid);
		var act_icon = document.getElementById('document-note-respncon');
		act_icon.innerHTML = '';
		var act_note = document.getElementById('document-note-valid');
		act_note.innerHTML = 'Uploading and validating...';
		var req = $.ajax({
			type: "POST",
			url: url,
			dataType: "json",
			data: {
				content: content,
				content_type: 'content',
				csrfmiddlewaretoken: csrftoken},
			context: this,
			success: this.updateDocumentHTMLDone,
			error: function (request, status, error) {
				alert('Problem updating the document HTML: ' + status);
			}
		});
	}
	this.updateDocumentHTMLDone = function(data){
		// handles successful result of document content HTML updates
		var act_icon = document.getElementById('document-note-respncon');
		act_icon.innerHTML = '';
		var act_note = document.getElementById('document-note-valid');
		act_note.innerHTML = '';
		if (data.ok) {
			this.make_temp_update_note_html('document-note-respncon');
		}
		this.make_html_valid_note_html(data, 'document-note-valid');
	}
	
	
	/******************************************************
	* Abstract related editing funcitons
	*******************************************************/
	this.make_abstract_edit_html = function(){
		// interface for making (long) project and table abstracts
		var dom_prefix = 'proj-';
		var note_text = [
			'An abstract should use HMTL tags for formatting, including images, ',
			'hyperlinks, and may even include some javascript for dynamic ',
			'interactions. The content of the abstract should include ',
			'essential background information about the project, its research goals, ',
			'research methods and potential sampling biases / issues, ',
			'potential ways the data can be reused, and other important information ',
			'useful for interpretation.'
		].join('\n');
		
		if (this.item_type == 'tables') {
			dom_prefix = 'tables-';
			note_text = [
				'An abstract should use HMTL tags for formatting, including images, ',
				'hyperlinks. The content of the abstract should include ',
				'essential background information about the dataset, ',
				'potential sampling biases / issues, ',
				'potential ways the data can be reused, and other important information ',
				'useful for interpretation.'
			].join('\n');
		}
		
		var act_pred = 'dc-terms:abstract';
		var placeholder = '';
		var abstract_html = this.item_json_ld_obj.predGetDefaultString(act_pred);
		if (abstract_html == false) {
			var abstract_html = '';
			var placeholder = 'placeholder="A detailed abstract descripting the project, research methods, data reuse ideas, etc."';
		}
		var button_html = [
			'<button type="button" ',
			'class="btn btn-primary" ',
			'onclick="' + this.obj_name + '.updateAbstract();">',
			'Update',
			'</button>'
		].join('\n');
		
		var html = [
			'<div class="row">',
				'<div class="col-sm-9">',
					'<div class="form-group">',
                        '<label for="' + dom_prefix + 'abstract">',
						'Abstract / Overview</label>',
                        '<textarea id="' + dom_prefix + 'abstract" ',
						'class="form-control" rows="24" ',
						placeholder + '>',
						abstract_html,
						'</textarea>',
                    '</div>', 
				'</div>',
				'<div class="col-sm-3">',
					'<div id="' + dom_prefix + 'abstract-submitcon" style="padding-top: 24px;">',
					button_html,
					'</div>',
					'<div id="' + dom_prefix + 'abstract-respncon" style="padding-top: 10px;">',
					'</div>',
					'<div id="' + dom_prefix + 'abstract-valid">',
					'</div>',
					this.make_localize_row_html(act_pred, 'content', 'Abstract'),
					'<div>',
						'<label>Note</label>',
						'<p class="small">',
						note_text,
						'</p>',
						'<p class="small">',
						'The abstract should validate as HTML. Upon submission or update, Open ',
						'Context will check and validate the HTML. It will accept bad HTML, but bad ',
						'HTML may cause severe formatting or other problems. Please use the W3C ',
						'HTML <a href="https://validator.w3.org/" targer="_blank">validation services</a> ',
						'to help debug your HTML.',
						'</p>',
					'</div>',
				'</div>',
			'</div>'
		].join('\n');
		return html;
	}
	this.updateAbstract = function() {
		/* updates the short description of a project item
		*/
		var dom_prefix = 'proj-';
		if (this.item_type == 'tables') {
			dom_prefix = 'tables-';
		}
		var act_domID = dom_prefix + 'abstract';
		var content = document.getElementById(act_domID).value;
		var url = this.make_url("/edit/update-item-basics/") + encodeURIComponent(this.item_uuid);
		var act_icon = document.getElementById(dom_prefix + 'abstract-respncon');
		act_icon.innerHTML = '';
		var act_note = document.getElementById(dom_prefix + 'abstract-valid');
		act_note.innerHTML = 'Uploading and validating...';
		var req = $.ajax({
			type: "POST",
			url: url,
			dataType: "json",
			data: {
				item_alt_id: this.item_alt_id,
				content: content,
				content_type: 'content',
				csrfmiddlewaretoken: csrftoken},
			context: this,
			success: this.updateAbstractDone,
			error: function (request, status, error) {
				alert('Problem updating the abstract: ' + status);
			}
		});
	}
	this.updateAbstractDone = function(data){
		// handles successful result of abstract / long description updates
		var dom_prefix = 'proj-';
		if (this.item_type == 'tables') {
			dom_prefix = 'tables-';
		}
		var act_icon = document.getElementById(dom_prefix + 'abstract-respncon');
		act_icon.innerHTML = '';
		var act_note = document.getElementById(dom_prefix + 'abstract-valid');
		act_note.innerHTML = '';
		if (data.ok) {
			this.make_temp_update_note_html(dom_prefix + 'abstract-respncon');
		}
		this.make_html_valid_note_html(data, dom_prefix + 'abstract-valid');
	}
	
	
	/******************************************************
	 * Functions relating to making localizaiton buttings,
	 * creating multilingual localization objects
	 * ***************************************************/
	this.localizeInterface = function(act_pred, content_type, label){
		// creates a localization object if not already present for this ml_key
		// then opens its interface
		var ml_key = act_pred.replace(':', '-');
		if (ml_key in this.multilingual) {
			// we already have a multilingual object for this key
			var act_ml = this.multilingual[ml_key];
		}
		else{
			// create a new multingual object for this ml_key
			var act_ml = new multilingual();
			act_ml.localization = this.item_json_ld_obj.predGetLocalizations(act_pred);
		    act_ml.parent_obj_name = this.obj_name;
			act_ml.obj_name = 'multilingual[\'' + ml_key + '\']';
			act_ml.label = label;
			act_ml.edit_type = 'content';
			act_ml.content_type = content_type;
			act_ml.edit_uuid = this.item_uuid;
			act_ml.dom_ids = act_ml.default_domids(0, ml_key);
			if (ml_key == 'dc-terms-abstract' || ml_key == 'skos-note' || ml_key == 'rdf-HTML') {
				// make a big text box, because abstract
				act_ml.text_box_rows = 24;
			}
			act_ml.initialize();
			this.multilingual[ml_key] = act_ml;
		}
		act_ml.localizeInterface();
		return false;
	}
	this.make_localize_row_html = function(ml_key, content_type, label){
		var note = '<p class="small">Click button to translate <em>' + label + '</em></p>';
		var html = [
			//'<div class="container-fluid">',
				'<div class="row">',
					'<div class="col-xs-1" style="padding-top: 5px;">',
					this.make_localize_buttom_html(ml_key, content_type, label),
					'</div>',
					'<div class="col-xs-10">',
					note,
					'</div>',
				'</div>',
			//'</div>',
		].join('\n');
		return html;
	}
	this.make_localize_buttom_html = function(ml_key, content_type, label){
		var title = 'Translate / localize ' + label;
		var style = '';
		var buttom_params = '\'' + ml_key + '\', \'' + content_type + '\', \'' + label + '\'';
		var button_html = [
			'<div ' + style + ' >',
			'<button title="' + title + '" ',
			'class="btn btn-info btn-xs" ',
			// below, the "return false;" part stops the page from reloading after onlick is done
			'onclick="' + this.obj_name + '.localizeInterface(' + buttom_params + '); return false;">',
			'<span class="glyphicon glyphicon-flag"></span>',
			'</button>',
			'</div>',
			].join('\n');
		return button_html;
	}
	
	/******************************************************
	 * Generally used, helper functions
	 * ***************************************************/
	this.make_html_valid_note_html = function(data, valid_dom_id){
		// makes an html note about the validation status of
		// submitted text. notes if it works for HTML
		if (document.getElementById(valid_dom_id)) {
			var act_dom = document.getElementById(valid_dom_id); 
			var valid_html = true;
			if ('errors' in data) {
				var errors = data.errors;
				if ('html' in errors) {
					if (errors.html != false) {
						valid_html = false;
						html_message = errors.html;
					}
				}
			}
			if (valid_html) {
				var html = [
					'<div class="alert alert-success small" role="alert">',
					'<span class="glyphicon glyphicon-ok-circle text-success" aria-hidden="true"></span> ',
					'Text OK in HTML',
					'</div>'
				].join('\n');
			}
			else{
				var html = [
					'<div class="alert alert-warning small" role="alert">',
					'<span class="glyphicon glyphicon-warning-sign text-warning" aria-hidden="true"></span> ',
					html_message,
					'</div>'
				].join('\n');
			}
			act_dom.innerHTML = html;
		}
	}
	this.make_temp_update_note_html = function(note_dom_id){
		// makes a temporary note that says the update was completed
		// disappears after 4.5 seconds
		if (document.getElementById(note_dom_id)) {
			var act_dom = document.getElementById(note_dom_id);
			var html = [
				'<div style="margin-top: 10px;">',
					'<div class="alert alert-success small" role="alert">',
						'<span class="glyphicon glyphicon-ok-circle" aria-hidden="true"></span>',
						'<span class="sr-only">Success:</span>',
						'Update done.',
					'</div>',
				'</div>'
			].join('\n');
			act_dom.innerHTML = html;
			setTimeout(function() {
				// display an OK message for a short time
				act_dom.innerHTML = '';
			}, 4500);
		}
	}
	this.get_checked_radio_value_by_class = function(class_name){
		// gets the value of a checked radio input element
		// by class
		var output = null;
		var act_inputs = document.getElementsByClassName(class_name);
		for (var i = 0, length = act_inputs.length; i < length; i++) {
			if (act_inputs[i].checked) {
				var output = act_inputs[i].value;
			}
		}
		return output;
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