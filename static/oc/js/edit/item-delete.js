/*
 * Functions to edit multiple language strings
 */
function deleteItem(){
	this.modal_dom_id = 'delete-modal';
	this.modal_title_dom_id = 'delete-title';
	this.modal_inter_dom_id = 'delete-interface';
	this.invalid_alert_class = 'alert alert-warning';
	this.parent_obj_name = false;
	this.value_num = 0;
	this.obj_name = 'deleteItem';
	this.name = false;
	this.label = 'Label for the item to delete';
	this.dom_ids = null;
	this.edit_uuid = null;
	this.edit_type = false;
	this.act_editorial_type = 'edit-deletion';
	this.editorial_types = {};
	
	this.initialize = function(){
		if (this.parent_obj_name != false) {
			this.name = this.parent_obj_name + '.' + this.obj_name;
		}
		else{
			this.name = this.obj_name;
		}
		if (this.dom_ids == null) {
			this.dom_ids = this.default_domids(this.value_num, 'default-ml');
		}
	}
	this.default_domids = function(value_num, suffix){
		var dom_ids = {
			del_label: (value_num + '-del-label-' + suffix),  //for delete editorial label
			del_note: (value_num + '-del-note-' + suffix),  //for delete editorial note
			del_class: (value_num + '-del-class-' + suffix),  //for delete editorial class_uri
			del_submitcon: (value_num + '-del-sbcon-' + suffix), //container ID for delete submitt button
			del_respncon: (value_num + '-del-respcon-' + suffix), //container ID for delete submission response
		}
		this.dom_ids = dom_ids;
		return dom_ids;
	}
	/*************************************************
	 * Functions to generate interface HTML
	 * ***********************************************
	 */
	this.deleteInterface = function(){
		var inter_dom = document.getElementById(this.modal_inter_dom_id);
		var title_dom = document.getElementById(this.modal_title_dom_id);
		title_dom.innerHTML = 'Delete <em>"' + this.label + '"</em> ?';
		var interface_html = this.make_interface_html();
		inter_dom.innerHTML = interface_html;
		var modal_id = "#" + this.modal_dom_id;
		$(modal_id).modal('show');
	}
	this.make_interface_html = function(){
		// make the HTML for the interface
		var html = [
			'<div class="container-fluid">',
				'<div class="row">',
					'<div class="col-xs-12">',
					'Open Context organizes data by linking records together. ',
					'This means deleting records will can impact related records. ',
					'',
					'</div>',
				'</div>',
			'</div>'
		].join('\n');
		return html;
	}
	
	/*
	 * Supplemental Functions (used throughout)
	 */ 
	this.make_url = function(relative_url){
	//makes a URL for requests, checking if the base_url is set	
		 //makes a URL for requests, checking if the base_url is set
		var rel_first = relative_url.charAt(0);
		if (typeof base_url != "undefined") {
			var base_url_last = base_url.charAt(-1);
			if (base_url_last == '/' && rel_first == '/') {
				return base_url + relative_url.substring(1);
			}
			else{
				return base_url + relative_url;
			}
		}
		else{
			if (rel_first == '/') {
				return '../..' + relative_url;
			}
			else{
				return '../../' + relative_url;
			}
		}
	}
	this.make_loading_gif = function(message){
		var src = this.make_url('/static/oc/images/ui/waiting.gif');
		var html = [
			'<div class="row">',
			'<div class="col-sm-1">',
			'<img alt="loading..." src="' + src + '" />',
			'</div>',
			'<div class="col-sm-11">',
			message,
			'</div>',
			'</div>'
			].join('\n');
		return html;
	}
}