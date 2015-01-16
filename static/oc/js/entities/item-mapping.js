/*
 * Map an individual item with GeoJSON
 */
var polyStyle = {
	"color": "#ff7800",
	"weight": 2,
	"opacity": 0.85,
	"fillOpacity": 0.5
 };

function initmap() {
     
	map = L.map('map').setView([start_lat, start_lon], start_zoom); //map the map
	bounds = new L.LatLngBounds();
	var osmTiles = L.tileLayer('http://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
	    attribution: '&copy; <a href="http://osm.org/copyright">OpenStreetMap</a> contributors'
	});
   
	var mapboxTiles = L.tileLayer('http://api.tiles.mapbox.com/v3/ekansa.map-tba42j14/{z}/{x}/{y}.png', {
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
		"MapBox": mapboxTiles,
	};
  
	map.addLayer(gmapSat);
	map._layersMaxZoom = 20;
	L.control.layers(baseMaps).addTo(map);
	L.geoJson(geojson, {style: polyStyle}).addTo(map)
}