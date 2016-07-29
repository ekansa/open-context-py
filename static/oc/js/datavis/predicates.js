/*
 * Graph data for a predicate item
 */
 
function predicate_bar_chart(json_url) {
	
	// Specify the chart area and dimensions
	var chart = d3.select(".chart");
	chart.bar_fill_color = false;
	chart.predicate_slug = "";
	chart.json_data = false;
	chart.base_url = "";
	chart.json_url = json_url.replace('&amp;', '&');
	chart.dom_id = "predicate-graph";
	chart.loading_dom_id = "predicate-graph-loading";
	chart.get_json = function (){
		/*
		*  Gets the JSON with graph data
		*/
		if (document.getElementById(this.loading_dom_id)) {
			// show the loading script
			var act_dom_id = this.loading_dom_id;
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
				chart.json_data = data;
				chart.convert_chart_data();
			}
		})
	}

	chart.convert_chart_data = function (){
		/*
		*  converts the data for use with D3,
		*  displays it
		*/
		if (document.getElementById(this.loading_dom_id)) {
			// show the loading script
			var act_dom_id = this.loading_dom_id;
			document.getElementById(act_dom_id).innerHTML ='';
		}
		
		var data = false;
		var active_facet = false;
		var active_options = false
		if ('oc-api:has-numeric-facets' in chart.json_data) {
			var facets = chart.json_data['oc-api:has-numeric-facets'];
		}
		else if ('oc-api:has-date-facets' in chart.json_data) {
			var facets = chart.json_data['oc-api:has-date-facets'];
		}
		else if ('oc-api:has-facets' in chart.json_data) {
			var facets = chart.json_data['oc-api:has-facets'];
		}
		else{
			var facets = false;
		}
		
		if (facets != false) {
			var check_id = "#facet-prop-" + chart.predicate_slug;
			for (var i = 0, length = facets.length; i < length; i++) {
				var facet = facets[i];
				if (facet.id == check_id) {
					// we found the facet for the current predicate
					active_facet = facet;
					if ('oc-api:has-range-options' in active_facet) {
						active_options = active_facet['oc-api:has-range-options'];
					}
					else if ('oc-api:has-id-options' in active_facet) {
						active_options = active_facet['oc-api:has-id-options'];
					}
				}
			}
		}
		if (active_options != false) {
			data = {'labels': [],
			        'urls': [],
			        'series': [{'label': 'Values',
					    'values': []}]};
			for (var i = 0, length = active_options.length; i < length; i++) {
				var opt = active_options[i];
				var url = removeURLParameter(opt.id, 'response');
				data.urls.push(url);
				data.labels.push(opt.label);
				data.series[0].values.push(opt.count);
			}
			chart.chart_data(data);
		}
	}
	
	chart.chart_data = function(data){
		    
		// Zip the series data together (first values, second values, etc.)
		var zippedData = [];
		for (var i=0; i<data.labels.length; i++) {
			for (var j=0; j<data.series.length; j++) {
				zippedData.push(data.series[j].values[i]);
			}
		}
		
		var 	chartWidth       = 300,
			barHeight        = 20,
			groupHeight      = barHeight * data.series.length,
			gapBetweenGroups = 10,
			spaceForLabels   = 175,
			spaceForLegend   = 125;
		    
		if (document.getElementById(this.dom_id)) {
			// resize the chart to current window size
			var act_dom_id = this.dom_id;
			var chart_dom = document.getElementById(act_dom_id);
			chartWidth = $(chart_dom).width()-200;
		}
		
		// Color scale
		var color = d3.scale.category20();
		var chartHeight = barHeight * zippedData.length + gapBetweenGroups * data.labels.length;
		
		console.log(color);
		
		var x = d3.scale.linear()
			  .domain([0, d3.max(zippedData)])
			  .range([0, chartWidth]);
		    
		var y = d3.scale.linear()
			  .range([chartHeight + gapBetweenGroups, 0]);
		    
		var yAxis = d3.svg.axis()
			      .scale(y)
			      .tickFormat('')
			      .tickSize(0)
			      .orient("left");
		    
		// Specify the chart area and dimensions
		chart.attr("width", spaceForLabels + chartWidth + spaceForLegend);
		chart.attr("height", chartHeight);
		    
		    // Create bars
		    var bar = chart.selectAll("g")
			.data(zippedData)
			.enter().append("g")
			.attr("transform", function(d, i) {
			  return "translate(" + spaceForLabels + "," + (i * barHeight + gapBetweenGroups * (0.5 + Math.floor(i/data.series.length))) + ")";
			});
		    
		    // Create rectangles of the correct width
		    bar.append("rect")
			.attr("fill", function(d,i) { return color(i % data.series.length); })
			.attr("class", "bar")
			.attr("width", x)
			.attr("height", barHeight - 1);
		    
		    // Add text label in bar
		    bar.append("text")
			.attr("x", function(d) { return x(d) - 3; })
			.attr("y", barHeight / 2)
			.attr("fill", "red")
			.attr("dy", ".35em")
			.text(function(d) { return d; })
			.style("opacity", function(d) {
				var op = 1;
				var ds = d + '';
				if (x(d) < ds.length * 8) {
					// hide if not enough space to show
					// label
					op = 0;
				}
				return op;
			});
		    
		    // Draw labels
		    bar.append("text")
			.attr("class", "label")
			.attr("x", function(d) { return - 10; })
			.attr("y", groupHeight / 2)
			.attr("dy", ".30em")
			.text(function(d,i) {
				var label = "";
				if (i % data.series.length === 0){
					label = data.labels[Math.floor(i/data.series.length)];
					if (label.length > 25) {
						label = label.substring(0, 22) + '...';
					}
				}
				return label;
			});
			
		
		    bar.on("click", function (d,i){
			if (i % data.series.length === 0){
				var url = data.urls[Math.floor(i/data.series.length)];
				window.location = url;
			}
		    });
		    
			
			chart.append("g")
			  .attr("class", "y axis")
			  .attr("transform", "translate(" + spaceForLabels + ", " + -gapBetweenGroups/2 + ")")
			  .call(yAxis);
		    
	}
	
	this.chart = chart;
}
