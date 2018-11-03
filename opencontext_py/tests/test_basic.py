import pytest

from django.test.utils import setup_test_environment
from django.test.client import Client

def test_hello():
    assert True

def test_main_page():

    client = Client()

    response = client.get('/')
    assert response.status_code == 200

