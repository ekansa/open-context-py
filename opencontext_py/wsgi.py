"""
WSGI config for opencontext_py project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/1.6/howto/deployment/wsgi/
"""

import os
import sys
import site

"""
# This proved very useful for getting this to work on an Ubuntu Server
# with uWSGI.

sys.path.append(os.path.dirname(__file__))
site.addsitedir(os.path.join('/var/oc_venv',
                             'lib/python3.4/site-packages'))

# from platform import python_version
# print('If you see, Python Version:' +  python_version() + ', things are going OK.')

"""

from django.core.wsgi import get_wsgi_application

os.environ['DJANGO_SETTINGS_MODULE'] = 'opencontext_py.settings'
application = get_wsgi_application()