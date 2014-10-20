var start_data = [{label: 'Containment Hierarchy'}];
var tree_app;
var tree_service;
var act_tree_root = false;
(function() {
	/* Sets up the Tree view for browsing hierarchies of entity categories */
	var app;
	var deps;
	deps = ['angularBootstrapNavTree'];
	if (angular.version.full.indexOf("1.2") >= 0) {
	  deps.push('ngAnimate');
	}
	app = angular.module('TreeApp', deps);
	tree_app = app.controller('TreeController', function($scope, $timeout) {
		$scope.my_tree_handler = function(branch) {
			if (branch.id != null) {	
				var act_domID = "tree-sel-label";
				var act_dom = document.getElementById(act_domID);
				act_dom.innerHTML = branch.label;
				var act_domID = "tree-sel-id";
				var act_dom = document.getElementById(act_domID);
				act_dom.innerHTML = branch.id;
				if (branch.icon != false) {
					var act_domID = "tree-sel-icon";
					var act_dom = document.getElementById(act_domID);
					act_dom.innerHTML = "<img src=\"" + branch.icon + "\" alt=\"Icon\"/>";
				}
			}
			else{
				var act_domID = "tree-sel-label";
				var act_dom = document.getElementById(act_domID);
				act_dom.innerHTML = "Select a field first.";
			}
		};
		$scope.tree_data = start_data;
		$scope.tree_service = function(data) {
			$scope.tree_data = [];
			$scope.doing_async = true;
			return $timeout(function() {
			  $scope.tree_data = data;
			  $scope.doing_async = false;
			}, 1000);
		};
		tree_service = $scope.tree_service;
	});
	
}).call(this);

function getTypeHierarchyDone(data){
	/* Updates the Hierarchy tree with new JSON data */
	tree_service(data)
	var act_domID = "tree-sel-label";
	var act_dom = document.getElementById(act_domID);
	act_dom.innerHTML = "";
}



/* ----------------------------------------------------
 * Functions to DELETE field annotations
 *
 * ----------------------------------------------------
*/

function deleteAnnotation(annotation_id){
	/* AJAX call delete a specific annotation */
	var url = "../../imports/field-annotation-delete/" + encodeURIComponent(source_id) + "/" + annotation_id;
	var req = $.ajax({
		type: "POST",
		url: url,
		dataType: "json",
		data: {csrfmiddlewaretoken: csrftoken},
		success: deleteAnnotationDone
	});
}

function deleteAnnotationDone(data){
	/* Finish delete by showing updated list of annotations */
	displayAnnotations(data);
}





/* ----------------------------------------------------
 * Functions to add annotations to fields
 *
 * ----------------------------------------------------
*/

function displayAnnotations(data){
	/* Displays annotations after updates, data is JSON data from AJAX response */
	var tbodyDom = document.getElementById("fieldAnnotationsTbody");
	tbodyDom.innerHTML = "";
	for (var i = 0, length = data.length; i < length; i++) {
		var anno = data[i];
		var newRow = document.createElement("tr");
		newRow.id = "anno-num-" + anno.id;
		var obj_id_link = anno.object.id; //default, no link
		var entityIDdomID = "obj-id-" + anno.id;
		var linkHTML = generateEntityLink(entityIDdomID, anno.object.type, anno.object.id, anno.object.id);
		var rowString = [
			"<td>",
			"<button onclick=\"javascript:deleteAnnotation(" + anno.id +" );\" type=\"button\" class=\"btn btn-warning btn-xs\">",
			"<span class=\"glyphicon glyphicon-remove\"></span>",
			"</button>",
			"</td>",
			"<td>",
			"<span id=\"sub-label-" + anno.id +"\">" + anno.subject.label + "</span>",
			"<br/>",
			"<samp>",
			"<small>Import field</small>",
			"<small id=\"sub-id-" + anno.id + "\">" + anno.subject.id + "</small>",
			"</samp>",
			"</td>",
			"<td>",
			"<span id=\"pred-label-" + anno.id +"\">" + anno.predicate.label + "</span>",
			"<br/>",
			"<samp>",
			"<small id=\"pred-id-" + anno.id + "\">" + anno.predicate.id + "</small>",
			"</samp>",
			"</td>",
			"<td>",
			"<span id=\"obj-label-" + anno.id + "\">" + anno.object.label + "</span>",
			"<br/>",
			"<samp>",
			"<small id=\"obj-type-" + anno.id + "\">" + anno.object.type + "</small>",
			"<small id=\"obj-outer-id-" + anno.id + "\">" + linkHTML + "</small>",
			"</samp>",
			"</td>"
		].join("\n");
		newRow.innerHTML = rowString;
		tbodyDom.appendChild(newRow);
	}
}


