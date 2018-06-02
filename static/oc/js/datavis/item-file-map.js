/*
 * Map search results (currently only geo-facets)
 * from the GeoJSON API service
 */
var prev_polyStyle = {
	"color": "#ff7800",
	"weight": 2,
	"opacity": 0.85,
	"fillOpacity": 0.5
 };
var pmap = null;
function item_file_map(geo_json_url) {
	
	var map_dom_id = 'preview-map';
	var map_box_token = "pk.eyJ1IjoiZWthbnNhIiwiYSI6IlZFQ1RfM3MifQ.KebFObTZOeh9pDHM_yXY4g";
	
	this.json_url = geo_json_url; // base url for geo-json requests
	this.json_url = this.json_url.replace('&amp;', '&');
	
	pmap  = L.map(map_dom_id).setView([45, 0], 2); //map the map
	pmap.map_title_dom_id = 'map-title';
	pmap.json_url = this.json_url;
	pmap.default_overlay_layer = 'any';
	var bounds = new L.LatLngBounds();
	var osmTiles = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
		maxZoom: 26,
		id: 'osm',
		attribution: '&copy; <a href="https://osm.org/copyright">OpenStreetMap</a> contributors'
	});
   
	var mapboxLight = L.tileLayer('https://api.tiles.mapbox.com/v4/mapbox.light/{z}/{x}/{y}.png?access_token=' + map_box_token, {
		maxZoom: 26,
		id: 'mapbox-light',
		attribution: '&copy; <a href="https://MapBox.com">MapBox.com</a> '
	});
	
	var mapboxDark = L.tileLayer('https://api.tiles.mapbox.com/v4/mapbox.dark/{z}/{x}/{y}.png?access_token=' + map_box_token, {
		maxZoom: 26,
		id: 'mapbox-dark',
		attribution: '&copy; <a href="https://MapBox.com">MapBox.com</a> '
	});
   
	var ESRISatelliteTiles = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
		maxZoom: 26,
		id: 'esri-sat',
		attribution: '&copy; <a href="https://services.arcgisonline.com/">ESRI.com</a> '
	});
   
	var gmapRoad = new L.gridLayer.googleMutant({
			maxZoom: 26,
			type:'roadmap'
		});
	gmapRoad.id = 'gmap-road';
	var gmapSat = new L.gridLayer.googleMutant({
			maxZoom: 26,
			type:'satellite'
		});
	gmapSat.id = 'gmap-sat';
	var gmapTer = new L.gridLayer.googleMutant({
			maxZoom: 26,
			type:'terrain'
		});
	gmapTer.id = 'gmap-ter';
	var gmapHybrid = new L.gridLayer.googleMutant({
			maxZoom: 26,
			type:'hybrid'
		});
	gmapHybrid.id = 'gmap-hybrid';
	var baseMaps = {
		"Google-Terrain": gmapTer,
		"Google-Satellite": gmapSat,
		"ESRI-Satellite": ESRISatelliteTiles,
		"Google-Roads": gmapRoad,
		"OpenStreetMap": osmTiles,
		"Mapbox-Light": mapboxLight,
		"Mapbox-Dark": mapboxDark,
	};
	pmap._layersMaxZoom = 35;
	pmap.default_base_name = "Google-Satellite";
	pmap.base_name = pmap.default_base_name;
	pmap.act_base_map = gmapSat; //default base map
	pmap.base_layers = baseMaps;
	// add the layer control
	var layerControl = L.control.layers(baseMaps).addTo(pmap);
	pmap.addLayer(pmap.act_base_map);
	
	/**************************************************
	 * AJAX Request to get new map data
	 * 
	 *************************************************
	*/
	pmap.get_geojson = function (){
		pmap.show_region_loading(); // show loading gif
		//do the ajax request
		$.ajax({
			type: "GET",
			url: pmap.json_url,
			async: true,
			dataType: "json",
			success: function(data) {
				// make so we don't ask for chrono-facets after the first load
				var geojson_layer = L.geoJson(data, {style: prev_polyStyle}).addTo(pmap);
				pmap._layersMaxZoom = 30;
				pmap.options.maxZoom = 30;
				var newbounds = geojson_layer.getBounds();
				pmap.fitBounds(newbounds);
			}
		});
	};
	
	
	/**************************************************
	 * Functions for HTML changes for loading maps
	 * and displaying map titles
	 *************************************************
	 */
	pmap.show_region_loading = function (){
		if (document.getElementById(pmap.map_title_dom_id)) {
			// show the loading script
			map.button_ready = false;
			var act_dom_id = pmap.map_title_dom_id;
			var loading = "<img style=\"margin-top:-4px;\" height=\"16\"  src=\"";
			loading += base_url + "/static/oc/images/ui/waiting.gif\" alt=\"Loading icon...\" />";
			loading += " Loading Regions...";
			document.getElementById(act_dom_id).innerHTML = loading;
			var act_dom_id = map.map_title_suffix_dom_id;
			document.getElementById(act_dom_id).innerHTML = "";
		}
	}
	
	this.pmap = pmap;
}
