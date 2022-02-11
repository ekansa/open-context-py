
const Vue = require('vue');
import { BootstrapVue, IconsPlugin } from 'bootstrap-vue'

// Import Bootstrap an BootstrapVue CSS files (order is important)
import 'bootstrap/dist/css/bootstrap.css'
import 'bootstrap-vue/dist/bootstrap-vue.css'

// Vue and Bootstrap additional add ons
import VueRouter from 'vue-router'

// import VueTypeaheadBootstrap from 'vue-typeahead-bootstrap'
import VueCookies from 'vue-cookies'
import ApexCharts from 'apexcharts'
import VueApexCharts from 'vue-apexcharts'


// Map related imports
// See: https://github.com/Leaflet/Leaflet.markercluster/issues/874
import 'leaflet';
const L = window['L'];

import * as Vue2Leaflet from 'vue2-leaflet';

import easyButton from 'leaflet-easybutton'
L.easyButton = easyButton;
import h337 from 'heatmapjs'
import HeatmapOverlay from 'leaflet-heatmap'



var oc_colors = require('./oc_js/color-scales');
var oc_utils = require('./oc_js/general-utilities');
var goog_mutant = require('./oc_js/GoogleMutant');
var oc_url_utils = require('./oc_js/url-utilities');


// Make BootstrapVue available throughout your project
Vue.use(BootstrapVue)
// Optionally install the BootstrapVue icon components plugin
Vue.use(IconsPlugin)

// Use the imported addons
Vue.use(VueCookies)
Vue.use(VueApexCharts)
