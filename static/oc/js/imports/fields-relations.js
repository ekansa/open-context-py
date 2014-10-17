var start_data = [{label: 'Containment Hierarchy'}];
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



/* ----------------------------------------------------
 * Functions to DELETE field annotations
 *
 * ----------------------------------------------------
*/

function deleteAnnotation(annotation_id){
	/* AJAX call to search entities filtered by a search-string */
	var url = "../../imports/field-annotation-delete/" + encodeURIComponent(source_id) + "/" + annotation_id;
	var req = $.ajax({
		type: "POST",
		url: url,
		dataType: "json",
		data: {csrfmiddlewaretoken: csrftoken},
		success: deleteAnnotationDone
	});
}

function deleteAnnotationDone(data){
	/* Finish delete by showing updated list of annotations */
	displayAnnotations(data);
}





/* ----------------------------------------------------
 * Functions to add annotations to fields
 *
 * ----------------------------------------------------
*/

function displayAnnotations(data){
	/* Displays annotations after updates, data is JSON data from AJAX response */
	var tbodyDom = document.getElementById("fieldAnnotationsTbody");
	tbodyDom.innerHTML = "";
	for (var i = 0, length = data.length; i < length; i++) {
		var anno = data[i];
		var newRow = document.createElement("tr");
		newRow.id = "anno-num-" + anno.id;
		var rowString = [
			"<td>",
			"<button onclick=\"javascript:deleteAnnotation(" + anno.id +" );\" type=\"button\" class=\"btn btn-warning btn-xs\">",
			"<span class=\"glyphicon glyphicon-remove\"></span>",
			"</button>",
			"</td>",
			"<td>",
			"<span id=\"sub-label-" + anno.id +"\">" + anno.subject.label + "</span>",
			"<br/>",
			"<samp>",
			"<small>Import field</small>",
			"<small id=\"sub-id-" + anno.id + "\">" + anno.subject.id + "</small>",
			"</samp>",
			"</td>",
			"<td>",
			"<span id=\"pred-label-" + anno.id +"\">" + anno.predicate.label + "</span>",
			"<br/>",
			"<samp>",
			"<small id=\"pred-id-" + anno.id + "\">" + anno.predicate.id + "</small>",
			"</samp>",
			"</td>",
			"<td>",
			"<span id=\"obj-label-" + anno.id + "\">" + anno.object.label + "</span>",
			"<br/>",
			"<samp>",
			"<small id=\"obj-type-" + anno.id + "\">" + anno.object.type + "</small>",
			"<small id=\"obj-id-" + anno.id + "\">" + anno.object.id + "</small>",
			"</samp>",
			"</td>"
		].join("\n");
		newRow.innerHTML = rowString;
		tbodyDom.appendChild(newRow);
	}
}

function addRelInterface(predicate_id){
	var title_domID = "myModalLabel";
	var title_dom = document.getElementById(title_domID);
	if (predicate_id == "oc-gen:contains") {
		title_dom.innerHTML = "Add <strong>Containment</strong> Relation";
	}
	else if (predicate_id == "oc-gen:contained-in") {
		title_dom.innerHTML = "Add <strong>Contained in</strong> [a subject entity] Relation";
	}
	else{
		title_dom.innerHTML = "Go away and never come back";
	}
	var modal = $("#myModal").modal("show");
}

