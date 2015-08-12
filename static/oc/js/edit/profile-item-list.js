/*
 * Functions for getting + dispaying lists of records created with a given profile
 */
function profile_items(profile_uuid){
	
	this.act_dom_id = false;
	this.parent_obj_name = false;
	this.name = 'profileItems';
	this.profile_uuid = profile_uuid;
	this.current_uuid = false;
	this.data =  false;
	this.error = false;
	this.start = 0;
	this.rows = 5;
	this.do_last_revised_list = false;
	this.sort_list = ['revised', 'label'];
	this.get_data = function(){
		// get the list of items from for a profile
		// with URL and parameters composed by this, the client
		var data = {
			start: this.start,
			rows: this.rows,
			sort: this.sort_list.join(',')
		};
		if (this.do_last_revised_list) {
			data.last = 1;
			data.sort = ['revised', 'label'].join(',');
		}
		var url = this.make_url("/edit/inputs/profile-item-list/") + encodeURIComponent(this.profile_uuid);
		return $.ajax({
			type: "GET",
			url: url,
			dataType: "json",
			context: this,
			data: data,
			success: this.get_dataDone,
			error: function (request, status, error) {
				alert('Sadly, could not get list of items created by this profile. Status: ' + request.status);
			} 
		});
	}
	this.get_data_by_url = function(url){
		//get data with a passed url
		return $.ajax({
			type: "GET",
			url: url,
			dataType: "json",
			context: this,
			success: this.get_dataDone,
			error: function (request, status, error) {
				alert('Sadly, could not get list of items created by this profile. Status: ' + request.status);
			} 
		});
	}
	this.get_dataDone = function(data){
		this.data = data;
		this.showData();
	}
	this.showData = function(){
		if (this.do_last_revised_list) {
			this.showListData();
		}
		else{
			this.showTableData();
		}
	}
	this.showListData = function(){
		var items_html = '';
		for (var i = 0, length = this.data.items.length; i < length; i++) {
			var item = this.data.items[i];
			if (this.current_uuid == item.uuid) {
				var item_html = [
					'<li>',
					'<strong>',
					item.label,
					'</strong>',
					'</li>',
				].join("\n");
			}
			else{
				var item_html = [
					'<li>',
					'<a href="' + this.make_url('/edit/inputs/profiles/' + this.profile_uuid + '/' + item.uuid) + '" ',
					'title="Click to edit">',
					item.label,
					'</a>',
					'</li>',
				].join("\n");
			}
			items_html += item_html;
		}
		var html = [
			'<ul>',
			items_html,
			'</ul>'
		].join("\n");
		if (document.getElementById(this.act_dom_id)) {
			document.getElementById(this.act_dom_id).innerHTML = html;
		}
		return html;
	}
	this.showTableData = function(){
		
	}
	this.make_url = function(relative_url){
		//makes a URL for requests, checking if the base_url is set
		var rel_first = relative_url.charAt(0);
		if (typeof base_url != "undefined") {
			var base_url_last = base_url.charAt(-1);
			if (base_url_last == '/' && rel_first == '/') {
				alert('hey');
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
}
