/*
 * Controll display of human remains in search results
 */
 
function human_remains(){
	
	this.toggle_url = base_url + '/utilities/human-remains-ok';
	this.img_class = 'human-remains-div';
	this.warn_class = 'human-warning';
	this.global_dom_id = 'human-remains-global-alert';
	
	this.toggle_opt_in = function (){
		//do the ajax request, use GET so as not to need a CRT token
        $.ajax({
			type: "GET",
			url: this.toggle_url,
			dataType: "json",
			context: this,
			success: this.toggle_display
		});
	};
	
	this.toggle_display = function(data){
		
		if (data.new_opt_in){
			// we've opted in to view human remains
			this.toggle_general_alert(true);
			this.hide_dom_nodes_by_class(this.warn_class);
			this.show_dom_nodes_by_class(this.img_class);
		}
		else{
			// we've opted not to view human remains
			this.toggle_general_alert(false);
			this.hide_dom_nodes_by_class(this.img_class);
			this.show_dom_nodes_by_class(this.warn_class);
		}
		// return false;
	};
	
	this.hide_dom_nodes_by_class = function(class_name){
		var nodeList = document.getElementsByClassName(class_name);
		for (var i = 0, length = nodeList.length; i < length; i++) {
			var act_dom = nodeList[i];
			act_dom.style.display = 'none';
		}
		return false;
	};
	
	this.show_dom_nodes_by_class = function(class_name){
		var nodeList = document.getElementsByClassName(class_name);
		for (var i = 0, length = nodeList.length; i < length; i++) {
			var act_dom = nodeList[i];
			act_dom.style.display = 'block';	
		}
		return false;
	};
	
	this.toggle_general_alert = function(showing){
		if(document.getElementById(this.global_dom_id)){
			var html = '';
			var act_dom = document.getElementById(this.global_dom_id);
			if (showing){
				html = [
					'<span class="glyphicon glyphicon-eye-open" aria-hidden="true"></span> ',
					'You have <strong>ALLOWED</strong> ',
					'the display of images of human remains or burials. ',
					'Click <a href="javascript:humanRemains.toggle_opt_in();">HERE</a> ',
					'to NOT view such images.'
				].join('\n');
			}
			else{
				html = [
					'<span class="glyphicon glyphicon-eye-close" aria-hidden="true"></span> ',
					'To display search results with images of human remains, give permission first. ',
					'Click <a href="javascript:humanRemains.toggle_opt_in();">HERE</a> ',
					'to view such images.'
				].join('\n');
			}
			act_dom.innerHTML = html;
		}
		return false;
	}
}
