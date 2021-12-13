
function style_bce_ce_year(date_num, null_result){
	//styles a year BCE / CE
	let output = null;
	if (date_num == false || date_num == null) {
		return null_result;
	}
	if (date_num < 0) {
		output = (date_num * -1) + ' BCE';
	}
	else{
		output = date_num + ' CE';
	}	
	return output;
}