function source_dialogue(id){
	addInterface('source', id);
}
function refine_dialogue(id){
	addInterface('refine', id);
}


var main_modal_title_domID = "myModalLabel";
var main_modal_body_domID = "myModalBody";
var act_interface_type = false;

function datasetInterface(type, id){
	/* object for making interfaces of different types */
	this.type = type;
	if (type == "source") {
		this.title = "Modify Import Already Loaded from Refine";
		this.body = generateSourceBody(id);
	}
	else if (type == "refine") {
		this.title = "Import New Dataset from Refine";
		this.body = generateRefineBody(id);
	}
	else{
		this.title = "God knows what you Want";
		this.body = "??";
	}
}

function addInterface(type, id){
	/* creates a new inferface
	*/
	act_interface_type = type;
	var title_dom = document.getElementById(main_modal_title_domID);
	var body_dom = document.getElementById(main_modal_body_domID);
	var actInterface = new datasetInterface(type, id);
	title_dom.innerHTML = actInterface.title;
	body_dom.innerHTML = actInterface.body;
	$("#myModal").modal("show");
}



/* --------------------------------------------------------------
 * Interface For "Source" Modifications
 * --------------------------------------------------------------
 */
function generateSourceBody(id){
	var act_dom_id = "source-label-" + id;
	var label = document.getElementById(act_dom_id).innerHTML;
	var act_dom_id = "source-id-" + id;
	var source_id = document.getElementById(act_dom_id).innerHTML;
	var act_dom_id = "source-status-" + id;
	var status = document.getElementById(act_dom_id).innerHTML;
	status = status.toLowerCase();
	var act_dom_id = "source-refine-" + id;
	var refine_id = document.getElementById(act_dom_id).innerHTML;
	refine_id = refine_id.toLowerCase();
	if (refine_id == "false") {
		refine_id = false;
	}
	var act_dom_id = "source-undo-" + id;
	var undo = document.getElementById(act_dom_id).innerHTML;
	undo = undo.toLowerCase();
	if (undo == "true") {
		undo = true;
	}
	else{
		undo = false;
	}
	var prep_html = make_prepare_controlHTML(source_id);
	var reload_html = make_reload_controlHTML(undo, refine_id, status, source_id);
	if (status == "done") {
		var undo_html =  make_undo_controlHTML(undo, source_id);
		var unload_html = make_unload_controlHTML(undo, source_id);
	}
	else{
		var undo_html =  "";
		var unload_html = "";
	}
	var bodyString = [
		"<div class=\"container-fluid\">",
			"<div id=\"action-div\">",	
			"</div>",
			"<div class=\"row\">",	
				"<div class=\"col-xs-6\">",
					"<h4>Options:</h4>",
					"<div class=\"row\">",
						"<div class=\"col-xs-6\">",
							
						"</div>",
						"<div class=\"col-xs-6\">",
						
						"</div>",
					"</div>",
					prep_html,
					undo_html,
					reload_html,
					unload_html,
				"</div>",
				"<div class=\"col-xs-6\">",
					"<h4>"+ label + "</h4>",
					"<p>This source has already been loaded from Refine.</p>",
				"</div>",
			"</div>",
		"</div>"
	].join("\n");
	return bodyString;
}

/* Makes HTML for button to prepare an import */
function make_prepare_controlHTML(source_id){
	var html = [
		"<div class=\"row\" style=\"padding-bottom:2%;\" >",
			"<div class=\"col-xs-3\">",
				"<a href=\"../../imports/field-types/" + source_id + "\">",
				"<button title=\"Prepare this import\"",
                "type=\"button\" class=\"col-xs-12 btn btn-info\">",
                "Prepare",
                "</button>",
				"</a>",
			"</div>",
			"<div class=\"col-xs-9\">",
				"<small>Prepare these data for import through description and schema mapping.</small>",	
			"</div>",
		"</div>"
		].join("\n");
	return html;
}

/* Makes HTML for button to undo an import */
function make_undo_controlHTML(undo, source_id){
	if (undo) {
		var html = [
		"<div class=\"row\" style=\"padding-bottom:2%;\" >",
			"<div class=\"col-xs-3\">",
				"<button title=\"Undo this import\"",
                "onclick=\"javascript:undo_import('" + source_id + "');\"",
                "type=\"button\" class=\"col-xs-12 btn btn-warning\">",
                "Undo",
                "</button>",			
			"</div>",
			"<div class=\"col-xs-9\">",
				"<small>Removes entities imported to Open Context from this source</small>",	
			"</div>",
		"</div>"
		].join("\n");
	}
	else{
		var html = [
		"<div class=\"row\" style=\"padding-bottom:2%;\">",
			"<div class=\"col-xs-3\">",
				"<button title=\"Undo this import\"",
                "disabled=\"disabled\"",
                "type=\"button\" class=\"col-xs-12 btn btn-warning\">",
                "Undo",
                "</button>",			
			"</div>",
			"<div class=\"col-xs-9\">",
				"<small>Cannot remove entities imported to Open Context ",
				"because of potential dependencies with later imports. ",
				"Please undo later imports first.",
				"</small>",	
			"</div>",
		"</div>"
		].join("\n");
	}
	return html;
}

