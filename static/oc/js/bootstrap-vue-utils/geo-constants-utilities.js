/*
This configures Open Context geojson data visualization.
*/



// These are geojson feature properties for individual records
// that should be excluded from the UI and downloads.
const UI_RECORD_EXCLUDE_PROPERTY_KEYS = [
    'id',
    'feature-type',
    'href',
];

// These are geojson feature property keys (used in individual records)
// mapped to more human readable labels.
const UI_RECORD_PROPERTY_KEY_HUMAN_READABLE_MAPPINGS = {
    'uri': 'URI',
    'citation uri': 'Citation URI',
    'label': 'Item Label',
    'project label': 'Project',
    'project href': 'Project URI',
    'context label': 'Context',
    'context href': 'Context URI',
    'latitude': 'Latitude (WGS-84)',
    'longitude': 'Longitude (WGS-84)',
    'early bce/ce': 'Early BCE/CE',
    'late bce/ce': 'Late BCE/CE',
    'item category': 'Item Category',
    'thumbnail': 'Thumbnail',
    'snippet': 'Search-Term Snippet',
    'published': 'Published Date',
    'updated': 'Updated Date',
};

// These configure consolidation of label and URI fields
// to make hyperlinks in the user interface.
const UI_RECORD_PROPERTY_LINK_CONSOLIDATE = {
    'URI': null,
    'Item Label': 'URI',
    'Citation URI': 'Citation URI',
    'Project URI': null,
    'Project': 'Project URI',
    'Context URI': null,
    'Context': 'Context URI',
}


function skip_excluded_property_key(key){
    if(UI_RECORD_EXCLUDE_PROPERTY_KEYS.indexOf(key) >= 0){
        return true;
    }
    return false;
}

function map_property_key_to_field(key){
	if(UI_RECORD_PROPERTY_KEY_HUMAN_READABLE_MAPPINGS.hasOwnProperty(key)){
	   return UI_RECORD_PROPERTY_KEY_HUMAN_READABLE_MAPPINGS[key];
	}
	return key;
}


