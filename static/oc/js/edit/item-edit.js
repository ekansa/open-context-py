/*
 * Functions to edit an item
 */

function getTypeHierarchy() {
	/* Gets the hiearchy of child types for the item's type 
	*/
	var field_type = 'oc-gen:' + item_type;
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

var select_cat_label = false;
var select_cat_id = false;
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
				select_cat_label = branch.label;
				select_cat_id = branch.id;
				updateCategoryButton();
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

function updateCategoryButton(){
	var act_domID = "cat-update-button-outer";
	var act_dom = document.getElementById(act_domID);
	var html = "<button type=\"button\" class=\"btn btn-info\" onclick=\"javascript:updateCategory();\">Update</button>";
	html += "<br/>Update to:<br/><small style=\"word-wrap: break-word;\">'" + select_cat_label + "'</small>";
	act_dom.innerHTML = html;
}

function getTypeHierarchyDone(data){
	/* Updates the Hierarchy tree with new JSON data */
	tree_service(data)
	var act_domID = "tree-sel-label";
	var act_dom = document.getElementById(act_domID);
	act_dom.innerHTML = "<small>Use the tree menu below to select a new category for this item.</small>";
	var act_domID = "tree-sel-id";
	var act_dom = document.getElementById(act_domID);
	act_dom.innerHTML = "";
	var act_domID = "tree-sel-icon";
	var act_dom = document.getElementById(act_domID);
	var html = "<button type=\"button\" class=\"btn btn-default btn-lg\">";
	html += "<span class=\"glyphicon glyphicon-edit\" aria-hidden=\"true\"></span>";
	html += "</button>";
	act_dom.innerHTML = html;
}












/* ---------------------------------------------------
Functions for changing the item label
------------------------------------------------------
*/
function updateLabel() {
	/* Assigns a an entity category for values of cells that are to be
	 * reconciled in an import
	*/
	var act_domID = "item-label";
	var new_label = document.getElementById(act_domID).value;
	if (new_label.length > 0) {
		url = "../../edit/update-item/" + encodeURIComponent(uuid);
		var req = $.ajax({
			type: "POST",
			url: url,
			dataType: "json",
			data: {
				label: new_label,
				csrfmiddlewaretoken: csrftoken},
			success: updateLabelDone
		});
	}
}

function updateLabelDone(data){
	// reload the whole page from the server
	// it's too complicated to change all the instances of the item label on the page,
	// easier just to reload the whole page
	console.log(data);
	location.reload(true);
}




/* ---------------------------------------------------
Functions for changing categories
------------------------------------------------------
*/
function updateCategory() {
	/* Assigns a an entity category for values of cells that are to be
	 * reconciled in an import
	*/
	if (select_cat_id.length > 0) {
		url = "../../edit/update-item/" + encodeURIComponent(uuid);
		var req = $.ajax({
			type: "POST",
			url: url,
			dataType: "json",
			data: {
				class_uri: select_cat_id,
				csrfmiddlewaretoken: csrftoken},
			success: updateCategoryDone
		});
	}
}

function updateCategoryDone(data){
	// reload the whole page from the server
	// it's too complicated to change all the instances of the item category on the page,
	// easier just to reload the whole page
	console.log(data);
	location.reload(true);
}




