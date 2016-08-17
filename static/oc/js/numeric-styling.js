/*
 * Javascript for generating color gradients useful for
 * charts and mapping
 */


function hex (c) {
	// converts decimal to hexidecimal value
	var s = "0123456789abcdef";
	var i = parseInt (c);
	if (i == 0 || isNaN (c))
	  return "00";
	i = Math.round (Math.min (Math.max (0, i), 255));
	return s.charAt ((i - i % 16) / 16) + s.charAt (i % 16);
}
 
function convertToHex (rgb) {
	// converts rgb list to a hexidecimal string value
	return hex(rgb[0]) + hex(rgb[1]) + hex(rgb[2]);
}

function RGBtoHex(c) {
	// conversts RGB values to hex
   var m = /rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)/.exec(c);
   return m ? (1 << 24 | m[1] << 16 | m[2] << 8 | m[3]).toString(16).substr(1) : c;
}

function trim (s) {
	// Remove '#' in color hex string
	return (s.charAt(0) == '#') ? s.substring(1, 7) : s
}

function convertToRGB (hex) {
	// Convert hexidecimal color string to an RGB list value
	var color = new Array();
	color[0] = parseInt ((trim(hex)).substring (0, 2), 16);
	color[1] = parseInt((trim(hex)).substring (2, 4), 16);
	color[2] = parseInt((trim(hex)).substring (4, 6), 16);
	return color;
}



function numericStyle(){
	// 	makes an object that assigns colors and opacity
	var base_opacity = .75
	this.base_opacity = base_opacity
	
	//starting default gradient colors from low to high
	var gradient_colors = [
		convertToRGB('#FFFF66'),
		convertToRGB('#FF3300'),
		convertToRGB('#5A0000')
    ];
	
	this.gradient_colors = gradient_colors;
	this.hex_prefix = '#'; // for making a hex color, add the prefix
	this.min_value = 0;
	this.max_value = 1;
	this.act_value = .5;
	
	this.reset_gradient_colors = function(color_list){
		if (color_list.length == 3) {
			this.gradient_colors = [convertToRGB(color_list[0]),
					        convertToRGB(color_list[1]),
					        convertToRGB(color_list[2])];
		}
	}
	
	this.generate_color = function(){
		// does the actual work of making the color
		var value_span = this.max_value - this.min_value;
		if (value_span != 0) {
			var proportion = this.act_value / value_span;
		}
		else{
			var proportion = 1;
		}
		
		var color = new Array();
		if (proportion >= .5) {
			// active value is greater than the mid-point
			var start_color = this.gradient_colors[1];
			var end_color = this.gradient_colors[2];
			var color_proportion = 1 - ((1 - proportion) * 2);
		}
		else{
			// active value is less than the mid point
			var start_color = this.gradient_colors[0];
			var end_color = this.gradient_colors[1];
			var color_proportion = 1 - ((.5 - proportion) * 2);
		}
		
		color[0] = start_color[0] + Math.round((end_color[0] - start_color[0]) * color_proportion);
		color[1] = start_color[1] + Math.round((end_color[1] - start_color[1]) * color_proportion);
		color[2] = start_color[2] + Math.round((end_color[2] - start_color[2]) * color_proportion);
		
		return color;
	}
	
	this.generate_hex_color = function(){
		// makes a color in hex format
		var color = this.generate_color();
		return this.hex_prefix + convertToHex(color);
	}
	
	this.generate_opacity = function(){
		// makes an opacity value based in numeric ranges
		
		var value_span = this.max_value - this.min_value;
		if (value_span != 0) {
			var proportion = this.act_value / value_span;
		}
		else{
			var proportion = 1;
		}
		var opacity =  Math.round(this.base_opacity * Math.sqrt(proportion)+ (this.base_opacity * .5 * Math.sqrt(proportion *.3)), 2);
		opacity += .2;
		
		if(opacity > this.base_opacity){
			opacity = this.base_opacity;
		}
		
		return opacity
	}
}