
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


function getSubjectsHierarchy() {
	exec_getSubjectsHierarchy().then(get_other_links);
}

function exec_getSubjectsHierarchy() {
	/* Gets the hiearchy of subject entities to be imported,
	 * as modeled by field containment relatinships
	*/
	var url = "../../imports/subjects-hierarchy-examples/" + encodeURIComponent(source_id);
	return $.ajax({
		type: "GET",
		url: url,
		dataType: "json",
		success: getSubjectsHierarchyDone
	});
}

function getSubjectsHierarchyDone(data){
	/* Updates the Hierarchy tree with new JSON data */
	start_data = data;	
	tree_service(data);
}

function get_other_links(data){
	/* Gets the hiearchy of subject entities to be imported,
	 * as modeled by field containment relatinships
	*/
	var url = "../../imports/field-linked-examples/" + encodeURIComponent(source_id);
	var req = $.ajax({
		type: "GET",
		url: url,
		dataType: "json",
		success: get_other_links_Done
	});
}

function get_other_links_Done(data){
	/* Updates the other links display with new JSON data */
	if (data.length > 0) {
		var example_HTML = "";
		for (var i = 0, length = data.length; i < length; i++) {
			example_HTML += generate_example_link_tabHTML(data[i]);
		}
	}
	else{
		var example_HTML = [
			"<div class=\"alert alert-info\" role=\"alert\">",
			"[No descriptions assigned yet]",
			"</div>"
		].join("\n");
	}
	var example_DomID = "other-links-outer";
	var example_dom = document.getElementById(example_DomID);
	example_dom.innerHTML = example_HTML;
}

function generate_example_link_tabHTML(entity){
	var rowsHTML = generate_example_link_rowsHTML(entity);
	var tab_HTML = [
		"<h5>" + entity.label + "</h5>",
		"<table id=\"" + entity.id + "-des-tab\" class=\"table table-condensed table-bordered table-striped\">",
			"<thead>",
				"<th class=\"col-sm-6\">Link Predicate</th>",
				"<th class=\"col-sm-6\">Object(s)</th>",
			"</thead>",
			"<tbody>",
				rowsHTML,
			"</tbody>",
		"</table>",
	].join("\n");
	return tab_HTML;
}

function generate_example_link_rowsHTML(entity){
	var rowsHTML = "";
	for (var i = 0, length = entity.links.length; i < length; i++) {
		var act_link = entity.links[i];
		if (act_link.object != false){
			var valsHTML = act_link.object.label;
			if (valsHTML.length > 144) {
				valsHTML = valsHTML.substring(0, 144) + "...";	
			}
		}
		else{
			var valsHTML = "[Missing object]";
		}
		var rowHTML = [
			"<tr>",
				"<td>" + act_link.predicate.label,
				"</td>",
				"<td>" + valsHTML,
				"</td>",
			"</tr>"
		].join("\n");
		rowsHTML += rowHTML;
	}
	return rowsHTML;
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
		if (anno.predicate.id != 'oc-gen:describes') {
			tbodyDom.appendChild(newRow);
		}
	}
}


var main_modal_title_domID = "myModalLabel";
var main_modal_body_domID = "myModalBody";
var act_interface_type = false;
var interfaces = {
	"contains": false,
	"contained-in": false,			
	"links-field": false,
	"links-entity": false,
	"media-part-of": false,
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
		this.body = generateContainsBody();
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
		this.body = generateLinksFieldsBody();
	}
	else if (type == "links-entity") {
		this.predicate_id = PREDICATE_LINK;
		this.predicate_label = "Links with";
		this.title = "Add <strong>Links with</strong> [an Object Enitty] Relation";
		this.body = "";
	}
	else if (type == "media-part-of") {
		this.predicate_id = PRED_MEDIA_PART_OF;
		this.predicate_label = "Media part of";
		this.title = "Add <strong>Media part of</strong> [a Media Enity] Relation";
		this.body = generateMediaPartOfBody();
	}
	else{
		this.predicate_id = false;
		this.predicate_label = false;
		this.title = "Add <strong>Custom</strong> Linking Relation(s)";
		this.body = generateOtherBody();
	}
}

