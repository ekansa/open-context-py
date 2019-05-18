import pytest
from django.conf import settings
from opencontext_py.settings import DATABASES

@pytest.fixture(scope="module")
def django_db_setup():
    # Sets up the test database to use the default Open Context database
    # imported from opencontext_py.settings
    settings.DATABASES['default'] = DATABASES['default']