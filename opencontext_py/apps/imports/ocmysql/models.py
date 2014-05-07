import requests


# OCmysql requests JSON-data from the MySQL datastore.
# This is useful for synching the postgres and mysql databases as a temporary measure
class OCmysql():
    LAST_UPDATE_URL = "http://oc2/export/last-updates"
    TABLE_RECORD_COUNTS_URL = "http://oc2/export/table-records-count"
    TABLE_RECORDS_URL = "http://oc2/export/table-records-mapped"
    TABLES = ['oc_manifest', 'oc_assertions']
    mysql_last_updates = []

    def get_last_updates(self):
        r = requests.get(self.LAST_UPDATE_URL, timeout=240)
        json_r = r.json()
        self.mysql_last_updates = json_r['result']
        return self.mysql_last_updates