var title_domID = "myModalLabel";
var model_bodyDomID = "myModalBody";
var act_interface_type = false;
var interfaces = {
	"contains": false,
	"contained-in": false,			
	"links-field": false,
	"links-entity": false,
	"other": false
	};
var field_data = [];

function relationInterface(type){
	/* object for making interfaces of different types */
	this.type = type;
	if (type == "contains") {
		this.predicate_id = PREDICATE_CONTAINS;
		this.predicate_label = "Containment";
		this.title = "Add <strong>Containment</strong> Relation";
		this.body = "";
	}
	else if (type == "contained-in") {
		this.predicate_id = PREDICATE_CONTAINED_IN;
		this.predicate_label = "Contained in";
		this.title = "Add <strong>Contained in</strong> [a subject entity] Relation";
		this.body = generateContainedInBody();
	}
	else if (type == "links-field") {
		this.predicate_id = PREDICATE_LINK;
		this.predicate_label = "Links with";
		this.title = "Add <strong>Links with</strong> [an Object Field] Relation";
		this.body = "";
	}
	else if (type == "links-entity") {
		this.predicate_id = PREDICATE_LINK;
		this.predicate_label = "Links with";
		this.title = "Add <strong>Links with</strong> [an Object Enitty] Relation";
		this.body = "";
	}
	else{
		this.predicate_id = false;
		this.predicate_label = false;
		this.title = "Go away and never come back";
		this.body = "";
	}
}

function addRelInterface(type){
	/* creates a new add annotation relation interface
	 * or calls up a stored one from interfaces
	*/
	act_interface_type = type;
	var title_dom = document.getElementById(title_domID);
	var body_dom = document.getElementById(model_bodyDomID);
	if (interfaces[type] == false) {
		var actInterface = new relationInterface(type);
		interfaces[type] = actInterface; 
	}
	else{
		var actInterface = interfaces[type];
	}
	title_dom.innerHTML = actInterface.title;
	body_dom.innerHTML = actInterface.body;
	$('#myModal').on('hide.bs.modal', function(){
		var actInterface = interfaces[act_interface_type];
		var body_dom = document.getElementById(model_bodyDomID);
		actInterface.body = body_dom.innerHTML;
		interfaces[act_interface_type] = actInterface; 
	});
	/*
	 * var modal = $("#myModal").modal("show");
	*/
	$("#myModal").modal("show");
}

function checkActionReady(){
	/* Checks if an annoation is ready to go, depending on the type of annotation */
	if (act_interface_type == "contains") {
		//code
	}
	else if (act_interface_type == "contained-in") {
		checkContainmentInActionReady();
	}
	else if (act_interface_type == "links-field") {
		//code
	}
	else if (act_interface_type == "links-entity") {
		//code
	}
	else {
		//code
	}
}



/* --------------------------------------------------------------
 * Interface For "Contained-in" Relations
 * --------------------------------------------------------------
 */
function generateContainedInBody(){
	/* Generates the HTML for the Contained In interface body */
	var predicateHTML = generateAddPredicateHTML("oc-gen:contained-in", "Contained in");
	
	/* changes global varaiables from entities.js */
	entities_panel_title = "Select Parent Entity";
	limit_item_type = "subjects";
	selectFoundEntityFunction = "selectParentEntity";
	var subjectInterfaceHTML = generateFieldListHTML('subject', ['subjects']);
	var entityInterfaceHTML = generateEntitiesInterface("");
	var bodyString = [
		"<div class=\"container-fluid\">",
			"<div id=\"action-div\">",	
			"</div>",
			"<div class=\"row\">",	
				"<div class=\"col-xs-6\">",
					subjectInterfaceHTML,
				"</div>",
				"<div class=\"col-xs-6\">",
					entityInterfaceHTML,
				"</div>",
			"</div>",
		"</div>"
	].join("\n");
	return bodyString;
}

