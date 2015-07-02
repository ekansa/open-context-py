/*
 * Functions to explore a list-based hiearchy tree
 */
var hierarchy_data = {}; // object for containment data in memory

function hierarchy(parent_id, parent_dom_id) {
	
	this.parent_dom_id = parent_dom_id;
	this.parent_id = parent_id;
	this.object_prefix = 'tree-' + (hierarchy_data.length + 1);
	this.edit_links = true;
	this.view_links = true;
	this.class_subdivide = true;
	this.data = false;
	this.get_data = function(){
		
	}
}