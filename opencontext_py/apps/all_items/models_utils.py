import re
import roman
import requests

# For geospace manipulations.
from shapely.geometry import mapping, shape

from math import pow
from time import sleep
from unidecode import unidecode

from django.core.cache import caches

from django.db.models import Q

from django.template.defaultfilters import slugify

from opencontext_py.apps.all_items import configs


DEFAULT_LABEL_SORT_LEN = 9


# ---------------------------------------------------------------------
# Generally used validation functions
# ---------------------------------------------------------------------
def validate_related_manifest_item_type(
    man_obj,
    allowed_types,
    obj_role,
    raise_on_fail=True
):
    if not isinstance(allowed_types, list):
        allowed_types = [allowed_types]
    if man_obj.item_type in allowed_types:
        return True
    if raise_on_fail:
        raise ValueError(
            f'{obj_role} has item_type {man_obj.item_type} '
            f'but must be: {str(allowed_types)}'
        )
    return False


def validate_related_project(project_obj, raise_on_fail=True):
    return validate_related_manifest_item_type(
        man_obj=project_obj,
        allowed_types=['projects'],
        obj_role='project',
        raise_on_fail=raise_on_fail
    )


def web_protocol_check(uri):
    """Checks if a URI responds to https:// or http://"""

    # Import here to avoid circular imports.
    from opencontext_py.apps.all_items.models import AllManifest

    sleep(0.1)
    protocols = ['https://', 'http://',]
    for protocol in protocols:
        check_uri = protocol + AllManifest().clean_uri(uri)
        try:
            r = requests.head(check_uri)
            if (
                (r.status_code == requests.codes.ok)
                or
                (r.status_code >= 300 and r.status_code <= 310)
            ):
                return check_uri
        except:
            pass
    return uri

# ---------------------------------------------------------------------
#  Functions used with the Manifest Model
# ---------------------------------------------------------------------
def prepend_zeros(sort, digit_length=DEFAULT_LABEL_SORT_LEN):
    """ prepends zeros if too short """
    sort = str(sort)
    while len(sort) < digit_length:
        sort = '0' + sort
    return sort


def sort_digits(index, digit_length=DEFAULT_LABEL_SORT_LEN):
    """ Makes a 3 digit sort friendly string from an index """
    if index >= pow(10, digit_length):
        index = pow(10, digit_length) - 1
    return prepend_zeros(str(index), digit_length)


def sting_number_splitter(string_to_split):
    parts = []
    if not string_to_split:
        # Return Nothing
        return [], False
    act_part = ''
    prior_part_type = None
    has_number_part = False
    for char in string_to_split:
        part_type = char.isdigit()
        if part_type:
            has_number_part = True
        if part_type != prior_part_type and len(act_part):
            parts.append(
                (prior_part_type, act_part,)
            )
            act_part = ''
        prior_part_type = part_type
        act_part += char
    # The last part
    parts.append(
        (part_type, act_part,)
    )
    return parts, has_number_part


def make_sort_string_from_label(raw_label):
    raw_label = unidecode(str(raw_label))
    parts, _ = sting_number_splitter(raw_label)
    first_number = None
    lesser_parts = []
    for is_num, part in parts:
        if first_number is None and is_num:
            first_number = part
        lesser_parts.append(part)
    if first_number is False:
        return raw_label.ljust(100, '0')
    sort_label = first_number.rjust(8, '0')
    for less_part in lesser_parts:
        for act_char in less_part:
            char_val = str(ord(act_char))
            sort_label += char_val.rjust(3, '0')
    return sort_label[:100]



