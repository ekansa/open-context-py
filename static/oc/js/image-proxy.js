/*
 * Javascript for commonly needed utilities
 * for loading images via a proxy.
 */
function imgLoaded(imgElement) {
	return imgElement.complete && imgElement.naturalHeight !== 0;
}

function wait(ms){
	var start = new Date().getTime();
	var end = start;
	while(end < start + ms) {
	  end = new Date().getTime();
   }
}

function proxyLoadMerrittImages(attempt) {
	// Checks to see if images load, if not
	if (attempt == 1 ){
		var check_start = "https://merritt.cdlib.org";
	}
	else{
		var check_start = "/entities/proxy/";
	} 
	var images = document.images;
	for (var i=0; i < images.length; i++) {
		var image = images[i];
		var src = image.src;
		if (!imgLoaded(image) && src.startsWith(check_start)){
			// Wait 350 milliseconds so OC doesn't reject the request.
			wait(350);
			if(check_start != "/entities/proxy/"){
				src = "/entities/proxy/" + encodeURI(src);
			}
			else{
				if(src.indexOf("?merritt-proxy=") === -1){
					src += "?merritt-proxy=";
				}
				src.split("?merritt-proxy=")[0];
				src += "?merritt-proxy=" + attempt;
			}
			image.src = src;
			console.log('Attempt: ' + attempt + ', Trying to get: '+ src);
		}
	}
}