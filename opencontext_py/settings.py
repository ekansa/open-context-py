"""
Django settings for opencontext_py project.

For more information on this file, see
https://docs.djangoproject.com/en/1.6/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.6/ref/settings/
"""

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os
BASE_DIR = os.path.dirname(os.path.dirname(__file__))

PROJECT_PATH = os.path.realpath(os.path.dirname(__file__))


# The following reads secret settings from a JSON file called 'secrets.json'
import json
import os.path
from os.path import join, normpath
from django.core.exceptions import ImproperlyConfigured

if os.path.isfile('secrets.json'):
    # get secret configuration information from the secrets.json file
    with open('secrets.json') as f:
        secrets = json.loads(f.read())
else:
    # print('Trying ' + BASE_DIR + '/secrets.json')
    with open(BASE_DIR + '/secrets.json') as f:
        secrets = json.loads(f.read())


def get_secret(setting, secrets=secrets):
    """Get secret variable or return an exception"""
    try:
        return secrets[setting]
    except KeyError:
        error_msg = 'Set the {0} environment variable'.format(setting)
        raise ImproperlyConfigured(error_msg)


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.6/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = get_secret('SECRET_KEY')
SOLR_HOST = get_secret('SOLR_HOST')
SOLR_PORT = get_secret('SOLR_PORT')
SOLR_COLLECTION = get_secret('SOLR_COLLECTION')

# Testing (for new indices) solr connection
if 'SOLR_HOST_TEST' in secrets:
    SOLR_HOST_TEST = get_secret('SOLR_HOST_TEST')
    SOLR_PORT_TEST = get_secret('SOLR_PORT_TEST')
    SOLR_COLLECTION_TEST = get_secret('SOLR_COLLECTION_TEST')
else:
    # Default to the normal solr connection
    SOLR_HOST_TEST = SOLR_HOST
    SOLR_PORT_TEST = SOLR_PORT_TEST
    SOLR_COLLECTION_TEST = SOLR_COLLECTION_TEST

# SECURITY WARNING: don't run with debug turned on in production!
if get_secret('DEBUG') == 1:
    DEBUG = True
    # TEMPLATE_DEBUG = True
    if str(os.getenv('DEBUG', 1)) == '0':
        # Allow an environment variable to turn off
        # debugging. Nice for indexing on a dev machine
        # from the shell.
        DEBUG = False
else:
    DEBUG = False
    # TEMPLATE_DEBUG = False
    if str(os.getenv('DEBUG', 0)) == '1':
        # allow environment variable to determine if debug
        DEBUG = True


TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            os.path.join(PROJECT_PATH, 'templates')
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                # Insert your TEMPLATE_CONTEXT_PROCESSORS here or use this
                # list if you haven't customized them:
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                # 'django.contrib.auth.context_processors.PermWrapper',
                'django.template.context_processors.i18n',
                'django.template.context_processors.media',
                'django.template.context_processors.static',
                'django.template.context_processors.tz',
                # for some reason, I can't get the following to work
                'opencontext_py.templates.context_processors.piwik_settings',
                'opencontext_py.templates.context_processors.page_metadata',
            ],
            'debug': DEBUG,
            # 'DEBUG': DEBUG,
            # 'TEMPLATE_DEBUG': DEBUG
        },

    },
]

INTERNAL_IPS =[
    '127.0.0.1',
    '0.0.0.0',
]

ALLOWED_HOSTS = [
    '.opencontext.org',
    '127.0.0.1',
    '0.0.0.0',
]

# saves configuration problems
# settings.py can be updated without upsetting
# local deployment configurations
added_host = get_secret('ALLOWED_HOST')
if len(added_host) > 1:
    ALLOWED_HOSTS.append(added_host)



# Is this deployement connected to the Web?
# Defaults to TRUE, but the setting exists in case
# only locally available files (CSS, Javascript, media)
# can be used
WEB_OK = True
if 'WEB_OK' in secrets:
    secrets_web_ok = get_secret('WEB_OK')
    if secrets_web_ok != 1:
        WEB_OK = False


