import os
import json
import codecs
from itertools import islice
from django.db import models
from django.conf import settings
from django.core import serializers
from datetime import datetime
from django.utils import timezone
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.ocitems.assertions.models import Assertion
from opencontext_py.apps.ocitems.events.models import Event
from opencontext_py.apps.ocitems.geospace.models import Geospace
from opencontext_py.apps.ocitems.obsmetadata.models import ObsMetadata
from opencontext_py.apps.ocitems.predicates.models import Predicate
from opencontext_py.apps.ocitems.octypes.models import OCtype
from opencontext_py.apps.ocitems.strings.models import OCstring
from opencontext_py.apps.ocitems.subjects.models import Subject
from opencontext_py.apps.ocitems.mediafiles.models import Mediafile
from opencontext_py.apps.ocitems.documents.models import OCdocument
from opencontext_py.apps.ocitems.persons.models import Person
from opencontext_py.apps.ocitems.projects.models import Project
from opencontext_py.apps.ocitems.identifiers.models import StableIdentifer
from opencontext_py.apps.ldata.linkannotations.models import LinkAnnotation
from opencontext_py.apps.ldata.linkentities.models import LinkEntity
from opencontext_py.apps.entities.redirects.models import RedirectMapping
from opencontext_py.apps.exports.expfields.models import ExpField
from opencontext_py.apps.exports.exprecords.models import ExpCell
from opencontext_py.apps.exports.exptables.models import ExpTable
from opencontext_py.apps.edit.inputs.profiles.models import InputProfile
from opencontext_py.apps.edit.inputs.fieldgroups.models import InputFieldGroup
from opencontext_py.apps.edit.inputs.inputrelations.models import InputRelation
from opencontext_py.apps.edit.inputs.inputfields.models import InputField
from opencontext_py.apps.edit.inputs.rules.models import InputRule


