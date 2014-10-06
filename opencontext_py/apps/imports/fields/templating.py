from django.db import models
from django.conf import settings
from django.db import models
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.apps.ocitems.assertions.models import Assertion
from opencontext_py.apps.ocitems.geospace.models import Geospace
from opencontext_py.apps.ocitems.events.models import Event
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.ocitems.subjects.models import Subject
from opencontext_py.apps.entities.entity.models import Entity
from opencontext_py.apps.imports.fields.models import ImportField
from opencontext_py.apps.imports.fieldannotations.models import ImportFieldAnnotation
from opencontext_py.apps.imports.records.models import ImportCell
from opencontext_py.apps.imports.fieldannotations.general import ProcessGeneral


# Stores data about fields from imported tables
class ImportProfile():

    def __init__(self, source_id):
        self.source_id = source_id
        pg = ProcessGeneral(source_id)
        pg.get_source()
        self.project_uuid = pg.project_uuid
        self.fields = []
        self.label = False

    def get_fields(self, field_num_list=False):
        if field_num_list is not False:
            imp_fields = ImportField.objects\
                                    .filter(source_id=self.source_id,
                                            field_num__in=field_num_list)
        else:
            imp_fields = ImportField.objects\
                                    .filter(source_id=self.source_id)
        self.fields = imp_fields

    def jsonify_fields(self):
        """ Returns the list of field objects as a json-friendly object """
        output = []
        for field_obj in self.fields:
            field_dict = LastUpdatedOrderedDict()
            field_dict['field_num'] = field_obj.field_num
            field_dict['label'] = field_obj.label
            field_dict['ref_name'] = field_obj.ref_name
            field_dict['field_type'] = field_obj.field_type
            field_dict['field_data_type'] = field_obj.field_data_type
            field_dict['field_value_cat'] = field_obj.field_value_cat
            field_dict['obs_num'] = field_obj.obs_num
            field_dict['value_prefix'] = field_obj.value_prefix
            field_dict['unique_count'] = field_obj.unique_count
            field_dict['f_uuid'] = field_obj.f_uuid
            output.append(field_dict)
        return output