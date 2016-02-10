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
TEMPLATE_DIRS = (
    os.path.join(PROJECT_PATH, 'templates'),
)

# The following reads secret settings from a JSON file called 'secrets.json'
import json
import os.path
from os.path import abspath, basename, dirname, join, normpath
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

# SECURITY WARNING: don't run with debug turned on in production!
if get_secret('DEBUG') == 1:
    DEBUG = True
    TEMPLATE_DEBUG = True
else:
    DEBUG = False
    TEMPLATE_DEBUG = False




ALLOWED_HOSTS = ['.opencontext.org']

# saves configuration problems
# settings.py can be updated without upsetting
# local deployment configurations
added_host = get_secret('ALLOWED_HOST')
if len(added_host) > 1:
    ALLOWED_HOSTS.append(added_host)

# Application definition

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.humanize',
    'reversion',
    'opencontext_py.apps.edit.versioning',
    'opencontext_py.apps.edit.inputs.profiles',
    'opencontext_py.apps.edit.inputs.fieldgroups',
    'opencontext_py.apps.edit.inputs.inputfields',
    'opencontext_py.apps.edit.inputs.inputrelations',
    'opencontext_py.apps.edit.inputs.rules',
    'opencontext_py.apps.entities.uri',
    'opencontext_py.apps.entities.entity',
    'opencontext_py.apps.ocitems.namespaces',
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
    'opencontext_py.apps.imports.ocmysql',
    'opencontext_py.apps.imports.fields',
    'opencontext_py.apps.imports.fieldannotations',
    'opencontext_py.apps.imports.records',
    'opencontext_py.apps.imports.sources',
    'opencontext_py.apps.ldata.linkannotations',
    'opencontext_py.apps.ldata.linkentities',
    'opencontext_py.apps.exports.expfields',
    'opencontext_py.apps.exports.exprecords',
    'opencontext_py.apps.exports.exptables',
    'opencontext_py.apps.indexer',
    'opencontext_py.apps.searcher.search',
    'django.contrib.staticfiles',
    'debug_toolbar',
)

MIDDLEWARE_CLASSES = (
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
)


ROOT_URLCONF = 'opencontext_py.urls'

WSGI_APPLICATION = 'opencontext_py.wsgi.application'


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

ADMINS = (
    (get_secret('ADMIN_NAME'), get_secret('ADMIN_EMAIL'))
)
MANAGERS = (
    (get_secret('MANAGE_NAME'), get_secret('MANAGE_EMAIL'))
)

if DEBUG:
    # Short caching for debugging
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
            'LOCATION': 'oc_cache_table',
            'TIMEOUT': 1,
            'OPTIONS': {
                'MAX_ENTRIES': 5
            }
        },
        'redis': {
            'BACKEND': 'redis_cache.RedisCache',
            'LOCATION': 'redis://127.0.0.1:6379/1',
            'TIMEOUT': (60 * 2),  # 2 minute for cache
            'OPTIONS': {
                'MAX_ENTRIES': 100
            }
        }
    }
else:
    # CACHES, Makes things faster
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
            'LOCATION': 'oc_cache_table',
            'TIMEOUT': (1.5 * 24 * 60 * 60),  # 1.5 days for cache
            'OPTIONS': {
                'MAX_ENTRIES': 15000
            }
        },
        'redis': {
            'BACKEND': 'django_redis.cache.RedisCache',
            'LOCATION': 'redis://127.0.0.1:6379/1',
            'TIMEOUT': (60 * 60),  # 1 hour for cache
            'OPTIONS': {
                'MAX_ENTRIES': 5000,
                'CLIENT_CLASS': 'django_redis.client.DefaultClient'
            }
        }
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
# IMPORTER SETIINGS
# ----------------------------
IMPORT_BATCH_SIZE = 500  # number of records to import in 1 batch


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
    DEPLOYED_HOST = 'http://' + DEPLOYED_HOST
DEPLOYED_SITE_NAME = get_secret('DEPLOYED_SITE_NAME')
if get_secret('DEPLOYED_HOST') == 1:
    TO_DEPLOYED_URIS = True
else:
    TO_DEPLOYED_URIS = False

CANONICAL_HOST = 'http://opencontext.org'
CANONICAL_SITENAME = 'Open Context'

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

STABLE_ID_URI_PREFIXES = {'doi': 'http://dx.doi.org/',
                          'orcid': 'http://orcid.org/',
                          'ark': 'http://n2t.net/ark:/'}

NAV_ITEMS = [{'key': 'about',
              'link': None,
              'display': 'About',
              'always': True,
              'urls': [{'display': 'About Open Context',
                        'link': '/about/'},
                       {'display': 'Uses',
                        'link': '/about/uses'},
                       {'display': 'Publishing',
                        'link': '/about/publishing'},
                       {'display': 'Publishing Fees',
                        'link': '/about/estimate'},
                       {'display': 'Concepts',
                        'link': '/about/concepts'},
                       {'display': 'Technology',
                        'link': '/about/technology'},
                       {'display': 'APIs and Web Services',
                        'link': '/about/services'},
                       {'display': 'Recipes using APIs',
                        'link': '/about/recipes'},
                       {'display': 'Intellectual Property',
                        'link': '/about/intellectual-property'},
                       {'display': 'People',
                        'link': '/about/people'},
                       {'display': 'Support + Sponsors',
                        'link': '/about/sponsors'},
                       {'display': 'Bibliography',
                        'link': '/about/bibliography'}]},
             {'key': 'explore',
              'link': None,
              'display': 'Explore',
              'always': True,
              'urls': [{'display': 'Browse Projects',
                        'link': '/projects-search/'},
                       {'display': 'Browse Media',
                        'link': '/media-search/'},
                       {'display': 'Browse Data Records',
                        'link': '/subjects-search/'},
                       {'display': 'Browse Everything',
                        'link': '/search/'}]},
             {'key': 'subjects',
              'link': '/subjects/',
              'display': 'Data Record',
              'always': False,
              'urls': None},
             {'key': 'media',
              'link': '/media/',
              'display': 'Media Item',
              'always': False,
              'urls': None},
             {'key': 'documents',
              'link': '/documents/',
              'display': 'Document Item',
              'always': False,
              'urls': None},
             {'key': 'persons',
              'link': '/persons/',
              'display': 'Person or Organization',
              'always': False,
              'urls': None},
             {'key': 'predicates',
              'link': '/predicates/',
              'display': 'Property or Relation',
              'always': False,
              'urls': None},
             {'key': 'types',
              'link': '/types/',
              'display': 'Category or Type',
              'always': False,
              'urls': None},
             {'key': 'tables',
              'link': '/tables/',
              'display': 'Data Table',
              'always': False,
              'urls': None},
             {'key': 'vocabularies',
              'link': '/vocabularies/',
              'display': 'Vocabulary / Ontology',
              'always': False,
              'urls': None},
             {'key': 'contact',
              'link': '/about/people#contact-editors',
              'display': 'Contact',
              'always': True,
              'urls': None}]

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
