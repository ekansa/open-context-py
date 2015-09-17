/*
 * Functions to edit spatial coodinates and time ranges
 */
function geoChronoEdit(item_type, item_uuid){
	this.project_uuid = project_uuid;
	this.item_uuid = item_uuid;
	this.item_type = item_type;
	this.obj_name = 'geochrono_item';
	this.item_json_ld_obj = false;
	this.edit_features = [];
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