def make_label_sort_val(raw_label):
    """Extract a sortable value"""
    raw_label = unidecode(str(raw_label))
    sort_label = ''
    prev_type = None
    for act_char in raw_label:
        char_val = ord(act_char)
        if char_val >= 49 and char_val <= 57:
            act_type = 'number'
        elif char_val >= 65 and char_val <= 122:
            act_type = 'letter'
        else:
            act_type = None
        if act_type and prev_type:
            if act_type != prev_type:
                act_char = '-' + act_char
        sort_label += act_char
        prev_type = act_type
    # Split the label by different delims.
    label_parts = re.split(
        ':|\ |\.|\,|\;|\-|\(|\)|\_|\[|\]|\/',
        sort_label
    )
    sorts = []
    for part in label_parts:
        if not len(part):
            # Skip, the part has nothing in it.
            continue
        if part.isdigit():
            # A numeric part
            num_part = int(float(part))
            part_sort = sort_digits(num_part)
            sorts.append(part_sort)
            # Continue, we're done with sorting
            # this part.
            continue

        # The part is a string, so process as
        # string
        part = unidecode(part)
        part = re.sub(r'\W+', '', part)
        try:
            roman_num = roman.fromRoman(part)
        except:
            roman_num = None
        if roman_num:
            part_sort = sort_digits(roman_num)
            sorts.append(part_sort)
            # Continue, we're done with sorting
            # this part.
            continue
        part_sort_parts = []
        for act_char in part:
            char_val = ord(act_char) - 48
            if char_val > 9:
                act_part_sort_part = sort_digits(char_val, 3)
            else:
                act_part_sort_part = str(char_val)
            part_sort_parts.append(act_part_sort_part)
        # Now bring together the part_sort_parts
        part_sort = ''.join(part_sort_parts)
        sorts.append(part_sort)
    # Now do the final
    final_sort = []
    for sort_part in sorts:
        sort_part = str(sort_part)
        if len(sort_part) > DEFAULT_LABEL_SORT_LEN:
            sort_part = sort_part[:DEFAULT_LABEL_SORT_LEN]
        elif len(sort_part) < DEFAULT_LABEL_SORT_LEN:
            sort_part = prepend_zeros(
                sort_part,
                DEFAULT_LABEL_SORT_LEN
            )
        final_sort.append(sort_part)
    if not len(final_sort):
        final_sort.append(prepend_zeros(0, DEFAULT_LABEL_SORT_LEN))
    return '-'.join(final_sort)


def get_project_short_id(project_id, not_found_default=0):
    """Get a project short id """

    # Import here to avoid circular imports.
    from opencontext_py.apps.all_items.models import AllManifest

    # Get the project id
    proj = None
    if project_id:
        proj = AllManifest.objects.filter(uuid=project_id).first()
    if proj:
        return proj.meta_json.get('short_id', not_found_default)
    return not_found_default


def suggest_project_short_id():
    """Suggests a project short id, not already in use"""

    # Import here to avoid circular imports.
    from opencontext_py.apps.all_items.models import AllManifest

    m_qs = AllManifest.objects.filter(item_type='projects')
    short_ids = []
    for m in m_qs:
        if not m.meta_json.get('short_id'):
            continue
        try:
            act_short_id = int(float(m.meta_json.get('short_id')))
        except:
            act_short_id = None
        if not act_short_id:
            continue
        short_ids.append(act_short_id)
    if not len(short_ids):
        # We don't have any project short ids yet, so suggest the first.
        return 1
    # Suggest 1 plus the max we already have.
    return max(short_ids) + 1


def make_sort_label(
    label,
    item_type,
    project_id,
    item_type_list,
    short_id=None
):
    """Makes a sort value for a record as a numeric string"""
    sort_parts = []
    if item_type not in item_type_list:
        item_type_num = len(item_type_list)
    else:
        item_type_num = item_type_list.index(item_type)
    sort_parts.append(
        prepend_zeros(item_type_num, 2)
    )
    if not short_id:
        short_id = get_project_short_id(project_id)
    sort_parts.append(
        prepend_zeros(short_id, 4)
    )
    sort_parts.append(
        make_label_sort_val(label)
    )
    final_sort = '-'.join(sort_parts)
    return final_sort


