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
from opencontext_py.apps.exports.exptables.identifiers import ExpTableIdentifiers
from opencontext_py.apps.ocitems.mediafiles.models import ManageMediafiles
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.ldata.linkentities.models import LinkEntity
from opencontext_py.apps.ldata.linkannotations.authorship import Authorship
from opencontext_py.apps.ldata.linkannotations.models import LinkAnnotation
from opencontext_py.apps.exports.exprecords.dump import CSVdump


class ExpManage():
    """ Methods to manage export tables. Currently this feature is
        still in development. We're mainly supporting
        access to table dumps from the previous version
        of Open Context

from opencontext_py.apps.exports.exptables.manage import ExpManage
ex_man = ExpManage()
ex_man.reduce_lat_lon_precision('b5f81371-35db-4644-b353-3f5648eeb222')
ex_man.reduce_lat_lon_precision('ea16a444-9876-4fe7-8ffb-389b54a7e3a0')
ex_man.generate_table_metadata('05f2db65ff4faee1290192bd9a1868ed', True)


from opencontext_py.apps.exports.exptables.manage import ExpManage
ex_man = ExpManage()
table_id = '0c14c4ad-fce9-4291-a605-8c065d347c5d'
file_uri = 'https://archive.org/download/oc-table-0c14c4ad-fce9-4291-a605-8c065d347c5d/oc-table-0c14c4ad-fce9-4291-a605-8c065d347c5d.zip'
file_uri = 'https://artiraq.org/static/opencontext/tables/oc-table-0c14c4ad-fce9-4291-a605-8c065d347c5d.zip'
file_uri = 'https://artiraq.org/static/opencontext/tables/oc-table-0c14c4ad-fce9-4291-a605-8c065d347c5d.csv'
ex_man.add_table_file_download(table_id, file_uri)

    """

    SLEEP_TIME = .5

    def __init__(self):
        self.delay_before_request = self.SLEEP_TIME
        self.authors_field = 7
        self.category_field = 5
        self.project_to_table_predicate = 'dc-terms:isReferencedBy'
        self.cat_vocab_uri = 'http://opencontext.org/vocabularies/oc-general/'
        self.temp_table_base_url = 'http://artiraq.org/static/opencontext/tables/'
        self.rev_table_base_url = 'http://artiraq.org/static/opencontext/revised-tables/'
        self.metadata_predicates = ['dc-terms:contributor',
                                    'dc-terms:creator',
                                    'dc-terms:source',
                                    'dc-terms:subject']

    def link_table_to_projects(self, table_id):
        """ links a table to a project """
        ex_id = ExpTableIdentifiers()
        ex_id.make_all_identifiers(table_id)
        proj_uuid_counts = self.get_table_project_uuid_counts(ex_id.table_id)
        for proj_uuid_count in proj_uuid_counts:
            project_uuid = proj_uuid_count['project_uuid']
            la_recs = LinkAnnotation.objects\
                                    .filter(subject=project_uuid,
                                            object_uri=ex_id.uri)[:1]
            if len(la_recs) < 1:
                # we don't have a relationship between this project and this
                # table yet, so OK to create it.
                la = LinkAnnotation()
                la.subject = project_uuid
                la.subject_type = 'projects'
                la.project_uuid = project_uuid
                la.source_id = 'exp-tables-management'
                la.predicate_uri = self.project_to_table_predicate
                la.object_uri = ex_id.uri
                la.creator_uuid = ''
                la.save()
                print('Linked project: ' + project_uuid + ' to ' + ex_id.uri)

    def save_table_manifest_record(self, table_id):
        """ saves a table (public-id) record
            to the manifest
        """
        ex_id = ExpTableIdentifiers()
        ex_id.make_all_identifiers(table_id)
        tab_obj = False
        try:
            tab_obj = ExpTable.objects.get(table_id=ex_id.table_id)
        except Manifest.DoesNotExist:
            tab_obj = False
        if tab_obj is not False:
            man_list = Manifest.objects\
                               .filter(uuid=ex_id.public_table_id)[:1]
            if len(man_list) < 1:
                project_uuid = '0'  # default to all projects
                proj_uuid_counts = self.get_table_project_uuid_counts(ex_id.table_id)
                if len(proj_uuid_counts) == 1:
                    project_uuid = proj_uuid_counts[0]['project_uuid']
                man_obj = Manifest()
                man_obj.uuid = ex_id.public_table_id
                man_obj.project_uuid = project_uuid
                man_obj.source_id = 'exp-tables-management'
                man_obj.item_type = 'tables'
                man_obj.class_uri = ''
                man_obj.label = tab_obj.label
                man_obj.save()
                print('Manifest saved table: ' + str(unidecode(man_obj.label)))
            else:
                man_obj = man_list[0]
                if man_obj.label != tab_obj.label:
                    man_obj.label = tab_obj.label
                    man_obj.save()
                    print('Manifest updated for table: ' + str(unidecode(man_obj.label)))
                else:
                    print('Manifest all ready current for table: ' + str(unidecode(man_obj.label)))

    def generate_table_metadata(self, table_id, overwrite=False):
        """ makes metadata for a specific table """
        ex_id = ExpTableIdentifiers()
        ex_id.make_all_identifiers(table_id)
        table_ids = [ex_id.table_id,
                     ex_id.public_table_id]
        try:
            ex_tab = ExpTable.objects.get(table_id=table_id)
        except ExpTable.DoesNotExist:
            print('No ExpTable object for: ' + ex_id.public_table_id)
            ex_tab = None
        try:
            man_obj = Manifest.objects.get(uuid=ex_id.public_table_id)
        except Manifest.DoesNotExist:
            print('No manifest object for: ' + ex_id.public_table_id)
            man_obj = None
        if ex_tab is not None and man_obj is not None:
            proj_uuid_counts = None
            for meta_pred in self.metadata_predicates:
                if overwrite:
                    num_old_delete = LinkAnnotation.objects\
                                                   .filter(subject__in=table_ids,
                                                           predicate_uri=meta_pred)\
                                                   .delete()
                    print('Deleted annoations ' + str(num_old_delete) + ' for ' + meta_pred)
                    add_meta_for_pred = True
                else:
                    num_exists = LinkAnnotation.objects\
                                               .filter(subject__in=table_ids,
                                                       predicate_uri=meta_pred)[:1]
                    if len(num_exists) < 1:
                        add_meta_for_pred = True
                    else:
                        add_meta_for_pred = False
                if add_meta_for_pred:
                    if meta_pred == 'dc-terms:contributor':
                        print('Getting contributors for ' + table_id)
                        sorted_author_list = self.get_table_author_counts(table_id)
                        contrib_sort = 0
                        for s_author in sorted_author_list:
                            contrib_sort += 1
                            obj_extra = LastUpdatedOrderedDict()
                            obj_extra['count'] = s_author['count']
                            la = LinkAnnotation()
                            la.subject = man_obj.uuid
                            la.subject_type = man_obj.item_type
                            la.project_uuid = man_obj.project_uuid
                            la.source_id = 'exp-table-manage'
                            la.predicate_uri = meta_pred
                            la.object_uri = URImanagement.make_oc_uri(s_author['uuid'], 'persons')
                            la.creator_uuid = '0'
                            la.sort = contrib_sort
                            la.obj_extra = obj_extra
                            la.save()
                    if meta_pred in ['dc-terms:creator',
                                     'dc-terms:source']:
                        # need to get projects for this
                        if proj_uuid_counts is None:
                            # only get this if not gotten yet
                            print('Getting projects for ' + table_id)
                            proj_uuid_counts = self.get_table_project_uuid_counts(table_id)
                        if meta_pred == 'dc-terms:creator':
                            print('Getting creators for ' + table_id)
                            dc_creator_list = self.make_table_dc_creator_list(proj_uuid_counts)
                            create_sort = 0
                            for dc_creator in dc_creator_list:
                                create_sort += 1
                                obj_extra = LastUpdatedOrderedDict()
                                obj_extra['count'] = dc_creator['count']
                                la = LinkAnnotation()
                                la.subject = man_obj.uuid
                                la.subject_type = man_obj.item_type
                                la.project_uuid = man_obj.project_uuid
                                la.source_id = 'exp-table-manage'
                                la.predicate_uri = meta_pred
                                la.object_uri = dc_creator['id']
                                la.creator_uuid = '0'
                                la.sort = create_sort
                                la.obj_extra = obj_extra
                                la.save()
                        if meta_pred == 'dc-terms:source':
                            print('Getting sources for ' + table_id)
                            proj_sort = 0
                            for proj_uuid_count in proj_uuid_counts:
                                proj_sort += 1
                                obj_extra = LastUpdatedOrderedDict()
                                obj_extra['count'] = proj_uuid_count['num_uuids']
                                la = LinkAnnotation()
                                la.subject = man_obj.uuid
                                la.subject_type = man_obj.item_type
                                la.project_uuid = man_obj.project_uuid
                                la.source_id = 'exp-table-manage'
                                la.predicate_uri = meta_pred
                                la.object_uri = URImanagement.make_oc_uri(proj_uuid_count['project_uuid'],
                                                                          'projects')
                                la.creator_uuid = '0'
                                la.sort = proj_sort
                                la.obj_extra = obj_extra
                                la.save()
                    if meta_pred == 'dc-terms:subject':
                        print('Getting subjects for ' + table_id)
                        dc_subject_list = self.make_table_dc_subject_category_list(table_id)
                        subj_sort = 0
                        for dc_subject in dc_subject_list:
                            subj_sort += 1
                            obj_extra = LastUpdatedOrderedDict()
                            obj_extra['count'] = dc_subject['count']
                            la = LinkAnnotation()
                            la.subject = man_obj.uuid
                            la.subject_type = man_obj.item_type
                            la.project_uuid = man_obj.project_uuid
                            la.source_id = 'exp-table-manage'
                            la.predicate_uri = meta_pred
                            la.object_uri = dc_subject['id']
                            la.creator_uuid = '0'
                            la.sort = subj_sort
                            la.obj_extra = obj_extra
                            la.save()

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
                item['id'] = ld_ents[0].uri
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
            proj_count = proj_uuid_count['num_uuids']
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
                        item['id'] = URImanagement.make_oc_uri(auth_uuid, 'persons')
                        item['count'] = proj_count
                        dc_creators.append(item)
        return dc_creators

    def add_table_file_download(self, table_id, file_uri):
        """ adds a file_uri for a pre-cached table download """
        ex_tabs = ExpTable.objects.filter(table_id=table_id)[:1]
        for ex_tab in ex_tabs:
            if ExpTable.PREDICATE_DUMP in ex_tab.meta_json:
                dump_list = ex_tab.meta_json[ExpTable.PREDICATE_DUMP]
            else:
                # no predicate for a data dump, so look for it
                dump_list = []
            mm = ManageMediafiles()
            ok = mm.get_head_info(file_uri)
            if ok:
                dump_item = LastUpdatedOrderedDict()
                dump_item['id'] = file_uri
                dump_item['dc-terms:hasFormat'] = mm.mime_type_uri
                dump_item['dcat:size'] = float(mm.filesize)
                print('Found: ' + str(dump_item))
                dump_list.append(dump_item)
                ex_tab.meta_json[ExpTable.PREDICATE_DUMP] = dump_list
                ex_tab.save()
                man_items = Manifest.objects.filter(uuid=table_id)[:1]
                if len(man_items) > 0:
                    man_obj = man_items[0]
                    new_anno = LinkAnnotation()
                    new_anno.subject = man_obj.uuid
                    new_anno.subject_type = man_obj.item_type
                    new_anno.project_uuid = man_obj.project_uuid
                    new_anno.source_id = 'download-file-relate'
                    new_anno.predicate_uri = ExpTable.PREDICATE_DUMP
                    new_anno.object_uri = file_uri
                    new_anno.sort = len(dump_list)
                    new_anno.obj_extra = dump_item
                    new_anno.save()
                    

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
                    dump_item['id'] = new_file_uri
                    dump_item['dc-terms:hasFormat'] = mm.mime_type_uri
                    dump_item['dcat:size'] = float(mm.filesize)
                    dump_item['dc-terms:replaces'] = old_file_uri
                    print('Found: ' + str(dump_item))
                    dump_list.append(dump_item)
                if ok_old and ok_new:
                    ex_tab.meta_json[ExpTable.PREDICATE_DUMP] = dump_list
                    ex_tab.save()

    def reduce_lat_lon_precision(self, table_id, places=6):
        """ gets rid of annoying floating point errors that
            give too much precision to coordinate numbers
        """
        act_fields = [8,9]
        lat_lons = ExpCell.objects\
                          .filter(table_id=table_id,
                                  field_num__in=act_fields)
        for lat_lon in lat_lons:
            if len(lat_lon.record) > 0:
                val = float(lat_lon.record)
                new_val = round(val, places)
                lat_lon.record = str(new_val)
                lat_lon.save()

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
