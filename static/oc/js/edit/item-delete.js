/*
 * Functions to edit multiple language strings
 */
function deleteItem(){
	this.modal_dom_id = 'delete-modal';
	this.modal_title_dom_id = 'delete-title';
	this.modal_inter_dom_id = 'delete-interface';
	this.invalid_alert_class = 'alert alert-warning';
	this.parent_obj_name = false;
	this.value_num = 0;
	this.obj_name = 'deleteItem';
	this.name = false;
	this.label = 'Label for the item to delete';
	this.dom_ids = null;
	this.edit_uuid = null;
	this.edit_type = false;
	this.edit_project_uuid = false;
	this.act_editorial_type = 'edit-deletion';
	this.editorial_types = {};
	this.mergeIntoEntSearch = null;
	
	this.initialize = function(){
		if (this.parent_obj_name != false) {
			this.name = this.parent_obj_name + '.' + this.obj_name;
		}
		else{
			this.name = this.obj_name;
		}
		if (this.dom_ids == null) {
			this.dom_ids = this.default_domids(this.value_num, 'default-ml');
		}
	}
	this.default_domids = function(value_num, suffix){
		var dom_ids = {
			del_label: (value_num + '-del-label-' + suffix),  //for delete editorial label
			del_note: (value_num + '-del-note-' + suffix),  //for delete editorial note
			del_class: (value_num + '-del-class-' + suffix),  //for delete editorial class_uri
			del_concon: (value_num + '-del-concon-' + suffix), //container ID for delete alert button
			del_confcon: (value_num + '-del-confcon-' + suffix), //container ID for delete alert button
			del_respncon: (value_num + '-del-respcon-' + suffix), //container ID for delete submission response
			del_infocon: (value_num + '-del-infocon-' + suffix), //container ID for delete info response
			del_mergecon: (value_num + '-del-mergecon-' + suffix), //containter ID for merge into interface
			del_mergeuuid: (value_num + '-del-mergeuuid-' + suffix), // input element for merge_into_uuid
			del_mergelabel: (value_num + '-del-mergelabel-' + suffix), // input element for merge_into_label
		}
		this.dom_ids = dom_ids;
		return dom_ids;
	}
	/*************************************************
	 * Functions to generate interface HTML
	 * ***********************************************
	 */
	this.deleteInterface = function(){
		var inter_dom = document.getElementById(this.modal_inter_dom_id);
		var title_dom = document.getElementById(this.modal_title_dom_id);
		title_dom.innerHTML = 'Delete "' + this.edit_type + '" item: ';
		title_dom.innerHTML += '<em>' + this.label + '</em> ?';
		var interface_html = this.make_interface_html();
		inter_dom.innerHTML = interface_html;
		var modal_id = "#" + this.modal_dom_id;
		$(modal_id).modal('show');
	}
	this.make_interface_html = function(){
		// make the HTML for the interface
		var note_placeholder = '(Optional) note regarding deletion of this item.';
		var merge_html = '';
		if (this.edit_type == 'subjects' || this.edit_type == 'media' || this.edit_type == 'documents') {
			merge_html = this.make_merge_into_interface_html();
		}
		var html = [
			'<div class="container-fluid">',
				'<div class="row">',
					'<div class="col-xs-8">',
						'<div class="form-group">',
							'<label for="' + this.dom_ids.del_note + '">',
							'Reason for Deletion</label>',
							'<textarea class="form-control" rows="3" ',
							'id="' + this.dom_ids.del_note + '" ',
							'placeholder="' + note_placeholder + '">',
							'</textarea>',
						'</div>',
					'</div>',
					'<div class="col-xs-4">',
						'<div style="margin-top:25px;" ',
					     'id="' + this.dom_ids.del_concon + '">',
							'<button class="btn btn-warning btn-sm" ',
							'',
							'onclick="' + this.name + '.deleteBeforeConfirm();">',
							'<span class="glyphicon glyphicon-remove-circle" aria-hidden="true"></span>',
							' Delete</button>',
						'</div>',
						'<div id="' + this.dom_ids.del_confcon + '">',
						'<small><em>Clicking "Delete" above will require confirmation</em></small>',
						'</div>',
						'<div id="' + this.dom_ids.del_respncon + '">',
						'</div>',
					'</div>',
				'</div>',
				'<div class="row">',
					'<div class="col-xs-12">',
						merge_html,
					'</div>',
				'</div>',
				'<div class="row">',
					'<div class="col-xs-12">',
						'<div style="margin-top:24px;">',
							'<h5><strong>About Deleting Records</strong></h5>',
							'<p class="small">Open Context organizes data by linking records together. ',
							'This means deleting a given record can impact other related records. ',
							'For this reason, deletion functions are only available to administrative ',
							'"super-users".',
							'</p>',
							'<p class="small"><em>Please delete records only ',
							'after careful consideration.</em><p>',
						'</div>',
					'</div>',
				'</div>',
			'</div>'
		].join('\n');
		return html;
	}
	
	this.make_merge_into_interface_html = function(){
		var button_html = [
			'<button title="Click to expand" role="button" ',
			'class="btn btn-default btn-xs" ',
			'onclick="'+ this.name + '.expandMergeInto();">',
			'<span class="glyphicon glyphicon-resize-vertical" aria-hidden="true">',
			'</span>',
			'</button>'
		].join('\n');
		var html =[
			'<div class="panel-group">',
				'<div class="panel panel-default" style="margin-top:4px;">',
					'<div class="panel-heading">',
						button_html,
						'(Optional) Merge this Item into Another',
					'</div>',
					'<div id="' +  this.dom_ids.del_mergecon + '" class="collapse" >',
						'<div class="panel-body">',
							'<div class="row">',
								'<div class="col-xs-5">',
									'<div class="form-group">',
										'<label for="' + this.dom_ids.del_mergelabel + '">',
										'Merge Label</label>',
										'<input id="' + this.dom_ids.del_mergelabel + '" ',
										'class="form-control input-sm" ',
										'type="text" value="" length="20" />',
									'</div>',
									'<div class="form-group">',
										'<label for="' + this.dom_ids.del_mergeuuid + '">',
										'Merge UUID</label>',
										'<input id="' + this.dom_ids.del_mergeuuid + '" ',
										'class="form-control input-sm" ',
										'type="text" value="" length="20" />',
									'</div>',
								'</div>',
								'<div class="col-xs-7">',
									this.make_merge_into_entity_search(),
								'</div>',
							'</div>',
							'<div class="row">',
								'<div class="col-xs-12 small" style="margin-top:20px;">',
								'<h5><strong>About Merging Prior to Deletion</strong></h5>',
								'Prior to deletion, you can merge this item: ' + this.label,
								' (' + this.edit_uuid + ') into another item ',
								'identified by the field "Merge UUID" above. ',
								'If you specify a Merge UUID, items linked to the item ',
								'you delete will be linked to the item identified by the ',
								'Merge UUID.',
								'</div>',
							'</div>',
						'</div>',
					'</div>',
				'</div>',
			'</div>',
		
		].join('\n');
		return html;
	}
	this.expandMergeInto = function(){
		$('#' + this.dom_ids.del_mergecon).on('shown.bs.collapse', function () {
			// triggered on shown
			// do nothing for now
		});
		$('#' + this.dom_ids.del_mergecon).collapse('toggle');
	}
	this.deleteBeforeConfirm = function(){
		// put some waiting notifications up
		var del_dom = document.getElementById(this.dom_ids.del_concon);
		del_dom.innerHTML = '';
		var conf_dom = document.getElementById(this.dom_ids.del_confcon);
		conf_dom.innerHTML = this.make_loading_gif('Checking deletion impacts...');
		// do an AJAX request to get info about deleting
		this.ajax_check_delete_item();
	}
	this.make_deleteConfirmInterface_html = function(impact_html){
		// create HTML interface to confirm deletion
		if (impact_html.length > 1) {
			impacts = '<div class="small" style="margin-bottom: 20px;">';
			impacts += '<p><strong>Impacts if you Delete</strong></p>';
			impacts += impact_html;
			impacts += '</div>';
		}
		else{
			impacts = '<div class="small" style="margin-bottom: 20px;">';
			impacts += '<p><strong>Impacts if you Delete</strong></p>';
			impacts += 'No other items will be affected.';
			impacts += '</div>';
		}
		var del_dom = document.getElementById(this.dom_ids.del_concon);
		del_dom.innerHTML = '';
		var conf_dom = document.getElementById(this.dom_ids.del_confcon);
		var html = [
			'<div class="alert alert-danger" role="alert">',
				impacts,
				'<p class="small" style="margin-bottom: 20px;">',
				'By clicking "Delete" below ',
				'you confirm you will delete this record</p>',
				'<div class="row">',
					'<div class="col-xs-6">',
						'<button class="btn btn-danger btn-sm" ',
						'',
						'onclick="' + this.name + '.deleteConfirm();">',
						'<span class="glyphicon glyphicon-remove-sign" ',
						'aria-hidden="true"></span>',
						' Delete</button>',
					'</div>',
					'<div class="col-xs-6">',
						'<button class="btn btn-default btn-sm" ',
						'',
						'onclick="' + this.name + '.deleteCancel();">',
						'Cancel</button>',
					'</div>',
				'</div>',
			'</div>'
		].join('\n');
		conf_dom.innerHTML = html;
	}
	this.deleteCancel = function(){
		// cancel the delete, close the window.
		var modal_id = "#" + this.modal_dom_id;
		$(modal_id).modal('hide');
	}
	this.deleteConfirm = function(){
		// onclick button function for confirming a delete
		var del_dom = document.getElementById(this.dom_ids.del_concon);
		del_dom.innerHTML = '';
		var conf_dom = document.getElementById(this.dom_ids.del_confcon);
		if (document.getElementById(this.dom_ids.del_mergeuuid)){
			var merge_into_uuid = document.getElementById(this.dom_ids.del_mergeuuid).value;
		}
		else{
			var merge_into_uuid = '';
		}
		if (merge_into_uuid.length < 1) {
			// no merge_into_uuid specified
			conf_dom.innerHTML = this.make_loading_gif('Deleting Item...');
		}
		else{
			// merge_into_uuid specified, so merging
			conf_dom.innerHTML = this.make_loading_gif('Merging then Deleting Item...');
		}
		
		// triggers the AJAX request for deletion sent to server
		this.ajax_delete();
	}
	this.make_merge_into_entity_search = function(){
		
		// make an entity search for items in the id field
		var entityInterfaceHTML = '';
		/* changes global authorSearchObj from entities/entities.js */
		var entSearchObj = new searchEntityObj();
		var ent_name = 'mergeIntoEntSearch';
		entSearchObj.name = ent_name;
		entSearchObj.ultra_compact_display = true;
		entSearchObj.parent_obj_name = this.name;
		entSearchObj.entities_panel_title = 'Search for an Item to Merge Into';
		entSearchObj.limit_item_type = this.edit_type;
		entSearchObj.limit_project_uuid = "0," + this.edit_project_uuid;
		var entDomID = entSearchObj.make_dom_name_id();
		var afterSelectDone = this.make_afterSelectDone_obj(entDomID);
		afterSelectDone.exec = function(){
			var sel_id = document.getElementById(this.entDomID + "-sel-entity-id").value;
			var sel_label = document.getElementById(this.entDomID +  "-sel-entity-label").value;
			document.getElementById(this.dom_ids.del_mergelabel).value = sel_label;
			document.getElementById(this.dom_ids.del_mergeuuid).value = sel_id;
		};
		entSearchObj.afterSelectDone = afterSelectDone;
		this.mergeIntoEntSearch = entSearchObj;
		var entityInterfaceHTML = entSearchObj.generateEntitiesInterface();
		return entityInterfaceHTML
	}
	this.make_afterSelectDone_obj = function(entDomID){
		// starts an object that will include a function to be executed
		// after a user has selected an item in the entity search object
		// result list
		var dom_ids = this.dom_ids
		var afterSelectDone = {
			dom_ids: dom_ids,
			entDomID: entDomID,
			name: this.name,
			exec: false
		}
		return afterSelectDone;
	}
	
	
	
	
	/*
	 * AJAX function to get information about a deletion's impacts
	 * and to actually execute the Deletion
	 */
	this.ajax_check_delete_item = function(){
		// Sends an AJAX request to get information about
		// the impact of a deletion
		var url = this.make_url("/edit/check-delete-item/");
		url += encodeURIComponent(this.edit_uuid); // the edit_uuid is the item_uuid in the manifest
		return $.ajax({
				type: "GET",
				url: url,
				dataType: "json",
				context: this,
				success: this.ajax_check_delete_itemDone,
				error: function (request, status, error) {
					alert('Getting info about delete impacts failed, sadly. Status: ' + request.status);
				} 
			});
	}
	this.ajax_check_delete_itemDone = function(data){
		// handle success of AJAX response to check delete impacts
		var impact_html = '';
		if (data.predicate_uses != null) {
			impact_html = 'This predicate helps describe: <strong>';
			impact_html += data.predicate_uses;
			impact_html += ' items</strong>';
		}
		if (data.type_uses != null) {
			impact_html = 'This controlled vocabulary type helps describe: <strong>';
			impact_html += data.type_uses;
			impact_html += ' items</strong>';
		}
		if (data.spatial_children != null) {
			impact_html = '<p>This item contains (in spatial/context relations): <strong>';
			impact_html += data.spatial_children;
			impact_html += ' items</strong></p>';
			if (data.default_merge_uuid != null && data.spatial_children > 0) {
				var link_url = this.make_url('/subjects/' + data.default_merge_uuid);
				impact_html += '<p>If deleted, the spatial/context contents of this ';
				impact_html += 'item will become the contents of ';
				impact_html += '<a target="_blank" href="' + link_url + '">';
				impact_html += '<span class="glyphicon glyphicon-new-window"></span> ';
				impact_html += data.default_merge_label;
				impact_html += '</a></p>';
			}
			
		}
		if (data.uniqely_linked_items != null) {
			if (data.uniqely_linked_items > 0) {
				impact_html += 'This item uniquely links to: <strong>';
				impact_html += data.uniqely_linked_items;
				impact_html += ' items</strong>';
			}
		}
		this.make_deleteConfirmInterface_html(impact_html);
	}
	this.ajax_delete = function(){
		// Sends an AJAX request to delete the item
		var note_dom = document.getElementById(this.dom_ids.del_note);
		if (document.getElementById(this.dom_ids.del_mergeuuid)){
			var merge_into_uuid = document.getElementById(this.dom_ids.del_mergeuuid).value;
		}
		else{
			var merge_into_uuid = '';
		}
		 
		var data = {
			edit_note: note_dom.value, // the note about the deletion
			merge_into_uuid: merge_into_uuid,
			csrfmiddlewaretoken: csrftoken};	
		var url = this.make_url("/edit/delete-item/");
		url += encodeURIComponent(this.edit_uuid); // the edit_uuid is the item_uuid in the manifest
		return $.ajax({
				type: "POST",
				url: url,
				dataType: "json",
				context: this,
				data: data,
				success: this.ajax_deleteDone,
				error: function (request, status, error) {
					alert('Item deletion failed, sadly. Status: ' + request.status);
				} 
			});
	}
	this.ajax_deleteDone = function(data){
		// delete item response
		var del_dom = document.getElementById(this.dom_ids.del_concon);
		del_dom.innerHTML = '';
		var conf_dom = document.getElementById(this.dom_ids.del_confcon);
		conf_dom.innerHTML = '';
		var resp_dom = document.getElementById(this.dom_ids.del_respncon);
		if (data.ok) {
			var icon_html = '<span class="glyphicon glyphicon-ok-circle" aria-hidden="true"></span>';
			var alert_class = 'alert alert-success';
			var message_html = '<p>' + icon_html + ' <strong>Note</strong><br/> ';
			message_html += data.change.note + '</p>';
			if (data.merge_into_uuid != null) {
				var merge_url = this.make_url('/' + data.merge_into_type + '/' + data.merge_into_uuid);
				if (data.user_specified_merge) {
					message_html += '<p>Successfully merged this record with: ';
				}
				else{
					message_html += '<p>Some relationships re-assigned to: ';
				}
				message_html += '<a href="' + merg_url + '">';
				message_html += data.merge_into_label + '</a></p>';
			}
			message_html += '<p><a href="' + this.make_url('/projects/' + data.project_uuid) + '">';
			message_html += 'Click Here to Continue Edits';
			message_html += '</a></p>';
		}
		else{
			var icon_html = '<span class="glyphicon glyphicon-warning-sign" aria-hidden="true"></span>';
			var alert_class = 'alert alert-warning';
			var message_html = '<p>' + icon_html + ' Problem(s) encountered deleting item: </p>';
			if (data.errors.length > 0) {
				message_html += '<ul>';
				for (var i = 0, length = data.errors.length; i < length; i++) {
					var error = data.errors[i];
					message_html += '<li>' + error + '</li>';
				}
				message_html += '</ul>';
			}
			else{
				message_html += '<p>' + data.changes.note + '</p>';
			}
		}
		var alert_html = [
				'<div role="alert" class="' + alert_class + '" >',
					message_html,
				'</div>'
			].join('\n');
		resp_dom.innerHTML = alert_html;
	}
	/*
	 * Supplemental Functions (used throughout)
	 */ 
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
	this.make_loading_gif = function(message){
		var src = this.make_url('/static/oc/images/ui/waiting.gif');
		var html = [
			'<div class="row">',
			'<div class="col-sm-1">',
			'<img alt="loading..." src="' + src + '" />',
			'</div>',
			'<div class="col-sm-11">',
			message,
			'</div>',
			'</div>'
			].join('\n');
		return html;
	}
}