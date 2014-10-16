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


function searchEntities(){
	/* AJAX call to search entities filtered by a search-string */
	var act_domID = "entity-string";
	var qstring = document.getElementById(act_domID).value;
	var searchEntityListDomID = "search-entity-list";
	var searchEntityListDom = document.getElementById(searchEntityListDomID);
	searchEntityListDom.innerHTML = "<li>Searching for '" + qstring + "'...</li>";
	var url = "../../entities/look-up/0";
	var req = $.ajax({
		type: "GET",
		url: url,
		dataType: "json",
		data: { q:qstring },
		success: searchEntitiesDone
	});
}


function searchEntitiesDone(data){
	/* Displays list of entities that meet search criteria */
	var searchEntityListDomID = "search-entity-list";
	var searchEntityListDom = document.getElementById(searchEntityListDomID);
	searchEntityListDom.innerHTML = "";
	for (var i = 0, length = data.length; i < length; i++) {
		var newListItem = document.createElement("li");
		newListItem.id = "search-entity-item-" + i;
		var entityString = "<a href=\"javascript:selectEntity(" + i + ")\" id=\"search-entity-label-" + i + "\" >" + data[i].label + "</a>";
		entityString += "<br/><small id=\"search-entity-id-" + i + "\">" + data[i].id + "</small>";
		newListItem.innerHTML = entityString;
		searchEntityListDom.appendChild(newListItem);
	}
}

function selectEntity(item_num) {
	/* Adds selected entity label and ID to the right dom element */
	var act_domID = "search-entity-id-" + item_num;
	var item_id = document.getElementById(act_domID).innerHTML;
	var sel_id_dom = document.getElementById("sel-entity-id");
	sel_id_dom.value = item_id;
	act_domID =  "search-entity-label-" + item_num;
	var item_label = document.getElementById(act_domID).innerHTML;
	var sel_label_dom = document.getElementById("sel-entity-label");
	sel_label_dom.value = item_label;
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

