/*
 * ------------------------------------------------------------------
	AJAX for using the Open Context API,
	to get examples of a given type
 * ------------------------------------------------------------------
*/


function types_item_examples(examples_url) {
	/* Object for runing searches + displaying results from Open Context */
	this.url = examples_url;
	this.data = null;
	this.summary_dom_id = 'oc-summary';
	this.results_dom_id = 'oc-results'; // DOM ID for where to put HTML displaying search results
	this.response = 'metadata,uri-meta';
	this.attribute_slugs = [
		'thumbnail',
		'href'
	];
	this.sort = null;
	this.examples_per_row = 4;
	this.record_start = 0;  // the start number for the results
	this.record_rows = 20;  // the number of rows returned in a search result
	this.loading_message = 'Getting examples of items described by this type...';

	this.get_data = function() {
		// calls the Open Context API to get data described by the type
		this.make_loading_message();
		var url = this.url;
		var params = this.set_parameters();
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
			success: this.get_dataDone, //do this when we get data w/o problems
			error: this.get_dataError //error message display
		});
	}
	this.get_dataDone = function(data){
		// function to display results of a request for data
		this.data = data;
		console.log(data);
		
		//render the results as HTML on the Web page.
		this.make_results_html();
		return false;
	}
	this.get_dataError = function(){
		// handle errors in getting data
		if (document.getElementById(this.results_dom_id)) {
			var act_dom = document.getElementById(this.results_dom_id);
			act_dom.innerHTML = 'Cannot display example items at this time.';
		}
	}
	this.set_parameters = function(){
		// this function sets the parameters used to filter a search,
		// page through results, request additional attributes for search results
		// and sort the search results
		params = {}; // default, empty search parameters
		
		if (this.attribute_slugs.length > 0) {
			params['attributes'] = this.attribute_slugs.join(',');
		}
		if (this.sort != null) {
			params['sort'] = this.sort;  // sorting 
		}
		params['start'] = this.record_start;  // the start number for records in this batch
		params['rows'] = this.record_rows; // number of rows we want
		params['response'] = this.response;  // the type of JSON response to get from OC
		
		return params;
	}
	/*
	 * Functions below here are for displaying results in HTML
	 * You can edit these functions for generating HTML so results look good on
	 * your own website.
	 */
	this.make_results_html = function(){
		// this renders all the results as HTML on the webpage
		if (this.data != null) {
			// we have API results, so proceed to display them.
			if (document.getElementById(this.summary_dom_id)) {
				var sum_dom = document.getElementById(this.summary_dom_id);
				if (this.data['totalResults'] > 0) {
					var sum_html = 'Examples of the ';
					sum_html += this.data['totalResults'];
					sum_html += ' Item(s) Described by this Type';
				}
				else{
					var sum_html = 'No Items Described by this Type';
				}
				sum_dom.innerHTML = sum_html;
			}
			
			if (document.getElementById(this.results_dom_id)) {
				// found the DOM element for where search results will be added
				// result_dom will be the HTML container for the search results
				var result_dom = document.getElementById(this.results_dom_id);
				var result_html = '';
				// check to make sure we actually have result records in the data from the API
				if ('oc-api:has-results' in this.data) {
				
					// now loop through the records from the data obtained via the API
					var all_rows = [];
					var act_row = [];
					// organize them into rows for consistent display
					for (var i = 0, length = this.data['oc-api:has-results'].length; i < length; i++) { 
						// a record object has data about an individual Open Context record
						// returned from the search.
						var record = this.data['oc-api:has-results'][i];
						var record_html = this.make_record_html(record);
						if (act_row.length >= this.examples_per_row) {
							all_rows.push(act_row);
							var act_row = [];
						}
						act_row.push(record_html);
					}
					all_rows.push(act_row);
					
					// now make the html for the rows
					for (var i = 0, length = all_rows.length; i < length; i++) {
						var act_row = all_rows[i];
						result_html += '<div class="row">';
						for (var j = 0, ar_length = act_row.length; j < ar_length; j++) {
							var act_cell = act_row[j];
							result_html += act_cell;
						}
						result_html += '</div>';
					}
					
					var html_link = [
						'<p>',
						'<a title="More search options for this type" ',
						'href="' + this.url + '" >',
						'More Options to Search',
						'</a> this Type',
						'</p>'
					].join('\n');
					
					result_html += html_link;
				}
				
				result_dom.innerHTML = result_html;
			}
			else{
				// cannot find the DOM element for the search results
				// alert with an error message.
				var error = [
				'Cannot find the DOM element for putting search results, ',
				'set the "results_dom_id" attribute for this object ',
				'to indicate the ID of the HTML DOM element where ',
				'search results will be displayed.'
				].join('\n');
				alert(error);
			}
		}
		return false;
	}
	this.make_record_html = function(record){
		// make HTML for a search result
		
		var thumb = false;
		
		if ('thumbnail' in record) {
			if (record['thumbnail'] != false) {
				thumb = record['thumbnail'];
			}
		}
		
		if (thumb != false) {
			var item_html = [
				'<a href="' + record.href + '" ',
				'title="' + record.label + '" ',
				'target="_blank">',
					'<img alt="thumbail for ' + record.label + '" ',
					'src="' + thumb + '" class="img-responsive img-rounded center-block" />',
				'</a>'
			].join('\n');
		}
		else{
			var item_html = [
				'<a href="' + record.href + '" target="_blank" class="text-center">',
					record.label,
				'</a>'
			].join('\n');
		}
		
		var record_html = [
			'<div class="col-xs-6 col-sm-4 col-md-3">',
			    '<div class="type-example-panel-outer">',
					'<div class="panel panel-default">',
						'<div class="panel-body type-example-item text-center">',
						item_html,
						'</div>',
					'</div>',
				'</div>',
			'</div>'
		].join('\n');
		
		return record_html;
	}
	this.make_loading_message = function(){
		// makes the loading GIF with messag
		if (document.getElementById(this.results_dom_id)) {
			var act_dom = document.getElementById(this.results_dom_id);
			var html = this.make_loading_gif(this.loading_message);
			act_dom.innerHTML = html;
		}
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
