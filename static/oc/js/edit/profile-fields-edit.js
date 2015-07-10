/*
 * Functions to edit a profile
 */

function profile_fields_edit(){
	this.field_uuid = "";
	this.data_type = "";
	this.label = "";
	this.profile_obj = false;
	this.addField = function(){
		//builds an interface to add a field to a group
		var main_modal_title_domID = "myModalLabel";
		var main_modal_body_domID = "myModalBody";
		var title_dom = document.getElementById(main_modal_title_domID);
		var body_dom = document.getElementById(main_modal_body_domID);
		var body_html = this.make_field_group_edit_html(false, 'open', 'New Field Group', '');
		title_dom.innerHTML = 'Add a Field to Group: "' + this.fgroup_label + '"';
		$("#myModal").modal('show');
	}
	
}