/*
 * Functions for Interacting with Open Context item JSON-LD
 */
function item_object(item_type, uuid){
	this.data =  false;
	this.error = false;
	this.uuid = uuid;
	this.item_type = item_type;
	this.predicates_by_slug_key = {}; // predicate items by slug key
	this.predicates_by_uuid = {}; // predicate items by uuid key
	this.req = false;
	this.default_language = 'en'; // default language code
	this.exec_before_data_get = false; // can add a function to complete before AJAX data retreval
	this.exec_after_data_get = false; // can add a function to complete after AJAX data is retrieved
	this.do_async = false;
	this.getItemData = function(){
		var output = false;
		if (!this.req) {
			this.getItemJSON();
		}
		else{
			if (!this.error) {
				output = true;
			}
		}
		return output;
	};
	this.getItemJSON = function(){
		/* gets the item JSON-LD from the server */
		if (this.exec_before_data_get != false) {
			// execute some additional supplied function
			if (typeof(this.exec_before_data_get.exec) !== 'undefined') {
				this.exec_before_data_get.exec();
			}
		}
		var url = this.make_url("/" + this.item_type + "/" + encodeURIComponent(this.uuid) + ".json");
		this.req =  $.ajax({
			type: "GET",
			url: url,
			context: this,
			dataType: "json",
			async: this.do_async,
			error: this.getItemJSONerror,
			success: this.getItemJSONDone
		});
	}
	this.getItemJSONerror = function(data){
		/* something horrible happened, record it in the console log */
		console.log(data);
		this.error = true;
	}
	this.getItemJSONDone = function(data){
		/* the JSON-LD becomes this object's data */
		this.data = data;
		if (this.exec_after_data_get != false) {
			// execute some additional supplied function
			if (typeof(this.exec_after_data_get.exec) !== 'undefined') {
				this.exec_after_data_get.exec();
			}
		}
	}
/* --------------------------------------------------
 * Functions for getting commonly needed info from a JSON-LD object
 *
 *
 * --------------------------------------------------
 */
    this.getAltLabel = function(){
		// gets  (SKOS) alt label object, a dictionary object of labels
		// where the key is the language code
		var output = null;
		if (this.data != false) {
			if (this.data['skos:altLabel'] !== undefined) {
				output = this.data['skos:altLabel'];
			}
		}
		return output;
	}
    this.getItemCategories = function(){
		var output = [];
		if (this.data != false) {
			if (this.data['category'] !== undefined) {
				for (var i = 0, length = this.data['category'].length; i < length; i++) {
					var cat_id = this.data['category'][i];
					var cat_item = {
						id: cat_id,
					    label: this.getCategoryLabel(cat_id),
						icon: this.getCategoryIcon(cat_id)
					};
					output.push(cat_item);
				}	
			}
			if (output.length < 1) {
				var cat_item = {
					id: '',
					label: '',
					icon: ''
				};
				output.push(cat_item);
			}
		}
		return output;
	}
    this.getPredicates = function(){
		// gets a list of predicates used in the item
		var output = [];
		if (this.data != false) {
			if (this.data['@context'] !== undefined) {
				var context = this.data['@context'];
				for (var i = 0, length = context.length; i < length; i++) {
					var context_part = context[i];
					if( typeof context_part === 'string' ) {
						// alert('skip the string ' + context_part);
					}
					else{
						//predicates!
						for (var slug_key in context_part) {
							if (context_part.hasOwnProperty(slug_key)) {
								var context_pred =  context_part[slug_key];
								var uuid = false;
								var uri = false;
								var label = false;
								var data_type = false;
								var pred_type = 'variable';
								var slug = slug_key.replace('oc-pred:', '');
								if ('owl:sameAs' in context_pred) {
									uri = context_pred['owl:sameAs'];
									uuid = this.getUUIDfrom_OC_URI(uri);
								}
								if ('label' in context_pred) {
									label = context_pred['label'];
								}
								if ('oc-gen:predType' in context_pred) {
									pred_type = context_pred['oc-gen:predType'];
								}
								if ('type' in context_pred) {
									data_type = context_pred['type'].replace('@', '');
								}
								if ('slug' in context_pred) {
									slug = context_pred['slug'];
								}
								var pred_item = {slug_key: slug_key,
								                 slug: slug,
								                 id: uri,
													  uuid: uuid,
													  label: label,
													  pred_type: pred_type,
													  data_type: data_type};
							   if (uri != false) {
									output.push(pred_item);
									this.predicates_by_slug_key[slug_key] = pred_item;
									this.predicates_by_uuid[uuid] = pred_item;
								}
							}
						}
					}
				}
				// now add a preset predicate type
				var pred_item = {
					slug_key: 'oc-gen:has-note',
					slug: 'oc-gen:has-note',
					id: 'oc-gen:has-note',
					uuid: 'oc-gen:has-note',
					label: 'Note',
					pred_type: 'variable',
					data_type: 'xsd:string'};
				output.push(pred_item);
				this.predicates_by_slug_key[pred_item.slug_key] = pred_item;
				this.predicates_by_uuid[pred_item.uuid] = pred_item;
			}
		}
		return output;
	}
    this.getValuesByPredicateUUID = function(predicate_uuid){
		var output = [];
		var predicates = this.getPredicates();
		if (predicate_uuid in this.predicates_by_uuid) {
			var slug_key = this.predicates_by_uuid[predicate_uuid].slug_key;
			var data_type = this.predicates_by_uuid[predicate_uuid].data_type;
			var observations = this.getObservations();
			for (var i = 0, length = observations.length; i < length; i++) {
				var obs = observations[i];
				if (slug_key in obs) {
					var raw_values = obs[slug_key];
					for (var vi = 0, vlength = raw_values.length; vi < vlength; vi++) {
						var raw_value = raw_values[vi];
						var act_value = this.obs_prop_raw_to_active_value(data_type, raw_value);
						output.push(act_value);
					}
				}
			}
		}
		return output;
	}
	this.getObsValuesByPredicateUUID = function(obs_num, predicate_uuid){
		var output = [];
		var predicates = this.getPredicates();
		if (predicate_uuid in this.predicates_by_uuid) {
			var slug_key = this.predicates_by_uuid[predicate_uuid].slug_key;
			var data_type = this.predicates_by_uuid[predicate_uuid].data_type;
			var observations = this.getObservations();
			for (var i = 0, length = observations.length; i < length; i++) {
				if (obs_num == i) {
					// only look in a specific observation for values
					var obs = observations[i];
					if (slug_key in obs) {
						var raw_values = obs[slug_key];
						for (var vi = 0, vlength = raw_values.length; vi < vlength; vi++) {
							var raw_value = raw_values[vi];
							var act_value = this.obs_prop_raw_to_active_value(data_type, raw_value);
							output.push(act_value);
						}
					}
				}
			}
		}
		return output;
	}
	this.obs_prop_raw_to_active_value = function(data_type, raw_value){
		// converts a raw observation property value
		// to an active value useful for editing functions, etc.
		if (data_type == 'id') {
			var act_value = {
				id: raw_value.id,
				uuid: this.getUUIDfrom_OC_URI(raw_value.id),
				slug: raw_value.slug,
				label: raw_value.label,
				literal: null,
				hash_id: null,
			}
		}
		else if(data_type == 'xsd:string') {
			var act_value = {
				id: raw_value.id,
				uuid: raw_value.id.replace('#string-', ''),
				literal: this.getDefaultString(raw_value['xsd:string']),
				hash_id: null,
				localization: this.getLocalizations(raw_value['xsd:string'])
			}
		}
		else{
			if (raw_value.hasOwnProperty('literal')) {
				var act_value = {
					id: false,
					literal: raw_value.literal,
					hash_id: null,
				}
			}
			else{
				var act_value = {
					id: false,
					literal: raw_value,
					hash_id: null,
				}	
			}
		}
		if (raw_value.hasOwnProperty('hash_id')) {
			act_value.hash_id = raw_value.hash_id;
		}
		return act_value;
	}
	this.getObservations = function(){
		var observations = [];
		if (this.data != false) {
			if (this.data['oc-gen:has-obs'] !== undefined) {
				var observations = this.data['oc-gen:has-obs'];
			}
		}
		return observations;
	}
	this.getParent = function(){
		// gets a object for the item's immediate parent, if it exists
		var output = false;
		if (this.data != false) {
			if (this.data['oc-gen:has-context-path'] !== undefined) {
				if (this.data['oc-gen:has-context-path']['oc-gen:has-path-items'] !== undefined) {
					var pcount = this.data['oc-gen:has-context-path']['oc-gen:has-path-items'].length;
					output = this.data['oc-gen:has-context-path']['oc-gen:has-path-items'][pcount-1];
					output['uuid'] = this.getUUIDfrom_OC_URI(output['id']);
				}	
			}
		}
		return output;
	};
	this.getParentProject = function(){
		// gets an object for the item's parent project
		var output = false;
		if (this.data != false) {
			if (this.data['dc-terms:isPartOf'] !== undefined) {
				for (var i = 0, length = this.data['dc-terms:isPartOf'].length; i < length; i++) {
					var parent_obj = this.data['dc-terms:isPartOf'][i];
					if (parent_obj.id.indexOf('/projects/') >= 0) {
						// the parent item is a project
						var uuid = this.getUUIDfrom_OC_URI(parent_obj.id);
						output = parent_obj;
						output['uuid'] = uuid;
					}
				}
			}
		}
		return output;
	}
	this.getChildren = function(){
		// gets a object for the item's immediate parent, if it exists
		var output = false;
		if (this.data != false) {
			if (this.data['oc-gen:has-contents'] !== undefined) {
				if (this.data['oc-gen:has-contents']['oc-gen:contains'] !== undefined) {
					output = this.data['oc-gen:has-contents']['oc-gen:contains'];
				}	
			}
		}
		return output;
	};
	this.getEditorialStatus = function(){
		// get the project editorial status
		var edit_status = false;
		var output = false;
		if (this.data != false) {
			if (this.data['bibo:status'] !== undefined) {
				for (var i = 0, length = this.data['bibo:status'].length; i < length; i++) {
					var status_item = this.data['bibo:status'][i];
					if (status_item.id.indexOf('http://opencontext.org') >= 0) {
						// this is the Open Context namespace
						var uri_ex = status_item.id.split('/');
						var last_uri_part = uri_ex[uri_ex.length - 1];
						var last_uri_part_ex = last_uri_part.split('-');
						var edit_status = last_uri_part_ex[last_uri_part_ex.length - 1];
						var output = status_item;
						output['edit_status'] = edit_status;
					}
				}
			}
		}
		return output;
	}
	this.getProjectHeros = function(){
		// get the project hero images
		var edit_status = false;
		var output = false;
		if (this.data != false) {
			if (this.data['foaf:depiction'] !== undefined) {
				output = this.data['foaf:depiction'];
			}
		}
		return output;
	}
	this.getMediaFiles = function(){
		// get the media item media files
		var output = false;
		if (this.data != false) {
			if (this.data['oc-gen:has-files'] !== undefined) {
				output = this.data['oc-gen:has-files'];
			}
		}
		return output;
	}
	this.getPersonData = function(){
		// makes an object with person names using the same
		// keys as the database
		var output = false;
		if (this.data != false) {
	        if (this.data['category'] !== undefined) {
				var foaf_type = this.data['category'][0];
			}
			else{
				var foaf_type = '';
			}
			if (this.data['foaf:name'] !== undefined) {
				var combined_name = this.data['foaf:name'];
			}
			else{
				var combined_name = '';
			}
			if (this.data['foaf:givenName'] !== undefined) {
				var given_name = this.data['foaf:givenName'];
			}
			else{
				var given_name = '';
			}
			if (this.data['foaf:familyName'] !== undefined) {
				var surname = this.data['foaf:familyName'];
			}
			else{
				var surname = '';
			}
			if (this.data['foaf:nick'] !== undefined) {
				var initials = this.data['foaf:nick'];
			}
			else{
				var initials = '';
			}
			if (this.data['oc-gen:familyName'] !== undefined) {
				var mid_init = this.data['oc-gen:familyName'];
			}
			else{
				var mid_init = '';
			}
			var output = {
				foaf_type: foaf_type,
				combined_name: combined_name,
				given_name: given_name,
				surname: surname,
				initials: initials,
				mid_init: mid_init
			};
			
		}
		return output;
	}
	this.getCategoryLabel = function(category){
		// gets an icon image src for a category, if it exists
		var output = false;
		if (this.data != false) {
			if (this.data['@graph'] !== undefined) {
				for (var i = 0, length = this.data['@graph'].length; i < length; i++) {
					var graph_item = this.data['@graph'][i];
					if (this.getIDvalue(graph_item) == category) {
						if (graph_item['label'] !== undefined) {
							output = graph_item.label;
							break;
						}
					}
				}
			}
		}
		return output;
	};
	this.getCategoryIcon = function(category){
		// gets an icon image src for a category, if it exists
		var output = false;
		if (this.data != false) {
			if (this.data['@graph'] !== undefined) {
				for (var i = 0, length = this.data['@graph'].length; i < length; i++) {
					if (this.getIDvalue(this.data['@graph'][i]) == category) {
						if (this.data['@graph'][i]['oc-gen:hasIcon'] !== undefined) {
							output = this.getIDvalue(this.data['@graph'][i]['oc-gen:hasIcon'][0]);
							break;
						}
					}
				}
			}
		}
		return output;
	};
	this.predGetDefaultString = function(predicate_key){
		// values for string predicates can be just simple strings (for default language)
		// or they can be dictionary objects if there are localizations given
		// this gets just the default language string
		var output = false;
		if (this.data != false) {
			if (this.data.hasOwnProperty(predicate_key)) {
				output = this.getDefaultString(this.data[predicate_key]);
			}
		}
		return output;
	}
	this.predGetLocalizations = function(predicate_key){
		// values for string predicates can be just simple strings (for default language)
		// or they can be dictionary objects if there are localizations given
		// this gets JUST the dictionary object of localizations (NO default language)
		var output = null;
		if (this.data != false) {
			if (this.data.hasOwnProperty(predicate_key)) {
				output = this.getLocalizations(this.data[predicate_key]);
			}
		}
		return output;
	}
	this.getDefaultString = function(value_obj){
		//gets the default language string from a value obj
		var output = null;
		if (typeof value_obj === 'string' || value_obj instanceof String) {
			output = value_obj;
		}
		else{
			if (this.default_language in value_obj) {
				output = value_obj[this.default_language];
			}
		}
		return output;
	}
	this.getLocalizations = function(value_obj){
		//gets an array  of the localizations (not including the default language)
		var output = null;
		if (typeof value_obj === 'string' || value_obj instanceof String) {
			output = null;
		}
		else{
			output = {};
			for (var key in value_obj) {
				if (value_obj.hasOwnProperty(key)) {
					if (this.default_language != key){
						output[key] = value_obj[key]; 
					}
				}
			}
		}
		return output;
	}
	this.getIDvalue = function(entity_obj){
		// gets an ID for a entity referenced in the JSON-LD
		if (entity_obj['@id'] !== undefined) {
			var output = entity_obj['@id'];
		}
		else if (entity_obj['id'] !== undefined) {
			var output = true;
		}
		else {
			var output = false;
		}
		return output;
	};
	this.getUUIDfrom_OC_URI = function(oc_uri){
		var uri_ex = oc_uri.split("/");
		var len_uri_ex = uri_ex.length;
		if (len_uri_ex > 0) {
			// uuid is the last part
			var output = uri_ex[len_uri_ex - 1]; 
		}
		else{
			// something seems wrong
			var output = oc_uri;
		}
		return output;
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
