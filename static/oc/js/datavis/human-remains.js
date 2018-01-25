/*
 * Controll display of human remains in search results
 */
 
function human_remains(){
	
	this.toggle_url = base_url + '/utilities/human-remains-ok';
	this.human_remains_class = '';
	
	this.toggle_opt_in = function (){
		//do the ajax request
        var action = $.ajax({
			type: "POST",
			url: this.toggle_url,
			dataType: "json",
			success: this.toggle_display
		});
	};
	
	this.toggle_display = function(data){
		
	};
	
}
