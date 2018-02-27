/*
 * Map an individual item with GeoJSON
 */
var polyStyle = {
	"color": "#ff7800",
	"weight": 2,
	"opacity": 0.85,
	"fillOpacity": 0.5
 };

function localize_oc_uri(uri){
	var output = uri;
	if(typeof base_url != 'undefined'){
		if(uri.indexOf('http://opencontext.org') === 0){
			len_uri = uri.length;
			output = base_url + uri.substring(22, len_uri);
		}
	}
	return output;
}

function initmap() {
    maxZoom = 25;
	
	map = L.map('map').setView([start_lat, start_lon], start_zoom); //map the map
	map.fit_bounds = false;
	bounds = new L.LatLngBounds();
	var osmTiles = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
	    attribution: '&copy; <a href="https://osm.org/copyright">OpenStreetMap</a> contributors',
		maxZoom: maxZoom,
		maxNativeZoom: 18
	});
   
	var mapboxTiles = L.tileLayer('https://api.tiles.mapbox.com/v3/ekansa.map-tba42j14/{z}/{x}/{y}.png', {
		attribution: '&copy; <a href="https://MapBox.com">MapBox.com</a> ',
		maxZoom: maxZoom,
		maxNativeZoom: 18
	});
   
	var ESRISatelliteTiles = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
		attribution: '&copy; <a href="https://services.arcgisonline.com/">ESRI.com</a> ',
		maxZoom: maxZoom,
		maxNativeZoom: 19
	});
   
	var gmapRoad = new L.Google('ROADMAP');
	gmapRoad.maxZoom = maxZoom;
	gmapRoad.maxNativeZoom = 18;
	var gmapSat = new L.Google('SATELLITE');
	gmapSat.maxZoom = 20;
	gmapSat.maxNativeZoom = 18;
	var gmapTer = new L.Google('TERRAIN');
    gmapTer.maxNativeZoom = 19;
	gmapTer.maxZoom = 20;
   
	var baseMaps = {
		"Google-Terrain": gmapTer,
		"Google-Satellite": gmapSat,
		"ESRI-Satellite": ESRISatelliteTiles,
		"Google-Roads": gmapRoad,
		"OpenStreetMap": osmTiles,
		"MapBox": mapboxTiles,
	};
    
	// useful for seeting zooms. If only points, then we want to zoom
	// further away
	var point_features_only = true;
	
	function on_each_feature(feature, layer){
		// map popup function
		console.log(feature);
		if(feature.geometry.type != 'Point' && feature.geometry.type != 'point'){
			// we have features that aren't point, so do not do a big zoom out
			point_features_only = false;
		}
		if (feature.properties) {
			var props = feature.properties;
			var loc_note = '';
			var loc_note_html = '';
			if('location-note' in props){
				loc_note += props['location-note']+ ' ';
			}
			else{
				if('location-region-note' in props){
					loc_note += props['location-region-note'] + ' ';
				}
			}
			if('reference-type' in props){
				if (props['reference-type'] == 'inferred'){
					if('reference-label' in props && 'reference-uri' in props){
						var uri = localize_oc_uri(props['reference-uri']);
						loc_note_html = [
							'<dl>',
							'<dt>Location Inferred from:</dt>',
							'<dd>',
							'<a href="' + uri + '" target="_blank">',
							props['reference-label'] + '</a>',
							'</dd>',
							'<dt>Location Note:</dt>',
							'<dd>',
							loc_note,
							'</dd>',
						].join("\n");
					}
				}
				else{
					if('location-precision-note' in props){
						loc_note += props['location-precision-note'] + ' ';
					}
					var loc_info = 'This item has its own location data.';
					if(typeof item_type != 'undefined'){
						if(item_type == 'projects'){
							loc_info = 'Summarizing locations in this project';
						}
					}
					loc_note_html = [
						'<dl>',
						'<dt>Location:</dt>',
						'<dd>',
						loc_info,
						'</dd>',
						'<dt>Location Note:</dt>',
						'<dd>',
						loc_note,
						'</dd>',
					].join("\n");
				}
			}
			
			
			var popupContent = [
			'<div>',
			loc_note_html,
			'</div>'].join("\n");
			layer.bindPopup(popupContent);
		}
	}
	
	map.addLayer(gmapSat);
	map._layersMaxZoom = 30;
	L.control.layers(baseMaps).addTo(map);
	var act_layer = L.geoJson(geojson, {
		style: polyStyle,
		onEachFeature: on_each_feature
		}
	);
	map.fitBounds(act_layer.getBounds());
	// set zooom controls appropriately
	map.removeLayer(gmapSat);
	map.addLayer(osmTiles);
	map.removeLayer(osmTiles);
	map.addLayer(gmapSat);
	map.zoomOut(2);
	var current_zoom = map.getZoom();
	if (current_zoom > start_zoom && point_features_only){
		// we are zoomed into far, so go out
		map.setZoom(start_zoom);
	}
	if (current_zoom < 1){
		map.setZoom(1);
	}
	act_layer.addTo(map);
}