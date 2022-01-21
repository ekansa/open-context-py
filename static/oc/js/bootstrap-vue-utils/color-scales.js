const COLOR_GRADIENTS = {
	gray: [
		{v: 0, color: '#000000', },
		{v: 1, color: '#FFFFFF', },
	],
	gray_inv: [
		{v: 0, color: '#FFFFFF', },
		{v: 1, color: '#000000', },
	],
	/*
	incandescent: [
		{v: 0, color: '#000000', },
		{v: 0.33, color: '#290000', },
		{v: 0.66, color: '#FFFF00', },
		{v: 1, color: '#FFFFFF', },
	],
	sand_blue: [
		{v: 0, color: '#3E5151', },
		{v: 1, color: '#DECBA4', },
	],
	black_aqua_white: [
		{v: 0, color: '#000000', },
		{v: 0.5, color: '#00FFFF', },
		{v: 1, color: '#FFFFFF', },
	],
	*/
	// #d3f2a3,#97e196,#6cc08b,#4c9b82,#217a79,#105965,#074050
	emrld: [
		{v: 0, color: '#d3f2a3', },
		{v: 0.2, color: '#97e196', },
		{v: 0.4, color: '#6cc08b', },
		{v: 0.5, color: '#4c9b82', },
		{v: 0.6, color: '#217a79', },
		{v: 0.8, color: '#105965', },
		{v: 1, color: '#074050', },
	],
	geyser: [
		{v: 0, color: '#008080', },
		{v: 0.2, color: '#70a494', },
		{v: 0.4, color: '#b4c8a8', },
		{v: 0.5, color: '#f6edbd', },
		{v: 0.6, color: '#edbb8a', },
		{v: 0.8, color: '#de8a5a', },
		{v: 1, color: '#ca562c', },
	],
	fall: [
		{v: 0, color: '#3d5941', },
		{v: 0.2, color: '#778868', },
		{v: 0.4, color: '#b5b991', },
		{v: 0.5, color: '#f6edbd', },
		{v: 0.6, color: '#edbb8a', },
		{v: 0.8, color: '#de8a5a', },
		{v: 1, color: '#ca562c', },
	],
	temps: [
		{v: 0, color: '#009392', },
		{v: 0.2, color: '#39b185', },
		{v: 0.4, color: '#9ccb86', },
		{v: 0.5, color: '#e9e29c', },
		{v: 0.6, color: '#eeb479', },
		{v: 0.8, color: '#e88471', },
		{v: 1, color: '#cf597e', },
	],
	blue_red_5: [
		{v: 0, color: '#0000FF', },
		{v: 0.25, color: '#00FFFF', },
		{v: 0.5, color: '#008000', },
		{v: 0.75, color: '#FFFF00', },
		{v: 1, color: '#FF0000', },
	],
	blue_red: [
		{v: 0, color: '#0000FF', },
		{v: 1, color: '#FF0000', },
	],
	heated_metal: [
		{v: 0, color: '#000000', },
		{v: 0.4, color: '#800080', },
		{v: 0.6, color: '#FF0000', },
		{v: 0.8, color: '#FFFF00', },
		{v: 1, color: '#FFFFFF', },
	],
	sunrise: [
		{v: 0, color: '#FF0000', },
		{v: 0.667, color: '#FFFF00', },
		{v: 1, color: '#FFFFFF', },
	],
	sunset_dark: [
		{v: 0, color: '#fcde9c', },
		{v: 0.2, color: '#faa476', },
		{v: 0.4, color: '#f0746e', },
		{v: 0.5, color: '#e34f6f', },
		{v: 0.6, color: '#dc3977', },
		{v: 0.8, color: '#b9257a', },
		{v: 1, color: '#7c1d6f', },
	],
	legacy_oc: [
		{v: 0, color: '#FFFF66', },
		{v: 0.5, color: '#FF3300', },
		{v: 1, color: '#5A0000', },
	]
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
