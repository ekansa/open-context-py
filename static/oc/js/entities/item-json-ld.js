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
		console.log(this.data);
	}
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
	}
	
}