# Is this deployment defaulting to HTTPS?
# Defaults to False, but the setting exists
# in case we want to make all links, and all
# static files and media HTTPS
SECURE_SSL_REDIRECT = False
DEFAULT_HTTPS = False
if 'SECURE_SSL_REDIRECT' in secrets:
    secrets_https = get_secret('SECURE_SSL_REDIRECT')
    if secrets_https == 1 or secrets_https == '1':
        SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
        SECURE_SSL_REDIRECT = True
        DEFAULT_HTTPS = True


# Merritt (CDL repository) seems to do strange HTTP redirects which
# break browser display of images. This setting toggles proxying of
# these image files. A crude solution that seems to lead to too many
# 500 errors.
MERRITT_IMAGE_PROXY = False

# EZID Authentication and configuration
# This is used to interact with the EZID service
# to make and manage persistent identifiers
EZID_USERNAME = False
EZID_PASSWORD = False
EZID_ARK_SHOULDER = False
EZID_DOI_SHOULDER = False
if 'EZID_USERNAME' in secrets:
    EZID_USERNAME = get_secret('EZID_USERNAME')
if 'EZID_PASSWORD' in secrets:
    EZID_PASSWORD = get_secret('EZID_PASSWORD')
if 'EZID_ARK_SHOULDER' in secrets:
    EZID_ARK_SHOULDER = get_secret('EZID_ARK_SHOULDER')
if 'EZID_DOI_SHOULDER' in secrets:
    EZID_DOI_SHOULDER = get_secret('EZID_DOI_SHOULDER')


# Application definition

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.humanize',
    'reversion',

    # These asre now the cannonical source of
    # data published by Open Context\
    'opencontext_py.apps.all_items',
    'opencontext_py.apps.etl.importer',

    # This is for estimating publishing costs
    'opencontext_py.apps.publish_costs',

    'opencontext_py.apps.entities.redirects',

    # These are being deprecated
    'opencontext_py.apps.entities.uri',
    'opencontext_py.apps.entities.entity',
    'opencontext_py.apps.ocitems.namespaces',

    # These are beind deprecated.
    'opencontext_py.apps.ocitems.subjects',
    'opencontext_py.apps.ocitems.ocitem',
    'opencontext_py.apps.ocitems.manifest',
    'opencontext_py.apps.ocitems.assertions',
    'opencontext_py.apps.ocitems.events',
    'opencontext_py.apps.ocitems.geospace',
    'opencontext_py.apps.ocitems.mediafiles',
    'opencontext_py.apps.ocitems.documents',
    'opencontext_py.apps.ocitems.persons',
    'opencontext_py.apps.ocitems.projects',
    'opencontext_py.apps.ocitems.strings',
    'opencontext_py.apps.ocitems.octypes',
    'opencontext_py.apps.ocitems.octypetree',
    'opencontext_py.apps.ocitems.predicates',
    'opencontext_py.apps.ocitems.predicatetree',
    'opencontext_py.apps.ocitems.identifiers',
    'opencontext_py.apps.ocitems.obsmetadata',
    'opencontext_py.apps.ocitems.editorials',
    'opencontext_py.apps.ldata.linkannotations',
    'opencontext_py.apps.ldata.linkentities',

    'django.contrib.staticfiles',
    'debug_toolbar',
    'django_user_agents',

    # New for editorial interfaces to make export tables.
    'django_rq',
    'django_extensions',

    # Sitemaps for search engines
    'django.contrib.sites',
    'django.contrib.sitemaps',
)

# For site maps
SITE_ID = 1

# For graphing ORM relations.
GRAPH_MODELS = {
    'pygraphviz': True,
    'app_labels': ["all_items"],
}


