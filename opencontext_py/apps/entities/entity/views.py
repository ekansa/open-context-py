import json
import requests
from django.http import HttpResponse, Http404
from django.conf import settings
from opencontext_py.libs.rootpath import RootPath
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.libs.generalapi import GeneralAPI
from django.views.decorators.cache import cache_control
from django.views.decorators.cache import never_cache


def proxy(request, target_url):
    """ Proxy request so as to get around CORS
        issues for displaying PDFs with javascript
        and other needs
    """
    gapi = GeneralAPI()
    if 'https:' in target_url:
        target_url = target_url.replace('https:', 'http:')
    if 'http://' not in target_url:
        target_url = target_url.replace('http:/', 'http://')
    ok = True
    status_code = 404
    print('Try to see: ' + target_url)
    try:
        r = requests.get(target_url,
                         timeout=240,
                         headers=gapi.client_headers)
        status_code = r.status_code
        r.raise_for_status()
    except:
        ok = False
        content = target_url + ' ' + str(status_code)
    if ok:
        status_code = r.status_code
        content = r.content
        if 'Content-Type' in r.headers:
            mimetype = r.headers['Content-Type']
            return HttpResponse(content,
                                status=status_code,
                                content_type=mimetype)
        else:
            return HttpResponse(content,
                                status=status_code,
                                content_type='application/gzip')
    else:
        return HttpResponse('Fail with HTTP status: ' + str(content),
                            status=status_code,
                            content_type='text/plain')


@cache_control(no_cache=True)
@never_cache
def proxy_header(request, target_url):
    """ Proxy request so as to get around CORS
        issues for displaying PDFs with javascript
        and other needs
    """
    gapi = GeneralAPI()
    ok = True
    status_code = 404
    try:
        r = requests.head(target_url,
                          headers=gapi.client_headers)
        status_code = r.status_code
        r.raise_for_status()
        output = {
            'status': status_code,
            'url': target_url
        }
        if 'Content-Length' in r.headers:
            output['Content-Length'] = int(float(r.headers['Content-Length']))
        if 'Content-Type' in r.headers:
            output['Content-Type'] = r.headers['Content-Type']
    except:
        ok = False
        content = target_url + ' ' + str(status_code)
    if ok:
        json_output = json.dumps(output,
                                 indent=4,
                                 ensure_ascii=False)
        return HttpResponse(json_output,
                            content_type='application/json; charset=utf8')
    else:
        return HttpResponse('Fail with HTTP status: ' + str(content),
                            status=status_code,
                            content_type='text/plain')
