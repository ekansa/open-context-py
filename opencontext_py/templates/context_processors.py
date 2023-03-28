from django.conf import settings
from opencontext_py.apps.web_metadata.social import make_social_media_metadata


def piwik_settings(request):
    # return values for using PIWIK in templates
    return {
        'PIWIK_SITE_ID': settings.PIWIK_SITE_ID,
        'PIWIK_DOMAIN_PATH': settings.PIWIK_DOMAIN_PATH,
    }

def page_metadata(request):
    # Doing imports in here to avoid circular imports.
    from opencontext_py.libs.rootpath import RootPath
    rp = RootPath()
    BASE_URL = rp.get_baseurl()
    url = request.get_full_path()
    canonical_uri = f'https://{settings.CANONICAL_BASE_URL}{url}'
    if url.startswith('/all-items/'):
        # The all-items view will return a specific CANONICAL_URI by default.
       return {
            # The CANONICAL_URI will be specified by the all-items view.
            'CANONICAL_SITEMAP_URL': f'https://{settings.CANONICAL_BASE_URL}/sitemap.xml',
            'BASE_URL': BASE_URL,
            'NAV_ITEMS': settings.NAV_ITEMS,
        }

    return {
        # The CANONICAL_URI is the 'main' uri for this particular request.
        # Given our default settings, it'll be at https://opencontext.org/some-path
        'CANONICAL_URI': canonical_uri,
        'CANONICAL_SITEMAP_URL': f'https://{settings.CANONICAL_BASE_URL}/sitemap.xml',
        'BASE_URL': BASE_URL,
        'NAV_ITEMS': settings.NAV_ITEMS,
        'SOCIAL_MEDIA_META': make_social_media_metadata(
            url_path=url,
            canonical_uri=canonical_uri,
        ),
    }