def make_slug_from_label(label, project_id, short_id=None):
    """Makes a slug from a label for a project item"""
    label = label.strip()
    label = label.replace('_', ' ')
    raw_slug = slugify(unidecode(label[:60]))
    if not short_id:
        short_id = get_project_short_id(project_id)
    if raw_slug == '-' or not len(raw_slug):
        # Slugs are not a dash or are empty
        raw_slug = 'x'
    raw_slug = str(short_id) + '-' + raw_slug
    return raw_slug


def make_slug_from_uri(uri):
    """Makes a slug from a label for a project item"""

    # Import here to avoid circular imports.
    from opencontext_py.apps.all_items.models import AllManifest

    uri = AllManifest().clean_uri(uri)
    # Remove any www. prefix to a URI.
    for bad_prefix in ['www.']:
        if not uri.startswith(bad_prefix):
            continue
        uri = uri[len(bad_prefix):]

    # Now look for uri_roots to convert to a slug prefix based on
    # configuration.
    for uri_root, slug_prefix in configs.LINKED_DATA_URI_PREFIX_TO_SLUGS.items():
        if not uri.startswith(uri_root):
            continue
        # Replace the uri_root with the slug prefix.
        uri = slug_prefix + uri[len(uri_root):]
        break

    replaces = [
        ('/', '-',),
        ('.', '-',),
        ('#', '-'),
        ('%20', '-'),
        ('q=', '-'),
        ('+', '-'),
        ('_', '-'),
    ]
    for f, r in replaces:
        uri = uri.replace(f, r)
    raw_slug = slugify(unidecode(uri[:55]))

    # Slugs can't have more than 1 dash characters
    raw_slug = re.sub(r'([-]){2,}', r'--', raw_slug)
    return raw_slug


def make_uri_for_oc_item_types(uuid, item_type):
    """Makes a URI for an item type if not provide yet"""
    if item_type not in (
        configs.OC_ITEM_TYPES + configs.NODE_ITEM_TYPES
    ):
        return None
    return f'{configs.OC_URI_ROOT}/{item_type}/{uuid}'


def make_manifest_slug(
    label,
    item_type,
    uri,
    project_id,
    short_id=None
):
    """Makes a sort value for a record as a numeric string"""

    # Import here to avoid circular imports.
    from opencontext_py.apps.all_items.models import AllManifest

    if item_type in configs.URI_ITEM_TYPES:
        # Check for a publisher specific config for
        # this kind of item type.
        raw_slug = make_slug_from_uri(uri)
    else:
        # The item_type is in the type that has the
        # project_short_id as a slug prefix. This is used
        # for open context item types or item types for
        # 'nodes' in assertions.
        raw_slug = make_slug_from_label(
            label,
            project_id,
            short_id=short_id
        )

    # Make sure no triple dashes, conflicts with solr hierarchy
    # delims.
    raw_slug = raw_slug.replace('---', '--')
    keep_trimming = True
    while keep_trimming and len(raw_slug):
        if raw_slug.endswith('-'):
            # slugs don't end with dashes
            raw_slug = raw_slug[:-1]
        else:
            keep_trimming = False
            break

    if raw_slug == '-' or not len(raw_slug):
        # Slugs are not a dash or are empty
        raw_slug = 'x'

    # Slugs can't have more than 1 dash characters
    slug_prefix = re.sub(r'([-]){2,}', r'-', raw_slug)
    q_slug = slug_prefix

    # Check to see if this slug is in use.
    m_slug = AllManifest.objects.filter(
        slug=q_slug
    ).first()
    if not m_slug:
        # This slug is not yet used, so skip out.
        return q_slug
    # Make a prefix based on the length the number of
    # slugs.
    m_slug_count = AllManifest.objects.filter(
        slug__startswith=slug_prefix
    ).count()
    slug_exists = True
    act_slug = f'{slug_prefix}-{m_slug_count}'
    while slug_exists:
        m_slug_count += 1
        act_slug = f'{slug_prefix}-{m_slug_count}'
        s_count = AllManifest.objects.filter(
            slug=act_slug
        ).count()
        if s_count < 1:
            slug_exists = False
    return act_slug



