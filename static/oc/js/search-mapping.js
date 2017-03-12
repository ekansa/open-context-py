/*
 * Map search results (currently only geo-facets)
 * from the GeoJSON API service
 */

function search_map(json_url, base_search_link, response_tile_zoom) {
	
	var map_dom_id = 'map';
	var rows = 20; // default number of rows
	var tile_constrained = false;
	var map_box_token = "pk.eyJ1IjoiZWthbnNhIiwiYSI6IlZFQ1RfM3MifQ.KebFObTZOeh9pDHM_yXY4g";
	
	this.base_search_link = base_search_link;
	this.json_url = json_url; // base url for geo-json requests
	this.json_url = this.json_url.replace('&amp;', '&');
	if (response_tile_zoom !== undefined) {
		this.geodeep = response_tile_zoom; // geo-tile zoom level beyond current zoom level
	}
	else{
		this.geodeep = 6; // geo-tile zoom level beyond current zoom level
	}
	// this.response_types = 'geo-facet,chrono-facet'; // initial response type
	this.response_types = 'geo-facet'; // initial response type
	this.set_geodeep = function() {
		/* We need to set a reasonable size for the geospatial facet
		 * tiles that we will request. 'geodeep' is the level of 
		 * tile depth below the current map zoom that is requested
		 * 
		 */
		var geodeep = this.geodeep;
		var url_parts = parseUrl(this.json_url);
		var context_path_geodeep = false;
		if (url_parts['disc-geotile']) {
			// if a geotile is used as a search filter, as for
			// 4 zoom levels deeper to show geo-tile facets constrained
			// by this filter
			geodeep = 4;
			tile_constrained = true;
		}
		//if geodeep is in the url, use it.
		if (url_parts['geodeep']) {
			geodeep = url_parts['geodeep'];
		}
		return geodeep;
	}
	
	map = L.map(map_dom_id).setView([45, 0], 2); //map the map
	hash = new L.Hash(map);
	map.map_title_dom_id = 'map-title';
	map.map_title_suffix_dom_id = 'map-title-suffix';
	map.map_menu_dom_id = 'map-menu';
	map.json_url = this.json_url;
	map.response_types = this.response_types;
	map.geodeep = this.set_geodeep();
	// remove the geodeep parameter
	this.json_url = removeURLParameter(this.json_url, 'geodeep');
	//map.fit_bounds exists to set an inital attractive view
	map.rows = rows;
	map.fit_bounds = false;
	map.max_tile_zoom = 20;
	map.default_overlay_layer = 'any';
	map.layer_limit = false;
	map.button_ready = true;
	map.min_tile_count_display = 25;
	map.geojson_facets = {};  //geojson data for facet regions, geodeep as key
	map.geojson_records = {}; //geojson data for records, start as key
	if (map.geodeep > 6 || tile_constrained) {
		map.fit_bounds = true;
	}
	if (map.geodeep > 20) {
		map.geodeep = 20;
	}
	var bounds = new L.LatLngBounds();
	var osmTiles = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
		id: 'osm',
		attribution: '&copy; <a href="https://osm.org/copyright">OpenStreetMap</a> contributors'
	});
   
	var mapboxLight = L.tileLayer('https://api.tiles.mapbox.com/v4/mapbox.light/{z}/{x}/{y}.png?access_token=' + map_box_token, {
		id: 'mapbox-light',
		attribution: '&copy; <a href="https://MapBox.com">MapBox.com</a> '
	});
	
	var mapboxDark = L.tileLayer('https://api.tiles.mapbox.com/v4/mapbox.dark/{z}/{x}/{y}.png?access_token=' + map_box_token, {
		id: 'mapbox-dark',
		attribution: '&copy; <a href="https://MapBox.com">MapBox.com</a> '
	});
   
	var ESRISatelliteTiles = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
		id: 'esri-sat',
		attribution: '&copy; <a href="https://services.arcgisonline.com/">ESRI.com</a> '
	});
   
	var gmapRoad = new L.Google('ROADMAP');
	gmapRoad.id = 'gmap-road';
	var gmapSat = new L.Google('SATELLITE');
	gmapSat.id = 'gmap-sat';
	var gmapTer = new L.Google('TERRAIN');
	gmapTer.id = 'gmap-ter';
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
	map.default_base_name = "Google-Satellite";
	map.base_name = map.default_base_name;
	map.act_base_map = gmapSat; //default base map
	map.base_layers = baseMaps;
	map.record_base_change = false;
	// add the layer control
	var layerControl = L.control.layers(baseMaps).addTo(map);
	map.on('baselayerchange', function(e) {
		// when the base layer changes, keep the id
		this.base_name = e.name;
		if (this.record_base_change) {
			hash.forceHashChange(this);
		}
		else{
			// don't record the hash change
			// for the fist layer change
			this.record_base_change = true;
		}
	});
	// now add the active base map
	map.addLayer(map.act_base_map);
	
	
	
	
	/**************************************************************
	 * Check for hashes in the URL that may indicate map parameters
	 *************************************************************/
	map.req_hash = window.location.hash;
	map.req_hash_layer = false;
	map.get_request_hash = function(){
		// get the original map hash
		if(map.req_hash) {
			// Fragment exists
			var args = map.req_hash.split("/");
			if (args.length >= 3) {
				var geodeep = parseInt(args[3], 10);
				if (!isNaN(geodeep)) {
					map.geodeep = geodeep;
				}
				if (args.length >= 4) {
					if (args[4] != 'false'){
						map.req_hash_layer = args[4];
					}	
				}
				if (args.length >= 5) {
					var map_name = args[5];
					if (map_name in map.base_layers){
						map.base_name = map_name;
						var act_base_map = map.act_base_map;
						map.removeLayer(act_base_map);
						var act_base_map = map.base_layers[map_name];
						map.act_base_map = act_base_map;
						map.addLayer(act_base_map);
					}	
				}
			}
		} else {
			// Fragment doesn't exist
			map.req_hash = false;
		}
	}
	
	
	/**************************************************
	 * Functions for change tile resolution, or
	 * changing between rectable and circle markers for
	 * geofacets
	 **************************************************
	 */
	var region_controls = false;
	map.add_region_controls = function(){
		/*
		* Add geo-regions (control)
		*/
		if (!region_controls) {
			var buttonControls = L.DomUtil.create('div', 'leaflet-bar leaflet-control');
			buttonControls.id = 'region-facet-buttons';
			var deep_tile_control = L.easyButton('glyphicon-th',
				// the control for higher resolution region tiles
				function (){
					map.default_overlay_layer = 'tile';
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
				// control for lower resolution region tiles
				function (){
					map.default_overlay_layer = 'tile';
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
					map.default_overlay_layer = 'circle';
					map.circle_regions();
				},
				'Circle-markers for Open Context regions',
				buttonControls
			);
			deep_tile_control.id = 'test-control';
			deep_tile_control.link.id = 'tile-more-precision';
			big_tile_control.link.id = 'tile-less-precision';
			region_controls = true;
			
			var download_control = L.easyButton('glyphicon-download', 
				function (){
					if( confirm('Save a file of region-summary GeoJSON (GIS) data?') ) {
						
						var data = map.geojson_facets[map.geodeep];
						var geojson = JSON.stringify(data, null, 2);
						//now save it!
						var filename = 'Open-Context-GeoSpatial-Summary.geojson';
						var blob = new Blob([geojson], { type: 'application/json;charset=utf-8;' });
						if (navigator.msSaveBlob) { // IE 10+
							navigator.msSaveBlob(blob, filename);
						} else {
							var link = document.createElement("a");
							if (link.download !== undefined) { // feature detection
								// Browsers that support HTML5 download attribute
								var url = URL.createObjectURL(blob);
								link.setAttribute("href", url);
								link.setAttribute("download", filename);
								link.style.visibility = 'hidden';
								document.body.appendChild(link);
								link.click();
								document.body.removeChild(link);
							}
						}
						
					}
				}, 
				'Locally save GeoJSON (GIS) region summary of search results',
				buttonControls
			);
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
			if (geodeep <= map.max_tile_zoom && map.button_ready) {
				// go get new data
				map.geodeep = geodeep;
				map.get_geojson_regions();
			}
		}
	}
	
	
	/**************************************************
	 * Functions for displaying geo-facets as rectangle
	 * polygon regions
	 **************************************************
	 */
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
		map.button_ready = true;
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
	
	
	
	/**************************************************
	 * Functions for displaying geo-facets as circle
	 * markers
	 **************************************************
	 */
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
		}
		map.button_ready = true;
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
	
	
	
	/**************************************************
	 * AJAX Request to get new map data
	 * 
	 *************************************************
	*/
	map.get_geojson_regions = function (){
		map.show_region_loading(); // show loading gif
		//do the ajax request
		$.ajax({
			type: "GET",
			url: map.json_url,
			async: true,
			dataType: "json",
			data: {
				response: map.response_types,
				geodeep: map.geodeep},
			success: function(data) {
				// make so we don't ask for chrono-facets after the first load
				map.response_types = 'geo-facet';
				
				map.show_region_loading();
				if ('oc-api:response-tile-zoom' in data) {
					map.geodeep = data['oc-api:response-tile-zoom'];
				}
				map.geojson_facets[map.geodeep] = data;
				if (map.layer_limit == false) {
					//code
					if (map.req_hash_layer == 'circle') {
						// initial hash request wants a circle
						map.circle_regions();
					}
					else if (map.req_hash_layer == 'tile') {
						// initial hash request wants a tile
						map.render_region_layer();
					}
					else{
						// intital has request did not specify circle or tile
						if (data.features.length > map.min_tile_count_display
						    || map.default_overlay_layer == 'tile') {
							map.render_region_layer();
						}
						else{
							map.circle_regions();
						}
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
				var scale = L.control.scale().addTo(map); 
				if (map.req_hash != false) {
					// for the initial load of the page,
					// go back to the original request hash
					window.location.replace(map.req_hash);
					// do it only once, for the first page load
					map.req_hash = false;
					map.req_hash_layer  = false;
				}
			}
		})
	}
	
	
	/**************************************************
	 * Functions for HTML changes for loading maps
	 * and displaying map titles
	 *************************************************
	 */
	map.show_region_loading = function (){
		if (document.getElementById(map.map_title_dom_id)) {
			// show the loading script
			map.button_ready = false;
			var act_dom_id = map.map_title_dom_id;
			var loading = "<img style=\"margin-top:-4px;\" height=\"16\"  src=\"";
			loading += base_url + "/static/oc/images/ui/waiting.gif\" alt=\"Loading icon...\" />";
			loading += " Loading Regions...";
			document.getElementById(act_dom_id).innerHTML = loading;
			var act_dom_id = map.map_title_suffix_dom_id;
			document.getElementById(act_dom_id).innerHTML = "";
		}
	}
	map.show_title_menu = function(map_type, geodeep){
		/*
		* Show current layer type
		*/
		if (document.getElementById(map.map_title_dom_id)) {
			//if the map title element exits
			var act_dom_id = map.map_title_dom_id;
			var title = document.getElementById(act_dom_id);
			var act_dom_id = map.map_title_suffix_dom_id;
			var title_suf = document.getElementById(act_dom_id);
			title_suf.innerHTML = "";
			var act_dom_id = map.map_menu_dom_id;
			var menu = document.getElementById(act_dom_id);
			
			/*
			* Handle geo-regions (facets)
			*/
			if (map_type == 'geo-facet') {
				title.innerHTML = "Map of Counts by Region";
			}
		}
	}
	
	this.map = map;
}
