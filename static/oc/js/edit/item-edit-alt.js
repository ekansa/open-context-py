/*
 * Functions to edit an item
 */
function itemEdit(item_type, item_uuid){
	this.super_user = false;
	this.project_uuid = project_uuid;
	this.item_uuid = item_uuid;
	this.item_type = item_type;
	this.label_field = false; // the field object for the item label
	this.class_field = false; // the field object for the item class
	this.context_field = false; // the field object for the item context
	this.fields = [];  // list of field objects for other descriptive fields (in the item observations)
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
				// get observation data
				this.prepare_basics();
				this.show_basic_fields();
				this.prepare_fields();
				this.show_observation_data();
				this.fields_postprocess();
				if (typeof edit_geoevents !=  "undefined") {
					// prep geospatial interface if interface object exists
					edit_geoevents.show_existing_data()
				}
				if (this.item_type == 'projects') {
					// display project specifics
					this.display_project_edits();
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
	this.show_observation_data = function(){
		// first get information on the predicates from the JSON-LD context
		console.log(this.fields);
		//this.item_json_ld_obj.getPredicates();
		var observations = this.item_json_ld_obj.getObservations();
		var number_obs = observations.length;
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
		var dom_ids = this.make_obs_dom_ids(obs_num);
		if (this.active_search_entity != false) {
			// we have a search entity to use
			var predicate_uuid = false;
			if (this.active_search_entity.hasOwnProperty('uuid')) {
				var predicate_uuid = this.active_search_entity.uuid;
			}
			else if (this.active_search_entity.hasOwnProperty('id')) {
				var predicate_uuid = this.active_search_entity.id;
			}
			var obs = this.observations[obs_num];
			var field = new edit_field();
			field.id = this.fields.length;
			field.project_uuid = this.project_uuid;
			field.pred_type = this.active_search_entity.class_uri;
			field.parent_obj_name = this.obj_name;
			field.obj_name = 'fields[' + field.id + ']';
			field.add_new_data_row = true;
			field.edit_new = false;
			field.edit_uuid = this.item_uuid;
			field.item_type = this.item_type;
			field.label = this.active_search_entity.label;
			field.predicate_uuid = predicate_uuid;
			field.draft_sort = this.fields.length + 1;
			field.obs_num = obs_num;
			field.obs_node = obs['id'];
			field.data_type = this.active_search_entity.data_type;
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
			//now hide the modal interface
			$("#myModal").modal('hide');
		}
		else{
			alert('no active field');
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
		if (this.item_json_ld_obj.data.hasOwnProperty('description')) {
			var short_des = this.item_json_ld_obj.data['description'];
		}
		else{
			var short_des = '';
		}
		if (short_des.length > 0) {
			var placeholder = '';
		}
		else{
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
                        '<label for="proj-short-des">Short Description / Summary</label>',
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
				'</div>',
				'<div class="col-sm-3">',
					'<label>Note</label>',
					'<p class="small">',
					'A short "Tweetable" (140 character) or so text description',
					'</p>',
				'</div>',
			'</div>'
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
		// inferface for editing short project description
		if (this.item_json_ld_obj.data.hasOwnProperty('dc-terms:abstract')) {
			var proj_abstract = this.item_json_ld_obj.data['dc-terms:abstract'];
		}
		else{
			var proj_abstract = '';
		}
		if (proj_abstract.length > 0) {
			var placeholder = '';
		}
		else{
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
                        '<label for="proj-abstract">Project Abstract / Overview</label>',
                        '<textarea id="proj-abstract" ',
						'class="form-control" rows="24" ',
						placeholder + '>',
						proj_abstract,
						'</textarea>',
                    '</div>', 
				'</div>',
				'<div class="col-sm-3">',
					'<div id="proj-abstract-submitcon" style="padding-top: 24px;">',
					button_html,
					'</div>',
					'<div id="proj-abstract-respncon" style="padding-top: 10px;">',
					'</div>',
					'<div id="proj-abstract-valid">',
					'</div>',
					'<div>',
						'<label>Note</label>',
						'<p class="small">',
						'An abstract should use HMTL tags for formatting, including images, ',
						'hyperlinks, and may even include some javascript for dynamic ',
						'interactions. The content of the abstract should include ',
						'essential background information about the project, its research goals, ',
						'research methods and potential sampling biases / issues, ',
						'potential ways the data can be reused, and other important information ',
						'useful for interpretation.',
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
		document.getElementById("edit-proj-abstract").innerHTML = html;
	}
	this.updateAbstract = function() {
		/* updates the short description of a project item
		*/
		var act_domID = "proj-abstract";
		var content = document.getElementById(act_domID).value;
		var url = this.make_url("/edit/update-item-basics/") + encodeURIComponent(this.item_uuid);
		var act_icon = document.getElementById('proj-abstract-respncon');
		act_icon.innerHTML = '';
		var act_note = document.getElementById('proj-abstract-valid');
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
			success: this.updateAbstractDone,
			error: function (request, status, error) {
				alert('Problem updating the abstract: ' + status);
			}
		});
	}
	this.updateAbstractDone = function(data){
		// handles successful result of short description updates
		var act_icon = document.getElementById('proj-abstract-respncon');
		act_icon.innerHTML = '';
		var act_note = document.getElementById('proj-abstract-valid');
		act_note.innerHTML = '';
		if (data.ok) {
			this.make_temp_update_note_html('proj-abstract-respncon');
		}
		this.make_html_valid_note_html(data, 'proj-abstract-valid');
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
		this.display_proj_short_des();
		
		
		this.display_proj_abstract();
		this.display_proj_edit_status();
		this.display_proj_parent();
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