# ---------------------------------------------------------------------
#  Functions used with the Assertion Model
# ---------------------------------------------------------------------
def get_immediate_concept_parent_objs_db(child_obj):
    """Get the immediate parents of a child manifest object using DB"""

    # Import here to avoid circular imports.
    from opencontext_py.apps.all_items.models import AllAssertion

    subj_super_qs = AllAssertion.objects.filter(
        object_id=child_obj.uuid,
        predicate_id__in=(
            configs.PREDICATE_LIST_SBJ_IS_SUPER_OF_OBJ
            + configs.PREDICTATE_LIST_CONTEXT_SBJ_IS_SUPER_OF_OBJ
        ),
    )
    subj_subord_qs = AllAssertion.objects.filter(
        subject_id=child_obj.uuid,
        predicate_id__in=configs.PREDICATE_LIST_SBJ_IS_SUBORD_OF_OBJ,
    )
    all_parents = [a.subject for a in subj_super_qs]
    all_parents += [a.object for a in subj_subord_qs if a.object not in all_parents]
    return all_parents


def get_immediate_concept_children_objs_db(parent_obj):
    """Get the immediate children of a parent manifest object using DB"""

    # Import here to avoid circular imports.
    from opencontext_py.apps.all_items.models import AllAssertion

    subj_super_qs = AllAssertion.objects.filter(
        subject=parent_obj,
        predicate_id__in=(
            configs.PREDICATE_LIST_SBJ_IS_SUPER_OF_OBJ
            + configs.PREDICTATE_LIST_CONTEXT_SBJ_IS_SUPER_OF_OBJ
        ),
    )
    subj_subord_qs = AllAssertion.objects.filter(
        object=parent_obj,
        predicate_id__in=configs.PREDICATE_LIST_SBJ_IS_SUBORD_OF_OBJ,
    )
    all_children = [a.object for a in subj_super_qs]
    all_children += [a.subject for a in subj_subord_qs if a.subject not in all_children]
    return all_children


def get_immediate_context_parent_obj_db(child_obj):
    """Get the immediate (spatial) context parent of a child_obj"""
    # Import here to avoid circular imports.
    from opencontext_py.apps.all_items.models import AllAssertion

    p_assert = AllAssertion.objects.filter(
        predicate_id=configs.PREDICATE_CONTAINS_UUID,
        object=child_obj
    ).first()
    if not p_assert:
        return None
    return p_assert.subject


def get_immediate_context_children_objs_db(parent_obj):
    """Get the immediate (spatial) context children of a parent_obj"""

    # Import here to avoid circular imports.
    from opencontext_py.apps.all_items.models import AllAssertion

    return [
        a.object
        for a in AllAssertion.objects.filter(
            subject=parent_obj,
            predicate_id=configs.PREDICATE_CONTAINS_UUID,
        )
    ]


def get_immediate_concept_parent_objs(child_obj, use_cache=True):
    """Get the immediate parents of a child manifest object"""
    if not use_cache:
        return get_immediate_concept_parent_objs_db(child_obj)
    cache_key = f'{str(child_obj.uuid)}-concept-parents'
    cache = caches['redis']
    all_parents = cache.get(cache_key)
    if all_parents is not None:
        return all_parents
    # We don't have this cached yet, so get the result from
    # the cache.
    all_parents = get_immediate_concept_parent_objs_db(child_obj)
    try:
        cache.set(cache_key, all_parents)
    except:
        pass
    return all_parents


