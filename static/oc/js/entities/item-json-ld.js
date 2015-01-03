/*
 * Functions for Interacting with Open Context item JSON-LD
 */
function item_object(item_type, uuid){
	this.data =  false;
	this.error = false;
	this.uuid = uuid;
	this.item_type = item_type;
	this.host = '../../';
	this.req = false;
	this.exec_before_data_get = false; // can add a function to complete before AJAX data retreval
	this.exec_after_data_get = false; // can add a function to complete after AJAX data is retrieved
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
		var url = this.host + this.item_type + "/" + encodeURIComponent(this.uuid) + ".json";
		this.req =  $.ajax({
			type: "GET",
			url: url,
			context: this,
			dataType: "json",
			//async: false,
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
	this.getParent = function(){
		// gets a object for the item's immediate parent, if it exists
		var output = false;
		if (this.data != false) {
			if (this.data['oc-gen:has-context-path'] !== undefined) {
				if (this.data['oc-gen:has-context-path']['oc-gen:has-path-items'] !== undefined) {
					var pcount = this.data['oc-gen:has-context-path']['oc-gen:has-path-items'].length;
					output = this.data['oc-gen:has-context-path']['oc-gen:has-path-items'][pcount-1];
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
}
