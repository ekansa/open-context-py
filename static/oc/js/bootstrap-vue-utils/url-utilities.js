/*
These are functions needed to play with the URLs returned
by the Open Context search API so we can do useful things
in Vue templating.
*/

function remove_prefix(str, prefix){
    if(str.startsWith(prefix)){
         return str.slice(prefix.length);
    } else {
         return str;
    }
}

function abs_to_rel_url(url, base_url=''){
    return remove_prefix(url, base_url);
}

function make_url_variants(url){
    var urls = [url];
    var prefixes = [
         {f: 'http://', r: 'https://'},
         {f: 'https://', r: 'http://'},
         {f: 'oc-gen:', r: 'http://opencontext.org/'},
         {f: 'http://', r: 'https://'}, // for https variants of OC.
    ];
    for(let prefix_conf of prefixes){
         var new_url = url;
         if(url.startsWith(prefix_conf.f)){
              new_url = prefix_conf.r + remove_prefix(url, prefix_conf.f);
         }
         if(urls.indexOf(new_url) >= 0 ){
              continue;
         }
         urls.push(new_url);
    }
    return urls;
}



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


const SEARCH_FRAGMENT_KEYS = [
    'tab', // tab in view
    'aq', // active query
    'zm', // map zoom level
    'tilezm', // tie zoom level
    'lat', // map lat
    'lon', // map lon
    'geovis', // map visualization type
    'tiles', // base map tile type
];

const FRAG_KEY_DELIM = '/';
const FRAG_KEY_VAL_DEMIM = '=';

function parse_frag_dict(frag_str, allowed_keys){
    let frag_obj = {};
    let frag_parts = frag_str.split(FRAG_KEY_DELIM);
    for(let frag_part of frag_parts){
        let key_val = frag_part.split(FRAG_KEY_VAL_DEMIM);
        if(key_val.length != 2){
            continue;
        }
        let key = key_val[0];
        let val = key_val[1];
        if(allowed_keys.indexOf(key) < 0){
            console.log("Unknown frag key: " + key);
            continue;
        }
        frag_obj[key] = val;
    }
    return frag_obj;
}

function parse_search_frag_dict(frag_str){
    return parse_frag_dict(frag_str, SEARCH_FRAGMENT_KEYS);
}

function encode_frag_obj(frag_obj){
    let key_vals = [];
    for (let entry of Object.entries(frag_obj)) {
        let str_entry = entry.join(FRAG_KEY_VAL_DEMIM);
        key_vals.push(str_entry);
    }
    return key_vals.join(FRAG_KEY_DELIM);
}

function get_frag_key(key, frag_str, allowed_keys){
    let frag_obj = parse_frag_dict(frag_str, allowed_keys);
    if(key in frag_obj){
        return frag_obj[key];
    }
    return null;
}

function get_search_frag_key(key, frag_str){
    return get_frag_key(key, frag_str, SEARCH_FRAGMENT_KEYS);
}

function update_frag_str(key, val, frag_str, allowed_keys){
    let frag_obj = parse_frag_dict(frag_str, allowed_keys);
    if(allowed_keys.indexOf(key) < 0){
        return encode_frag_obj(frag_obj);
    }
    frag_obj[key] = val;
    return encode_frag_obj(frag_obj);
}

function update_search_frag_str(key, val, frag_str){
    return update_frag_str(key, val, frag_str, SEARCH_FRAGMENT_KEYS);
}

function get_current_frag_obj(allowed_keys){
    if(window.location.hash) {
        //Puts hash in variable, and removes the # character
        let frag_str = window.location.hash.substring(1);
        return parse_frag_dict(frag_str, allowed_keys);
    }
    else{
        return {};
    }
}

function get_search_current_frag_obj(){
    if(window.location.hash) {
        //Puts hash in variable, and removes the # character
        let frag_str = window.location.hash.substring(1);
        return parse_search_frag_dict(frag_str);
    }
    else{
        return {};
    }
}

function get_current_frag_key(key, allowed_keys){
    let frag_obj = get_current_frag_obj(allowed_keys);
    if(key in frag_obj){
        return frag_obj[key];
    }
    return null;
}

function get_search_current_frag_key(key){
    let frag_obj = get_search_current_frag_obj();
    if(key in frag_obj){
        return frag_obj[key];
    }
    return null;
}

function update_url_frag_key_val(url, key, val, allowed_keys){
    let frag_str = '';
    if(url.indexOf('#') >= 0){
        url_parts = url.split('#');
        url = url_parts[0];
        frag_str = url_parts[1];
    }
    frag_str = update_frag_str(key, val, frag_str, allowed_keys);
    return url + '#' + frag_str;
}

function update_search_url_frag_key_val(url, key, val){
    return update_url_frag_key_val(url, key, val, SEARCH_FRAGMENT_KEYS);
}