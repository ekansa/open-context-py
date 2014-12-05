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
	var bodyString = [
		"<div class=\"container-fluid\">",
			"<div id=\"action-div\">",	
			"</div>",
			"<div class=\"row\">",	
				"<div class=\"col-xs-6\">",
					"source-stuff: "+ id,
				"</div>",
				"<div class=\"col-xs-6\">",
					"source-stuff: "+ id,
				"</div>",
			"</div>",
		"</div>"
	].join("\n");
	return bodyString;
}


/* --------------------------------------------------------------
 * Interface For "Refine" Relations
 * --------------------------------------------------------------
 */
function generateRefineBody(id){
	/* changes global varaiables from entities.js */
	var bodyString = [
		"<div class=\"container-fluid\">",
			"<div id=\"action-div\">",	
			"</div>",
			"<div class=\"row\">",	
				"<div class=\"col-xs-6\">",
					"refine-stuff: "+ id,
				"</div>",
				"<div class=\"col-xs-6\">",
					"refine-stuff: "+ id,
				"</div>",
			"</div>",
		"</div>"
	].join("\n");
	return bodyString;
}
