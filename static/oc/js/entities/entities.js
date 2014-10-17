/*
 * ------------------------------------------------------------------
	AJAX for entity searches
 * ------------------------------------------------------------------
*/

/* DOM id for input element with search string */
var act_domID = "entity-string"; 
/* DOM id for <ul> element where entity search results go */
var searchEntityListDomID = "search-entity-list";
var selectFoundEntityFunction = "selectEntity";

function searchEntities(){
	/* AJAX call to search entities filtered by a search-string */
	var act_domID = "entity-string";
	var qstring = document.getElementById(act_domID).value;
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
	var searchEntityListDom = document.getElementById(searchEntityListDomID);
	searchEntityListDom.innerHTML = "";
	for (var i = 0, length = data.length; i < length; i++) {
		var newListItem = document.createElement("li");
		newListItem.id = "search-entity-item-" + i;
		var entityString = "<a href=\"javascript:" + selectFoundEntityFunction + "(" + i + ")\" id=\"search-entity-label-" + i + "\" >" + data[i].label + "</a>";
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