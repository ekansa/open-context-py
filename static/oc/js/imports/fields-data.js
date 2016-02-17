
/* ----------------------------------------------------
 * AJAX to load up fields
 *
 * ----------------------------------------------------
*/

var field_data = [];
var annotations = [];
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

function chained_field_data(){
	/* AJAX to get field data, used in a chain */
	var url = "../../imports/field-list/" + encodeURIComponent(source_id);
	return $.ajax({
		type: "GET",
		url: url,
		dataType: "json",
		success: alt_field_data_Done
	});
}

function get_field_data_Done(data){
	/* Stores field data in the global 'field_list' */
	field_data = [];
	annotations = [];
	for (var i = 0, length = data.length; i < length; i++) {
		field_data.push(data[i]);
		for (var j = 0, length_anno = data[i].annotations.length; j < length_anno; j++) {
			annotations.push(data[i].annotations[j]);
		}
	}
}

/* ----------------------------------------------------
 * Display field data, limited by list of accepted field_type_limits
 *
 * ----------------------------------------------------
*/

var field_select_function = "selectField";

function generateFieldListHTML(sub_obj_type, field_type_limits){
	/* Makes a snippett of HTML for a field list used as either a subject or object */
	var main_DomID = sub_obj_type + "-field-interfacce";
	var tbody_DomID = sub_obj_type + "-Tbody";
	var third_tHead = "";
	var second_tHead_class = "col-sm-11";
	var formHTML = [
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
		"</form>"
		].join("\n");
	if (sub_obj_type == "all_descriptions") {
		var panelTitle = "Descriptive Fields";
		var table_class = "table table-condensed";
		formHTML = "";
		tbody_DomID = "fieldtabfields"; // So correct CSS shown to indicate selection
		second_tHead_class = "col-sm-6";
		third_tHead = "<th class=\"col-sm-5\">Used with</th>";
	}
	else if (sub_obj_type == "described") {
		var panelTitle = "Subjects of Descriptions";
		var table_class = "table table-condensed table-hover";
		formHTML = "";
		// second_tHead_class = "col-sm-6";
		// third_tHead = "<th class=\"col-sm-5\">Described using</th>";
	}
	else{
		var panelTitle = "Relationship '" + sub_obj_type + "' field";
		var table_class = "table table-condensed table-hover";
	}
	var rowsHTML = generateFieldListRowsHTML(sub_obj_type, field_type_limits);
	var mainHTML = [
		"<div class=\"panel panel-default\">",
			"<div class=\"panel-heading\">",
				"<h4 class=\"panel-title\">" + panelTitle + "</h4>",
			"</div>",
			"<div class=\"panel-body\">",
				formHTML,
				"<table id=\"" + sub_obj_type + "-fieldsTable\" class=\"" + table_class + "\">",
					"<thead>",
						"<th class=\"col-sm-1\">Field</th>",
						"<th class=\"" + second_tHead_class + "\">Label</th>",
						third_tHead,
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
			if (sub_obj_type == "all_descriptions") {
				var field_association_domID = "flink-field-num-" + field.field_num;
				var field_describes_HTML = generate_field_describesHTML(field);
				rowHTML = [
					"<tr id=\"" + row_id  + "\">",
						"<td>",
							field.field_num,	
						"</td>",
						"<td>",
							field.label,	
						"</td>",
						"<td id=\"" + field_association_domID  + "\">",
							field_describes_HTML,	
						"</td>",
					"</tr>"
				].join("\n");
			}
			else if (sub_obj_type == "described") {
				var field_association_domID = "flinkby-field-num-" + field.field_num;
				rowHTML = [
					"<tr id=\"" + row_id  + "\">",
						"<td>",
							field.field_num,	
						"</td>",
						"<td>",
							"<a id=\"" + label_id + "\" href=\"javascript:" + field_select_function + "('" + sub_obj_type + "'," + field.field_num + ");\">" + field.label + "</a>",	
						"</td>",
					"</tr>"
				].join("\n");
			}
			else{
				rowHTML = [
					"<tr id=\"" + row_id  + "\">",
						"<td>",
							field.field_num,	
						"</td>",
						"<td>",
							"<a id=\"" + label_id + "\" href=\"javascript:" + field_select_function + "('" + sub_obj_type + "'," + field.field_num + ");\">" + field.label + "</a>",	
						"</td>",
					"</tr>"
				].join("\n");
			}
			rows.push(rowHTML);
		}
	}
	var rowsHTML = rows.join("\n"); 
	return rowsHTML;
}


function generate_field_describesHTML(field){
	// makes HTML snippet for what the field describes
	var outputHTML = "";
	for (var i = 0, length = field.annotations.length; i < length; i++) {
		if (field.annotations[i].predicate.id == PRED_DESCRIBES ||
			 field.annotations[i].predicate.id == PRED_GEO_LOCATION ||
			 field.annotations[i].predicate.id == PRED_DATE_EVENT ||
			 field.annotations[i].predicate.id == PRED_VALUE_OF) {
			outputHTML = "<button type=\"button\" class=\"btn btn-warning btn-xs\" ";
			outputHTML += "onclick=\"javascript:removeDescriptionAnno(" + field.annotations[i].id + ");\" >";
			outputHTML += "<span class=\"glyphicon glyphicon-remove\"></span></button> ";
			outputHTML += field.annotations[i].object.label;
			outputHTML += "<br/><samp>(Field: " + field.annotations[i].object.field_num + ")</samp>";
		}
		
	}
	return outputHTML;
}