def get_immediate_concept_children_objs(parent_obj, use_cache=True):
    """Get the immediate children of a parent manifest object"""
    if not use_cache:
        return get_immediate_concept_children_objs_db(parent_obj)
    cache_key = f'{str(parent_obj.uuid)}-concept-children'
    cache = caches['redis']
    all_children = cache.get(cache_key)
    if all_children is not None:
        return all_children
    # We don't have this cached yet, so get the result from
    # the cache.
    all_children = get_immediate_concept_children_objs_db(parent_obj)
    try:
        cache.set(cache_key, all_children)
    except:
        pass
    return all_children


def get_immediate_context_parent_obj(child_obj, use_cache=True):
    """Get the immediate parents of a child manifest object"""
    if not use_cache:
        return get_immediate_context_parent_obj_db(child_obj)
    cache_key = f'{str(child_obj.uuid)}-context-parent'
    cache = caches['redis']
    parent_obj = cache.get(cache_key)
    if parent_obj is not None:
        return parent_obj
    # We don't have this cached yet, so get the result from
    # the cache.
    parent_obj = get_immediate_concept_parent_objs_db(child_obj)
    try:
        cache.set(cache_key, parent_obj)
    except:
        pass
    return parent_obj


def get_immediate_context_children_obs(parent_obj, use_cache=True):
    """Get the immediate children of a parent manifest object"""
    if not use_cache:
        return get_immediate_context_children_objs_db(parent_obj)
    cache_key = f'{str(parent_obj.uuid)}-context-children'
    cache = caches['redis']
    all_children = cache.get(cache_key)
    if all_children is not None:
        return all_children
    # We don't have this cached yet, so get the result from
    # the cache.
    all_children = get_immediate_context_children_objs_db(parent_obj)
    try:
        cache.set(cache_key, all_children)
    except:
        pass
    return all_children


def check_if_obj_is_concept_parent(
    is_a_parent_obj,
    of_obj,
    use_cache=True,
    max_depth=configs.MAX_HIERARCHY_DEPTH
):
    """Checks if is_a_parent_obj is a parent of the of_obj"""
    check_objs = [of_obj]
    i = 0
    while i <= max_depth and len(check_objs):
        i += 1
        parent_objs = []
        for check_obj in check_objs:
            # Add to the list of all the parents.
            parent_objs += get_immediate_concept_parent_objs(
                child_obj=check_obj,
                use_cache=use_cache
            )
        # Consolidate so to parent objs are unique.
        check_objs = list(set(parent_objs))
        for check_obj in check_objs:
            if check_obj == is_a_parent_obj:
               return True

    if i > max_depth:
        raise ValueError(
            f'Object {child_obj.uuid} too deep in hierarchy'
        )
    return False


def validate_context_subject_objects(subject_obj, object_obj):
    """Validates the correct item-types for context relations"""
    if subject_obj.item_type != "subjects":
        # Spatial context must be between 2
        # subjects items.
        raise ValueError(
            f'Subject must be item_type="subjects", not '
            f'{subject_obj.item_type} for {subject_obj.uuid}'
        )
    if object_obj.item_type != "subjects":
        # Spatial context must be between 2
        # subjects items.
        raise ValueError(
            f'Object must be item_type="subjects", not '
            f'{object_obj.item_type} for {object_obj.uuid}'
        )
    return True