/*
Adapted from: https://github.com/consbio/Leaflet.ZoomBox
Developed with support from the South Atlantic Landscape Conservation 
Cooperative, and maintained with support from Peninsular Florida LCC 
and the U.S. Forest Service Northwest Regional Climate Hub.
Binding to the map's zoom box (shift-click) was inspired by ScanEx
*/
L.Control.ZoomBox = L.Control.extend({
    _active: false,
    _map: null,
    includes: L.Evented ? L.Evented.prototype : L.Mixin.Events,
    options: {
        position: 'topleft',
        addToZoomControl: false,
        content: "",
        className: "leaflet-zoom-box-icon",
        modal: false,
        title: "Zoom to specific area"
    },
    onAdd: function (map) {
        this._map = map;
        var separate_container = !map.zoomControl || !this.options.addToZoomControl;
        if (!separate_container) {
            this._container = map.zoomControl._container;
        } else {
            this._container = L.DomUtil.create('div', 'leaflet-zoom-box-control leaflet-bar');
        }
        this._link = L.DomUtil.create('a', this.options.className, this._container);
        this._link.title = this.options.title;
        this._link.innerHTML = this.options.content || "";
        this._link.href = "#";
        this._link.setAttribute('role', 'button');
        this._link.setAttribute('aria-pressed', 'false');

        // Bind to the map's boxZoom handler for mouse down
        var _origMouseDown = map.boxZoom._onMouseDown;
        map.boxZoom._onMouseDown = function(e){
            if (e.button === 2) return;  // prevent right-click from triggering zoom box
            _origMouseDown.call(map.boxZoom, {
                clientX: e.clientX,
                clientY: e.clientY,
                which: 1,
                shiftKey: true
            });
            // get lat lng points from the mouse event
            var box_point = map.mouseEventToLatLng(e);
            if(!map.boxZoom.hasOwnProperty('b_points')){
                map.boxZoom.b_points = [];
            }
            map.boxZoom.b_points.push(box_point);
            console.log('Add mouse down bounding box point');
            console.log(box_point);
        };

        // Bind to the map's boxZoom handler for mouse up
        var _origMouseUp = map.boxZoom._onMouseUp;
        map.boxZoom._onMouseUp = function(e){
            if (e.button === 2) return;  // prevent right-click from triggering zoom box
            _origMouseUp.call(map.boxZoom, {
                clientX: e.clientX,
                clientY: e.clientY,
                which: 1,
                shiftKey: true
            });
            // get lat lng points from the mouse event
            var box_point = map.mouseEventToLatLng(e);
            if(!map.boxZoom.hasOwnProperty('b_points')){
                map.boxZoom.b_points = [];
            }
            map.boxZoom.b_points.push(box_point);
            console.log('Add mouse up bounding box point');
            console.log(box_point);
        };

        map.on('zoomend', function(){
            if (map.getZoom() == map.getMaxZoom()){
                L.DomUtil.addClass(this._link, 'leaflet-disabled');
                this._link.setAttribute('aria-disabled', 'true');
            }
            else {
                L.DomUtil.removeClass(this._link, 'leaflet-disabled');
                this._link.removeAttribute('aria-disabled');
            }

            console.log('finished zoom');
            console.log(map.boxZoom);
            let ok_search = false;
            if (map.boxZoom.hasOwnProperty('b_points')) {
                console.log('Prepare bbox query');
                console.log(map.boxZoom.b_points);
                if(map.boxZoom.b_points.length >=2 ){
                    ok_search = true;
                }
            }
            if(ok_search){
                let min_lat = map.boxZoom.b_points[0].lat;
                let min_lng = map.boxZoom.b_points[0].lng;
                let max_lat = map.boxZoom.b_points[0].lat;
                let max_lng = map.boxZoom.b_points[0].lng;
                for (let act_point of map.boxZoom.b_points){
                    if (act_point.lat < min_lat) {
                        min_lat = act_point.lat;
                    }
                    if (act_point.lng < min_lng) {
                        min_lng = act_point.lng;
                    }
                    if (act_point.lat > max_lat) {
                        max_lat = act_point.lat;
                    }
                    if (act_point.lng > max_lng) {
                        max_lng = act_point.lng;
                    }    
                }
                let bbox_query = [min_lng, min_lat, max_lng, max_lat].join(',');
                console.log('bbox_query is: ' + bbox_query);
                if (!map.hasOwnProperty('update_with_bbox_query')) {
                    console.log('Cannot find query method');
                    return null;
                }
                map.update_with_bbox_query(bbox_query);
                return null;
            }
        }, this);
        if (!this.options.modal) {
            map.on('boxzoomend', this.deactivate, this);
        }

        L.DomEvent
            .on(this._link, 'dblclick', L.DomEvent.stop)
            .on(this._link, 'click', L.DomEvent.stop)
            .on(this._link, 'mousedown', L.DomEvent.stopPropagation)
            .on(this._link, 'click', function(){
                this._active = !this._active;
                if (this._active && map.getZoom() != map.getMaxZoom()){
                    this.activate();
                }
                else {
                    this.deactivate();
                }
            }, this);
        return this._container;
    },
    activate: function() {
        L.DomUtil.addClass(this._link, 'active');
        this._map.dragging.disable();
        this._map.boxZoom.addHooks();
        L.DomUtil.addClass(this._map.getContainer(), 'leaflet-zoom-box-crosshair');
        this._link.setAttribute('aria-pressed', 'true');
    },
    deactivate: function() {
        L.DomUtil.removeClass(this._link, 'active');
        this._map.dragging.enable();
        this._map.boxZoom.removeHooks();
        L.DomUtil.removeClass(this._map.getContainer(), 'leaflet-zoom-box-crosshair');
        this._active = false;
        this._link.setAttribute('aria-pressed', 'false');
    }
});

L.control.zoomBox = function (options) {
  return new L.Control.ZoomBox(options);
};