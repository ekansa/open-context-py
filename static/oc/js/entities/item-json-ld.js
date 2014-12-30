/*
 * Functions for Interacting with Open Context item JSON-LD
 */
var item_obj = {
	data: false,
	uuid: false,
	item_type: false,
	host: '../../',
	getParent: function(){
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

function getItemJSON(host, item_type, uuid){
	// AJAX request to get an item's JSON-LD
	var url = host + item_type + "/" + encodeURIComponent(uuid) + ".json";
	return  $.ajax({
		type: "GET",
		url: url,
		async: false,
		dataType: "json",
		success: getItemJSONDone
	});
}

function getItemJSONDone(data){
	// AJAX response for an item's JSON-LD
	item_obj.data = data;
	return data;
}

function create_item_object_locally(item_type, uuid){
	// Calls the local server to create an item_object
	item_obj.item_type = item_type;
	item_obj.uuid = uuid;
	getItemJSON(item_obj.host, item_obj.item_type, item_obj.uuid);
	console.log(item_obj);
}