def validate_context_assertion(
    subject_obj,
    object_obj,
    max_depth=configs.MAX_HIERARCHY_DEPTH
):
    """Validates a spatial context assertion"""
    validate_context_subject_objects(subject_obj, object_obj)

    obj_parent = get_immediate_context_parent_obj(
        child_obj=object_obj,
        use_cache=False
    )
    if obj_parent and obj_parent != subject_obj:
        # The child object already has a parent, and
        # we allow only 1 parent.
        raise ValueError(
            f'Object {object_obj.uuid} already contained in '
            f'{obj_parent.label} {obj_parent.uuid}'
        )
    subj_parent = subject_obj
    i = 0
    while i <= max_depth and subj_parent is not None:
        i += 1
        subj_parent = get_immediate_context_parent_obj(
            child_obj=subj_parent,
            use_cache=False
        )
        if subj_parent == object_obj:
            raise ValueError(
                'Circular containment error. '
                f'(Child) object {object_obj.uuid}: {object_obj.label} is a '
                f'parent object for {subject_obj.uuid}: {subject_obj.label}'
            )
    if i > max_depth:
        raise ValueError(
            f'Parent object {subject_obj.uuid} too deep in hierarchy'
        )
    print(
        f'Context containment OK: '
        f'{subject_obj.uuid}: {subject_obj.label} -> contains -> '
        f'{object_obj.uuid}: {object_obj.label}'
    )
    return True


def validate_hierarchy_assertion(
    subject_obj,
    predicate_obj,
    object_obj,
    max_depth=configs.MAX_HIERARCHY_DEPTH,
    use_cache=False,
):
    """Validates an assertion about a hierarchy relationship"""
    predicate_uuid = str(predicate_obj.uuid)
    check_preds = (
        configs.PREDICTATE_LIST_CONTEXT_SBJ_IS_SUPER_OF_OBJ
        + configs.PREDICATE_LIST_SBJ_IS_SUBORD_OF_OBJ
        + configs.PREDICATE_LIST_SBJ_IS_SUPER_OF_OBJ
    )
    if predicate_uuid not in check_preds:
        # Valid, not a hierarchy relationship that we
        # need to check
        return True

    if subject_obj == object_obj:
        raise ValueError(
            'An item cannot have a hierarchy relation to itself.'
        )

    if predicate_uuid in configs.PREDICTATE_LIST_CONTEXT_SBJ_IS_SUPER_OF_OBJ:
        # Spatial context relations only allowed between item_type 'subjects'
        validate_context_subject_objects(subject_obj, object_obj)

    if predicate_uuid == configs.PREDICATE_CONTAINS_UUID:
        # Do a special spatial context check.
        return validate_context_assertion(
            subject_obj,
            object_obj,
            max_depth=max_depth
        )

    # Everything below is to validate concept hierarchies.
    if predicate_uuid in configs.PREDICATE_LIST_SBJ_IS_SUBORD_OF_OBJ:
        # The subject item is subordinate to the object (parent) item.
        parent_obj = object_obj
        child_obj = subject_obj
    else:
        # The object item is subordinate to the subject (parent) item.
        # This will also apply for checking assertions about the
        # secondary spatial context PREDICATE_ALSO_CONTAINS_UUID
        parent_obj = subject_obj
        child_obj = object_obj

    # Check to see if this would be a circular hierarchy. A circular
    # hierarchy would happen if the child_obj happens to be a
    # parent concept of the parent_obj.
    is_circular = check_if_obj_is_concept_parent(
        is_a_parent_obj=child_obj,
        of_obj=parent_obj,
        use_cache=use_cache,
        max_depth= max_depth
    )
    if is_circular:
        raise ValueError(
            'Circular hierarchy error. '
            f'(Child) object {child_obj.uuid}: {child_obj.label} is a '
            f'parent object for {parent_obj.uuid}: {parent_obj.label}'
        )

    print(
        f'Concept hierarchy OK: '
        f'{parent_obj.uuid}: {parent_obj.label} -> has child -> '
        f'{child_obj.uuid}: {child_obj.label}'
    )
    return True


def validate_has_unit_assertion(predicate_obj, object_obj):
    """Checks that the object of a cidoc-crm:P91_has_unit is a unit"""
    if str(predicate_obj.uuid) != configs.PREDICATE_CIDOC_HAS_UNIT_UUID:
        # Not a cidoc-crm:P91_has_unit assertion, so skip this
        # validation check.
        return True
    if object_obj.item_type != 'units':
        raise ValueError(
            f'Object {child_obj.label} ({child_obj.uuid}) has item_type of '
            f'"{ object_obj.item_type}"" not "units".'
        )


