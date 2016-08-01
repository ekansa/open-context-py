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
	this.col_field = 3; // column width for the orcid data field
	this.col_value = 9; // column width for the orcid data value
	this.get_data = function() {
		// calls the orcid API to get data
		var url = this.api_url;
		if (url != false) {
		    url = url.replace('http://', 'https://');
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
		// function to display results of a request for data
		this.data = data;
		console.log(data);
		var act_dom = this.get_parent_dom();
		if (act_dom != false) {
			var html = [
			'<div class="panel panel-default">',
			'<div class="panel-body">',
			this.other_names(data, true),
			this.bio(data, true),
			this.publications(data, true),
			'</div>',
			'</div>'
			].join('\n');
			act_dom.innerHTML = html;
		}
	}
	this.other_names = function(data, format){
		// gets and formats other person names
		var output = false;
		var path = ['orcid-profile',
			    'orcid-bio',
			    'personal-details',
			    'other-names',
			    'other-name'];
		var names = this.get_data_path(path, data);
		if (names != false) {
			for (var i = 0, length = names.length; i < length; i++) {
				if (output == false) {
					output = names[i].value;
				}
				else{
					output += ', ' + names[i].value;
				}
			}
		}
		if (format && output != false) {
			// format result
			output = this.format_html_value('Other names:', output);
		}
		else if (format && output == false) {
			output = '';
		}
		else{
			// do nothing. yet...
		}
		return output;
	}
	this.bio = function(data, format){
		// gets and formats other person names
		var output = false;
		var path = ['orcid-profile',
			    'orcid-bio',
			    'biography',
			    'value'];
		var output = this.get_data_path(path, data);
		if (format && output != false && output != null) {
			// format result
			output = this.format_html_value('Biography:', output);
		}
		else if (format && output == false) {
			output = '';
		}
		else{
			// do nothing. yet...
		}
		return output;
	}
	this.publications = function(data, format){
		var output = false;
		var path = ['orcid-profile',
			    'orcid-activities',
			    'orcid-works',
			    'orcid-work'];
		var pubs = this.get_data_path(path, data);
		var html = false;
		if (pubs != false) {
			var html = ['<ul class="list-unstyled">'];
			for (var i = 0, length = pubs.length; i < length; i++) {
				var pub = pubs[i];
				var pub_html = this.publication(pub);
				if (pub_html != false) {
					pub_html = '<li>' + pub_html + '</li>';
					html.push(pub_html);
				}
			}
			html.push('</ul>');
			if (html.length > 0) {
				html = html.join('\n');
			}
			else{
				html = false;
			}
		}
		if (format && html != false) {
			// format result
			output = this.format_html_value('Works:', html);
		}
		else if (format && html == false) {
			output = '';
		}
		else if (format == false && pubs != false) {
			output = pubs;
		}
		else{
			output = false;
		}
		return output;
	}
	this.publication = function(pub){
		//makes HTML for a publication, returns false if minimal data
		// cannot be found
		var path = ['work-citation',
			    'citation'];
		var citation = this.get_data_path(path, pub);
		path = ['work-citation',
			'work-citation-type'];
		var cite_type = this.get_data_path(path, pub);
		path = ['work-title',
			'title',
			'value'];
		var title = this.get_data_path(path, pub);
		path = ['journal-title',
			'value'];
		var journal_title = this.get_data_path(path, pub);
		path = ['publication-date',
			'year',
			'value'];
		var pub_year = this.get_data_path(path, pub);
		path = ['work-type'];
		var work_type = this.get_data_path(path, pub);
		if (work_type != false) {
			work_type = work_type.toLowerCase();
			work_type = work_type.replace('_', '-');
		}
		var pub_link = this.get_pub_link(pub);
		if (cite_type.toUpperCase() == 'BIBTEX') {
			// can't cope with parsing this now
			citation = false;
		}
		if ((title != false && pub_year != false) || citation != false) {
			var html = this.make_work_html(title, pub_year, journal_title, work_type, pub_link, citation);
		}
		else{
			var html = false;
		}
		return html;
	}
	this.make_work_html = function(title, year, sub_title, work_type, link, cite){
		if (sub_title == false) {
			sub_title = '';
		}
		else{
			sub_title = '<cite>' + sub_title + '</cite></br>' 
		}
		if (work_type == false) {
			work_type = '';
		}
		else{
			work_type = ' [' + work_type + ']' 
		}
		if (year != false) {
			var year_html = year + work_type + '</br>';
		}
		else{
			var year_html = '';
		}
		if (link != false) {
			if (link['label'].length > 50) {
				link['label'] = link['label'].substring(0,45) + '...';
			}
			
			var link_html = [
			link['type'] + ': ',
			'<a target="_blank" href="' + link['id'] + '">' + link['label'] + '</a>',
			'<br/>'
			].join('\n');
		}
		else{
			var link_html = '';
		}
		if (title != false && year != false) {
			var html = [
			'<div style="padding-bottom: 10px;">',
			title + '<br/>',
			'<div class="small">',
			sub_title,
			year_html,
			link_html,
			'</div>',
			'</div>'
			].join('\n');
		}
		else if (cite != false){
			var html = [
			'<div style="padding-bottom: 10px;">',
			cite + '<br/>',
			'<div class="small">',
			link_html,
			'</div>',
			'</div>'
			].join('\n');
		}
		else{
			var html = '';
		}
		return html;
	}
	this.get_pub_link = function(pub){
		var url = false;
		var path = ['work-external-identifiers',
			    'work-external-identifier'];
		var ids = this.get_data_path(path, pub);
		if (ids != false) {
			for (var i = 0, length = ids.length; i < length; i++) {
				if ('work-external-identifier-type' in ids[i] && url == false) {
					var id_type = ids[i]['work-external-identifier-type']
					if (id_type.toUpperCase() == 'DOI') {
						path = ['work-external-identifier-id',
							'value'];
						var doi = this.get_data_path(path, ids[i]);
						if (doi != false) {
							url = {id: 'http://dx.doi.org/' + doi,
							       label: doi,
							       type: 'DOI'};
						}
					}
				}
			}
		}
		if (url == false) {
			//couldn't find a DOI, so look for a URL
			path = ['url',
				'value'];
			var raw_url = this.get_data_path(path, pub);
			if (raw_url != false) {
				url = {id: raw_url,
				       label: raw_url,
				       type: 'URL'};
			}
		}
		return url;
	}
	this.format_html_value = function(field_name, value){
		var html = [
			'<div class="row">',
			'<div class="col-sm-12"><strong>' + field_name + '</strong></br>',
			'<div style="padding-bottom: 15px;">' + value + '</div>',
			'</div>',
			'</div>'
		].join('\n');
		return html;
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
	this.get_data_path = function(path_list, data){
		var output_data = data;
		for (var i = 0, length = path_list.length; i < length; i++) {
			var path_key = path_list[i];
			if (output_data != false && output_data != null) {
				if (path_key in output_data) {
					output_data = output_data[path_key];
				}
				else{
					output_data = false;
				}
			}
			else{
				output_data = false;
			}
		}
		return output_data;
	}
}
