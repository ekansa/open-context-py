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
from django.core.exceptions import ImproperlyConfigured
#get secret configuration information from the secrets.json file
with open('secrets.json') as f:
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

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

TEMPLATE_DEBUG = False

ALLOWED_HOSTS = []


# Application definition

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
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
    'opencontext_py.apps.ldata.linkannotations',
    'opencontext_py.apps.ldata.linkentities',
    'opencontext_py.apps.exports.fields',
    'opencontext_py.apps.exports.records',
    'opencontext_py.apps.indexer',
    'opencontext_py.apps.searcher.sets',
)

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
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
        'HOST': get_secret('DATABASES_HOST')
    }
}

# Internationalization
# https://docs.djangoproject.com/en/1.6/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.6/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR + '/static/'
STATICFILES_DIRS = (
    os.path.join(BASE_DIR, 'static'),
    '/static/',
)
import socket

#get the local host server name
try:
    HOSTNAME = socket.gethostname()
except:
    HOSTNAME = 'localhost'

CANONICAL_HOST = "http://opencontext.org"

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
