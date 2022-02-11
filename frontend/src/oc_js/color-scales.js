/*
This list of available color gradients is informed by
recommendations for color choices developed by data visualization
experts (considering perception, variation in human color
sensitivity, etc.).

For more, see: 
https://www.thinkingondata.com/something-about-viridis-library/
https://academy.datawrapper.de/article/140-what-to-consider-when-choosing-colors-for-data-visualization

*/

const COLOR_GRADIENTS = {
	viridis: [
		{v: 0, color: '#fde725', },
		{v: 0.15, color: '#90d743', },
		{v: 0.35, color: '#35b779', },
		{v: 0.5, color: '#21918c', },
		{v: 0.65, color: '#31688e', },
		{v: 0.85, color: '#443983', },
		{v: 1, color: '#440154', },
	],
	emrld: [
		{v: 0, color: '#d3f2a3', },
		{v:0.15, color: '#97e196', },
		{v:0.35, color: '#6cc08b', },
		{v: 0.5, color: '#4c9b82', },
		{v:0.65, color: '#217a79', },
		{v:0.85, color: '#105965', },
		{v: 1, color: '#074050', },
	],
	geyser: [
		{v: 0, color: '#008080', },
		{v:0.15, color: '#70a494', },
		{v:0.35, color: '#b4c8a8', },
		{v: 0.5, color: '#f6edbd', },
		{v:0.65, color: '#edbb8a', },
		{v:0.85, color: '#de8a5a', },
		{v: 1, color: '#ca562c', },
	],
	temps: [
		{v: 0, color: '#009392', },
		{v:0.15, color: '#39b185', },
		{v:0.35, color: '#9ccb86', },
		{v: 0.5, color: '#e9e29c', },
		{v:0.65, color: '#eeb479', },
		{v:0.85, color: '#e88471', },
		{v: 1, color: '#cf597e', },
	],
	turbo: [
		{v: 0, color: '#30123b', },
		{v: 0.2, color: '#4661d6', },
		{v: 0.3, color: '#37a8fa', },
		{v: 0.4, color: '#1ae4b6', },
		{v: 0.5, color: '#71fe5f', },
		{v: 0.6, color: '#c8ef34', },
		{v: 0.7, color: '#faba39', },
		{v: 0.8, color: '#f56918', },
		{v: 0.9, color: '#ca2a04', },
		{v: 1, color: '#7a0403', },
	],
	plasma: [
		{v: 0, color: '#f0f921', },
		{v:0.15, color: '#fdb42f', },
		{v:0.35, color: '#ed7953', },
		{v: 0.5, color: '#cc4778', },
		{v:0.65, color: '#9c179e', },
		{v:0.85, color: '#5c01a6', },
		{v: 1, color: '#0d0887', },
	],
	inferno: [
		{v: 0, color: '#fcffa4', },
		{v:0.15, color: '#fbb61a', },
		{v:0.35, color: '#ed6925', },
		{v: 0.5, color: '#bc3754', },
		{v:0.65, color: '#781c6d', },
		{v:0.85, color: '#320a5e', },
		{v: 1, color: '#000004', },
	],
	sunset_dark: [
		{v: 0, color: '#fcde9c', },
		{v:0.15, color: '#faa476', },
		{v:0.35, color: '#f0746e', },
		{v: 0.5, color: '#e34f6f', },
		{v:0.65, color: '#dc3977', },
		{v:0.85, color: '#b9257a', },
		{v: 1, color: '#7c1d6f', },
	],
	blue_pink: [
		{v: 0, color: '#edf8fb', },
		{v:0.15, color: '#bfd3e6', },
		{v:0.35, color: '#9ebcda', },
		{v: 0.5, color: '#8c96c6', },
		{v:0.65, color: '#8c6bb1', },
		{v:0.85, color: '#88419d', },
		{v: 1, color: '#6e016b', },
	],
	oc: [
		{v: 0, color: '#ffffb2', },
		{v:0.15, color: '#fed976', },
		{v:0.35, color: '#feb24c', },
		{v: 0.5, color: '#fd8d3c', },
		{v:0.65, color: '#fc4e2a', },
		{v:0.85, color: '#e31a1c', },
		{v: 1, color: '#b10026', },
	],
	gray: [
		{v: 0, color: '#000001', },
		{v: 1, color: '#FFFFFF', },
	],
	gray_inv: [
		{v: 0, color: '#FFFFFF', },
		{v: 1, color: '#000001', },
	],
};


function hex (c) {
	// converts decimal to hexidecimal value
	var s = "0123456789abcdef";
	var i = parseInt (c);
	if (i == 0 || isNaN (c))
	  return "00";
	i = Math.round (Math.min (Math.max (0, i), 255));
	return s.charAt((i - i % 16) / 16) + s.charAt (i % 16);
}
 
function convertToHex (rgb) {
	// converts rgb list to a hexadecimal string value
	return hex(rgb[0]) + hex(rgb[1]) + hex(rgb[2]);
}

function RGBtoHex(c) {
	// converts RGB values to hex
   var m = /rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)/.exec(c);
   return m ? (1 << 24 | m[1] << 16 | m[2] << 8 | m[3]).toString(16).substr(1) : c;
}

function trim (s) {
	// Remove '#' in color hex string
	return (s.charAt(0) == '#') ? s.substring(1, 7) : s
}

function convertToRGB (hex) {
	// Convert hexadecimal color string to an RGB list value
	var color = new Array();
	color[0] = parseInt ((trim(hex)).substring (0, 2), 16);
	color[1] = parseInt((trim(hex)).substring (2, 4), 16);
	color[2] = parseInt((trim(hex)).substring (4, 6), 16);
	return color;
}


function make_hex_color_in_gradient(act_p, gradient_list){
	// act_p is a float between 0 and 1.
	// gradient_list is a list of objects with:
	// {v:associated_value (0-1 scale), color:hex_color}
	if((act_p < 0) || (act_p > 1)){
		return null;
	}
	let low_color = gradient_list[0];
	let high_color = gradient_list.slice(-1)[0];
	for(let conf_color of gradient_list){
		if(act_p >= conf_color.v && conf_color.v > low_color.v){
			low_color = conf_color;
		}
		if(act_p <= conf_color.v && conf_color.v < high_color.v){
			high_color = conf_color;
		}
	}
	if(low_color.v == high_color.v){
		return low_color.color;
	}
	
    let color_p =  act_p / high_color.v;
	let low_rgb = convertToRGB(low_color.color);
	let high_rgb = convertToRGB(high_color.color);
	
	let act_rgb = new Array();
	for (let i = 0; i < 3; i++) {
		act_rgb[i] = low_rgb[i] + Math.round((high_rgb[i] - low_rgb[i]) * color_p);
	}
	return '#' + convertToHex(act_rgb);
}
