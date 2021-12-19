
function style_bce_ce_year(date_num, null_result){
	//styles a year BCE / CE
	let output = null;
	if (date_num == false || date_num == null) {
		return null_result;
	}
	if (date_num < 0) {
		output = (date_num * -1) + ' BCE';
	}
	else{
		output = date_num + ' CE';
	}	
	return output;
}


// Get nested object by a string of part3[0].name pattern.
Object.byString = function(o, s) {
    s = s.replace(/\[(\w+)\]/g, '.$1'); // convert indexes to properties
    s = s.replace(/^\./, '');           // strip a leading dot
    var a = s.split('.');
    for (var i = 0, n = a.length; i < n; ++i) {
        var k = a[i];
        if (k in o) {
            o = o[k];
        } else {
            return null;
        }
    }
    return o;
}

function safe_get_nested_object_by_str_key(some_obj, key_path_str){
	let output = null;
	if(some_obj == null){
		return output;
	}
	try {
		output = Object.byString(some_obj, key_path_str);
	}
	catch(err) {
		output = null;
	}
	return output;
}