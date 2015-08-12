/*
 * ------------------------------------------------------------------
	AJAX for entity searches
 * ------------------------------------------------------------------
*/

function searchEntityObj() {
	/* Object for composing search entities */
	this.name = "ent"; //object name, used for DOM-ID prefixes and object labeling
	this.parent_obj_name = false; //name of the parent object making the search object
	this.search_text_domID = "entity-string";
	this.searchEntityListDomID = "search-entity-list";
	this.selectFoundEntityFunction = "selectEntity";
	this.entities_panel_title = "Entity Lookup";
	this.compact_display = false;
	this.ultra_compact_display = false;
	this.data = false;
	this.limit_class_uri = false;
	this.limit_project_uuid = false;
	this.limit_vocab_uri = false;
	this.limit_item_type = false;
	this.limit_ent_type = false;
	this.limit_context_uuid = false;
	this.limit_data_type = false;
	this.url = make_url("/entities/look-up/");
	this.interfaceDomID = false;
	this.req = false;
	this.selectReadOnly = true;
	this.additionalButton = false;
	this.afterSelectDone = false; // put a function here to execute after a user selects an entity
	this.show_type = false;
	this.show_partof = false;
	this.ids = {}
	this.selected_entity = false
	
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
					 context_html += '<div class="col-xs-10" id="' + this.make_dom_name_id() + '-sel-type"></div>';
					 context_html += '</div>';	
				}
				if (this.show_partof) {
					 context_html += '<div class="row small">';
					 context_html += '<div class="col-xs-2"><label>Part of</label></div>';
					 context_html += '<div class="col-xs-10" id="' + this.make_dom_name_id() + '-sel-partof"></div>';
					 context_html += '</div>';
				}
				context_html += '<div class="row small">';
				context_html += '<div class="col-xs-12"><div style="padding:10px;"></div></div>';
				context_html += '</div>';
		  }
		  var display_style = '';
		  if (this.compact_display) {
				// we want a compact version of this display, so hife the selected entity input fields
				display_style = " style=\"display:none;\" ";
		  }
		if (this.ultra_compact_display) {
		  var interfaceString = [
				"<div>",
					 "<form class=\"form-horizontal\" role=\"form\">",
						  "<div style=\"display:none;\">",
								"<div class=\"form-group form-group-sm\">",
									 "<label for=\"sel-entity-label\" class=\"col-xs-2 control-label\">Label</label>",
									  "<div class=\"col-xs-10\">",
										  "<input id=\"" + this.make_dom_name_id() + "-sel-entity-label\" type=\"text\"  value=\"\" placeholder=\"Select an entity\" class=\"form-control input-sm\" " + this.selectReadOnly + "/>",
									  "</div>",
								  "</div>",
								  "<div class=\"form-group form-group-sm\">",
									  "<label for=\"sel-entity-id\" class=\"col-xs-2 control-label\">ID</label>",
									  "<div class=\"col-xs-10\">",
										  "<input id=\"" + this.make_dom_name_id() + "-sel-entity-id\" type=\"text\"  value=\"\" placeholder=\"Select an entity\" class=\"form-control input-sm\" " + this.selectReadOnly + "/>",
									  "</div>",
								  "</div>",
							 "</div>",
							 context_html,
							 buttonGroupHTML,
							 "<div class=\"form-group form-group-sm\">",
								 "<label for=\"entity-string\" class=\"col-xs-2 control-label\">Search</label>",
								 "<div class=\"col-xs-10\">",
									 "<input id=\"" + this.make_dom_name_id() + "-" + this.search_text_domID + "\" type=\"text\"  value=\"\" onkeydown=\"" + this.make_obj_name_id() + ".searchEntities();\" class=\"form-control input-sm\" />",
								 "</div>",
							 "</div>",
					  "</form>",
					  "<ul id=\"" + this.make_dom_name_id() + "-" + this.searchEntityListDomID + "\">",
					  "</ul>",
				  "</div>",
		  ].join("\n");
		}
		else{
		  var interfaceString = [	
			  "<div class=\"panel panel-default\">",
				  "<div class=\"panel-heading\">",
					  "<h4 class=\"panel-title\">" + this.entities_panel_title + "</h4>",
				  "</div>",
				  "<div class=\"panel-body\">",
					  "<form class=\"form-horizontal\" role=\"form\">",
							 "<div " + display_style + ">",
								  "<div class=\"form-group form-group-sm\">",
									  "<label for=\"sel-entity-label\" class=\"col-xs-2 control-label\">Label</label>",
									  "<div class=\"col-xs-10\">",
										  "<input id=\"" + this.make_dom_name_id() + "-sel-entity-label\" type=\"text\"  value=\"\" placeholder=\"Select an entity\" class=\"form-control input-sm\" " + this.selectReadOnly + "/>",
									  "</div>",
								  "</div>",
								  "<div class=\"form-group form-group-sm\">",
									  "<label for=\"sel-entity-id\" class=\"col-xs-2 control-label\">ID</label>",
									  "<div class=\"col-xs-10\">",
										  "<input id=\"" + this.make_dom_name_id() + "-sel-entity-id\" type=\"text\"  value=\"\" placeholder=\"Select an entity\" class=\"form-control input-sm\" " + this.selectReadOnly + "/>",
									  "</div>",
								  "</div>",
							 "</div>",
							 context_html,
							 buttonGroupHTML,
							 "<div class=\"form-group form-group-sm\">",
								 "<label for=\"entity-string\" class=\"col-xs-2 control-label\">Search</label>",
								 "<div class=\"col-xs-10\">",
									 "<input id=\"" + this.make_dom_name_id() + "-" + this.search_text_domID + "\" type=\"text\"  value=\"\" onkeydown=\"" + this.make_obj_name_id() + ".searchEntities();\" class=\"form-control input-sm\" />",
								 "</div>",
							 "</div>",
					  "</form>",
					  "<ul id=\"" + this.make_dom_name_id() + "-" + this.searchEntityListDomID + "\">",
					  "</ul>",
				  "</div>",
			  "</div>"].join("\n");
		}
		if (this.interfaceDomID != false) {
			var act_dom = document.getElementById(this.interfaceDomID);
			act_dom.innerHTML = interfaceString;
		}
		return interfaceString;
	};
	this.make_dom_name_id = function(){
		  if (this.parent_obj_name != false) {
				// this object is in a parent object
				var dom_name_id = this.parent_obj_name + '.' + this.name;
				dom_name_id = this.replaceAll('.', '_', dom_name_id);
				dom_name_id = this.replaceAll('[', '_', dom_name_id);
				dom_name_id = this.replaceAll(']', '', dom_name_id);
				return dom_name_id;
		  }
		  else{
				return this.name;
		  }
	}
	this.make_obj_name_id = function(){
		  if (this.parent_obj_name != false) {
				// this object is in a parent object
				var obj_name_id = this.parent_obj_name + '.' + this.name;
				return obj_name_id;
		  }
		  else{
				return this.name;
		  }
	}
	 this.searchEntities = function(){
		  this.ids = {}; // clear IDs
		  var url = this.url;
		  var qstring = document.getElementById(this.make_dom_name_id() + "-" + this.search_text_domID).value;
		  var searchEntityListDom = document.getElementById(this.make_dom_name_id() + "-" + this.searchEntityListDomID);
		  if (qstring.length > 0) {
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
				if (this.limit_context_uuid != false) {
				  data['context_uuid'] = this.limit_context_uuid;
				}
				if (this.limit_data_type != false) {
				  data['data_type'] = this.limit_data_type;
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
		  else{
				searchEntityListDom.innerHTML = "";
		  }
		
	}
	 this.searchEntitiesDone = function(data){
		  /* Displays list of entities that meet search criteria */
		  this.data = data;
		  // now display the full list, with a 'false' argument passed
		  // so as not to limit this display to 1 item
		  this.displayEntityListHTML(false);
	 }
	 this.displayEntityListHTML = function(display_only_id){
		  // displays the HTML for entities
		  // found in the search
		  var data = this.data;
		  var searchEntityListDom = document.getElementById(this.make_dom_name_id() + "-" + this.searchEntityListDomID);
		  searchEntityListDom.innerHTML = "";
		  for (var i = 0, length = data.length; i < length; i++) {
				
				if (!('data_type' in data[i])) {
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
					data[i].data_type = data_type;
				}
				var partof = data[i].partOf_label;
				this.ids[data[i].id] = data[i]; // keep in memory for later use
				
				var tooltiplink = [
					'<a onclick="' + this.make_obj_name_id() + '.selectEntity(' + i + ')" ',
					'data-toggle="tooltip" data-placement="bottom" ',
					'style="cursor:pointer;" ',
					'title="Type: ' + data_type + '; part of: ' + partof + '" ',
					'id="' + this.make_dom_name_id() + '-search-entity-label-' + i + '" >',
					data[i].label,
					'</a>'
				].join('');
				
				var newListItem = document.createElement("li");
				newListItem.id = this.make_dom_name_id() + "-search-entity-item-" + i;
				var entityIDdomID = this.make_dom_name_id() + "-search-entity-id-" + i;
				var linkHTML = generateEntityLink(entityIDdomID, data[i].type, data[i].id, data[i].id);
				var entityString = tooltiplink;
				// entityString += "<br/><small id=\"search-entity-id-" + i + "\">" + data[i].id + "</small>";
				entityString += "<br/><small>" + linkHTML + "</small>";
				newListItem.innerHTML = entityString;
				if (this.compact_display && display_only_id != false) {
					 if ( display_only_id == data[i].id) {
						  // display only those that match the id
						  searchEntityListDom.appendChild(newListItem);
					 }
				}
				else{
					 //display all of the search finds
					 searchEntityListDom.appendChild(newListItem);	 
				}
		  }
	
		  // turn on tool tips for these search results
		  $(function () {
				$('[data-toggle="tooltip"]').tooltip();
		  })
	 }
	 this.selectEntity = function(item_num){
		  /* Adds selected entity label and ID to the right dom element */
		  var act_domID = this.make_dom_name_id() + "-search-entity-id-" + item_num;
		  var item_id = document.getElementById(act_domID).innerHTML;
		  var sel_id_dom = document.getElementById(this.make_dom_name_id() + "-sel-entity-id");
		  sel_id_dom.value = item_id;
		  act_domID =  this.make_dom_name_id() + "-search-entity-label-" + item_num;
		  var item_label = document.getElementById(act_domID).innerHTML;
		  var sel_label_dom = document.getElementById(this.make_dom_name_id() + "-sel-entity-label");
		  sel_label_dom.value = item_label;
		  if (item_id in this.ids) {
				this.selected_entity = this.ids[item_id];
		  }
		  if (this.show_type && item_id in this.ids) {
				document.getElementById(this.make_dom_name_id() + "-sel-type").innerHTML = this.ids[item_id].data_type;
		  }
		  if (this.show_partof && item_id in this.ids) {
				document.getElementById(this.make_dom_name_id() + "-sel-partof").innerHTML = this.ids[item_id].partOf_label;
		  }
		  if (this.compact_display) {
				// shrink the search list to only show the item
				// selected
				this.displayEntityListHTML(item_id);
		  }
		  if (this.afterSelectDone != false) {
				// execute a post selection entity is done function
				if (typeof(this.afterSelectDone.exec) !== 'undefined') {
					 if (item_id in this.ids) {
						  this.afterSelectDone.selected_entity = this.ids[item_id];
					 }
					 else{
						  this.afterSelectDone.selected_entity = false;
					 }
					this.afterSelectDone.exec();
				}
		  }
	 }
	 this.replaceAll = function(find, replace, str) {
		   return str.replace(new RegExp(this.escapeRegExp(find), 'g'), replace);
	 }
	 this.escapeRegExp = function (string) {
		  return string.replace(/([.*+?^=!:${}()|\[\]\/\\])/g, "\\$1");
	 }
}


function generateEntityLink(nodeID, entity_type, entity_id, entity_label){
	var linkHTML = "";
	var labelSpan = "<span id=\"" + nodeID + "\">" + entity_label + "</span>";
	if (entity_type != "uri" && entity_type != "import-field" && entity_type != "user-typed-link") {
		var icon = "<span class=\"glyphicon glyphicon-new-window\"></span> ";
		linkHTML = "<a title=\"View in new tab\" href=\"" + make_url("/" + entity_type + "/" + entity_id) + "\" target=\"_blank\">" + icon + labelSpan + "</a>";
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
	this.entities_panel_title = "Add or Edit Linked Data Entity";
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
					"<div class=\"form-horizontal\">",
						"<div class=\"form-group form-group-sm\">",
							"<label for=\"sel-entity-id\" class=\"col-xs-3 control-label\">URI</label>",
							"<div class=\"col-xs-9\">",
								"<input id=\"" + this.name + "-add-entity-id\" ",
								"type=\"text\"  value=\"\" placeholder=\"Add URI\" ",
								"class=\"form-control input-sm\" ",
								"onkeyup=\"" + this.name + ".messageClear()\" />",
							"</div>",
						"</div>",
						"<div class=\"form-group form-group-sm\">",
							"<label for=\"sel-entity-label\" class=\"col-xs-3 control-label\">Label</label>",
							"<div class=\"col-xs-9\">",
								"<input id=\"" + this.name + "-add-entity-label\" ",
								"type=\"text\"  value=\"\" placeholder=\"Add main label\" ",
								"class=\"form-control input-sm\" ",
								"onkeyup=\"" + this.name + ".messageClear()\" />",
							"</div>",
						"</div>",
						"<div class=\"form-group form-group-sm\">",
							"<label for=\"sel-entity-label\" class=\"col-xs-3 control-label\">Alt. Label</label>",
							"<div class=\"col-xs-9\">",
								"<input id=\"" + this.name + "-add-entity-altlabel\" ",
								"type=\"text\"  value=\"\" placeholder=\"Add alternate label\" ",
								"class=\"form-control input-sm\" ",
								"onkeyup=\"" + this.name + ".messageClear()\" />",
							"</div>",
						"</div>",
						"<div class=\"form-group form-group-sm\">",
							"<label for=\"sel-entity-label\" class=\"col-xs-3 control-label\">Vocab. URI</label>",
							"<div class=\"col-xs-9\">",
								"<input id=\"" + this.name + "-add-entity-vocab-uri\" ",
								"type=\"text\"  value=\"\" placeholder=\"Add URI to identify the concept's vocabulary\" ",
								"class=\"form-control input-sm\" ",
								"onkeyup=\"" + this.name + ".messageClear()\" />",
							"</div>",
						"</div>",
						"<div class=\"form-group form-group-sm\" style=\"margin-left:5px;\">",
					
					'<label>URI Entity Type</label><br/>',
					'<label class="radio-inline">',
					'<input type="radio" name="new-ent-type" id="ent-type-prop" ',
					'class="' + this.name + '-new-ent-type" value="property" >',
					'Property </label>',
					'<label class="radio-inline">',
					'<input type="radio" name="new-ent-type" id="ent-type-class" ',
					'class="' + this.name + '-new-ent-type" value="class" checked="checked" />',
					'Class (type) </label>',
					'<label class="radio-inline">',
					'<input type="radio" name="new-ent-type" id="ent-type-vocabulary" ',
					'class="' + this.name + '-new-ent-type" value="vocabulary" />',
					'Vocabulary </label>',

						"</div>",
						buttonGroupHTML,
						"<div class=\"form-group form-group-sm\">",
							"<div class=\"col-xs-12\">",
								'<button class="btn btn-primary" onclick="',
								this.name + '.addUpdateLD();">Add or Update</button>',
							"</div>",
						"</div>",
					"</div>",
					"<div id=\"" + this.name + "-add-update-res\">",
					"</div>",
					"<div class=\"small\">",
					"<p><strong>NOTE:</strong></p>",
					"<p>Each 'property' or 'class' entity needs ",
					"to be part of a URI identified vocabulary. Use this interface to add ",
					"URI identified vocabularies as needed.</p>",
					"<p>You can also use this form to edit and update the labeling of a ",
					"URI identified entity.</p>",
					"</div>",
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
	
	this.messageClear = function() {
		// clears the message area
		var mes_dom = document.getElementById(this.name + "-add-update-res");
		mes_dom.innerHTML = '';
	};
	
	this.addUpdateLD = function() {
		var uri = document.getElementById(this.name + "-add-entity-id").value;
		var label = document.getElementById(this.name + "-add-entity-label").value;
		var alt_label = document.getElementById(this.name + "-add-entity-altlabel").value;
		var vocab_uri = document.getElementById(this.name + "-add-entity-vocab-uri").value;
		var e_types = document.getElementsByClassName(this.name + "-new-ent-type");
		for (var i = 0, length = e_types.length; i < length; i++) {
			if (e_types[i].checked) {
				var ent_type = e_types[i].value;
			}
		}
		var url = make_url("/edit/add-update-ld-entity/");
		if ((uri.length > 0 && label.length > 0)) {
			//code
			return $.ajax({
				type: "POST",
				url: url,
				dataType: "json",
				data: {
					uri: uri,
					label: label,
					alt_label: alt_label,
					ent_type: ent_type,
					vocab_uri: vocab_uri,
					csrfmiddlewaretoken: csrftoken},
				context: this,
				success: this.addUpdateLD_Done
			});
		}
		else {
			alert("Please supply data for fields before submission.");
		}
	}
	this.addUpdateLD_Done = function(data){
		var mes_dom = document.getElementById(this.name + "-add-update-res");
		if (data.ok) {
			// the interaction was a success
			var html = '<div class="alert alert-success" role="alert">';
			html += '<span class="glyphicon glyphicon-ok-sign" aria-hidden="true"></span>';
			html += ' Linked Data entity: ' + data.label + ' (' + data.uri + ') ' + data.action + '.';
			html += '<br/>' + data.change.note;
			html += '</div>';
		}
		else{
			var html = '<div class="alert alert-warning" role="alert">';
			html += '<span class="glyphicon glyphicon-warning-sign" aria-hidden="true"></span>';
			html += ' Linked Data entity: ' + data.label + ' (' + data.uri + ') ' + data.action + '.';
			html += '<br/><p class="small"><strong>Note:</strong> ' + data.change.note + '</p>';
			html += '</div>';
		}
		mes_dom.innerHTML = html;
	}
}

function make_url(relative_url){
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
