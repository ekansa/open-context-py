// from: http://stackoverflow.com/a/10787789
$(document).ready(function() {
    var hash = document.location.hash;
    var prefix = "tab_";
    if (hash) {
        $('.nav-tabs a[href=' + hash.replace(prefix, "") + ']').tab('show');
    }

    $('.nav-tabs a').on('shown.bs.tab', function(e) {
        window.location.hash = e.target.hash.replace("#", "#" + prefix);
    });

});

function change_tab(tab_id){
    // change the tab
    $('.nav-tabs a[href=' + tab_id + ']').tab('show');

    $('.nav-tabs a').on('shown.bs.tab', function(e) {
        var prefix = "tab_";
        window.location.hash = e.target.hash.replace("#", "#" + prefix);
    });

    
}