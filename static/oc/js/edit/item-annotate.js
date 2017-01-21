
var uriSearchObj = false;  // for searching for objects of identifiers
var uriAddObj = false; // for adding new entities to use for linked data annotations

function showAnnotateItemInterface(type){
	/* shows an interface for annotating an item
	 * 
	*/
	var main_modal_title_domID = "myModalLabel";
	var main_modal_body_domID = "myModalBody";
	var title_dom = document.getElementById(main_modal_title_domID);
	var body_dom = document.getElementById(main_modal_body_domID);
	var actInterface = new annotateItemInterface(type);
	title_dom.innerHTML = actInterface.title;
	body_dom.innerHTML = actInterface.body;
	$("#myModal").modal('show');
}

function annotateItemInterface(type){
	if (type == 'author') {
		//make an interface for adding dc-terms:creator or dc-terms:contributor persons
		this.title = '<i class="fa fa-users"></i>';
		this.title += ' Add Contributor and Creator (Authorship) Information';
		this.body = annotate_author_body();
	}
	else if (type == 'stableID') {
		//make an interface for adding stable identifiers
		this.title = '<i class="fa fa-university"></i>';
		this.title += ' Add a Stable / Persistent Identifier';
		this.body = annotate_stableID_body();
	}
	else if (type == 'dc') {
		//make an interface for adding stable identifiers
		this.title = '<i class="fa fa-tags"></i>';
		this.title += ' Add a Dublin Core Annotation (not author related) ';
		this.body = annotate_dc_body();
	}
	else if (type == 'vocab') {
		//make an interface for adding stable identifiers
		this.title = '<i class="fa fa-share-alt"></i>';
		this.title += ' Relate to a Controlled Vocabulary or Ontology ';
		this.body = annotate_vocab_body();
	}
}

function annotate_author_body(){
	
	var entityInterfaceHTML = "";
	/* changes global authorSearchObj from entities/entities.js */
	authorSearchObj = new searchEntityObj();
	authorSearchObj.name = "authorSearchObj";
	authorSearchObj.entities_panel_title = "Select Author or Editor";
	authorSearchObj.limit_item_type = "persons";
	authorSearchObj.limit_project_uuid = "0," + project_uuid;
	var afterSelectDone = {
		exec: function(){
				return authorObject();
			}
		};
	authorSearchObj.afterSelectDone = afterSelectDone;
	var entityInterfaceHTML = authorSearchObj.generateEntitiesInterface();
	console.log(authorSearchObj);
	
	var html = [
	'<div>',
	'<div class="row">',
	'<div class="col-xs-6">',
	'<label>Role / Relationship</label><br/>',
	'<label class="radio-inline">',
	'<input type="radio" name="pred-uri" id="new-anno-pred-uri-dc-contrib" ',
	'class="new-item-pred-uri" value="dc-terms:contributor" checked="checked">',
	'Contributor </label>',
	'<label class="radio-inline">',
	'<input type="radio" name="pred-uri" id="new-anno-pred-uri-dc-creator" ',
	'class="new-item-pred-uri" value="dc-terms:creator">',
	'Creator </label><br/><br/>',
	'<div class="form-group">',
	'<label for="new-anno-object-id">Person / Org. (Object ID)</label>',
	'<input id="new-anno-object-id" class="form-control input-sm"',
	'type="text" value="" />',
	'</div>',
	'<div class="form-group" id="new-anno-object-label-out">',
	'<label for="new-anno-object-label">Person / Org. (Object Label)</label>',
	'<input id="new-anno-object-label" class="form-control input-sm"',
	'type="text" disabled="disabled" value="Completed upon lookup to the right" />',
	'</div>',
	'<div class="form-group">',
	'<label for="new-anno-sort">Rank / Sort Order (0 = Unsorted)</label>',
	'<input id="new-anno-sort" class="form-control input-sm" style="width:20%;"',
	'type="text" value="0" />',
	'</div>',
	'<div class="form-group">',
	'<label for="new-anno-sort">Add Authorship Relation</label>',
	'<button class="btn btn-primary" onclick="addAuthorAnnotation();">Submit</button>',
	'</div>',
	'</div>',
	'<div class="col-xs-6">',
	entityInterfaceHTML,
	'</div>',
	'</div>',
	'<div class="row">',
	'<div class="col-xs-12">',
	'<small>Use <strong>contributor</strong> for persons or organizations with an overall secondary ',
	'role in making the content. Use <strong>creator</strong> for persons or organizations that ',
	'played more leading roles as directors, principle investigators or editors.',
	'<small>',
	'</div>',
	'</div>',
	'</div>'
	].join('\n');
	return html;
}

