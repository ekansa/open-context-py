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
		'#135F8E',
		'#1175AA',
		// '#FFFF00',
		'#9B2400'
	]; // list of colors for gradients
	this.obj_name = 'chrono';
	this.response_types = 'chrono-facet'; // initial response type
	this.control_dom_id = 'chrono-controls';
	this.slider_dom_id = 'chrono-slider';
	this.slider_button_div_dom_id = 'chrono-control-button-div';
	this.slider = null;
	this.chrono_facets_min_year = null;
	this.chrono_facets_max_year = null;
	this.current_y_at_x = {};
	this.curent_year_keys = [];
	this.json_data = null;
	this.chart = null;
	this.initialize = function(){
		if(this.json_data == null){
			this.get_api_data();
		}
	}
	this.get_api_data = function(){
		this.json_url = this.json_url.replace('&amp;', '&');
		var url = this.json_url;
		var params = {'response': this.response_types};
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
		
		this.chrono_facets_min_year = all_min_year;
		this.chrono_facets_max_year = all_max_year;
		
		// now sort the keys, reverse order 
		var	keys_sorted = Object.keys(list).sort(function(a,b){return list[a]-list[b]});
		keys_sorted.reverse();
		// keys_sorted.sort();
		// console.log(keys_sorted);
		
		// datasets
		var datasets = [];
		this.make_current_y_at_x(all_min_year, all_max_year);
		
		var all_t_span = Math.abs(all_max_year - all_min_year);
		var chart_count_year = max_count / all_t_span;
		var chart_count_year = total_count / all_t_span;

		var nearest = 25;
		if(all_t_span > 2000){
			nearest = Math.ceil(Math.log10(all_t_span)) * 100 / 2;
		}
		for (var i = 0, length = keys_sorted.length; i < length; i++) {
			var key = keys_sorted[i];
			var chrono = chrono_objs[key];
			var t_span = list[key];
			
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
			var l_hex_color = l_style_obj.generate_hex_color();
			var b_gradient = this.make_grandient_object(hex_color);
			var l_gradient = this.make_grandient_object(l_hex_color);
			
			// dataset.backgroundColor = hex_color;
			dataset.backgroundColor = b_gradient;
			// dataset.borderColor = l_hex_color;
			dataset.borderColor = l_gradient;
			dataset.borderStrokeColor = "#fff";
			dataset.url = chrono.id;
			/*
			dataset.label = chrono['start'] + ' to ' + chrono['stop'];
			dataset.title = this.round_date(nearest, chrono['start'])
			dataset.title += ' to ';
			dataset.title += this.round_date(nearest, chrono['stop']);
			*/
			dataset.label = this.round_date(nearest, chrono['start']);
			dataset.label += ' to ';
			dataset.label += this.round_date(nearest, chrono['stop']);
			dataset.label += ' (';
			dataset.label += chrono.count;
			dataset.label += ' items)';
			dataset.data = this.make_data_points(chart_count_year,
												 chrono);
			datasets.push(dataset);
		} 
		return datasets;
	}
	this.round_date = function(nearest, date){
		var n_date = parseFloat(date);
		var rounded = n_date + nearest/2 - (n_date + nearest/2) % nearest;
		return rounded;
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
	this.make_data_points = function(chart_count_year,
									 chrono){
		/* methods to the madness:
		
		(1) compute different standard deviations for each chrono,
		    the shortest time spans should have the smallest standard deviation
		    
		(2) the chart_count_year is the total number of records / the whole
		    time span in the chart. The c_per_year value is the number of records
		    in the given chrono-facet time span, times the chart_count_year. This
		    helps make the areas for each chrono-facet curve proportional to the
		    total number of records for all the chrono-facets retrieved
		
		*/
		var data_list = [];
		var start = parseFloat(chrono['start']);
		var end = parseFloat(chrono['stop']);
		var median_year = (start + end) / 2;
		var t_span = Math.abs(end - start);
		// console.log({start: start, end:end, mean:median_year})
		var added = 0;
		for (var i = 0, length = this.curent_year_keys.length; i < length; i++) {
			var year = this.curent_year_keys[i];
			if (year >= start && year <= end) {
				// we're in the time span of the current dataset
				// var c_per_year = chrono.count / t_span;
				var c_per_year = chrono.count * chart_count_year;
				
				var act_median_year = median_year;
				var sigma = t_span * .15;
				var y = this.gaussian(year, act_median_year, sigma);
				y = y * (c_per_year);
				
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
		// console.log(data_list);
		return data_list;
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
			events: [
				'click'
			],
			options: {
				legend: {
					display: false,
				},
				tooltipEvents: ['mousemove', 'click'],
				tooltips: {
					callbacks: {
						label: function(tooltipItems, data){
							// console.log(data.datasets[tooltipItems.datasetIndex].label);
							return data.datasets[tooltipItems.datasetIndex].label;
						},
						title: function(){
							return 'Estimated Time Span';
						}
					},
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
		// now make the contols
		this.make_controls();
	}
	this.make_controls = function(){
		if(document.getElementById(this.control_dom_id)){
			// console.log(this.chart);
			var slider_min = this.chart.scales['x-axis-0'].start;
			var slider_max = 2000;
			var all_t_span = Math.abs(this.chrono_facets_max_year - this.chrono_facets_min_year);
			var nearest = 25;
			if(all_t_span > 2000){
				nearest = Math.ceil(Math.log10(all_t_span)) * 100 / 2;
			}
			var old_start = this.round_date(nearest, this.chrono_facets_min_year);
			if(old_start > this.chrono_facets_min_year){
				old_start = old_start - nearest;
			}
			if(old_start < slider_min){
				old_start = slider_min;
			}
			var late_start = this.round_date(nearest, this.chrono_facets_max_year);
			if(late_start < this.chrono_facets_max_year){
				late_start = late_start + nearest;
			}
			if(late_start > slider_max){
				late_start = slider_max;
			}	
			var act_dom = document.getElementById(this.control_dom_id);
			var html =[
			'<div class="row">',
			'<div class="col-xs-11">',
			'<div style="margin-left: 2.5%; ">',
			'<input id="' + this.slider_dom_id + '" type="text" ',
			'style="width: 100%;" value="" ',
			'data-slider-min="' + slider_min + '" ',
			'data-slider-max="' + slider_max + '" ',
			'data-slider-step="1" ',
			'data-slider-value="[' + old_start + ',' + late_start  +']" />',
			'</div>',
			'</div>',
			'<div class="col-xs-1" id="' + this.slider_button_div_dom_id + '">',
			'<button type="submit" ',
			'class="btn btn-default btn-sm" ',
			'title="Use Sliders to search with a time span" ',
			'onclick="' + this.obj_name + '.chrono_search();">',
			'<span class="glyphicon glyphicon-filter" aria-hidden="true"></span>',
			'</button>',
			'</div>',
			'</div>'
			].join('\n');
			act_dom.innerHTML = html;
			
			this.slider = new Slider(('#' + this.slider_dom_id), {
				current_min: old_start,
				current_max: late_start,
				/*
				formatter: function(value) {
					console.log(value);
					var num_vals = [];
					num_vals.push(parseInt(value[0]));
					num_vals.push(parseInt(value[1]));			  
					return 'Search: ' + Math.min(num_vals) + ' to ' + Math.max(num_vals);
				}
				*/
			});
		}
	}
	this.chrono_search = function(){
		var value = this.slider.getValue();
		var hashed_part = ''; 
        var url = window.location.href;
        if ( url.indexOf('#') > -1) {
            hashed_part = window.location.hash;
            url = url.substr(0, url.indexOf('#'));
        }
		url = replaceURLparameter(url, 'form-start', value[0]);
        url = replaceURLparameter(url, 'form-stop', value[1]);
		var act_dom = document.getElementById(this.slider_button_div_dom_id);
		var html = [
			'<img style="margin-top:-4px;" height="16" ',
			'src="' + base_url + '/static/oc/images/ui/waiting.gif" ',
			'alt="Loading icon..." />',
		].join(' ');
		act_dom.innerHTML = html;
        window.location = url; //load the page with the time query
	}
}
