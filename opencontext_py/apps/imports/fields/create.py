import uuid as GenUUID
import datetime
from django.db import models
from django.db.models import Q
from opencontext_py.apps.imports.fields.models import ImportField
from opencontext_py.apps.imports.refine.api import RefineAPI


# Imports records, doing the appropriate lookups for uuids
class ImportFields():

    def __init__(self):
        self.source_id = False
        self.project_uuid = False

    def save_refine_model(self, refine_project):
        """ Loads a schema from refine, saves it in the database """
        r_api = RefineAPI(refine_project)
        self.source_id = r_api.source_id
        r_api.prepare_model()
        r_api.col_schema
        if r_api.col_schema is not False:
            new_fields = []
            for col_index, col in r_api.col_schema.items():
                imp_f = ImportField()
                imp_f.project_uuid = self.project_uuid
                imp_f.source_id = self.source_id
                imp_f.field_num = col_index
                imp_f.field_type = imp_f.DEFAULT_FIELD_TYPE
                imp_f.label = col['name']
                imp_f.orig_label = col['originalName']
                imp_f.f_uuid = self.heck_for_updated_uuid(col['name'],
                                                          col['originalName'])
            # Now that we've got likely related UUIDs, let's delete the old
            ImportField.objects.fielter(source_id=self.source_id).delete()
            for new_imp_f in new_fields:
                new_imp_f.save()

    def check_for_updated_uuid(self, label, orig_label):
        """ Checks to see if a previously assigned field_uuid should be kept"""
        f_uuid = ''
        old_fields = ImportField.objects\
                                .filter(source_id=self.source_id,
                                        Q(label=label) | Q(orig_label=orig_label))[:1]
        if len(old_fields) > 0:
            f_uuid = old_fields[0].f_uuid
        return f_uuid

    def get_make_field_uuid_by_label_type(self, label, field_type=False):
        """ Gets or makes a uuid for a field, by label, and field type
            A uuid is assumed to be unique for a field with the same
            type and label in a project
        """
        if field_type is False:
            poss_rel_fields = ImportField.object\
                                         .filter(project_uuid=self.project_uuid
                                                 label=label)[:1]
        else:
            poss_rel_fields = ImportField.object\
                                         .filter(project_uuid=self.project_uuid,
                                                 field_type=field_type,
                                                 label=label)[:1]
        if len(poss_rel_fields) > 0:
            f_uuid = poss_rel_fields[0].f_uuid
        else:
            f_uuid = GenUUID.uuid4()
        return f_uuid