function authorObject(){
	// puts the selected item from the entity lookup interface
	// into the appropriate field for making a new assertion
	var obj_id = document.getElementById("authorSearchObj-sel-entity-id").value;
	var obj_label = document.getElementById("authorSearchObj-sel-entity-label").value;
	document.getElementById("new-anno-object-id").value = obj_id;
	//so we can edit disabled state fields
	var l_outer = document.getElementById("new-anno-object-label-out");
	var html = [
	'<label for="new-anno-object-label">Person / Org. (Object Label)</label>',
	'<input id="new-anno-object-label" class="form-control input-sm"',
	'type="text" disabled="disabled" value="' + obj_label + '" />'
	].join('\n');
	l_outer.innerHTML = html;
}

function addAuthorAnnotation(){
	//submits the new author annotation information
	var obj_id = document.getElementById("new-anno-object-id").value;
	if (obj_id.length > 0) {
		var sort_val = document.getElementById("new-anno-sort").value;
		var p_types = document.getElementsByClassName("new-item-pred-uri");
		for (var i = 0, length = p_types.length; i < length; i++) {
			if (p_types[i].checked) {
				var pred_uri = p_types[i].value;
			}
		}
		var url = "../../edit/add-item-annotation/" + encodeURIComponent(uuid);
		var req = $.ajax({
			type: "POST",
			url: url,
			dataType: "json",
			data: {
				sort: sort_val,
				predicate_uri: pred_uri,
				object_uri: obj_id,
				csrfmiddlewaretoken: csrftoken},
			success: addAuthorAnnotationDone
		});
	}
	else{
		alert("Need to select an author / editor first.");
	}
}

function addAuthorAnnotationDone(data){
	// reload the whole page from the server
	// it's too complicated to change all the instances of the item label on the page,
	// easier just to reload the whole page
	console.log(data);
	location.reload(true);
}

function annotate_stableID_body(){
	var html = [
	'<div>',
	'<div class="row">',
	'<div class="col-xs-8">',
	'<label>Stable ID Type</label><br/>',
	'<label class="radio-inline">',
	'<input type="radio" name="stable-id-type" id="stable-id-type-doi" ',
	'class="stable-id-type" value="doi" checked="checked" />',
	'DOI </label>',
	'<label class="radio-inline">',
	'<input type="radio" name="stable-id-type" id="stable-id-type-ark" ',
	'class="stable-id-type" value="ark" />',
	'ARK </label>',
	'<label class="radio-inline">',
	'<input type="radio" name="stable-id-type" id="stable-id-type-orcid" ',
	'class="stable-id-type" value="orcid" />',
	'ORCID </label><br/><br/>',
	'<div class="form-group">',
	'<label for="new-anno-object-id">Identifier</label>',
	'<input id="new-anno-object-id" class="form-control input-sm"',
	'type="text" value="" />',
	'</div>',
	'<div class="form-group">',
	'<label for="new-anno-sort">Add Identifier</label>',
	'<button class="btn btn-primary" onclick="addStableId();">Submit</button>',
	'</div>',
	'</div>',
	'<div class="col-xs-4">',
	'<h4>Notes on Stable Identifiers</h4>',
	'<p><small>Manually enter a stable / persistent identifier curated ',
	'by an external identifier service. Use EZID for items published by Open Context. ',
	'Use ORCID to identify persons.',
	'</small></p>',
	'</div>',
	'</div>',
	'</div>'
	].join('\n');
	return html;
}

