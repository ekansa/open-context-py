/*
 * Graph data for a predicate item
 */
 
function predicate_bar_chart(chart_dom_id, json_url) {
	
	this.base_url = "";
	this.title_dom_id = "";
	this.chart_dom_id = chart_dom_id;
	this.json_url = json_url; // base url for geo-json requests
	this.json_url = this.json_url.replace('&amp;', '&');
	
	this.json_data = false;
	this.get_json = function (){
		/*
		*  Gets the JSON with graph data
		*/
		if (document.getElementById(this.chart_dom_id)) {
			// show the loading script
			var act_dom_id = this.chart_dom_id;
			var loading = "<img style=\"margin-top:-4px;\" height=\"16\"  src=\"";
			loading += this.base_url + "/static/oc/images/ui/waiting.gif\" alt=\"Loading icon...\" />";
			loading += " Loading Graph Data...";
			document.getElementById(act_dom_id).innerHTML =loading;
		}
		//do the ajax request
		$.ajax({
			type: "GET",
			url: this.json_url,
			dataType: "json",
			data: {response: "metadata,facet"},
			success: function(data) {
				this.json_data = data;
				this.chart_data();
			}
		})
	}

	this.chart_data = function (){
		alert('OK!');
	}
}