/* Makes HTML for button to reload an import */
function make_reload_controlHTML(undo, refine_id, status, source_id){
	if (status == "done") {
		var a_html = "Removes entities already imported to Open Context from this source.";
		var b_html = "Reloads records staged for import from Refine. Prior descriptions and schema mappings will be retained.";
	}
	else{
		var a_html = "Reloads records staged for import from Refine for this source.";
		var b_html = "Prior descriptions and schema mappings will be retained."
	}
	if (!undo) {
		var d_a_html = "Cannot remove entities imported to Open Context and update staged records from Refine because of potential dependencies with later imports"
	}
	else{
		var d_a_html = "";
	}
	if (!refine_id) {
		d_a_html += "Please turn on Refine to activate this option. ";
	}
	if (undo && refine_id != false) {
		var html = [
		"<div class=\"row\" style=\"padding-bottom:2%;\">",
			"<div class=\"col-xs-3\">",
				"<button title=\"Reload from refine\"",
                "onclick=\"javascript:reload_import('" + source_id + "');\"",
                "type=\"button\" class=\"col-xs-12 btn btn-warning\">",
                "Reload",
                "</button>",			
			"</div>",
			"<div class=\"col-xs-9\">",
				"<small>Reloads data from Refine. This undoes any prior imports from this source:</small>",
				"<ol>",
				"<li><small>" + a_html + "</small></li>",
				"<li><small>" + b_html + "</small></li>",
				"</ol>",
			"</div>",
		"</div>"
		].join("\n");
	}
	else{
		var html = [
		"<div class=\"row\" style=\"padding-bottom:2%;\">",
			"<div class=\"col-xs-3\">",
				"<button title=\"Reload from refine\"",
                "disabled=\"disabled\"",
                "type=\"button\" class=\"col-xs-12 btn btn-warning\">",
                "Reload",
                "</button>",			
			"</div>",
			"<div class=\"col-xs-9\">",
				"<small>",
				d_a_html,
				"</small>",
			"</div>",
		"</div>"
		].join("\n");
	}
	return html;
}

/* Makes HTML control to delete an import */
function make_unload_controlHTML(undo, source_id){
	if (undo == "True") {
		var html = [
		"<div class=\"row\" style=\"padding-bottom:2%;\" >",
			"<div class=\"col-xs-3\">",
				"<button title=\"Delete + unload this import\"",
                "onclick=\"javascript:undo_import('" + source_id + "');\"",
                "type=\"button\" class=\"col-xs-12 btn btn-danger\">",
                "Delete",
                "</button>",			
			"</div>",
			"<div class=\"col-xs-9\">",
				"<small>A more dramatic undo. This also deletes preparations for an import:</small>",
				"<ol>",
				"<li><small>Removes entities imported to Open Context from this source.</small></li>",
				"<li><small>Deletes all records staged for import, ",
				"along with deleting descriptions and schema mappings.</small></li>",
				"</ol>",
			"</div>",
		"</div>"
		].join("\n");
	}
	else{
		var html = [
		"<div class=\"row\" style=\"padding-bottom:2%;\" >",
			"<div class=\"col-xs-3\">",
				"<button title=\"Delete + unload this import\"",
                "disabled=\"disabled\"",
                "type=\"button\" class=\"col-xs-12 btn btn-danger\">",
                "Delete",
                "</button>",			
			"</div>",
			"<div class=\"col-xs-9\">",
				"<small>Cannot remove entities imported to Open Context or delete staged records for import ",
				"because of potential dependencies with later imports. ",
				"Please undo / delete later imports first.",
				"</small>",
			"</div>",
		"</div>"
		].join("\n");
	}
	return html;
}



/* --------------------------------------------------------------
 * Interface For "Refine" Relations
 * --------------------------------------------------------------
 */
function generateRefineBody(id){
	var act_dom_id = "ref-name-" + id;
	var label = document.getElementById(act_dom_id).innerHTML;
	var act_dom_id = "ref-url-" + id;
	var url = document.getElementById(act_dom_id).href;
	
	var bodyString = [
		"<div class=\"container-fluid\">",
			"<div class=\"row\">",	
				"<div class=\"col-xs-7\">",
					"<h4>Load Data from Refine</h4>",
					"<div id=\"ref-button-outer\" style=\"padding-bottom:2%;\">",
						"<button title=\"Start Loading from Refine\" onclick=\"javascript:accessionAllData('" + id + "');\" ",
						" type=\"button\" class=\"btn btn-primary\" id=\"ref-load-button\">",
                            "<span class=\"glyphicon glyphicon-upload\"></span>",
							"Load Data Now",
						"</button>",
					"</div>",
				"</div>",
				"<div class=\"col-xs-5\">",
					"<h4>Import from Refine:</h4>",
					"<p>",
						"<a target=\"_blank\" href=\"" + url + "\">" + label + "</a>",
					"</p>",
				"</div>",
			"</div>",
			"<div class=\"row\">",	
				"<div class=\"col-xs-7\">",
					"<div class=\"row\">",
						"<div id=\"ref-prog-spin-outer\" class=\"col-xs-4\">",
						"</div>",
						"<div id=\"ref-prog-data-outer\" class=\"col-xs-8\">",
						"</div>",
					"</div>",
					"<div class=\"row\">",
						"<div id=\"ref-load-prog-bar-outer\" class=\"col-xs-12\">",
						"</div>",
					"</div>",
					"<div class=\"row\">",
						"<div id=\"ref-uuid-prog-bar-outer\" class=\"col-xs-12\">",
						"</div>",
					"</div>",
				"</div>",
				"<div class=\"col-xs-5\">",
					"Refine 'project' identifier: "+ id,
				"</div>",
			"</div>",
		"</div>"
	].join("\n");
	return bodyString;
}
