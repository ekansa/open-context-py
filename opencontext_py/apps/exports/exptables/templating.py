import json
from django.conf import settings
from opencontext_py.apps.entities.uri.models import URImanagement
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.apps.exports.expfields.models import ExpField
from opencontext_py.apps.exports.exprecords.models import ExpCell
from opencontext_py.apps.exports.exptables.models import ExpTable

"""
Methods for making metadata templates for a table
"""

class ExpTableTemplating():

    def __init__(self, table_id):
        self.table_id = table_id
        self.exp_tab = self.get_exp_table_obj(table_id)

    def get_exp_table_obj(self, table_id):
        """ gets an export table model object
            or returns false if it does not exist
        """
        try:
            exp_tab = ExpTable.objects.get(table_id=table_id)
        except ExpTable.DoesNotExist:
            exp_tab = False
        return exp_tab

    def make_json_ld(self):
        """ makes a JSON-LD object for the table metadata
        """
        json_ld = LastUpdatedOrderedDict()
        if self.exp_tab is not False:
            json_ld['id'] =  URImanagement.make_oc_uri(self.table_id, 'subjects')
            json_ld['label'] = self.exp_tab.label
            json_ld['rows'] = self.exp_tab.row_count
            json_ld['fields'] = self.exp_tab.field_count
            for key, objects in self.exp_tab.meta_json.items():
                json_ld[key] = objects
        return json_ld
