/*
 * Functions to explore a list-based hiearchy tree
 */
var hierarchy_data = {}; // object for containment data in memory
var hierarchy_objs = {}; // object to hold all of the hiearchies
var data_loads = 1;
function hierarchy(parent_id, act_dom_id) {
	
	this.act_dom_id = act_dom_id;
	this.parent_id = parent_id;
	this.object_prefix = 'tree_' + data_loads;
	this.edit_links = true;
	this.view_links = true;
	this.class_subdivide = true;
	this.data = false;
	this.button_dom_id = false;
	this.expanded = true;
	this.get_data = function(){
		// ajax request to get the data for this hiearchy
		this.show_loading();
		var url = base_url + "/entities/contain-children/" + encodeURIComponent(this.parent_id);
		return $.ajax({
				type: "GET",
				url: url,
				dataType: "json",
				context: this,
				data: {depth: 2},
				success: this.get_dataDone
		});
	}
	this.get_dataDone = function(data){
		//handle successful results of getting data
		data_loads += 1;
		hierarchy_data[this.parent_id] = data;
		this.show_data();
	}
	this.show_loading = function(){
		//display a spinning gif for loading
		if (document.getElementById(this.act_dom_id)) {
			var act_dom = document.getElementById(this.act_dom_id);
			var html = [
			'<div class="row">',
			'<div class="col-sm-1">',
			'<img alt="loading..." src="' + base_url + '/static/oc/images/ui/waiting.gif" />',
			'</div>',
			'<div class="col-sm-11">',
			'Loading...',
			'</div>',
			'</div>'
			].join('\n');
			act_dom.innerHTML = html;
		}
	}
	this.show_data = function(){
		//display data loaded from 
		if (document.getElementById(this.act_dom_id)) {
			if (this.parent_id in hierarchy_data) {
				var data = hierarchy_data[this.parent_id];
				//get the cashed data to display a tree
				var act_dom = document.getElementById(this.act_dom_id);
				var html = this.make_data_html(data);
				act_dom.innerHTML = html;
			}
			this.make_collapse_botton();
			$('#' + this.act_dom_id).collapse('show');
			this.expanded = true;
		}
	}
	this.exec_toggle_collapse = function(){
		var link_dom_id = this.act_dom_id.replace('-more-', '-expa-');
		if (this.expanded) {
			$('#' + this.act_dom_id).collapse('hide');
			//alert('hidden: ' + link_dom_id);
			if (document.getElementById(link_dom_id)) {
				var a_link = document.getElementById(link_dom_id);
				a_link.innerHTML = '<span class="hierarchy-tog glyphicon glyphicon-plus" aria-hidden="true"></span>';
			}
			this.expanded = false;
		}
		else{
			$('#' + this.act_dom_id).collapse('show');
			//alert('hidden: ' + link_dom_id);
			if (document.getElementById(link_dom_id)) {
				var a_link = document.getElementById(link_dom_id);
				a_link.innerHTML = '<span class="hierarchy-tog glyphicon glyphicon-minus" aria-hidden="true"></span>';
			}
			this.expanded = true;
		}
	}
	this.make_data_html = function(data){
		var html = [];
		for (var i = 0, length = data.length; i < length; i++) {
			//html.push('<ul class="list-group" style="margin-bottom:5px">');
			html.push('<ul class="list-unstyled">');
			var children_html = this.make_children_html(data[i].children, i);
			html.push(children_html);
			html.push('</ul>');
		}
		return html.join('\n');
	}
	this.make_children_html = function(children, node_i){
		var html = [];
		for (var i = 0, length = children.length; i < length; i++) {
			var child = children[i];
			if (child.children.length > 0) {
				//this child has children so make a loading carrot for it.
				var tog_html = this.make_load_more_html(child.id, node_i, i);
				var children_area_html = this.make_more_div_html(node_i, i);
			}
			else{
				var tog_html = '<span class="glyphicon glyphicon-file" aria-hidden="true"></span>';
				var children_area_html = '';
			}
			//html.push('<li class="list-group-item" style="border:none; padding:5px;">');
			html.push('<li>');
			//html.push('<div class="row">');
			//html.push('<div class="col-sm-1">');
			html.push(tog_html);
			//html.push('</div>');
			//html.push('<div class="col-sm-11">');
			html.push(child.label);
			//html.push('</div>');
			//html.push('</div>');
			html.push(children_area_html);
			html.push('</li>');
		}
		return html.join('\n');
	}
	this.make_load_more_html = function(item_id, node_i, index){
		// makes html for the 
		var dom_id = this.object_prefix + '-exp-' + node_i + '-' +index;
		var more_div_dom_id = this.object_prefix + '-more-' + node_i + '-' +index;
		var tog_html = [
			'<span id="' + dom_id + '">',
			'<a title="Click to load more data and expand" role="button" ',
			'onclick="load_expand(\''+ item_id + '\', \''+ more_div_dom_id + '\', \''+ dom_id + '\');">',
			'<span class="glyphicon glyphicon-plus" aria-hidden="true">',
			'</span>',
			'</a>',
			'</span>'
		].join('\n');
		return tog_html;
	}
	this.make_more_div_html = function(node_i, index){
		var more_div_dom_id = this.object_prefix + '-more-' + node_i + '-' +index;
		var html = [
		'<div id="' + more_div_dom_id + '" class="tree-cont container collapse" style="margin-top:5px; margin-bottom:5px">',
		'</div>'
		].join('\n');
		return html;
	}
	this.make_collapse_botton = function(){
		if (this.button_dom_id != false) {
			if (document.getElementById(this.button_dom_id)) {
				var button_a_id = this.button_dom_id.replace('-exp-', '-expa-');
				var tog_html = [
				'<a title="Click to expand" data-toggle="collapse" expanded="true" ',
				//'href="#' + act_dom_id + '" role="button" class="hierarchy-exp" aria-expanded="true" ',
				'onclick="collapse_toggle(\'' + this.object_prefix + '\',\'' + act_dom_id + '\')" role="button" class="hierarchy-exp" aria-expanded="true" ',
				'id="' + button_a_id + '" >',
				'<span class="glyphicon glyphicon-minus hierarchy-tog" aria-hidden="true">',
				'</span>',
				'</a>'
				].join('\n');
				var act_dom = document.getElementById(this.button_dom_id);
				act_dom.innerHTML = tog_html;
			}
		}
	}
}

function load_expand(parent_id, act_dom_id, button_dom_id){
	// expand a node in the tree by loading new data and populating the html
	if (document.getElementById(act_dom_id)) {
		var expanded_tree = new hierarchy(parent_id, act_dom_id);
		expanded_tree.button_dom_id = button_dom_id;
		expanded_tree.get_data();
		var tree_key = expanded_tree.object_prefix; 
		hierarchy_objs[tree_key] = expanded_tree;
	}
}

function collapse_toggle(tree_key, act_dom_id){
	// this calls the appropriate tree object to show or hide a node.
	if (tree_key in hierarchy_objs) {
		var tree = hierarchy_objs[tree_key];
		tree.exec_toggle_collapse();
		hierarchy_objs[tree_key] = tree;
	}
}
