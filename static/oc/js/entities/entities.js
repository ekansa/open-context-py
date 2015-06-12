/*
 * ------------------------------------------------------------------
	AJAX for entity searches
 * ------------------------------------------------------------------
*/

function searchEntityObj() {
	/* Object for composing search entities */
	this.name = "ent"; //object name, used for DOM-ID prefixes and object labeling
	this.search_text_domID = "entity-string";
	this.searchEntityListDomID = "search-entity-list";
	this.selectFoundEntityFunction = "selectEntity";
	this.entities_panel_title = "Entity Lookup";
	this.limit_class_uri = false;
	this.limit_project_uuid = false;
	this.limit_vocab_uri = false;
	this.limit_item_type = false;
	this.limit_ent_type = false;
	this.url = "../../entities/look-up/";
	this.interfaceDomID = false;
	this.req = false;
	this.selectReadOnly = true;
	this.additionalButton = false;
	this.afterSelectDone = false; // put a function here to execute after a user selects an entity
	this.show_type = false;
	this.show_partof = false;
	
	this.generateEntitiesInterface = function (){
		/* returns a HTML string to generate an entities search interface */
		if (this.selectReadOnly) {
			this.selectReadOnly = "readonly";
		}
		else{
			this.selectReadOnly = "";
		}
		this.selectReadOnly = this.selectReadOnly || "readonly";
		if (this.additionalButton != false) {
			//request to add an additional button to add more functionality
			var disabled = "";
			if (this.additionalButton.buttonDisabled) {
				disabled = "disabled=\"disabled\"";
			}
			var buttonGroupHTML = [
				"<div class=\"form-group form-group-sm\">",
					"<label for=\"sel-added-control\" class=\"col-xs-2 control-label\">" + this.additionalButton.label + "</label>",
						"<div class=\"col-xs-10\">",
							"<button id=\"" + this.additionalButton.buttonID + "\" style=\"margin-bottom:1%;\" type=\"button\" ",
							"class=\"" + this.additionalButton.buttonClass + "\" onclick=\"javascript:" + this.additionalButton.funct + ";\"",
							disabled + ">",
							"<span class=\"" + this.additionalButton.icon + "\"></span>",
							" " + this.additionalButton.buttonText + "</button>",
						"</div>",
					"</div>"
			].join("\n");
		}
		else{
			var buttonGroupHTML = "";
		}
		var context_html = "";
		if (this.show_type || this.show_partof) {
			if (this.show_type) {
				context_html += '<div class="row small">';
				context_html += '<div class="col-xs-2"><label>Type</label></div>';
				context_html += '<div class="col-xs-10" id="' + this.name + 'sel-type"></div>';
				context_html += '</div>';
			}
			if (this.show_partof) {
				context_html += '<div class="row small">';
				context_html += '<div class="col-xs-2"><label>Part of</label></div>';
				context_html += '<div class="col-xs-10" id="' + this.name + 'sel-partof"></div>';
				context_html += '</div>';
			}
			context_html += '<div class="row small">';
			context_html += '<div class="col-xs-12"><div style="padding:10px;"></div></div>';
			context_html += '</div>';
		}
		var interfaceString = [	
			"<div class=\"panel panel-default\">",
				"<div class=\"panel-heading\">",
					"<h4 class=\"panel-title\">" + this.entities_panel_title + "</h4>",
				"</div>",
				"<div class=\"panel-body\">",
					"<form class=\"form-horizontal\" role=\"form\">",
						"<div class=\"form-group form-group-sm\">",
							"<label for=\"sel-entity-label\" class=\"col-xs-2 control-label\">Label</label>",
							"<div class=\"col-xs-10\">",
								"<input id=\"" + this.name + "-sel-entity-label\" type=\"text\"  value=\"\" placeholder=\"Select an entity\" class=\"form-control input-sm\" " + this.selectReadOnly + "/>",
							"</div>",
						"</div>",
						"<div class=\"form-group form-group-sm\">",
							"<label for=\"sel-entity-id\" class=\"col-xs-2 control-label\">ID</label>",
							"<div class=\"col-xs-10\">",
								"<input id=\"" + this.name + "-sel-entity-id\" type=\"text\"  value=\"\" placeholder=\"Select an entity\" class=\"form-control input-sm\" " + this.selectReadOnly + "/>",
							"</div>",
						"</div>",
						context_html,
						buttonGroupHTML,
						"<div class=\"form-group form-group-sm\">",
							"<label for=\"entity-string\" class=\"col-xs-2 control-label\">Search</label>",
							"<div class=\"col-xs-10\">",
								"<input id=\"" + this.name + "-" + this.search_text_domID + "\" type=\"text\"  value=\"\" onkeydown=\"javascript:" + this.name + ".searchEntities();\" class=\"form-control input-sm\" />",
							"</div>",
						"</div>",
					"</form>",
					"<ul id=\"" + this.name + "-" + this.searchEntityListDomID + "\">",
					"</ul>",
				"</div>",
			"</div>"].join("\n");
		if (this.interfaceDomID != false) {
			var act_dom = document.getElementById(this.interfaceDomID);
			act_dom.innerHTML = interfaceString;
		}
		return interfaceString;
	};
	this.searchEntities = function(){
		var url = this.url;
		var qstring = document.getElementById(this.name + "-" + this.search_text_domID).value;
		var searchEntityListDom = document.getElementById(this.name + "-" + this.searchEntityListDomID);
		searchEntityListDom.innerHTML = "<li>Searching for '" + qstring + "'...</li>";
		var data = { q:qstring };
		if (this.limit_class_uri != false) {
			data['class_uri'] = this.limit_class_uri;
		}
		if (this.limit_project_uuid != false) {
			data['project_uuid'] = this.limit_project_uuid;
		}
		if (this.limit_vocab_uri != false) {
			data['vocab_uri'] = this.limit_vocab_uri;
		}
		if (this.limit_ent_type != false) {
			data['ent_type'] = this.limit_ent_type;
		}
		if (this.limit_item_type != false) {
			url += this.limit_item_type;
		}
		else{
			url += "0";
		}
		this.req = $.ajax({
			type: "GET",
			url: url,
			dataType: "json",
			data: data,
			context: this,
			success: this.searchEntitiesDone
		});
	}
	this.searchEntitiesDone = function(data){
		/* Displays list of entities that meet search criteria */
		var searchEntityListDom = document.getElementById(this.name + "-" + this.searchEntityListDomID);
		searchEntityListDom.innerHTML = "";
		for (var i = 0, length = data.length; i < length; i++) {
			var data_type = 'Not Specified';
			if (data[i].class_uri != false) {
				var data_type = data[i].class_uri;
			}
			else if (data[i].ent_type != false) {
				var data_type = data[i].ent_type + ' (Linked Data)'; 
			}
			else{
				var data_type = "Not specified";
			}
			var partof = data[i].partOf_label;
			
			var tooltiplink = [
				'<a onclick="' + this.name + '.selectEntity(' + i + ')" ',
				'data-toggle="tooltip" data-placement="bottom" ',
				'title="Type: ' + data_type + '; part of: ' + partof + '" ',
				'id="' + this.name + '-search-entity-label-' + i + '" >',
				data[i].label,
				'</a>'
			].join('');
			
			var newListItem = document.createElement("li");
			newListItem.id = this.name + "-search-entity-item-" + i;
			var entityIDdomID = this.name + "-search-entity-id-" + i;
			var linkHTML = generateEntityLink(entityIDdomID, data[i].type, data[i].id, data[i].id);
			var entityString = tooltiplink;
			// entityString += "<br/><small id=\"search-entity-id-" + i + "\">" + data[i].id + "</small>";
			entityString += "<br/><small>" + linkHTML + "</small>";
			newListItem.innerHTML = entityString;
			searchEntityListDom.appendChild(newListItem);
		}

		// turn on tool tips for these search results
		$(function () {
			$('[data-toggle="tooltip"]').tooltip()
		})
		
	}
	this.selectEntity = function(item_num){
		/* Adds selected entity label and ID to the right dom element */
		var act_domID = this.name + "-search-entity-id-" + item_num;
		var item_id = document.getElementById(act_domID).innerHTML;
		var sel_id_dom = document.getElementById(this.name + "-sel-entity-id");
		sel_id_dom.value = item_id;
		act_domID =  this.name + "-search-entity-label-" + item_num;
		var item_label = document.getElementById(act_domID).innerHTML;
		var sel_label_dom = document.getElementById(this.name + "-sel-entity-label");
		sel_label_dom.value = item_label;
		if (this.afterSelectDone != false) {
			// execute a post selection entity is done function
			if (typeof(this.afterSelectDone.exec) !== 'undefined') {
				this.afterSelectDone.exec();
			}
		}
	}
}


