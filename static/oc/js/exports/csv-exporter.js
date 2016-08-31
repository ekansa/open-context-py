/*
 * Functions to edit spatial coodinates and time ranges
 */
function CSVexporter(json_url, total_results){
	this.obj_name = 'CSVexporter';
	this.json_url = json_url; // base url for geo-json requests
	this.meta_facets_url = false; 
	this.modal_id = 'searchModal';
	this.total_results = total_results;
	this.completed_export_page = 0;
	this.total_export_pages = 0;
	this.records_per_page = 100;
	this.completed_pages = [];
	this.data = [];
	this.metadata = false;
	this.added_field_slug_list = [];
	this.default_add_common_fields = true;
	this.export_type = 'csv';
	this.continue_exporting = false;
	this.sleep_pause = 300; // milliseconds to pause between requests
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
	this.default_fields_order = [
		'uri',
		'citation uri',
		'label',
		'project label',
		'project uri',
		'context label',
		'context uri',
		'latitude',
		'longitude',
		'early bce/ce',
		'late bce/ce',
		'item category',
		'published',
		'updated'
	];
	this.csv_filename = 'open-context-csv-export.csv';
	this.geojson_filename = 'open-context-geojson-export.json';
	this.show_interface = function(){
		/* shows an interface for starting the exporter
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
		/* makes the HTML for the exporter interface
		 * 
		*/
		var controls_html = this.show_controls_html();
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
			'<div class="well well-sm">',
				'<div id="metadata-attributes">',
				'</div>',
				'<div id="export-controls">',
				controls_html,
				'</div>',
			'</div>',
		'</div>'
		].join('\n');
		return html;
	}
	this.show_controls_html = function(){
		/* Shows controls to start, stop an export
		 * and to determine what kind of data to export
		 */
		var radio_html = this.make_file_type_radio_html();	
		var start_html = this.make_start_button_html();
		//var pause_html = this.make_pause_button_html();
		var reset_html = this.make_reset_button_html();
		
		var html = [
			'<div style="margin-top: 20px;">',
				'<div class="row">',
					'<div class="col-xs-6"  id="export-progress">',
					'</div>',
					'<div class="col-xs-3">',
						'<label>Export File Type:</label><br/>',
						radio_html,
					'</div>',
					'<div class="col-xs-3">',
						'<label>Export Controls:</label><br/>',
						'<div class="row">',
							'<div class="col-xs-12">',
								'<div style="margin-bottom: 10px;" id="exp-start-button-outer">',
								start_html,
								'</div>',
							'</div>',
						'</div>',
						'<div class="row">',
							'<div class="col-xs-12">',
								'<div style="margin-bottom: 10px;" id="exp-reset-button-outer">',
								reset_html,
								'</div>',
							'</div>',
						'</div>',
					'</div>',
				'</div>',
			'</div>',
		].join('\n');
		return html;
	}
	this.make_file_type_radio_html = function(){
		// makes the html for the radio buttons for export file formats
		var export_csv = '';
		var export_geojson = '';
		if (this.export_type == 'csv') {
			export_csv = ' checked="checked" ';
		}
		else{
			export_geojson = ' checked="checked" ';
		}
		var html = [
		'',
		'<div class="radio" id="data-type-export-outer-csv">',
			'<label>',
				'<input type="radio" class="data-type-export" ' + export_csv,
				'id="data-type-csv" name="data-type-export" value="csv" />',
				'<i class="fa fa-table"></i>',
				' Table (CSV)',
			'</label>',
		'</div>',
		'<div class="radio" id="data-type-export-outer-geojson">',
			'<label>',
				'<input type="radio" class="data-type-export" ' + export_geojson,
				'id="data-type-geojson" name="data-type-export" value="geojson" />',
				'<i class="fa fa-map-marker"></i>',
				' GIS (GeoJSON)',
			'</label>',
		'</div>',
		].join('\n');
		return html;
	}
	this.make_file_type_radio_inline_html = function(){
		// another HTML format for export file format interface controls
		var export_csv = '';
		var export_geojson = '';
		if (this.export_type == 'csv') {
			export_csv = ' checked="checked" ';
		}
		else{
			export_geojson = ' checked="checked" ';
		}
		var html = [
		'',
		'<label class="radio-inline">',
			'<input type="radio" class="data-type-export" ' + export_csv,
			'id="data-type-csv" name="data-type-export" value="csv" />',
			'<i class="fa fa-table"></i>',
			' Table (CSV)',
		'</label>',
		'<label style="margin-left: 20px;" class="radio-inline">',
			'<input type="radio" class="data-type-export" ' + export_geojson,
			'id="data-type-geojson" name="data-type-export" value="geojson" />',
			'<i class="fa fa-map-marker"></i>',
			' GIS (GeoJSON)',
		'</label>',
		].join('\n');
		return html;
	}
	this.make_start_button_html = function(){
		//makes the HTML for the start button, optionally disabled
		var page_total = this.get_total_export_pages();
		
		var dis_html = '';
		if (this.continue_exporting) {
			var dis_html = ' disabled="disabled" ';
		}
		var start_index = this.data.length; 
		if (start_index < 1) {
			var html = [
			'<button type="button" class="btn btn-primary btn-block" ',
			'title="Start download" ' + dis_html,
			'onclick="' + this.obj_name + '.resumeExport();">',
			'Start Export',
			'<span style="margin-left: 5px;" ',
			'class="glyphicon glyphicon-cloud-download" aria-hidden="true"></span>',
			'</button>',
			].join('');
		}
		else if (start_index >= this.total_results) {
			var dis_html = ' disabled="disabled" ';
			var html = [
			'<button type="button" class="btn btn-default btn-block" ',
			dis_html,
			' >',
			'Export Done',
			'<span style="margin-left: 5px;" ',
			'class="glyphicon glyphicon-ok" aria-hidden="true"></span>',
			'</button>',
			].join('');
		}
		else{
			var html = [
			'<button type="button" class="btn btn-primary btn-block" ',
			'title="Resume download" ' + dis_html,
			'onclick="' + this.obj_name + '.resumeExport();">',
			'Exporting.. ',
			'<span style="margin-left: 5px;" ',
			'class="glyphicon glyphicon-cloud-download" aria-hidden="true"></span>',
			'</button>',
			].join('');
		}
		return html;
	}
	this.make_pause_button_html = function(){
		//makes the HTML for the start button, optionally disabled
		var page_total = this.get_total_export_pages();
		var dis_html = '';
		if (this.continue_exporting == false) {
			var dis_html = ' disabled="disabled" ';
		}
		if (this.completed_export_page >= page_total){
			var dis_html = ' disabled="disabled" ';
			var html = [
			'<button type="button" class="btn btn-default btn-block" ',
			dis_html,
			' >',
			'Export Done',
			'<span style="margin-left: 5px;" ',
			'class="glyphicon glyphicon-ok" aria-hidden="true"></span>',
			'</button>',
			].join('');
		}
		else {
			var html = [
			'<button type="button" class="btn btn-warning btn-block" ',
			'title="Pause download" ' + dis_html,
			'onclick="' + this.obj_name + '.pauseExport();">',
			'Pause Export',
			'<span style="margin-left: 5px;" ',
			'class="glyphicon glyphicon-pause" aria-hidden="true"></span>',
			'</button>',
			].join('');
		}
		return html;
	}
	this.make_reset_button_html = function(){
		//makes the HTML for the reset button, optionally disabled
		var dis_html = '';
		if (this.continue_exporting) {
			var dis_html = ' disabled="disabled" ';
		}
		var start_index = this.data.length; 
		if (start_index < 1) {
			// no data downloaded yet, make non-dangerous reset button
			var b_class = 'btn btn-default btn-block';
			var b_title = 'Reset to export fields to defaults';
			var b_icon = 'glyphicon glyphicon-refresh';
			var label = 'Reset Export';
			var onclick = this.obj_name + '.reset()';
		}
		else if (start_index >= this.total_results) {
			// all data downloaded
			var b_class = 'btn btn-success btn-block';
			var b_title = 'Save the exported data to a file';
			var b_icon = 'glyphicon glyphicon-save-file';
			var label = 'Save to File';
			var onclick = this.obj_name + '.save()';
		}
		else{
			var b_class = 'btn btn-danger btn-block';
			var b_title = 'Clear, reset fields to defaults, and start-over';
			var b_icon = 'glyphicon glyphicon-trash';
			var label = 'Reset Export';
			var onclick = this.obj_name + '.reset()';
		}
		
		var html = [
			'<button type="button" class="' + b_class + '" ',
			'title="' + b_title + '" ' + dis_html,
			'onclick="' + onclick + '">',
			label,
			'<span style="margin-left: 5px;" ',
			'class="' + b_icon +'" aria-hidden="true"></span>',
			'</button>',
		].join('');
		
		return html;
	}
	
	/*---------------------------------------------------------------------
	 * Functions for displaying export progress and controls
	 * 
	 *
	 *---------------------------------------------------------------------
	 */
	this.resumeExport = function(){
		this.set_export_type();
		this.continue_exporting = true;
		this.toggle_export_buttons();
		this.get_record_pages();
	}
	this.get_record_pages = function(){
		if (document.getElementById('export-progress')) {
			var act_dom = document.getElementById('export-progress');
			act_dom.innerHTML = this.make_loading_gif('Preparing to download records for export...');
		}
		this.ajax_next_page_records();
	}
	this.ajax_next_page_records = function(){
		var page_total = this.get_total_export_pages();
		if (this.continue_exporting) {
			var start_index = this.data.length;
			var current_export_page = this.completed_export_page + 1;
			if (start_index < this.total_results) {
				if (start_index > 1) {
					// pause between requests, because of rate limiting on server
					var slept = this.sleep(this.sleep_pause);
				}
				if (this.export_type == 'csv') {
					var url = replaceURLparameter(this.json_url, 'response', 'uri-meta');
				}
				else{
					var url = replaceURLparameter(this.json_url, 'response', 'geo-record');	
				}
				url = replaceURLparameter(url, 'start', start_index);
				url = url.replace(/&amp;prop=/g, '&prop=');
				url = url.replace(/&amp&prop=/g, '&prop=');
				url = url.replace(/&amp&/g, '&');
				
				var data = {
					start: start_index,
					rows: this.records_per_page,
					attributes: this.added_field_slug_list.join(','),
					'flatten-attributes': 1
				};
				return $.ajax({
					type: "GET",
					url: url,
					dataType: "json",
					data: data,
					context: this,
					success: function(data){
						
						this.completed_pages.push(current_export_page);
						var pages_done = this.completed_pages.length;
						
						if (this.export_type == 'csv') {
							this.data = this.data.concat(data);
						}
						else{
							this.data = this.data.concat(data.features);
						}
						var records_done = this.data.length;
						
						this.completed_export_page += 1;
						if (records_done < this.total_results && pages_done < page_total) {
							this.continue_exporting = true;
						}
						else{
							this.continue_exporting = false;
						}
						this.update_progress(page_total, pages_done, records_done);
						this.toggle_export_buttons();
						if (this.continue_exporting) {
							this.ajax_next_page_records();
						}
					},
					error: function (request, status, error) {
						this.continue_exporting = false;
						alert('Request failed to: ' + url);
						return false;
					}
				});
			}
			else{
				return false;
			}
		}
		else{
			return false;
		}
	}
	this.toggle_export_buttons = function(){
		// changes export button state
		if (document.getElementById('exp-start-button-outer')) {
			var act_dom = document.getElementById('exp-start-button-outer');
			act_dom.innerHTML = this.make_start_button_html();
		}
		if (document.getElementById('exp-pause-button-outer')) {
			var act_dom = document.getElementById('exp-pause-button-outer');
			// act_dom.innerHTML = this.make_pause_button_html();
		}
		if (document.getElementById('exp-reset-button-outer')) {
			var act_dom = document.getElementById('exp-reset-button-outer');
			act_dom.innerHTML = this.make_reset_button_html();
		}
		return true;
	}
	this.update_progress = function(page_total, pages_done, records_done){
		if (document.getElementById('export-progress')) {
			var act_dom = document.getElementById('export-progress');
			var bar_html = this.progress_bar_html(page_total, pages_done);
			if (pages_done >= page_total) {
				var label = '<label>Export Complete:</label><br/>';
			}
			else{
				var label = '<label>Export Progress:</label><br/>';
			}
			var html = [
				label,
				'<div style="margin-top: 10px;">',
				bar_html,
				'</div>',
				'<dl class="dl-horizontal">',
					'<dt>Batches Downloaded:</dt>',
					'<dd>' + pages_done + ' of ' + page_total + '</dd>',
					'<dt>Total Exported:</dt>',
					'<dd>' + records_done + ' of ' + this.total_results + '</dd>',
				'</dl>',
			].join('\n');
			act_dom.innerHTML = html;
		}
	}
	this.progress_bar_html = function(page_total, pages_done){
		/*
		 * Makes Bootstrap progress bar HTML based on current pagination
		 */
		var portion_done = 0;
		if (page_total > 0) {
			portion_done = pages_done / page_total;
			portion_done = Math.round((portion_done * 100), 2);
		}
		else{
			portion_done = 1;
		}
		
		var portion_html = portion_done + '%';
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
	this.set_export_type = function(){
		// sets the export type based on the radio buttons for user import
		var export_type = this.export_type;
		var act_types = document.getElementsByClassName("data-type-export");
		for (var i = 0, length = act_types.length; i < length; i++) {
			if (act_types[i].checked) {
				export_type = act_types[i].value;
			}
		}
		var export_types = [
			'csv',
			'geojson'
		];
		for (var i = 0, length = export_types.length; i < length; i++) {
			var hide_type = export_types[i];
			var dom_id = 'data-type-export-outer-' + hide_type;
			if (hide_type != export_type) {
				if (document.getElementById(dom_id)) {
					var act_dom = document.getElementById(dom_id);
					act_dom.innerHTML = '';
				}
			}
		}
		this.export_type = export_type;
		return export_type;
	}
	 /*---------------------------------------------------------------------
	 * Functions for saving downloaded files
	 * 
	 *
	 *---------------------------------------------------------------------
	 */
	this.save = function(){
		if (this.data.length > 0) {
			if (this.export_type == 'csv') {
				this.save_csv();
			}
			else{
				this.save_geojson();
			}
		}
	}
	this.save_csv = function(){
		
		//first set up the ordering of the fields
		var ordered_field_key_list = this.default_fields_order;
		//now add the labels for the added fields, since the labels are
		//the keys used in the returned data
		for (var i = 0; i < this.added_field_slug_list.length; i++) {
			var slug = this.added_field_slug_list[i];
			var label = this.get_field_val_from_metadata(slug, 'label');
			var label_in_list = this.check_item_in_list(label, ordered_field_key_list);
			if (label_in_list == false) {
				//new label, add to then end of the field_key_list
				ordered_field_key_list.push(label);
			}
		}
		var max_context_depth = 0;
		//now we double check to make sure we've got all the field keys in the
		//actual downloaded data
		var checked_field_keys = {};
		for (var i = 0; i < this.data.length; i++) {
			var item = this.data[i];
            for (var key in item){
				if (checked_field_keys.hasOwnProperty(key)) {
					// skip
				}
				else{
					checked_field_keys[key] = true;
					//OK we haven't checked this key yet, so lets check if
					//it's in our ordered field list
					var key_in_list = this.check_item_in_list(key, ordered_field_key_list);
					if (key_in_list == false) {
						//we haven't seen this item yet!
						ordered_field_key_list.push(key)
					}
					
				}
				if (key == 'context label') {
					// check for context depth
					var contexts = this.spit_contexts(item);
					if (contexts.length > max_context_depth) {
						max_context_depth = contexts.length;
					}
				}
			}
        }
        
		//now we write the actual CSV file
		//start first with the field names
        var rowDelim = '\r\n';
		
		var csvFile = '';
		
		var row_list = [];
		for (var i = 0; i < ordered_field_key_list.length; i++) {
			var field = ordered_field_key_list[i];
			var field_value = field;
			if (this.default_field_mappings.hasOwnProperty(field)) {
				field_value = this.default_field_mappings[field];
			}
			if (field != 'context label') {
				// normal fields, add as normal
				row_list.push(field_value);
			}
			else {
				// add fields for each level of context
				for (var ii = 1; ii <= max_context_depth; ii++) {
					var context_field_value = field_value + ' (' + ii + ')';
					row_list.push(context_field_value);
				}
			}
        }
		
		// now add the row of field names as the first from of the CSV string 
		console.log(row_list);
		var req_field_count = row_list.length;
		csvFile += row_list.join(",");
		csvFile += rowDelim;
		
		//now add the rows of data records to the CSV string
		for (var i = 0; i < this.data.length; i++) {
			var item = this.data[i];
			var row_list = [];
			var item_context_list = this.spit_contexts(item);
			var num_item_contexts = item_context_list.length;
			// now loop through the field-keys in their proper order
			for (var jj = 0; jj < ordered_field_key_list.length; jj++) {
				var field_key = ordered_field_key_list[jj];
				var field_value = '';
				if (item.hasOwnProperty(field_key)) {
					field_value = item[field_key];
				}
				if (field_key != 'context label') {
					// a normal field
					row_list.push(this.csv_escape(field_value));
				}
				else{
					// contexts! Need to split and put into seperate fields
					for (var ii = 0; ii < max_context_depth; ii++) {
						if (ii < num_item_contexts) {
							//there's context for this context field
							var act_context_value = this.csv_escape(item_context_list[ii]);
						}
						else{
							//there's no context for this context field, so make a blank value
							var act_context_value = this.csv_escape('');
						}
						row_list.push(act_context_value);
					}
				}
			}
			csvFile += row_list.join(",");
			csvFile += rowDelim;
		}
		
		
		//now save it!
		var filename = this.csv_filename;
        var blob = new Blob([csvFile], { type: 'text/csv;charset=utf-8;' });
        if (navigator.msSaveBlob) { // IE 10+
            navigator.msSaveBlob(blob, filename);
        } else {
            var link = document.createElement("a");
            if (link.download !== undefined) { // feature detection
                // Browsers that support HTML5 download attribute
                var url = URL.createObjectURL(blob);
                link.setAttribute("href", url);
                link.setAttribute("download", filename);
                link.style.visibility = 'hidden';
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
            }
        }
	}
	this.csv_escape = function(value_str){
		value_str = value_str + '';
		value_str = value_str.replace(/"/g, '""'); 
		return '"' + value_str + '"';
	}
	this.save_geojson = function(){
		//package it all up into a Feature Collection
		var geojson_obj = {
			type: 'FeatureCollection',
			features: this.data
		};
		//convert the json to a string
		var geojson = JSON.stringify(geojson_obj, null, 2);
		//now save it!
		var filename = this.geojson_filename;
        var blob = new Blob([geojson], { type: 'application/json;charset=utf-8;' });
        if (navigator.msSaveBlob) { // IE 10+
            navigator.msSaveBlob(blob, filename);
        } else {
            var link = document.createElement("a");
            if (link.download !== undefined) { // feature detection
                // Browsers that support HTML5 download attribute
                var url = URL.createObjectURL(blob);
                link.setAttribute("href", url);
                link.setAttribute("download", filename);
                link.style.visibility = 'hidden';
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
            }
        }
	}
	this.spit_contexts = function(item_obj){
		var result = [];
		if (item_obj.hasOwnProperty('context label')) {
			var context = item_obj['context label'];
			result = context.split('/');
		}
		return result;
	}
	/*---------------------------------------------------------------------
	 * Functions for displaying and manipulating fields / attributes
	 * to include in the export
	 *
	 *---------------------------------------------------------------------
	 */
	this.show_attributes_html = function(){
		/* Shows fields / attributes to be exported and also
		 * shows additional fields a user can choose to export
		 */
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
			'<div class="row">',
				'<div class="col-sm-4">',
					'<label>Fields / Attributes Included in Export</label><br/>',
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
				var full_label = label;
				if (label.length > 36) {
					label = label.substring(0, 34) + '..';
				}
				
				var item_html = [
					'<button type="button" class="btn btn-default btn-xs" ',
					'title="Remove, do not export field: ' + full_label + '" ',
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
		// now update all of the shown attributes
		if (document.getElementById('added-attributes')) {
			// found the dom that takes added attributes, so refresh it
			// update for the shown and not shown attributes
			var attribute_choices_html = this.makes_attribute_choices_html();
			var added_fields_html = this.make_added_fields_html();
			var act_dom = document.getElementById('added-attributes');
			act_dom.innerHTML = added_fields_html;
		}
		else{
			// couldn't find the right dom, 
			// ok just refresh the whole thing
			this.show_attributes_html();	
		}
		
		// now hide the button we just used
		var dom_id = 'add-fieldslug-' + slug;
		if (document.getElementById(dom_id)) {
			// just remove the add button for this field.
			var act_dom = document.getElementById(dom_id);
			act_dom.style.display = 'none';
		}
		
	}
	this.makes_attribute_choices_html = function(){
		var html = '';
		var attribute_lists = this.make_attribute_choices_lists();
	    // console.log(attribute_lists);
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
			'ld-id': {	'label': 'Classification',
					'type': 'Common Standards',
					'list': []},
			'ld-num': {	'label': 'Numeric',
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
						var ld_defined_by = false;
						if (facet_group['rdfs:isDefinedBy'].indexOf('http://') == 0 || facet_group['rdfs:isDefinedBy'].indexOf('https://') == 0) {
							ld_defined_by = true;
						}
						if (facet_group['rdfs:isDefinedBy'] == 'oc-api:facet-prop-ld' || ld_defined_by){
							if (ld_defined_by) {
								// only check for numeric values if defined_by a full URI (not a common namespace)
								attribute_lists['ld-num']['list'] = attribute_lists['ld-num']['list'].concat(this.get_options_from_facet_group(facet_group, 'oc-api:has-numeric-options'));
							}
							if (facet_group['rdfs:isDefinedBy'] == 'oc-api:facet-prop-ld') {
								// only check for these if in a common namespace
								// Linked data / common standards attributes
								attribute_lists['ld-id']['list'] = attribute_lists['ld-id']['list'].concat(this.get_options_from_facet_group(facet_group, 'oc-api:has-id-options'));
							}
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
							'<div>',
							'<samp>' + act_atts_html + '</samp>',
							'</div>',
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
			var full_label = label;
			if (label.length > 36) {
				label = attrib['label'].substring(0, 34) + '..';
			}
			
			var attrib_html = [
				'<button type="button" class="btn btn-primary btn-xs" style="margin-bottom: 2px;" ',
				    'id="add-fieldslug-' + attrib['slug'] + '" ',
					'title="Add to export field: ' + full_label + '" ',
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
						var ld_defined_by = false;
						if (facet_group['rdfs:isDefinedBy'].indexOf('http://') == 0 || facet_group['rdfs:isDefinedBy'].indexOf('https://') == 0) {
							ld_defined_by = true;
						}
						if (facet_group['rdfs:isDefinedBy'] == 'oc-api:facet-prop-ld' || ld_defined_by){
							// Linked data / common standards attributes
							var act_list = this.get_options_from_facet_group(facet_group, 'oc-api:has-id-options');
							search_list = search_list.concat(act_list);
							var act_list = this.get_options_from_facet_group(facet_group, 'oc-api:has-numeric-options');
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
		this.completed_pages = [];
		this.data = [];
		this.added_field_slug_list = [];
		this.default_add_common_fields = true;
		this.show_interface();
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
		this.meta_facets_url = this.meta_facets_url.replace(/&amp;prop=/g, '&prop=');
		this.meta_facets_url = this.meta_facets_url.replace(/&amp&prop=/g, '&prop=');
		this.meta_facets_url = this.meta_facets_url.replace(/&amp&/g, '&');
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
	this.check_item_in_list = function(item, act_list){
		// returns true if the item is in a list 
		var item_in_list = false;
		for (var i = 0; i < act_list.length; i++) {
			var test_item = act_list[i];
			if (test_item == item) {
				item_in_list = true;
				break;
			}
		}
		return item_in_list;
	}
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
	this.sleep = function(milliseconds) {
		var start = new Date().getTime();
		for (var i = 0; i < 1e7; i++) {
			if ((new Date().getTime() - start) > milliseconds){
				break;
			}
		}
		return true;
	}
}