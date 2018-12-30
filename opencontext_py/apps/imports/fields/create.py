import uuid as GenUUID
from unidecode import unidecode
import datetime
from django.db import models
from django.db.models import Q
from opencontext_py.apps.imports.fields.models import ImportField
from opencontext_py.apps.imports.refine.api import RefineAPI
from opencontext_py.apps.imports.kobotoolbox.kobofields import KoboFields


# Imports records, doing the appropriate lookups for uuids
class ImportFields():

    def __init__(self):
        self.source_id = False
        self.obsolete_source_id = False
        self.project_uuid = False
        self.refine_schema = False

    def get_refine_schema(self, refine_project):
        """ Gets the column schema from Refine """
        output = False
        r_api = RefineAPI(refine_project)
        self.source_id = r_api.source_id
        r_api.prepare_model()
        r_api.col_schema
        if r_api.col_schema is not False:
            self.refine_schema = r_api.col_schema
            output = True
        return output

    def save_refine_model(self, refine_project):
        """ Loads a schema from refine, saves it in the database """
        output = False
        schema_ok = self.get_refine_schema(refine_project)
        kobo_fields = KoboFields()
        if schema_ok:
            # print('Refine schema is OK')
            new_fields = []
            for col_index, col in self.refine_schema.items():
                imp_f = ImportField()
                imp_f.project_uuid = self.project_uuid
                imp_f.source_id = self.source_id
                imp_f.field_num = col_index
                imp_f.is_keycell = False
                imp_f.obs_num = 1
                imp_f.label = col['name']
                imp_f.ref_name = col['name']
                imp_f.ref_orig_name = col['originalName']
                imp_f.unique_count = 0
                imp_f = self.check_for_updated_field(imp_f,
                                                     col['name'],
                                                     col['originalName'])
                imp_f = kobo_fields.classify_if_kobofield(imp_f)
                new_fields.append(imp_f)
            # Now that we've got likely related UUIDs, let's delete the old
            ImportField.objects.filter(source_id=self.source_id).delete()
            print('New fields to save: ' + str(len(new_fields)))
            for new_imp_f in new_fields:
                print('Saving field: ' + str(unidecode(new_imp_f.label)))
                new_imp_f.save()
            output = True
        else:
            print('Problem with refine schema: ' + refine_project)
        return output

    def check_for_updated_field(self,
                                imp_f,
                                label,
                                orig_name,
                                all_sources=False):
        """ Checks to see if a previously assigned attributes to the field should be kept"""
        if all_sources:
            old_fields = ImportField.objects\
                                    .filter(Q(label=label) | Q(ref_name=label) | Q(ref_orig_name=orig_name),
                                            project_uuid=self.project_uuid)[:1]
        else:
            old_fields = ImportField.objects\
                                    .filter(Q(label=label) | Q(ref_name=label) | Q(ref_orig_name=orig_name),
                                            Q(source_id=self.source_id) | Q(source_id=self.obsolete_source_id))[:1]
        if len(old_fields) > 0:
            imp_f.label = old_fields[0].label
            imp_f.field_type = old_fields[0].field_type
            imp_f.field_data_type = old_fields[0].field_data_type
            imp_f.field_value_cat = old_fields[0].field_value_cat
            imp_f.value_prefix = old_fields[0].value_prefix
            imp_f.f_uuid = old_fields[0].f_uuid
        else:
            if all_sources:
                # ok, the project lacks related fields, so use defaults
                imp_f.field_type = imp_f.DEFAULT_FIELD_TYPE
                imp_f.field_data_type = imp_f.DEFAULT_DATA_TYPE
                imp_f.field_value_cat = imp_f.DEFAULT_VALUE_CAT
                imp_f.value_prefix = ''
                imp_f.f_uuid = GenUUID.uuid4()
            else:
                # ok, now look for all previously imported fields in the project
                imp_f = self.check_for_updated_field(imp_f,
                                                     label,
                                                     orig_name,
                                                     True)
        return imp_f
