/*
 * Functions to get and display profiles for a project
 */

function profiles(act_dom_id, project_uuid){
	this.project_uuid = project_uuid;
	this.act_dom_id = act_dom_id;  // dom id where the profile list will be rendered
	this.profile_count_dom_id = "profile-total-count";
	this.profile_count = 0;
	this.get_data = function(){
		// ajax request to get the data for this hiearchy
		this.show_loading();
		var url = this.make_url('/edit/inputs/') + encodeURIComponent(this.project_uuid) + '.json';
		return $.ajax({
				type: "GET",
				url: url,
				dataType: "json",
				context: this,
				success: this.get_dataDone
		});
	}
	this.get_dataDone = function(data){
		//handle successful results of getting data
		var html = '<table class="table table-hover table-striped">';
		html += '<thead>';
		html += '<tr>';
		html += '<th class="col-sm-1">Add Record</th>';
		html += '<th class="col-sm-2">Item Type</th>';
		html += '<th class="col-sm-3">Label</th>';
		html += '<th class="col-sm-4">Description</th>';
		html += '<th class="col-sm-1">Last Updated</th>';
		html += '<th class="col-sm-1">Created</th>';
		html += '</tr>';
		html += '</thead>';
		html += '<tbody>';
		for (var i = 0, length = data.length; i < length; i++) {
			var prof = data[i];
			var button_use_html = [
			'<a class="btn btn-primary" title="Create a new record with this Input Profile" ',
			'href="' + this.make_url('/edit/inputs/profiles/' + encodeURIComponent(prof.id) + '/new') + '">',
			'<span class="glyphicon glyphicon-plus-sign" aria-hidden="true"></span>',
			'</a>',
			].join('\n');
			var row = [
			'<tr>',
			'<td>' + button_use_html + '</td>',
			'<td>' + this.describe_item_type_html(prof.item_type) + '</td>',
			'<td>' + prof.label,
			'<br/><samp class="uri-id">',
			'<a title="Edit this Input Profile" target="_blank" ',
			'href="' + this.make_url('/edit/inputs/profiles/' +  encodeURIComponent(prof.id) + '/edit') + '">',
			prof.id + ' <span class="glyphicon glyphicon-edit" aria-hidden="true"></span>',
			'</a>',
			'</samp>',
			'</td>',
			'<td>',
			'<dl>',
			'<dt>Fields</dt>',
			'<dd>' + prof.field_count + ' fields in ' + prof.fgroup_count + ' groups</dd>',
			'<dt>Explanatory Note</dt>',
			'<dd>' + prof.note + '</dd>',
			'</dl>',
			'</td>',
			'<td>' + prof.updated + '</td>',
			'<td>' + prof.created + '</td>',
			'</tr>'
			].join('\n');
			html += row;
		}
		html += '</tbody>';
		html += '</table>';
		if (document.getElementById(this.act_dom_id)) {
			var act_dom = document.getElementById(this.act_dom_id);
			act_dom.innerHTML = html;
		}
		if (document.getElementById(this.profile_count_dom_id)) {
			var act_dom = document.getElementById(this.profile_count_dom_id);
			act_dom.innerHTML = data.length + " profiles";
		}
	}
	this.describe_item_type_html = function(item_type){
		var des_type = this.describe_item_type(item_type);
		if (des_type != false) {
			var html = [
			'<span title="' + des_type.note + '">' + des_type.sup_label + '</span>',
			'<br/><samp class="uri-id">' + item_type+ '</samp>',		
			].join('\n');
		}
		else{
			var html = '<samp class="uri-id">' + item_type + '</samp>';		
		}
		return html;
	}
	this.describe_item_type = function(item_type){
		types = {'subjects': {'sup_label': 'Locations, objects', 'note': 'Primary records of locations, contexts, objects + ecofacts'},
		         'media': {'sup_label': 'Media', 'note': 'Media files (images, videos, 3D files, PDFs, etc.) that help document subjects items'},
					'documents': {'sup_label': 'Documents', 'note': 'Text documents HTML text records of notes, diaries, logs, and other forms of narrative'},
					'persons': {'sup_label': 'Persons, organizations', 'note': 'Persons or organizations that have some role in the project'}
					}
		var output = false;
		if (item_type in types) {
			output = types[item_type];
		}
		return output;
	}
	this.show_loading = function(){
		//display a spinning gif for loading
		if (document.getElementById(this.act_dom_id)) {
			var act_dom = document.getElementById(this.act_dom_id);
			var html = this.make_loading_gif('Loading...');
			act_dom.innerHTML = html;
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
	this.make_url = function(relative_url){
	//makes a URL for requests, checking if the base_url is set	
		if (typeof base_url != "undefined") {
			return base_url + relative_url;
		}
		else{
			return '../../' + relative_url;
		}
	}
}