import copy
import hashlib
import uuid as GenUUID

import numpy as np
import pandas as pd

from django.conf import settings
from django.core.cache import caches


from opencontext_py.apps.all_items import configs
from opencontext_py.apps.all_items.models import (
    AllManifest,
)

# NOTE: This import is used to get "context" of assertions made on
# project-specific "predicates" and "types" items. These
# assertions may include equivalence relations to Linked Data
# entities.
from opencontext_py.apps.all_items.project_contexts import context

from opencontext_py.apps.all_items.representations.rep_utils import (
    ASSERTION_DATA_TYPE_LITERAL_MAPPINGS
)

from opencontext_py.apps.all_items.representations import item_class_defaults

LITERAL_ASSERTION_ATTRIBUTES = [v for _, v in ASSERTION_DATA_TYPE_LITERAL_MAPPINGS.items()]

# Make these from fixtures so don't need to query the DB
EQUIV_OBS_OBJECT = AllManifest(**configs.DEFAULT_EQUIV_OBS_DICT)
DEFAULT_CLASS_OBJECT = AllManifest(**configs.DEFAULT_CLASS_DICT)
DEFAULT_EVENT_OBJECT = AllManifest(**configs.DEFAULT_EVENT_DICT)
DEFAULT_ATTRIBUTE_GROUP_OBJECT = AllManifest(**configs.DEFAULT_ATTRIBUTE_GROUP_DICT)
DEFAULT_LANGUAGE_OBJECT = AllManifest(**configs.DEFAULT_LANGUAGE_DICT)


# ---------------------------------------------------------------------
# NOTE: About equivalent_ld
#
# Open Context editors often use SKOS "closeMatch" or other predicates
# to assign equivalence relationships between project-specific
# "predicates" and "types" item_types and other Linked Data entities
# curated by other institutions and data systems. Equivalence
# relationships with these Linked Data entities adds some meaningful
# context and interoperability across datasets in Open Context.
#
# The main point of equivalent_ld is to add assertions about an
# item based on equivalence relationships between project-specific
# "predicates" and "types" that are used to describe a given item
# and Linked Data entities.
#
# For example, an animal bone item may have a descriptive
# assertion using project specific "predicates" and "types" like:
#
# "Bone 1" -> "Is Species" (predicates) -> "Wolf" (types)
#
# We use context.get_item_context_df to look up equivalence
# relationships for "Is Species" and "Wolf" and find that:
#
# "Is Species" -> "Close Match" -> "http://purl.obolibrary.org/obo/FOODON_00001303" (Has taxonomic ID)
# "Wolf" -> "Close Match" -> "https://www.gbif.org/species/5219173" (Canis lupus)
#
# In this case, the equivalent_ld adds the inferred assertion:
#
# "Bone 1" -> Has taxonomic ID -> Canis lupus
#
#
# The functions and classes in equivalent_ld are used to add
# "assertion analog objects", which are instances of the
# NotStoredAssertion and the NotStoredManifestItem classes.
# These objects have attributes in common with the AllAssertion
# and the AllManifest models, so they can be processed in the same
# way. The main difference is that instances of the NotStoredAssertion
# and the NotStoredManifestItem classes don't get stored in the
# database.
#
# ---------------------------------------------------------------------


class NotStoredManifestItem():
    """A Not Stored analog to a Manifest item"""

    def __init__(self):
        self.uuid = None
        self.project = None
        self.item_class = DEFAULT_CLASS_OBJECT
        self.item_type = None
        self.data_type = None
        self.slug = None
        self.label = None
        self.uri = None
        self.item_key = None
        self.context = None
        self.meta_json = {}

    def populate_from_context_df_row_cols(self, row, cols):
        """Populates from columns in a context_df row

        :param DataFrame.row row: A row form a context_df
            dataframe
        :param list cols: A list of columns with data
            that will populate this instance
        """
        attributes_col_ends = [
            ('uuid', '_id',),
            ('item_type', '__item_type',),
            ('data_type', '__data_type',),
            ('slug', '__slug',),
            ('label', '__label',),
            ('uri', '__uri',),
            ('item_key', '__item_key',),
            ('meta_json', '__meta_json',),
        ]
        for col in cols:
            for attrib, col_end in attributes_col_ends:
                if not col.endswith(col_end):
                    continue
                attrib_value = row[col]
                setattr(self, attrib, attrib_value)


