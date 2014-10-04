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
	alert(field_type + ' to add to ' + selected_fields)
}
