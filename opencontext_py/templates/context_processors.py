from django.conf import settings


def piwik_settings(request):
    # return values for using PIWIK in templates
    print('Adding request context! ')
    return {
        'PIWIK_SITE_ID': settings.PIWIK_SITE_ID,
        # 'PIWIK_DOMAIN_PATH': settings.PIWIK_DOMAIN_PATH
        'PIWIK_DOMAIN_PATH': 'blubbie'
    }