class NotStoredAssertion():
    """A Not Stored analog to an Assertion item"""

    def __init__(self, item_man_obj=None):
        self.uuid = str(GenUUID.uuid4())
        self.project = None
        self.subject = None
        if item_man_obj:
            self.project = item_man_obj.project
            self.subject = item_man_obj
        self.observation = EQUIV_OBS_OBJECT
        self.event = DEFAULT_EVENT_OBJECT
        self.attribute_group = DEFAULT_ATTRIBUTE_GROUP_OBJECT
        self.predicate = None
        self.sort = 0
        self.language = DEFAULT_LANGUAGE_OBJECT
        self.object = None
        self.obj_string = None
        self.obj_boolean = None
        self.obj_integer = None
        self.obj_double = None
        self.obj_datetime = None
        self.updated = None
        self.created = None
        if item_man_obj:
            self.updated = item_man_obj.updated
            self.created = item_man_obj.updated
        self.meta_json = {}
        self.object_class_icon = None
        self.for_solr = False


    @property
    def hash_id(self):
        """Make a hash_id for the assertion based on content"""

        # NOTE: This is just a simple way to make a finger print
        # for these temp (fake) assertions, so we can know that
        # we're actually making unique fake assertions.

        hash_obj = hashlib.sha1()
        act_str = (
            f'{str(self.obj_string)} '
            f'{str(self.obj_boolean)} '
            f'{str(self.obj_integer)} '
            f'{str(self.obj_double)} '
            f'{str(self.obj_datetime)} '
        )
        rel_objs = [
            self.subject,
            self.observation,
            self.event,
            self.attribute_group,
            self.predicate,
            self.object,
        ]
        for rel_obj in rel_objs:
            if rel_obj is None:
                act_str += ' None '
                continue
            act_str += f' {str(rel_obj.uuid)}'
        hash_obj.update(act_str.encode('utf-8'))
        return hash_obj.hexdigest()


    def make_temp_equiv_obj_from_context_df_row(self, equiv_row, equiv_obj='predicate'):
        """Makes an equivalent object of a given type from a context_df row"""
        if self.for_solr:
            act_item = get_real_man_obj_from_equiv_row(equiv_row)
        else:
            act_context = NotStoredManifestItem()
            act_context.populate_from_context_df_row_cols(
                equiv_row,
                cols=[
                    f'object__context_id',
                    f'object__context__item_type',
                    f'object__context__label',
                    f'object__context__uri',
                    f'object__context__meta_json'
                ],
            )
            act_item = NotStoredManifestItem()
            act_item.populate_from_context_df_row_cols(
                equiv_row,
                cols=[
                    f'object_id',
                    f'object__item_key',
                    f'object__uri',
                    f'object__slug',
                    f'object__item_type',
                    f'object__data_type',
                    f'object__label',
                    f'object__meta_json',
                ],
            )
            act_item.context = act_context
        if equiv_obj == 'predicate':
            self.predicate = act_item
        elif equiv_obj == 'object':
            self.object = act_item


def make_manifest_obj_cache_key(uuid):
    """Make a cache key for fetching a manifest object by cache key"""
    return f'{settings.CACHE_PREFIX_MANIFEST_OBJ}{str(uuid)}'


