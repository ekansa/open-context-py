/*
 * This handles AJAX requests and responses for estimating project publication costs
 *
 */

function estimation(){
	
	
	
	this.submit = function(){
		this.ajax_exec_estimate();
	}
	
	this.ajax_exec_estimate = function(){
		// sends an ajax request a project cost estimate
		var data = this.make_estimate_data();
		var url = this.make_url('/about/process-estimate');
		return $.ajax({
				type: "POST",
				url: url,
				dataType: "json",
				context: this,
				data: data,
				success: this.ajax_exec_estimateDone,
				error: function (request, status, error) {
					alert('Data submission failed, sadly. Status: ' + request.status);
				} 
			});
	}
	this.ajax_exec_estimateDone = function(data){
		var alert_class = 'alert alert-success';
		if (data.errors.length > 0) {
			alert_class = 'alert alert-warning';
			var error_html = '<ul>';
			for (var i = 0, length = data.errors.length; i < length; i++) {
				error_html += '<li>' + data.errors[i] + '</li>';
			}
			error_html += '</ul>';
		}
		else{
			var error_html = '';
		}
		var html = [
			'<div style="margin-top: 20px; ">',
				'<div class="' + alert_class + '">',
				'<p>Total publlication and archiving cost estimate:</p>',
				'<blockquote>',
					'<h4>' + data.dollars  + '</h4>',
					'<footer>Based on provided project size and complexity, and assuming good data quality</footer>',
				'</blockquote>',
				error_html,
				'<p><strong>Note:</strong> ',
				'Emailing of results is a feature that is not yet ready. It will be implemented shortly.</p>',
				'</div>',
			'</div>',
		].join('\n');
		
		document.getElementById('estimation-results').innerHTML = html;
	}
	this.preliminary_estimate = function(){
		
	}
	
	
	this.make_estimate_data = function(){
		// basic contact + metadata
		var user_name = document.getElementById('input-name').value;
		var user_email = document.getElementById('input-email').value;
		// var user_phone = document.getElementById('input-phone').value;
		var project_name = document.getElementById('input-proj-name').value;
		var is_grad_student = this.get_checked_value_by_class('input-diss-proj');
		var duration = document.getElementById('input-proj-years').value;
		var count_spec_datasets = document.getElementById('input-spec-datasets').value;
		var count_tables = document.getElementById('input-count-tables').value;
		var count_images = this.get_checked_value_by_class('input-count-images');
		var count_docs = this.get_checked_value_by_class('input-count-docs');
		var count_gis = this.get_checked_value_by_class('input-count-gis');
		var count_other = this.get_checked_value_by_class('input-count-other');
		var comment = document.getElementById('input-comment').value;
		var license_uri = this.get_checked_value_by_class('input-license');
		var license_note = document.getElementById('input-license-note').value;
		
		var data = {
			csrfmiddlewaretoken: csrftoken,
			user_name: user_name,
			user_email: user_email,
			// user_phone: user_phone,
			project_name: project_name,
			is_grad_student: is_grad_student,
			duration: duration, 
			count_spec_datasets: count_spec_datasets,
			count_tables: count_tables,
			count_images: count_images,
			count_docs: count_docs,
			count_other: count_other,
			comment: comment,
			license_uri: license_uri,
			license_note: license_note
		};
		return data;
	}
	
	this.get_checked_value_by_class = function(class_name){
		// gets the checked value indicated for input elements that
		// have the same class (used with radio buttons)
		var output = false;
		var act_inputs = document.getElementsByClassName(class_name);
		for (var i = 0, length = act_inputs.length; i < length; i++) {
			if (act_inputs[i].checked) {
				output = act_inputs[i].value;
			}
		}
		return output;
	}
	
	this.make_url = function(relative_url){
	//makes a URL for requests, checking if the base_url is set	
		 //makes a URL for requests, checking if the base_url is set
		var rel_first = relative_url.charAt(0);
		if (typeof base_url != "undefined") {
			var base_url_last = base_url.charAt(-1);
			if (base_url_last == '/' && rel_first == '/') {
				return base_url + relative_url.substring(1);
			}
			else{
				return base_url + relative_url;
			}
		}
		else{
			if (rel_first == '/') {
				return '../..' + relative_url;
			}
			else{
				return '../../' + relative_url;
			}
		}
	}
	this.make_loading_gif = function(message){
		var src = this.make_url('/static/oc/images/ui/waiting.gif');
		var html = [
			'<div class="row">',
			'<div class="col-sm-1">',
			'<img alt="loading..." src="' + src + '" />',
			'</div>',
			'<div class="col-sm-11">',
			message,
			'</div>',
			'</div>'
			].join('\n');
		return html;
	}
	
} // end of the edit_field_object
