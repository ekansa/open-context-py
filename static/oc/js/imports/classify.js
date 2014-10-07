/*
 * Functions to classify fields for import
 */
$(function() {
	/* Makes the table rows selectable. 
	*/
    $( "#fieldtabfields" ).selectable({
		filter:'tr'
	});
});

function getSelectedFieldNumbers(){
	var nodeList = document.getElementsByClassName('ui-selected');
	var selected_fields = ''
	for (var i = 0, length = nodeList.length; i < length; i++) {
		field_num = nodeList[i].id.replace('field-num-', '');
		if (i < 1){
			selected_fields = field_num
		}
		else{
			selected_fields += ',' + field_num
		}
	}
	return selected_fields;
}

function assignType(field_type) {
	/* Composes request to add a field_type to a selected list of rows 
	*/
	var selected_fields = getSelectedFieldNumbers();
	url = "../../imports/field-classify/" + encodeURIComponent(source_id);
	var req = $.ajax({
		type: "POST",
		url: url,
		dataType: "json",
		data: {
			field_type: field_type,
			field_num: selected_fields,
			csrfmiddlewaretoken: csrftoken},
		success: assignTypeDone
	});
}

function assignTypeDone(data){
	/* Shows updates to field_types */
	for (var i = 0, length = data.length; i < length; i++) {
		var field_num = data[i].field_num
		var ft_dom_id = 'field-type-' + field_num
		var ft_dom = document.getElementById(ft_dom_id)
		ft_dom.innerHTML = data[i].field_type
	}
}

function assignDataType(field_data_type) {
	/* Composes request to add a field_type to a selected list of rows 
	*/
	var selected_fields = getSelectedFieldNumbers();
	url = "../../imports/field-classify/" + encodeURIComponent(source_id);
	var req = $.ajax({
		type: "POST",
		url: url,
		dataType: "json",
		data: {
			field_data_type: field_data_type,
			field_num: selected_fields,
			csrfmiddlewaretoken: csrftoken},
		success: assignDataTypeDone
	});	
}

function assignDataTypeDone(data){
	/* Shows updates to field_data_type */
	for (var i = 0, length = data.length; i < length; i++) {
		var field_num = data[i].field_num
		var ft_dom_id = 'field-data-type-' + field_num
		var ft_dom = document.getElementById(ft_dom_id)
		ft_dom.innerHTML = data[i].field_data_type
	}
}