def cache_all_df_context_related_manifest_objects(df_context):
    cache = caches['redis']
    if not 'object_id' in df_context.columns:
        return None
    all_uuids = df_context[
        ~df_context['object_id'].isnull()
        & (df_context['object_id'] != 'nan')
    ]['object_id'].unique().tolist()
    uuids = []
    for uuid in all_uuids:
        cache_key = make_manifest_obj_cache_key(uuid)
        if cache.get(cache_key):
            # We've already got this cached.
            continue
        uuids.append(uuid)

    mqs = AllManifest.objects.filter(
        uuid__in=uuids
    ).select_related(
        'context'
    )
    for man_obj in mqs:
        cache_key = make_manifest_obj_cache_key(man_obj.uuid)
        try:
            cache.set(cache_key, man_obj)
        except:
            pass


def get_real_man_obj_from_equiv_row(equiv_row, use_cache=True):
    """Get a real manifest object from an equivalence row"""
    uuid = equiv_row['object_id']
    man_obj = None
    cache_key = None
    if use_cache:
        cache_key = make_manifest_obj_cache_key(uuid)
        cache = caches['redis']
        man_obj = cache.get(cache_key)
    if man_obj:
        return man_obj
    man_obj = AllManifest.objects.filter(
        uuid=uuid
    ).select_related(
        'context'
    ).first()
    if cache_key:
        try:
            cache.set(cache_key, man_obj)
        except:
            pass
    return man_obj


def add_to_list_new_no_store_assertion(ns_ass, ns_asserts=None):
    """Adds to a list a No-store-assertion if not already present"""
    if not ns_asserts:
        ns_asserts = []
    ids = [n.hash_id for n in ns_asserts]
    if ns_ass.hash_id in ids:
        # This already exists in our list, so just return the list
        # un modified
        return ns_asserts
    ns_asserts.append(ns_ass)
    return ns_asserts


