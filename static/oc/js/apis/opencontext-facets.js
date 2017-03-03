/*
 * ------------------------------------------------------------------
	Javascript and AJAX for using the Open Context API,
	to provide a user-interface that allows for searches
	of multiple facet options (boolean "OR" searches)
 * ------------------------------------------------------------------
*/


function OpenContextFacetsAPI(json_url) {
	this.or_prep_class = 'or-prep-gifs';
	this.toggle_class = 'or-options-toggle';
	this.response = 'metadata,facet';
	this.obj_name = 'oc_facets';
	this.json_url = json_url; // base url for geo-json requests) {
	this.json_url = this.json_url.replace('&amp;', '&');
	this.json_url = this.json_url.replace('response=geo-facet', 'response=' + this.response);
	this.json_data = null; // search result data
	this.selected_options = {};
	this.initialize = function(){
		if(this.json_data == null){
			this.get_api_data();
		}
		else{
			this.prep_buttons();
		}
	}
	this.get_api_data = function(){
		var url = this.json_url;
		var params = {};
		return $.ajax({
			type: "GET",
			url: url,
			data: params,
			dataType: "json",
			headers: {
				//added to get JSON data (content negotiation)
				Accept : "application/json; charset=utf-8"
			},
			context: this,
			success: this.get_api_dataDone, //do this when we get data w/o problems
			error: this.get_api_dataError //error message display
		});
	}
	this.get_api_dataDone = function(data){
		this.json_data = data;
		this.prep_buttons();
	}
	this.get_api_dataError = function(){
		
	}
	this.prep_buttons = function(){
		// prepares OR button options for a type of facet
		var gif_list = document.getElementsByClassName(this.or_prep_class);
		for (var i = 0, l_length = gif_list.length; i < l_length; i++){
			var item = gif_list[i];
			item.style.display = 'none';
		}
		var toggle_list = document.getElementsByClassName(this.toggle_class);
		for (var i = 0, l_length = toggle_list.length; i < l_length; i++){
			var item = toggle_list[i];
			item.style.display = '';
		}
	}
	this.get_facet = function(f_field_id){
		// prepares facets for retrieval
		var facet = null;
		if(this.facets == null){
			var s_f_field_id = '#' + f_field_id;
			if(this.json_data != null){
				if('oc-api:has-facets' in this.json_data){
					var facets = this.json_data['oc-api:has-facets'];
					for (var i = 0, l_length = facets.length; i < l_length; i++){
						var act_facet = facets[i];
						if(act_facet.id == f_field_id || act_facet.id == s_f_field_id){
							facet = act_facet;
							break;
						}
					}
				}
			}	
		}
		return facet;
	}
	this.get_facet_options = function(f_field_id, op_type){
		// prepares facets for retrieval
		var facet_options = [];
		var facet = this.get_facet(f_field_id);
		if(facet != null){
			if(op_type == 'id' && 'oc-api:has-id-options' in facet){
				facet_options = facet['oc-api:has-id-options'];
			}
		}  
		return facet_options;
	}
	this.show_options = function(f_field_id, op_type){
		// shows different search options, either the single (click) or the
		// multiple select for a given facet field
		var panel_dom_id = '#panel-' + f_field_id + '-' + op_type;
		$(panel_dom_id).collapse('show');
		var s_ops_dom_id = 's-ops-' + f_field_id + '-' + op_type;
		var all_m_ops_dom_id = 'all-m-ops-' + f_field_id + '-' + op_type;
		if(document.getElementById(s_ops_dom_id) && document.getElementById(all_m_ops_dom_id)){
			var single_opt_dom = document.getElementById(s_ops_dom_id);
			var multi_opt_dom = document.getElementById(all_m_ops_dom_id);
			if(single_opt_dom.style.display != 'none'){
				// hide the single options
				single_opt_dom.style.display = 'none';
				// show or make the multiple options
				multi_opt_dom.style.display = 'block';
				this.make_multi_option_html(f_field_id, op_type);
			}
			else{
				// show the single options
				single_opt_dom.style.display = 'block';
				// hide the multiple options
				multi_opt_dom.style.display = 'none';
			}
		}
	}
	
	this.make_multi_option_html = function(f_field_id, op_type){
		// makes the HTLML for the multi-selection tions for a facet field
		if(f_field_id in this.selected_options){
			var len_opts = this.selected_options[f_field_id].length;
		}
		else{
			this.selected_options[f_field_id] = [];
			var len_opts = this.selected_options[f_field_id].length;
		}
		var all_m_ops_dom_id = 'all-m-ops-' + f_field_id + '-' + op_type;
		var m_ops_dom_id = 'm-ops-' + f_field_id + '-' + op_type;
		if(document.getElementById(all_m_ops_dom_id)){
			var act_dom = document.getElementById(all_m_ops_dom_id);
			if(len_opts < 1){
				// nothing selected, so make the list new
				var html = [
					'<ul class="list-group f-opt-list" id="' + m_ops_dom_id + '">',
					this.make_options_html(f_field_id, op_type),
					'</ul>',
				].join('\n');
				act_dom.innerHTML = html;
			}
			else{
				// something was already selected, so show this
				act_dom.style.display = 'block';
			}
		}
	}
	this.make_options_html = function(f_field_id, op_type){
		// makes the multi-select HTML for the facet options
		var facet_options = this.get_facet_options(f_field_id, op_type);
		var in_class = 'm-op-' + f_field_id;
		var li_class = 'list-group-item f-opt-top';
		var html_list = [];
		for (var i = 0, l_length = facet_options.length; i < l_length; i++){
			var opt = facet_options[i];
			var opt_html = [
			'<li class="'+ li_class + '">',
				'<div class="container-fluid">',
					'<div class="row">',
						'<div class="col-xs-9 f-opt-label">',
						'<input class="' + in_class + '" type="checkbox" ',
						'onchange="' + this.obj_name + '.opt_check(\'' + f_field_id + '\', \'' + op_type + '\');" ',
						'value="' + opt.id + '" /> ',
						opt.label,
					'</div>',
					'<div class="col-xs-3 f-count">',
						'<span class="badge">' + this.number_style(opt.count) + '</span>',
					'</div>',
				'</div>',
			'</li>',	
			].join('\n');
			html_list.push(opt_html);
			li_class = 'list-group-item f-opt';
		}
		var html = html_list.join('\n');
		return html;
	}
	this.number_style = function(x) {
		// adds commas to numbers for legibility
		return x.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
	}
	this.search_button_toggle = function(f_field_id, op_type, state){
		// turns the search button on or off (visible, invisible)
		var dom_id = 'opts-do-' + f_field_id + '-' + op_type;
		if(document.getElementById(dom_id)){
			var act_dom = document.getElementById(dom_id);
			if(state == 'on'){
				act_dom.style.display = 'block';
			}
			else{
				act_dom.style.display = 'none';
			}
		}
	}
	this.single_multi_toggle = function(f_field_id, op_type, state){
		// turns button on or off (visible, invisible) for switching
		// between single select links and multi-select check boxes
		var dom_id = 'opts-show-' + f_field_id + '-' + op_type;
		if(document.getElementById(dom_id)){
			var act_dom = document.getElementById(dom_id);
			if(state == 'on'){
				act_dom.style.display = 'block';
			}
			else{
				act_dom.style.display = 'none';
			}
		}
	}
	this.opt_check = function(f_field_id, op_type){
		// executed when a user checks or unchecks a multi-select option
		var sel_options = this.get_selected_options(f_field_id);
		console.log(sel_options);
		if(sel_options.length > 0){
			// alert(sel_options.length);
			this.search_button_toggle(f_field_id, op_type, 'on');
			this.single_multi_toggle(f_field_id, op_type, 'off');
		}
		else{
			this.search_button_toggle(f_field_id, op_type, 'off');
			this.single_multi_toggle(f_field_id, op_type, 'on');
		}
	}
	this.get_selected_options = function(f_field_id){
		var sel_options = [];
		var in_class = 'm-op-' + f_field_id;
		var ops_list = document.getElementsByClassName(in_class);
		for (var i = 0, l_length = ops_list.length; i < l_length; i++){
			var item = ops_list[i];
			if(item.checked){
				sel_options.push(item.value);
			}
		}
		return sel_options;
	}
}
