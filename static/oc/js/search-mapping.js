/*
 * Map an individual item with GeoJSON
 */
var polyStyle = {
	"color": "#ff7800",
	"weight": 2,
	"opacity": 0.85,
	"fillOpacity": 0.5
 };
 
function search_map(json_url) {
	
	var map_dom_id = 'map';
	var map_title_dom_id = 'map-title';
	var map_title_suffix_dom_id = 'map-title-suffix';
	var map_menu_dom_id = 'map-menu';
	var geodeep = 6; // default geo-facet tile depth
	var rows = 20; // default number of rows
	var tile_constrained = false;
	var map_box_token = "pk.eyJ1IjoiZWthbnNhIiwiYSI6IlZFQ1RfM3MifQ.KebFObTZOeh9pDHM_yXY4g";
	
	this.json_url = json_url; // base url for geo-json requests
	this.json_url = this.json_url.replace('&amp;', '&');
	var url_parts = getJsonFromUrl(json_url);
	if (url_parts['disc-geotile']) {
		//geodeep = url_parts['disc-geotile'].length + 4;
		geodeep = 4;
		tile_constrained = true;
	}
	else{
		// zoom in a bit if deeper in the context path
		var check_url = this.json_url.replace('.json', '');
		var url_ex = check_url.split('/sets/');
		if (url_ex.length > 1) {
			var after_sets = url_ex[1];
			if (after_sets.length > 0) {
				geodeep = 8;
				var after_sets = url_ex[1];
				var slash_count = (after_sets.match(/\//g) || []).length;
				if (slash_count > 0) {
					geodeep += slash_count + 2;
				}
			}
		}
	}
	
	//if geodeep is in the url, use it.
	if (url_parts['geodeep']) {
		geodeep = url_parts['geodeep'];
	}
	
	map = L.map(map_dom_id).setView([45, 0], 2); //map the map
	// remove the geodeep parameter
	this.json_url = removeURLParameter(this.json_url, 'geodeep');
	map.json_url = this.json_url
	map.geodeep = geodeep;
	map.rows = rows;
	//map.fit_bounds exists to set an inital attractive view
	map.fit_bounds = false;
	map.max_tile_zoom = 20;
	map.default_layer = 'tile';
	map.layer_limit = false;
	map.min_tile_count_display = 200;
	map.geojson_facets = {};  //geojson data for facet regions, geodeep as key
	map.geojson_records = {}; //geojson data for records, start as key
	if (map.geodeep > 6 || tile_constrained) {
		map.fit_bounds = true;
	}
	if (map.geodeep > 20) {
		map.geodeep = 20;
	}
	var bounds = new L.LatLngBounds();
	var osmTiles = L.tileLayer('http://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
		attribution: '&copy; <a href="http://osm.org/copyright">OpenStreetMap</a> contributors'
	});
   
	var mapboxLight = L.tileLayer('http://api.tiles.mapbox.com/v4/mapbox.light/{z}/{x}/{y}.png?access_token=' + map_box_token, {
		attribution: '&copy; <a href="http://MapBox.com">MapBox.com</a> '
	});
	
	var mapboxDark = L.tileLayer('http://api.tiles.mapbox.com/v4/mapbox.dark/{z}/{x}/{y}.png?access_token=' + map_box_token, {
		attribution: '&copy; <a href="http://MapBox.com">MapBox.com</a> '
	});
   
	var ESRISatelliteTiles = L.tileLayer('http://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
		attribution: '&copy; <a href="http://services.arcgisonline.com/">ESRI.com</a> '
	});
   
	var gmapRoad = new L.Google('ROADMAP');
	var gmapSat = new L.Google('SATELLITE');
	var gmapTer = new L.Google('TERRAIN');
   
	var baseMaps = {
		"Google-Terrain": gmapTer,
		"Google-Satellite": gmapSat,
		"ESRI-Satellite": ESRISatelliteTiles,
		"Google-Roads": gmapRoad,
		"OpenStreetMap": osmTiles,
		"Mapbox-Light": mapboxLight,
		"Mapbox-Dark": mapboxDark,
	};
  
	map._layersMaxZoom = 20;
	var layerControl = L.control.layers(baseMaps).addTo(map);
	map.addLayer(gmapSat);
	
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
	
	var region_controls = false;
	map.add_region_controls = function(){
		/*
		* Add geo-regions (control)
		*/
		if (!region_controls) {
			var buttonControls = L.DomUtil.create('div', 'leaflet-bar leaflet-control');
			buttonControls.id = 'region-facet-buttons';
			var deep_tile_control = L.easyButton('glyphicon-th', 
				function (){
					var new_geodeep = parseInt(map.geodeep) + 1;
					if (new_geodeep <= map.max_tile_zoom) {
						//can still zoom in
						map.view_region_layer_by_zoom(new_geodeep);
					}
				},
				'Higher resolution Open Context regions',
				buttonControls
			);
			var big_tile_control = L.easyButton('glyphicon-th-large', 
				function (){
					var new_geodeep = map.geodeep - 1;
					if (new_geodeep > 3) {
						//can still zoom out
						map.view_region_layer_by_zoom(new_geodeep);
					}
				},
				'Lower resolution Open Context regions',
				buttonControls
			);
			var circle_control = L.easyButton('fa-circle-o', 
				function (){
					if (map.hasLayer(tile_region_layer)) {
						// delete the currently displayed layer
						map.removeLayer(tile_region_layer);
					}
					map.circle_regions();
				},
				'Circle-markers for Open Context regions',
				buttonControls
			);
			deep_tile_control.id = 'test-control';
			deep_tile_control.link.id = 'tile-more-precision';
			big_tile_control.link.id = 'tile-less-precision';
			region_controls = true;
			
			//now add a box-zoom
			var zoom_control = L.control.zoomBox({modal: true});
			map.addControl(zoom_control);
		}
		else{
			// toggle map controls based on map.geodeep
			map.toggle_tile_controls();
		}
	}
	
	map.toggle_tile_controls = function(){
		var act_dom_id = 'tile-more-precision';
		var link = document.getElementById(act_dom_id);
		if (map.geodeep >= map.max_tile_zoom) {
			// can't zoom in anymore
			link.className = 'diabled-map-button';
			link.title = 'At maximum spatial resolution for these data';
		}
		else {
			link.title = 'Higher resolution Open Context regions';
			link.className = '';
			link.style = '';
		}
		var act_dom_id = 'tile-less-precision';
		var link = document.getElementById(act_dom_id);
		if (map.geodeep <= 4) {
			// can't zoom out anymore
			link.title = 'At minimum spatial resolution';
			link.className = 'diabled-map-button';
		}
		else{
			link.title = 'Lower resolution Open Context regions';
			link.className = '';
			link.style = '';
		}
	}
	
	
	map.view_region_layer_by_zoom = function(geodeep){
		/*
		 * get a layer by zoom level
		 */
		if (map.hasLayer(circle_region_layer)) {
			//delete the cicle if it exits
			map.removeLayer(circle_region_layer);
		}
		if (map.hasLayer(tile_region_layer)) {
			// delete the tile if it exits
			map.removeLayer(tile_region_layer);
		}
		map.fit_bounds = true;
		if (geodeep in map.geojson_facets) {
			map.geodeep = geodeep;
			map.render_region_layer();
		}
		else{
			if (geodeep <= map.max_tile_zoom) {
				// go get new data
				map.geodeep = geodeep;
				map.get_geojson_regions();
			}
		}
	}
	
	var tile_region_layer = false;
	map.render_region_layer = function (){
		// does the work of rendering a region facet layer
		if (map.geodeep in map.geojson_facets) {
			/*
			 * Loop through features to get the range of counts.
			 */
			var geojson_facets = map.geojson_facets[map.geodeep];
			if ('oc-api:max-disc-tile-zoom' in geojson_facets) {
				map.max_tile_zoom = geojson_facets['oc-api:max-disc-tile-zoom'];
			}
			var max_value = 1;
			var min_value = 0;
			for (var i = 0, length = geojson_facets.features.length; i < length; i++) {
				feature = geojson_facets.features[i];
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
			var region_layer = false;
			var region_layer = L.geoJson(geojson_facets,
				{
					style: function(feature){
							// makes colors, opacity for each feature
							var style_obj = new numericStyle();
							style_obj.min_value = min_value;
							style_obj.max_value = max_value;
							style_obj.act_value = feature.count;
							var hex_color = style_obj.generate_hex_color();
							var fill_opacity = style_obj.generate_opacity();
							return {color: hex_color,
									fillOpacity: fill_opacity,
									weight: 2}
						    },
					onEachFeature: on_each_region_feature
				});
			region_layer.geodeep = map.geodeep;
			region_layer.max_value = max_value;
			region_layer.min_value = min_value;
			tile_region_layer = region_layer;
			if (map.fit_bounds) {
				//map.fit_bounds exists to set an inital attractive view
				map.fitBounds(region_layer.getBounds());
			}
			region_layer.addTo(map);
			if (region_controls) {
				map.toggle_tile_controls();
			}
		}
	}
	
	function on_each_region_feature(feature, layer){
		/*
		 * For handeling facet region features
		 */
		feature.re_color = function(min_value, max_value){
			// make a function for each feature to assign new colors
			var style_obj = new numericStyle();
			style_obj.min_value = min_value;
			style_obj.max_value = max_value;
			style_obj.act_value = feature.count;
			var hex_color = style_obj.generate_hex_color();
			var fill_opacity = style_obj.generate_opacity();
			layer.setStyle({
				color: hex_color,
				fillOpacity: fill_opacity
			});
		}
		if (feature.properties) {
			if (feature.properties['early bce/ce'] != feature.properties['late bce/ce']) {
				var date_range = style_bce_ce_year(feature.properties['early bce/ce']);
				date_range += " to " + style_bce_ce_year(feature.properties['late bce/ce']);
			}
			else{
				var date_range = style_bce_ce_year(feature.properties['early bce/ce']);
			}
			
			var popupContent = "<div> This discovery region has " + feature.count;
			popupContent += " items, with a date range of: " + date_range;

			popupContent += ". ";
			if(feature.properties.href){
				var use_href = removeURLParameter(feature.properties.href, 'response');
				use_href = removeURLParameter(use_href, 'geodeep');
				var next_deep = 5;
				if (next_deep > 20) {
					next_deep = 20;
				}
				use_href += "&geodeep=" + next_deep;
				popupContent += "<a href='" + use_href + "'>Click here</a> to filter by this region."
			}
			popupContent += "</div>";
			layer.bindPopup(popupContent);
		}
		
		if (typeof layer._latlngs !== 'undefined') {
			var newbounds = layer.getBounds();
			bounds.extend(newbounds.getSouthWest());
			bounds.extend(newbounds.getNorthEast());
		}
	}
	
	
	function on_each_circle_feature(feature, layer){
		
		if (feature.properties) {
			
			var popupContent = "<div> This discovery region has " + feature.count;
			popupContent += " items. ";
			if(feature.properties.href){
				var use_href = removeURLParameter(feature.properties.href, 'response');
				use_href = removeURLParameter(use_href, 'geodeep');
				var next_deep = 5;
				if (next_deep > 20) {
					next_deep = 20;
				}
				use_href += "&geodeep=" + next_deep;
				popupContent += "<a href='" + use_href + "'>Click here</a> to filter by this region."
			}
			popupContent += "</div>";
			layer.bindPopup(popupContent);
		}
	}
	
	var circle_region_layer = false;
	map.circle_regions = function (){
		// does the work of rendering a region facet layer
		if (map.geodeep in map.geojson_facets) {
			// var original_geojson = map.geojson_facets[map.geodeep];
			var geojson_facets = map.geojson_facets[map.geodeep];
			if ('oc-api:max-disc-tile-zoom' in geojson_facets) {
				map.max_tile_zoom = geojson_facets['oc-api:max-disc-tile-zoom'];
			}
			/*
			 * 1st we aggregate nearby tiles getting points for the center of each
			 * tile region
			 */
			var aggregated_tiles = {}
			for (var i = 0, length = geojson_facets.features.length; i < length; i++) {
				var feature = geojson_facets.features[i];
				var geometry = feature.geometry;
				var geo_id_ex = geometry.id.split('-');
				var geo_tile = geo_id_ex[geo_id_ex.length - 1];
				var aggregate_tile_id = geo_tile.substring(0, (geo_tile.length -1));
				if (aggregate_tile_id in aggregated_tiles) {
					var act_tile = aggregated_tiles[aggregate_tile_id];
				}
				else{
					var act_tile = [];
				}
				var centroid = getCentroid(geometry.coordinates[0]);
				var tile_point = {'centroid': centroid,
						  'count': feature.count,
						  'url': feature.id.replace(geo_tile, aggregate_tile_id) };
				act_tile.push(tile_point);
				aggregated_tiles[aggregate_tile_id] = act_tile;
			}
			/*
			 * 2nd we compute the weighted average for nearby tile center points
			 * based on their counts. This will help make the map look less like a grid
			 */
			var max_value = 1;
			var min_value = false;
			var count_keys = [];
			var points = {};
			for(var tile_key in aggregated_tiles) { 
				var points_data = aggregated_tiles[tile_key];
				var total_count = 0;
				var sum_longitude = 0;
				var sum_latitude = 0;
				var url = points_data[0]['url'];
				// console.log(points_data);
				for (var i = 0, length = points_data.length; i < length; i++) {
					var act_pdata = points_data[i];
					total_count += act_pdata['count'];
					sum_longitude += act_pdata['centroid'][0] * act_pdata['count'];
					sum_latitude += act_pdata['centroid'][1] * act_pdata['count'];
				}
				// computed weighted average for the center of these tile regions
				var mean_longitude = sum_longitude / total_count;
				var mean_latitude = sum_latitude / total_count;
				var point = {'type': 'Feature',
				             'properties': {
						'href': url
					     },
					     'geometry': {
						'type': 'Point',
						'coordinates': [mean_longitude, mean_latitude]
					     },
					     'count': total_count,
					     'url': url}
				var count_key = make_unique_count_key(total_count, count_keys);
				count_keys.push(count_key)
				points[count_key] = point;
				if (total_count > max_value) {
					max_value = total_count;
				}
				if (min_value == false) {
					min_value = total_count;
				}
				else{
					if (total_count < min_value) {
						min_value = total_count;
					}
				}
			}
			/*
			 * 3rd we sort the points in descending order of count so the point features with
			 * the highest counts will be rendered lower
			 */
			count_keys.sort(function(a, b){return b-a});
			var feature_points = []
			for (var i = 0, length = count_keys.length; i < length; i++) { 
				var count_key = count_keys[i];
				var point = points[count_key];
				feature_points.push(point);
			}
			// now switch the polygon regions for points
			pgeo_json = {'type': "FeatureCollection",
			             'features': feature_points}
			var circle_layer = L.geoJson(pgeo_json, {
				onEachFeature: on_each_circle_feature,
				pointToLayer: function (feature, latlng) {
					var style_obj = new numericStyle();
					color_list = ['#FFC600',
						      '#FF6F00',
						      '#FF1600'];
					style_obj.reset_gradient_colors(color_list);
					style_obj.min_value = min_value;
					style_obj.max_value = max_value;
					style_obj.act_value = feature.count;
					var hex_color = style_obj.generate_hex_color();
					var radius = Math.round(30 * (feature.count / max_value), 0) + 5;
					var markerOps = {
						'radius': radius,
						'fillColor': hex_color,
						'color': hex_color,
						weight: 1,
						opacity: 1,
						fillOpacity: 0.8
					}
					return L.circleMarker(latlng, markerOps);
				}
			});
			circle_region_layer = circle_layer;
			if (map.fit_bounds) {
				//map.fit_bounds exists to set an inital attractive view
				map.fitBounds(circle_layer.getBounds());
			}
			circle_layer.addTo(map);
			if (region_controls) {
				map.toggle_tile_controls();
			}
			// delete map.geojson_facets[map.geodeep];
			// map.geojson_facets[map.geodeep] = original_geojson;
		}
	}
	
	map.show_region_loading = function (){
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
	}
	map.get_geojson_regions = function (){
		/*
		* Show current layer type
		*/
		map.show_region_loading();
		//do the ajax request
		$.ajax({
			type: "GET",
			url: map.json_url,
			dataType: "json",
			data: {
				response: "geo-facet",
				geodeep: map.geodeep},
			success: function(data) {
				map.geojson_facets[map.geodeep] = data;
				if (map.layer_limit == false) {
					//code
					if (data.features.length > map.min_tile_count_display || map.default_layer == 'tile') {
						map.render_region_layer();
					}
					else{
						map.circle_regions();
					}
				}
				else if(map.layer_limit == 'circle'){
					map.circle_regions();
				}
				else{
					map.render_region_layer();
				}
				map.show_title_menu('geo-facet', map.geodeep);
				map.add_region_controls();
			}
		})
	}

	this.map = map;
}
