import copy
import datetime
import json

from django.conf import settings
from django.core.cache import caches
from django.utils.encoding import force_text

from opencontext_py.apps.all_items.models import AllManifest
from opencontext_py.libs.isoyears import ISOyears

from opencontext_py.libs.models import (
    make_dict_json_safe, 
    make_model_object_json_safe_dict
)


# The delimiter for parts of an object value added to a
# solr field.
SOLR_VALUE_DELIM = '___'
SOLR_VALUE_SUB = '__'


SOLR_DATA_TYPE_TO_DATA_TYPE = {
    'id': 'id',
    'bool': 'xsd:boolean',
    'int': 'xsd:integer',
    'double': 'xsd:double',
    'string': 'xsd:string',
    'date': 'xsd:date',
}

DATA_TYPE_TO_SOLR_DATA_TYPE = {v:k for k,v in SOLR_DATA_TYPE_TO_DATA_TYPE.items()}



def make_dict_of_manifest_objs_from_assertion_objs(assert_objs):
    """Makes a string UUID keyed dict of manifest objects from the assertion objects
    """
    rel_man_objs = {}
    for assert_obj in assert_objs:
        if not str(assert_obj.subject.uuid) in rel_man_objs:
            rel_man_objs[str(assert_obj.subject.uuid)] = assert_obj.subject
        if not str(assert_obj.observation.uuid) in rel_man_objs:
            rel_man_objs[str(assert_obj.observation.uuid)] = assert_obj.observation
        if not str(assert_obj.event.uuid) in rel_man_objs:
            rel_man_objs[str(assert_obj.event.uuid)] = assert_obj.event
        if not str(assert_obj.attribute_group.uuid) in rel_man_objs:
            rel_man_objs[str(assert_obj.attribute_group.uuid)] = assert_obj.attribute_group
        if not str(assert_obj.predicate.uuid) in rel_man_objs:
            rel_man_objs[str(assert_obj.predicate.uuid)] = assert_obj.predicate
        if assert_obj.predicate.data_type != 'id':
            continue
        if not str(assert_obj.object.uuid) in rel_man_objs:
            rel_man_objs[str(assert_obj.object.uuid)] = assert_obj.object
    return rel_man_objs


def get_manifest_obj_from_man_obj_dict(uuid, man_obj_dict, use_cache=True):
    """Get a manifest object from the manifest object dict, or fallback
     to cache, then DB
    """
    man_obj = man_obj_dict.get(uuid)
    if man_obj:
        # We have the item in the dict.
        return man_obj
    # Fallback 1: Look in the cache.
    cache_key = None
    if use_cache:
        cache_key = f'man-obj-{str(uuid)}'
        cache = caches['redis']
        man_obj = cache.get(cache_key)
        if man_obj:
            # We found the item in the cache.
            return man_obj
    man_obj = AllManifest.objects.filter(uuid=uuid).first()
    if man_obj and cache_key:
        # set the cache with this manifest object
        try:
            cache.set(cache_key, man_obj)
        except:
            pass
    return man_obj


def get_solr_data_type_from_data_type(data_type, prefix=''):
    '''
    Defines whether our dynamic solr fields names for
    predicates end with ___pred_id, ___pred_double, etc.
    
    :param str predicate_type: String data-type used by Open
        Context
    :param str prefix: String prefix to append before the solr type
    :param list string_default_pred_types: list of values that
        default to string without triggering an exception.
    '''

    solr_data_type = DATA_TYPE_TO_SOLR_DATA_TYPE.get(data_type)
    if not solr_data_type:
        raise ValueError(f'No solr data type for {data_type}')
    
    return prefix + solr_data_type


def ensure_text_solr_ok(text_str):
    """ Makes sure the text is solr escaped """
    return force_text(
        text_str,
        encoding='utf-8',
        strings_only=False,
        errors='surrogateescape'
    )


def convert_slug_to_solr(slug):
    """Converts a slug to a solr style slug."""
    # slug = self.solr_doc_prefix + slug
    return slug.replace('-', '_')


def string_clean_for_solr(str_for_solr_val):
    """Clean strings for solr values to make sure they will parse properly"""
    str_for_solr_val = str(str_for_solr_val).replace(
        SOLR_VALUE_DELIM, 
        SOLR_VALUE_SUB,
    )
    return str_for_solr_val.strip('_')


def make_solr_entity_str(
    slug,
    data_type,
    uri,
    label,
    alt_label=None,
    act_solr_doc_prefix='',
    solr_value_delim=SOLR_VALUE_DELIM
):
    """Make a string value for solr that describes an entity"""
    # NOTE: The '-' character is reserved in Solr, so we need to replace
    # it with a '_' character in order to do prefix queries on the slugs.
    if act_solr_doc_prefix:
        act_solr_doc_prefix = act_solr_doc_prefix.replace('-', '_')
        if not slug.startswith(act_solr_doc_prefix):
            slug = act_solr_doc_prefix + slug 
    slug = convert_slug_to_solr(slug)
    slug = string_clean_for_solr(slug)
    solr_data_type = get_solr_data_type_from_data_type(data_type)
    solr_data_type = string_clean_for_solr(solr_data_type)
    uri = string_clean_for_solr(AllManifest().clean_uri(uri))
    label = string_clean_for_solr(label)
    values = [slug, solr_data_type, uri, label]
    if alt_label:
        alt_label = string_clean_for_solr(alt_label)
    if alt_label and alt_label != label:
        values.append(alt_label)
    return solr_value_delim.join(values)


def solr_convert_man_obj_obj_dict(obj_or_dict, dict_lookup_prefix='object'):
    """Convert a manifest or object dictionary into 
    a solr doc creation friendly item dict
    """
    if isinstance(obj_or_dict, AllManifest):
        obj_dict = make_model_object_json_safe_dict(obj_or_dict)
        obj_dict['id'] = obj_dict.get('uri')
    else:
        obj_dict = copy.deepcopy(obj_or_dict)
        obj_dict['uuid'] = obj_or_dict.get(
            f'{dict_lookup_prefix}_id', 
            obj_or_dict.get('uuid')
        )
        obj_dict['item_type'] = obj_or_dict.get(
            f'{dict_lookup_prefix}__item_type',
            obj_or_dict.get('item_type')
        )
        obj_dict['meta_json'] = obj_or_dict.get(
            f'{dict_lookup_prefix}__meta_json',
            obj_or_dict.get('meta_json')
        )
        obj_dict['context__meta_json'] = obj_or_dict.get(
            f'{dict_lookup_prefix}__context__meta_json',
            obj_or_dict.get('context__meta_json')
        )
    return obj_dict


def make_obj_or_dict_solr_entity_str(
    obj_or_dict,
    default_data_type='id',
    default_alt_label=None,
    act_solr_doc_prefix='',
    solr_value_delim=SOLR_VALUE_DELIM,
    dict_lookup_prefix='object',
):

    """Makes a solr entity string from an instance of a
    AllManifest object or a JSON-LD dictionary object
    """
    obj_dict = solr_convert_man_obj_obj_dict(
        obj_or_dict,
        dict_lookup_prefix=dict_lookup_prefix,
    )
    return make_solr_entity_str(
        slug=obj_dict.get('slug'),
        data_type=obj_dict.get('data_type', default_data_type),
        uri=AllManifest().clean_uri(obj_dict.get('id', '')),
        label=obj_dict.get('label'),
        alt_label=obj_dict.get('alt_label', default_alt_label),
        solr_value_delim=solr_value_delim,
        act_solr_doc_prefix=act_solr_doc_prefix,
    )