MIDDLEWARE = (
    'debug_toolbar.middleware.DebugToolbarMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # added caching
    'django.middleware.cache.UpdateCacheMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.cache.FetchFromCacheMiddleware',
    # Adding security
    'django.middleware.security.SecurityMiddleware',
    # User agent
    'django_user_agents.middleware.UserAgentMiddleware',
    # Record requests
    # 'opencontext_py.middleware.requestmiddleware.RequestMiddleware',
)

DEBUG_TOOLBAR_PANELS = [
    # 'debug_toolbar.panels.versions.VersionsPanel',
    'debug_toolbar.panels.timer.TimerPanel',
    'debug_toolbar.panels.settings.SettingsPanel',
    'debug_toolbar.panels.headers.HeadersPanel',
    'debug_toolbar.panels.request.RequestPanel',
    'debug_toolbar.panels.sql.SQLPanel',
    # 'debug_toolbar.panels.staticfiles.StaticFilesPanel',
    # 'debug_toolbar.panels.templates.TemplatesPanel',
    'debug_toolbar.panels.cache.CachePanel',
    # 'debug_toolbar.panels.signals.SignalsPanel',
    # 'debug_toolbar.panels.logging.LoggingPanel',
    # 'debug_toolbar.panels.redirects.RedirectsPanel',
]


ROOT_URLCONF = 'opencontext_py.urls'

WSGI_APPLICATION = 'opencontext_py.wsgi.application'

SESSION_ENGINE = ('django.contrib.sessions.backends.db')

SESSION_COOKIE_AGE = 7 * 24 * 60 * 60 # session expires in 1 week

# Database
# https://docs.djangoproject.com/en/1.6/ref/settings/#databases
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': get_secret('DATABASES_NAME'),
        'USER': get_secret('DATABASES_USER'),
        'PASSWORD': get_secret('DATABASES_PASSWORD'),
        'HOST': get_secret('DATABASES_HOST'),
        'CONN_MAX_AGE': 600,
    }
}

# Can we connect to the production database?
CONNECT_PROD_DB = False
if secrets.get('PROD_DATABASES_HOST'):
    CONNECT_PROD_DB = True
    DATABASES['prod'] = {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': secrets.get('PROD_DATABASES_NAME'),
        'USER': secrets.get('PROD_DATABASES_USER'),
        'PASSWORD': secrets.get('PROD_DATABASES_PASSWORD'),
        'HOST': secrets.get('PROD_DATABASES_HOST'),
        'PORT': secrets.get('PROD_DATABASES_PORT'),
        'CONN_MAX_AGE': 600,
    }


ADMINS = [
    (get_secret('ADMIN_NAME'), get_secret('ADMIN_EMAIL'),)
]
MANAGERS = [
    (get_secret('MANAGE_NAME'), get_secret('MANAGE_EMAIL'),)
]

DEFAULT_REDIS_HOST_PORT = '127.0.0.1:6379'
env_redis_host_port = os.getenv('REDIS_HOST_PORT', DEFAULT_REDIS_HOST_PORT)
REDIS_HOST_PORT = secrets.get('REDIS_HOST_PORT', env_redis_host_port)
if not ':' in REDIS_HOST_PORT:
    # Add the default Redis host port if not present.
    REDIS_HOST_PORT += ':6379'
redis_split = REDIS_HOST_PORT.split(':')
REDIS_HOST = redis_split[0]
REDIS_PORT = redis_split[1]

