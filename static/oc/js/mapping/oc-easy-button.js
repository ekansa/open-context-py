L.Control.EasyButtons = L.Control.extend({
    // slight extension of the easy button Leaflet plugin to
    // enable creation of grouped buttons
    options: {
        position: 'topleft',
        title: '',
        intentedIcon: 'fa-circle-o',
        buttonContainerDom: false
    },

    onAdd: function () {
        if (this.options.buttonContainerDom == false) {
            var container = L.DomUtil.create('div', 'leaflet-bar leaflet-control');
        }
        else{
            var container = this.options.buttonContainerDom; 
        }

        this.link = L.DomUtil.create('a', 'leaflet-bar-part', container);
        this._addImage()
        this.link.href = '#';

        L.DomEvent.on(this.link, 'click', this._click, this);
        this.link.title = this.options.title;

        return container;
    },

    intendedFunction: function(){ alert('no function selected');},

    _click: function (e) {
        L.DomEvent.stopPropagation(e);
        L.DomEvent.preventDefault(e);
        this.intendedFunction();
    },

    _addImage: function () {
        var extraClasses = this.options.intentedIcon.lastIndexOf('fa', 0) === 0 ? ' fa fa-lg' : ' glyphicon';

        L.DomUtil.create('i', this.options.intentedIcon + extraClasses, this.link);
    }
});

L.easyButton = function( btnIcon , btnFunction , btnTitle , btnContainer, btnMap ) {
  var newControl = new L.Control.EasyButtons;
  if (btnIcon) newControl.options.intentedIcon = btnIcon;

  if ( typeof btnFunction === 'function'){
    newControl.intendedFunction = btnFunction;
  }

  if (btnTitle) newControl.options.title = btnTitle;

  if (btnContainer) {
    // added for open context
    newControl.options.buttonContainerDom = btnContainer;
  }
  if ( btnMap == '' ){
    // skip auto addition
  } else if ( btnMap ) {
    btnMap.addControl(newControl);
  } else {
    map.addControl(newControl);
  }
  return newControl;
};
