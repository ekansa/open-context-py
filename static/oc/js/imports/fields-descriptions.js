/* ----------------------------------------------------
 * Initial load of fields for use in descriptions
 *
 * ----------------------------------------------------
*/

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
		dataType: "json"
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