if DEBUG:
    # Short caching for debugging
    FILE_CACHE_TIMEOUT = (60 * 5)
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
            'LOCATION': 'oc_cache_table',
            'TIMEOUT': 1,
            'OPTIONS': {
                'MAX_ENTRIES': 5000
            }
        },
        'redis': {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            'LOCATION': f'redis://{REDIS_HOST_PORT}/1',
            'TIMEOUT': (60 * 5),  # 2 minute for cache
        },
        'redis_search': {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            'LOCATION': f'redis://{REDIS_HOST_PORT}/1',
            'TIMEOUT': (60 * 5),  # 2 minute for cache
        },
        'redis_context': {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            'LOCATION': f'redis://{REDIS_HOST_PORT}/1',
            'TIMEOUT': (60 * 5),  # 2 minute for cache
        },
        'file': {
            'BACKEND': 'django.core.cache.backends.filebased.FileBasedCache',
            'LOCATION': get_secret('FILE_CACHE_PATH'),
            'TIMEOUT': FILE_CACHE_TIMEOUT,
            'OPTIONS': {
                'MAX_ENTRIES': 10
            }
        },
        'memory': {
            # 'BACKEND': 'django.core.cache.backends.memcached.PyMemcacheCache',
            # 'LOCATION': '127.0.0.1:11211',
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'unique-snowflake',
        }
    }
else:
    # CACHES, Makes things faster
    FILE_CACHE_TIMEOUT = (1 * 24 * 60 * 60)  # 1 days for cache
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
            'LOCATION': 'oc_cache_table',
            'TIMEOUT': (7 * 24 * 60 * 60),  # 7 days for cache
            'OPTIONS': {
                'MAX_ENTRIES': 500000,
            }
        },
        'redis': {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            'LOCATION': f'redis://{REDIS_HOST_PORT}/1',
            'TIMEOUT': (60 * 60 * 4),  # 4 hours for cache
        },
        'redis_search': {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            'LOCATION': f'redis://{REDIS_HOST_PORT}/1',
            'TIMEOUT': (60 * 60 * 4),  # 4 hours for cache
        },
        'redis_context': {
           "BACKEND": "django.core.cache.backends.redis.RedisCache",
            'LOCATION': f'redis://{REDIS_HOST_PORT}/1',
            'TIMEOUT': (60 * 60 * 4),  # 4 hours for cache
        },
        'file': {
            'BACKEND': 'django.core.cache.backends.filebased.FileBasedCache',
            'LOCATION': get_secret('FILE_CACHE_PATH'),
            'TIMEOUT': FILE_CACHE_TIMEOUT,
            'OPTIONS': {
                'MAX_ENTRIES': 1500
            }
        },
        'memory': {
            # 'BACKEND': 'django.core.cache.backends.memcached.PyMemcacheCache',
            # 'LOCATION': '127.0.0.1:11211',
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'unique-snowflake',
        },
        'local_memory': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'unique-snowflake',
        },
    }

# user agents cache, memory cache for speed
USER_AGENTS_CACHE = 'redis'

RQ_QUEUES = {
    'default': {
        "HOST": REDIS_HOST,
        "PORT": f'{REDIS_PORT}',
        "URL": os.getenv("REDISTOGO_URL", f'redis://{REDIS_HOST_PORT}'),  # If you're
        "DB": 0,
        "DEFAULT_TIMEOUT": 480,
    },
    'high': {
        "HOST": REDIS_HOST,
        "PORT": f'{REDIS_PORT}',
        "URL": os.getenv("REDISTOGO_URL", f'redis://{REDIS_HOST_PORT}'),  # If you're
        "DB": 0,
        "DEFAULT_TIMEOUT": 480,
    },
    'low': {
        "HOST": REDIS_HOST,
        "PORT": f'{REDIS_PORT}',
        "URL": os.getenv("REDISTOGO_URL", f'redis://{REDIS_HOST_PORT}'),  # If you're
        "DB": 0,
        "DEFAULT_TIMEOUT": 480,
    },
}

