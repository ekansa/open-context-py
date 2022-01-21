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
    'lat', // map latitute
    'lng', // map longitude
    'ov', // active map overlays
    'ovgrd', //map overlay color gradient key
    'bm', // base map tile name
];

const FRAG_KEY_DELIM = '/';
const FRAG_KEY_VAL_DEMIM = '=';
const FRAG_KEY_MULTI_VAL_DEMIM = '~';

function parse_frag_dict(frag_str, allowed_keys){
    if(frag_str.indexOf('#') == 0) {
        frag_str = frag_str.substr(1);
    }
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
        if(val.indexOf(FRAG_KEY_MULTI_VAL_DEMIM) < 0){
            frag_obj[key] = val;
        }
        else{
            frag_obj[key] = val.split(FRAG_KEY_MULTI_VAL_DEMIM);
        }
    }
    return frag_obj;
}

function parse_search_frag_dict(frag_str){
    return parse_frag_dict(frag_str, SEARCH_FRAGMENT_KEYS);
}

function isArray (value) {
    return value && typeof value === 'object' && value.constructor === Array;
}


function encode_frag_obj(frag_obj, null_val=null){
    if(frag_obj == null){
        return null_val;
    }
    let key_vals = [];
    for (let entry of Object.entries(frag_obj)) {
        if(isArray(entry[1])){
            entry[1] = entry[1].join(FRAG_KEY_MULTI_VAL_DEMIM);
        }  
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
    if(!url){
        return null;
    }
    let frag_str = '';
    if(url.indexOf('#') >= 0){
        url_parts = url.split('#');
        url = url_parts[0];
        frag_str = url_parts[1];
    }
    frag_str = update_frag_str(key, val, frag_str, allowed_keys);
    return url + '#' + frag_str;
}

function abs_to_rel_url_with_frag_obj(url, base_url, frag_obj){
    if(url == null){
        return null;
    }
    let frag_str = '';
    if(frag_obj != null){
        frag_str = encode_frag_obj(frag_obj, null_val='');
    }
    if(frag_str.length > 1){
        if(url.indexOf('#') >= 0){
            let url_ex = url.split('#');
            url = url_ex[0];
        }
        url += '#' + frag_str;
    }
    url = abs_to_rel_url(url, base_url);
    return url;
}