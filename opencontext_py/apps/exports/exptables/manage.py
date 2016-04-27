import json
from django.db.models import Count
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.apps.entities.uri.models import URImanagement
from opencontext_py.apps.exports.expfields.models import ExpField
from opencontext_py.apps.exports.exprecords.models import ExpCell
from opencontext_py.apps.exports.exptables.models import ExpTable
from opencontext_py.apps.ocitems.mediafiles.models import ManageMediafiles
from opencontext_py.apps.ocitems.manifest.models import Manifest


class ExpManage():
    """ Methods to manage export tables. Currently this feature is
        still in development. We're mainly supporting
        access to table dumps from the previous version
        of Open Context

from opencontext_py.apps.exports.exptables.manage import ExpManage
expman = ExpManage()
expman.temp_crawl_csv()

from opencontext_py.apps.exports.exptables.manage import ExpManage
expman = ExpManage()
table_id = 'def8fb9c9d7fdc1993db45b7350ca955'
proj_uuid_counts = expman.get_table_project_uuid_counts(table_id)
expman.make_table_project_uri_counts_list(proj_uuid_counts)
    """

    def __init__(self):
        self.project_uri_field = 4
        self.temp_table_base_url = 'http://artiraq.org/static/opencontext/tables/'

    def create_missing_metadata(self):
        """ creates missing metadata for an export table """
        pass

    def get_table_project_uuid_counts(self, table_id):
        """ gets project uuids and counts for a table, in
            descenting order of counts
        """
        proj_uuid_counts = ExpCell.objects\
                                  .filter(table_id=table_id)\
                                  .values('project_uuid')\
                                  .annotate(num_uuids=Count('uuid', distinct=True))\
                                  .order_by('-num_uuids')
        return proj_uuid_counts

    def make_table_project_uri_counts_list(self, proj_uuid_counts):
        """ makes a list of project URIs with labels
            and counts of records
        """
        project_list = []
        i = 0
        for proj_uuid_count in proj_uuid_counts:
            i += 1
            item = LastUpdatedOrderedDict()
            item['id'] = '#project-' + str(i)
            item['rdfs:isDefinedBy'] = URImanagement.make_oc_uri(proj_uuid_count['project_uuid'], 'projects')
            proj_man = False
            item['label'] = '[Project label not known]'
            try:
                proj_man = Manifest.objects.get(uuid=proj_uuid_count['project_uuid'])
            except Manifest.DoesNotExist:
                proj_man = False
            if proj_man is not False:
                item['label'] = proj_man.label
            item['count'] = proj_uuid_count['num_uuids']
            project_list.append(item)
        return project_list

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
