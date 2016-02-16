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

function assignFieldValuePrefix(field_num) {
	/* Assigns a prefix for the labeling of entities in a given field 
	*/
	var fvp_domID = "field-value-prefix-" + field_num;
	var value_prefix = document.getElementById(fvp_domID).value;
	url = "../../imports/field-meta-update/" + encodeURIComponent(source_id);
	var selected_fields = getSelectedFieldNumbers();
	if (selected_fields == '') {
		selected_fields = field_num;
	}
	else{
		selected_fields += "," + field_num;
	}
	var req = $.ajax({
		type: "POST",
		url: url,
		dataType: "json",
		data: {
			value_prefix: value_prefix,
			field_num: selected_fields,
			csrfmiddlewaretoken: csrftoken},
		success: assignFieldValuePrefixDone
	});
}

function assignFieldValuePrefixDone(data){
	/* Shows updates to the value prefix with example entity labels */
	for (var i = 0, length = data.length; i < length; i++) {
		var field_num = data[i].field_num
		var ft_dom_id = 'field-value-examples-' + field_num
		var ft_dom = document.getElementById(ft_dom_id)
		ft_dom.innerHTML = data[i].ex_csv
	}
}

var act_field_type = false;
var tree_dom_id = 'hierarchy-tree';
function getTypeHierarchy(field_num) {
	/* Gets the hiearchy of child types for a general field type 
	*/
	var ft_domID = "field-type-" + field_num;
	var field_type = document.getElementById(ft_domID).innerHTML;
	field_type = 'oc-gen:' + field_type
	if (act_field_type != field_type) {
		act_field_type = field_type;
		var tree = new hierarchy(field_type, tree_dom_id);
		tree.root_node = true;  //root node of this tree
		tree.collapse_root = true;
		tree.object_prefix = 'tree-1';
		tree.exec_primary_onclick = 'assign_category';
		tree.exec_primary_title = 'Click to select this category';
		tree.do_entity_hierarchy_tree();
		tree.get_data();
		var tree_key = tree.object_prefix; 
		hierarchy_objs[tree_key] = tree;
	}
}




function assign_category(field_value_cat, label, skip, do_nothing) {
	/* Assigns a an entity category for values of cells that are to be
	 * reconciled in an import
	*/
	if (field_value_cat.length > 0) {
		url = "../../imports/field-meta-update/" + encodeURIComponent(source_id);
		var selected_fields = getSelectedFieldNumbers();
		var req = $.ajax({
			type: "POST",
			url: url,
			dataType: "json",
			data: {
				field_value_cat: field_value_cat,
				field_num: selected_fields,
				csrfmiddlewaretoken: csrftoken},
			success: assignEntityCategoryDone
		});
	}
}

function assignMediaCategory(media_cat) {
	/* Assigns a media category for values of cells that are specific to 
	 * different versions of a media item (thumbail, preview, full)
	*/
	if (media_cat.length > 0) {
		url = "../../imports/field-meta-update/" + encodeURIComponent(source_id);
		var selected_fields = getSelectedFieldNumbers();
		var req = $.ajax({
			type: "POST",
			url: url,
			dataType: "json",
			data: {
				field_value_cat: media_cat,
				field_num: selected_fields,
				csrfmiddlewaretoken: csrftoken},
			success: assignEntityCategoryDone
		});
	}
}

function assignEntityCategoryDone(data){
	/* Shows updates to the entity value category */
	for (var i = 0, length = data.length; i < length; i++) {
		if (data[i].field_value_cat.length > 0) {
			var field_num = data[i].field_num
			var act_domID = "field-value-cat-label-" + field_num;
			var act_dom = document.getElementById(act_domID);
			act_dom.innerHTML = data[i].field_value_cat_label;
			var act_domID = "field-value-cat-id-" + field_num;
			var act_dom = document.getElementById(act_domID);
			act_dom.innerHTML = data[i].field_value_cat;
			if (data[i].field_value_cat_icon != false) {
				var act_domID = "field-val-cat-icon-" + field_num;
				var act_dom = document.getElementById(act_domID);
				act_dom.innerHTML = "<img src=\"" + data[i].field_value_cat_icon + "\" alt=\"Icon\"/>";
			}
		}
	}
}