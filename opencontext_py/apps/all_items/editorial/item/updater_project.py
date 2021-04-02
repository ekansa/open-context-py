import copy
import json
import uuid as GenUUID

import reversion

from django.conf import settings
from django.core.validators import (
    validate_slug as django_validate_slug,
    URLValidator
)

from django.db.models import Q
from django.db import transaction
from django.utils import timezone


from opencontext_py.apps.all_items import configs
from opencontext_py.apps.all_items.models import (
    sting_number_splitter,
    suggest_project_short_id,
    AllManifest,
    AllAssertion,
    AllHistory,
    AllResource,
    AllIdentifier,
    AllSpaceTime,
)
from opencontext_py.apps.all_items import utilities as model_utils
from opencontext_py.apps.all_items.legacy_all import update_old_id
from opencontext_py.apps.all_items.editorial import api as editorial_api

from opencontext_py.apps.all_items import permissions
from opencontext_py.apps.all_items.editorial.item import edit_configs
from opencontext_py.apps.all_items.editorial.item import updater_general
from opencontext_py.apps.all_items.editorial.item import updater_manifest
from opencontext_py.apps.all_items.editorial.item import updater_assertions
from opencontext_py.apps.all_items.editorial.item import updater_spacetime
from opencontext_py.apps.all_items.editorial.item import updater_resources
from opencontext_py.apps.all_items.editorial.item import updater_identifiers


from opencontext_py.libs.models import (
    make_dict_json_safe, 
    make_model_object_json_safe_dict
)