function generateEntityLink(nodeID, entity_type, entity_id, entity_label){
	var linkHTML = "";
	var labelSpan = "<span id=\"" + nodeID + "\">" + entity_label + "</span>";
	if (entity_type != "uri" && entity_type != "import-field" && entity_type != "user-typed-link") {
		var icon = "<span class=\"glyphicon glyphicon-new-window\"></span> ";
		linkHTML = "<a title=\"View in new tab\" href=\"../../" + entity_type + "/" + entity_id + "\" target=\"_blank\">" + icon + labelSpan + "</a>";
	}
	else if (entity_type == "uri") {
		var icon = "<span class=\"glyphicon glyphicon-new-window\"></span> ";
		linkHTML = "<a title=\"View in new tab\" href=\"" + entity_id + "\" target=\"_blank\">" + icon + labelSpan + "</a>";
	}
	else{
		if (entity_type == "user-typed-link") {
			var icon = "<span class=\"glyphicon glyphicon-new-window\"></span> ";
		}
		linkHTML = labelSpan;
	}
	return linkHTML;
}


function addEntityObj() {
	/* Object for adding a record of a linked-data entity */
	this.name = "add_ent"; //object name, used for DOM-ID prefixes and object labeling
	this.selectFoundEntityFunction = "addEntity";
	this.entities_panel_title = "Add Linked Data Entity";
	this.limit_vocab_uri = false;
	this.limit_ent_type = false;
	this.url = "../../entities/add-linked-entity/";
	this.interfaceDomID = false;
	this.req = false;
	this.additionalButton = false;
	this.collapse_panel = true;
	this.afterSelectDone = false; // put a function here to execute after a user selects an entity
	this.generateInterface = function (){
		/* returns a HTML string to generate an entities search interface */
		
		if (this.additionalButton != false) {
			//request to add an additional button to add more functionality
			var disabled = "";
			if (this.additionalButton.buttonDisabled) {
				disabled = "disabled=\"disabled\"";
			}
			var buttonGroupHTML = [
				"<div class=\"form-group form-group-sm\">",
					"<label for=\"sel-added-control\" class=\"col-xs-2 control-label\">" + this.additionalButton.label + "</label>",
						"<div class=\"col-xs-10\">",
							"<button id=\"" + this.additionalButton.buttonID + "\" style=\"margin-bottom:1%;\" type=\"button\" ",
							"class=\"" + this.additionalButton.buttonClass + "\" onclick=\"javascript:" + this.additionalButton.funct + ";\"",
							disabled + ">",
							"<span class=\"" + this.additionalButton.icon + "\"></span>",
							" " + this.additionalButton.buttonText + "</button>",
						"</div>",
					"</div>"
			].join("\n");
		}
		else{
			var buttonGroupHTML = "";
		}
		
		if (this.collapse_panel) {
			//the interface will be in a collapse panel
			var contain_div_id = this.name + '-outer-div';
			var collapse_div_id = this.name + '-collapse-div';
			var collapse_class = ' collapse';
			var contain_div = '<div class="panel-group" id="' + contain_div_id + '">';
			var head_html = [
			'<h4 class="panel-title">',
                        '<a data-toggle="collapse" data-parent="#' + contain_div_id + '" ',
			'href="#' + collapse_div_id + '">',
                        '<span class="glyphicon glyphicon-resize-vertical"></span> ',
                        this.entities_panel_title,    
                        '</a>',
                        '</h4>'
			].join("\n");
		}
		else{
			var collapse_class = "";
			var collapse_div_id = this.name + '-collapse-div';
			var contain_div = '<div>';
			var head_html = "<h4 class=\"panel-title\">" + this.entities_panel_title + "</h4>";
		}
		
		var interfaceString = [	
			contain_div,
			"<div class=\"panel panel-default\">",
				"<div class=\"panel-heading\">",
					head_html,
				"</div>",
				"<div id=\"" + collapse_div_id + "\" class=\"panel-body" + collapse_class + "\">",
					"<form class=\"form-horizontal\" role=\"form\">",
						"<div class=\"form-group form-group-sm\">",
							"<label for=\"sel-entity-id\" class=\"col-xs-3 control-label\">URI</label>",
							"<div class=\"col-xs-9\">",
								"<input id=\"" + this.name + "-add-entity-id\" type=\"text\"  value=\"\" placeholder=\"Add URI\" class=\"form-control input-sm\" />",
							"</div>",
						"</div>",
						"<div class=\"form-group form-group-sm\">",
							"<label for=\"sel-entity-label\" class=\"col-xs-3 control-label\">Label</label>",
							"<div class=\"col-xs-9\">",
								"<input id=\"" + this.name + "-add-entity-label\" type=\"text\"  value=\"\" placeholder=\"Add main label\" class=\"form-control input-sm\" />",
							"</div>",
						"</div>",
						"<div class=\"form-group form-group-sm\">",
							"<label for=\"sel-entity-label\" class=\"col-xs-3 control-label\">Alt. Label</label>",
							"<div class=\"col-xs-9\">",
								"<input id=\"" + this.name + "-add-entity-altlabel\" type=\"text\"  value=\"\" placeholder=\"Add alternative label\" class=\"form-control input-sm\" />",
							"</div>",
						"</div>",
						"<div class=\"form-group form-group-sm\">",
							"<label for=\"sel-entity-label\" class=\"col-xs-3 control-label\">Vocab. URI</label>",
							"<div class=\"col-xs-9\">",
								"<input id=\"" + this.name + "-add-entity-vocab-uri\" type=\"text\"  value=\"\" placeholder=\"Add to a URI identified vocabulary\" class=\"form-control input-sm\" />",
							"</div>",
						"</div>",
						"<div class=\"form-group form-group-sm\" style=\"margin-left:5px;\">",
					
					'<label>URI Entity Type</label><br/>',
					'<label class="radio-inline">',
					'<input type="radio" name="new-ent-type" id="ent-type-prop" ',
					'class="new-ent-type" value="property" >',
					'Property </label>',
					'<label class="radio-inline">',
					'<input type="radio" name="new-ent-type" id="ent-type-class" ',
					'class="new-ent-type" value="class" checked="checked" />',
					'Class (type) </label>',
					'<label class="radio-inline">',
					'<input type="radio" name="new-ent-type" id="ent-type-vocabulary" ',
					'class="new-ent-type" value="vocabulary" />',
					'Vocabulary </label>',

						"</div>",
						buttonGroupHTML,
						"<div class=\"form-group form-group-sm\">",
							"<div class=\"col-xs-12\">",
								'<button class="btn btn-primary" onclick="',
								this.name + '.addLinkDataEntity();">Submit</button>',
							"</div>",
						"</div>",
					"</form>",
					"<p><small><strong>NOTE:</strong> Each 'property' or 'class' entity needs ",
					"to be part of a URI identified vocabulary. Use this interface to add ",
					"URI identified vocabularies as needed.</small></p>",
				"</div>",
			"</div>",
			"</div>"
			].join("\n");
		if (this.interfaceDomID != false) {
			var act_dom = document.getElementById(this.interfaceDomID);
			act_dom.innerHTML = interfaceString;
		}
		return interfaceString;
	};
	this.addLinkDataEntity = function(){
		alert('ok');
	}
}