function addRelInterface(type){
	/* creates a new add annotation relation interface
	 * or calls up a stored one from interfaces
	*/
	act_interface_type = type;
	var title_dom = document.getElementById(main_modal_title_domID);
	var body_dom = document.getElementById(main_modal_body_domID);
	if (interfaces[type] == false || interfaces[type] == null) {
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
		var body_dom = document.getElementById(main_modal_body_domID);
		actInterface.body = body_dom.innerHTML;
		interfaces[act_interface_type] = actInterface;
		getSubjectsHierarchy(); // get hiearchy tree on hiding
	});
	/*
	 * var modal = $("#myModal").modal("show");
	*/
	$("#myModal").modal('show');
}

function checkActionReady(){
	/* Checks if an annoation is ready to go, depending on the type of annotation */
	if (act_interface_type == "contains") {
		checkContainsActionReady();
	}
	else if (act_interface_type == "contained-in") {
		checkContainmentInActionReady();
	}
	else if (act_interface_type == "links-field") {
		checkLinksFieldsReady();
	}
	else if (act_interface_type == "media-part-of") {
		checkMediaPartOfActionReady();
	}
	else if (act_interface_type == "links-entity") {
		//code
	}
	else {
		checkOtherActionReady();
	}
}



/* --------------------------------------------------------------
 * Interface For "Contains" Relations
 * --------------------------------------------------------------
 */
function generateContainsBody(){
	var subjectInterfaceHTML = generateFieldListHTML('subject', ['subjects']);
	var objectInterfaceHTML = generateFieldListHTML('object', ['subjects']);
	var bodyString = [
		"<div class=\"container-fluid\">",
			"<div id=\"action-div\">",	
			"</div>",
			"<div class=\"row\">",	
				"<div class=\"col-xs-6\">",
					subjectInterfaceHTML,
				"</div>",
				"<div class=\"col-xs-6\">",
					objectInterfaceHTML,
				"</div>",
			"</div>",
		"</div>"
	].join("\n");
	return bodyString;
}

function checkContainsActionReady(){
	// Check to see if there's a selected subject field.
	var subj_num_domID = "subject" + "-f-num";
	var field_num = document.getElementById(subj_num_domID).value;
	
	// Check to see if there's a selected parent entity.
	var obj_num_domID = "object" + "-f-num";
	var obj_field_num = document.getElementById(obj_num_domID).value;
	
	if (field_num > 0 && obj_field_num > 0) {
		// We're ready to try to create a 'contained-in' relationship
		var subj_label_domID = "subject" + "-f-label";
		var field_label = document.getElementById(subj_label_domID).value;
		var obj_label_domID = "object" + "-f-label";
		var obj_label_dom = document.getElementById(obj_label_domID);
		var object_label = obj_label_dom.value;
		
		var button_row = document.getElementById("action-div");
		button_row.className = "row alert alert-success";
		var rowHTML = [
			"<div class=\"col-xs-3\">",
				field_label,
			"</div>",
			"<div class=\"col-xs-4\">",
				"<span class=\"glyphicon glyphicon-chevron-right\"></span>",
				" <strong>Contains</strong> ",
				"<span class=\"glyphicon glyphicon-chevron-right\"></span>",
			"</div>",
			"<div class=\"col-xs-3\">",
				object_label,
			"</div>",
			"<div class=\"col-xs-2\" id=\"action-botton-div\">",
				"<button onclick=\"javascript:addContains();\" type=\"button\" class=\"btn btn-primary\" style=\"margin:1%;\">",
					"<span class=\"glyphicon glyphicon-cloud-upload\" ></span> Save",
				"</button>",
			"</div>"
		].join("\n");
		button_row.innerHTML = rowHTML;
	}
}

function addContains(){
	/* AJAX call to search entities filtered by a search-string */
	var subj_num_domID = "subject" + "-f-num";
	var field_num = document.getElementById(subj_num_domID).value;
	
	var obj_num_domID = "object" + "-f-num";
	var obj_field_num = document.getElementById(obj_num_domID).value;
	
	//Replace action button with an "updating" message
	var act_dom = document.getElementById("action-botton-div");
	act_dom.innerHTML = "Saving 'contains' relation...";
	
	var url = "../../imports/field-annotation-create/" + encodeURIComponent(source_id);
	var req = $.ajax({
		type: "POST",
		url: url,
		dataType: "json",
		data: {
			field_num: field_num,
			predicate: PREDICATE_CONTAINS,
			object_field_num: obj_field_num,
			csrfmiddlewaretoken: csrftoken},
		success: addContainsDone
	});
}

