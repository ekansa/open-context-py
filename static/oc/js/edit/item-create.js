function showCreateItemInterface(type){
	/* shows an interface for creating an item
	 * 
	*/
	var main_modal_title_domID = "myModalLabel";
	var main_modal_body_domID = "myModalBody";
	var title_dom = document.getElementById(main_modal_title_domID);
	var body_dom = document.getElementById(main_modal_body_domID);
	var actInterface = new createItemInterface(type);
	title_dom.innerHTML = actInterface.title;
	body_dom.innerHTML = actInterface.body;
	$("#myModal").modal('show');
}

function createItemInterface(type){
	if (type == 'persons') {
		//make a new persons interface
		this.title = '<span class="glyphicon glyphicon-user" aria-hidden="true"></span>';
		this.title += ' Create a New Person or Organization Item';
		this.body = createPersonFields();
	}
}

function createPersonFields(){
	var html = [
	'<div>',
	'<div class="form-group">',
	'<label for="new-item-given-name">Given Name (First Name)</label>',
	'<input id="new-item-given-name" class="form-control input-sm" ',
	'type="text" value="" onchange="person_name_comp();" />',
	'</div>',
	'<div class="form-group">',
	'<label for="new-item-mid-init">Middle Initials</label>',
	'<input id="new-item-mid-init" class="form-control input-sm" style="width:15%;"',
	'type="text" value="" length="5" onchange="person_name_comp();" />',
	'</div>',
	'<div class="form-group">',
	'<label for="new-item-surname">Surname (Family Name)</label>',
	'<input id="new-item-surname" class="form-control input-sm" ',
	'type="text" value="" onchange="person_name_comp();" />',
	'</div>',
	'<div class="form-group">',
	'<label for="new-item-combined-name">Full Name</label>',
	'<input id="new-item-combined-name" class="form-control input-sm" ',
	'type="text" value="" />',
	'</div>',
	'<div class="row" id="new-person-button-row">',
		'<div class="col-xs-4">',
		'<div class="form-group">',
		'<label for="new-item-initials">Initals</label>',
		'<input id="new-item-initials" class="form-control input-sm" style="width:50%;"',
		'type="text" value="" />',
		'</div>',
		'</div>',
		'<div class="col-xs-6">',
		'<label>New Item Type</label><br/>',
		'<label class="radio-inline">',
		'<input type="radio" name="new-item-foaf-type" id="new-item-foaf-type-p" ',
		'class="new-item-foaf-type" value="foaf:Person" checked="checked">',
		'Person </label>',
		'<label class="radio-inline">',
		'<input type="radio" name="new-item-foaf-type" id="new-item-foaf-type-o" ',
		'class="new-item-foaf-type" value="foaf:Organization">',
		'Organization </label>',
		'</div>',
		'<div class="col-xs-2">',
		'<label>Create</label><br/>',
		'<button onclick="createNewPerson();">',
		'<span class="glyphicon glyphicon-plus-sign" aria-hidden="true"></span>',
		' Submit',
		'</button>',
		'</div>',
	'</div>',
	'<div class="row" id="new-person-bottom-row">',
		'<div class="col-xs-4">',
		'<div class="form-group">',
		'<label for="new-item-project-uuid">Add Item to Project UUID</label>',
		'<input id="new-item-project-uuid" class="form-control input-sm" ',
		'type="text" value="' + project_uuid + '" />',
		'</div>',
		'</div>',
		'<div class="col-xs-4">',
		'<div class="form-group">',
		'<label for="new-item-project-uuid">Source ID</label>',
		'<input id="new-item-source-id" class="form-control input-sm" ',
		'type="text" value="manual-web-form" />',
		'</div>',
		'</div>',
		'<div class="col-xs-4">',
		'</div>',
	'</div>',
	'</div>'
	].join('\n');
	return html;
}


function person_name_comp(){
	var g_name = document.getElementById("new-item-given-name").value;
	var s_name = document.getElementById("new-item-surname").value;
	var m_init = document.getElementById("new-item-mid-init").value;
	var com_dom = document.getElementById("new-item-combined-name");
	var init_dom = document.getElementById("new-item-initials");
	var com_name = [g_name, m_init, s_name].join(' ');
	var initials = g_name.charAt(0) + m_init.replace('.','') + s_name.charAt(0);
	initials = initials.toUpperCase();
	com_name = com_name.replace('  ', ' ');
	com_dom.value = com_name;
	init_dom.value = initials;
}

function createNewPerson(){
	var g_name = document.getElementById("new-item-given-name").value;
	var s_name = document.getElementById("new-item-surname").value;
	var m_init = document.getElementById("new-item-mid-init").value;
	var com_name = document.getElementById("new-item-combined-name").value;
	var initials = document.getElementById("new-item-initials").value;
	var p_types = document.getElementsByClassName("new-item-foaf-type");
	for (var i = 0, length = p_types.length; i < length; i++) {
		if (p_types[i].checked) {
			var foaf_type = p_types[i].value;
		}
	}
	var new_project_uuid = document.getElementById("new-item-project-uuid").value;
	var new_source_id = document.getElementById("new-item-source-id").value;
	var url = "../../edit/create-item-into/" + encodeURIComponent(new_project_uuid);
	var req = $.ajax({
		type: "POST",
		url: url,
		dataType: "json",
		data: {
			item_type: 'persons',
			source_id: new_source_id,
			foaf_type: foaf_type,
			combined_name: com_name,
			given_name: g_name,
			surname: s_name,
			mid_init: m_init,
			initials: initials,
			csrfmiddlewaretoken: csrftoken},
		success: createNewPersonDone
	});
}

function createNewPersonDone(data){
	var bottom_row = document.getElementById("new-person-bottom-row");
	bottom_row.innerHTML = '<div class="col-xs-12"> </div>';
	var button_row = document.getElementById("new-person-button-row");
	if (data.change.uuid != false) {
		var link_html = 'New item: <a target="_blank" ';
		link_html += 'href="../../edit/items/' + data.change.uuid + '">';
		link_html += data.change.label + '</a>';
	}
	else{
		var link_html = data.change.label;
	}
	var html = [
	'<div class="col-xs-4">',
	link_html,
	'</div>',
	'<div class="col-xs-8">',
	data.change.note,
	'</div>'
	].join('\n');
	button_row.innerHTML = html;
}