function addStableId(){
	//submits the new stable identifier information
	var stable_id = document.getElementById("new-anno-object-id").value;
	if (stable_id.length > 0) {
		var id_types = document.getElementsByClassName("stable-id-type");
		for (var i = 0, length = id_types.length; i < length; i++) {
			if (id_types[i].checked) {
				var stable_type = id_types[i].value;
			}
		}
		var url = "../../edit/add-item-stable-id/" + encodeURIComponent(uuid);
		var req = $.ajax({
			type: "POST",
			url: url,
			dataType: "json",
			data: {
				stable_type: stable_type,
				stable_id: stable_id,
				csrfmiddlewaretoken: csrftoken},
			success: addStableIdDone
		});
	}
	else{
		alert("Need to add the identifier first.");
	}
}

function addStableIdDone(data){
	console.log(data);
	location.reload(true);
}

function annotate_dc_body(){
	
	var entityInterfaceHTML = "";
	/* changes global authorSearchObj from entities/entities.js */
	uriSearchObj = new searchEntityObj();
	uriSearchObj.name = "uriSearchObj";
	uriSearchObj.entities_panel_title = "Find a URI identified Object";
	uriSearchObj.limit_item_type = "uri";
	uriSearchObj.ent_type = 'class';
	uriSearchObj.show_type = true;
	uriSearchObj.show_partof = true;
	var afterSelectDone = {
		exec: function(){
				return entityObject();
			}
		};
	uriSearchObj.afterSelectDone = afterSelectDone;
	var entityInterfaceHTML = uriSearchObj.generateEntitiesInterface();
	
	var newEntityInterfaceHTML = "";
	// make a panel for adding new entities
	uriAddObj = new addEntityObj();
	uriAddObj.name = "uriAddObj";
	newEntityInterfaceHTML = uriAddObj.generateInterface();
	
	var html = [
	'<div>',
	'<div class="row">',
	'<div class="col-xs-6">',
	'<label>Dublin Core Predicate (Property)</label><br/>',
	'<ul class="list-unstyled">',
	'<li>',
	'<input type="radio" name="pred_uri" id="pred_uri-1" ',
	'class="pred_uri" value="dc-terms:subject" />',
	'Subject</li>',
	'<li>',
	'<input type="radio" name="pred_uri" id="pred_uri-2" ',
	'class="pred_uri" value="dc-terms:coverage" />',
	'Coverage (Unspecified Geographic/Time)</li>',
	'<li>',
	'<input type="radio" name="pred_uri" id="pred_uri-3" ',
	'class="pred_uri" value="dc-terms:spatial" />',
	'Spatial Coverage (Geographic)</li>',
	'<li>',
	'<input type="radio" name="pred_uri" id="pred_uri-4" ',
	'class="pred_uri" value="dc-terms:temporal" />',
	'Temporal (Time Period)</li>',
	'<li>',
	'<input type="radio" name="pred_uri" id="pred_uri-5" ',
	'class="pred_uri" value="dc-terms:references" />',
	'References (Cites/references another source)</li>',
	'<li>',
	'<input type="radio" name="pred_uri" id="pred_uri-6" ',
	'class="pred_uri" value="dc-terms:replaces" />',
	'Replaces (replaces, supercedes another resource)</li>',
	'<li>',
	'<input type="radio" name="pred_uri" id="pred_uri-7" ',
	'class="pred_uri" value="dc-terms:isReplacedBy" />',
	'Is Replaced by (is superceded by another resource)</li>',
	'<li>',
	'<input type="radio" name="pred_uri" id="pred_uri-8" ',
	'class="pred_uri" value="dc-terms:isReferencedBy" />',
	'Is referenced by (Is cited by another source)</li>',
	'<li>',
	'<input type="radio" name="pred_uri" id="pred_uri-9" ',
	'class="pred_uri" value="dc-terms:license" />',
	'Has Copyright License</li>',
	'</ul>',
	'<div class="form-group">',
	'<label for="new-anno-object-id">Object URI</label>',
	'<input id="new-anno-object-id" class="form-control input-sm"',
	'type="text" value="" />',
	'</div>',
	'<div class="form-group" id="new-anno-object-label-out">',
	'<label for="new-anno-object-label">Object Label</label>',
	'<input id="new-anno-object-label" class="form-control input-sm"',
	'type="text" disabled="disabled" value="Completed upon lookup to the right" />',
	'</div>',
	'<div class="form-group">',
	'<label for="new-anno-sort">Add Annotation</label>',
	'<button class="btn btn-primary" onclick="addDC();">Submit</button>',
	'</div>',
	'<div id="annotation-results">',
	'</div>',
	'</div>',
	'<div class="col-xs-6">',
	entityInterfaceHTML,
	newEntityInterfaceHTML,
	'</div>',
	'</div>',
	'<div class="row">',
	'<div class="col-xs-12">',
	'<h4>Notes on Dublin Core Properties</h4>',
	'<p><small>Use this interface to add additional metadata properties ',
	'to items using the Dublin Core Terms vocabulary. These properties help to ',
	'add more digital library / scholarly context to Open Context items.',
	'</small></p>',
	'</div>',
	'</div>',
	'</div>',
	'</div>',
	'</div>'
	].join('\n');
	return html;
}