function selectParentEntity(item_num) {
	/* Adds selected entity label and ID to the right dom element */
	var act_domID = "search-entity-id-" + item_num;
	var item_id = document.getElementById(act_domID).innerHTML;
	var sel_id_dom = document.getElementById("sel-entity-id");
	sel_id_dom.value = item_id;
	act_domID =  "search-entity-label-" + item_num;
	var item_label = document.getElementById(act_domID).innerHTML;
	var sel_label_dom = document.getElementById("sel-entity-label");
	sel_label_dom.value = item_label;
	checkActionReady();
}

function checkContainmentInActionReady(){
	// Check to see if there's a selected subject field.
	var sel_num_domID = "subject" + "-f-num";
	var field_num = document.getElementById(sel_num_domID).value;
	
	// Check to see if there's a selected parent entity.
	var sel_id_dom = document.getElementById("sel-entity-id");
	var entity_id = sel_id_dom.value;
	
	if (field_num > 0 && entity_id.length > 0) {
		// We're ready to try to create a 'contained-in' relationship
		var sel_label_domID = "subject" + "-f-label";
		var field_label = document.getElementById(sel_label_domID).value;
		var sel_label_dom = document.getElementById("sel-entity-label");
		var entity_label = sel_label_dom.value;
		
		var button_row = document.getElementById("action-div");
		button_row.className = "row alert alert-success";
		var rowHTML = [
			"<div class=\"col-xs-3\">",
				field_label,
			"</div>",
			"<div class=\"col-xs-4\">",
				"<span class=\"glyphicon glyphicon-chevron-right\"></span>",
				" is <strong>Contained in</strong> ",
				"<span class=\"glyphicon glyphicon-chevron-right\"></span>",
			"</div>",
			"<div class=\"col-xs-3\">",
				entity_label,
			"</div>",
			"<div class=\"col-xs-2\" id=\"action-botton-div\">",
				"<button onclick=\"javascript:addContainedIn();\" type=\"button\" class=\"btn btn-primary\" style=\"margin:1%;\">",
					"<span class=\"glyphicon glyphicon-cloud-upload\" ></span> Save",
				"</button>",
			"</div>"
		].join("\n");
		button_row.innerHTML = rowHTML;
	}
}

function addContainedIn(){
	/* AJAX call to search entities filtered by a search-string */
	var sel_num_domID = "subject" + "-f-num";
	var field_num = document.getElementById(sel_num_domID).value;
	
	// Check to see if there's a selected parent entity.
	var sel_id_dom = document.getElementById("sel-entity-id");
	var entity_id = sel_id_dom.value;
	
	//Replace action button with an "updating" message
	var act_dom = document.getElementById("action-botton-div");
	act_dom.innerHTML = "Saving 'contained-in' relation...";
	
	var url = "../../imports/field-annotation-create/" + encodeURIComponent(source_id);
	var req = $.ajax({
		type: "POST",
		url: url,
		dataType: "json",
		data: {
			field_num: field_num,
			predicate_rel: PREDICATE_CONTAINED_IN,
			object_uuid: entity_id,
			csrfmiddlewaretoken: csrftoken},
		success: addContainedInDone
	});
}

function addContainedInDone(data){
	/* Finish new relation by showing updated list of annotations */
	$("#myModal").modal("hide");
	displayAnnotations(data);
}











/* --------------------------------------------------------------
 * Interface HTML Snippet Generation
 * --------------------------------------------------------------
 */

function generateAddPredicateHTML(predicate_id, predicate_label){
	/* Makes a snippett of HTML for the active predicate used to make an annotion */
	var predicateHTML = [
		"<span id=\"add-pred-label\">" + predicate_label + "</span>",
		"<br/>",
		"<samp>",
		"<small id=\"add-pred-id\">" + predicate_id + "</small>",
		"</samp>"].join("\n");
	return predicateHTML;
}

