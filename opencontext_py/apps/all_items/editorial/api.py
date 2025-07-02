

from lxml import etree
import lxml.html

from random import sample
import uuid as GenUUID

from django.db.models import Q


from opencontext_py.apps.all_items import configs
from opencontext_py.apps.all_items.models import (
    AllManifest,
    AllAssertion,
    AllIdentifier,
)
from opencontext_py.apps.all_items import models_utils

from opencontext_py.apps.all_items.legacy_all import update_old_id

from opencontext_py.libs.models import (
    make_dict_json_safe
)


MANIFEST_LOOKUP_DEFAULT_ROWS = 10
MULTI_VALUE_DELIM = '||'

REQUEST_PARAMS_TO_MANIFEST_ATTRIBUTES = [
    'project_id',
    'project__slug',
    'project__label',
    'project__label__startswith',
    'project__label__endswith',
    'project__label__contains',

    'context_id',
    'context__item_type',
    'context__slug',
    'context__uri',
    'context__uri__contains',
    'context__uri__icontains',
    'context__label',
    'context__label__startswith',
    'context__label__endswith',
    'context__label__contains',
    'context__label__icontains',

    'item_class_id',
    'item_class__slug',
    'item_class__label',
    'item_class__uri',
    'item_class__item_key',
    'item_class__label__startswith',
    'item_class__label__endswith',
    'item_class__label__contains',
    'item_class__label__icontains',

    'uuid',
    'slug',
    'item_key',
    'item_type',
    'data_type',
    'uri',
    'uri__contains',
    'uri__startswith',
    'label',
    'label__startswith',
    'label__endswith',
    'label__contains',
    'label__icontains',

    'path',
    'path__startswith',
    'path__endswith',
    'path__contains',
    'path__icontains',

    'meta_json__combined_name',
    'meta_json__combined_name__startswith',
    'meta_json__combined_name__endswith',
    'meta_json__combined_name__contains',
    'meta_json__combined_name__icontains',

    # for common gazetteer lookups
    'meta_json__geonames_id',
    'meta_json__pleiades_id',
    'meta_json__wikidata_id',
]

UUID_ATTRIBUTES = [
    'uuid',
    'project_id',
    'context_id',
    'item_class_id',
]

# The request param 'q' will map to the following filters for the manifest
KEYWORD_SEARCH_MANIFEST_FILTERS = [
    'uuid',
    'slug',
    'item_key',
    'uri__icontains',
    'label__icontains',
    'meta_json__combined_name__icontains',
]


# Keys to use group distinct metadata attributes. This makes it more convenient
# for the front end.
LOOKUP_GENERAL_DISTINCT_GROUPED_ATTRIBUTES = [
    (
        'item_type',
        ['item_type'],
    ),
    (
        'project',
        [
            'project_id',
            'project__slug',
            'project__label',
        ],
    ),
    (
        'item_class',
        [
            'item_class_id',
            'item_class__slug',
            'item_class__label',
        ],
    ),
    (
        'context',
        [
            'context_id',
            'context__item_type',
            'context__slug',
            'context__uri',
            'context__label',
        ],
    ),
]

# Attributes on which to select distinct when returning general metadata on
# manifest lookups
LOOKUP_GENERAL_DISTINCT_ATTRIBUTES = [
    a for _, attrib_list in LOOKUP_GENERAL_DISTINCT_GROUPED_ATTRIBUTES
    for a in attrib_list
]



FAKE_UUID = 'ffffffff-ffff-ffff-ffff-ffffffffffff'

# Predicates to use in lookups with the 'q' general keyword search parameter
OTHER_LABEL_PREDICATE_IDS = [
    configs.PREDICATE_SKOS_PREFLABEL_UUID,
    configs.PREDICATE_SKOS_ALTLABEL_UUID,
    configs.PREDICATE_SKOS_ALTLABEL_UUID,
    configs.PREDICATE_DCTERMS_TITLE_UUID,
]



def get_html_entities():
    return """
    <!DOCTYPE doc [
        <!ENTITY % ISOEntities PUBLIC 'ISO 8879-1986//ENTITIES ISO Character Entities 20030531//EN//XML' 'http://www.s1000d.org/S1000D_4-1/ent/ISOEntities'>
        %ISOEntities;]
    >
    """

