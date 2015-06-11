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
		if (data.stable_ids.length > 0) {
			var stable_ids_html = this.make_html_stable_ids(data.stable_ids);
			var row = '<tr>';
			row += '<td>Stable / Persistent Identifier</td>';
			row += '<td>' + stable_ids_html + '</td>';
			row += '</tr>';
			html.push(row);
		}
		resultDom.innerHTML = html.join("\n");
	}
	this.dialogModal_html = function(){
		var html = [
		'<style type="text/css">',
		'.uri-id {max-width: 200px; word-wrap: break-word;}',
		'</style>',
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
		if (objects.length > 1) {
			var do_updown = true;
		}
		else{
			var do_updown = false;
		}
		for (var i = 0, length = objects.length; i < length; i++) {
			var obj = objects[i];
			var hash_id = obj.hash_id;
			var obj_html = this.make_html_link_data_item(obj);
			obj.predicate_label = predicate_label;
			var label = this.make_ld_item_label(obj);
			obj.label = label;
			this.all_objects[hash_id] = obj;
			if (obj.sort < 1) {
				var sorting = '[Not sorted]';
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
			if (do_updown) {
				// we have multiple objects so we may want to rank them
				var up_html = [
					'<div style="margin-top: 5px;">',
					'<button class="btn btn btn-info btn-xs" ',
					'onclick="' + this.name + '.rankAnnotation(\''+ hash_id +'\', -1);" ',
					'title="Higher rank in sort order">',
					'<span class="glyphicon glyphicon-arrow-up"></span>',
					'</button>',
					'</div>'
				].join("\n");
				var down_html = [
					'<div style="margin-top: 2px;">',
					'<button class="btn btn btn-info btn-xs" ',
					'onclick="' + this.name + '.rankAnnotation(\''+ hash_id +'\', 1);" ',
					'title="Lower rank in sort order">',
					'<span class="glyphicon glyphicon-arrow-down"></span>',
					'</button>',
					'</div>'
				].join("\n");
				var up_down = up_html + down_html;
			}
			else{
				var up_down = '';
			}
			var row = [
				'<div class="row">',
				'<div class="col-xs-1">',
				delete_html,
				'</div>',
				'<div class="col-xs-2 text-center">',
				sorting,
				'</div>',
				'<div class="col-xs-1">',
				up_down,
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
			var ld_html = label + '<br/><samp class="uri-id">' + ld_id + '</samp>';
		}
		else{
			var ld_html = label;
		}
		return ld_html;
	}
	this.make_html_stable_ids = function(stable_ids){
		var html = [];
		for (var i = 0, length = stable_ids.length; i < length; i++) {
			var id_obj = stable_ids[i];
			var obj_html = this.make_stable_id_html(id_obj);
			var delete_html = [
				'<div style="margin-top: 10px;">',
				'<button class="btn btn-danger btn-xs" ',
				'onclick="' + this.name + '.deleteStableID(\''+ id_obj.type +'\', \''+ id_obj.stable_id +'\');" ',
				'title="Delete this stable ID">',
				'<span class="glyphicon glyphicon-remove-sign"></span>',
				'</button>',
				'</div>'
			].join("\n");
			var row = [
				'<div class="row">',
				'<div class="col-xs-1">',
				delete_html,
				'</div>',
				'<div class="col-xs-3 text-right" style="margin-top: 10px;">',
				id_obj.type,
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
	this.make_stable_id_html = function(id_obj){
		var ld_id = '<a target="_blank" href="' + id_obj.id + '">';
		ld_id += id_obj.id;
		ld_id += ' <span class="glyphicon glyphicon-new-window"></span>';
		ld_id += '</a>'
		return id_obj.stable_id + '<br/><samp class="uri-id">' + ld_id + '</samp>';
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
	this.rankAnnotation = function(hash_id, sort_change){
		// re-rank the sorting of an annotation accoding to a direction
		// sort_change = -1 is a lower sort value (move toward 1st place)
		// sort_change = 1 is a higher sort order (move toward last place)
		this.exec_rankAnnotation(hash_id, sort_change).then(this.getAnnotations);
	}
	this.exec_rankAnnotation = function(hash_id, sort_change){
		// sends the AJAX request to change the sort order
		var url = "../../edit/edit-annotation/" + encodeURIComponent(this.entity_id);
		return req = $.ajax({
			type: "POST",
			url: url,
			dataType: "json",
			context: this,
			data: {
				hash_id: hash_id,
				sort_change: sort_change,
				csrfmiddlewaretoken: csrftoken},
			success: this.rankAnnotationDone
		});
	}
	this.rankAnnotationDone = function(data){
		return true;
	}
	this.deleteStableID = function(type, stable_id){
		/* Sends a request to delete an annotation by the hash-id */
		var html = [
			'<div style="padding:10px;" class="container-fluid">',
			'<div class="row">',
			'<div class="col-xs-12">',
			'<h4>Are you sure you want to delete this stable identifier?</h4>',
			'<p><samp>' + type + ' ',
			stable_id + '</samp></p>',
			'</div>',
			'</div>',
			'<div class="row">',
			'<div class="col-xs-6">',
			'<button class="btn btn-danger btn-sm" ',
			'onclick="' + this.name + '.conDeleteStableID(\''+ stable_id +'\');" >',
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
	this.conDeleteStableID = function(stable_id){
		$("#" + this.name + "-modal-id").modal('hide');
		this.exec_deleteStableID(stable_id);
	}
	this.exec_deleteStableID = function(stable_id){
		var url = "../../edit/delete-item-stable-id/" + encodeURIComponent(this.entity_id);
		return req = $.ajax({
			type: "POST",
			url: url,
			dataType: "json",
			context: this,
			data: {
				stable_id: stable_id,
				csrfmiddlewaretoken: csrftoken},
			success: this.deleteStableIdDone
		});
	}
	this.deleteStableIdDone = function(data){
		console.log(data);
		location.reload(true);
	}
}


