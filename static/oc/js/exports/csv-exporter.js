/*
 * Functions to edit spatial coodinates and time ranges
 */
function CSVexporter(total_results){
	this.modal_id = 'searchModal';
	this.total_results = total_results;
	this.current_export_page = 0;
	this.total_export_pages = 0;
	this.records_per_page = 100;
	this.data = false;
	this.show_interface = function(){
		/* shows an interface for creating an item
		 * 
		*/
		var main_modal_title_domID = this.modal_id + "Label";
		var main_modal_body_domID = this.modal_id + "Body";
		var title_dom = document.getElementById(main_modal_title_domID);
		title_dom.innerHTML = 'Export These ' + this.total_results + ' Records in a Table (CSV)';
		var body_dom = document.getElementById(main_modal_body_domID);
		$("#" + this.modal_id).modal('show');
	}
	this.reset = function(){
		/* shows an interface for creating an item
		 * 
		*/
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