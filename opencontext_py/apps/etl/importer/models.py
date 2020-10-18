import hashlib
import pytz
import time
import re
import roman
import requests
import reversion  # version control object
import uuid as GenUUID

# For geospace manipulations.
from shapely.geometry import mapping, shape

from datetime import datetime
from math import pow
from time import sleep
from unidecode import unidecode

from django.core.cache import caches

from django.db import models
from django.db.models import Q

from django.contrib.postgres.fields import ArrayField, JSONField
from django.core.exceptions import ObjectDoesNotExist
from django.template.defaultfilters import slugify
from django.utils import timezone

from django.conf import settings


from opencontext_py.apps.all_items import configs

