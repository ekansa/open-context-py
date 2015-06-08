/*
 * Functions to edit an item
 */
var contextSearchObj = false;
var childSearchObj = false;
var act_item = false;
function start(){
	/* Thing to do on page load 
	*/
	act_item = new item_object(item_type, uuid);
	var exec_after_data_get = {
		exec: function(){
				// add event (geospatial, chronology) list
				displayEvents(); // defined in edit/geo-chrono-edit.js
			}
		};
	act_item.exec_after_data_get = exec_after_data_get;
	act_item.getItemData();
	console.log(act_item);
	getTypeHierarchy();
	if (item_type == 'subjects') {
		// add an object for searching parent entities defined in entities/entities.js
		contextSearchObj = new searchEntityObj();
		contextSearchObj.name = "contextSearchObj";
		contextSearchObj.interfaceDomID = "sel-parent-entities";
		contextSearchObj.entities_panel_title = "Context Lookup";
		contextSearchObj.limit_item_type = "subjects";
		var afterSelectDone = {
		exec: function(){
				// turn on the update button if there's an ID selected
				var dom_id = "contextSearchObj-sel-entity-id";
				if (document.getElementById(dom_id).value.length > 0) {
					document.getElementById("change-parent-button").disabled = "";
				}
			}
		};
		contextSearchObj.afterSelectDone = afterSelectDone;
		contextSearchObj.generateEntitiesInterface(true, false);
		
		// add an object for search for new child entities, defined in entities/entities.js
		childSearchObj = new searchEntityObj();
		childSearchObj.name = "childSearchObj";
		childSearchObj.interfaceDomID = "sel-child-entities";
		childSearchObj.entities_panel_title = "Child Item Lookup";
		childSearchObj.limit_item_type = "subjects";
		var afterSelectDone = {
		exec: function(){
				// turn on the update button if there's an ID selected
				var dom_id = "childSearchObj-sel-entity-id";
				if (document.getElementById(dom_id).value.length > 0) {
					document.getElementById("add-child-button").disabled = "";
				}
			}
		};
		childSearchObj.afterSelectDone = afterSelectDone;
		childSearchObj.generateEntitiesInterface(true, false);
	}
	
}




function getTypeHierarchy() {
	/* Gets the hiearchy of child types for the item's type 
	*/
	var act_domID = "tree-sel-label";
	var field_type = 'oc-gen:' + item_type;
	if (act_tree_root != field_type && document.getElementById(act_domID)) {
		act_tree_root = field_type;
		url = "../../entities/hierarchy-children/" + encodeURIComponent(field_type);
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
	/* Simple changes of labeling
	 * for items
	*/
	var act_domID = "item-label";
	var new_label = document.getElementById(act_domID).value;
	if (new_label.length > 0) {
		url = "../../edit/update-item-basics/" + encodeURIComponent(uuid);
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
	else{
		alert('Cannot have a blank value for a label.')
	}
}

function updatePersonNames(){
	// more complicated changes of labels and names for person items
	var g_name = document.getElementById("pers-given-name").value;
	var s_name = document.getElementById("pers-surname").value;
	var com_name = document.getElementById("pers-combined-name").value;
	var initials = document.getElementById("pers-initials").value;
	if (com_name.length > 0) {
		url = "../../edit/update-item-basics/" + encodeURIComponent(uuid);
		var req = $.ajax({
			type: "POST",
			url: url,
			dataType: "json",
			data: {
				label: com_name,
				combined_name: com_name,
				given_name: g_name,
				surname: s_name,
				initials: initials,
				csrfmiddlewaretoken: csrftoken},
			success: updateLabelDone
		});
	}
	else{
		alert('Cannot have a blank value for a full name.')
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
		url = "../../edit/update-item-basics/" + encodeURIComponent(uuid);
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

function updatePersonCategory(){
	// updates a category for a person item
	var p_types = document.getElementsByClassName("person-foaf-type");
	for (var i = 0, length = p_types.length; i < length; i++) {
		if (p_types[i].checked) {
			var foaf_type = p_types[i].value;
		}
	}
	url = "../../edit/update-item-basics/" + encodeURIComponent(uuid);
	var req = $.ajax({
		type: "POST",
		url: url,
		dataType: "json",
		data: {
			class_uri: foaf_type,
			csrfmiddlewaretoken: csrftoken},
		success: updateCategoryDone
	});
}

function updateCategoryDone(data){
	// reload the whole page from the server
	// it's too complicated to change all the instances of the item category on the page,
	// easier just to reload the whole page
	console.log(data);
	location.reload(true);
}



/* ---------------------------------------------------
Functions for changing short descriptions and content
------------------------------------------------------
*/
function updateShortDescriptionText() {
	/* updates the short description of a project item
	*/
	var act_domID = "sd-string-content";
	var content = document.getElementById(act_domID).value;
	var url = "../../edit/update-item-basics/" + encodeURIComponent(uuid);
	var act_icon = document.getElementById('sd-text-content-valid-icon');
	act_icon.innerHTML = '';
	var act_note = document.getElementById('sd-text-content-valid-note');
	act_note.innerHTML = 'Uploading and validating...';
	var req = $.ajax({
		type: "POST",
		url: url,
		dataType: "json",
		data: {
			content: content,
			content_type: 'short_des',
			csrfmiddlewaretoken: csrftoken},
		success: updateContentDone
	});
}

function updateContent() {
	/* updates the main content of an item (project, document, or table abstract)
	*/
	var act_domID = "main-string-content";
	var content = document.getElementById(act_domID).value;
	var url = "../../edit/update-item-basics/" + encodeURIComponent(uuid);
	var act_icon = document.getElementById('text-content-valid-icon');
	act_icon.innerHTML = '';
	var act_note = document.getElementById('text-content-valid-note');
	act_note.innerHTML = 'Uploading and validating...';
	var req = $.ajax({
		type: "POST",
		url: url,
		dataType: "json",
		data: {
			content: content,
			content_type: 'content',
			csrfmiddlewaretoken: csrftoken},
		success: updateContentDone
	});
}

function updateContentDone(data){
	// display HTML validation results
	var valid_html = true;
	var html_message = 'Text OK in HTML';
	if ('errors' in data) {
		var errors = data.errors;
		if ('html' in errors) {
			if (errors.html != false) {
				valid_html = false;
				html_message = errors.html;
			}
		}
	}
	if (data.change.prop == 'short_des') {
		var act_icon = document.getElementById('sd-text-content-valid-icon');
		var act_note = document.getElementById('sd-text-content-valid-note');
	}
	else {
		var act_icon = document.getElementById('text-content-valid-icon');
		var act_note = document.getElementById('text-content-valid-note');
	}
	if (valid_html) {
		act_icon.innerHTML = '<span class="glyphicon glyphicon-ok-circle text-success" aria-hidden="true"></span>';
		act_note.innerHTML = '<p class="text-success">' + html_message + '</p>';
	}
	else{
		act_icon.innerHTML = '<span class="glyphicon glyphicon-warning-sign text-warning" aria-hidden="true"></span>';
		act_note.innerHTML = '<p class="text-warning">' + html_message + '</p>';
	}
}




