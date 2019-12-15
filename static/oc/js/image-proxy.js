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

function proxyLoadMerrittImages() {
	// Checks to see if images load, if not 
	var images = document.images;
	for (var i=0; i < images.length; i++) {
		var image = images[i];
		var src = image.src;
		if (!imgLoaded(image) && src.startsWith("https://merritt.cdlib.org")){
			// Wait 350 milliseconds so OC doesn't reject the request.
			wait(350);
			src = "/entities/proxy/" + encodeURI(src);
			image.src = src;
			console.log('Trying to get: '+ src);
		}
	}
}