def html_validate(check_str):
    """ checks to see if a string is OK as HTML """
    parser = etree.XMLParser(
        load_dtd=True,
        no_network=False,
        encoding='utf-8',
    )
    check_str = get_html_entities() + f'<div>{check_str}</div>'
    errors = []
    try:
        is_valid = True
        tree = etree.XML(check_str, parser)
    except:
        is_valid = False
        for i, elog in enumerate(parser.error_log):
            errors.append(
                f'HTML problem ({(i + 1)}): {elog.message}'
            )
    return is_valid, errors


def make_integer_or_default(raw_value, default_value):
    """Make a value an integer or, if not valid, a default value"""
    if not raw_value:
        return default_value
    try:
        int_value = int(float(raw_value))
    except:
        int_value = default_value
    return int_value


def is_valid_uuid(val):
    try:
        return GenUUID.UUID(str(val))
    except ValueError:
        return None


def dict_uuids_to_string(dict_obj):
    """Iterates through a dictionary object to change UUID values to strings"""
    for key, val in dict_obj.items():
        if not isinstance(val, GenUUID.UUID):
            continue
        dict_obj[key] = str(val)
    return dict_obj


def manifest_obj_to_json_safe_dict(
    manifest_obj,
    do_minimal=False,
    for_edit=False,
):
    """Makes a dict safe for JSON expression from a manifest object"""
    if not manifest_obj:
        return None
    if do_minimal:
        # Return only a limited number of attributes
        return {
            'uuid': str(manifest_obj.uuid),
            'slug': manifest_obj.slug,
            'label': manifest_obj.label,
            'item_type': manifest_obj.item_type,
            'data_type': manifest_obj.data_type,
            'path': manifest_obj.path,
            'uri': manifest_obj.uri,
        }
    if not manifest_obj.item_class:
        # In case we don't have an item class, fill it in with a temporary
        # object.
        item_class_obj = AllManifest(
            **{
                'uuid': configs.DEFAULT_CLASS_UUID,
                'label': 'Default (null) class',
                'slug': 'oc-default-class',
            }
        )
        manifest_obj.item_class = item_class_obj
    output = {
        'uuid': str(manifest_obj.uuid),
        'slug': manifest_obj.slug,
        'label': manifest_obj.label,
        'item_type': manifest_obj.item_type,
        'data_type': manifest_obj.data_type,
        'context_id': str(manifest_obj.project.uuid),
        'project_id': str(manifest_obj.project.uuid),
        'project__label': manifest_obj.project.label,
        'project__slug': manifest_obj.project.slug,
        'item_class_id': str(manifest_obj.item_class.uuid),
        'item_class__label': manifest_obj.item_class.label,
        'item_class__slug': manifest_obj.item_class.slug,
        'context_id': str(manifest_obj.context.uuid),
        'context__label': manifest_obj.context.label,
        'context__slug': manifest_obj.context.slug,
        'context__uri': manifest_obj.context.uri,
        'path': manifest_obj.path,
        'uri': manifest_obj.uri,
        'source_id': manifest_obj.source_id,
        'alt_label': manifest_obj.meta_json.get('alt_label'),
        'meta_json': manifest_obj.meta_json,
    }
    if for_edit:
        output['meta_json'] = manifest_obj.meta_json
        output['indexed'] = None
        output['published'] = None
        output['updated'] = None
        if manifest_obj.indexed:
            output['indexed'] = manifest_obj.indexed.date().isoformat()
        if manifest_obj.revised:
            output['revised'] = manifest_obj.revised.date().isoformat()
        if manifest_obj.published:
            output['published'] = manifest_obj.published.date().isoformat()
        if manifest_obj.updated:
            output['updated'] = manifest_obj.updated.date().isoformat()
    return output


def get_manifest_item_dict_by_uuid(uuid, do_minimal=False):
    """Returns a manifest item dict by uuid"""
    manifest_obj = AllManifest.objects.filter(uuid=uuid).first()
    if not manifest_obj:
        return None
    return manifest_obj_to_json_safe_dict(
        manifest_obj,
        do_minimal=do_minimal
    )


def get_man_qs_by_any_id(identifier, man_qs=None):
    """Gets a manifest object by an type of unique identifier"""
    _, new_uuid = update_old_id(identifier)

    if not man_qs:
        man_qs = AllManifest.objects.all()
    man_qs = AllManifest.objects.filter(
        Q(uuid=new_uuid)
        |Q(slug=identifier)
        |Q(uri=AllManifest().clean_uri(identifier))
    ).select_related(
        'item_class'
    ).select_related(
        'context'
    ).select_related(
        'project'
    ).order_by()
    return man_qs


