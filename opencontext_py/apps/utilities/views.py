import json
from django.http import HttpResponse, Http404
from django.conf import settings
from django.template import RequestContext, loader
from opencontext_py.libs.rootpath import RootPath
from opencontext_py.libs.requestnegotiation import RequestNegotiation
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.libs.globalmaptiles import GlobalMercator


def meters_to_lat_lon(request):
    """ Converts Web mercator meters to WGS-84 lat / lon """
    gm = GlobalMercator()
    mx = None
    my = None
    if request.GET.get('mx') is not None:
        mx = request.GET['mx']
    if request.GET.get('my') is not None:
        my = request.GET['my']
    try:
        mx = float(mx)
    except:
        mx = False
    try:
        my = float(my)
    except:
        my = False
    if isinstance(mx, float) and isinstance(my, float):
        lat_lon = gm.MetersToLatLon(mx, my)
        output = LastUpdatedOrderedDict()
        if len(lat_lon) > 0:
            output['lat'] = lat_lon[0]
            output['lon'] = lat_lon[1]
        else:
            output['error'] = 'Stange error, invalid numbers?'
        return HttpResponse(json.dumps(output,
                                       ensure_ascii=False,
                                       indent=4),
                            content_type='application/json; charset=utf8')
    else:
        return HttpResponse('mx and my paramaters must be numbers',
                            status=406)