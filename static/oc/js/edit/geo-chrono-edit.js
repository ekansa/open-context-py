/*
 * Functions to edit spatial coodinates and time ranges
 */
var geo_types = {
	'oc-gen:discovey-location': 'Location of observation or discovery'
};

var chrono_types = {
	'oc-gen:formation-use-life': 'Time of formation, use, or life'
}


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
				"<div id=\"feature-id-" + geo_id + "\" class=\"row\">",
					"<div class=\"col-xs-3\"><dl><dt>Location Type:</dt><dd>" + get_objval_via_keys(event, ['properties', 'type']) + "</dd></dl></div>",
					"<div class=\"col-xs-2\"><dl><dt>Lat:</dt><dd>" + lat + "</dd></dl></div>",
					"<div class=\"col-xs-2\"><dl><dt>Lon:</dt><dd>" + lon + "</dd></dl></div>",
					"<div class=\"col-xs-2\"><dl><dt>Geo Precision:</dt><dd>" + get_objval_via_keys(event, ['properties', 'location-precision']) + "</dd></dl></div>",
					"<divclass=\"col-xs-3\"><dl><dt>Coodinates (GeoJSON):</dt><dd><code style=\"font-size:75%;\">" + coords + "</code></dd></dl></div>",
				"</div>",
				"<div id=\"event-id-" + event_id + "\" class=\"row\">",
					"<div class=\"col-xs-3\"><dl><dt>Chrono Type:</dt><dd>" + get_objval_via_keys(event, ['when', 'type']) + "</dd></dl></div>",
					"<div class=\"col-xs-2\"><dl><dt>Start:</dt><dd>" + get_objval_via_keys(event, ['when', 'start']) + "</dd></dl></div>",
					"<div class=\"col-xs-2\"><dl><dt>Stop:</dt><dd>" + get_objval_via_keys(event, ['when', 'stop']) + "</dd></dl></div>",
					"<div class=\"col-xs-5\" colspan=\"2\"><dl><dt>Notes:</dt><dd>" + notesHTML + "</dd></dl></div>",
				"</div>",
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
 * Functions related to making an editable map
 * --------------------------------------------------------
 */
var edit_map;
var edit_map_resized = false;
var edit_marker = false;
var act_lat = false;
var act_lon = false;
function init_edit_map(lat, lon) {
    edit_map_resized = false; 
	edit_map = L.map('edit-map').setView([45, 45], 4); //map the map
	edit_marker = L.marker(new L.LatLng(lat, lon), {
		draggable: true
	}).addTo(edit_map);
	edit_marker.on('dragend', function (e) {
		var lat = edit_marker.getLatLng().lat;
		var lon = edit_marker.getLatLng().lng;
		document.getElementById('edit-lat').value = lat;
		document.getElementById('edit-lon').value = lon;
		edit_map.panTo([lat, lon]);
		act_lat = lat;
		act_lon = lon;
	});
	
	var osmTiles = L.tileLayer('http://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
	    attribution: '&copy; <a href="http://osm.org/copyright">OpenStreetMap</a> contributors'
	});
   
	var mapboxTiles = L.tileLayer('http://api.tiles.mapbox.com/v3/ekansa.map-tba42j14/{z}/{x}/{y}.png', {
	    attribution: '&copy; <a href="http://MapBox.com">MapBox.com</a> '
	});
   
	var ESRISatelliteTiles = L.tileLayer('http://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
	    attribution: '&copy; <a href="http://services.arcgisonline.com/">ESRI.com</a> '
	});
   
	var gmapRoad = new L.Google('ROADMAP');
	var gmapSat = new L.Google('SATELLITE');
	var gmapTer = new L.Google('TERRAIN');
   
	var baseMaps = {
		"Google-Terrain": gmapTer,
		"Google-Satellite": gmapSat,
		"ESRI-Satellite": ESRISatelliteTiles,
		"Google-Roads": gmapRoad,
		"OpenStreetMap": osmTiles,
		"MapBox": mapboxTiles,
	};
	
	edit_map._layersMaxZoom = 20;
	L.control.layers(baseMaps).addTo(edit_map);
	edit_map.panTo([lat, lon]);
	edit_map.addLayer(mapboxTiles);
}

