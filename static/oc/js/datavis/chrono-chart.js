/*
 * Testing stacked area chart for chronological facets
 * with data from the API service
 */

function chrono_chart(chart_dom_id, json_url) {
	
	this.ctx = document.getElementById(chart_dom_id);
	this.json_url = json_url; // base url for geo-json requests
	this.json_url = this.json_url.replace('&amp;', '&');
	this.json_url = this.json_url.replace('response=geo-facet', 'response=chrono');
	this.area_color_list = [
		'#166CA5',
		'#1383C4',
		// '#FFFF66',
		'#B22A29'
	]; // list of colors for gradients
	this.line_color_list = [
		'#166CA5',
		'#1383C4',
		// '#FFFF00',
		'#B22A00'
	]; // list of colors for gradients
	
	this.current_y_at_x = {};
	this.curent_year_keys = [];
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
		var total_count = 0;
		var max_count = 0;
		var max_c_per_year = 0;
		var all_min_year = null;
		var all_max_year = null;
		for (var i = 0, length = chrono_facets.length; i < length; i++) {
			var chrono = chrono_facets[i];
			var id = chrono.id;
			total_count += chrono.count;
			if (chrono.count > max_count) {
				max_count = chrono.count;
			}
			var t_span = parseFloat(chrono['stop']) - parseFloat(chrono['start']);
			var c_per_year = chrono.count / t_span;
			if (all_min_year == null) {
				all_min_year = parseFloat(chrono['start']);
			}
			else{
				if (all_min_year > parseFloat(chrono['start'])) {
					all_min_year = parseFloat(chrono['start']);
				}
			}
			if (all_max_year == null) {
				all_max_year = parseFloat(chrono['stop']);
			}
			else{
				if (all_max_year < parseFloat(chrono['stop'])) {
					all_max_year = parseFloat(chrono['stop']);
				}
			}
			if (c_per_year > max_c_per_year) {
				max_c_per_year = c_per_year;
			}
			list[id] = t_span;
			chrono_objs[id] = chrono;
		}
		// now sort the keys, reverse order 
		var	keys_sorted = Object.keys(list).sort(function(a,b){return list[a]-list[b]});
		keys_sorted.reverse();
		// keys_sorted.sort();
		console.log(keys_sorted);
		
		// datasets
		var datasets = [];
		this.make_current_y_at_x(all_min_year, all_max_year);
		for (var i = 0, length = keys_sorted.length; i < length; i++) {
			var key = keys_sorted[i];
			var chrono = chrono_objs[key];
			var t_span = list[key];
			var c_per_year = chrono.count / t_span;
			var dataset = this.make_dataset();
			var style_obj = new numericStyle();
			style_obj.reset_gradient_colors(this.area_color_list);
			style_obj.min_value = 0;
			style_obj.max_value = max_count;
			style_obj.act_value = chrono.count;
			//style_obj.max_value = max_c_per_year;
			//style_obj.act_value = c_per_year;
			var hex_color = style_obj.generate_hex_color();
			
			var l_style_obj = new numericStyle();
			l_style_obj.reset_gradient_colors(this.line_color_list);
			l_style_obj.min_value = 0;
			l_style_obj.max_value = max_count;
			l_style_obj.act_value = chrono.count;
			
			//l_style_obj.max_value = max_c_per_year;
			//l_style_obj.act_value = c_per_year;
			var l_hex_color = l_style_obj.generate_hex_color();
			
			var prop_max_c_per_year = (c_per_year / max_c_per_year) * 100;
			if (prop_max_c_per_year < .05) {
				// prop_max_c_per_year = .05;
			}
			// prop_max_c_per_year = prop_max_c_per_year + (max_c_per_year * .1);
			
			var b_gradient = this.make_grandient_object(hex_color);
			var l_gradient = this.make_grandient_object(l_hex_color);
			
			// dataset.backgroundColor = hex_color;
			dataset.backgroundColor = b_gradient;
			// dataset.borderColor = l_hex_color;
			dataset.borderColor = l_gradient;
			dataset.borderStrokeColor = "#fff";
			dataset.label = chrono['start'] + ' to ' + chrono['stop'];
			dataset.data = this.make_data_points(prop_max_c_per_year,
												 chrono);
			datasets.push(dataset);
		} 
		
		return datasets;
	}
	this.make_grandient_object = function(hex_color){
		// makes a gradient object for a color hex string
		var chart = this.ctx.getContext('2d');
		var gradient = chart.createLinearGradient(0, 0, 0, 400);
		var rgba_background = convertToRGB(hex_color);
		var rgba_str_0 = 'rgba(' + rgba_background.join(', ') + ', 1)';
		var rgba_str_1 = 'rgba(' + rgba_background.join(', ') + ', .5)';
		var rgba_str_2 = 'rgba(' + rgba_background.join(', ') + ', .15)';
		gradient.addColorStop(.15, rgba_str_0);   
		gradient.addColorStop(.5, rgba_str_1);
		gradient.addColorStop(1, rgba_str_2);
		return gradient;
	}
	this.make_current_y_at_x = function(all_min_year, all_max_year){
		var t_span = Math.abs(all_max_year - all_min_year);
		var increment = t_span / 2000;
		var current_y_at_x = {};
		all_min_year = all_min_year - (increment * 3);
		all_max_year = all_max_year + (increment * 3);
		for (var year = all_min_year; year <= all_max_year; year += increment) {
			current_y_at_x[year] = 0;
			this.curent_year_keys.push(year);
		}
		this.current_y_at_x = current_y_at_x; 
		return this.current_y_at_x;
	}
	this.get_current_y_for_year = function(year){
		//get the current y value for the year
		if (year in this.current_y_at_x) {
			return this.current_y_at_x[year];
		}
		else{
			return 0;
		}
	}
	this.make_data_points = function(c_per_year, chrono){
		
		var data_list = [];
		var start = parseFloat(chrono['start']);
		var end = parseFloat(chrono['stop']);
		var median_year = (start + end) / 2;
		var t_span = Math.abs(end - start);
		var added = .002;
		for (var i = 0, length = this.curent_year_keys.length; i < length; i++) {
			var year = this.curent_year_keys[i];
			if (year >= start && year <= end) {
				// we're in the time span of the current dataset
				var act_median_year = median_year;
				var y = this.make_y_value(t_span,
										  added,
										  year,
										  c_per_year,
										  act_median_year);
				var data_point = {
					x: year,
					y: y};
			}
			else{
				var data_point = {
					x: year,
					y: 0};
			}
			data_list.push(data_point);
		}
		// console.log(this.current_y_at_x);
		console.log(data_list);
		return data_list;
	}
	
	this.make_y_value = function(t_span,
								 added,
								 year,
								 c_per_year,
								 mid_year){
		var half_span = t_span * .5;
		var mid_year_dif = Math.abs(mid_year - year);
		var per_span = (half_span - mid_year_dif) / half_span;
		var sigma = 150;
		var y_mean = (year + mid_year) / 2;
		var y_mean = mid_year;
		var y = this.gaussian(year, y_mean, sigma);
		y = y * c_per_year;
		
		
		if (y < added){
			if (per_span <= .15) {
				// we're at the extreme ends
				var y = added * ( per_span / .15);
			}
			else{
				var y = added;
			}
		}
		
		return y
	}
	this.gaussian = function(x, mean, sigma) {
		var gaussianConstant = 1 / Math.sqrt(2 * Math.PI);
		x = (x - mean) / sigma;
		return gaussianConstant * Math.exp(-.5 * x * x) / sigma;
	};
	this.make_dataset = function(){
		var dataset = {
			label: '',
			url: '',
			data: [],
			backgroundColor: "rgba(75,192,192,0.4)",
            borderColor: "rgba(75,192,192,1)",
			borderWidth: 1,
			pointRadius: 0,
			showLines: true,
			spanGaps: true,
			lineTension: 0,
			lineJoin: 'round',
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
						stacked: true,
						display: false
					}],
					xAxes: [{
						type: 'linear',
						position: 'top',
						ticks: {
							max: 2000,
						}
					}]
				}
			},
		});
		this.chart = act_chart;	
	}
}
