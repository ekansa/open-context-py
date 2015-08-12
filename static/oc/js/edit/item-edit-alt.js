/*
 * Functions to edit an item
 */
function itemEdit(item_type, item_uuid){
	this.project_uuid = project_uuid;
	this.item_uuid = item_uuid;
	this.item_type = item_type;
	this.fields = [];
	this.obj_name = 'edit_item';
	this.panels = [];
	this.obs_fields = {};
	this.observations = {};
	this.searchObject = false;
	this.active_search_entity = false;
	this.active_obs_num = false;
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
				this.prepare_fields();
				this.show_observation_data();
				this.fields_postprocess();
			}
		}
	}
	this.show_observation_data = function(){
		// first get information on the predicates from the JSON-LD context
		console.log(this.fields);
		this.item_json_ld_obj.getPredicates();
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
					obs_panel.title_html = fgroup.label;
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
	
	this.prepare_fields = function(){
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
			field.postprocess();
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
}