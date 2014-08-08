import datetime
import json
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.apps.exports.fields.models import ExpField
from opencontext_py.apps.exports.records.models import ExpRecord
from django.db import models
from django.db.models import Avg, Max, Min
from opencontext_py.apps.ocitems.geospace.models import Geospace
from opencontext_py.apps.ocitems.events.models import Event
from opencontext_py.apps.ocitems.assertions.containment import Containment
from opencontext_py.apps.ocitems.assertions.model import Assertion


# Stores data about fields for research
class Create():

    def __init__(self):
        self.source_id = False
        self.label = False
        self.records = LastUpdatedOrderedDict()

