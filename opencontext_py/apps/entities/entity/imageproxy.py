import urllib.parse
from django.conf import settings
from opencontext_py.libs.rootpath import RootPath


def proxy_image_url_if_needed(image_url, primary_url=None, width=150):
    """Makes a proxy URL to an image file if needed"""
    if not settings.MERRITT_IMAGE_PROXY:
        return image_url
    
    if not image_url:
        return image_url

    if not image_url.startswith('https://merritt.cdlib.org'):
        return image_url
    
    rp = RootPath()
    base_url = rp.get_baseurl()
    image_url = (
        base_url 
        + '/entities/proxy/' 
        + urllib.parse.quote(image_url)
    )
    
    if not primary_url or not primary_url.startswith('https://archive.org/download/'):
        return image_url

    archive_image_part = primary_url.split('https://archive.org/download/')[-1]
    if not '/' in archive_image_part:
        return image_url

    archive_id_part = archive_image_part.split('/')[0]
    image_url = (
        + 'https://iiif.archivelab.org/iiif/'
        + archive_id_part
        + '/full/{},/0/default.jpg'.format(width)
        + '#merritt-alt'
    )
    return image_url