def get_man_obj_by_any_id(identifier, item_key_dict=None):
    """Gets a manifest object by an type of unique identifier"""
    man_obj = None
    if item_key_dict:
        # check to see if the item is in our 
        # item_key_dict (used in the faceted search)
        man_obj = item_key_dict.get(identifier)
    if man_obj:
        # We found the item with no need to bother
        # further queries
        return man_obj
    man_qs = get_man_qs_by_any_id(identifier)
    man_obj = man_qs.first()
    if man_obj:
        # We found the item with no need to bother
        # with the item_key
        return man_obj
    if item_key_dict and not man_obj:
        # We already checked by item_key_dict
        # so there's no need to redo the query below
        return None
    # Do an expensive lookup on item_key which will
    # which is allowed to be null.
    man_obj = AllManifest.objects.filter(
        item_key=identifier
    ).select_related(
        'item_class'
    ).select_related(
        'context'
    ).select_related(
        'project'
    ).order_by().first()
    return man_obj


def get_item_children(identifier, man_obj=None, output_child_objs=False):
    """Gets a dict for an object and a list of its children"""

    if identifier and not man_obj:
        man_obj = get_man_obj_by_any_id(identifier)
    if not man_obj:
        return None

    if man_obj.item_type == 'subjects':
        # Gets spatial context children
        children_objs = models_utils.get_immediate_context_children_objs_db(
            man_obj
        )
    elif man_obj.item_type == 'projects':
        children_objs = AllManifest.objects.filter(
            item_type='projects',
            context=man_obj
        ).exclude(
            uuid=man_obj.uuid
        ).order_by(
            'label'
        )
    else:
        # Gets concept hierarchy children.
        children_objs = models_utils.get_immediate_concept_children_objs_db(
            man_obj
        )

    if not len(children_objs) and man_obj.item_type == 'predicates' and man_obj.data_type == 'id':
        # We've got a predicate that may have types that is convenient to consider as
        # children.
        children_objs = AllManifest.objects.filter(
            item_type='types',
            context=man_obj,
        ).order_by('label')


    if output_child_objs:
        # Return the child manifest objects, not JSON safe
        # dict representations
        return children_objs

    output = manifest_obj_to_json_safe_dict(man_obj)
    output['children'] = []
    for child_obj in children_objs:
        child_dict = manifest_obj_to_json_safe_dict(child_obj)
        output['children'].append(child_dict)

    return output


def get_item_assertion_examples(identifier):
    """Gets random example list of item as predicate or object of assertions"""
    man_obj = get_man_obj_by_any_id(identifier)
    if not man_obj:
        return None

    example_qs = AllAssertion.objects.filter(
        Q(object=man_obj)
        |Q(predicate=man_obj)
    ).distinct(
        'subject'
    ).order_by(
        'subject'
    )[:1000]
    output = []
    objs = [o for o in example_qs]
    if len(objs) > 10:
        objs = sample(objs, 10)
    for example_ass in objs:
        example_dict = manifest_obj_to_json_safe_dict(example_ass.subject)
        output.append(example_dict)
    return output


def make_keyword_search_filter_to_qs(qs, q_term):
    """Adds filters for a general keyword ('q') search """

    query = None
    # Loop through the different attributes for the subject of
    # assertions to include in an OR query.
    for man_attribute in KEYWORD_SEARCH_MANIFEST_FILTERS:
        if man_attribute in UUID_ATTRIBUTES and not is_valid_uuid(q_term):
            # This value is not valid as a UUID, so don't query with it.
            continue
        act_query_dict = {man_attribute: q_term}
        if query is None:
            query = Q(**act_query_dict)
            continue
        query = query | Q(**act_query_dict)


    # Loop through the different predicates and object strings to
    # include in the OR query.
    assert_qs = AllAssertion.objects.all()
    assert_query = None
    for other_label_predicate_id in OTHER_LABEL_PREDICATE_IDS:
        act_q = Q(predicate_id=other_label_predicate_id, obj_string__icontains=q_term)
        if assert_query is None:
            assert_query = act_q
            continue
        assert_query = assert_query | act_q

    # Select the distinct subjects of assertions that match this query criterion.
    assert_qs = assert_qs.filter(
        assert_query
    ).distinct(
        'subject',
        'obj_string',
    ).order_by()

    assert_qs_vals = assert_qs.values(
        'subject_id',
        'obj_string',
    )

    assert_uuids = set([d['subject_id'] for d in assert_qs_vals])
    # Now add the list of subjects with alternate label
    query = query | Q(uuid__in=assert_uuids)
    qs = qs.filter(query)
    return qs, assert_qs