# -----------------------
# EMAIL settings
# -----------------------
EMAIL_USE_TLS = True
EMAIL_HOST = get_secret('EMAIL_HOST')
EMAIL_PORT = get_secret('EMAIL_PORT')
EMAIL_HOST_USER = get_secret('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = get_secret('EMAIL_HOST_PASSWORD')
DEFAULT_FROM_EMAIL = get_secret('DEFAULT_FROM_EMAIL')
DEFAULT_TO_EMAIL = get_secret('DEFAULT_TO_EMAIL')




# Internationalization
# https://docs.djangoproject.com/en/1.6/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True

# ----------------------------
# WEB MAPPING SETTINGS
# ----------------------------
MAPBOX_PUBLIC_ACCESS_TOKEN = 'pk.eyJ1IjoiZWthbnNhIiwiYSI6IlZFQ1RfM3MifQ.KebFObTZOeh9pDHM_yXY4g'

# ----------------------------
# IMPORTER SETTINGS
# ----------------------------
IMPORT_BATCH_SIZE = 500  # number of records to import in 1 batch

# Use the normal dict get method, because we don't need to throw
# an error if this secret does not exist.
REFINE_URL = secrets.get(
    'REFINE_URL',
    'http://127.0.0.1:3333', # The default.
)

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.6/howto/static-files/
if DEBUG:
    ADMIN_MEDIA_PREFIX = '/static/admin/'
    STATIC_URL = '/static/'
    # STATIC_ROOT = BASE_DIR + '/static/'
    STATIC_ROOT = BASE_DIR
    STATICFILES_DIRS = (
        os.path.join(BASE_DIR, 'static'),
        # '/static/',
    )
    # STATIC_EXPORTS_ROOT = STATIC_ROOT + '/exports/'
    # STATIC_IMPORTS_ROOT = STATIC_ROOT + '/imports/'
    STATIC_EXPORTS_ROOT = STATIC_ROOT + '/static/exports/'
    STATIC_IMPORTS_ROOT = STATIC_ROOT + '/static/imports/'
else:
    ADMIN_MEDIA_PREFIX = '/static/admin/'
    STATIC_URL = '/static/'
    STATIC_ROOT = get_secret('STATIC_ROOT')
    STATICFILES_DIRS = (
        normpath(join(BASE_DIR, 'static')),
    )
    STATIC_EXPORTS_ROOT = STATIC_ROOT + '/exports/'
    STATIC_IMPORTS_ROOT = STATIC_ROOT + '/imports/'

STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'

import socket

#get the local host server name
try:
    HOSTNAME = socket.gethostname()
except:
    HOSTNAME = 'localhost'

ADMIN_EMAIL = get_secret('ADMIN_EMAIL')

# assumes DEPLOYED_HOST starts with 'http://' or 'https://'
DEPLOYED_HOST = get_secret('DEPLOYED_HOST')
if 'http://' not in DEPLOYED_HOST and 'https://' not in DEPLOYED_HOST:
    if DEFAULT_HTTPS:
        DEPLOYED_HOST = 'https://' + DEPLOYED_HOST
    else:
        DEPLOYED_HOST = 'http://' + DEPLOYED_HOST

DEPLOYED_SITE_NAME = get_secret('DEPLOYED_SITE_NAME')
if get_secret('DEPLOYED_HOST') == 1:
    TO_DEPLOYED_URIS = True
else:
    TO_DEPLOYED_URIS = False

CANONICAL_BASE_URL = 'opencontext.org'
CANONICAL_HOST = f'http://{CANONICAL_BASE_URL}'
CANONICAL_SITENAME = 'Open Context'
TWITTER_SITE = '@opencontext'
if 'HOST_TAGLINE' in secrets:
    HOST_TAGLINE = get_secret('HOST_TAGLINE')
else:
    HOST_TAGLINE = 'Publication and exhibition of open research data '\
                    + 'and media from archaeology and related fields'

GEOIP_PATH = None
if 'GEOIP_PATH' in secrets:
    # we have a GeoIP path for geo data of IP addresses
    GEOIP_PATH = get_secret('GEOIP_PATH')

# useful hack to allow presence of a 'debug.json' file to
# toggle debug mode
if os.path.isfile('debug.json'):
    # get secret configuration information from the secrets.json file
    DEBUG = True
    TEMPLATE_DEBUG = True
    DEPLOYED_HOST = 'http://localhost'
elif os.path.isfile(BASE_DIR + '/debug.json'):
    DEBUG = True
    TEMPLATE_DEBUG = True
    DEPLOYED_HOST = 'http://localhost'
else:
    # do nothing, no debug file flag
    pass

# PIWIK tracking, if enabled
PIWIK_SITE_ID = 0
PIWIK_DOMAIN_PATH = None
if DEBUG is False:
    if 'PIWIK_SITE_ID' in secrets:
        # site id for PIWIK tracking
        PIWIK_SITE_ID = get_secret('PIWIK_SITE_ID')
    if 'PIWIK_DOMAIN_PATH' in secrets:
        PIWIK_DOMAIN_PATH = get_secret('PIWIK_DOMAIN_PATH')


# Cloud Storage (S3, Google, etc.) Credentials
# NOTE: The CLOUD_STORAGE_SERVICE constant must be named by
# Apache Libcloud as a cloud storage service provider
CLOUD_STORAGE_SERVICE = secrets.get("CLOUD_STORAGE_SERVICE")
CLOUD_KEY = secrets.get("CLOUD_KEY")
CLOUD_SECRET = secrets.get("CLOUD_SECRET")
CLOUD_CONTAINER_EXPORTS = secrets.get("CLOUD_CONTAINER_EXPORTS")
CLOUD_BASE_URL = secrets.get("CLOUD_BASE_URL")

# Internet Archive Credentials
# generate keys at: https://archive.org/account/s3.php
if 'INTERNET_ARCHIVE_ACCESS_KEY' in secrets:
    # S3 access key fr the internet archive.
    INTERNET_ARCHIVE_ACCESS_KEY = get_secret('INTERNET_ARCHIVE_ACCESS_KEY')
else:
    INTERNET_ARCHIVE_ACCESS_KEY = None
if 'INTERNET_ARCHIVE_SECRET_KEY' in secrets:
    # password for the internet archive
    INTERNET_ARCHIVE_SECRET_KEY = get_secret('INTERNET_ARCHIVE_SECRET_KEY')
else:
    INTERNET_ARCHIVE_SECRET_KEY = None

if 'ZENODO_ACCESS_TOKEN' in secrets:
    # API access / credential / authorization token for Zendo requests
    ZENODO_ACCESS_TOKEN = get_secret('ZENODO_ACCESS_TOKEN')
else:
    ZENODO_ACCESS_TOKEN = None

if 'ZENODO_SANDBOX_TOKEN' in secrets:
    # API access / credential / authorization token for Zendo SANDBOX (testing) requests
    ZENODO_SANDBOX_TOKEN = get_secret('ZENODO_SANDBOX_TOKEN')
else:
    ZENODO_SANDBOX_TOKEN = None

if 'ORCID_CLIENT_ID' in secrets:
    # ORCID service client ID.
    ORCID_CLIENT_ID = get_secret('ORCID_CLIENT_ID')
else:
    ORCID_CLIENT_ID = None

if 'ORCID_CLIENT_SECRET' in secrets:
    # ORCID client secret, needed to access ORCID apis
    ORCID_CLIENT_SECRET = get_secret('ORCID_CLIENT_SECRET')
else:
    ORCID_CLIENT_SECRET = None


if 'CORS_OK_DOMAINS' in secrets:
    # password for the internet archive
    CORS_OK_DOMAINS = [get_secret('CORS_OK_DOMAINS')]
else:
    CORS_OK_DOMAINS = []

if not DEBUG:
    # Add these for CORS support of storage buckets in production settings.
    CORS_OK_DOMAINS += [
        'storage.googleapis.com/opencontext-media',
        'storage.googleapis.com/opencontext-parquet',
    ]

# Added to fix
if not DEBUG:
    CSRF_TRUSTED_ORIGINS = [
        DEPLOYED_HOST,
        'https://*.opencontext.org',
        'http://*.opencontext.org',
    ]

ITEM_TYPES = (
    ('subjects', 'subjects'),
    ('media', 'media'),
    ('documents', 'documents'),
    ('projects', 'projects'),
    ('persons', 'persons'),
    ('types', 'types'),
    ('predicates', 'predicates'),
    ('tables', 'tables'),
    ('vocabularies', 'vocabularies'),
)

SLUG_TYPES = ['predicates', 'projects']

STABLE_ID_URI_PREFIXES = {'doi': 'https://doi.org/',
                          'orcid': 'https://orcid.org/',
                          'ark': 'https://n2t.net/ark:/'}

TEXT_CONTENT_PREDICATES = [
    'dc-terms:description',
    'description',
    'dc-terms:abstract',
    'rdfs:comment',
    'rdf:HTML',
    'skos:note'
]

NAV_ITEMS = [
    {
        'key': 'about',
        'link': None,
        'display': 'About',
        'always': True,
        'PIWIK_SITE_ID': PIWIK_SITE_ID,  # HACK! not a good way to pass this, but works
        'PIWIK_DOMAIN_PATH': PIWIK_DOMAIN_PATH,
        'urls': [
            {
                'display': 'About Open Context',
                'link': '/about/',
            },
            {
                'display': 'Uses',
                'link': '/about/uses',
            },
            {
                'display': 'Publishing',
                'link': '/about/publishing',
            },
            {
                'display': 'Publishing Fees',
                'link': '/about/estimate',
            },
            {
                'display': 'Technology and Archiving',
                'link': '/about/technology',
            },
            {
                'display': 'APIs and Web Services',
                'link': '/about/services',
            },
            {
                'display': 'Data and API Recipes',
                'link': '/about/recipes',
            },
            {
                'display': 'Intellectual Property',
                'link': '/about/intellectual-property',
            },
            {
                'display': 'FAIR and CARE Data',
                'link': '/about/fair-care',
            },
            {
                'display': 'People',
                'link': '/about/people',
            },
            {
                'display': 'Support + Sponsors',
                'link': '/about/sponsors',
            },
            {
                'display': 'Bibliography',
                'link': '/about/bibliography',
            },
            {
                'display': 'Terms of Use, Privacy',
                'link': '/about/terms',
            },
        ]
    },
    {
        'key': 'highlights',
        'link': '/highlights/',
        'display': 'Highlights',
        'always': True,
        'urls': [
            {
                'display': 'Highlights',
                'link': '/highlights/'
            },
        ]
    },
    {
        'key': 'publications',
        'link': '/projects-index/',
        'display': 'Data Publications',
        'always': True,
        'urls': [
            {
                'display':  'Data Publications',
                'link': '/projects-index/',
            },
        ]
    },
    {
        'key': 'explore',
        'link': '/query/',
        'display': 'Explore',
        'always': True,
        'urls': [
            {
                'display': 'Search Records',
                'link': '/query/'
            },
        ]
    },
]

LOGGING_DIR = BASE_DIR + '/logs/'

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(LOGGING_DIR, 'error.log'),
            'maxBytes': 1024*1024*15,  # 15MB
            'backupCount': 10
            }
        },
    'loggers': {
        'opencontext_py.apps.indexer.crawler': {
            'handlers': ['file'],
            'level': 'DEBUG'
            }
        }
    }

# These are common prefixes used in caching.
CACHE_PREFIX_SEARCH = 'search_'
CACHE_PREFIX_FACET_DF = 'fctdf_'
CACHE_PREFIX_VIEW = 'view_'
CACHE_PREFIX_PROJ_CONTEXT = 'pcntx_' # For project context dataframe caching
CACHE_PREFIX_PROJ_META = 'prj_meta_' # For project image overlay and other metadata
CACHE_PREFIX_MANIFEST_OBJ = 'man_obj_'