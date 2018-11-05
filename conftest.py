import pytest
import json

@pytest.fixture(autouse=True)
def enable_db_access_for_all_tests(db):
        pass

@pytest.fixture(scope='session')
def django_db_setup():

	secrets = json.loads('secrets.json')

    settings.DATABASES['default'] = {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': secrets.get('DATABASES_NAME'),
        'USER': secrets.get('DATABASES_USER'),
        'PASSWORD': secrets.get('DATABASES_PASSWORD'),
        'HOST': secrets,get('DATABASES_HOST'),
        'CONN_MAX_AGE': 600,
    }