function entityObject(){
	// puts the selected item from the entity lookup interface
	// into the appropriate field for making a new assertion
	var obj_id = document.getElementById("uriSearchObj-sel-entity-id").value;
	var obj_label = document.getElementById("uriSearchObj-sel-entity-label").value;
	document.getElementById("new-anno-object-id").value = obj_id;
	//so we can edit disabled state fields
	var l_outer = document.getElementById("new-anno-object-label-out");
	var html = [
	'<label for="new-anno-object-label">URI item label</label>',
	'<input id="new-anno-object-label" class="form-control input-sm"',
	'type="text" disabled="disabled" value="' + obj_label + '" />'
	].join('\n');
	l_outer.innerHTML = html;
}

function addDC(){
	
	var obj_uri = document.getElementById("new-anno-object-id").value;
	if (obj_uri.length > 0) {
		var pred_uri = false;
		var p_types = document.getElementsByClassName("pred_uri");
		for (var i = 0, length = p_types.length; i < length; i++) {
			if (p_types[i].checked) {
				pred_uri = p_types[i].value;
			}
		}
		if (pred_uri != false) {
			// code to execute the annotation creation, load the annotations
			// via calling the act_annotations object defined in item_edit.js
			exec_addDC(pred_uri, obj_uri).then(
			function() {
				act_annotations = new entityAnnotationsObj();
				act_annotations.name = 'act_annotations';
				act_annotations.entity_id = uuid;
				act_annotations.getAnnotations();
			}
			);
		}
		else{
			alert("Select Dublin Core property to use first.");
		}
	}
	else{
		alert("Need to select a URI for the object of this annotation.");
	}
}

function exec_addDC(pred_uri, obj_uri){
	var url = "../../edit/add-item-annotation/" + encodeURIComponent(uuid);
	return $.ajax({
			type: "POST",
			url: url,
			dataType: "json",
			data: {
				sort: 0,
				predicate_uri: pred_uri,
				object_uri: obj_uri,
				csrfmiddlewaretoken: csrftoken},
			success: addAnnotationDone
		});
}
function addAnnotationDone(data){
	var mes_dom = document.getElementById("annotation-results");
		if (data.ok) {
			// the interaction was a success
			var html = '<div class="alert alert-success" role="alert">';
			html += '<span class="glyphicon glyphicon-ok-sign" aria-hidden="true"></span>';
			html += ' Annotation successfully added.';
			if (data.change.note.length > 0) {
				html += '<br/>' + data.change.note;
			}
			html += '</div>';
		}
		else{
			var html = '<div class="alert alert-warning" role="alert">';
			html += '<span class="glyphicon glyphicon-warning-sign" aria-hidden="true"></span>';
			html += ' We found a problem adding the annotation.';
			html += '<br/><p class="small"><strong>Note:</strong> ' + data.change.note + '</p>';
			html += '</div>';
		}
		mes_dom.innerHTML = html;
}

