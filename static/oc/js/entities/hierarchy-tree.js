/*
 * Functions to explore a list-based hiearchy tree
 */
var hierarchy_data = {}; // object for containment data in memory
var hierarchy_objs = {}; // object to hold all of the hiearchies
var data_loads = 1;
function hierarchy(parent_id, act_dom_id) {
	 this.make_url = function(relative_url){
	 //makes a URL for requests, checking if the base_url is set	
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
	 this.act_dom_id = act_dom_id;
	 this.parent_id = parent_id;
	 this.object_prefix = 'tree_' + data_loads;
	 this.class_subdivide = true;
	 this.request_url = this.make_url("/entities/contain-children/");
	 this.root_node = false;
	 this.collapse_root = false;
	 this.data = false;
	 this.button_dom_id = false;
	 this.expanded = true;
	 this.exec_primary_onclick = false;  //name of function for onclick interactions with an item in the tree
	 this.exec_primary_title = ''; //text for titles that explain onclick interacction to user
	 this.exec_primary_passed_val = false; //additional value passed as a parameter for function in onclick interations
	 this.exec_primary_link = 'edit';
	 //this.supplemental_links = ['view'];
	 this.supplemental_links = [];
      this.vocab_ontology = false;  // are we doing a local vocabulary or ontology?
	 this.do_description_tree = function(){
		 // if doing a desciption tree, change the request URL
		 this.request_url = this.make_url("/entities/description-children/");
	 }
	 this.do_entity_hierarchy_tree = function(){
			this.request_url = this.make_url("/entities/hierarchy-children/"); 
	 }
      this.do_vocab_hierarchy_tree = function(){
               this.vocab_ontology = true;
			this.request_url = this.make_url("/vocabularies/"); 
	 }
	 this.get_data = function(){
		 // ajax request to get the data for this hiearchy
		 this.show_loading();
		 var url = this.request_url + encodeURIComponent(this.parent_id);
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
			  if (!this.root_node) {
				  $('#' + this.act_dom_id).collapse('show');
			  }
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
				this.make_collapse_button();
				if (this.root_node && this.collapse_root) {
					 $('#' + this.act_dom_id).collapse('hide');
					 this.expanded = false;
				}
				else{
					 $('#' + this.act_dom_id).collapse('show');
					 this.expanded = true;
				}
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
          if ('id' in data){
               // the data is not a list, but a single dictionary object
               var html = this.make_nonlist_data_html(data);
          }
		else{
               // the data is in a list, so iterate through the list
               var html = [];
               for (var i = 0, length = data.length; i < length; i++) {
                    //html.push('<ul class="list-group" style="margin-bottom:5px">');
                    var rec = data[i];
                    if ('id' in rec || 'href' in rec) {
                        if (this.vocab_ontology){
                             // use the href property for linking vocab concepts
                             var item_html = this.make_item_linking_html(rec.href, rec.label, false);
                             html.push(item_html);
                        }
                        else{
                             // use the item ID for linking
                             var item_html = this.make_item_linking_html(rec.id, rec.label, rec.item_type);
                        }
                    }
                    if('root' in rec && this.vocab_ontology){
                        var item_html = '<h5>' + rec.root + '</h5>';
                        html.push(item_html);
                    }
                    if('children' in rec){
                        html.push('<ul class="list-unstyled">');
                        var children_html = this.make_children_html(rec.children, i);
                        html.push(children_html);
                        html.push('</ul>');
                    }
               }
          }
		return html.join('\n');
	 }
      this.make_nonlist_data_html = function(data){
          // makes a list of html for data that's not in a list
          var html_list = [];
          if('children' in data){
               html_list.push('<ul class="list-unstyled">');
               var children_html = this.make_children_html(data.children, 0);
               html_list.push(children_html);
               html_list.push('</ul>');
		 }
		 return html_list;
	 }
	 this.make_children_html = function(children, node_i){
		 var html = [];
           
		 var class_list = [];
		 if (this.class_subdivide) {
			 // sub divide children into lists of seperate classes
			 var classes = {};
			 for (var i = 0, length = children.length; i < length; i++) {
				 var child = children[i];
				 if (child.class_label in classes) {
					 classes[child.class_label].push(child);
				 }
				 else{
					 classes[child.class_label] = [child];
					 class_list.push(child.class_label);
				 }
			 }
		 }
		 var html = [];
		 if (class_list.length > 1) {
			 //multiple classes, put them into sub lists
			 for (var i = 0, length = class_list.length; i < length; i++) {
				 var act_class = class_list[i];
				 if (act_class in classes) {
					 var act_c_list = classes[act_class];
					 var children_row_html = this.make_children_rows_html(act_c_list, node_i);
					 html.push('<li>');
					 html.push('<em>' + act_class + '</em>');
					 html.push('<div class="container-fluid" style="margin-top:5px; margin-bottom:5px;">');
					 html.push('<ul class="list-unstyled">');
					 html.push(children_row_html);
					 html.push('</ul>');
					 html.push('</div>');
					 html.push('</li>');
				 }
			 }
		 }
		 else{
			 var children_row_html = this.make_children_rows_html(children, node_i);
			 html.push(children_row_html);
		 }
		 return html.join('\n');
	 }
	 this.make_children_rows_html = function(children, node_i){
		 // makes list elements for children
		 var html = [];
		 for (var i = 0, length = children.length; i < length; i++) {
			 var child = children[i];
			 var child_has_children = false;
			 var tog_html = '<span class="glyphicon glyphicon-file" aria-hidden="true"></span>';
			 var children_area_html = '';
			 if ('children' in child) {
				 if (child.children.length > 0 || child.more) {
					 //this child has children so make a loading carrot for it.
					 child_has_children = true;
				 }
			 }
			 else if ('more' in child) {
				 // the service says it has more children
				 child_has_children = true;
			 }
			 if (child_has_children) {
				 //this child has children so make a loading carrot for it.
                     if (this.vocab_ontology){
                         var slug_id = child.slug + '.json';
                         var tog_html = this.make_load_more_html(slug_id, node_i, i);
                     }
                     else{
                         var tog_html = this.make_load_more_html(child.id, node_i, i);    
                     }
				 var children_area_html = this.make_more_div_html(node_i, i);
			 }
			 else{
				 var tog_html = '<span class="glyphicon glyphicon-file" aria-hidden="true"></span>';
				 var children_area_html = '';
			 }
                if (this.vocab_ontology){
                    // use the href property for linking vocab concepts
                    var item_html = this.make_item_linking_html(child.href, child.label, false);
                }
                else{
                    var item_html = this.make_item_linking_html(child.id, child.label, child.item_type);
                }
			 html.push('<li>');
			 html.push(tog_html);
			 html.push(item_html);
			 html.push(children_area_html);
			 html.push('</li>');
		 }
		 return html.join('\n');
	 }
	 this.make_load_more_html = function(item_id, node_i, index){
		 // makes html for the 
		 var dom_id = this.object_prefix + '-exp-' + node_i + '-' + index;
		 var more_div_dom_id = this.object_prefix + '-more-' + node_i + '-' + index;
		 var tog_html = [
			 '<span id="' + dom_id + '">',
			 '<a title="Click to load more data and expand" role="button" ',
			 'onclick="load_expand(\''+ this.object_prefix + '\', \''+ item_id + '\', \''+ more_div_dom_id + '\', \''+ dom_id + '\');">',
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
		 '<div id="' + more_div_dom_id + '" class="tree-cont container-fluid collapse" style="margin-top:5px; margin-bottom:5px">',
		 '</div>'
		 ].join('\n');
		 return html;
	 }
	 this.make_collapse_button = function(){
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
	 this.make_item_linking_html = function(id, label, item_type){
		 // makes the html for the primary link (for the label)
		  var item_html = '<a ';
		  if (this.exec_primary_onclick == false) {
				item_html += 'target="_blank" ';
				if (this.exec_primary_link == 'edit') {
					var title = 'Edit in new window';
					var href = base_url + '/edit/items/' + encodeURIComponent(id);
				}
				else{
					var title = 'View in new window';
                         if (this.vocab_ontology){
                              var href = id;
                         }
                         else{
                              var href = base_url + '/' + item_type + '/' + encodeURIComponent(id);
                         }
				}
				item_html += 'title="' + title + '" href="' + href + '" >';
		  }
		  else{
				// case with a function passed for onclick interactions with the
				// item in the tree. useful for integrating the hierarchy tree
				// with other UI components
				item_html += 'role="button" ';
				item_html += ' onclick="' + this.exec_primary_onclick;
				item_html += '(\'' + id + '\', \'' + label + '\', \'' + item_type + '\', \'' + this.exec_primary_passed_val + '\');'
				item_html += '" ';
				item_html += 'title="' + this.exec_primary_title + '" >';
		  }
		  item_html += label + '</a>';
		  if (this.exec_primary_onclick == false && id.indexOf('/') > -1 && !this.vocab_ontology) {
				item_html = label;
		  }
		  // add supplemental links, if configured for supplmental links.
		  var sups = [];
		  for (var i = 0, length = this.supplemental_links.length; i < length; i++) {
				var sup_type = this.supplemental_links[i];
				if (sup_type == 'view') {
					var href = base_url + '/' + item_type + '/' + encodeURIComponent(id);
					var sup_html = [
					'<a target="_blank" title="View in new window" href="' + href + '">',
					'<span class="glyphicon glyphicon-new-window" aria-hidden="true"></span>',
					'</a>'
					].join('\n');
				}
				else if (sup_type == 'edit') {
					var href = base_url + '/' + item_type + '/' + encodeURIComponent(id);
					var sup_html = [
					'<a target="_blank" title="Edit in new window" href="' + href + '">',
					'<span class="glyphicon glyphicon-edit" aria-hidden="true"></span>',
					'</a>'
					].join('\n');
				}
				else{
					var sup_html = false;
				}
				if (sup_html != false) {
					sups.push(sup_html);
				}
		  }
		  if (sups.length > 0) {
				// only add supplemental links if there are 1 or more to add
				item_html += ' (' + sups.join(', ') + ')';
		  }
		  return item_html;
	 }
}

function load_expand(tree_key, parent_id, act_dom_id, button_dom_id){
	// expand a node in the tree by loading new data and populating the html
	 if (document.getElementById(act_dom_id)) {
		  var expanded_tree = new hierarchy(parent_id, act_dom_id);
		  if (tree_key in hierarchy_objs) {
				// so as to use the same request URL for the parent tree
				expanded_tree.request_url = hierarchy_objs[tree_key].request_url;
				expanded_tree.exec_primary_title = hierarchy_objs[tree_key].exec_primary_title;
				expanded_tree.exec_primary_onclick = hierarchy_objs[tree_key].exec_primary_onclick;
				expanded_tree.exec_primary_passed_val = hierarchy_objs[tree_key].exec_primary_passed_val;
                    expanded_tree.exec_primary_link = hierarchy_objs[tree_key].exec_primary_link;
                    expanded_tree.vocab_ontology = hierarchy_objs[tree_key].vocab_ontology;
false
		  }
		  expanded_tree.button_dom_id = button_dom_id;
		  expanded_tree.get_data();
		  var tree_key = expanded_tree.object_prefix; 
		  hierarchy_objs[tree_key] = expanded_tree;
            // console.log(hierarchy_objs);
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