def add_filter_or_exclude_term(qs, attribute, raw_value, attribute_prefix='', value_delim=MULTI_VALUE_DELIM, as_exclude=False):
    """Adds a filter term to a query_set, sometimes values into lists if delimited"""
    no_delim_attrib_endings = [
        '__startswith',
        '__endswith',
        '__contains',
        '__icontains',
    ]

    has_no_delim_ending = False
    for attrib_ending in no_delim_attrib_endings:
        if attribute.endswith(attrib_ending):
            has_no_delim_ending = True

    if has_no_delim_ending or not isinstance(raw_value, str):
        # The attribute has an ending for a partial string matching, so we're not going to
        # try to separate the raw_value into a list. OR the raw_value is not a string,
        # so it can't be seperated by a delim.
        q_attribute = f'{attribute_prefix}{attribute}'
        query_dict = {q_attribute: raw_value}
        print(f'Add query condition (exclude {as_exclude}): {query_dict}')
        if as_exclude:
            qs = qs.exclude(**query_dict)
        else:
            qs = qs.filter(**query_dict)
        return qs

    values = [v.strip() for v in raw_value.split(value_delim)]


    if attribute in UUID_ATTRIBUTES:
        # Special processing to validate queries to UUID fields.
        # We'll only allow values that are valid uuids. If we don't
        # have any valid uuids, then we'll filter by a fake_uuid to
        # help signal this was bad.
        values = [v for v in values if is_valid_uuid(v)]
        if not len(values):
            values.append(FAKE_UUID)

    if len(values) > 1:
        q_attribute = f'{attribute_prefix}{attribute}__in'
        query_dict = {q_attribute: values}
    else:
        q_attribute = f'{attribute_prefix}{attribute}'
        query_dict = {q_attribute: values[0]}

    print(f'Add query condition (exclude {as_exclude}): {query_dict}')
    # Now add the filter or exclude term.
    if as_exclude:
        qs = qs.exclude(**query_dict)
    else:
        qs = qs.filter(**query_dict)
    return qs


def make_lookup_qs(request_dict, value_delim=MULTI_VALUE_DELIM):
    """Makes a Manifest query set for item lookups"""
    q_term = request_dict.get('q')
    qs = AllManifest.objects.all()
    assert_qs = None
    if q_term:
        qs, assert_qs = make_keyword_search_filter_to_qs(qs, q_term)

    for attribute in REQUEST_PARAMS_TO_MANIFEST_ATTRIBUTES:
        filter_raw_value = request_dict.get(attribute)
        exclude_raw_value = request_dict.get(f'ex__{attribute}')
        if not filter_raw_value and not exclude_raw_value:
            continue
        if filter_raw_value:
            qs = add_filter_or_exclude_term(
                qs,
                attribute,
                filter_raw_value,
                value_delim=value_delim,
            )
        if exclude_raw_value:
            qs = add_filter_or_exclude_term(
                qs,
                attribute,
                exclude_raw_value,
                value_delim=value_delim,
                as_exclude=True,
            )

    if request_dict.get('id'):
        # Add an ID filter
        qs = get_man_qs_by_any_id(
            identifier=request_dict.get('id'),
            man_qs=qs
        )

    return qs, assert_qs