# Outputs and writes files of serialized JSON for models
# associated with a given project
class SerizializeJSON():
    """

from opencontext_py.apps.exports.serialization.models import SerizializeJSON
sj = SerizializeJSON()
sj.dump_serialized_rel_tables()


from opencontext_py.apps.exports.serialization.models import SerizializeJSON
project_uuid = 'DF043419-F23B-41DA-7E4D-EE52AF22F92F'
sj = SerizializeJSON()
sj.export_redirects = True
sj.limit_source_ids = [
    'kobo-pc-2018-all-contexts-subjects.csv',
    'kobo-pc-2018-all-media',
    'kobo-pc-2018-bulk-finds',
    'kobo-pc-2018-catalog',
    'kobo-pc-2018-links-catalog',
    'kobo-pc-2018-links-locus-strat',
    'kobo-pc-2018-links-media',
    'kobo-pc-2018-locus',
    'kobo-pc-2018-small-finds',
    'kobo-pc-2018-trench-book'
]
sj.dump_serialized_data(project_uuid)


from opencontext_py.apps.exports.serialization.models import SerizializeJSON
project_uuid = 'DF043419-F23B-41DA-7E4D-EE52AF22F92F'
sj = SerizializeJSON()
sj.export_redirects = True
# sj.after_date = '2017-02-25'
# sj.limit_export_table_id = '0c14c4ad-fce9-4291-a605-8c065d347c5d'
sj.dump_serialized_data(project_uuid)

from opencontext_py.apps.exports.serialization.models import SerizializeJSON
sj = SerizializeJSON()
sj.act_export_dir = '/home/dainst_ekansa'
sj.dump_serialize_recent_projects("2015-06-01")
sj.dump_serialized_data("3885b0b6-2ba8-4d19-b597-7f445367c5c0")

from opencontext_py.apps.exports.serialization.models import SerizializeJSON
sj = SerizializeJSON()
sj.after_date = '2016-12-25'
sj.limit_file_types = ['oc-gen:ia-fullfile', 'oc-gen:iiif']
sj.dump_project_table('0', 'oc_mediafiles')

from opencontext_py.apps.exports.serialization.models import SerizializeJSON
sj = SerizializeJSON()
sj.after_date = '2016-12-10'
sj.dump_serialized_annotations('fed-reg-api-lookup')

projects = Project.objects.filter(updated__gte="2015-06-01")

    """
    def __init__(self):
        self.root_export_dir = settings.STATIC_EXPORTS_ROOT
        self.project_uuid = False
        self.after_date = False
        self.chunk_size = 5000
        self.export_redirects = False
        self.act_export_dir = False
        self.limit_source_ids = []
        self.limit_item_types = False
        self.limit_file_types = False  # limit media export to a few file_types
        self.limit_export_table_id = False # limit to data related to an export table
        self.all_models = [
            'link_entities',
            'oc_redirects'
        ]
        self.project_models = ['oc_assertions',
                               'oc_documents',
                               'oc_events',
                               'oc_geospace',
                               'oc_identifiers',
                               'oc_manifest',
                               'oc_mediafiles',
                               'oc_obsmetadata',
                               'oc_persons',
                               'oc_predicates',
                               'oc_projects',
                               'oc_strings',
                               'oc_subjects',
                               'oc_types',
                               'exp_fields',
                               'exp_records',
                               'exp_tables',
                               'crt_fieldgroups',
                               'crt_fields',
                               'crt_profiles',
                               'crt_relations',
                               'crt_rules',
                               'link_annotations']
        self.table_models = ['oc_manifest',
                             'exp_tables',
                             'link_annotations']
        self.source_id_tabs = [
            'oc_assertions',
            'oc_documents',
            'oc_events',
            'oc_geospace',
            'oc_manifest',
            'oc_mediafiles',
            'oc_obsmetadata',
            'oc_persons',
            'oc_predicates',
            'oc_projects',
            'oc_strings',
            'oc_subjects',
            'oc_types',
            'link_annotations',
        ]

    def check_table_qset(self,
                         table_name,
                         start,
                         end):
        """ test a queryset output """
        query_set = self.get_queryset(table_name,
                                      start,
                                      end)
        print(table_name + ' has ' + str(len(query_set)))

    def dump_serialize_recent_projects(self, after_date):
        """ Finds projects that have been recently created,
            dumps them in serialized JSON format
        """
        projects = Project.objects\
                          .filter(updated__gte=after_date)\
                          .iterator()
        for proj in projects:
            man_proj = Manifest.objects\
                               .filter(item_type='projects',
                                       uuid=proj.uuid)[:1]
            if len(man_proj) > 0:
                if len(proj.label) < 1:
                    proj.label = man_proj[0].label
                    proj.save()
                print('Output: ' + str(man_proj[0].slug) + ' (' + str(proj.uuid) + ')')
                self.dump_serialized_data(proj.uuid)

    def dump_serialized_rel_tables(self):
        """ dumps serialized data documenting tables """
        self.limit_item_types = ['tables']
        proj_dir = self.prep_directory('rel-tabs')
        if proj_dir is not False:
            table_list = self.all_models + self.table_models
            for table_name in table_list:
                print('Working on ' + table_name + ' for export tables')
                batch = 1
                query_set = self.get_queryset(table_name)
                if query_set is not False and query_set is not None:
                    act_set = []
                    for obj in query_set.iterator():
                        if len(act_set) < self.chunk_size:
                            act_set.append(obj)
                        if len(act_set) >= self.chunk_size:
                            self.save_serialized_json_batch(proj_dir, table_name, batch, act_set)
                            batch = batch + 1
                            act_set = []  # start the act set from scratch again
                    if len(act_set) > 0:
                        # now save the remaining batch
                        self.save_serialized_json_batch(proj_dir, table_name, batch, act_set)

    def dump_serialized_data(self, project_uuid):
        """ dumps serialized data for a projproect """
        proj_dir = self.prepare_dump_directory(project_uuid)
        if proj_dir is not False:
            # we're good to go to dump data
            table_list = self.all_models + self.project_models
            for table_name in table_list:
                print('Working on ' + table_name + ' for ' + project_uuid)
                batch = 1
                query_set = self.get_queryset(table_name)
                if query_set is not False and query_set is not None:
                    act_set = []
                    for obj in query_set.iterator():
                        if len(act_set) < self.chunk_size:
                            act_set.append(obj)
                        if len(act_set) >= self.chunk_size:
                            self.save_serialized_json_batch(proj_dir, table_name, batch, act_set)
                            batch = batch + 1
                            act_set = []  # start the act set from scratch again
                    if len(act_set) > 0:
                        # now save the remaining batch
                        self.save_serialized_json_batch(proj_dir, table_name, batch, act_set)  
    
    def dump_project_table(self, project_uuid, table_name):
        """ dumps a specific table for a given project """
        proj_dir = self.prepare_dump_directory(project_uuid)
        if proj_dir is not False:
            # we're good to go to dump data
            if project_uuid == '0':
                self.project_uuid = False
            print('Working on ' + table_name + ' for ' + project_uuid)
            batch = 1
            query_set = self.get_queryset(table_name)
            if query_set is not False and query_set is not None:
                act_set = []
                for obj in query_set.iterator():
                    if len(act_set) < self.chunk_size:
                        act_set.append(obj)
                    if len(act_set) >= self.chunk_size:
                        self.save_serialized_json_batch(proj_dir, table_name, batch, act_set)
                        batch = batch + 1
                        act_set = []  # start the act set from scratch again
                if len(act_set) > 0:
                    # now save the remaining batch
                    self.save_serialized_json_batch(proj_dir, table_name, batch, act_set)

    def dump_serialized_annotations(self, source_ids=None):
        """ dumps serialized data for a given source """
        if not isinstance(source_ids, list):
            if isinstance(source_ids, str):
                source_ids = [source_ids]
        proj_dir = self.prepare_dump_directory('0')
        if proj_dir is not False:
            # we're good to go to dump data
            table_list = ['link_annotations']
            for table_name in table_list:
                print('Working on ' + table_name + ' for ' + str(source_ids))
                batch = 1
                args = {}
                if isinstance(source_ids, list):
                    args['source_id__in'] = source_ids
                if self.after_date is not False:
                    args['updated__gte'] = self.after_date
                if len(args) > 0:
                    query_set = LinkAnnotation.objects\
                                              .filter(**args)
                else:
                    query_set = LinkAnnotation.objects.all()
                if query_set is not False and query_set is not None:
                    act_set = []
                    for obj in query_set.iterator():
                        if len(act_set) < self.chunk_size:
                            act_set.append(obj)
                        if len(act_set) >= self.chunk_size:
                            self.save_serialized_json_batch(proj_dir, table_name, batch, act_set)
                            batch = batch + 1
                            act_set = []  # start the act set from scratch again
                    if len(act_set) > 0:
                        # now save the remaining batch
                        self.save_serialized_json_batch(proj_dir, table_name, batch, act_set)
    
    def save_serialized_json_batch(self, proj_dir, table_name, batch, act_set):
        """ saves a batch of data, serialized as JSON """
        JSONserializer = serializers.get_serializer('json')
        json_serializer = JSONserializer()
        filename = table_name + '-' + self.prepend_zeros(str(batch), 5) + '.json'
        file_path = proj_dir + filename
        data = json_serializer.serialize(act_set,
                                         ensure_ascii=False)
        json_output = json.dumps(data,
                                 indent=4,
                                 ensure_ascii=False)
        file = codecs.open(file_path, 'w', 'utf-8')
        # file.write(codecs.BOM_UTF8)
        file.write(json_output)
        file.close()

    def get_queryset(self, table_name):
        """ gets the query set for a specific
            model. 
        """
        query_set = False
        if table_name in self.all_models:
            if table_name == 'link_entities':
                query_set = LinkEntity.objects.all()
            elif table_name == 'oc_redirects' and self.export_redirects:
                query_set = RedirectMapping.objects.all()
            else:
                query_set = False
        elif table_name in self.project_models or \
             table_name in self.table_models:
            # the table name is for a model
            # that is filtered by the project_uuid
            args = {}
            if self.project_uuid is not False:
                args['project_uuid__in'] = [self.project_uuid,
                                            '0']
            if self.after_date is not False:
                if table_name != 'oc_manifest':
                    args['updated__gte'] = self.after_date
                else:
                    # oc_manifest is different
                    args['record_updated__gte'] = self.after_date
            if self.limit_item_types is not False:
                if table_name == 'oc_manifest':
                    args['item_type__in'] = self.limit_item_types
                if table_name == 'oc_assertions':
                    args['subject_type__in'] = self.limit_item_types
                if len(self.limit_item_types) == 1 and \
                   self.limit_item_types[0] == 'tables':
                    if table_name == 'link_annotations':
                        args['object_uri__contains'] = '/tables/'
            if isinstance(self.limit_export_table_id, str):
                # limit to records relating to an export table
                uuid_tabs = [
                    'oc_manifest',
                    'oc_identifiers',
                    'oc_assertions'
                ]
                exp_tab_tabs = [
                    'exp_tables',
                    'exp_fields',
                    'exp_records'
                ]
                if table_name in exp_tab_tabs:
                    # get all the records associated with the export table
                    args = {}
                    args['table_id'] = self.limit_export_table_id
                elif table_name in uuid_tabs:
                    # just get the manifest record for the export table
                    args = {}
                    args['uuid'] = self.limit_export_table_id
                elif table_name == 'link_annotations':
                    # just get the manifest record for the export table
                    args = {}
                    args['subject'] = self.limit_export_table_id
                else:
                    # then we don't want any other outputs
                   table_name = False
            
            if (table_name in self.source_id_tabs
                and self.limit_source_ids):
                args['source_id__in'] = self.limit_source_ids
            if table_name == 'oc_assertions':
                query_set = Assertion.objects\
                                     .filter(**args)
            elif table_name == 'oc_documents':
                query_set = OCdocument.objects\
                                      .filter(**args)
            elif table_name == 'oc_events':
                query_set = Event.objects\
                                 .filter(**args)
            elif table_name == 'oc_geospace':
                query_set = Geospace.objects\
                                    .filter(**args)
            elif table_name == 'oc_identifiers':
                query_set = StableIdentifer.objects\
                                           .filter(**args)
            elif table_name == 'oc_manifest':
                query_set = Manifest.objects\
                                    .filter(**args)
            elif table_name == 'oc_mediafiles':
                if isinstance(self.limit_file_types, list):
                    # we want to limit the export to only certain file_types
                    args['file_type__in'] = self.limit_file_types
                query_set = Mediafile.objects\
                                     .filter(**args)
            elif table_name == 'oc_obsmetadata':
                query_set = ObsMetadata.objects\
                                       .filter(**args)
            elif table_name == 'oc_persons':
                query_set = Person.objects\
                                  .filter(**args)
            elif table_name == 'oc_predicates':
                query_set = Predicate.objects\
                                     .filter(**args)
            elif table_name == 'oc_projects':
                query_set = Project.objects\
                                   .filter(**args)
            elif table_name == 'oc_strings':
                query_set = OCstring.objects\
                                    .filter(**args)
            elif table_name == 'oc_subjects':
                query_set = Subject.objects\
                                   .filter(**args)
            elif table_name == 'oc_types':
                query_set = OCtype.objects\
                                  .filter(**args)
            elif table_name == 'exp_fields':
                dist_tables = ExpCell.objects\
                                     .filter(**args)\
                                     .values_list('table_id', flat=True)\
                                     .distinct()
                query_set = ExpField.objects\
                                    .filter(table_id__in=dist_tables)
            elif table_name == 'exp_records':
                query_set = ExpCell.objects\
                                   .filter(**args)
            elif table_name == 'exp_tables':
                dist_tables = ExpCell.objects\
                                     .filter(**args)\
                                     .values_list('table_id', flat=True)\
                                     .distinct()
                query_set = ExpTable.objects\
                                    .filter(table_id__in=dist_tables)
            elif table_name == 'crt_fieldgroups':
                query_set = InputFieldGroup.objects\
                                           .filter(**args)
            elif table_name == 'crt_fields':
                query_set = InputField.objects\
                                      .filter(**args)
            elif table_name == 'crt_profiles':
                query_set = InputProfile.objects\
                                        .filter(**args)
            elif table_name == 'crt_relations':
                query_set = InputRelation.objects\
                                         .filter(**args)
            elif table_name == 'crt_rules':
                query_set = InputRule.objects\
                                     .filter(**args)
            elif table_name == 'link_annotations':
                query_set = LinkAnnotation.objects\
                                          .filter(**args)
            else:
                query_set = False
        return query_set

    def prep_directory(self, act_dir):
        """ Prepares a directory to receive export files """
        output = False
        full_dir = self.root_export_dir + act_dir + '/'
        if self.act_export_dir is not False:
            full_dir = self.act_export_dir + '/' + act_dir
        full_dir.replace('//', '/')
        if not os.path.exists(full_dir):
            os.makedirs(full_dir)
        if os.path.exists(full_dir):
            output = full_dir
        if output[-1] != '/':
            output += '/'
        print('Prepared directory: ' + str(output))
        return output

    def prepare_dump_directory(self, project_uuid):
        """ Prepares a directory to receive
            export files, using the project
            slug as the directory name
        """
        proj_dir = False
        man_proj = Manifest.objects\
                           .filter(item_type='projects',
                                   uuid=project_uuid)[:1]
        if len(man_proj) > 0:
            # the project exists, so lets make a directory for it!
            slug = man_proj[0].slug
            self.project_uuid = project_uuid
            proj_dir = self.prep_directory(slug)
        elif project_uuid == '0':
            self.project_uuid = project_uuid
            proj_dir = self.prep_directory('oc-dump')
        return proj_dir

    def export_project_meta(self):
        """ Exports projects """
        man_projs = Manifest.objects.filter(item_type='projects')
        for man_proj in man_projs:
            uuid = man_proj.uuid
            slug = man_proj.slug
            # proj_dir = self.prep_directory(slug)
            # proj_file = proj_dir + slug + '.json'
            proj_dir = self.prep_directory(slug)
            proj_file = proj_dir + uuid + '.json'
            ocitem = OCitem()
            ocitem.get_item(uuid)
            json_output = json.dumps(ocitem.json_ld,
                                     indent=4,
                                     ensure_ascii=False)
            file = codecs.open(proj_file, 'w', 'utf-8')
            file.write(json_output)
            file.close()

    def prepend_zeros(self, num_id_part, digit_length):
        """ prepends zeros if too short """
        num_id_part = str(num_id_part)
        if digit_length is not False:
            if len(num_id_part) < digit_length:
                while len(num_id_part) < digit_length:
                    num_id_part = '0' + num_id_part
        return num_id_part
