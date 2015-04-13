/*
 * Map projects from GeoJSON
 */
 
function project_map(json_url) {
	
	var map_dom_id = 'map';
	var map_title_dom_id = 'map-title';
	var map_title_suffix_dom_id = 'map-title-suffix';
	var map_menu_dom_id = 'map-menu';
	var map_box_token = "pk.eyJ1IjoiZWthbnNhIiwiYSI6IlZFQ1RfM3MifQ.KebFObTZOeh9pDHM_yXY4g";
	
	this.json_url = json_url; // base url for geo-json requests
	this.json_url = this.json_url.replace('&amp;', '&');
	
	map = L.map(map_dom_id).setView([45, 0], 2); //map the map
	// remove the geodeep parameter
	this.json_url = removeURLParameter(this.json_url, 'geodeep');
	map.json_url = this.json_url
	
	//map.fit_bounds exists to set an inital attractive view
	map.fit_bounds = false;
	map.geojson = false;  //current geojson data
	map.circle_layer = false;
	map.color_list = false;
	
	var bounds = new L.LatLngBounds();
	var mapboxPencil = L.tileLayer('http://api.tiles.mapbox.com/v4/mapbox.pencil/{z}/{x}/{y}.png?access_token=' + map_box_token, {
		attribution: '&copy; <a href="http://MapBox.com">MapBox.com</a> '
	});
	var mapboxLight = L.tileLayer('http://api.tiles.mapbox.com/v4/mapbox.light/{z}/{x}/{y}.png?access_token=' + map_box_token, {
		attribution: '&copy; <a href="http://MapBox.com">MapBox.com</a> '
	});
	var baseMaps = {
		"Pencil": mapboxPencil,
		"Light": mapboxLight,
	};
  
	map._layersMaxZoom = 20;
	// var layerControl = L.control.layers(baseMaps).addTo(map);
	// console.log(layerControl);
	map.addLayer(mapboxLight);
	
	map.show_title_menu = function(map_type, geodeep){
		/*
		* Show current layer type
		*/
		if (document.getElementById(map_title_dom_id)) {
			//if the map title element exits
			var act_dom_id = map_title_dom_id;
			var title = document.getElementById(act_dom_id);
			var act_dom_id = map_title_suffix_dom_id;
			var title_suf = document.getElementById(act_dom_id);
			title_suf.innerHTML = "";
			var act_dom_id = map_menu_dom_id;
			var menu = document.getElementById(act_dom_id);
			
			/*
			* Handle geo-regions (facets)
			*/
			if (map_type == 'geo-facet') {
				title.innerHTML = "Map of Counts by Region";
			}
		}
	}
	
	function on_each_project_feature(feature, layer){
		
		if (feature.properties['early bce/ce'] != feature.properties['late bce/ce']) {
			var date_range = style_bce_ce_year(feature.properties['early bce/ce']);
			date_range += " to " + style_bce_ce_year(feature.properties['late bce/ce']);
		}
		else{
			var date_range = style_bce_ce_year(feature.properties['early bce/ce']);
		}
		if (feature.properties) {
			var popupContent = [
			"<div>",
			"<dl>",
			"<dt>Project</dt>",
			"<dd>",
			"<a href='" + feature.properties.href + "'>" + feature.properties.label + "</a>",
			"</dd>",
			//"</dl>",
			//"<dl>",
			"<dt>Time Range</dt>",
			"<dd>" + date_range + "</dd>",
			//"</dl>",
			//"<dl>",
			"<dt>Records</dt>",
			"<dd>",
			"<a href='" + feature.properties.search + "'>" + feature.count + " (Click to Browse)</a>",
			"</dd>",
			"</dl>",
			"</div>"].join("\n");
			layer.bindPopup(popupContent);
		}
	}
	
	map.circle_projects = function (){
		// renders the geojson for projects
		
		//first get min and max counts
		var max_value = 1;
		var min_value = 0;
		for (var i = 0, length = map.geojson.features.length; i < length; i++) {
			feature = map.geojson.features[i];
			if (feature.count > max_value) {
				max_value = feature.count;
			}
			if (i < 1) {
				min_value = feature.count;
			}
			else{
				if (feature.count < min_value) {
					min_value = feature.count;
				}
			}
		}
		var circle_layer = L.geoJson(map.geojson.features, {
			pointToLayer: function (feature, latlng) {
				var style_obj = new numericStyle();
				if (map.color_list != false) {
					style_obj.reset_gradient_colors(map.color_list);
				}
				style_obj.min_value = min_value;
				style_obj.max_value = max_value;
				style_obj.act_value = feature.count;
				var hex_color = style_obj.generate_hex_color();
				var radius = Math.round(20 * (feature.count / max_value), 0) + 5;
				var markerOps = {
					'radius': radius,
					'fillColor': hex_color,
					'color': hex_color,
					weight: 1,
					opacity: 1,
					fillOpacity: 0.8
				}
				return L.circleMarker(latlng, markerOps);
			},
			onEachFeature: on_each_project_feature
		});
		map.circle_layer = circle_layer;
		if (map.fit_bounds) {
			//map.fit_bounds exists to set an inital attractive view
			map.fitBounds(circle_layer.getBounds());
		}
		circle_layer.addTo(map);
	}
	
	map.get_geojson = function (){
		/*
		* Show current layer type
		*/
		if (document.getElementById(map_title_dom_id)) {
			// show the loading script
			var act_dom_id = map_title_dom_id;
			var loading = "<img style=\"margin-top:-4px;\" height=\"16\"  src=\"";
			loading += base_url + "/static/oc/images/ui/waiting.gif\" alt=\"Loading icon...\" />";
			loading += " Loading Regions...";
			document.getElementById(act_dom_id).innerHTML =loading;
			var act_dom_id = map_title_suffix_dom_id;
			document.getElementById(act_dom_id).innerHTML = "";
		}
		//do the ajax request
		$.ajax({
			type: "GET",
			url: map.json_url,
			dataType: "json",
			data: {response: "geo-project"},
			success: function(data) {
				map.geojson = data;
				map.circle_projects();
			}
		})
	}

	this.map = map;
}