function generateFieldListHTML(sub_obj_type, field_type_limits){
	/* Makes a snippett of HTML for a field list used as either a subject or object */
	
	if (sub_obj_type == "subject") {
		var panelTitle = "Relationship Subject Field";
	}
	else{
		var panelTitle = "Relationship Object Field";
	}
	var main_DomID = sub_obj_type + "-field-interfacce";
	var tbody_DomID = sub_obj_type + "-Tbody";
	var rowsHTML = generateFieldListRowsHTML(sub_obj_type, field_type_limits);
	var mainHTML = [
		"<div class=\"panel panel-default\">",
			"<div class=\"panel-heading\">",
				"<h4 class=\"panel-title\">" + panelTitle + "</h4>",
			"</div>",
			"<div class=\"panel-body\">",
				"<form class=\"form-horizontal\" role=\"form\">",
					"<div class=\"form-group form-group-sm\">",
						"<label for=\"" + sub_obj_type + "-f-label\" class=\"col-xs-2 control-label\">Label</label>",
						"<div class=\"col-xs-10\">",
							"<input id=\"" + sub_obj_type + "-f-label\" type=\"text\"  value=\"\" placeholder=\"Select a field\" class=\"form-control input-sm\" />",
						"</div>",
					"</div>",
					"<div class=\"form-group form-group-sm\">",
						"<label for=\"" + sub_obj_type + "-f-num\" class=\"col-xs-2 control-label\">Field#</label>",
						"<div class=\"col-xs-10\">",
							"<input id=\"" + sub_obj_type + "-f-num\" type=\"text\"  value=\"\" placeholder=\"Select a field\" class=\"form-control input-sm\" />",
						"</div>",
					"</div>",
				"</form>",
				"<table id=\"" + sub_obj_type + "-fieldsTable\" class=\"table table-condensed table-hover\">",
					"<thead>",
						"<th class=\"col-sm-1\">Field</th>",
						"<th class=\"col-sm-11\">Label</th>",
					"</thead>",
					"<tbody id=\"" + tbody_DomID + "\">",
						rowsHTML,
					"</tbody>",
				"</table>",
			"</div>",
		"</div>"
	].join("\n");
	return mainHTML;
}

function generateFieldListRowsHTML(sub_obj_type, field_type_limits){
	/* Makes a snippett of HTML for rows of a field list used as either a subject or object */
	var rows = [];
	for (var i = 0, length = field_data.length; i < length; i++) {
		field = field_data[i];
		var use_field = false;
		if (field_type_limits[0] == 'none') {
			// don't limit by field_type
			use_field = true;
		}
		else{
			// limit by a list of allowed field types, check if in that list
			if (field_type_limits.indexOf(field.field_type) >= 0) {
				use_field = true;
			}
		}
		if (use_field) {
			var row_id = sub_obj_type + "-field-num-" + field.field_num;
			var label_id = sub_obj_type + "-field-label-" + field.field_num;
			rowHTML = [
				"<tr id=\"" + row_id  + "\">",
					"<td>",
						field.field_num,	
					"</td>",
					"<td>",
						"<a id=\"" + label_id + "\" href=\"javascript:selectField('" + sub_obj_type + "'," + field.field_num + ");\">" + field.label + "</a>",	
					"</td>",
				"</tr>"
			].join("\n");
			rows.push(rowHTML);
		}
	}
	var rowsHTML = rows.join("\n"); 
	return rowsHTML;
}

function selectField(sub_obj_type, field_num){
	/* Selects a field to use as either a subject or an object field */
	var label_domID = sub_obj_type + "-field-label-" + field_num;
	var label = document.getElementById(label_domID).innerHTML;
	var sel_label_domID = sub_obj_type + "-f-label";
	document.getElementById(sel_label_domID).value = label;
	var sel_num_domID = sub_obj_type + "-f-num";
	document.getElementById(sel_num_domID).value = field_num;
	checkActionReady()
}




/* ----------------------------------------------------
 * AJAX to load up fields
 *
 * ----------------------------------------------------
*/

function get_field_data(){
	/* AJAX to get field data */
	var url = "../../imports/field-list/" + encodeURIComponent(source_id);
	var req = $.ajax({
		type: "GET",
		url: url,
		dataType: "json",
		success: get_field_data_Done
	});
}

function get_field_data_Done(data){
	/* Stores field data in the global 'field_list' */
	for (var i = 0, length = data.length; i < length; i++) {
		field_data.push(data[i]);
	}
}
