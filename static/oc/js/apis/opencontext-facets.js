/*
 * ------------------------------------------------------------------
	Javascript and AJAX for using the Open Context API,
	to provide a user-interface that allows for searches
	of multiple facet options (boolean "OR" searches)
 * ------------------------------------------------------------------
*/


function OpenContextFacetsAPI() {
	this.obj_name = 'oc_facets';
	this.field_options = {};  // object with field_id as key for list of options objects
	
	this.show_options = function(f_field_id, op_type){
		// shows different search options, either the single (click) or the
		// multiple select for a given facet field
		var dom_ids = this.make_dom_ids(f_field_id, op_type);
		var panel_dom_id = '#' + dom_ids.panel;
		$(panel_dom_id).collapse('show');
		if(document.getElementById(dom_ids.single_ops) && document.getElementById(dom_ids.multi_ops)){
			var single_opt_dom = document.getElementById(dom_ids.single_ops);
			var multi_opt_dom = document.getElementById(dom_ids.multi_ops);
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
	
	this.get_field_options_from_html = function(f_field_id, op_type){
		// gets the field options from the HTML dom
		var options = [];
		var dom_ids = this.make_dom_ids(f_field_id, op_type);
		var ops_list = document.getElementsByClassName(dom_ids.single_op_class);
		for (var i = 0, l_length = ops_list.length; i < l_length; i++){
			var a_opt = ops_list[i];
			var opt = {
				id: a_opt.href,
			    label: a_opt.innerHTML,
				count: parseInt(a_opt.getAttribute('data-count'))
			};
			options.push(opt);
		}
		this.field_options[f_field_id] = options;
		return options;
	}
	
	this.make_multi_option_html = function(f_field_id, op_type){
		// makes the HTLML for the multi-selection tions for a facet field
		var dom_ids = this.make_dom_ids(f_field_id, op_type);
		if(f_field_id in this.field_options){
			var len_opts = this.field_options[f_field_id].length;
		}
		else{
			this.field_options[f_field_id] = [];
			var len_opts = this.field_options[f_field_id].length;
		}
		
		if(document.getElementById(dom_ids.multi_ops)){
			var act_dom = document.getElementById(dom_ids.multi_ops);
			if(len_opts < 1){
				// nothing selected, so make the list new
				var html = [
					'<ul class="list-group f-opt-list" id="' + dom_ids.mult_ops_list + '">',
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
		var dom_ids = this.make_dom_ids(f_field_id, op_type);
		var facet_options = this.get_field_options_from_html(f_field_id, op_type);
		var li_class = 'list-group-item f-opt-top';
		var html_list = [];
		for (var i = 0, l_length = facet_options.length; i < l_length; i++){
			var opt = facet_options[i];
			var opt_html = [
			'<li class="'+ li_class + '">',
				'<div class="container-fluid">',
					'<div class="row">',
						'<div class="col-xs-9 f-opt-label">',
						'<input class="' + dom_ids.sel_class + '" type="checkbox" ',
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
	
	this.opt_check = function(f_field_id, op_type){
		// executed when a user checks or unchecks a multi-select option
		var dom_ids = this.make_dom_ids(f_field_id, op_type);
		var sel_options = this.get_selected_options(f_field_id);
		if(document.getElementById(dom_ids.control)){
			var act_dom = document.getElementById(dom_ids.control);
			if(sel_options.length > 0){
				// fill the control area with a search button html
				act_dom.innerHTML = this.make_search_execute_html(f_field_id, op_type, sel_options.length);
			}
			else{
				// fill the control area with a toggle button html
				act_dom.innerHTML = this.make_options_toggle_html(f_field, op_type);
			}
		}
	}
	
	this.get_selected_options = function(f_field_id){
		// gets the list of options checked for selection
		var dom_ids = this.make_dom_ids(f_field_id, '');
		var sel_options = [];
		var ops_list = document.getElementsByClassName(dom_ids.sel_class);
		for (var i = 0, l_length = ops_list.length; i < l_length; i++){
			var item = ops_list[i];
			if(item.checked){
				sel_options.push(item.value);
			}
		}
		return sel_options;
	}
	
	this.search_options = function(f_field_id, op_type){
		// executes the actual search
		var dom_ids = this.make_dom_ids(f_field_id, op_type);
		var sel_options = this.get_selected_options(f_field_id);
		if(sel_options.length > 0 && document.getElementById(dom_ids.control)){
			// make the spinny gif to show we're loading the next page
			var act_dom = document.getElementById(dom_ids.control);
			act_dom.innerHTML = this.make_searching_html(sel_options.length);
			
			// now compute the search URL
			var difs_list = [];
			var first_url = sel_options[0];
			for (var i = 0, l_length = sel_options.length; i < l_length; i++){
				var id = sel_options[i];
				var act_dif = this.find_url_dif(first_url, id);
				if(act_dif.o != false && act_dif.n != false){
					// only add the differences if they exist
					difs_list.push(act_dif);
				}
			}
			if(difs_list.length > 0){
				var query_opts = [];
				var url = difs_list[0].pre; // start the URL with the pre difference string
				query_opts.push(difs_list[0].o); // add the first, original option as a query option
				for (var i = 0, l_length = difs_list.length; i < l_length; i++){
					var act_dif = difs_list[i];
					query_opts.push(act_dif.n); // add the new query option
				}
				url += query_opts.join('||'); // add the different query options to the url, with || delim
				url += difs_list[0].post; // now complete the url with the rest of the parameters following the dif
			}
			else{
				var url = first_url; // only 1 option selected.
			}
			// console.log(url);
			// do the actual search
			window.open(url, '_self');
		}
		else{
			alert('Select a search option first.');
		}
	}
	
	this.find_url_dif = function( o_str, n_str) {
		// this function compares different Open Context query URLs to
		// find parameter is different. The o_str is the URL that gets
		// compared against the n_str.
		// it returns an object with the original 'o' parameter value,
		// the new 'n' parameter value,
		// and the string before the difference 'pre',
		// and the string after the difference 'post'
		// this assumes only 1 difference between the URLs !!!!
		
		// first break the URLs into parts, preserving the delimiters
		var separators = ['(/)', '(---)', '(\\\?)', '(\\\&)', '(\\\=)'];
		var o_parts = o_str.split(new RegExp(separators.join('|'), 'g'));
		var n_parts = n_str.split(new RegExp(separators.join('|'), 'g'));
		// console.log({o_parts: o_parts, n_parts: n_parts})
		var dif = {
			o: false,
			n: false,
			pre: '',
			post: ''
		};
		var dif_found = false;
		if (o_parts.length == n_parts.length){
			// equivalent length lists for both URLs so safe to compare differences
			for (var i = 0, l_length = o_parts.length; i < l_length; i++){
				var str_ok = false;
				var o_part = o_parts[i];
				var n_part = n_parts[i];
				if(typeof o_part === 'string' || o_part instanceof String){
					if(typeof n_part === 'string' || n_part instanceof String){
						// we've got strings, not undefined parts.
						str_ok = true;
					}
				}
				if(str_ok){
					// we've got OK strings, so do comparison
					if(o_part != n_part && dif_found == false){
						// we've found the parameter value with the difference
						dif_found = true;
						dif.o = o_part;
						dif.n = n_part;
					}
					else if(o_part == n_part && dif_found == false){
						// haven't found a difference yet, so add to the 'pre'
						// difference string
						dif.pre += o_part;
					}
					else{
						if(dif_found){
							// we've found the difference already so
							// add to the post difference string
							dif.post += o_part;
						}
					}
				}
			}
		}
		return dif;
	}
	
	this.make_options_toggle_html = function(f_field_id, op_type){
		var dom_ids = this.make_dom_ids(f_field_id, op_type);
		var html = [
			'<a class="or-options-toggle" id="' + dom_ids.tog + '" ',
			'onclick="'+ this.obj_name + '.show_options(\''+ f_field_id + '\', \'' + op_type + '\');" ',
			'title="Select multiple options">',
                '<span class="glyphicon glyphicon-option-vertical" aria-hidden="true"></span>',
            '</a>'
		].join('\n');
		return html;
	}
	
	this.make_search_execute_html = function(f_field_id, op_type, num_sel){
		var dom_ids = this.make_dom_ids(f_field_id, op_type);
		var title = 'Search selected ' + num_sel + ' option(s)';
		var html = [
			'<a class="or-options-toggle" id="' + dom_ids.search + '" ',
			'class="text-primary" ',
			'onclick="'+ this.obj_name + '.search_options(\''+ f_field_id + '\', \'' + op_type + '\');" ',
			'title="' + title + '">',
                '<span class="glyphicon glyphicon-search text-primary" aria-hidden="true"></span>',
            '</a>'
		].join('\n');
		return html;
	}
	
	this.make_searching_html = function(num_sel){
		var title = 'Running search on ' + num_sel + ' option(s)';
		var html = [
			'<img style="margin-top:-4px;" height="16" ',
			'src="' + base_url + '/static/oc/images/ui/waiting.gif" ',
			'alt="Loading icon..." title="' + title + '" />'
		].join('\n');
		return html;
	}
	
	this.make_dom_ids = function(f_field_id, op_type){
		var id_part = f_field_id + '-' + op_type
		var dom_ids = {
			control: 'opts-control-' + id_part,  // heading where control buttons go
			tog: 'opts-show-' + id_part,  // toggle button for single, multiple search
			search: 'opts-do-' + id_part,  // search button
			panel: 'panel-' + id_part, // panel id
			single_ops: 's-ops-' + id_part, // list of single select options
			multi_ops: 'all-m-ops-' + id_part, // multi select options
			mult_ops_list: 'm-ops-' + id_part, // id for ul of mult-select options list
			sel_class: 'm-op-' + f_field_id,  // class for multiple select options
			single_op_class: 'f-op-l-' + id_part,  // class for single select options
		}
		return dom_ids;
	}
}
