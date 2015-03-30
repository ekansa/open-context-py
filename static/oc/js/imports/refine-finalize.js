function start_finalization() {
	// Does AJAX POST requests until the response says done=True
	finalizeStartHTML();
	var loop = 0;
	var reset_state = true;
    function finalizeData() {
		loop += 1;
		var url = "../../imports/import-finalize/" + encodeURIComponent(source_id);
		var post_data = {'csrfmiddlewaretoken': csrftoken}
		if (reset_state) {
			post_data['reset_state'] = reset_state
			reset_state = false
		}
        $.ajax({
            url: url,
			type: 'POST',
            method: 'POST',
            async: true,
			dataType: "json",
			data: post_data,
            success: function(data) {
				data.loop = loop;
				// console.log(data)
                if (!data.done && data.ok) {
                    showProgress(data);
                    finalizeData();
                }
				else{
					finalizeDoneHTML(data);
				}
            }
        });
    }
    finalizeData();
}

function demo_start_finalization() {
	/* This is a short demo function
	 * used to test UI elements without actually
	 * importing data
	 */
	finalizeStartHTML();
	data = {'source_id': source_id,
			'ok': true,
			'done': false,
			'done_stage': 'verify',
			'next_stage': 'subjects',
			'done_stage_num': 2,
			'total_stages': 5,
			'end': 5,
			'row_count': 25};
	showProgress(data);
	finalizeDoneHTML(data);
}

function finalizeStartHTML(){
	var act_dom_id = "ref-final-spin-outer";
	var loadImageHTML = [
		"<div style=\"text-align:center; padding-top:10%;\">",
			"<img src=\"../../static/oc/images/ui/waiting.gif\" alt=\"Loading icon...\" />",
		"</div>"
	].join('\n');
	document.getElementById(act_dom_id).innerHTML = loadImageHTML;
	var act_dom_id = "ref-final-button";
	document.getElementById(act_dom_id).disabled = "disabled";
	var actionHTML = [
		"<dl>",
			"<dt>Action:</dt>",
			"<dd>Checking if import ok to continue...</dd>",
		"</dl>"
	].join('\n');
	var act_dom_id = "ref-final-prog-stage-note-outer";
	document.getElementById(act_dom_id).innerHTML = actionHTML;
}

function finalizeDoneHTML(data){
	showProgress(data);
	if (data.ok) {
		var act_dom_id = "ref-final-spin-outer";
		var loadImageHTML = [
			"<div style=\"text-align:center; padding-top:10%;\">",
				"<span style=\"font-size:36px;\" class=\"glyphicon glyphicon-ok-circle\"></span>",
			"</div>"
		].join('\n');
		document.getElementById(act_dom_id).innerHTML = loadImageHTML;
		var act_dom_id = "ref-final-button";
		document.getElementById(act_dom_id).innerHTML = "Import Done!";
	}
	else{
		var act_dom_id = "ref-final-spin-outer";
		var loadImageHTML = [
			"<div style=\"text-align:center; padding-top:10%;\">",
				"<span style=\"font-size:36px;\" class=\"glyphicon glyphicon-exclamation-sign\"></span>",
			"</div>"
		].join('\n');
		document.getElementById(act_dom_id).innerHTML = loadImageHTML;
		var act_dom_id = "ref-final-button";
		document.getElementById(act_dom_id).innerHTML = "Import Failed!";
	}
}

function showProgress(data){
	/* Displays feedback on progress regarding an import of data
	from refine to a project
	*/
	var badHTML = "";
	if (!data.ok) {
		var badHTML = [
			"<dt>ERROR:</dt>",
			"<dd>" + data.error + "</dd>"
		].join('\n');
	}
	var actionHTML = [
		"<dl>",
			badHTML,
			"<dt>Completed Action:</dt>",
			"<dd>Import - " + data.done_stage + "</dd>",
			"<dt>Next Action:</dt>",
			"<dd>Import - " + data.next_stage + "</dd>",
		"</dl>"
	].join('\n');
	var act_dom_id = "ref-final-prog-stage-note-outer";
	document.getElementById(act_dom_id).innerHTML = actionHTML;
	
	stage_progress_HTML(data.done_stage_num, data.total_stages);
	
	var statsHTML = [
		"<dl>",
			"<dt>Total Number of Rows:</dt>",
			"<dd>" + data.row_count + "</dd>",
			"<dt>Rows Imported:</dt>",
			"<dd>" + data.end + "</dd>",
		"</dl>"
	].join("\n");
	var act_dom_id = "ref-final-prog-all-nums-outer";
	document.getElementById(act_dom_id).innerHTML = statsHTML;
	
	import_progress_HTML(data.end, data.row_count);
}

function stage_progress_HTML(act_val, total_val){
	//makes a progress bar 	
	var act_dom_id = "ref-final-prog-stage-bar-outer";
	var act_dom = document.getElementById(act_dom_id);
	if (act_val < total_val) {
		var titleHTML = "<h5>Process stage in this batch...</h5>";
	}
	else{
		var titleHTML = "<h5>Batch completed</h5>";	
	}
	var barHTML = progress_HTML(act_val, total_val);
	act_dom.innerHTML = titleHTML + barHTML;
}

function import_progress_HTML(act_val, total_val){
	//makes a progress bar 	
	var act_dom_id = "ref-final-prog-all-bar-outer";
	var act_dom = document.getElementById(act_dom_id);
	if (act_val < total_val) {
		var titleHTML = "<h5>Importing data from source...</h5>";
	}
	else{
		var titleHTML = "<h5>Import concluded</h5>";	
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
