
function accessionAllData(refine_project) {
	// Does AJAX POST requests until the response says done=True
	loadingStartHTML();
    function accessionData() {
		var url = "../../imports/project-import-refine/" + encodeURIComponent(project_uuid);
        $.ajax({
            url: url,
			type: 'POST',
            method: 'POST',
            async: true,
			dataType: "json",
			data: {csrfmiddlewaretoken: csrftoken,
					refine_project: refine_project},
            success: function(data) {
                if (!data.done) {
                    showAccessionProgress(data);
                    accessionData();
                }
				else{
					loadingDoneHTML(data);
				}
            }
        });
    }
    accessionData();
}

function demo_accessionAllData(refine_project) {
	/* This is a short demo function
	 * used to test UI elements without actually
	 * importing data
	 */
	loadingStartHTML();
	data = {'source_id': 'demo-source-id',
			'done': true,
			'end': 5,
			'row_count': 25};
	showAccessionProgress(data);
	loadingDoneHTML(data);
}

function loadingStartHTML(){
	var act_dom_id = "ref-prog-spin-outer";
	var loadImageHTML = [
		"<div style=\"text-align:center; padding-top:10%;\">",
			"<img src=\"../../static/oc/images/ui/waiting.gif\" alt=\"Loading icon...\" />",
		"</div>"
	].join('\n');
	document.getElementById(act_dom_id).innerHTML = loadImageHTML;
	var act_dom_id = "ref-load-button";
	document.getElementById(act_dom_id).disabled = "disabled";
}

function loadingDoneHTML(data){
	showAccessionProgress(data);
	var act_dom_id = "ref-prog-spin-outer";
	var loadImageHTML = [
		"<div style=\"text-align:center; padding-top:10%;\">",
			"<span style=\"font-size:36px;\" class=\"glyphicon glyphicon-ok-circle\"></span>",
		"</div>"
	].join('\n');
	document.getElementById(act_dom_id).innerHTML = loadImageHTML;
	var act_dom_id = "ref-button-outer";
	var buttonHTML = [
		"<a title=\"Prepare these data for import\" href=\"../../imports/field-types/" + data.source_id + "\" ",
			" role=\"button\" class=\"btn btn-primary\" id=\"ref-load-button\">",
            "<span class=\"glyphicon glyphicon-wrench\"></span>",
			"Describe Data",
		"</a>",
	].join('\n');
	document.getElementById(act_dom_id).innerHTML = buttonHTML;
}

function showAccessionProgress(data){
	/* Displays feedback on progress regarding an import of data
	from refine to a project
	*/
	if (data.make_uuids) {
		// only makes responses to uuids if they are already generated
		// this defualts to off because it takes a long time
		var uuidsHTML = [
			"<dt>Total Number of Fields:</dt>",
			"<dd>" + data.field_count + "</dd>",
			"<dt>Fields with UUIDs Assigned:</dt>",
			"<dd>" + data.act_uuid_field + "</dd>"
		].join('\n');
		uuid_progress_HTML(data.act_uuid_field, data.field_count);
	}
	else{
		var uuidsHTML = "";
	}
	var statsHTML = [
		"<dl>",
			"<dt>Total Number of Rows:</dt>",
			"<dd>" + data.row_count + "</dd>",
			"<dt>Rows Imported:</dt>",
			"<dd>" + data.end + "</dd>",
			uuidsHTML,
		"</dl>"
	].join("\n");
	var act_dom_id = "ref-prog-data-outer";
	document.getElementById(act_dom_id).innerHTML = statsHTML;
	load_progress_HTML(data.end, data.row_count);
}

function load_progress_HTML(act_val, total_val){
	//makes a progress bar 	
	var act_dom_id = "ref-load-prog-bar-outer";
	var act_dom = document.getElementById(act_dom_id);
	if (act_val < total_val) {
		var titleHTML = "<h5>Loading Data from Refine...</h5>";
	}
	else{
		var titleHTML = "<h5>Refine Data Loaded</h5>";	
	}
	var barHTML = progress_HTML(act_val, total_val);
	act_dom.innerHTML = titleHTML + barHTML;
}

function uuid_progress_HTML(act_val, total_val){
	//makes a uuid progress bar 	
	var act_dom_id = "ref-uuid-prog-bar-outer";
	var act_dom = document.getElementById(act_dom_id);
	if (!act_val) {
		var titleHTML = "<h5>Waiting for Load to Complete</h5>";
	}
	else{
		if (act_val < total_val) {
			var titleHTML = "<h5>Adding Preliminary Identifiers...</h5>";
		}
		else{
			var titleHTML = "<h5>Preliminary Identifier Assignment Done</h5>";	
		}	
	}
	var barHTML = progress_HTML(act_val, total_val);
	act_dom.innerHTML = titleHTML + barHTML;
}

function progress_HTML(act_val, total_val){
	//makes a progress bar 	
	if (total_val > 0 ) {
		var proportion_now = act_val / total_val;
	}
	else{
		var proportion_now = 1
	}
	var value_now = Math.round((proportion_now * 100))
	var barHTML = [
		"<div class=\"progress\">",
			"<div id=\"ref-prog-bar\" class=\"progress-bar\" role=\"progressbar\" ",
				"aria-valuenow=\"" + value_now + "\" aria-valuemin=\"0\" aria-valuemax=\"100\" style=\"width: " + value_now + "%;\">",
				value_now + "%",
			"</div>",
		"</div>"
	].join("\n");
	return barHTML
}
