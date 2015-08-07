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
						if (data_type == 'id') {
							var act_value = {
								id: raw_value.id,
								uuid: this.getUUIDfrom_OC_URI(raw_value.id),
								slug: raw_value.slug,
								label: raw_value.label,
								literal: null
							}
						}
						else if(data_type == 'xsd:string') {
							var act_value = {
								id: raw_value.id,
								literal: raw_value['xsd:string']
							}
						}
						else{
							var act_value = {
								id: false,
								literal: raw_value
							}
						}
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
							if (data_type == 'id') {
								var act_value = {
									id: raw_value.id,
									uuid: this.getUUIDfrom_OC_URI(raw_value.id),
									slug: raw_value.slug,
									label: raw_value.label,
									literal: null
								}
							}
							else if(data_type == 'xsd:string') {
								var act_value = {
									id: raw_value.id,
									literal: raw_value['xsd:string']
								}
							}
							else{
								var act_value = {
									id: false,
									literal: raw_value
								}
							}
							output.push(act_value);
						}
					}
				}
			}
		}
		return output;
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
			if (this.data['oc-gen:has-obs'] !== undefined) {
				if (this.data['oc-gen:has-context-path']['oc-gen:has-path-items'] !== undefined) {
					var pcount = this.data['oc-gen:has-context-path']['oc-gen:has-path-items'].length;
					output = this.data['oc-gen:has-context-path']['oc-gen:has-path-items'][pcount-1];
					output['uuid'] = this.getUUIDfrom_OC_URI(output['id']);
				}	
			}
		}
		return output;
	};
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
