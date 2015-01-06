/*
 * Functions to edit spatial coodinates and time ranges
 */
function displayEvents() {
	// code to display a list of events
	if (act_item.data != false) {
		var feature_events =  get_objval_via_keys(act_item.data, ['features']);
		if (feature_events != false) {
			var rowsHTML = "";
			for (var i = 0, length = feature_events.length; i < length; i++) {
				var event = feature_events[i];
				if (event.id.indexOf("derived") < 0 ) {
					rowsHTML += eventHTML(event) + "\n";
				}
			}
			var dom_id = "event-list";
			document.getElementById(dom_id).innerHTML = rowsHTML;
		}
	}
}

function eventHTML(event){
	var feature_id = get_id_num_from_id(event.id);
	var geo_id = get_objval_via_keys(event, ['geometry', 'id']);
	if (geo_id != false) {
		var ids = get_geo_event_ids(geo_id);
		geo_id = ids.geo;
	}
	var event_id = get_objval_via_keys(event, ['when', 'id']);
	if (event_id != false) {
		event_id = get_id_num_from_id(event_id);
	}
	var show_id = geo_id;
	if (event_id != false) {
		show_id += "-" + event_id;
	}
	
	var lat = false;
	var lon = false;
	if (get_objval_via_keys(event, ['geometry', 'type']) == 'Point') {
		lat = get_objval_via_keys(event, ['geometry', 'coordinates', 1]);
		lon = get_objval_via_keys(event, ['geometry', 'coordinates', 0]);				
	}
	var coords = JSON.stringify(get_objval_via_keys(event, ['geometry', 'coordinates']));
	
	if (get_objval_via_keys(event, ['properties', 'reference-type']) == 'specified' || get_objval_via_keys(event, ['when', 'reference-type']) == 'specified') {
		var actionHTML = [
			"<button class=\"btn btn-info\" onclick=\"javascript:editEventForm("+ geo_id + ", " + event_id + ");\">",
				"<span class=\"glyphicon glyphicon-edit\" aria-hidden=\"true\"></span> Edit",
			"</button>"
		].join("\n");
	}
	else{
		var actionHTML = [
			"<button class=\"btn btn-info\" disabled=\"disabled\">",
				"<span class=\"glyphicon glyphicon-edit\" aria-hidden=\"true\"></span> Cannot edit",
			"</button>",
			"<br/>",
			"<small>Data inferred from context</small>"
		].join("\n");
	}
	
	var notesHTML = "<ul>";
	if (get_objval_via_keys(event, ['properties', 'note']) != false) {
		notesHTML += "<li>Other Note: " + get_objval_via_keys(event, ['properties', 'note']) + "</li>";
	}
	if (get_objval_via_keys(event, ['properties', 'note']) != false) {
		notesHTML += "<li>Other Note: " + get_objval_via_keys(event, ['properties', 'note']) + "</li>";
	}
	if (get_objval_via_keys(event, ['properties', 'location-note']) != false) {
		notesHTML += "<li>Location Note: " + get_objval_via_keys(event, ['properties', 'location-note']) + "</li>";
	}
	
	if (get_objval_via_keys(event, ['properties', 'reference-uri']) != false) {
		var ref_uuid = get_uuid_from_uri(get_objval_via_keys(event, ['properties', 'reference-uri']));
		var whereNoteHTML = [
			"<li>Geospatial ",
			get_objval_via_keys(event, ['properties', 'reference-type']),
			" from: ",
			"<a href=\"../../edit/items/" + ref_uuid + "\" target=\"_blank\">",
				"<span class=\"glyphicon glyphicon-new-window\" aria-hidden=\"true\"></span>",
				"<span class=\"glyphicon glyphicon-map-marker\" aria-hidden=\"true\"></span>",
				get_objval_via_keys(event, ['properties', 'reference-label']),
			"</a>",
			"</li>"
		].join("\n");
	}
	else{
		var whereNoteHTML = "<li>Map data specified for this item</li>";
	}
	if (get_objval_via_keys(event, ['when', 'reference-uri']) != false) {
		var ref_uuid = get_uuid_from_uri(get_objval_via_keys(event, ['when', 'reference-uri']));
		var whenNoteHTML = [
			"<li>Time-range ",
			get_objval_via_keys(event, ['when', 'reference-type']),
			" from: ",
			"<a href=\"../../edit/items/" + ref_uuid + "\" target=\"_blank\">",
				"<span class=\"glyphicon glyphicon-new-window\" aria-hidden=\"true\"></span>",
				"<span class=\"glyphicon glyphicon-calendar\" aria-hidden=\"true\"></span>",
				get_objval_via_keys(event, ['when', 'reference-label']),
			"</a>",
			"</li>",
		].join("\n");
	}
	else{
		var whenNoteHTML = "<li>Time-range specified for this item</li>";
	}
	
	notesHTML += whereNoteHTML + whenNoteHTML + "</ul>";
	
	var html = [
		"<tr id=\"feature-id-" + feature_id + "\">",
			"<td>",
				actionHTML,
			"</td>",
			"<td>" + show_id + "</td>",
			"<td>",
				"<table>",
					"<tr id=\"feature-id-" + event_id + "\" >",
						"<td class=\"col-xs-3\"><dl><dt>Location Type:</dt><dd>" + get_objval_via_keys(event, ['properties', 'type']) + "</dd></dl></td>",
						"<td class=\"col-xs-2\"><dl><dt>Lat:</dt><dd>" + lat + "</dd></dl></td>",
						"<td class=\"col-xs-2\"><dl><dt>Lon:</dt><dd>" + lon + "</dd></dl></td>",
						"<td class=\"col-xs-2\"><dl><dt>Geo Precision:</dt><dd>" + get_objval_via_keys(event, ['properties', 'location-precision']) + "</dd></dl></td>",
						"<td class=\"col-xs-3\"><dl><dt>Coodinates (GeoJSON):</dt><dd><code style=\"font-size:75%;\">" + coords + "</code></dd></dl></td>",
					"</tr>",
					"<tr>",
						"<td class=\"col-xs-3\"><dl><dt>Chrono Type:</dt><dd>" + get_objval_via_keys(event, ['when', 'type']) + "</dd></dl></td>",
						"<td class=\"col-xs-2\"><dl><dt>Start:</dt><dd>" + get_objval_via_keys(event, ['when', 'start']) + "</dd></dl></td>",
						"<td class=\"col-xs-2\"><dl><dt>Stop:</dt><dd>" + get_objval_via_keys(event, ['when', 'stop']) + "</dd></dl></td>",
						"<td class=\"col-xs-5\" colspan=\"2\"><dl><dt>Notes:</dt><dd>" + notesHTML + "</dd></dl></td>",
					"</tr>",
				"</table>",
			"</td>",
		"</tr>"
	].join('\n');
	
	return html;
}


