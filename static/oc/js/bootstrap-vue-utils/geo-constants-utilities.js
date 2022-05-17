/*
This configures Open Context geojson data visualization.
*/



// These are geojson feature properties for individual records
// that should be excluded from the UI and downloads.
const UI_RECORD_EXCLUDE_PROPERTY_KEYS = [
    'id',
    'feature-type',
    'href',
];

// These are geojson feature property keys (used in individual records)
// mapped to more human readable labels.
const UI_RECORD_PROPERTY_KEY_HUMAN_READABLE_MAPPINGS = {
    'uri': 'URI',
    'citation uri': 'Citation URI',
    'label': 'Item Label',
    'project label': 'Project',
    'project href': 'Project URI',
    'context label': 'Context',
    'context href': 'Context URI',
    'latitude': 'Latitude (WGS-84)',
    'longitude': 'Longitude (WGS-84)',
    'early bce/ce': 'Early BCE/CE',
    'late bce/ce': 'Late BCE/CE',
    'item category': 'Item Category',
    'thumbnail': 'Thumbnail',
    'snippet': 'Search-Term Snippet',
    'published': 'Published Date',
    'updated': 'Updated Date',
};

// These configure consolidation of label and URI fields
// to make hyperlinks in the user interface.
const UI_RECORD_PROPERTY_LINK_CONSOLIDATE = {
    'URI': null,
    'Item Label': 'URI',
    'Citation URI': 'Citation URI',
    'Project URI': null,
    'Project': 'Project URI',
    'Context URI': null,
    'Context': 'Context URI',
}


function skip_excluded_property_key(key){
    if(UI_RECORD_EXCLUDE_PROPERTY_KEYS.indexOf(key) >= 0){
        return true;
    }
    return false;
}

function map_property_key_to_field(key){
	if(UI_RECORD_PROPERTY_KEY_HUMAN_READABLE_MAPPINGS.hasOwnProperty(key)){
	   return UI_RECORD_PROPERTY_KEY_HUMAN_READABLE_MAPPINGS[key];
	}
	return key;
}