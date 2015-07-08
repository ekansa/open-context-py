/*
 * Functions to edit a profile
 */

function panel(id_num){
	this.id_num = id_num;
	this.dom_id_prefix = "prof-panel";
	this.dom_id = "";
	this.collapse_div_id = ""
	this.make_dom_ids = function(){
		this.dom_id = this.dom_id_prefix + '-' + this.id_num;
		this.collapse_div_id = this.dom_id + '-coldiv';
	}
	this.collapsing = true;
	this.collapsed = false;
	this.title_html = "";
	this.body_html = "";
	this.make_html = function(){
		// makes the panel html and puts it into the right parent dom id
		this.make_dom_ids();
		if (this.collapsing) {
			//code for collapsing panel
			var html = [
			'<div class="panel-group" id="' + this.dom_id + '">',
				'<div class="panel panel-default">',
					'<div class="panel-heading">',
						'<h4 class="panel-title">',
						'<a data-toggle="collapse" data-parent="#' + this.dom_id + '" href="#' + this.collapse_div_id + '">',
						'<span class="glyphicon glyphicon-resize-vertical"></span> ',
						this.title_html,
						'</a>',
						'</h4>',
					'</div>',
					'<div id="'+ this.collapse_div_id + '" class="panel-collapse collapse in">',
						'<div class="panel-body">',
						this.body_html,
						'</div>',
					'</div>',
				'</div>',
			'</div>'
			].join('\n');
		}
		else{
			var html = [
			'<div class="panel panel-default" id="' + this.dom_id + '">',
				'<div class="panel-heading">',
					'<h4 class="panel-title">' + this.title_html + '</h4>',
				'</div>',
				'<div class="panel-body">',
				this.body_html,
				'</div>',
			'</div>'
			].join('\n');
		}
		return html;
	}
}