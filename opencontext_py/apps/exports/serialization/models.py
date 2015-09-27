import os
import json
import codecs
from django.db import models
from django.conf import settings
from django.core import serializers
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
sj.act_export_dir = '/home/dainst_ekansa'
sj.dump_serialize_recent_projects("2015-06-01")
sj.dump_serialized_data("3885b0b6-2ba8-4d19-b597-7f445367c5c0")

projects = Project.objects.filter(updated__gte="2015-06-01")

    """
    def __init__(self):
        self.root_export_dir = settings.STATIC_EXPORTS_ROOT
        self.project_uuid = False
        self.after_date = False
        self.chunk_size = 2500
        self.act_export_dir = False
        self.all_models = ['link_entities']
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
                          .filter(updated__gte=after_date)
        for proj in projects:
            if len(proj.label) < 1:
                man_proj = Manifest.objects\
                                   .filter(item_type='projects',
                                           uuid=proj.uuid)[:1]
                if len(man_proj) > 0:
                    proj.label = man_proj[0].label
                    proj.save()
            print('Output: ' + str(proj.label) + ' (' + str(proj.uuid) + ')')
            self.dump_serialized_data(proj.uuid)

    def dump_serialized_data(self, project_uuid):
        """ dumps serialized data for a projproect """
        proj_dir = self.prepare_dump_directory(project_uuid)
        if proj_dir is not False:
            # we're good to go to dump data
            JSONserializer = serializers.get_serializer('json')
            json_serializer = JSONserializer()
            table_list = self.all_models + self.project_models
            for table_name in table_list:
                print('Working on ' + table_name + ' for ' + project_uuid)
                file_num = 1
                do_more = True
                start = 0
                end = self.chunk_size
                batch = 1
                while do_more:
                    filename = table_name + '-' + self.prepend_zeros(str(batch), 3) + '.json'
                    file_path = proj_dir + filename
                    do_more = False
                    query_set = self.get_queryset(table_name,
                                                  start,
                                                  end)
                    if query_set is not None:
                        if len(query_set) > 0:
                            data = json_serializer.serialize(query_set,
                                                             ensure_ascii=False)
                            json_output = json.dumps(data,
                                                     indent=4,
                                                     ensure_ascii=False)
                            file = codecs.open(file_path, 'w', 'utf-8')
                            # file.write(codecs.BOM_UTF8)
                            file.write(json_output)
                            file.close()
                            """
                            with open(file_path, "w") as out:
                                json_serializer.serialize(query_set,
                                                          stream=out,
                                                          ensure_ascii=False)
                            """
                            do_more = True
                            start = end
                            end = end + self.chunk_size
                            batch = batch + 1

    def get_queryset(self, table_name, start, end):
        """ gets the query set for a specific
            model. 
        """
        query_set = False
        if table_name in self.all_models:
            if table_name == 'link_entities':
                query_set = LinkEntity.objects.all()[start:end]
            else:
                query_set = False
        elif table_name in self.project_models:
            # the table name is for a model
            # that is filtered by the project_uuid
            args = {}
            args['project_uuid__in'] = [self.project_uuid,
                                        '0']
            if self.after_date is not False:
                if table_name != 'oc_manifest':
                    args['updated__gte'] = self.after_date
                else:
                    # oc_manifest is different
                    args['record_updated__gte'] = self.after_date
            if table_name == 'oc_assertions':
                query_set = Assertion.objects\
                                     .filter(**args)[start:end]
            elif table_name == 'oc_documents':
                query_set = OCdocument.objects\
                                      .filter(**args)[start:end]
            elif table_name == 'oc_events':
                query_set = Event.objects\
                                 .filter(**args)[start:end]
            elif table_name == 'oc_geospace':
                query_set = Geospace.objects\
                                    .filter(**args)[start:end]
            elif table_name == 'oc_identifiers':
                query_set = StableIdentifer.objects\
                                           .filter(**args)[start:end]
            elif table_name == 'oc_manifest':
                query_set = Manifest.objects\
                                    .filter(**args)[start:end]
            elif table_name == 'oc_mediafiles':
                query_set = Mediafile.objects\
                                     .filter(**args)[start:end]
            elif table_name == 'oc_obsmetadata':
                query_set = ObsMetadata.objects\
                                       .filter(**args)[start:end]
            elif table_name == 'oc_persons':
                query_set = Person.objects\
                                  .filter(**args)[start:end]
            elif table_name == 'oc_predicates':
                query_set = Predicate.objects\
                                     .filter(**args)[start:end]
            elif table_name == 'oc_projects':
                query_set = Project.objects\
                                   .filter(**args)[start:end]
            elif table_name == 'oc_strings':
                query_set = OCstring.objects\
                                    .filter(**args)[start:end]
            elif table_name == 'oc_subjects':
                query_set = Subject.objects\
                                   .filter(**args)[start:end]
            elif table_name == 'oc_types':
                query_set = OCtype.objects\
                                  .filter(**args)[start:end]
            elif table_name == 'exp_fields':
                dist_tables = ExpCell.objects\
                                     .filter(**args)\
                                     .values_list('table_id', flat=True)\
                                     .distinct()
                query_set = ExpField.objects\
                                    .filter(table_id__in=dist_tables)[start:end]
            elif table_name == 'exp_records':
                query_set = ExpCell.objects\
                                   .filter(**args)[start:end]
            elif table_name == 'exp_tables':
                dist_tables = ExpCell.objects\
                                     .filter(**args)\
                                     .values_list('table_id', flat=True)\
                                     .distinct()
                query_set = ExpTable.objects\
                                    .filter(table_id__in=dist_tables)[start:end]
            elif table_name == 'crt_fieldgroups':
                query_set = InputFieldGroup.objects\
                                           .filter(**args)[start:end]
            elif table_name == 'crt_fields':
                query_set = InputField.objects\
                                      .filter(**args)[start:end]
            elif table_name == 'crt_profiles':
                query_set = InputProfile.objects\
                                        .filter(**args)[start:end]
            elif table_name == 'crt_relations':
                query_set = InputRelation.objects\
                                         .filter(**args)[start:end]
            elif table_name == 'crt_rules':
                query_set = InputRule.objects\
                                     .filter(**args)[start:end]
            elif table_name == 'link_annotations':
                query_set = LinkAnnotation.objects\
                                          .filter(**args)[start:end]
            else:
                query_set = False
        return query_set

    def prep_directory(self, act_dir):
        """ Prepares a directory to receive export files """
        output = False
        full_dir = self.root_export_dir + act_dir + '/'
        if self.act_export_dir is not False:
            full_dir = self.act_export_dir + '/' + act_dir
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