function annotate_vocab_body(){
	
	var entityInterfaceHTML = "";
	/* changes global authorSearchObj from entities/entities.js */
	uriSearchObj = new searchEntityObj();
	uriSearchObj.name = "uriSearchObj";
	uriSearchObj.entities_panel_title = "Find a URI identified Object";
	uriSearchObj.limit_item_type = "uri";
	uriSearchObj.ent_type = 'class';
	uriSearchObj.show_type = true;
	uriSearchObj.show_partof = true;
	var afterSelectDone = {
		exec: function(){
				return entityObject();
			}
		};
	uriSearchObj.afterSelectDone = afterSelectDone;
	var entityInterfaceHTML = uriSearchObj.generateEntitiesInterface();
	
	var newEntityInterfaceHTML = "";
	// make a panel for adding new entities
	uriAddObj = new addEntityObj();
	uriAddObj.name = "uriAddObj";
	newEntityInterfaceHTML = uriAddObj.generateInterface();
	
	var html = [
	'<div>',
	'<div class="row">',
	'<div class="col-xs-6">',
	'<label>Relationship Property</label><br/>',
	'<ul class="list-unstyled">',
	'<li>',
	'<input type="radio" name="pred_uri" id="pred_uri-1" ',
	'class="pred_uri" value="skos:closeMatch" checked="checked"/>',
	'Close Match (skos:closeMatch)</li>',
	'<li>',
	'<input type="radio" name="pred_uri" id="pred_uri-2" ',
	'class="pred_uri" value="skos:exactMatch" />',
	'Exact Match (skos:exactMatch)</li>',
	'<li>',
	'<input type="radio" name="pred_uri" id="pred_uri-3" ',
	'class="pred_uri" value="owl:sameAs" />',
	'Same as, or has alternate URI (owl:sameAs)</li>',
	'<li>',
	'<input type="radio" name="pred_uri" id="pred_uri-4" ',
	'class="pred_uri" value="skos:broader" />',
	'In a broader classification (skos:broader)</li>',
	'<li>',
	'<input type="radio" name="pred_uri" id="pred_uri-5" ',
	'class="pred_uri" value="skos:related" />',
	'Has related concept (skos:related)</li>',
	'<li>',
	'<input type="radio" name="pred_uri" id="pred_uri-6" ',
	'class="pred_uri" value="rdfs:isDefinedBy" />',
	'Is defined by (rdfs:isDefinedBy)</li>',
	'<li>',
	'<input type="radio" name="pred_uri" id="pred_uri-7" ',
	'class="pred_uri" value="http://www.w3.org/2000/01/rdf-schema#range" />',
	'Has range (rdfs:range, for units of measurement)</li>',
	'</ul>',
	'<div class="form-group">',
	'<label for="new-anno-object-id">Object URI</label>',
	'<input id="new-anno-object-id" class="form-control input-sm"',
	'type="text" value="" />',
	'</div>',
	'<div class="form-group" id="new-anno-object-label-out">',
	'<label for="new-anno-object-label">Object Label</label>',
	'<input id="new-anno-object-label" class="form-control input-sm"',
	'type="text" disabled="disabled" value="Completed upon lookup to the right" />',
	'</div>',
	'<div class="form-group">',
	'<label for="new-anno-sort">Add Annotation</label>',
	'<button class="btn btn-primary" onclick="addDC();">Submit</button>',
	'</div>',
	'<div id="annotation-results">',
	'</div>',
	'</div>',
	'<div class="col-xs-6">',
	entityInterfaceHTML,
	newEntityInterfaceHTML,
	'</div>',
	'</div>',
	'<div class="row">',
	'<div class="col-xs-12">',
	'<h4>Notes on Vocabulary Mapping</h4>',
	'<p><small>One should generally use the "Close Match" (SKOS:closeMatch) ',
	'property to relate to an external controlled vocabulary or ontology. Use ',
	'"Exact Match" (SKOS:exactMatch) when the concepts fully interchangable. ',
	'"Same As" (OWL:sameAs) should only be used to indicate another URI for this ',
	'same resource. Finally, you should use "Is Defined By" (RDFS:isDefinedBy) to reference another ',
	'URI that has a definition (such as a Wikipedia page) for this concept.',
	'</small></p>',
	'</div>',
	'</div>',
	'</div>',
	'</div>',
	'</div>'
	].join('\n');
	return html;
}