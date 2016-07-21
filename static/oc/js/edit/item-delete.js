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
			lang_out: (value_num + '-field-fcl-' + suffix),  //for language adding options
			lang_sel: (value_num + '-field-lang-sel-' + suffix),  //for language selection input
			lang_literal: (value_num + '-field-lang-lit-' + suffix),  //for language text literal
			lang_valid: (value_num + '-field-lang-valid-' + suffix), //container ID for language validation feedback
			lang_valid_val: (value_num + '-field-lang-valid-val-' + suffix), //hidden input field for language value validation results
			lang_submitcon: (value_num + '-field-lang-sbcon-' + suffix), //container ID for language submitt button
			lang_respncon: (value_num + '-field-lang-respcon-' + suffix), //container ID for language submission response
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
		title_dom.innerHTML = 'Delete "<em>' + this.label + '</em>"?';
		var interface_html = this.make_localize_string_interface_html(null);
		inter_dom.innerHTML = interface_html;
		var modal_id = "#" + this.modal_dom_id;
		$(modal_id).modal('show');
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