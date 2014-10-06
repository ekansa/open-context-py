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
function assignType(field_type) {
	/* Composes request to add a field_type to a selected list of rows 
	*/
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
	for (var i = 0, length = data.length; i < length; i++) {
		var field_num = data[i].field_num
		var ft_dom_id = 'field-type-' + field_num
		var ft_dom = document.getElementById(ft_dom_id)
		ft_dom.innerHTML = data[i].field_type
	}
}
