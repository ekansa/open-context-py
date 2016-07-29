from django.db import models
from django.conf import settings
from django.core import serializers
from opencontext_py.libs.general import LastUpdatedOrderedDict
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
from opencontext_py.apps.ocitems.editorials.models import Editorial


class EditorialAction():
    """ methods to execute an editorial action
from opencontext_py.apps.ocitems.editorials.manage import EditorialAction
uuids = [
'40c2867f-f7d6-4642-b421-c33d17f9a357',
'fb6bfd6e-6d36-4aac-b9a3-644cd5c6613e',
'a1798207-8b9e-49b8-9674-a065d2ac4007',
'9f2c4737-d62a-44cf-af0b-387766e7242b',
'8572c796-0564-4f3f-abd8-788d17eded60',
'67675864-4eb3-4d0d-80c0-2ca5ced504dd',
'9add807a-6d3b-424b-8197-4892a8e7e2db',
'0eacb8da-c015-4d4c-94f0-12edb1de021c',
'c177502b-63a6-4a75-9a72-228ae35d2e38',
'b6e52cc1-7708-42c5-acbc-906d5eae445f',
'f170b177-3281-4b64-b9ab-5d79e7754846',
'33095146-ffe8-4e50-ac20-051ddbb6434e',
'38621946-5973-48df-a67d-20d986a8cd65',
'a9cd8d25-2282-4ea4-ba86-cf62f8afbbef']
ed_act = EditorialAction()
ed_act.editorial_uuid = 'f91dd97f-a0c5-4d83-855d-5866cc204547'
ed_act.editorial_project_uuid = '646b7034-07b7-4971-8d89-ebe37dda4cd2'
ed_act.editorial_user_id = 1
ed_act.editorial_class_uri = 'policy-redaction'
ed_act.editorial_label = 'Redaction of Records in Disputed Territories'
ed_act.editorial_note = 'After consulting with the Editorial Board, Open Context editors removed records '
ed_act.editorial_note += 'of specimen originating from sites in disputed territories.'
ed_act.redact_uuids(uuids)


    """
    
    def __init__(self):
        self.editorial_uuid = None
        self.editorial_user_id = 0
        self.editorial_project_uuid = '0'
        self.editorial_class_uri = None
        self.editorial_label = None
        self.editorial_note = None
        self.project_models = ['oc_assertions__subject',
                               'oc_assertions__predicate',
                               'oc_assertions__object',
                               'link_annotations',
                               'oc_documents',
                               'oc_events',
                               'oc_geospace',
                               'oc_manifest',
                               'oc_mediafiles',
                               'oc_persons',
                               'oc_predicates',
                               'oc_projects',
                               'oc_strings',
                               'oc_subjects',
                               'oc_types']
    
    def redact_uuids(self, uuid_list):
        """ Redacts uuids from a data publication for an editorial reason
            This saves the original data as a JSON formated string
            for the editorial, so in theory the original redacted data
            can be restored.
            Once the editorial and the restore data are saved, the
            redaction (deleteion) is executed
        """
        saved_query_sets = self.save_editorial_and_pre_redaction_data(uuid_list)
        del_count = self.delete_query_set_model_objects(saved_query_sets)
        if del_count > 0:
            ok = True
        else:
            ok = False
        return ok
    
    def save_editorial_and_pre_redaction_data(self, uuid_list):
        """ Redacts uuids from a data publication for an editorial reason """
        saved_query_sets = []
        ok = True
        if not isinstance(uuid_list, list):
            uuid_list = [uuid_list]
        editorial = Editorial()
        editorial.project_uuid = self.editorial_project_uuid
        editorial.user_id = self.editorial_user_id
        if self.editorial_uuid is not None:
            editorial.uuid = self.editorial_uuid
        if self.editorial_class_uri is not None:
            editorial.class_uri = self.editorial_class_uri
        if self.editorial_label is not None:
            editorial.label = self.editorial_label
        if self.editorial_note is not None:
            editorial.note = self.editorial_note
        editorial.save()
        if editorial.uuid is not None:
            print('Preparing editorial action: ' + str(editorial.uuid))
            self.editorial_uuid = editorial.uuid
        JSONserializer = serializers.get_serializer('json')
        json_serializer = JSONserializer()
        data = LastUpdatedOrderedDict()
        for model_name in self.project_models:
            query_set = self.get_query_set(model_name, uuid_list)
            if len(query_set) > 0:
                save_ok = False
                model_data = json_serializer.serialize(query_set,
                                                       ensure_ascii=False)
                data[model_name] = model_data
                editorial.restore_json = data
                try:
                    editorial.save()
                    save_ok = True
                except:
                    print('Failed to save restore data at: ' + model_name)
                    save_ok = False
                    ok = False
                if save_ok:
                    print('Saved restore data for model: ' + model_name)
                    saved_query_sets.append(query_set)
        if ok is False:
            # we don't want to delete anything if we had a problem
            # saving the restore data
            saved_query_sets = None
        return saved_query_sets
    
    def delete_query_set_model_objects(self, saved_query_sets):
        """ deletes models from a list of query sets
            related to the item(s) to be redacted
        """
        del_count = 0
        for query_set in saved_query_sets:
            # we've succeeded in saving the restore data, now delete these items
            for model_obj in query_set:
                del_ok = False
                try:
                    model_obj.delete()
                    del_ok = True
                except:
                    del_ok = False
                if del_ok:
                    del_count += 1
        return del_count

    def get_query_set(self, model_name, uuid_list):
        """ gets a query set for a given model name """
        if model_name == 'oc_assertions__subject':
            query_set = Assertion.objects\
                                 .filter(uuid__in=uuid_list)\
                                 .exclude(predicate_uuid__in=uuid_list)\
                                 .exclude(object_uuid__in=uuid_list)
        elif model_name == 'oc_assertions__predicate':
             query_set = Assertion.objects\
                                 .filter(predicate_uuid__in=uuid_list)\
                                 .exclude(uuid__in=uuid_list)\
                                 .exclude(object_uuid__in=uuid_list)
        elif model_name == 'oc_assertions__object':
             query_set = Assertion.objects\
                                 .filter(object_uuid__in=uuid_list)\
                                 .exclude(uuid__in=uuid_list)\
                                 .exclude(predicate_uuid__in=uuid_list)
        elif model_name == 'link_annotations':
            query_set = []
            for uuid in uuid_list:
                partial_query_set = LinkAnnotation.objects\
                                                  .filter(subject=uuid)\
                                                  .exclude(predicate_uri__contains=uuid)\
                                                  .exclude(object_uri__contains=uuid)
                if len(partial_query_set) > 0:
                    for lanno in partial_query_set:
                        query_set.append(lanno)
                partial_query_set = LinkAnnotation.objects\
                                                  .filter(predicate_uri__contains=uuid)\
                                                  .exclude(subject=uuid)\
                                                  .exclude(object_uri__contains=uuid)
                if len(partial_query_set) > 0:
                    for lanno in partial_query_set:
                        query_set.append(lanno)
                partial_query_set = LinkAnnotation.objects\
                                                  .filter(object_uri__contains=uuid)\
                                                  .exclude(subject=uuid)\
                                                  .exclude(predicate_uri__contains=uuid)
                if len(partial_query_set) > 0:
                    for lanno in partial_query_set:
                        query_set.append(lanno)
        
        elif model_name == 'oc_documents':
            query_set = OCdocument.objects\
                                  .filter(uuid__in=uuid_list)
        elif model_name == 'oc_events':
            query_set = Event.objects\
                             .filter(uuid__in=uuid_list)
        elif model_name == 'oc_geospace':
            query_set = Geospace.objects\
                                .filter(uuid__in=uuid_list)
        elif model_name == 'oc_manifest':
            query_set = Manifest.objects\
                                .filter(uuid__in=uuid_list)
        elif model_name == 'oc_mediafiles':
            query_set = Mediafile.objects\
                                 .filter(uuid__in=uuid_list)
        elif model_name == 'oc_persons':
            query_set = Person.objects\
                              .filter(uuid__in=uuid_list)
        elif model_name == 'oc_predicates':
            query_set = Predicate.objects\
                                 .filter(uuid__in=uuid_list)
        elif model_name == 'oc_projects':
            query_set = Project.objects\
                               .filter(uuid__in=uuid_list)
        elif model_name == 'oc_strings':
            query_set = OCstring.objects\
                                .filter(uuid__in=uuid_list)
        elif model_name == 'oc_subjects':
            query_set = Subject.objects\
                               .filter(uuid__in=uuid_list)
        elif model_name == 'oc_types':
            query_set = OCtype.objects\
                              .filter(uuid__in=uuid_list)
        else:
            query_set = []
        return query_set