function get_uuid_from_uri(uri){
	// get the uuid which is the last element in a '/' deliminated list
	var uri_list = uri.split("/");
	return uri_list[(uri_list.length - 1)];
}


function get_id_num_from_id(id){
	// get the id number which is the last element in a '-' deliminated list
	var id_list = id.split("-");
	return id_list[(id_list.length - 1)];
}

function get_objval_via_keys(act_obj, keys){
	// gets the value of a part of an object from a path of keys (a list)
	var output = false;
	for (var i = 0, length = keys.length; i < length; i++) {
		var key = keys[i];
		if (act_obj[key] !== undefined) {
			act_obj = act_obj[key];
			output = act_obj;
		}
		else{
			output = false;
			break;
		}
	}
	return output;
}

function get_geo_event_ids(id){
	var id_list = id.split("-");
	var geo_id = false;
	var event_id = false;
	for (var i = 0, length = id_list.length; i < length; i++) {
		var part = id_list[i];
		if (isNumber(part)) {
			if (geo_id == false) {
				geo_id = part;
			}
			else{
				if (event_id == false) {
					event_id = part;
				}
			}
		}
	}
	return {geo: geo_id,
			event: event_id};
}

function isNumber(n) {
   return !isNaN(parseFloat(n)) && isFinite(n);
}

/* --------------------------------------------------------
 * Functions related to adding new geospatial / chronological event data
 * --------------------------------------------------------
 */

function addEventForm(){
	var title_dom = document.getElementById('event-modal-title');
	var body_dom = document.getElementById('event-modal-body');
	title_dom.innerHTML = 'Add Geospatial and / or Chronological Data';
	var action_button = document.getElementById('event-modal-foot-button');
	var buttonHTML = "<span class=\"glyphicon glyphicon-cloud-upload\" aria-hidden=\"true\"></span>";
    buttonHTML += " Add Data";
	action_button.innerHTML = buttonHTML;
	action_button.onclick = addEvent;
	var bodyHTML = [
		'Eventually, a day will come when this will add a form that will enable a user to add space + time data. ',
		'But today is not that day.'
	].join('\n');
	body_dom.innerHTML = bodyHTML;
	$("#eventModal").modal('show');
}


function addEvent(){
	// does nothing yet
}



/* --------------------------------------------------------
 * Functions related to editing existing geospatial / chronological event data
 * --------------------------------------------------------
 */

function editEventForm(geo_id, event_id){
	var title_dom = document.getElementById('event-modal-title');
	var body_dom = document.getElementById('event-modal-body');
	title_dom.innerHTML = 'Add Geospatial and / or Chronological Data';
	var action_button = document.getElementById('event-modal-foot-button');
	var buttonHTML = "<span class=\"glyphicon glyphicon-cloud-upload\" aria-hidden=\"true\"></span>";
    buttonHTML += " Save Edits";
	action_button.innerHTML = buttonHTML;
	action_button.onclick = addEvent;
	var bodyHTML = [
		'Eventually, a day will come when this will enable a user to edit space + time data for feature id: ' + geo_id + "(" + event_id + ")",
		'But today is not that day.'
	].join('\n');
	body_dom.innerHTML = bodyHTML;
	$("#eventModal").modal('show');
}