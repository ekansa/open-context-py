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

function getTypeHierarchy(field_num) {
	/* Gets the hiearchy of child types for a general field type 
	*/
	var ft_domID = "field-type-" + field_num;
	var field_type = document.getElementById(ft_domID).innerHTML;
	field_type = 'oc-gen:' + field_type
	if (act_tree_root != field_type) {
		act_tree_root = field_type;
		url = "../../entities/hierarchy-children/" + encodeURIComponent(field_type);
		var act_domID = "tree-sel-label";
		var act_dom = document.getElementById(act_domID);
		act_dom.innerHTML = "... loading entity type categories ...";
		var act_domID = "tree-sel-id";
		var act_dom = document.getElementById(act_domID);
		act_dom.innerHTML = "";
		var act_domID = "tree-sel-icon";
		var act_dom = document.getElementById(act_domID);
		act_dom.innerHTML = "";
		var req = $.ajax({
			type: "GET",
			url: url,
			dataType: "json",
			success: getTypeHierarchyDone
		});
	}
}

var start_data = [{label: 'Type Hierarchy'}];
var tree_app;
var tree_service;
var act_tree_root = false;
(function() {
	/* Sets up the Tree view for browsing hierarchies of entity categories */
	var app;
	var deps;
	deps = ['angularBootstrapNavTree'];
	if (angular.version.full.indexOf("1.2") >= 0) {
	  deps.push('ngAnimate');
	}
	app = angular.module('TreeApp', deps);
	tree_app = app.controller('TreeController', function($scope, $timeout) {
		$scope.my_tree_handler = function(branch) {
			if (branch.id != null) {	
				var act_domID = "tree-sel-label";
				var act_dom = document.getElementById(act_domID);
				act_dom.innerHTML = branch.label;
				var act_domID = "tree-sel-id";
				var act_dom = document.getElementById(act_domID);
				act_dom.innerHTML = branch.id;
				if (branch.icon != false) {
					var act_domID = "tree-sel-icon";
					var act_dom = document.getElementById(act_domID);
					act_dom.innerHTML = "<img src=\"" + branch.icon + "\" alt=\"Icon\"/>";
				}
			}
			else{
				var act_domID = "tree-sel-label";
				var act_dom = document.getElementById(act_domID);
				act_dom.innerHTML = "Select a field first.";
			}
		};
		$scope.tree_data = start_data;
		$scope.tree_service = function(data) {
			$scope.tree_data = [];
			$scope.doing_async = true;
			return $timeout(function() {
			  $scope.tree_data = data;
			  $scope.doing_async = false;
			}, 1000);
		};
		tree_service = $scope.tree_service;
	});
	
}).call(this);

function getTypeHierarchyDone(data){
	/* Updates the Hierarchy tree with new JSON data */
	tree_service(data)
	var act_domID = "tree-sel-label";
	var act_dom = document.getElementById(act_domID);
	act_dom.innerHTML = "";
}

function assignEntityCategory() {
	/* Assigns a an entity category for values of cells that are to be
	 * reconciled in an import
	*/
	var scat_domID = "tree-sel-id";
	var field_value_cat = document.getElementById(scat_domID).innerHTML;
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