function addContainsDone(data){
	/* Finish new relation by showing updated list of annotations */
	$("#myModal").modal("hide");
	displayAnnotations(data);
}



/* --------------------------------------------------------------
 * Interface For "Contained-in" Relations
 * --------------------------------------------------------------
 */
var contextSearchObj = false;
function generateContainedInBody(){
	var entityInterfaceHTML = "";
	var subjectInterfaceHTML = generateFieldListHTML('subject', ['subjects']);
	
	/* changes global contextSearchObj from entities/entities.js */
	contextSearchObj = new searchEntityObj();
	contextSearchObj.name = "contextSearchObj";
	contextSearchObj.entities_panel_title = "Select Parent Entity";
	contextSearchObj.limit_item_type = "subjects";
	contextSearchObj.limit_project_uuid = "0," + project_uuid;
	var afterSelectDone = {
		exec: function(){
				return checkActionReady();
			}
		};
	contextSearchObj.afterSelectDone = afterSelectDone;
	var entityInterfaceHTML = contextSearchObj.generateEntitiesInterface();
	console.log(contextSearchObj);

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

function checkContainmentInActionReady(){
	// Check to see if there's a selected subject field.
	var sel_num_domID = "subject" + "-f-num";
	var act_dom = document.getElementById(sel_num_domID);
	if (act_dom != null) {
		var field_num = act_dom.value;
		// Check to see if there's a selected parent entity.
		var sel_id_dom = document.getElementById("contextSearchObj-sel-entity-id");
		var entity_id = sel_id_dom.value;
	}
	else{
		var field_num = 0;
		var entity_id = false;
	}
	
	if (field_num > 0 && entity_id.length > 0) {
		// We're ready to try to create a 'contained-in' relationship
		var sel_label_domID = "subject" + "-f-label";
		var field_label = document.getElementById(sel_label_domID).value;
		var sel_label_dom = document.getElementById("contextSearchObj-sel-entity-label");
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
	var sel_id_dom = document.getElementById("contextSearchObj-sel-entity-id");
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
			predicate: PREDICATE_CONTAINED_IN,
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
 * Interface For "Links" (fields) Relations
 * --------------------------------------------------------------
 */
function generateLinksFieldsBody(){
	var subjectInterfaceHTML = generateFieldListHTML('subject', DEFAULT_SUBJECT_TYPE_FIELDS);
	var objectInterfaceHTML = generateFieldListHTML('object', DEFAULT_SUBJECT_TYPE_FIELDS);
	var bodyString = [
		"<div class=\"container-fluid\">",
			"<div id=\"action-div\">",	
			"</div>",
			"<div class=\"row\">",	
				"<div class=\"col-xs-6\">",
					subjectInterfaceHTML,
				"</div>",
				"<div class=\"col-xs-6\">",
					objectInterfaceHTML,
				"</div>",
			"</div>",
		"</div>"
	].join("\n");
	return bodyString;
}

function checkLinksFieldsReady(){
	// Check to see if there's a selected subject field.
	var subj_num_domID = "subject" + "-f-num";
	var field_num = document.getElementById(subj_num_domID).value;
	
	// Check to see if there's a selected parent entity.
	var obj_num_domID = "object" + "-f-num";
	var obj_field_num = document.getElementById(obj_num_domID).value;
	
	if (field_num > 0 && obj_field_num > 0) {
		// We're ready to try to create a 'contained-in' relationship
		var subj_label_domID = "subject" + "-f-label";
		var field_label = document.getElementById(subj_label_domID).value;
		var obj_label_domID = "object" + "-f-label";
		var obj_label_dom = document.getElementById(obj_label_domID);
		var object_label = obj_label_dom.value;
		
		var button_row = document.getElementById("action-div");
		button_row.className = "row alert alert-success";
		var rowHTML = [
			"<div class=\"col-xs-3\">",
				field_label,
			"</div>",
			"<div class=\"col-xs-4\">",
				"<span class=\"glyphicon glyphicon-chevron-right\"></span>",
				" <strong>Links with</strong> ",
				"<span class=\"glyphicon glyphicon-chevron-right\"></span>",
			"</div>",
			"<div class=\"col-xs-3\">",
				object_label,
			"</div>",
			"<div class=\"col-xs-2\" id=\"action-botton-div\">",
				"<button onclick=\"javascript:addLinksFields();\" type=\"button\" class=\"btn btn-primary\" style=\"margin:1%;\">",
					"<span class=\"glyphicon glyphicon-cloud-upload\" ></span> Save",
				"</button>",
			"</div>"
		].join("\n");
		button_row.innerHTML = rowHTML;
	}
}

function addLinksFields(){
	/* AJAX call to search entities filtered by a search-string */
	var subj_num_domID = "subject" + "-f-num";
	var field_num = document.getElementById(subj_num_domID).value;
	
	var obj_num_domID = "object" + "-f-num";
	var obj_field_num = document.getElementById(obj_num_domID).value;
	
	//Replace action button with an "updating" message
	var act_dom = document.getElementById("action-botton-div");
	act_dom.innerHTML = "Saving 'contains' relation...";
	
	var url = "../../imports/field-annotation-create/" + encodeURIComponent(source_id);
	var req = $.ajax({
		type: "POST",
		url: url,
		dataType: "json",
		data: {
			field_num: field_num,
			predicate: PREDICATE_LINK,
			object_field_num: obj_field_num,
			csrfmiddlewaretoken: csrftoken},
		success: addLinksFieldsDone
	});
}

function addLinksFieldsDone(data){
	/* Finish new relation by showing updated list of annotations */
	$("#myModal").modal("hide");
	displayAnnotations(data);
}




/* --------------------------------------------------------------
 * Interface For "Media Part of" Relations
 * --------------------------------------------------------------
 */
function generateMediaPartOfBody(){
	var subjectInterfaceHTML = generateFieldListHTML('subject', ['media']);
	var objectInterfaceHTML = generateFieldListHTML('object', ['media']);
	var bodyString = [
		"<div class=\"container-fluid\">",
			"<div id=\"action-div\">",	
			"</div>",
			"<div class=\"row\">",	
				"<div class=\"col-xs-6\">",
					subjectInterfaceHTML,
				"</div>",
				"<div class=\"col-xs-6\">",
					objectInterfaceHTML,
				"</div>",
			"</div>",
		"</div>"
	].join("\n");
	return bodyString;
}

function checkMediaPartOfActionReady(){
	// Check to see if there's a selected subject field.
	var subj_num_domID = "subject" + "-f-num";
	var field_num = document.getElementById(subj_num_domID).value;
	
	// Check to see if there's a selected parent entity.
	var obj_num_domID = "object" + "-f-num";
	var obj_field_num = document.getElementById(obj_num_domID).value;
	
	if (field_num > 0 && obj_field_num > 0) {
		// We're ready to try to create a 'contained-in' relationship
		var subj_label_domID = "subject" + "-f-label";
		var field_label = document.getElementById(subj_label_domID).value;
		var obj_label_domID = "object" + "-f-label";
		var obj_label_dom = document.getElementById(obj_label_domID);
		var object_label = obj_label_dom.value;
		
		var button_row = document.getElementById("action-div");
		button_row.className = "row alert alert-success";
		var rowHTML = [
			"<div class=\"col-xs-3\">",
				field_label,
			"</div>",
			"<div class=\"col-xs-4\">",
				"<span class=\"glyphicon glyphicon-chevron-right\"></span>",
				" <strong>Is a Media Part Of</strong> ",
				"<span class=\"glyphicon glyphicon-chevron-right\"></span>",
			"</div>",
			"<div class=\"col-xs-3\">",
				object_label,
			"</div>",
			"<div class=\"col-xs-2\" id=\"action-botton-div\">",
				"<button onclick=\"javascript:addMediaPartOf();\" type=\"button\" class=\"btn btn-primary\" style=\"margin:1%;\">",
					"<span class=\"glyphicon glyphicon-cloud-upload\" ></span> Save",
				"</button>",
			"</div>"
		].join("\n");
		button_row.innerHTML = rowHTML;
	}
}

function addMediaPartOf(){
	/* AJAX call to search entities filtered by a search-string */
	var subj_num_domID = "subject" + "-f-num";
	var field_num = document.getElementById(subj_num_domID).value;
	
	var obj_num_domID = "object" + "-f-num";
	var obj_field_num = document.getElementById(obj_num_domID).value;
	
	//Replace action button with an "updating" message
	var act_dom = document.getElementById("action-botton-div");
	act_dom.innerHTML = "Saving 'media part of' relation...";
	
	var url = "../../imports/field-annotation-create/" + encodeURIComponent(source_id);
	var req = $.ajax({
		type: "POST",
		url: url,
		dataType: "json",
		data: {
			field_num: field_num,
			predicate: PRED_MEDIA_PART_OF,
			object_field_num: obj_field_num,
			csrfmiddlewaretoken: csrftoken},
		success: addMediaPartOfDone
	});
}

function addMediaPartOfDone(data){
	/* Finish new relation by showing updated list of annotations */
	$("#myModal").modal("hide");
	displayAnnotations(data);
}



/* --------------------------------------------------------------
 * Interface For "Other" Relations
 * --------------------------------------------------------------
 */
var other_predicate_id = '';
var other_predicate_label = '';
var other_predicate_type = '';
function generateOtherBody(){
	var subjectInterfaceHTML = generateFieldListHTML('subject', DEFAULT_SUBJECT_TYPE_FIELDS);
	var objectInterfaceHTML = generateFieldListHTML('object', DEFAULT_SUBJECT_TYPE_FIELDS);
	var predicateHTML = generateOtherLinkPredicateFinalHTML();
	var bodyString = [
		"<div class=\"container-fluid\">",
			"<div id=\"action-div\">",	
			"</div>",
			"<div class=\"row\">",
				"<div class=\"col-xs-6\" id=\"other-predicate-final-show\">",
					predicateHTML,
				"</div>",
				"<div class=\"col-xs-6\">",
					"<button style=\"margin-bottom:1%;\" type=\"button\" class=\"btn btn-info\" onclick=\"javascript:predicateInterface();\">",
						"<span class=\"glyphicon glyphicon-wrench\"></span>",
					" Set-up Custom Linking Relation</button>",
				"</div>",
			"</div>",
			"<div class=\"row\">",	
				"<div class=\"col-xs-6\">",
					subjectInterfaceHTML,
				"</div>",
				"<div class=\"col-xs-6\">",
					objectInterfaceHTML,
				"</div>",
			"</div>",
		"</div>"
	].join("\n");
	return bodyString;
}

function generateOtherLinkPredicateFinalHTML(){
	//Generates HTML for the final selected link predicate
	var show_other_pred_label = other_predicate_label;
	var show_other_pred_id = other_predicate_id;
	var show_other_pred_type = other_predicate_type;
	if (other_predicate_type == 'import-field') {
		show_other_pred_label = 'Field: ' +  other_predicate_id;
	}
	if (other_predicate_label.length > 0) {
		if (other_predicate_id == "-1") {
			show_other_pred_id = "[New / not yet reconciled]";
		}	
	}
	else{
		show_other_pred_id = "none selected";
		show_other_pred_type = "none selected";
	}
	
	if (other_predicate_label.length < 1) {
		var predicateHTML = "Click button on the right to set-up linking relationships.";
	}
	else{
		var predicateHTML = "Selected link relation: " + generateEntityLink('other-predicate-id', other_predicate_type, other_predicate_id, show_other_pred_label);	
	}
	return predicateHTML;
}

function checkOtherActionReady(){
	// Check to see if there's a selected subject field.
	var subj_num_domID = "subject" + "-f-num";
	var field_num = document.getElementById(subj_num_domID).value;
	
	// Check to see if there's a selected parent entity.
	var obj_num_domID = "object" + "-f-num";
	var obj_field_num = document.getElementById(obj_num_domID).value;
	
	if (field_num > 0 && obj_field_num > 0 && other_predicate_id != "") {
		// We're ready to try to create a 'contained-in' relationship
		var subj_label_domID = "subject" + "-f-label";
		var field_label = document.getElementById(subj_label_domID).value;
		var obj_label_domID = "object" + "-f-label";
		var obj_label_dom = document.getElementById(obj_label_domID);
		var object_label = obj_label_dom.value;
		var show_other_pred_label = other_predicate_label;
		var show_other_pred_id = other_predicate_id;
		var show_other_pred_type = other_predicate_type;
		if (other_predicate_type == 'import-field') {
			show_other_pred_label = 'Field: ' +  other_predicate_id;
		}
		if (other_predicate_id == "-1") {
			show_other_pred_type = "[New / not yet reconciled]";
			show_other_pred_id = "[New / not yet reconciled]";
		}	
		
		var button_row = document.getElementById("action-div");
		button_row.className = "row alert alert-success";
		var rowHTML = [
			"<div class=\"col-xs-3\">",
				field_label,
			"</div>",
			"<div class=\"col-xs-1\" style=\"text-align:right;\">",
				"<span class=\"glyphicon glyphicon-chevron-right\"></span>",
			"</div>",
			"<div class=\"col-xs-2\">",
				"<strong>" + show_other_pred_label + "</strong> " + show_other_pred_type + "",
			"</div>",
			"<div class=\"col-xs-1\" style=\"text-align:left;\">",
				"<span class=\"glyphicon glyphicon-chevron-right\"></span>",
			"</div>",
			"<div class=\"col-xs-3\">",
				object_label,
			"</div>",
			"<div class=\"col-xs-2\" id=\"action-botton-div\">",
				"<button onclick=\"javascript:addOther();\" type=\"button\" class=\"btn btn-primary\" style=\"margin:1%;\">",
					"<span class=\"glyphicon glyphicon-cloud-upload\" ></span> Save",
				"</button>",
			"</div>"
		].join("\n");
		button_row.innerHTML = rowHTML;
	}
	else{
		// alert('crap: ' + field_num+ " : " + obj_field_num + " : " + other_predicate_id);
	}
}

function addOther(){
	/* AJAX call to search entities filtered by a search-string */
	var subj_num_domID = "subject" + "-f-num";
	var field_num = document.getElementById(subj_num_domID).value;
	
	var obj_num_domID = "object" + "-f-num";
	var obj_field_num = document.getElementById(obj_num_domID).value;
	
	//Replace action button with an "updating" message
	var act_dom = document.getElementById("action-botton-div");
	act_dom.innerHTML = "Saving this relation...";
	
	var url = "../../imports/field-annotation-create/" + encodeURIComponent(source_id);
	var req = $.ajax({
		type: "POST",
		url: url,
		dataType: "json",
		data: {
			field_num: field_num,
			predicate: other_predicate_id,
			predicate_label: other_predicate_label,
			predicate_type: other_predicate_type,
			object_field_num: obj_field_num,
			csrfmiddlewaretoken: csrftoken},
		success: addOtherDone
	});
}

function addOtherDone(data){
	/* Finish new relation by showing updated list of annotations */
	$("#myModal").modal("hide");
	displayAnnotations(data);
}



/* ----------------------------------------------------------------
 * (Other) Predicate Interface
 * ----------------------------------------------------------------*/
var pred_modal_title_domID = "myModalLabel_b";
var pred_modal_body_domID = "myModalBody_b";
function predicateInterface(){
	/* creates a new add interface to select a custom
	 * linking relation predicate
	*/
	
	var title_dom = document.getElementById(pred_modal_title_domID);
	var body_dom = document.getElementById(pred_modal_body_domID);
	title_dom.innerHTML = "Add Custom Linking Relation Predicate";
	body_dom.innerHTML = generateOtherPredicateBody();
	$('#myModal_b').on('hide.bs.modal', function(){
		
	});

	$("#myModal_b").modal("show");
}

var predSearchObj = false;
function generateOtherPredicateBody(){
	var fieldInterfaceHTML = generateFieldListHTML('linking', ['relation']);
	var predicateHTML = generateSelectedCustomPredicateHTML();
	
	/* Entity search object from entities/entities.js */
	var additionalButton = {label: "Select",
		funct: "useSelectedLinkEnity()",
		icon: "glyphicon glyphicon-check",
		buttonID: "predSearchObj-sel-entity-use-button",
		buttonClass: "btn btn-info",
		buttonText: "Use the above Link Relation",
		buttonDisabled: true
	}
	predSearchObj = new searchEntityObj();
	predSearchObj.name = "predSearchObj";
	predSearchObj.entities_panel_title = "Select Link Relation Concept";
	predSearchObj.limit_item_type = "predicates";
	predSearchObj.limit_class_uri = "link";
	predSearchObj.limit_project_uuid = "0," + project_uuid;
	predSearchObj.selectReadOnly = true;
	predSearchObj.additionalButton = additionalButton;
	var afterSelectDone = {
		exec: function(){
				document.getElementById("predSearchObj-sel-entity-use-button").disabled = "";
				return checkActionReady();
			}
		};
	predSearchObj.afterSelectDone = afterSelectDone;
	var entityInterfaceHTML = predSearchObj.generateEntitiesInterface();
	console.log(predSearchObj);

	var bodyString = [
		"<div class=\"container-fluid\">",
			"<div id=\"action-div\">",	
			"</div>",
			"<div class=\"row\" style=\"padding-bottom:1%;\" id=\"other-predicate-interface-outer\">",
				predicateHTML,
			"</div>",
			"<div class=\"row\">",	
				"<div class=\"col-xs-6\">",
					fieldInterfaceHTML,
				"</div>",
				"<div class=\"col-xs-6\">",
					entityInterfaceHTML,
				"</div>",
			"</div>",
		"</div>"
	].join("\n");
	return bodyString;
}

function generateSelectedCustomPredicateHTML(){
	// Generates Selected Custom Predicate HTML
	var show_other_pred_label = other_predicate_label;
	var show_other_pred_id = other_predicate_id;
	var show_other_pred_type = other_predicate_type;
	if (other_predicate_type == 'import-field') {
		show_other_pred_label = 'Field: ' +  other_predicate_id;
	}
	if (other_predicate_label.length > 0) {
		if (other_predicate_id == "-1") {
			show_other_pred_id = "[New / not yet reconciled]";
		}	
	}
	else{
		show_other_pred_id = "none selected";
		show_other_pred_type = "none selected";
	}
	
	var predicateHTML = [
			"<div class=\"col-xs-4\">",
				"Selected Link/Relation (type for new): ",
				"<input onchange=\"javascript:newLinkPredicateLabel();\" id=\"custom-predicate-label\" value=\"" + show_other_pred_label + "\" type=\"\"/>",
			"</div>",
			"<div class=\"col-xs-4\">",
				"Selected Link/Relation ID: <input id=\"custom-predicate-id\" value=\"" + show_other_pred_id + "\" type=\"\"/>",
			"</div>",
			"<div class=\"col-xs-4\">",
				"Selected Link/Relation Type:<br/><span id=\"custom-predicate-type\">" + show_other_pred_type + "</span>",
			"</div>"
		].join("\n");
	return predicateHTML;
}


var doNewLinkPredicateLabel = true;
function useSelectedLinkEnity(){
	// Action to use a predicate entity, either previously selected from a list
	// if a list is not chosen, use the search string and note it is for a new entity
	
	//set doNewLinkPredicateLabel as false, so the change does not trigger the 
	//newLinkPredicateLabel() function
	doNewLinkPredicateLabel = false;
	
	other_predicate_label = document.getElementById("predSearchObj-sel-entity-label").value;
	other_predicate_id = document.getElementById("predSearchObj-sel-entity-id").value;
	other_predicate_type = "predicates";
	var predicateHTML = generateSelectedCustomPredicateHTML();
	document.getElementById("other-predicate-interface-outer").innerHTML = predicateHTML;
	var finalPredicateHTML = generateOtherLinkPredicateFinalHTML();
	document.getElementById("other-predicate-final-show").innerHTML = finalPredicateHTML;
	doNewLinkPredicateLabel = true;
	checkActionReady();
}

function newLinkPredicateLabel(){
	// Action to use a predicate entity, either previously selected from a list
	// if a list is not chosen, use the search string and note it is for a new entity
	if (doNewLinkPredicateLabel) {
		//only do this if doNewLinkPredicateLabel is true, so as not to get messed up by
		//selecting a link entity from the entity list
		other_predicate_label = document.getElementById("custom-predicate-label").value;
		other_predicate_id = -1;
		other_predicate_type = "user-typed-link";
		var predicateHTML = generateSelectedCustomPredicateHTML();
		document.getElementById("other-predicate-interface-outer").innerHTML = predicateHTML;
		var finalPredicateHTML = generateOtherLinkPredicateFinalHTML();
		document.getElementById("other-predicate-final-show").innerHTML = finalPredicateHTML;
		checkActionReady();
	}
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


/* --------------------------------------------------------------
 * Field selection function
 * --------------------------------------------------------------
 */
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

