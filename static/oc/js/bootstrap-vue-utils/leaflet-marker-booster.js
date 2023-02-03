// This javacript file is from: https://github.com/oliverheilig/leaflet-marker-booster
// Author: Oliver Heilig (released under a ISC License)


// override Leaflet implementation for fast symbol rendering
(function () {
	'use strict';

	var proto = L.Canvas.prototype;
	var prev = proto._updateCircle;

	proto._updateCircle = function (layer) {
		// only circleMARKER, not the standard circle
		if (layer instanceof L.Circle)
			return prev.call(this, layer);

		if (!this._drawing || layer._empty()) {
			return;
		}

		var p = layer._point,
		    ctx = this._ctx,
		    r = Math.max(Math.round(layer._radius), 1),
		    s = (Math.max(Math.round(layer._radiusY), 1) || r) / r;

		var options = layer.options;

		var scale = Math.pow(2, this._map.getZoom()) * 256 / Math.PI / 6378137;
		scale = Math.pow(scale, options.boostExp) * options.boostScale;
		r = r * scale;

		if(!options.boostType) {
			ctx.beginPath();
			ctx.arc(p.x, p.y, r, 0, Math.PI * 2, false);
			this._fillStroke(ctx, layer);
		}
		else switch (options.boostType) {
			case 'ball':
				if (options.fill) {
					if(options.stroke && options.weight !== 0)
						r = r + options.weight * 0.5 * scale;
					var grd = ctx.createRadialGradient(p.x - r/2, p.y - r/2, 0, p.x, p.y, 1.5 * r);
					grd.addColorStop(0, options.fillColor);
					grd.addColorStop(1, options.color);
					ctx.beginPath();
					ctx.fillStyle = grd;
					ctx.arc(p.x, p.y,  r, 0, Math.PI * 2, false);
					ctx.fill(options.fillRule || 'evenodd');
				}
				break;
			case 'balloon':
				if (options.fill) {
					if(options.stroke && options.weight !== 0)
						r = r + options.weight * 0.5 * scale;
					var grd = ctx.createRadialGradient(p.x - r/2, p.y - r/2 - 2*r, 0, p.x, p.y - 2*r, 2.5 * r);
					grd.addColorStop(0, options.fillColor);
					grd.addColorStop(1, options.color);
					ctx.beginPath();
					ctx.fillStyle = grd;
					ctx.moveTo(p.x, p.y);
					ctx.lineTo(p.x - r, p.y-2*r);
					ctx.lineTo(p.x + r, p.y-2*r);
					ctx.lineTo(p.x, p.y);
					ctx.arc(p.x, p.y - 2*r,  r, 0, Math.PI * 2, false);
					ctx.closePath();
					ctx.fill(options.fillRule = 'nonzero');
				}
				break;
			default:
				if (options.stroke && options.weight !== 0) {
					ctx.beginPath();
					ctx.arc(p.x, p.y, r + options.weight * 0.5 * scale, 0, Math.PI * 2, false);
					ctx.fillStyle = options.color;
					ctx.fill(options.fillRule || 'evenodd');
				}

				if (options.fill) {
					ctx.beginPath();
					ctx.arc(p.x, p.y, r - ((options.stroke && options.weight !== 0) ? options.weight * 0.5 * scale : 0), 0, Math.PI * 2, false);
					ctx.fillStyle = options.fillColor || options.color;
					ctx.fill(options.fillRule || 'evenodd');
				}
		}
	};

	var xproto = L.CircleMarker.prototype;
	var xprev = xproto._containsPoint;

	xproto._containsPoint = function (p) {
		if (this instanceof L.Circle)
			return xprev.call(this, p);

		var r = this._radius;

		var options = this.options;

		var scale = Math.pow(2, this._map.getZoom()) * 256 / Math.PI / 6378137;
		scale = Math.pow(scale, options.boostExp) * options.boostScale;
		r = r * scale;
		r = r + (this.options.stroke ? this.options.weight * scale / 2 : 0);

		if(options.boostType === 'balloon')
			p = new L.Point(p.x, p.y + 2 * r);

		return p.distanceTo(this._point) <= r + this._clickTolerance();
		// clickTolerance only for mobile! (seems to be fixed with LL1.4)
		// return p.distanceTo(this._point) <= r + ((L.Browser.touch && L.Browser.mobile) ? 10 : 0);
	};

	var cproto = L.Layer.prototype;
	var cprev = cproto._openPopup;
	cproto._openPopup = function (e) {
		var layer = e.layer || e.target;

		if (!(layer instanceof L.CircleMarker) || (layer instanceof L.Circle))
			return cprev.call(this, e);

		if (!this._popup) {
			return;
		}

		if (!this._map) {
			return;
		}

		// prevent map click
		L.DomEvent.stop(e);

		// treat it like a marker and figure out
		// if we should toggle it open/closed
		if (this._map.hasLayer(this._popup) && this._popup._source === layer) {
			this.closePopup();
		} else {
			this.openPopup(layer || e.target, layer._latlng);
			layer.on('preclick', L.DomEvent.stopPropagation);
		}
	};

	var pproto = L.Popup.prototype;
	var p_getAnchor = pproto._getAnchor;
	pproto._getAnchor = function () {
		if (!(this._source instanceof L.CircleMarker) || this._source instanceof L.Circle)
			return p_getAnchor.call(this);

		var r = this._source._radius;

		var options = this._source.options;

		var zoomScale;
		var scale = Math.pow(2, this._map.getZoom()) * 256 / Math.PI / 6378137;
		scale = Math.pow(scale, options.boostExp) * options.boostScale;

		if(options.boostType === 'balloon')
			r = 2.5 * r * scale;
		else
			r = 0.5 * r * scale;

		// Where should we anchor the popup on the source layer?
		return L.point(this._source && this._source._getPopupAnchor ? this._source._getPopupAnchor() : [0, -r]);
	};
})();