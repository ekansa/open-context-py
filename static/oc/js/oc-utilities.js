/*
 * Javascript for commonly needed utilities
 * in charting and mapping
 */
function replaceURLparameter(url, parameter, replace) {
    //prefer to use l.search if you have a location/link object
    var urlparts= url.split('?');   
    if (urlparts.length>=2) {

        var prefix= encodeURIComponent(parameter)+'=';
        var pars= urlparts[1].split(/[&;]/g);

        //reverse iteration as may be destructive
        for (var i= pars.length; i-- > 0;) {    
            //idiom for string.startsWith
            if (pars[i].lastIndexOf(prefix, 0) !== -1) {  
                pars.splice(i, 1);
            }
        }
        url= urlparts[0]+'?'+pars.join('&');
	url += '&';
    }
    else {
	url += '?';
    }
    url += encodeURIComponent(parameter) + '=' + encodeURIComponent(replace);
    return url;
}

function removeURLParameter(url, parameter) {
    //prefer to use l.search if you have a location/link object
    var urlparts= url.split('?');   
    if (urlparts.length>=2) {

        var prefix= encodeURIComponent(parameter)+'=';
        var pars= urlparts[1].split(/[&;]/g);

        //reverse iteration as may be destructive
        for (var i= pars.length; i-- > 0;) {    
            //idiom for string.startsWith
            if (pars[i].lastIndexOf(prefix, 0) !== -1) {  
                pars.splice(i, 1);
            }
        }

        url= urlparts[0]+'?'+pars.join('&');
        return url;
    } else {
        return url;
    }
}

function getURLParameter(url, param) {
    //prefer to use l.search if you have a location/link object
    var vars = {};
	url.replace( 
		/[?&]+([^=&]+)=?([^&]*)?/gi, // regexp
		function( m, key, value ) { // callback
			key = key.replace('amp;', '');
			vars[key] = value !== undefined ? value : '';
		}
	);

	if ( param ) {
		return vars[param] ? vars[param] : null;	
	}
	return vars;
}

function parseUrl() {
	// parse a URL
	var query = location.search.substr(1);
	var result = {};
	query.split("&").forEach(function(part) {
		var item = part.split("=");
		result[item[0]] = decodeURIComponent(item[1]);
	});
	return result;
}



var getCentroid = function (arr) {
	// get the centroid of a polygon
	return arr.reduce(function (x,y) {
	    return [x[0] + y[0]/arr.length, x[1] + y[1]/arr.length] 
	}, [0,0]) 
}

function make_unique_count_key(count_key, count_list) {
	if (count_key in count_list) {
		count_key = make_unique_count_key(count_key - .0001, count_list);
	}
	return count_key;
}

function style_bce_ce_year(date_num){
	//styles a year BCE / CE
	if (date_num == false) {
		output = '(recent)';
	}
	else{
		if (date_num < 0) {
			output = (date_num * -1) + ' BCE';
		}
		else{
			output = date_num + ' CE';
		}	
	}
	return output;
}