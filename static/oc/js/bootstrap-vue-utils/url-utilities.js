/*
These are functions needed to play with the URLs returned
by the Open Context search API so we can do useful things
in Vue templating.
*/

function remove_prefix(str, prefix){
    if(!str){
        return null;
    }
    if(str.startsWith(prefix)){
         return str.slice(prefix.length);
    } else {
         return str;
    }
}

function abs_to_rel_url(url, base_url=''){
    return remove_prefix(url, base_url);
}

function make_url_variants(url, add_missing_prefix=false){
    var urls = [url];
    if(add_missing_prefix && (url.indexOf(':') < 0)){
        let exp_prefixes = [
            'http://',
            'https://',
        ]
        for(let exp_prefix of exp_prefixes){
            let new_url = exp_prefix + url;
            urls.push(new_url);
        }
    }
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
    if(!url){
        return null;
    }
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


function use_all_items_href(href, base_url, use_all_items_href){
    if(!use_all_items_href){
        return href;
    }
    if(!href){
        return null;
    }
    if (typeof href === 'string' || href instanceof String){
        // we do have a string....
    }
    else{
        return href;
    }
    let do_all_items = false;
    if(href.indexOf('://opencontext.org/') >= 0){
        do_all_items = true;
    }
    if(href.indexOf('opencontext.org/vocabularies/') >= 0){
        do_all_items = false;
    }
    if(href.indexOf(base_url) >= 0){
        do_all_items = true;
    }
    if(href.indexOf(base_url + '/vocabularies/') >= 0){
        do_all_items = false;
    }
    if(href.indexOf(base_url + '/about/') >= 0){
        do_all_items = false;
    }
    if(!do_all_items){
        return href;
    }
    href_ex = href.split('/');
    let supported_item_types = [
        'subjects',
        'media',
        'documents',
        'predicates',
        'types',
        'projects',
        'persons',
        'tables',
    ];
    let item_type = href_ex[(href_ex.length - 2)];
    if(supported_item_types.indexOf(item_type) >= 0){
        return base_url + '/' + item_type+ '/' + href_ex[(href_ex.length - 1)];
    }
    return base_url + '/all-items/' + href_ex[(href_ex.length - 1)];
}


function use_local_subjects_href(href, base_url){
    if(!href){
        return null;
    }
    let ok_local = false;
    let req_part = 'opencontext.org/subjects/'
    if(href.indexOf(req_part) < 0){
        // We're not a subjects item, just return the url without change
        return href;
    }
    href_ex = href.split('/');
    return base_url + '/subjects/' + href_ex[(href_ex.length - 1)];
}


// a utility function to extract the sort from a URL
function get_field_sorting_from_url(url, sort_config){
    let sort_param = getURLParameter(url, 'sort');
    if(!sort_param){
        return null;
    }
    // multiple sorts are '---' split.
    let act_sorts = sort_param.split('---');
    let field_sorting = [];
    for(let act_sort of act_sorts){
        // the sort attribute and direction are '--' split
        let act_sort_ex = act_sort.split('--');
        if(act_sort_ex.length != 2){
            // not a valid sort.
            continue;
        }
        let act_oc_sort = act_sort_ex[0];
        let act_oc_dir = act_sort_ex[1];
        for (const [field_key, oc_value] of Object.entries(sort_config)) {
            if(act_oc_sort != oc_value){
                continue;
            }
            let field_sort = {
                field_key: field_key,
                oc_attrib: act_oc_sort,
                sortDirection: act_oc_dir,
            };
            field_sorting.push(field_sort);
        }
    }
    return field_sorting;
}