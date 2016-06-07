/*
 * Functions to edit spatial coodinates and time ranges
 */
function geoChronoEdit(item_type, item_uuid){
	this.project_uuid = project_uuid;
	this.item_uuid = item_uuid;
	this.item_type = item_type;
	this.obj_name = 'edit_geoevents';
	this.name = this.obj_name;
	this.item_json_ld_obj = false;
	this.edit_features = [];
	this.default_location_type = 'oc-gen:discovey-location';
	this.default_time_type = 'oc-gen:formation-use-life';
	this.getItemJSON = function(){
		if (typeof edit_item !=  "undefined") {
			if (edit_item.item_json_ld_obj != false) {
				if (edit_item.item_json_ld_obj.data != false) {
					// we have found existing JSON-LD data about this item
					// no need to make another AJAX request to get it
					this.show_existing_data();
				}
				else{
					edit_item.getItemJSON().then(this.show_existing_data);
				}
			}
			else{
				edit_item.getItemJSON().then(this.show_existing_data);
			}
		}
	}
	this.show_existing_data = function(){
		if (typeof edit_item !=  "undefined") {
			if (edit_item.item_json_ld_obj != false) {
				if (edit_item.item_json_ld_obj.data != false) {
					// get chronological and spatial event
					// metadata
					var features = this.get_event_features();
					this.get_edit_features(features);
					console.log(this.edit_features);
					this.make_edit_features_html();
				}
			}
		}
	}
	this.get_edit_features = function(features){
		// gets a list of unique geospatial features, with when_lists
		// organized to make editing interactions easier
		var geo_hash_ids = [];
		for (var i = 0, length = features.length; i < length; i++) {
			var feature = features[i];
			var geo_hash_id = feature.properties.hash_id;
			if (geo_hash_ids.indexOf(geo_hash_id) < 0) {
				// a new geo_hash_id!
				var when_list = this.get_feature_when_list(features, geo_hash_id);
				feature.when_list = when_list;
				this.edit_features.push(feature);
				// so we don't repeat this geo_hash id
				geo_hash_ids.push(geo_hash_id);
			}
		}
	}
	this.get_feature_when_list = function(features, geo_hash_id){
		// gets a list of all of the "When" objects that are
		// associated with a geosptial coordinate record identified
		// by the geo_hash_id
		var when_list = [];
		for (var i = 0, length = features.length; i < length; i++) {
			var feature = features[i];
			if (feature.properties.hash_id == geo_hash_id) {
				if ('when' in feature) {
					when_list.push(feature['when']);
				}
			}
		}
		return when_list;
	}
	this.get_event_features = function(){
		var features = [];
		if (edit_item.item_json_ld_obj.data != false) {
			if (edit_item.item_json_ld_obj.data['features'] !== undefined) {
				var features = edit_item.item_json_ld_obj.data['features'];
			}
		}
		return features;
	}
	this.make_edit_features_html = function(){
		var html_list = [
			'<ul class="list-group">'
		];
		for (var edit_i = 0, length = this.edit_features.length; edit_i < length; edit_i++) {
			var editfeat = this.edit_features[edit_i];
			var feat_html = this.make_edit_feature_html(edit_i, editfeat);
			var feat_item = [
				'<li class="list-group-item">',
				feat_html,
				'</li>'
			].join('\n');
			html_list.push(feat_item);
		}
		if (this.edit_features.length < 1){
			var editfeat = {
				id: false,
				properties: {'reference-type': 'specified'},
				geometry: {id: false}
			};
			var feat_html = this.make_edit_feature_html(0, editfeat);
			var feat_item = [
				'<li class="list-group-item">',
				feat_html,
				'</li>'
			].join('\n');
			html_list.push(feat_item);
		}
		html_list.push('</ul>');
		var html = html_list.join('\n');
		if (document.getElementById('edit-geo-features')) {
			document.getElementById('edit-geo-features').innerHTML = html;
		}
		return html;
	}
	
	this.make_edit_feature_html = function(edit_i, editfeat){
		
		var dom_ids = this.make_feature_dom_ids(edit_i);
		
		//get the hash_id or make it blank for a new input form
		var hash_id = '';
		if (editfeat.properties.hasOwnProperty('hash_id')) {
			if (editfeat.properties.hash_id != false) {
				hash_id = editfeat.properties.hash_id;
			}
		}
		
		var feature_id = 1;
		if (editfeat.properties.hasOwnProperty('feature_id')) {
			if (editfeat.properties.feature_id != false) {
				feature_id = editfeat.properties.feature_id;
			}
		}
		
		//now check to see if this geospatial data is specific to this
		//item or is inherited through spatial containment relations
		var inherited = true;
		if (editfeat.properties.hasOwnProperty('reference-type')) {
			if (editfeat.properties['reference-type'] == 'specified') {
				inherited = false;
			}
		}
		
		
		//a blank when object to create a new record
		var new_when_obj = {
			start: false,
			stop: false,
			hash_id: false
		};
		if (editfeat.hasOwnProperty('when_list') == false) {
			// for some reason we need to add a when_list property
			editfeat.when_list = [];
		}
		editfeat.when_list.push(new_when_obj);
		
		//this bit makes the rows for date range associated with this feature
		var when_html_list = [];
		for (var when_i = 0, length = editfeat.when_list.length; when_i < length; when_i++) {
			var when_obj = editfeat.when_list[when_i];
			var when_row_html = this.make_when_html(edit_i, when_i, when_obj);
			when_html_list.push(when_row_html);
		}
		var when_rows_html = when_html_list.join('\n');
		
		
		//now make some plain GeoJSON to show in a text area
		var plain_geojson = this.make_plain_geojson_from_edit_feat(editfeat);
		var plain_geojson_str = JSON.stringify(plain_geojson);
		if (editfeat.geometry.type == "Point") {
			var lon_lat = editfeat.geometry.coordinates;
			var lon = lon_lat[0];
			var lat = lon_lat[1];
		}
		else{
			var lon = '';
			var lat = '';
		}
		
		var hide_feature_html = inherited;
		if (inherited) {
			if (this.edit_features.length == 1) {
				// only 1 feature, and it's inherited so make an interface for editing
				hide_feature_html = false;
				hash_id = '';
				lat = '';
				lon = '';
				plain_geojson_str = '';
			}
		}
		
		
		if (hide_feature_html) {
			// HTML for location information that is inherited via spatial context
			// note, location data cannot be edited here, only reviewed
		}
		else{
			//make the submit button
			var submit_html = this.make_geo_submit_html(edit_i);
			
			// HTML for location information specific to the item iself
			var html = [
				'<div class="row">',
					'<div class="col-xs-5">',
						'<div class="well well-sm">',
							'<div class="form-group">',
								'<label for="' + dom_ids.lat + '">Latitude (WGS-84, decimal degrees)</label>',
								'<input class="form-control input-sm" ',
								'type="text" ',
								'id="' + dom_ids.lat + '" ',
								'value="' + lat + '" >',
							'</div>',
							'<div class="form-group">',
								'<label for="' + dom_ids.lon + '">Longitude (WGS-84, decimal degrees)</label>',
								'<input class="form-control input-sm" ',
								'type="text" ',
								'id="' + dom_ids.lon + '" ',
								'value="' + lon + '" >',
							'</div>',
						'</div>',
						'<div class="well well-sm">',
							'<div class="form-group">',
								'<label for="' + dom_ids.geojson + '">GeoJSON</label>',
								'<textarea class="form-control input-sm" ',
								'rows="4" ',
								'id="' + dom_ids.geojson + '" >',
								plain_geojson_str,
								'</textarea>',
								'<div class="small">',
									'Note: You can use a service like ',
									'<a title="GeoJSON editing service" target="_blank" ',
									'href="http://geojson.io/">',
									'http://geojson.io/',
									'<span class="glyphicon glyphicon-new-window"></span></a> ',
									'to create GeoJSON formatted geospatial data for ',
									'pasting in the text area above.',
								'</div>',
								'<input type="hidden" ',
								'id="' + dom_ids.hash_id + '" ',
								'value="' + hash_id + '" />',
								'<input type="hidden" ',
								'id="' + dom_ids.feature_id + '" ',
								'value="' + feature_id + '" />',
							'</div>',
						'</div>',
						'<div class="row">',
							'<div class="col-xs-1">',
							'</div>',
							'<div class="col-xs-10">',
								submit_html,	
							'</div>',
							'<div class="col-xs-1">',
							'</div>',
						'</div>',
					'</div>',
					'<div class="col-xs-7">',
						'<div class="well well-sm">',
							'<label>Time Spans for this Location</label>',
							'<table class="table table-condensed table-striped">',
								'<tbody>',
									when_rows_html,
								'</tbody>',
							'</table>',
						'</div>',
					'</div>',
				'</div>'
			].join('\n');
		}
		return html;
	}
	this.make_plain_geojson_from_edit_feat = function(editfeat){
		// deletes all of the extra stuff, leaving very plain GeoJSON
		// the idea here is that one can directly paste in GeoJSON
		// to make an edit on location
		delete editfeat.id;
		delete editfeat.geometry.id;
		delete editfeat.properties;
		if (editfeat.hasOwnProperty('when')) {
			delete editfeat.when;
		}
		if (editfeat.hasOwnProperty('when_list')) {
			delete editfeat.when_list;
		}
		editfeat.properties = {};
		return editfeat;
	}
	this.make_feature_dom_ids = function(edit_i){
		//makes dom_ids for when items, based on the
		//edit feature index (edit_i) and the
		//when_list index (when_i)
		var dom_ids = {
			hash_id: 'geo-hash-id-' + edit_i,
			feature_id: 'geo-feature-id-' + edit_i,
			geojson: 'geo-geojson-' + edit_i,
			lat: 'geo-lat-' + edit_i,
			lon: 'geo-lon-' + edit_i,
			new_outer: 'geo-new-outer-' + edit_i,
			valid: 'geo-valid-' + edit_i
		};
		return dom_ids;
	}
	this.make_geo_submit_html = function(edit_i){
		var new_feature = false;
		if (new_feature) {
			var new_button_label = 'Submit New';
			var new_button_icon = 'glyphicon glyphicon-plus';
		}
		else{
			var new_button_label = 'Submit Geospatial';
			var new_button_icon = 'glyphicon glyphicon-edit';
		}
		var new_button_html = [
			'<button title="Submit Geospatial Feature" ',
			'class="btn btn-primary btn-xs btn-block" ',
			'onclick="' + this.name + '.submitGeoFeature(' + edit_i + ');">',
			'<span class="' + new_button_icon + '"></span>' ,
			new_button_label,
			'</button>',
		].join('\n');
		return new_button_html;
	}
	this.make_when_html = function(edit_i, when_i, when_obj){
		if (when_obj['reference-type'] == 'specified') {
			// this makes an editing form for existing ranges
			var html = this.make_when_form_html(edit_i, when_i, when_obj);
		}
		else if (when_obj.hash_id == false) {
			// a new when edit form
			var html = this.make_when_form_html(edit_i, when_i, when_obj);
		}
		else{
			var html = '';
		}
		return html;
	}
	this.make_when_form_html = function(edit_i, when_i, when_obj){
		var button_height_offset = '26px;';
		var dom_ids = this.make_when_dom_ids(edit_i, when_i);
		if (when_obj.start != false) {
			var start_year = this.iso_to_float_date(when_obj.start);
		}
		else{
			var start_year = '';
		}
		if (when_obj.stop != false) {
			var stop_year = this.iso_to_float_date(when_obj.stop);
		}
		else{
			var stop_year = '';
		}
		if (when_obj.hash_id != false) {
			var hash_id = when_obj.hash_id;
			var del_style = ' style="margin-top: ' + button_height_offset + '" ';
			var del_title = 'Delete this date range';
			var del_button_html = [
				'<div ' + del_style + ' >',
				'<button title="' + del_title + '" ',
				'class="btn btn btn-danger btn-xs" ',
				'onclick="' + this.name + '.deleteDateRange(' + edit_i + ', ' + when_i + ');">',
				'<span class="glyphicon glyphicon-remove-sign"></span>',
				'</button>',
				'</div>'
			].join('\n');
			var new_button_html = this.make_date_range_submit_html(edit_i, when_i, false);
			var new_note_html = '';
		}
		else{
			var hash_id = '';
			var del_button_html = '';
			var new_button_html = this.make_date_range_submit_html(edit_i, when_i, true);
			var new_note_html = '<p class="small">If needing a new date range, add valid integer start and end years</p>';
		}
		
		var html = [
			'<tr>',	
				'<td class="col-xs-1">',
					del_button_html,
				'</td>',
				'<td class="col-xs-3">',
					'<input type="hidden" id="' + dom_ids.hash_id + '" ',
					'value="' + hash_id + '" />',
					'<div class="form-group">',
						'<label class="small" for="' + dom_ids.start + '">Start Year</label>',
						'<input id="' + dom_ids.start + '" class="form-control input-sm" ',
						'onkeydown="' + this.name + '.validate_year_range(' + edit_i + ', ' + when_i + ');" ',
						'onkeyup="' + this.name + '.validate_year_range(' + edit_i + ', ' + when_i + ');" ',
						'type="text" value="' + start_year + '" placeholder="Beginning of date range (- for BCE)" />',
					'</div>',
				'</td>',
				'<td class="col-xs-3">',
					'<div class="form-group">',
						'<label class="small" for="' + dom_ids.stop + '">End Year</label>',
						'<input id="' + dom_ids.stop + '" class="form-control input-sm" ',
						'onkeydown="' + this.name + '.validate_year_range(' + edit_i + ', ' + when_i + ');" ',
						'onkeyup="' + this.name + '.validate_year_range(' + edit_i + ', ' + when_i + ');" ',
						'type="text" value="' + stop_year + '" placeholder="End of date range (- for BCE)" />',
					'</div>',
				'</td>',
				'<td class="col-xs-5">',
					'<div style="margin-top: ' + button_height_offset + '" ',
					'id="' + dom_ids.new_outer + '">',
					new_button_html,	
					'</div>',
					'<div ',
					'id="' + dom_ids.valid + '">',
					new_note_html,
					'</div>',
				'</td>',
			'</tr>'
		].join('\n');
		
		return html;
	}
	this.make_date_range_submit_html = function(edit_i, when_i, new_range){
		if (new_range) {
			var new_button_label = 'Submit New';
			var new_button_icon = 'glyphicon glyphicon-plus';
		}
		else{
			var new_button_label = 'Submit Edit';
			var new_button_icon = 'glyphicon glyphicon-edit';
		}
		var new_button_html = [
			'<button title="Submit date range" ',
			'class="btn btn-primary btn-xs btn-block" ',
			'onclick="' + this.name + '.submitDateRange(' + edit_i + ', ' + when_i + ');">',
			'<span class="' + new_button_icon + '"></span>' ,
			new_button_label,
			'</button>',
		].join('\n');
		return new_button_html;
	}
	this.make_when_dom_ids = function(edit_i, when_i){
		//makes dom_ids for when items, based on the
		//edit feature index (edit_i) and the
		//when_list index (when_i)
		var dom_ids = {
			start: 'when-start-' + edit_i + '-' + when_i,
			stop: 'when-stop-' + edit_i + '-' + when_i,
			hash_id: 'when-hash-id-' + edit_i + '-' + when_i,
			new_outer: 'when-new-outer-' + edit_i + '-' + when_i,
			valid: 'when-valid-' + edit_i + '-' + when_i
		};
		return dom_ids;
	}
	
	/*
	 * AJAX functions for editing geodata
	 */
	this.submitGeoFeature = function(edit_i){
		var geo_dom_ids = this.make_feature_dom_ids(edit_i);
		var hash_id = document.getElementById(geo_dom_ids.hash_id).value;
		var lat = document.getElementById(geo_dom_ids.lat).value;
		var lon = document.getElementById(geo_dom_ids.lon).value;
		var feature_id = document.getElementById(geo_dom_ids.feature_id).value;
		var geojson = document.getElementById(geo_dom_ids.geojson).value;
		var meta_type = 'oc-gen:discovey-location';
		var specificity = 0;
		if (geojson.length < 2) {
			var feature_type = 'Point';
		}
		else{
			var feature_type = 'Polygon';
		}
		var url = this.make_url("/edit/add-update-geo-data/") + encodeURIComponent(this.item_uuid);
		var req = $.ajax({
			type: "POST",
			url: url,
			dataType: "json",
			data: {
				hash_id: hash_id,
				latitude: lat,
				longitude: lon,
				geojson: geojson,
				specificity: specificity,
				meta_type: meta_type,
				ftype: feature_type,
				feature_id: feature_id,
				source_id: 'web-form',
				csrfmiddlewaretoken: csrftoken},
			context: this,
			success: this.submitGeoFeatureDone,
			error: function (request, status, error) {
				alert('Problem updating / adding geo-data: ' + status);
			}
		});
		return req;
	}
	this.submitGeoFeatureDone = function(data){
		// too many things to change, so reload the whole page
		location.reload(true);
	}
	
	/*
	 * AJAX functions for editing date ranges
	 */
	this.submitDateRange = function(edit_i, when_i){
		var is_valid = this.validate_year_range(edit_i, when_i);
		if (is_valid) {
			//submit the date range data
			var geo_dom_ids = this.make_feature_dom_ids(edit_i);
			var dom_ids = this.make_when_dom_ids(edit_i, when_i);
			var hash_id = document.getElementById(dom_ids.hash_id).value;
			var start_year = document.getElementById(dom_ids.start).value;
			var stop_year = document.getElementById(dom_ids.stop).value;
			var meta_type = 'oc-gen:formation-use-life';
			var when_type = 'Interval';
			var feature_id = document.getElementById(geo_dom_ids.feature_id).value;
			var url = this.make_url("/edit/add-update-date-range/") + encodeURIComponent(this.item_uuid);
			var req = $.ajax({
				type: "POST",
				url: url,
				dataType: "json",
				data: {
					hash_id: hash_id,
					earliest: start_year,
					start: start_year,
					stop: stop_year,
					latest: stop_year,
					meta_type: meta_type,
					when_type: when_type,
					feature_id: feature_id,
					source_id: 'web-form',
					csrfmiddlewaretoken: csrftoken},
				context: this,
				success: this.submitDateRangeDone,
				error: function (request, status, error) {
					alert('Problem updating / adding the date range: ' + status);
				}
			});
			return req;
		}
		else{
			alert('not valid');
			return false;
		}
	}
	this.submitDateRangeDone = function(data){
		// too many things to change, so reload the whole page
		location.reload(true);
	}
	this.deleteDateRange = function(edit_i, when_i){
		var dom_ids = this.make_when_dom_ids(edit_i, when_i);
		var hash_id = document.getElementById(dom_ids.hash_id).value;
		var url = this.make_url("/edit/delete-date-range/") + encodeURIComponent(this.item_uuid);
		var req = $.ajax({
			type: "POST",
			url: url,
			dataType: "json",
			data: {
				hash_id: hash_id,
				csrfmiddlewaretoken: csrftoken},
			context: this,
			success: this.deleteDateRangeDone,
			error: function (request, status, error) {
				alert('Problem deleteing date range: ' + status);
			}
		});
		return req;
	}
	this.deleteDateRangeDone = function(data){
		// too many things to change, so reload the whole page
		location.reload(true);
	}
	
	
	
	/*
	 * Validation related functions
	 */
	this.validate_year_range = function(edit_i, when_i){
		var dom_ids = this.make_when_dom_ids(edit_i, when_i);
		var valid_dom = document.getElementById(dom_ids.valid);
		var button_parent_dom = document.getElementById(dom_ids.new_outer);
		var start_year = document.getElementById(dom_ids.start).value;
		var stop_year = document.getElementById(dom_ids.stop).value;
		var hash_id = document.getElementById(dom_ids.hash_id).value;
		if (hash_id.length > 1) {
			//we've got the hash_id for an existing date range
			var new_range = false;
		}
		else{
			var new_range = true;
		}
		
		var start_valid = this.validate_year_val(start_year);
		var stop_valid = this.validate_year_val(stop_year);	
		if (start_valid == false || stop_valid == false) {
			var is_valid = false;
			this.make_validation_html('Make sure your start and end years are integer values',
											  false,
											  dom_ids.valid);
			// button_parent_dom.innerHTML = '';
		}
		else{
			var is_valid = true;
			this.make_validation_html('Start and end years are valid integer values',
											  true,
											  dom_ids.valid);
			button_parent_dom.innerHTML = this.make_date_range_submit_html(edit_i,
																		   when_i,
																		   new_range);
		}
		return is_valid;
	}
	this.make_validation_html = function(message_html, is_valid, valid_dom_id){
		if (is_valid) {
			var icon_html = '<span class="glyphicon glyphicon-ok-circle" aria-hidden="true"></span>';
			var alert_class = "alert alert-success";
		}
		else{
			var icon_html = '<span class="glyphicon glyphicon-warning-sign" aria-hidden="true"></span>';
			var alert_class = 'alert alert-warning';
		}
		var alert_html = [
				'<div role="alert" class="' + alert_class + '" >',
					icon_html,
					message_html,
				'</div>'
			].join('\n');
		
		if (valid_dom_id != false) {
			if (document.getElementById(valid_dom_id)) {
				var act_dom = document.getElementById(valid_dom_id);
				act_dom.innerHTML = alert_html;
			}
		}
		return alert_html;
	}
	this.validate_year_val = function(raw_check_val){	
		var objRegExp  = /(^-?\d\d*$)/;  
		//check for integer characters
		var is_valid = objRegExp.test(raw_check_val);
		return is_valid;
	}
	this.isInt = function(x){
        return (typeof x === 'number') && (x % 1 === 0);
   }
	this.iso_to_float_date = function(iso_text){
		if (iso_text.indexOf('-') == 0) {
			//the date is a negative, it's BCE
			var output = parseInt(iso_text) - 1;
		}
		else if (iso_text == '0000' || iso_text == '+0000') {
			var output = -1;
		}
		else{
			var output = parseInt(iso_text);
		}
		return output;
	}
	
	
	/* Generally useful functions for making urls, loading gifs
	 *
	 */
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