/*
 * Functions to edit spatial coodinates and time ranges
 */
function CSVexporter(json_url, total_results){
	this.obj_name = 'CSVexporter';
	this.json_url = json_url; // base url for geo-json requests
	this.meta_facets_url = false; 
	this.modal_id = 'searchModal';
	this.total_results = total_results;
	this.current_export_page = 0;
	this.total_export_pages = 0;
	this.records_per_page = 100;
	this.data = [];
	this.metadata = false;
	this.added_field_slug_list = [];
	this.default_add_common_fields = true;
	this.default_field_mappings = {
		'uri': 'URI',
		'citation uri': 'Citation URI',
		'label': 'Item Label',
		'project label': 'Project Label',
		'project uri': 'Project URI',
		'context label': 'Context',
		'context uri': 'Context URI',
		'latitude': 'Latitude (WGS-84)',
		'longitude': 'Longitude (WGS-84)',
		'early bce/ce': 'Early BCE/CE',
		'late bce/ce': 'Late BCE/CE',
		'item category': 'Item Category',
		'published': 'Published Date',
		'updated': 'Updated Date',
	};
	this.show_interface = function(){
		/* shows an interface for creating an item
		 * 
		*/
		var main_modal_title_domID = this.modal_id + "Label";
		var main_modal_body_domID = this.modal_id + "Body";
		var title_dom = document.getElementById(main_modal_title_domID);
		title_dom.innerHTML = 'Export These ' + this.total_results + ' Records: Data Table (CSV) or GIS (GeoJSON)';
		var body_dom = document.getElementById(main_modal_body_domID);
		body_dom.innerHTML = this.make_interface_body_html();
		$("#" + this.modal_id).modal('show');
		if (this.metadata == false) {
			this.ajax_get_meta_facets().then(this.show_attributes_html);
		}
		else{
			this.show_attributes_html();
		}
	}
	this.make_interface_body_html = function(){
		/* shows an interface for creating an item
		 * 
		*/
		var html = [
		'<div>',
		    '<h4>About Exporting these Search Results</h4>',
			'<p class="small">',
			'This tool exports the current set of records as a data table or a GIS output. ',
			'For convenience, these outputs represent data in somewhat simplified formats. ',
			'If you need more expressive and complete representations of these data, please see the ',
			'<a href="' + base_url + '/about/services" target="_blank">API documentation</a>. ',
			'Please also note that geospatial data for certain records may be approximated ',
			'as a security precaution. The API provides full documentation about geospatial precision for ',
			'each record of data.',
			'</p>',
			'<div class="well well-sm" id="metadata-attributes">',
			'</div>',
		'</div>'
		].join('\n');
		return html;
	}
	this.show_attributes_html = function(){
		if (document.getElementById('metadata-attributes')) {
			var meta_dom = document.getElementById('metadata-attributes');
			meta_dom.innerHTML = this.make_loading_gif('Preparing attribute options...');
			
			var default_fields = [];
			for (var key in this.default_field_mappings) {
				if (this.default_field_mappings.hasOwnProperty(key)) {
					var default_field = this.default_field_mappings[key];
					default_fields.push(default_field);
				}
			}
			var default_fields_html = default_fields.join(', ');
			if (this.added_field_slug_list.length > 0) {
				default_fields_html += ', ';
			}
			var attribute_choices_html = this.makes_attribute_choices_html();
			var added_fields_html = this.make_added_fields_html();
			var html = [
			'<h4>Data Attributes Included in Export</h4>',
			'<div class="row">',
				'<div class="col-sm-4">',
					'<label>Export Fields / Attributes</label><br/>',
					'<samp class="small">' + default_fields_html,
					'<span id="added-attributes">' + added_fields_html + '</samp>',
					'</samp>',
				'</div>',
				'<div class="col-sm-1">',
				'</div>',
				'<div class="col-sm-7">',
					'<label>Additional Fields / Attributes to Choose</label><br/>',
					'<div id="attribute-lists">',
					attribute_choices_html,
					'</div>',
				'</div>',	
			'</div>'
			].join('\n');
			meta_dom.innerHTML = html;
			this.default_add_common_fields = false;
		}
	}
	this.make_added_fields_html = function(){
		// makes HTML for fields a user wants to add to the export table
		if (this.added_field_slug_list.length < 1) {
			var html = '';
		}
		else{
			// we have added field slugs
			var html_list = [];
			for (var i = 0; i < this.added_field_slug_list.length; i++) {
				var slug = this.added_field_slug_list[i];
				var label = this.get_field_val_from_metadata(slug, 'label');
				if (label == false) {
					label = '';
				}
				if (label.length > 36) {
					label = label.substring(0, 34) + '..';
				}
				
				var item_html = [
					'<button type="button" class="btn btn-default btn-xs" ',
					'onclick="' + this.obj_name + '.removeAttribute(\'' + slug + '\');">',
					label,
					'<span style="margin-left: 5px;" ',
					'class="glyphicon glyphicon-remove-circle" aria-hidden="true"></span>',
					'</button>',
				].join('');
				html_list.push(item_html);
			}
			var html = html_list.join('\n');
		}
		return html;
	}
	this.removeAttribute = function(slug){
		// removes the slug from the added_field_slug_list
		for(var i = this.added_field_slug_list.length - 1; i >= 0; i--) {
			if(this.added_field_slug_list[i] == slug) {
			   this.added_field_slug_list.splice(i, 1);
			}
		}
		// now update all of the attributes
		this.show_attributes_html();
	}
	this.addAttribute = function(slug){
		//add a slug to the added attributes list
		this.added_field_slug_list.push(slug);
		// now update all of the attributes
		this.show_attributes_html();
	}
	this.makes_attribute_choices_html = function(){
		var html = '';
		var attribute_lists = this.make_attribute_choices_lists();
		var list_count = this.count_obj_keys(attribute_lists);
		if (list_count > 0) {
			//code for multiple lists
			var all_id = 'attributes-accordion-panels';
			var html_list = [
				'<div class="panel-group small" id="' + all_id + '" role="tablist" aria-multiselectable="true">',
			];
			var exp = 'true';
			var t_class = '';
			var b_class = 'panel-collapse collapse in';
			for (var key in attribute_lists) {
				if (attribute_lists.hasOwnProperty(key)) {
					var act_atts = attribute_lists[key];
					var id_root = 'attribute-sel-' + key;
					var h_id = id_root + '-head';
					var b_id = id_root + '-body';
					var panel_title = act_atts['type'] + ' ' + act_atts['label'] + ' Fields';
					var panel_html = [
					'<div class="panel panel-default">',
						'<div class="panel-heading" role="tab" id="' + h_id + '">',
							'<h4 class="panel-title">',
							'<a role="button" data-toggle="collapse" ' + t_class,
							'data-parent="#' + all_id + '" href="#' + b_id +'" ',
							'aria-expanded="'+ exp + '" aria-controls="' + b_id +'">',
							panel_title,
							'</a>',
							'</h4>',
						'</div>',
						'<div id="' + b_id +'" class="' + b_class + '" ',
						'role="tabpanel" aria-labelledby="' + h_id + '">',
							'<div class="panel-body">',
							this.make_attributes_html(act_atts['list'], id_root),
							'</div>',
						'</div>',
					'</div>',
					].join('\n');
					html_list.push(panel_html);
					exp = 'false';
					t_class = ' class="collapsed" ';
					b_class = 'panel-collapse collapse';
				}
			}
			html_list.push('</div>');
			html = html_list.join('\n');
		}
		return html;
	}
	this.make_attribute_choices_lists = function(){
		var attribute_lists = {
			'ld': {	'label': 'Classification',
					'type': 'Common Standards',
					'list': []},
			'id': {	'label': 'Classification',
					'type': 'Project Specific',
					'list': []},
			'text': {	'label': 'Textual',
						'type': 'Project Specific',
						'list': []},
			'date': {	'label': 'Date',
						'type': 'Project Specific',
						'list': []},
			'numeric': {'label': 'Numeric',
						'type': 'Project Specific',
						'list': []},
		};
		if (this.metadata != false) {
			if (this.metadata['oc-api:has-facets'] !== undefined) {
				for (var i = 0; i < this.metadata['oc-api:has-facets'].length; i++) {
					var facet_group = this.metadata['oc-api:has-facets'][i];
					if (facet_group['rdfs:isDefinedBy'] !== undefined) {
						if (facet_group['rdfs:isDefinedBy'] == 'oc-api:facet-prop-ld'){
							// Linked data / common standards attributes
							attribute_lists['ld']['list'] = this.get_options_from_facet_group(facet_group, 'oc-api:has-id-options');
						}
						else if (facet_group['rdfs:isDefinedBy'] == 'oc-api:facet-prop-var'){
							// Linked data / common standards attributes
							attribute_lists['id']['list'] = this.get_options_from_facet_group(facet_group, 'oc-api:has-id-options');
							attribute_lists['numeric']['list'] = this.get_options_from_facet_group(facet_group, 'oc-api:has-numeric-options');
							attribute_lists['date']['list'] = this.get_options_from_facet_group(facet_group, 'oc-api:has-date-options');
							attribute_lists['text']['list'] = this.get_options_from_facet_group(facet_group, 'oc-api:has-text-options');
						}
						else{
							// twiddle thumbs
						}
					}
				}
			}
		}
		
		// now delete the keys for empty lists
		for (var key in attribute_lists) {
			if (attribute_lists.hasOwnProperty(key)) {
				if (attribute_lists[key]['list'].length < 1) {
					delete attribute_lists[key];
				}
			}
		}
		return attribute_lists;
	}
	this.make_attributes_html = function(attribute_list, par_id_root){
		
		var freq_lists = this.make_attributes_feq_lists(attribute_list);
		var all_id = 'freq-attributes-accordion-panels-' + par_id_root;
		var html_list = [
			'<div class="panel-group" id="' + all_id + '" role="tablist" aria-multiselectable="true">',
		];
		var exp = 'true';
		var t_class = '';
		var b_class = 'collapse in';
		var i = 0;
		for (var key in freq_lists) {
			if (freq_lists.hasOwnProperty(key)) {
				i += 1;
				var act_atts = freq_lists[key];
				var act_atts_html = act_atts.join('\n');
				var id_root = 'attribute-sel-' + par_id_root + '-' + i;
				var h_id = id_root + '-t';
				var b_id = id_root + '-body';
				var part_title = 'Fields in ' + key + ' Records';
				var panel_html = [
					'<div class="panel">',
						'<div role="tab" id="' + h_id + '">',
						    '<label>',
							'<a role="button" data-toggle="collapse" ' + t_class,
							'data-parent="#' + all_id + '" href="#' + b_id +'" ',
							'aria-expanded="'+ exp + '" aria-controls="' + b_id +'">',
							part_title,
							'</a>',
							'</label>',
						'</div>',
						'<div id="' + b_id +'" class="' + b_class + '" ',
						'role="tabpanel" aria-labelledby="' + h_id + '">',
							'<samp>' + act_atts_html + '</samp>',
						'</div>',
					'</div>',
					].join('\n');
				html_list.push(panel_html);
				exp = 'false';
				t_class = ' class="collapsed" ';
				b_class = 'collapse';
			}
		}
		html_list.push('</div>');
		var html = html_list.join('\n');
		return html;
	}
	this.make_attributes_feq_lists = function(attribute_list){
		// sorts the attribute list into categories
		// based on fequency
		var feq_lists = {
			'All or Most': [],
			'Many': [],
			'Some': [],
			'Few': []
		};
		for (var i = 0; i < attribute_list.length; i++) {
			var attrib = attribute_list[i];
			var percent = Math.round(attrib.count / this.total_results, 2) * 100;
			var label = attrib['label'];
			if (label.length > 36) {
				label = attrib['label'].substring(0, 34) + '..';
			}
			
			var attrib_html = [
				'<button type="button" class="btn btn-primary btn-xs" style="margin-bottom: 2px; "',
					'onclick="' + this.obj_name + '.addAttribute(\'' + attrib['slug'] + '\');">',
					label,
					'<span style="margin-left: 5px;" ',
					'class="glyphicon glyphicon-plus-sign" aria-hidden="true"></span>',
				'</button>',
			].join('');
			
			if (percent >= 75 && this.default_add_common_fields) {
				this.added_field_slug_list.push(attrib['slug']);
			}
			
			if (this.added_field_slug_list.indexOf(attrib['slug']) < 0) {
				// only add the field if it is not in the added_field_slug_list
				if (percent >= 75) {
					feq_lists['All or Most'].push(attrib_html);
				}
				else if (percent >= 33 && percent < 75) {
					feq_lists['Many'].push(attrib_html);
				}
				else if (percent >= 10 && percent < 33) {
					feq_lists['Some'].push(attrib_html);
				}
				else{
					feq_lists['Few'].push(attrib_html); 
				}
			}
			
		}
		// now delete the keys for empty lists
		for (var key in feq_lists) {
			if (feq_lists.hasOwnProperty(key)) {
				if (feq_lists[key].length < 1) {
					delete feq_lists[key];
				}
			}
		}
		return feq_lists;
	}
	this.get_options_from_facet_group = function(facet_group, options_key){
		// gets a list of options from a given facet group by key
		// (the key describes the type of field. Eg. id, string, date, number)
		var options_list = [];
		if (facet_group[options_key] !== undefined) {
			options_list = facet_group[options_key] 
		}
		return options_list;
	}
	this.get_field_val_from_metadata = function(slug, key){
		// get the value for a certain key from a field object from the metadata
		var key_value = false;
		var field_obj = this.get_field_obj_from_metadata(slug);
		if (field_obj != false) {
			if (field_obj[key] !== undefined) {
				key_value = field_obj[key];
			}
		}
		return key_value;
	}
	this.get_field_obj_from_metadata = function(slug){
		// gets the field-object from the metadata based on the slug as a key
		var field_obj = false;
		var search_list = [];
		if (this.metadata != false) {
			if (this.metadata['oc-api:has-facets'] !== undefined) {
				for (var i = 0; i < this.metadata['oc-api:has-facets'].length; i++) {
					var facet_group = this.metadata['oc-api:has-facets'][i];
					if (facet_group['rdfs:isDefinedBy'] !== undefined) {
						if (facet_group['rdfs:isDefinedBy'] == 'oc-api:facet-prop-ld'){
							// Linked data / common standards attributes
							var act_list = this.get_options_from_facet_group(facet_group, 'oc-api:has-id-options');
							search_list = search_list.concat(act_list);
						}
						else if (facet_group['rdfs:isDefinedBy'] == 'oc-api:facet-prop-var'){
							// Linked data / common standards attributes
							var act_list = this.get_options_from_facet_group(facet_group, 'oc-api:has-id-options');
							search_list = search_list.concat(act_list);
							var act_list = this.get_options_from_facet_group(facet_group, 'oc-api:has-numeric-options');
							search_list = search_list.concat(act_list);
							var act_list = this.get_options_from_facet_group(facet_group, 'oc-api:has-date-options');
							search_list = search_list.concat(act_list);
							var act_list = this.get_options_from_facet_group(facet_group, 'oc-api:has-text-options');
							search_list = search_list.concat(act_list);
						}
						else{
							// twiddle thumbs
						}
					}
				}
			}
		}
		for (var i = 0; i < search_list.length; i++) {
			var act_field = search_list[i];
			if (act_field['slug'] !== undefined) {
				if (act_field['slug'] == slug) {
					field_obj = act_field;
					break;
				}
			}
		}
		return field_obj;
	}
	this.reset = function(){
		/* resets the exporter
		 * 
		*/
		this.current_export_page = 0;
		this.data = [];
		this.added_field_slug_list = [];
		this.default_add_common_fields = true;
	}
	this.progress_bar_html = function(){
		/*
		 * Makes Bootstrap progress bar HTML based on current pagination
		 */
		var portion_done = 0;
		var page_total = this.get_total_export_pages();
		if (page_total > 0) {
			portion_done = this.current_export_page / page_total;
			portion_done = Math.round((portion_done * 100), 2);
		}
		var portion_html = Math.round((portion_done * 100), 2) + '%';
		var html = [
			'<div class="progress">',
				'<div class="progress-bar" role="progressbar" aria-valuenow="' + portion_done + '" ',
				'aria-valuemin="0" aria-valuemax="100" style="width: ' + portion_html + ';">',
				portion_html,
				'</div>',
			'</div>'
		].join('\n');
		return html;
	}
	
	/* ------------------------------------------------
	 * Functions for getting metadata about the current search set
	 * ------------------------------------------------
	 */
	this.ajax_get_meta_facets = function(){
		if (document.getElementById('metadata-attributes')) {
			var meta_dom = document.getElementById('metadata-attributes');
			meta_dom.innerHTML = this.make_loading_gif('Loading attribute options...');
		}
		
		this.meta_facets_url = replaceURLparameter(this.json_url, 'response', 'metadata,facet');
		return $.ajax({
			type: "GET",
			url: this.meta_facets_url,
			dataType: "json",
			context: this,
			success: this.ajax_get_meta_facetsDone,
			error: function (request, status, error) {
				alert('Request failed to: ' + this.meta_facets_url);
			}
		});
	}
	this.ajax_get_meta_facetsDone = function(data){
		if (document.getElementById('metadata-attributes')) {
			var meta_dom = document.getElementById('metadata-attributes');
			meta_dom.innerHTML = '';
		}
		this.metadata = data;
		console.log(this.metadata);
	}
	this.make_meta_facets_url = function(){
		/*
		 *  Makes the URL for getting metadata + facets for the current URL
		*/
		this.meta_facets_url = replaceURLparameter(this.json_url, 'response', 'metadata,facet');
		return this.meta_facets_url;
	}
	this.get_total_export_pages = function(){
		if (this.total_results > 0) {
			this.total_export_pages = this.total_results / this.records_per_page;
			if (Math.round(this.total_export_pages, 0) <this.total_export_pages) {
				this.total_export_pages = Math.round(this.total_export_pages, 0) + 1;
			}
			else{
				this.total_export_pages = Math.round(this.total_export_pages, 0);
			}	
		}
		return this.total_export_pages;
	}
	/* ----------------------------------------------------
	 *  Widely used utility funcitons
	 *  ---------------------------------------------------
	 */
	this.count_obj_keys = function(obj){
		// counts keys in an object
		var keys = [];
		for (var key in obj) {
			if (obj.hasOwnProperty(key)) {
				keys.push(key);	
			}
		}
		return keys.length;
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
	this.make_url = function(relative_url){	
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
}