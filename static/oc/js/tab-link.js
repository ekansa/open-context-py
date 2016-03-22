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