def lookup_manifest_objs(request_dict, value_delim=MULTI_VALUE_DELIM, default_rows=MANIFEST_LOOKUP_DEFAULT_ROWS):
    """Returns a list of manifest item objects that meet wide ranging search criteria"""

    start = make_integer_or_default(
        raw_value=request_dict.get('start', 0),
        default_value=0
    )
    # Default to 5 rows returned.
    rows = make_integer_or_default(
        raw_value=request_dict.get('rows', default_rows),
        default_value=default_rows
    )
    if rows < 1:
        rows = 1

    man_qs, assert_qs = make_lookup_qs(request_dict, value_delim=value_delim)

    # Check to make sure there's actually a queryset here.
    if not man_qs:
        return [], 0

    if assert_qs:
        # Yes, a given item may have more than 1 matching alt label, and this will only store
        # one of those alt labels. But that's OK, as this is a convenience only
        alt_labels = {a.subject_id:a.obj_string for a in assert_qs}
    else:
        alt_labels = {}

    # Return a list of manifest objects from the query.
    man_qs = man_qs.select_related(
        'project'
    ).select_related(
        'item_class'
    ).select_related(
        'context'
    )
    total_count = man_qs.count()
    if not request_dict.get('all'):
        # Limit the size of the query set returned
        man_qs = man_qs[start:(start + rows)]
    output = []
    for m in man_qs:
        alt_label = alt_labels.get(m.uuid)
        if alt_label:
            m.meta_json['alt_label'] = alt_label
        output.append(m)
    return output, total_count


def lookup_manifest_dicts(request_dict, value_delim=MULTI_VALUE_DELIM, default_rows=MANIFEST_LOOKUP_DEFAULT_ROWS):
    """Returns a list of manifest item dictionary objects that meet wide ranging search criteria"""
    manifest_objs, total_count = lookup_manifest_objs(
        request_dict=request_dict,
        value_delim=value_delim,
        default_rows=default_rows
    )
    manifest_dicts = [
        manifest_obj_to_json_safe_dict(m) for m in manifest_objs
    ]
    if request_dict.get('pids'):
        for m_dict in manifest_dicts:
            id_qs = AllIdentifier.objects.filter(
                item=m_dict.get('uuid'),
            ).order_by('scheme', 'rank')
            if not id_qs:
                continue
            m_dict['persistent_ids'] = []
            for id_obj in id_qs:
                id_dict = {'id': id_obj.id, 'scheme': id_obj.scheme, 'url': id_obj.url}
                m_dict['persistent_ids'].append(id_dict)
    return manifest_dicts, total_count


def lookup_up_general_distinct_metadata(request_dict, value_delim=MULTI_VALUE_DELIM):
    """Returns a list of distinct projects, item classes, and contexts metadata that match query criteria"""
    man_qs, assert_qs = make_lookup_qs(request_dict, value_delim=value_delim)

    if assert_qs:
        # We want manifest object from the subject of an
        # assertions query set.
        distincts = [f'subject__{attrib}' for attrib in LOOKUP_GENERAL_DISTINCT_ATTRIBUTES]
        assert_qs = assert_qs.select_related(
            'subject'
        ).select_related(
            'subject__project'
        ).select_related(
            'subject__item_class'
        ).select_related(
            'subject__context'
        ).values(
            *distincts
        ).distinct().order_by()

        output = []
        for q_dict in assert_qs:
            act_q_dict = {}
            for key, value in q_dict.items():
                # Remove the 'subject__' prefix from the attribute keys. This makes the
                # output consistent with outputs from manifest query sets.
                clean_key = key[len('subject__'):]
                act_q_dict[clean_key] = value
            act_q_dict = dict_uuids_to_string(act_q_dict)
            output.append(act_q_dict)
        return output

    if not man_qs:
        # We also don't have any manifest queryset results.
        return []

    man_qs = man_qs.select_related(
        'project'
    ).select_related(
        'item_class'
    ).select_related(
        'context'
    ).values(
        *LOOKUP_GENERAL_DISTINCT_ATTRIBUTES
    ).distinct().order_by()

    output = [
        make_dict_json_safe(q_dict) for q_dict in man_qs
    ]
    return output


def lookup_up_and_group_general_distinct_metadata(request_dict, value_delim=MULTI_VALUE_DELIM):
    """Looks up and groups distinct projects, item classes, and contexts metadata that match query criteria"""
    meta_list = lookup_up_general_distinct_metadata(request_dict, value_delim=value_delim)
    meta_dict = {}
    for dict_key, group_attribs in LOOKUP_GENERAL_DISTINCT_GROUPED_ATTRIBUTES:
        meta_dict.setdefault(dict_key, [])
        for meta_item in meta_list:
            group_dict = {k:meta_item.get(k) for k in group_attribs}
            if group_dict in meta_dict[dict_key]:
                continue
            meta_dict[dict_key].append(group_dict)
    return meta_dict
