const COLOR_GRADIENTS = {
	black_aqua_white: [
		{v: 0, color: '#000000', },
		{v: 0.5, color: '#00FFFF', },
		{v: 1, color: '#FFFFFF', },
	],
	blue_red: [
		{v: 0, color: '#0000FF', },
		{v: 1, color: '#FF0000', },
	],
	blue_red_5: [
		{v: 0, color: '#0000FF', },
		{v: 0.25, color: '#00FFFF', },
		{v: 0.5, color: '#008000', },
		{v: 0.75, color: '#FFFF00', },
		{v: 1, color: '#FF0000', },
	],
	incandescent: [
		{v: 0, color: '#000000', },
		{v: 0.33, color: '#290000', },
		{v: 0.66, color: '#FFFF00', },
		{v: 1, color: '#FFFFFF', },
	],
	heated_metal: [
		{v: 0, color: '#000000', },
		{v: 0.4, color: '#800080', },
		{v: 0.6, color: '#FF0000', },
		{v: 0.8, color: '#FFFF00', },
		{v: 1, color: '#FF0000', },
	],
	sunrise: [
		{v: 0, color: '#FF0000', },
		{v: 0.667, color: '#FFFF00', },
		{v: 1, color: '#FFFFFF', },
	],
	sea: [
		{v: 0, color: '#3f2b96', },
		{v: 1, color: '#a8c0ff', },
	],
	sand_blue: [
		{v: 0, color: '#3E5151', },
		{v: 1, color: '#DECBA4', },
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