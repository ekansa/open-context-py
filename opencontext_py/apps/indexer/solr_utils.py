import copy
import datetime
import json
from django.conf import settings
from django.utils.encoding import force_text
from opencontext_py.libs.isoyears import ISOyears


# The delimiter for parts of an object value added to a
# solr field.
SOLR_VALUE_DELIM = '___'


SOLR_DATA_TYPE_TO_DATA_TYPE = {
    'id': 'id',
    'bool': 'xsd:boolean',
    'int': 'xsd:integer',
    'double': 'xsd:double',
    'string': 'xsd:string',
    'date': 'xsd:date',
}

DATA_TYPE_TO_SOLR_DATA_TYPE = {v:k for k,v in SOLR_DATA_TYPE_TO_DATA_TYPE.items()}


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


def make_entity_string_for_solr(
    slug,
    data_type,
    uri,
    label,
    alt_label=None,
    solr_doc_prefix='',
    solr_value_delim=SOLR_VALUE_DELIM
):
    """Make a string value for solr that describes an entity"""
    # NOTE: The '-' character is reserved in Solr, so we need to replace
    # it with a '_' character in order to do prefix queries on the slugs.
    if solr_doc_prefix:
        solr_doc_prefix = solr_doc_prefix.replace('-', '_')
        if not slug.startswith(solr_doc_prefix):
            slug = solr_doc_prefix + slug 
    slug = convert_slug_to_solr(slug)
    solr_data_type = get_solr_data_type_from_data_type(data_type)
    values = [slug, solr_data_type, uri, label]
    if alt_label and alt_label != label:
        values.append(str(alt_label))
    return solr_value_delim.join(values)

