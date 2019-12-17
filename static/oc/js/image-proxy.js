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
	var proxy_param = "?merritt-proxy=";
	var proxy_start = "/entities/proxy/";
	var check_start = "https://merritt.cdlib.org";

	var images = document.images;
	for (var i=0; i < images.length; i++) {
		var image = images[i];
		var src = image.src;
		if (!imgLoaded(image) && (
				src.startsWith(check_start) 
				|| src.startsWith(proxy_start)
			)
		){
			if(attempt > 1){
				console.log("Still bad: " + src);
			}
			
			// Wait 350 milliseconds so OC doesn't reject the request.
			wait(350);
			if(src.startsWith(check_start)){
				src = "/entities/proxy/" + encodeURI(src);
			}
			else{
				if(src.indexOf(proxy_param) === -1){
					src += proxy_param;
				}
				src.split(proxy_param)[0];
				src += proxy_param + attempt;
			}
			image.src = src;
			console.log('Attempt: ' + attempt + ', Trying to get: '+ src);
		}
	}
}