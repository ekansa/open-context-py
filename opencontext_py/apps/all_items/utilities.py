
import uuid as GenUUID

from django.db.models import Q

from opencontext_py.apps.all_items import configs
from opencontext_py.apps.all_items.models import (
    AllManifest,
    AllAssertion,
    AllHistory,
)


def uri_to_common_prefix(uri, uri_prefixes):
    """Converts a uri to a common prefixed uri
    
    :param str uri: A uri string
    :param dict uri_prefixes: A keyed by a root uri
       prefix, and a value (ending in ":") for the abbreviated
       namespace.
    """
    uri = AllManifest().clean_uri(uri)
    common_prefix = None
    for uri_prefix, ns_prefix in uri_prefixes.items():
        uri_prefix = AllManifest().clean_uri(uri_prefix)
        if not uri.startswith(uri_prefix):
            continue
        # Make sure that the ns_prefix ends wit a ':'
        if ns_prefix[-1] != ':':
            ns_prefix += ':'
        common_prefix = ns_prefix + uri[len(uri_prefix):]
    return common_prefix


def get_man_obj_from_uri(uri, item_key=None, filters=None, excludes=None):
    """Gets a manifest object by uri"""
    uri = AllManifest().clean_uri(uri)
    if item_key:
        man_obj_qs = AllManifest.objects.filter(
           Q(uri=uri)
           | Q(item_key=item_key)
        )
    else:
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
    publisher_id=None,
    project_id=None,
    source_id=None,
    observation_id=configs.DEFAULT_OBS_UUID,
    event_id=configs.DEFAULT_EVENT_UUID,
    attribute_group_id=configs.DEFAULT_ATTRIBUTE_GROUP_UUID,
    language_id=configs.DEFAULT_LANG_UUID,
    sort=0,
    replace_old_content=False,
    print_obj=False):
    """Adds a string attribute assertion to a subject object"""
    if not str_content:
        return None
    if not project_id:
        project_id = subject_obj.project.uuid
    if not publisher_id:
        publisher_id = subject_obj.publisher.uuid
    if not source_id:
        source_id = subject_obj.source_id

    if replace_old_content:
        AllAssertion.objects.filter(
            subject=subject_obj,
            predicate_id=predicate_id,
            observation_id=observation_id,
            event_id=event_id,
            attribute_group_id=attribute_group_id,
            sort=sort,
        ).exclude(
            obj_string=str_content,
        ).delete()
    
    ass_obj, _ = AllAssertion.objects.get_or_create(
        uuid=AllAssertion().primary_key_create(
            subject_id=subject_obj.uuid,
            predicate_id=predicate_id,
            obj_string=str_content,
            observation_id=observation_id,
            event_id=event_id,
            attribute_group_id=attribute_group_id,
            language_id=language_id,
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
            'sort': sort,
            'language_id': language_id,
            'obj_string': str_content,
        }
    )
    if print_obj:
        print('-'*72)
        print(
            f'Assertion {ass_obj.uuid}: '
            f'is {ass_obj.subject.label} [{ass_obj.subject.uuid}]'
            f'-> {ass_obj.predicate.label} [{ass_obj.predicate.uuid}]'
            f'-> {ass_obj.obj_string}'
        )
    return ass_obj


