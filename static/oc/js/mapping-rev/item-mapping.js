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
	
	map = L.map('map').setView([start_lat, start_lon], start_zoom); //map the map
	map.fit_bounds = false;
	bounds = new L.LatLngBounds();
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
	
	// add project layers if they exist
	var overlayImages = false;
	if (typeof project_layers != "undefined" && project_layers !== false){
		// we have project layers
		var img_layer_cnt = 0;
		for (var i = 0, length = project_layers.overlays.length; i < length; i++) {
			// L.imageOverlay(imageUrl, imageBounds)
			var act_over = project_layers.overlays[i];
			if('url' in act_over && 'metadata' in act_over && 'Leaflet' in act_over.metadata){
				var meta = act_over.metadata.Leaflet;
				if('bounds' in meta){
					img_layer_cnt++;
					if(overlayImages === false){
						overlayImages = {};
					}
					var img_label = 'Project Layer ' + img_layer_cnt;
					if('label' in meta){
						img_label = meta.label;
					}
					var img_opacity = 0.9;
					if('opacity' in meta){
						img_opacity = meta.opacity;
					}
					// Coordinates need to be in the lat-lon order (not GeoJSON order)
					// meta.bounds = [[11.4019, 43.1523], [11.4033, 43.1531]]; (does not work)
					// meta.bounds = [[43.153660, 11.402448],[43.152420, 11.400873]]; works
					img_over = L.imageOverlay(act_over.url, meta.bounds);
					img_over.id = img_layer_cnt;
					img_over.img_label = img_label;
					img_over.setOpacity(img_opacity);
					overlayImages[img_label] = img_over;
					img_over.addTo(map);
					
					// now set the zoom to be a bit further out from the overlay
					map.fitBounds(img_over.getBounds());
					if(start_zoom < (map.getZoom() - 1)){
						start_zoom = map.getZoom() - 1;
					}
				}	
			}
		}
	}
	
	
	if(overlayImages !== false){
		// we have overlay images to add
		
		L.control.layers(baseMaps, overlayImages).addTo(map);
	}
	else{
		// normal case, no project overlay images
		L.control.layers(baseMaps).addTo(map);
	}
	
	
	var act_layer = L.geoJson(geojson, {
		style: polyStyle,
		onEachFeature: on_each_feature
		}
	);
	if(point_features_only === false){
		map.fitBounds(act_layer.getBounds());
		// map.zoomOut(1);
	}
	
	act_layer.addTo(map);
	var current_zoom = map.getZoom();
	if (current_zoom > start_zoom && point_features_only){
		// we are zoomed into far, so go out
		map.setZoom(start_zoom);
	}
	if (current_zoom < 1){
		map.setZoom(1);
	}
}