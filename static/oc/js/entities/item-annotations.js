/*
 * ------------------------------------------------------------------
	AJAX for entity annotations
 * ------------------------------------------------------------------
*/

function entityAnnotationsObj() {
	/* Object for composing search entities */
	this.name = "item-annotations"; //object name, used for DOM-ID prefixes and object labeling
	this.suffix_dom_id = "-ld-rows";
	this.url = "../../entities/annotations/";
	this.entity_id = false;
	this.getAnnotations = function(){
		var url = this.url + encodeURIComponent(this.entity_id);
		this.req = $.ajax({
			type: "GET",
			url: url,
			dataType: "json",
			data: data,
			context: this,
			success: this.getAnnotationsDone
		});
	}
	this.getAnnotationsDone = function(data){
		/* Displays the annotations to an item */
		var resultDom = document.getElementById(this.name + "-" + this.suffix_dom_id);
		resultDom.innerHTML = "";
		for (var i = 0, length = data.preds_objs.length; i < length; i++) {
			// to do, add HTML output for predicates, then objects
		}
	}
	this.displayPredicateObjects = function(objects){
		// display list of objects for a given predicate
		var html = "";
		return html;
	}
	this.deleteAnnotation = function(hash_id){
		/* Sends a request to delete an annotation by the hash-id */
	}
}


