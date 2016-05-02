import os
import json
from time import sleep
from unidecode import unidecode
from django.db.models import Count
from django.conf import settings
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.apps.entities.uri.models import URImanagement
from opencontext_py.apps.entities.entity.models import Entity
from opencontext_py.apps.exports.expfields.models import ExpField
from opencontext_py.apps.exports.exprecords.models import ExpCell
from opencontext_py.apps.exports.exptables.models import ExpTable
from opencontext_py.apps.ocitems.mediafiles.models import ManageMediafiles
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.ldata.linkentities.models import LinkEntity
from opencontext_py.apps.ldata.linkannotations.authorship import Authorship
from opencontext_py.apps.exports.exprecords.dump import CSVdump


class ExpManage():
    """ Methods to manage export tables. Currently this feature is
        still in development. We're mainly supporting
        access to table dumps from the previous version
        of Open Context

    """

    SLEEP_TIME = .5

    def __init__(self):
        self.delay_before_request = self.SLEEP_TIME
        self.authors_field = 7
        self.category_field = 5
        self.cat_vocab_uri = 'http://opencontext.org/vocabularies/oc-general/'
        self.temp_table_base_url = 'http://artiraq.org/static/opencontext/tables/'
        self.rev_table_base_url = 'http://artiraq.org/static/opencontext/revised-tables/'
        self.metadata_predicates = ['dc-terms:contributor',
                                    'dc-terms:creator',
                                    'dc-terms:source',
                                    'dc-terms:subject']

    def create_missing_metadata(self):
        """ creates missing metadata for an export table """
        ex_tabs = ExpTable.objects.all()
        for ex_tab in ex_tabs:
            proj_uuid_counts = None
            table_id = ex_tab.table_id
            old_meta = ex_tab.meta_json
            new_meta = LastUpdatedOrderedDict()
            for meta_pred in self.metadata_predicates:
                if meta_pred in old_meta:
                    new_meta[meta_pred] = old_meta[meta_pred]
                else:
                    if meta_pred == 'dc-terms:contributor':
                        print('Getting contributors for ' + table_id)
                        new_meta[meta_pred] = self.make_table_dc_contributor_list(table_id)
                    if meta_pred in ['dc-terms:creator',
                                     'dc-terms:source']:
                        # need to get projects for this
                        if proj_uuid_counts is None:
                            # only get this if not gotten yet
                            print('Getting projects for ' + table_id)
                            proj_uuid_counts = self.get_table_project_uuid_counts(table_id)
                        if meta_pred == 'dc-terms:creator':
                            print('Getting creators for ' + table_id)
                            new_meta[meta_pred] = self.make_table_dc_creator_list(proj_uuid_counts)
                        if meta_pred == 'dc-terms:source':
                            print('Getting sources for ' + table_id)
                            new_meta[meta_pred] = self.make_table_project_uri_counts_list(proj_uuid_counts)
                    if meta_pred == 'dc-terms:subject':
                        print('Getting subjects for ' + table_id)
                        new_meta[meta_pred] = self.make_table_dc_subject_category_list(table_id)
            for meta_key, old_meta_val in old_meta.items():
                if meta_key not in new_meta:
                    print('Setting old metadata ' + meta_key + '   for ' + table_id)
                    new_meta[meta_key] = old_meta_val
            ex_tab.meta_json = new_meta
            json_str = json.dumps(ex_tab.meta_json,
                                  indent=4,
                                  ensure_ascii=False)
            print(str(unidecode(json_str)))
            ex_tab.save()

    def make_table_dc_contributor_list(self, table_id):
        """ gets a list of dc-contributors from the counts
            of authors in the author field
        """
        dc_contribs = []
        sorted_author_list = self.get_table_author_counts(table_id)
        for s_author in sorted_author_list:
            i = len(dc_contribs) + 1
            item = LastUpdatedOrderedDict()
            item['id'] = '#contributor-' + str(i)
            item['rdfs:isDefinedBy'] = URImanagement.make_oc_uri(s_author['uuid'], 'persons')
            item['label'] = s_author['label']
            item['count'] = s_author['count']
            dc_contribs.append(item)
        return dc_contribs

    def get_table_author_counts(self, table_id):
        """ gets author names (and uuids) for a table
            does not bother with order because
            some author cell values will have multiple
            authors.
            Once authors have UUIDs looked up, and have their
            counts counted, then we put them in a reverse sorted
            list
        """
        authors_lookup = {}
        authors = {}
        raw_authors = ExpCell.objects\
                             .filter(table_id=table_id,
                                     field_num=self.authors_field)\
                             .values('project_uuid', 'record')\
                             .annotate(num_uuids=Count('uuid', distinct=True))
        for raw_author_cell in raw_authors:
            project_uuid = raw_author_cell['project_uuid']
            raw_author = raw_author_cell['record']
            uuid_count = raw_author_cell['num_uuids']
            if project_uuid not in authors_lookup:
                authors_lookup[project_uuid] = {}
            if ';' in raw_author:
                author_ex = raw_author.split(';')
            else:
                author_ex = [raw_author]
            for author in author_ex:
                author = author.strip()
                # print('Check: ' + str(unidecode(author)))
                if author not in authors_lookup[project_uuid]:
                    a_man_objs = Manifest.objects\
                                         .filter(project_uuid=project_uuid,
                                                 label=author)[:1]
                    if len(a_man_objs) > 0:
                        authors_lookup[project_uuid][author] = a_man_objs[0]
                    else:
                        authors_lookup[project_uuid][author] = False
                if authors_lookup[project_uuid][author] is not False:
                    if author not in authors:
                        authors[author] = {'uuid': authors_lookup[project_uuid][author].uuid,
                                           'project_uuid': project_uuid,
                                           'label': author,
                                           'count': 0}
                    authors[author]['count'] += uuid_count
        author_sorts = []
        authors_by_sort_keys = {}
        for author_key, author_item in authors.items():
            count_key = self.prepend_zeros(author_item['count'], 9) + ' ' + str(author_key)
            author_sorts.append(count_key)
            authors_by_sort_keys[count_key] = author_item
        sorted_author_list = []
        for count_key in sorted(author_sorts, reverse=True):
            act_author = authors_by_sort_keys[count_key]
            sorted_author_list.append(act_author)
        return sorted_author_list

    def make_table_dc_subject_category_list(self, table_id):
        """ gets category names (and uris) for a table
        """
        category_counts = []
        raw_cat_counts = ExpCell.objects\
                                .filter(table_id=table_id,
                                        field_num=self.category_field)\
                                .values('record')\
                                .annotate(num_uuids=Count('uuid', distinct=True))\
                                .order_by('-num_uuids')
        i = 0
        for raw_cat_count in raw_cat_counts:
            label = raw_cat_count['record']
            ld_ents = LinkEntity.objects\
                                .filter(label=label,
                                        vocab_uri=self.cat_vocab_uri)[:1]
            if len(ld_ents) > 0:
                i = len(category_counts) + 1
                item = LastUpdatedOrderedDict()
                item['id'] = '#category-' + str(i)
                item['rdfs:isDefinedBy'] = ld_ents[0].uri
                item['label'] = label
                item['count'] = raw_cat_count['num_uuids']
                category_counts.append(item)
        return category_counts

    def get_table_project_uuid_counts(self, table_id):
        """ gets project uuids and counts for a table, in
            descending order of counts
        """
        proj_uuid_counts = ExpCell.objects\
                                  .filter(table_id=table_id)\
                                  .values('project_uuid')\
                                  .annotate(num_uuids=Count('uuid', distinct=True))\
                                  .order_by('-num_uuids')
        return proj_uuid_counts

    def make_table_dc_creator_list(self, proj_uuid_counts):
        """ makes a list of dublin core creators
            from a project uuid + counts list """
        dc_creators = []
        for proj_uuid_count in proj_uuid_counts:
            project_uuid = proj_uuid_count['project_uuid']
            auth = Authorship()
            auth.get_project_authors(project_uuid)
            if len(auth.creators) < 1 and \
               len(auth.contributors) > 0:
                auth.creators = auth.contributors
            if len(auth.creators) > 0:
                for auth_uuid in auth.creators:
                    auth_man = False
                    try:
                        auth_man = Manifest.objects.get(uuid=auth_uuid)
                    except Manifest.DoesNotExist:
                        auth_man = False
                    if auth_man is not False:
                        i = len(dc_creators) + 1
                        item = LastUpdatedOrderedDict()
                        item['id'] = '#creator-' + str(i)
                        item['rdfs:isDefinedBy'] = URImanagement.make_oc_uri(auth_uuid, 'persons')
                        item['label'] = auth_man.label
                        item['count'] = proj_uuid_count['num_uuids']
                        dc_creators.append(item)
        return dc_creators

    def make_table_project_uri_counts_list(self, proj_uuid_counts):
        """ makes a list of project URIs with labels
            and counts of records
        """
        project_list = []
        i = 0
        for proj_uuid_count in proj_uuid_counts:
            i = len(project_list) + 1
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
            if ExpTable.PREDICATE_DUMP in ex_tab.meta_json:
                ex_tab.meta_json.pop(ExpTable.PREDICATE_DUMP, None)
            if ExpTable.PREDICATE_DUMP not in ex_tab.meta_json:
                # no predicate for a data dump, so look for it
                dump_list = []
                old_file_uri = self.temp_table_base_url + ex_tab.table_id + '.csv'
                new_file_uri = self.rev_table_base_url + ex_tab.table_id + '.csv'
                sleep(self.delay_before_request)
                mm = ManageMediafiles()
                ok_old = mm.get_head_info(old_file_uri)
                if ok_old:
                    dump_item = LastUpdatedOrderedDict()
                    dump_item['id'] = old_file_uri
                    dump_item['dc-terms:hasFormat'] = mm.mime_type_uri
                    dump_item['dcat:size'] = float(mm.filesize)
                    dump_item['dc-terms:isReplacedBy'] = new_file_uri
                    print('Found: ' + str(dump_item))
                    dump_list.append(dump_item)
                sleep(self.delay_before_request)
                mm = ManageMediafiles()
                ok_new = mm.get_head_info(new_file_uri)
                if ok_new:
                    dump_item = LastUpdatedOrderedDict()
                    dump_item['id'] = old_file_uri
                    dump_item['dc-terms:hasFormat'] = mm.mime_type_uri
                    dump_item['dcat:size'] = float(mm.filesize)
                    dump_item['dc-terms:replaces'] = old_file_uri
                    print('Found: ' + str(dump_item))
                    dump_list.append(dump_item)
                if ok_old and ok_new:
                    ex_tab.meta_json[ExpTable.PREDICATE_DUMP] = dump_list
                    ex_tab.save()

    def dump_tables(self):
        """ Prepares a directory to find import GeoJSON files """
        ex_tabs = ExpTable.objects.all()
        for ex_tab in ex_tabs:
            csv_dump = CSVdump()
            csv_dump.table_export_dir = 'export-csv-tables'
            filename = ex_tab.table_id + '.csv'
            directory = csv_dump.prep_directory()
            dir_file = os.path.join(directory,
                                    filename)
            if not os.path.exists(dir_file):
                csv_dump.dump(ex_tab.table_id,
                              filename)

    def prepend_zeros(self, val, digit_length):
        """ prepends zeros if too short """
        val = str(val)
        if len(val) < digit_length:
            while len(val) < digit_length:
                val = '0' + val
        return val
