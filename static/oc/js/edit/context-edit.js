/*
 * Functions to edit context
 */
function containSortDialog(){
	var title_dom = document.getElementById('modal-small-title');
	var body_dom = document.getElementById('modal-small-body');
	title_dom.innerHTML = 'Sort contained (child) items';
	var action_button = document.getElementById('modal-small-foot-button');
	var buttonHTML = "<span class=\"glyphicon glyphicon-sort\" aria-hidden=\"true\"></span>";
    buttonHTML += " Resort Children";
	action_button.innerHTML = buttonHTML;
	action_button.onclick = updateProjectContainSort;
	var bodyHTML = [
		'This function sorts all items in a containment relationship for this entire project. ',
		'Depending on the size of the project, this process can take some time. ',
		'Because this can be time consuming, it is generally best to wait until you have ',
		'created or imported all items to this project before you resort them. ',
		'If you add more items later, they will not be in the proper sort order and you will have ',
		'to execute this process again.'
	].join('\n');
	body_dom.innerHTML = bodyHTML;
	$("#contextModal").modal('show');
}



function updateProjectContainSort() {
	/* Assigns a an entity category for values of cells that are to be
	 * reconciled in an import
	*/
	url = "../../edit/update-item/" + encodeURIComponent(uuid);
	return $.ajax({
			type: "POST",
			url: url,
			dataType: "json",
			data: {
				sort_predicate: 'oc-gen:contains',
				sort_scope: project_uuid,
				csrfmiddlewaretoken: csrftoken},
			success: updateProjectContainSortDone
	});
}

function updateProjectContainSortDone(data){
	// reload the whole page from the server
	// it's too complicated to change all the instances of the item category on the page,
	// easier just to reload the whole page
	console.log(data);
	location.reload(true);
}




