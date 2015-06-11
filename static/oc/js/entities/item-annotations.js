/*
 * ------------------------------------------------------------------
	AJAX for entity annotations
 * ------------------------------------------------------------------
*/

function entityAnnotationsObj() {
	/* Object for composing search entities */
	this.name = "act_annotations"; //object name, used for DOM-ID prefixes and object labeling
	this.display_parent_dom_id = "item-annotations-ld-rows";
	this.url = "../../entities/annotations/";
	this.entity_id = false;
	this.getAnnotations = function(){
		var url = this.url + encodeURIComponent(this.entity_id);
		return $.ajax({
			type: "GET",
			url: url,
			dataType: "json",
			context: this,
			success: this.getAnnotationsDone
		});
	}
	this.all_objects = {}
	this.getAnnotationsDone = function(data){
		/* Displays the annotations to an item */
		this.all_objects = {} // clears any previous objects
		var resultDom = document.getElementById(this.display_parent_dom_id);
		var modal_html = this.dialogModal_html();
		html = []
		for (var i = 0, length = data.preds_objs.length; i < length; i++) {
			// to do, add HTML output for predicates, then objects
			var pred_html = this.make_html_link_data_item(data.preds_objs[i]);
			var predicate_label = this.make_ld_item_label(data.preds_objs[i]);
			var objects = data.preds_objs[i].objects;
			var objects_html = this.displayPredicateObjects(predicate_label, objects);
			if (i == 0) {
				objects_html += modal_html;
			}
			var row = '<tr>';
			row += '<td>' + pred_html + '</td>';
			row += '<td>' + objects_html + '</td>';
			row += '</tr>';
			html.push(row);
		}
		resultDom.innerHTML = html.join("\n");
	}
	this.dialogModal_html = function(){
		var html = [
		'<div class="modal fade bs-example-modal-sm" tabindex="-1" ',
		'id="' + this.name + '-modal-id" ',
		'role="dialog" aria-labelledby="mySmallModalLabel" aria-hidden="true">',
		'<div class="modal-dialog modal-sm">',
		'<div class="modal-content" id="' + this.name + '-modal-content">',
		'...',
		'</div>',
		'</div>',
		'</div>',
		].join("\n");
		return html;
	}
	this.displayPredicateObjects = function(predicate_label, objects){
		// display list of objects for a given predicate
		var html = [];
		for (var i = 0, length = objects.length; i < length; i++) {
			var obj = objects[i];
			var hash_id = obj.hash_id;
			var obj_html = this.make_html_link_data_item(obj);
			obj.predicate_label = predicate_label;
			var label = this.make_ld_item_label(obj);
			obj.label = label;
			this.all_objects[hash_id] = obj;
			if (obj.sort < 1) {
				var sorting = '';
			}
			else{
				var sorting = 'Sort:<br/>' + obj.sort;
			}
			var delete_html = [
				'<div style="margin-top: 10px;">',
				'<button class="btn btn-danger btn-xs" ',
				'onclick="' + this.name + '.deleteAnnotation(\''+ hash_id +'\');" ',
				'title="Delete this annotation">',
				'<span class="glyphicon glyphicon-remove-sign"></span>',
				'</button>',
				'</div>'
			].join("\n"); 
			var row = [
				'<div class="row">',
				'<div class="col-xs-1">',
				delete_html,
				'</div>',
				'<div class="col-xs-1">',
				sorting,
				'</div>',
				'<div class="col-xs-1">',
				'',
				'</div>',
				'<div class="col-xs-1">',
				'',
				'</div>',
				'<div class="col-xs-8">',
				'<div style="padding-bottom: 15px;">' + obj_html + '</div>',
				'</div>',
				'</div>',
				'</div>'
			].join("\n");
			html.push(row);
		}
		return html.join("\n");
	}
	this.make_ld_item_label = function(ld_item){
		var label = ld_item.label;
		if (label == false) {
			label = ld_item.id;
		}
		return label;
	}
	this.make_html_link_data_item = function(ld_item){
		var label = this.make_ld_item_label(ld_item);
		if (ld_item.href != false) {
			var ld_id = '<a target="_blank" href="' + ld_item.href + '">';
			ld_id += ld_item.id;
			ld_id += ' <span class="glyphicon glyphicon-new-window"></span>';
			ld_id += '</a>'
		}
		else{
			var ld_id = ld_item.id;
		}
		if (label != ld_id) {
			var ld_html = label + '<br/><samp>' + ld_id + '</samp>';
		}
		else{
			var ld_html = label;
		}
		return ld_html;
	}
	this.deleteAnnotation = function(hash_id){
		/* Sends a request to delete an annotation by the hash-id */
		var html = [
			'<div style="padding:10px;" class="container-fluid">',
			'<div class="row">',
			'<div class="col-xs-12">',
			'<h4>Are you sure you want to remove this assertion?</h4>',
			'<p><samp>' + this.all_objects[hash_id].predicate_label,
			' <span class="glyphicon glyphicon-arrow-right"></span>',
			this.all_objects[hash_id].label + '</samp></p>',
			'</div>',
			'</div>',
			'<div class="row">',
			'<div class="col-xs-6">',
			'<button class="btn btn-danger btn-sm" ',
			'onclick="' + this.name + '.conDeleteAnnotation(\''+ hash_id +'\');" >',
			'<span class="glyphicon glyphicon-remove-sign"></span> DELETE',
			'</button>',
			'</div>',
			'<div class="col-xs-2">',
			'</div>',
			'<div class="col-xs-4">',
			'<button class="btn btn-default btn-sm" ',
			'onclick="' + this.name + '.cancelDelete();" ',
			'title="Cancel">',
			' Cancel',
			'</button>',
			'</div>',
			'</div>',
			'</div>'
		].join("\n");
		var content = document.getElementById(this.name + '-modal-content');
		content.innerHTML = html;
		$("#" + this.name + "-modal-id").modal('show');
	}
	this.conDeleteAnnotation = function(hash_id){
		$("#" + this.name + "-modal-id").modal('hide');
		this.exec_deleteAnnotation(hash_id).then(this.getAnnotations);
	}
	this.exec_deleteAnnotation = function(hash_id){
		var url = "../../edit/delete-annotation/" + encodeURIComponent(this.entity_id);
		return req = $.ajax({
			type: "POST",
			url: url,
			dataType: "json",
			context: this,
			data: {
				hash_id: hash_id,
				csrfmiddlewaretoken: csrftoken},
			success: this.deleteAnnotationDone
		});
	}
	this.deleteAnnotationDone = function(data){
		return true;
	}
	this.cancelDelete = function(){
		$("#" + this.name + "-modal-id").modal('hide');
	}
}


