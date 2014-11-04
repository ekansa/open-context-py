/* ----------------------------------------------------
 * Initial load of fields for use in descriptions
 *
 * ----------------------------------------------------
*/
function start_descriptions(){
	/* Chains together AJAX request to get existing description annotations, examples */
	chained_field_data().then(get_example_entities).then(reload_fields);
}

function alt_field_data_Done(data){
	get_field_data_Done(data);
	var description_fields_DomID = "description_fields_outer";
	var description_fields_dom = document.getElementById(description_fields_DomID);
	var desciption_fields_HTML = generateFieldListHTML("all_descriptions", DEFAULT_DESCRIBE_TYPE_FIELDS);
	description_fields_dom.innerHTML = desciption_fields_HTML;
	var select_row_tab = $(function() {
		/* Makes the table rows selectable. 
		*/
		$( "#fieldtabfields" ).selectable({
			filter:'tr'
		});
	});
	field_select_function = "describeField";
	var described_fields_DomID = "described_fields_outer";
	var described_fields_dom = document.getElementById(described_fields_DomID);
	var var_val = check_for_var_val_fields();
	if (var_val) {
		var use_subj_fields = ['variable'];
		use_subj_fields = use_subj_fields.concat(DEFAULT_SUBJECT_TYPE_FIELDS);
	}
	else{
		var use_subj_fields = DEFAULT_SUBJECT_TYPE_FIELDS;
	}
	var described_fields_HTML = generateFieldListHTML("described", use_subj_fields);
	described_fields_dom.innerHTML = described_fields_HTML;
}

function check_for_var_val_fields(){
	//Checks to see if there are both variable AND value field_type fields
	output = false;
	value_field = false;
	variable_field = false;
	for (var i = 0, length = field_data.length; i < length; i++) {
		if (field_data[i].field_type == 'variable') {
			variable_field = true;
		}
		else if (field_data[i].field_type == 'value') {
			value_field = true;
		}
	}
	if (value_field && variable_field) {
		output = true;
	}
	return output;
}

function getSelectedFieldNumbers(){
	// gets comma sep value list of selected rows of desciptive fields
	var nodeList = document.getElementsByClassName('ui-selected');
	var selected_fields = ''
	for (var i = 0, length = nodeList.length; i < length; i++) {
		field_num = nodeList[i].id.replace('all_descriptions-field-num-', '');
		if (i < 1){
			selected_fields = field_num
		}
		else{
			selected_fields += ',' + field_num
		}
	}
	return selected_fields;
}

function determine_description_predicate(selected_fields, object_field_num){
	// determines what predicate to assign based on
	// the selected fields and the object field
	var act_predicate = PRED_DESCRIBES;
	value_field = false;
	variable_field = false;
	for (var i = 0, length = field_data.length; i < length; i++) {
		if (field_data[i].field_type == 'variable' && field_data[i].field_num == object_field_num) {
			variable_field = true;
		}
		else if (field_data[i].field_type == 'value' && field_data[i].field_num == selected_fields) {
			value_field = true;
		}
	}
	if (variable_field && value_field) {
		act_predicate = PRED_VALUE_OF;
	}
	return act_predicate;
}

function describeField(sub_obj_type, object_field_num){
	// sends ajax request to assign descriptions to fields
	post_annotation(sub_obj_type, object_field_num).then(get_example_entities).then(reload_fields);
}

function post_annotation(sub_obj_type, object_field_num){
	// sends ajax request to assign descriptions to fields
	var selected_fields = getSelectedFieldNumbers();
	var act_predicate = determine_description_predicate(selected_fields, object_field_num);
	var url = "../../imports/field-annotation-create/" + encodeURIComponent(source_id);
	return $.ajax({
		type: "POST",
		url: url,
		dataType: "json",
		data: {
			field_num: selected_fields,
			predicate: act_predicate,
			object_field_num: object_field_num,
			csrfmiddlewaretoken: csrftoken}
		});
}

function get_example_entities(data){
	var url = "../../imports/field-described-examples/" + encodeURIComponent(source_id);
	return $.ajax({
		type: "GET",
		url: url,
		dataType: "json",
		success: get_example_entitiesDone
	});
}

function reload_fields(data){
	var url = "../../imports/field-list/" + encodeURIComponent(source_id);
	var req = $.ajax({
			type: "GET",
			url: url,
			dataType: "json",
			success: alt_field_data_Done
		});
}
	

/* --------------------------------------------
 * Example entities display
 * --------------------------------------------
*/

function get_example_entitiesDone(data){
	if (data.length > 0) {
		var example_HTML = "";
		for (var i = 0, length = data.length; i < length; i++) {
			example_HTML += generate_example_entity_tabHTML(data[i]);
		}
	}
	else{
		var example_HTML = [
			"<div class=\"alert alert-info\" role=\"alert\">",
			"[No descriptions assigned yet]",
			"</div>"
		].join("\n");
	}
	var example_DomID = "described_examples_outer";
	var example_dom = document.getElementById(example_DomID);
	example_dom.innerHTML = example_HTML;
}

function generate_example_entity_tabHTML(entity){
	/* generates HTML for an example entity */
	var rowsHTML = generate_example_des_rowsHTML(entity);
	var tab_HTML = [
		"<h5>" + entity.label + "</h5>",
		"<table id=\"" + entity.id + "-des-tab\" class=\"table table-condensed table-bordered table-striped\">",
			"<thead>",
				"<th class=\"col-sm-6\">Property / Predicate</th>",
				"<th class=\"col-sm-6\">Value(s)</th>",
			"</thead>",
			"<tbody>",
				rowsHTML,
			"</tbody>",
		"</table>",
	].join("\n");
	return tab_HTML;
}

function generate_example_des_rowsHTML(entity){
	var rowsHTML = "";
	for (var i = 0, length = entity.descriptions.length; i < length; i++) {
		var act_des = entity.descriptions[i];
		if ( act_des.objects.length > 1) {
			var valsHTML = "<ul>";
			for (var j = 0, length = act_des.objects.length; j < length; j++) {
				var act_val_obj = act_des.objects[j];
				valsHTML += "<li>" + act_val_obj.record + "</li>";
			}
			valsHTML += "</ul>";
		}
		else{
			var valsHTML = act_des.objects[0].record;
			if (valsHTML.length > 144) {
				valsHTML = valsHTML.substring(0, 144) + "...";	
			}
		}
		var rowHTML = [
			"<tr>",
				"<td>" + act_des.predicate.label,
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
 * Functions to DELETE description annotations
 *
 * ----------------------------------------------------
*/

function removeDescriptionAnno(annotaiton_id){
	/* sets of a chain of AJAX calls to remove an annotation, then load up examples, then fields */
	deleteAnnotation(annotaiton_id).then(get_example_entities).then(reload_fields);
}

function deleteAnnotation(annotation_id){
	/* AJAX call delete a specific annotation */
	var url = "../../imports/field-annotation-delete/" + encodeURIComponent(source_id) + "/" + annotation_id;
	return $.ajax({
		type: "POST",
		url: url,
		dataType: "json",
		data: {csrfmiddlewaretoken: csrftoken}
	});
}