function intialize_map_marker(lat, lon){
	// adds onchange event so a user can manually change the location
	if (act_lat != false) {
		lat = act_lat;
	}
	if (act_lon != false) {
		lon = act_lon;
	}
	document.getElementById('edit-lat').value = lat;
	document.getElementById('edit-lat').onchange = input_marker;
	document.getElementById('edit-lon').value = lon;
	document.getElementById('edit-lon').onchange = input_marker;
	input_marker();
}

function input_marker(){
	// onchange so a user can type in coordinates to change them
	edit_map.invalidateSize();
	var lat = document.getElementById('edit-lat').value;
	var lon = document.getElementById('edit-lon').value;
	edit_marker.setLatLng([lat,lon]);
	edit_map.panTo([lat, lon]);
	act_lat = lat;
	act_lon = lon;
}

function resize_edit_map(){
	// fixes a bug in Leaflet where the map tiles don't load well
	// from a map made in a hidden div (like a modal)
	// can't think of a more elegant way to fix this.
	if (!edit_map_resized) {
		edit_map_resized = true;
		edit_map.invalidateSize();
	}
}

function editMapHTML(lat, lon, specificity){
	var editMapHTML = [
		"<div class=\"row\">",
			"<div class=\"col-xs-5\">",
				"<form class=\"form-horizontal\">",
					"<div class=\"form-group\">",
						"<label for=\"edit-lat\" class=\"col-xs-4 control-label\">Latitude</label>",
						"<div class=\"col-xs-8\">",
							"<input type=\"text\" class=\"form-control\" id=\"edit-lat\" value=\"" + 90 + "\">",
						"</div>",
					"</div>",
					"<div class=\"form-group\">",
						"<label for=\"edit-lon\" class=\"col-xs-4 control-label\">Longitude</label>",
						"<div class=\"col-xs-8\">",
							"<input type=\"text\" class=\"form-control\" id=\"edit-lon\" value=\"" + 90 + "\">",
						"</div>",
					"</div>",
					"<div class=\"form-group\">",
						"<label for=\"edit-specificity\" class=\"col-xs-4 control-label\">Specificity</label>",
						"<div class=\"col-xs-8\">",
							"<input type=\"text\" class=\"form-control\" id=\"edit-specificity\" value=\"" +specificity + "\">",
							"<br/><small>Enter positive or negative integers. ",
						"Zero (0) means specificity is not indicated. ",
						"Negative values mean intentional reduction in spatial precision to a given tile zoom-level, done as a site security precaution.",
						"Positive values indicate some known level of spatial precision to a given tile zoom-level. </small>",
						"</div>",
					"</div>",
				"</form>",
			"</div>",
			"<div class=\"col-xs-5\">",
				"<div id=\"edit-map\" style=\"width:400px; height:400px;\">",
				"</div>",
			"</div>",
		"</div>"
	].join('\n');
	return editMapHTML;
}

function editChronoHTML(start, stop){
	var editChronoHTML = [
		"<div class=\"row\" style=\"padding-top:2%;\">",
			"<div class=\"col-xs-5\">",
				"<form class=\"form-horizontal\">",
					"<div class=\"form-group\">",
						"<label for=\"edit-start\" class=\"col-xs-4 control-label\">Start Year (BCE/CE)</label>",
						"<div class=\"col-xs-8\">",
							"<input type=\"text\" class=\"form-control\" id=\"edit-start\" value=\"" + start + "\">",
						"</div>",
					"</div>",
					"<div class=\"form-group\">",
						"<label for=\"edit-stop\" class=\"col-xs-4 control-label\">Stop Year (BCE/CE)</label>",
						"<div class=\"col-xs-8\">",
							"<input type=\"text\" class=\"form-control\" id=\"edit-stop\" value=\"" + stop + "\">",
						"</div>",
					"</div>",
				"</form>",
			"</div>",
			"<div class=\"col-xs-7\">",
				"<small>Negative integers indicate BCE dates, positive indicate CE dates.</small>",
			"</div>",
		"</div>"
	].join('\n');
	return editChronoHTML;
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
		"<div onmouseover=\"javascript:resize_edit_map();\">",
		editMapHTML(0, 0, 0),
		editChronoHTML(0,0),
		"</div>"
	].join('\n');
	body_dom.innerHTML = bodyHTML;
	$("#eventModal").modal('show');
	init_edit_map(0, 0);
	intialize_map_marker(0, 0);
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
		editMapHTML(0, 0, 0)
	].join('\n');
	body_dom.innerHTML = bodyHTML;
	init_edit_map(0, 0);
	$("#eventModal").modal('show');
}