# ---------------------------------------------------------------------
# Functions for Resources
# ---------------------------------------------------------------------
def validate_resourcetype_id(resourcetype_id, raise_on_fail=True):
    """Validates the resource type against a configured list of valid class entities"""
    resourcetype_id = str(resourcetype_id)
    if resourcetype_id in configs.OC_RESOURCE_TYPES_UUIDS:
        return True
    if not raise_on_fail:
        return False
    raise ValueError(
        f'Resourcetype {resourcetype_id} not in valid list: {str(configs.OC_RESOURCE_TYPES_UUIDS)}'
    )


def check_geojson_media_type_obj(uri):
    """Checks if the extension says geojson"""

     # Import here to avoid circular imports.
    from opencontext_py.apps.all_items.models import AllManifest

    uri = uri.lower()
    if not uri.endswith('.geojson'):
        return None
    return AllManifest.objects.filter(
        item_type='media-types',
        uuid=configs.MEDIA_TYPE_GEO_JSON_UUID,
    ).first()


def get_media_type_obj(uri, raw_media_type):
    """Gets a media-type manifest object"""

    # Import here to avoid circular imports.
    from opencontext_py.apps.all_items.models import AllManifest

    media_type_obj = None
    media_type_qs = AllManifest.objects.filter(
        item_type='media-types',
    )
    if raw_media_type:
        media_type_obj = media_type_qs.filter(
                Q(meta_json__template=raw_media_type)
                |
                Q(item_key=f'media-type:{raw_media_type}')
            ).first()
    if media_type_obj:
        return media_type_obj

    # Now check to see if it matches a geojson extension
    media_type_obj = check_geojson_media_type_obj(uri)
    if media_type_obj:
        return media_type_obj

    # Guess by file extension. We can add to this as needed,
    # but for now, we're only guessing media type of Nexus
    # 3D format file extensions.
    guesses = [
        ('nxs', configs.MEDIA_NEXUS_3D_NXS_UUID, ),
        ('nxz', configs.MEDIA_NEXUS_3D_NXZ_UUID, ),
        ('geojson', configs.MEDIA_TYPE_GEO_JSON_UUID, ),
    ]
    uri = uri.lower()
    for extension, uuid in guesses:
        if not uri.endswith(f'.{extension}'):
            continue
        # Return the media_object for this extention
        return media_type_qs.filter(
            uuid=uuid
        ).first()
    return None



def get_web_resource_head_info(uri, redirect_ok=False, retry=True, protocol='https://'):
    """Gets header information about a web resource"""

    # Import here to avoid circular imports.
    from opencontext_py.apps.all_items.models import AllManifest

    sleep(0.1)
    output = {}
    try:
        raw_media_type = None
        uri = AllManifest().clean_uri(uri)
        uri = protocol + uri
        r = requests.head(uri)
        if (
            (r.status_code == requests.codes.ok)
            or
            (redirect_ok and r.status_code >= 300 and r.status_code <= 310)
        ):
            if r.headers.get('Content-Length'):
                output['filesize'] = int(r.headers['Content-Length'])
            if r.headers.get('location'):
                output['location'] = r.headers['location']
            if r.headers.get('Content-Type'):
                raw_media_type = r.headers['Content-Type']
                if ':' in raw_media_type:
                    raw_media_type = raw_media_type.split(':')[-1].strip()
            output['mediatype'] = get_media_type_obj(uri, raw_media_type)
    except:
        pass

    if retry and not output.get('filesize'):
        output = get_web_resource_head_info(
            uri,
            redirect_ok=redirect_ok,
            retry= False
        )
        if not output.get('filesize'):
            # Now try again without the https.
            output = get_web_resource_head_info(
                uri,
                redirect_ok=redirect_ok,
                retry= False,
                protocol='http://'
            )
    return output
