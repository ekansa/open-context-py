
v


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
	other_predicate_field_num = '';
	other_predicate_field_label = '';
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
	"document-text": false,
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
	else if (type == "contains-draft") {
		this.predicate_id = PRED_DRAFT_CONTAINS;
		this.predicate_label = "Containment (Partial Hierarchy)";
		this.title = "Add <strong>Containment</strong> Relation in partial hierarchy";
		this.body = generateContainsBody();
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
	else if (type == "document-text") {
		this.predicate_id = PRED_DOC_Text;
		this.predicate_label = "Has Document Text";
		this.title = "Add <strong>Document Text</strong> [a Document Enity] Relation";
		this.body = generateDocumentTextBody();
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
		checkContainsActionReady(PREDICATE_CONTAINS);
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
	else if (act_interface_type == "document-text") {
		checkDocumentTextReady();
	}
	else if (act_interface_type == "contains-draft") {
		checkContainsActionReady(PRED_DRAFT_CONTAINS);
	}
	else if (act_interface_type == "links-entity") {
		//code
	}
	else {
		checkOtherActionReady();
	}
}



/* --------------------------------------------------------------
 * Interface For "Contains" Relations, or DRAFT CONTAINS relations
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

function checkContainsActionReady(act_contains_predicate){
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
				"<button onclick=\"javascript:addContains('" + act_contains_predicate + "');\" ",
				"type=\"button\" class=\"btn btn-primary\" style=\"margin:1%;\">",
					"<span class=\"glyphicon glyphicon-cloud-upload\" ></span> Save",
				"</button>",
			"</div>"
		].join("\n");
		button_row.innerHTML = rowHTML;
	}
}

function addContains(act_contains_predicate){
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
			predicate: act_contains_predicate,
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
 * Interface For "Document Text" Relations
 * --------------------------------------------------------------
 */
function generateDocumentTextBody(){
	var subjectInterfaceHTML = generateFieldListHTML('subject', ['documents']);
	var objectInterfaceHTML = generateFieldListHTML('object', ['documents']);
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

function checkDocumentTextReady(){
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
				" <strong>Has Document Text</strong> ",
				"<span class=\"glyphicon glyphicon-chevron-right\"></span>",
			"</div>",
			"<div class=\"col-xs-3\">",
				object_label,
			"</div>",
			"<div class=\"col-xs-2\" id=\"action-botton-div\">",
				"<button onclick=\"javascript:addDocumentText();\" type=\"button\" class=\"btn btn-primary\" style=\"margin:1%;\">",
					"<span class=\"glyphicon glyphicon-cloud-upload\" ></span> Save",
				"</button>",
			"</div>"
		].join("\n");
		button_row.innerHTML = rowHTML;
	}
}

function addDocumentText(){
	/* AJAX call to search entities filtered by a search-string */
	var subj_num_domID = "subject" + "-f-num";
	var field_num = document.getElementById(subj_num_domID).value;
	
	var obj_num_domID = "object" + "-f-num";
	var obj_field_num = document.getElementById(obj_num_domID).value;
	
	//Replace action button with an "updating" message
	var act_dom = document.getElementById("action-botton-div");
	act_dom.innerHTML = "Saving 'document text' relation...";
	
	var url = "../../imports/field-annotation-create/" + encodeURIComponent(source_id);
	var req = $.ajax({
		type: "POST",
		url: url,
		dataType: "json",
		data: {
			field_num: field_num,
			predicate: PRED_DOC_Text,
			object_field_num: obj_field_num,
			csrfmiddlewaretoken: csrftoken},
		success: addDocumentTextDone
	});
}

function addDocumentTextDone(data){
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
var other_predicate_field_num = '';
var other_predicate_field_label = '';

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
	if (other_predicate_label.length > 0 || other_predicate_id.length > 0){
		// we've selected something other than a field for the predicate
		other_predicate_field_num = '';
		other_predicate_field_label = '';
	}
	if (other_predicate_label.length > 0) {
		if (other_predicate_id == "-1") {
			show_other_pred_id = "[New / not yet reconciled]";
		}
	}
	else{
		if(other_predicate_field_num.length > 0 && other_predicate_field_label.length > 0){
			show_other_pred_id = 'From values in field: ' + other_predicate_field_num;
			show_other_pred_type = 'Values in ' + other_predicate_field_label;
		}
		else{ 
			show_other_pred_id = "none selected";
			show_other_pred_type = "none selected";
		}
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
	
	if (field_num > 0 && obj_field_num > 0 && (other_predicate_id != "" || other_predicate_field_num != "")) {
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
			show_other_pred_label = other_predicate_field_label + ' (Field: ' + other_predicate_field_num + ')';
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
			predicate_field_num: other_predicate_field_num,
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
	if(sub_obj_type == 'linking'){
		other_predicate_field_num = field_num;
		other_predicate_field_label = label;
		other_predicate_type = 'import-field';
	}
	
	checkActionReady()
}

