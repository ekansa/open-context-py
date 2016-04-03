import json
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.apps.exports.expfields.models import ExpField
from opencontext_py.apps.exports.exprecords.models import ExpCell
from opencontext_py.apps.exports.exptables.models import ExpTable
from opencontext_py.apps.ocitems.mediafiles.models import ManageMediafiles


class ExpManage():
    """ Methods to manage export tables. Currently this feature is
        still in development. We're mainly supporting
        access to table dumps from the previous version
        of Open Context

from opencontext_py.apps.exports.exptables.manage import ExpManage
expman = ExpManage()
expman.temp_crawl_csv()
    """

    def __init__(self):
        self.temp_table_base_url = 'http://artiraq.org/static/opencontext/tables/'

    def temp_crawl_csv(self):
        """ add download link to ExpTable metadata """
        ex_tabs = ExpTable.objects.all()
        for ex_tab in ex_tabs:
            if ExpTable.PREDICATE_DUMP not in ex_tab.meta_json:
                # no predicate for a data dump, so look for it
                file_uri = self.temp_table_base_url + ex_tab.table_id + '.csv'
                mm = ManageMediafiles()
                ok = mm.get_head_info(file_uri)
                if ok:
                    dump_list = []
                    dump_item = LastUpdatedOrderedDict()
                    dump_item['id'] = file_uri
                    dump_item['dc-terms:hasFormat'] = mm.mime_type_uri
                    dump_item['dcat:size'] = mm.filesize
                    print('Found: ' + str(dump_item))
                    dump_list.append(dump_item)
                    ex_tab.meta_json[ExpTable.PREDICATE_DUMP] = dump_list
                    ex_tab.save()
