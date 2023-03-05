from django.conf import settings


def piwik_settings(request):
    # return values for using PIWIK in templates
    return {
        'PIWIK_SITE_ID': settings.PIWIK_SITE_ID,
        # 'PIWIK_DOMAIN_PATH': settings.PIWIK_DOMAIN_PATH
        'PIWIK_DOMAIN_PATH': 'blubbie'
    }

def page_metadata(request):
    from opencontext_py.libs.rootpath import RootPath
    rp = RootPath()
    BASE_URL = rp.get_baseurl()
    return {
        'BASE_URL': BASE_URL,
        'NAV_ITEMS': settings.NAV_ITEMS,
    }