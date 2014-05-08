import requests
from opencontext_py.apps.ldata.linkannotations.models import LinkAnnotation as LinkAnnotation
from opencontext_py.apps.ldata.linkentities.models import LinkEntity as LinkEntity
from opencontext_py.apps.ocitems.chronology.models import Chronology as Chronology
from opencontext_py.apps.ocitems.geodata.models import Geodata as Geodata

# OCmysql requests JSON-data from the MySQL datastore.
# This is useful for synching the postgres and mysql databases as a temporary measure
class OCmysql():
    LAST_UPDATE_URL = "http://oc2/export/last-updates"
    TABLE_RECORD_COUNTS_URL = "http://oc2/export/table-records-count"
    TABLE_RECORDS_URL = "http://oc2/export/table-records-mapped"
    TABLES = ['link_annotations']
    mysql_last_updates = []
    DEFAULT_EARLY = '1970-01-01'

    def get_last_updates(self):
        """
        gets json data for last update of all mysql data tables
        """
        r = requests.get(self.LAST_UPDATE_URL, timeout=240)
        json_r = r.json()
        self.mysql_last_updates = json_r['result']
        return self.mysql_last_updates

    def get_table_records(self, act_table, after, start):
        """
        gets json data for records of a mysql datatable after a certain time
        """
        payload = {'table': act_table, 'after': after, 'start': start}
        r = requests.get(self.TABLE_RECORDS_URL, params=payload, timeout=240)
        json_r = r.json()
        return json_r['result']

    def store_records(self, act_table, recs):
        """
        stores records retrieved for a given table
        """
        for rkey, record in recs.items():
            if(act_table == 'link_annotations'):
                la = LinkAnnotation(**record)
                la.save()
            elif(act_table == 'link_entities'):
                le = LinkEntity(**record)
                le.save()
            elif(act_table == 'link_hierarchies'):
                lh = LinkHierarchy(**record)
                lh.save()
            elif(act_table == 'oc_chronology'):
                lh = Chronology(**record)
                lh.save()
            elif(act_table == 'oc_geodata'):
                lh = Geodata(**record)
                lh.save()

    def process_table(self, act_table, after):
        """
        iterates through a data table to get records after a certain time
        """
        start = 0
        loop_ok = True
        while loop_ok:
            recs = self.get_table_records(act_table, after, start)
            if recs is not False:
                self.store_records(act_table, recs)
                count_recs = len(recs)
                start = start + count_recs
            else:
                loop_ok = False
        return start
