
import uuid as GenUUID

from django.db.models import Q

from opencontext_py.apps.all_items import configs
from opencontext_py.apps.all_items.models import (
    AllManifest,
    AllString,
    AllAssertion,
    AllHistory,
)


def get_man_obj_from_uri(uri, filters=None, excludes=None):
    """Gets a manifest object by uri"""
    uri = AllManifest().clean_uri(uri)
    man_obj_qs = AllManifest.objects.filter(uri=uri)
    if filters:
        man_obj_qs = man_obj_qs.filter(**filters)
    if excludes:
        man_obj_qs = man_obj_qs.exclude(**excludes)
    man_obj = man_obj_qs.first()
    return man_obj



def add_string_assertion_simple(
    subject_obj,
    predicate_id, 
    str_content,
    project_id=None,
    publisher_id=None,
    source_id=None,
    observation_id=configs.DEFAULT_OBS_UUID,
    event_id=configs.DEFAULT_EVENT_UUID,
    attribute_group_id=configs.DEFAULT_ATTRIBUTE_GROUP_UUID,
    language_id=configs.DEFAULT_LANG_UUID,
    replace_old_content=False):
    """Adds a string attribute assertion to a subject object"""

    if not project_id:
        project_id = subject_obj.project.uuid
    if not publisher_id:
        publisher_id = subject_obj.publisher.uuid
    if not source_id:
        source_id = subject_obj.source_id

    str_obj, _ = AllString.objects.get_or_create(
        uuid=AllString().primary_key_create(
            project_id=project_id,
            content=str_content,
        ),
        defaults={
            'project_id': project_id,
            'source_id': source_id,
            'content': str_content
        }
    )
    if replace_old_content:
        AllAssertion.objects.filter(
            subject=subject_obj,
            predicate_id=predicate_id,
            observation_id=observation_id,
            event_id=event_id,
            attribute_group_id=attribute_group_id,
        ).exclude(
            obj_string=str_obj
        ).delete()

    print('-'*72)
    print(f'Str_obj {str_obj.uuid} for content: {str_obj.content}')
    ass_obj, _ = AllAssertion.objects.get_or_create(
        uuid=AllAssertion().primary_key_create(
            subject_id=subject_obj.uuid,
            predicate_id=predicate_id,
            obj_string_id=str_obj.uuid,
            observation_id=observation_id,
            event_id=event_id,
            attribute_group_id=attribute_group_id,
        ),
        defaults={
            'project_id': project_id,
            'publisher_id': publisher_id,
            'source_id': source_id,
            'subject': subject_obj,
            'predicate_id': predicate_id,
            'observation_id': observation_id,
            'event_id': event_id,
            'attribute_group_id': attribute_group_id,
            'obj_string': str_obj,
        }
    )
    print(
        f'Assertion {ass_obj.uuid}: '
        f'is {ass_obj.subject.label} [{ass_obj.subject.uuid}]'
        f'-> {ass_obj.predicate.label} [{ass_obj.predicate.uuid}]'
        f'-> {ass_obj.obj_string.content} [{ass_obj.obj_string.uuid}]'
    )
    print('-'*72)

