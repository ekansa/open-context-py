import json
from django.db import models
from opencontext_py.apps.exports.expfields.models import ExpField
from opencontext_py.apps.exports.exprecords.models import ExpCell
from opencontext_py.apps.exports.exptables.models import ExpTable
from opencontext_py.apps.exports.exprecords.create import Create


# Legacy data for associations between tables and content
# in the old version of Open Context. Ignore this if you
# are starting with this Python version
class ExpLegacy(models.Model):
    hash_id = models.CharField(max_length=50, primary_key=True)
    uuid = models.CharField(max_length=50)
    project_uuid = models.CharField(max_length=50)
    table_id = models.CharField(max_length=50)
    page = models.IntegerField()
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'exp_temprecs'


class ExpMigrate():
    """ Migrates old tables into new tables

from opencontext_py.apps.exports.exptables.migrate import ExpMigrate
exm = ExpMigrate()
exm.get_table_id_list()
exm.table_id_list
table_id = '341853c35844195860d3e0cf731f0702'
table_id = '4c98ccdee589f0e76c5fa7376ac2638e'
exm.process_table_id(table_id)

    """

    def __init__(self):
        self.table_id_list = []

    def process_table_id(self,
                         table_id,
                         do_linked_data=True,
                         source_fields=True):
        """ creates table records for a given table_id """
        uuids = self.get_uuids_by_table_id(table_id)
        exp_create = Create()
        exp_create.table_id = table_id
        exp_create.include_original_fields = source_fields
        exp_create.prep_process_uuid_list(uuids, do_linked_data)

    def get_uuids_by_table_id(self, table_id):
        """ gets a list of uuids for a given table id """
        rec_list = ExpLegacy.objects\
                            .values('uuid')\
                            .filter(table_id=table_id)
        uuids = []
        for rec in rec_list:
            uuids.append(str(rec['uuid']))
        return uuids

    def get_table_id_list(self):
        """ gets a list of legacy table ids """
        tab_list = ExpLegacy.objects\
                            .values('table_id')\
                            .distinct()
        for rec in tab_list:
            self.table_id_list.append(str(rec['table_id']))
