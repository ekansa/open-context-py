/*
 * ------------------------------------------------------------------
	AJAX for using the ORCID API
 * ------------------------------------------------------------------
*/


function orcidObj() {
	/* Object for composing search entities */
	this.name = "orcid"; //object name, used for DOM-ID prefixes and object labeling
	this.api_url = false;
	this.data = false;
	this.parent_dom_id = false;
	this.base_url = false;
	this.get_data = function() {
		// calls the orcid API to get data
		var url = this.api_url;
		if (url != false) {
			this.loading_data();
			return $.ajax({
				type: "GET",
				url: url,
				dataType: "json",
				headers: {          
					Accept : "application/json; charset=utf-8"
				},
				context: this,
				success: this.get_dataDone,
				error: this.get_dataError
			});
		}
	}
	this.get_dataDone = function(data){
		this.data = data;
		console.log(data);
		var act_dom = this.get_parent_dom();
		if (act_dom != false) {
			act_dom.innerHTML = "Success";
		}
	}
	this.get_dataError = function(){
		var act_dom = this.get_parent_dom();
		if (act_dom != false) {
			var html = [
			'<div class="alert alert-warning" role="alert">',
			'<span class="glyphicon glyphicon-warning-sign" aria-hidden="true"></span>',
			'Failed to load valid data from ORCID.',
			'</div>'
			].join(' ');
			act_dom.innerHTML = html;
		}
	}
	this.loading_data = function(){
		var act_dom = this.get_parent_dom();
		if (act_dom != false) {
			var html = [
			'<img style="margin-top:-4px;" height="16"  ',
			'src="' + this.base_url + '/static/oc/images/ui/waiting.gif" ',
			'alt="Loading icon..." /> ',
			'Loading profile data from ORCID...'
			].join(' ');
			act_dom.innerHTML = html;
		}
	}
	this.get_parent_dom = function(){
		var act_dom = false;
		if (this.parent_dom_id != false) {
			if (document.getElementById(this.parent_dom_id)) {
				act_dom = document.getElementById(this.parent_dom_id);
			}
		}
		return act_dom;
	}
}
