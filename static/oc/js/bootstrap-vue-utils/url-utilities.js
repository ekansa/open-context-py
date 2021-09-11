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