def make_ld_equivalent_assertions(item_man_obj, assert_qs, for_solr=False):
    """Gets an observation of equivalent linked data describing an item

    :param AllManifest item_man_obj: Instance of the AllManifest model that
        we are describing with equivalent linked data.
    :param QuerySet assert_qs: A query set of assertions made on the item
    """
    if not assert_qs:
        return None

    # NOTE: The context_df structure makes assertions about project specific
    # 'predicates' and 'types' item_types, which are the subjects of the
    # assertions. The df_context 'predicates' columns note the type of
    # predicate relationship (especially linked data equivalences). The
    # object columns descripe what linked data entities the
    # (subject) project-specific 'predicates' and 'types' equate to.

    preds = []
    types = []
    pred_id_keyed_asserts = {}
    for act_ass in assert_qs:
        if act_ass.predicate.item_type != 'predicates':
            # Not a project-specific predicates item type
            continue
        if not act_ass.predicate in preds:
            preds.append(act_ass.predicate)
        str_pred_id = str(act_ass.predicate.uuid)
        pred_id_keyed_asserts.setdefault(
           str_pred_id,
            []
        )
        pred_id_keyed_asserts[str_pred_id].append(act_ass)
        if (str(act_ass.object.uuid) != configs.DEFAULT_NULL_OBJECT_UUID
            and act_ass.object.item_type == 'types'
            and not act_ass.object in types):
            types.append(act_ass.object)

    # Get a dataframe that provides linked data context for the
    # predicates and types items from our assert_qs.
    pred_id_list = [str(m.uuid) for m in preds]
    type_id_list = [str(m.uuid) for m in types]
    df_context = context.get_item_context_df(
        (pred_id_list + type_id_list),
        item_man_obj.project.uuid
    )
    if df_context is None or df_context.empty:
        # We have nothing to add, so skip out.
        return None

    if for_solr:
        # We're indexing solr documents and need the related
        # manifest objects.
        cache_all_df_context_related_manifest_objects(df_context)

    if not 'object__label' in df_context.columns:
        # We have nothing to add, so skip out.
        return None

    # Sort the context dataframes.
    df_context.sort_values(
        by=['subject__data_type', 'object__label'],
        inplace=True
    )

    # Make an index that of assertions that where the project-specific
    # predicates have some sort of equivalence relationships asserted in the
    # df_context.
    all_equiv_pred_index = (
        df_context['subject_id'].isin(pred_id_list)
        & df_context['predicate_id'].isin(configs.PREDICATE_LIST_SBJ_EQUIV_OBJ)
    )
    if df_context[all_equiv_pred_index].empty:
        # There are no linked data equivalences to the predicates
        # in this item.
        return None

    equiv_assertions = []
    # Iterate first through the ld equivalent predicates that we found. The
    # equiv_ld_pred_id is the object of an equivalence relationship with a
    # project-specific 'predicates' item in the df_context['subject_id']
    for equiv_ld_pred_id in df_context[all_equiv_pred_index]['object_id'].unique():
        equiv_pred_index = all_equiv_pred_index & (
            df_context['object_id'] == equiv_ld_pred_id
        )

        # OK! Now iterate through all of the project predicates that are
        # equivalent to the equiv_ld_pred_id.
        # NOTE: The 'subject_id' column of the df_context is the subject of
        # the equivalence relationship with a linked data

        # This gathers all the 'real assertions' using project specific
        # predicates that are equivalent to the equiv_ld_pred_id.
        act_real_asserts = []
        for proj_pred_id in df_context[equiv_pred_index]['subject_id'].unique():
            act_real_asserts += pred_id_keyed_asserts.get(
                proj_pred_id,
                []
            )

        if not len(act_real_asserts):
            # This should not happen, but handle it nicely.
            continue

        # This, weirdly, gets the first row of the df_context that has
        # our equiv_ld_pred_id as the 'object_id'.
        equiv_pred_row = next(df_context[equiv_pred_index].iterrows())[1]

        # Now iterate through all of the 'real assertions' come from
        # project-specific predicates equivalent to the equiv_ld_pred_id.
        # We do this to create not-stored assertions based on these
        # real assertions.
        for real_assert in act_real_asserts:

            # Make a new Not-Stored assertion object, populating
            # the subject part.
            ns_ass = NotStoredAssertion(item_man_obj)
            ns_ass.for_solr = for_solr

            # Now add the predicate part. The predicate will be for the
            # equiv_ld_pred_id id.
            ns_ass.make_temp_equiv_obj_from_context_df_row(
                equiv_pred_row,
                equiv_obj='predicate'
            )

            # Make sure we have agreement in the data type of the
            # not-stored assertion and the real_assert.
            ns_ass.predicate.data_type = real_assert.predicate.data_type
            # Also make sure the not-stored assertion has the
            # same language as the real_assert.
            ns_ass.language = real_assert.language

            # Use the real assertion time stamps for this not-stored
            # assertion.
            ns_ass.updated = real_assert.updated
            ns_ass.created = real_assert.created
            if hasattr(real_assert, 'object_class_icon'):
                ns_ass.object_class_icon = real_assert.object_class_icon

            if real_assert.predicate.data_type != 'id':
                # This assertion has a literal value. Copy this into the ns_ass.
                ns_ass.obj_string = real_assert.obj_string
                ns_ass.obj_boolean = real_assert.obj_boolean
                ns_ass.obj_integer = real_assert.obj_integer
                ns_ass.obj_double = real_assert.obj_double
                ns_ass.obj_datetime = real_assert.obj_datetime

                equiv_assertions = add_to_list_new_no_store_assertion(
                    ns_ass,
                    ns_asserts=equiv_assertions
                )
                continue

            # If we're here, we have to deal with the fact that the
            # named entity object of the real_assert may itself have
            # 0 or more linked data equivalences.
            equiv_assert_obj_index = (
                (df_context['subject_id'] == str(real_assert.object.uuid))
                & df_context['predicate_id'].isin(configs.PREDICATE_LIST_SBJ_EQUIV_OBJ)
            )
            if df_context[equiv_assert_obj_index].empty:
                # OK. The named entity that's the object of the real_assert
                # does NOT have a linked data equivalent. So we'll fall back on
                # using the real object of real assertion.
                ns_ass.object = real_assert.object
                equiv_assertions = add_to_list_new_no_store_assertion(
                    ns_ass,
                    ns_asserts=equiv_assertions
                )
                continue

            # OK, we have 1 or more linked data equivalents to the object
            # of the real_assert. Iterate through those equivalents to make
            # new not-stored assertions.
            for _, equiv_obj_row in df_context[equiv_assert_obj_index].iterrows():
                obj_ns_ass = copy.deepcopy(ns_ass)
                obj_ns_ass.make_temp_equiv_obj_from_context_df_row(
                    equiv_obj_row,
                    equiv_obj='object'
                )
                equiv_assertions = add_to_list_new_no_store_assertion(
                    obj_ns_ass,
                    ns_asserts=equiv_assertions
                )

    # OK! We should have all of our glorious not-stored linked data
    # equivalence assertions to return.
    return equiv_assertions


