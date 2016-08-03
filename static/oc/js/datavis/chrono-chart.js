/*
 * Testing stacked area chart for chronological facets
 * with data from the API service
 */

function chrono_chart(chart_dom_id, json_url) {
	
	this.ctx = document.getElementById(chart_dom_id);
	this.json_url = json_url; // base url for geo-json requests
	this.json_url = this.json_url.replace('&amp;', '&');
	this.json_url = this.json_url.replace('response=geo-facet', 'response=chrono');
	this.json_data = null;
	this.chart = null;
	this.initialize = function(){
		this.get_api_data();
	}
	this.get_api_data = function(){
		var url = this.json_url;
		var params = {};
		return $.ajax({
			type: "GET",
			url: url,
			data: params,
			dataType: "json",
			headers: {
				//added to get JSON data (content negotiation)
				Accept : "application/json; charset=utf-8"
			},
			context: this,
			success: this.get_api_dataDone, //do this when we get data w/o problems
			error: this.get_api_dataError //error message display
		});
	}
	this.get_api_dataDone = function(data){
		this.json_data = data;
		this.make_chart();
	}
	this.get_api_dataError = function(){
		
	}
	this.get_chart_datasets = function(){
		var datasets = null;
		if (this.json_data != null) {
			if ('oc-api:has-form-use-life-ranges' in this.json_data) {
				// we have time span facets
				var chrono_facets = this.json_data['oc-api:has-form-use-life-ranges'];
				datasets = this.make_chart_datasets(chrono_facets);
			}
		}
		return datasets;
	}
	this.make_chart_datasets = function(chrono_facets){
		// first sort the time spans into reverse order, so the biggest are best
		var list = {};
		var chrono_objs = {};
		for (var i = 0, length = chrono_facets.length; i < length; i++) {
			var chrono = chrono_facets[i];
			var id = chrono.id;
			var t_span = parseFloat(chrono['stop']) - parseFloat(chrono['start']);
			list[id] = t_span;
			chrono_objs[id] = chrono;
		}
		// now sort the keys, reverse order 
		var	keys_sorted = Object.keys(list).sort(function(a,b){return list[a]-list[b]});
		keys_sorted.reverse();
		console.log(keys_sorted);
		
		// datasets
		var datasets = [];
		for (var i = 0, length = keys_sorted.length; i < length; i++) {
			var key = keys_sorted[i];
			var chrono = chrono_objs[key];
			var t_span = list[key];
			var c_per_year = chrono.count / t_span;
			var dataset = this.make_dataset();
			dataset.label = chrono['start'] + ' to ' + chrono['stop'];
			dataset.data = this.make_data_points(c_per_year, chrono);
			datasets.push(dataset);
		} 
		
		return datasets;
	}
	this.make_data_points = function(c_per_year, chrono){
		var data_list = [];
		var start = parseFloat(chrono['start']);
		var end = parseFloat(chrono['stop']);
		var t_span = end - start;
		var increment = t_span / 20;
		for (var i = start; i <= end; i += increment) {
			var data_point = {
				x: i,
			    y: c_per_year};
			data_list.push(data_point);
		}
		if (i < end) {
			var data_point = {
				x: i,
			    y: c_per_year};
			data_list.push(data_point);
		}
		return data_list;
	}
	
	this.make_dataset = function(){
		var dataset = {
			label: '',
			url: '',
			data: [],
			backgroundColor: "rgba(75,192,192,0.4)",
            borderColor: "rgba(75,192,192,1)",
			pointRadius: 0,
			spanGaps: true
		}
		return dataset;
	}
	this.make_chart = function(){
		var datasets = this.get_chart_datasets();
		var act_chart = new Chart(this.ctx,
		{
			type: 'line',
			responsive: true,
			data: {
				datasets: datasets,
			},
			options: {
				legend: {
					display: false,
				},
				scales: {
					yAxes: [{
						stacked: true
					}],
					xAxes: [{
						type: 'linear',
						position: 'top',
						ticks: {
							max: 2050,
						}
					}]
				}
			},
		});
		this.chart = act_chart;	
	}
}