def temp_man_obj_populate_attributes_from_dict(man_dict):
    """Returns a Manifest object (that's not saved) based
    on cleaning the contents of a man_dict
    """
    attrib_keys = [
        'uuid',
        'item_type',
        'data_type',
        'slug',
        'label',
        'uri',
        'meta_json',
    ]
    clean_man_dict = {}
    for attrib in attrib_keys:
        attrib_value = man_dict.get(attrib)
        if not attrib_value:
            continue
        if attrib == 'uuid':
            attrib_value = GenUUID.UUID(str(attrib_value))
        clean_man_dict[attrib] = attrib_value
    man_obj = AllManifest(**clean_man_dict)
    return man_obj


def make_nested_not_stored_man_obj(man_dict):
    main_man_obj = temp_man_obj_populate_attributes_from_dict(man_dict)
    for rel_obj_prefix in ['project', 'item_class', 'context']:
        rel_obj_dict = {}
        for key, val in man_dict.items():
            if not key.startswith(rel_obj_prefix):
                continue
            if key == f'{rel_obj_prefix}_id':
                rel_obj_dict['uuid'] = val
                continue
            dict_key = key.replace(f'{rel_obj_prefix}__', '')
            rel_obj_dict[dict_key] = val
        rel_obj = temp_man_obj_populate_attributes_from_dict(rel_obj_dict)
        setattr(main_man_obj, rel_obj_prefix, rel_obj)
    return main_man_obj


def add_default_ld_equivalent_assertions(item_man_obj, equiv_assertions, for_solr=False):
    """Adds default equivalent linked data assertions if needed

    :param AllManifest item_man_obj: Instance of the AllManifest model that
        we are describing with equivalent linked data.
    :param list equiv_assertions: The current list of equivalent linked
        data assertions
    """
    if not item_man_obj:
        return equiv_assertions
    act_default_dict = item_class_defaults.ITEM_CLASS_ASSERTIONS.get(
        item_man_obj.item_class.slug
    )
    if not act_default_dict:
        # We don't have default assertions configured for this
        # item_class.slug, so skip out.
        return equiv_assertions
    for default_pred_slug, default_obj_dict in act_default_dict.items():
        pred_dict = item_class_defaults.PREDICATES.get(
            default_pred_slug
        )
        if not pred_dict:
            # Our configuration is broken / incomplete
            continue
        pred_slug_found = False
        for equiv_ass in equiv_assertions:
            if equiv_ass.predicate.slug == default_pred_slug:
                pred_slug_found = True
                break
        if pred_slug_found:
            print(f'we found the expected default predicate {default_pred_slug}')
            # We already have an assertion using this predicate, so
            # we don't need to add a default.
            continue
        # Make a new (fake) assertion for this item.
        ns_ass = NotStoredAssertion(item_man_obj)
        ns_ass.for_solr = for_solr
        pred_obj = make_nested_not_stored_man_obj(pred_dict)
        obj_obj = make_nested_not_stored_man_obj(default_obj_dict)
        ns_ass.predicate = pred_obj
        ns_ass.object = obj_obj
        print(f'Adding default assertion for predicate {default_pred_slug}')
        equiv_assertions.append(ns_ass)
    return equiv_assertions