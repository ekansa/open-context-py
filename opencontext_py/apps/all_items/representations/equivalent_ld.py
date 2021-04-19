
import copy
import hashlib
import uuid as GenUUID

from opencontext_py.libs.general import LastUpdatedOrderedDict

from opencontext_py.apps.all_items import configs
from opencontext_py.apps.all_items.models import (
    AllManifest,
    AllAssertion,
    AllHistory,
    AllResource,
    AllIdentifier,
    AllSpaceTime,
)
from opencontext_py.apps.all_items import utilities
from opencontext_py.apps.all_items.project_contexts import context


# Make these from fixtures so don't need to query the DB
EQUIV_OBS_OBJECT = AllManifest(**configs.DEFAULT_EQUIV_OBS_DICT)
DEFAULT_EVENT_OBJECT = AllManifest(**configs.DEFAULT_EVENT_DICT)
DEFAULT_ATTRIBUTE_GROUP_OBJECT = AllManifest(**configs.DEFAULT_ATTRIBUTE_GROUP_DICT)


class TempItem():
    """A Temporary item to simulate an All Manifest item"""
    def __init__(self):
        self.uuid = None
        self.project = None
        self.item_class = None
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
            (self.uuid, '_id',),
            (self.item_type, '__item_type',),
            (self.data_type, '__data_type',),
            (self.slug, '__slug',),
            (self.label, '__label',),
            (self.uri, '__uri',),
            (self.item_key, '__item_key',),
            (self.meta_json, '__meta_json',),
        ]
        for col in cols:
            for attrib, col_end in attributes_col_ends:
                if not col.endswith(col_end):
                    continue
                attrib = row[col]


class TempAssert():
    def __init__(self, item_man_obj=None):
        self.uuid = None
        self.project = None
        self.subject = None
        if item_man_obj:
            self.project = item_man_obj.project
            self.subject = item_man_obj
        self.observation = EQUIV_OBS_OBJECT
        self.event = DEFAULT_EVENT_OBJECT
        self.attribute_group = DEFAULT_ATTRIBUTE_GROUP_OBJECT
        self.predicate = None
        self.object = None
        self.language = None
        self.obj_string = None
        self.obj_boolean = None
        self.obj_double = None
        self.obj_integer = None
        self.obj_datetime = None


    def make_temp_equiv_obj_from_context_df_row(self, equiv_row, equiv_obj='predicate'):
        """Makes an equivalent object of a given type from a context_df row"""
        act_context = TempItem()
        act_context.populate_from_context_df_row_cols(
            equiv_row,
            cols=[
                f'{equiv_obj}__context_id',
                f'{equiv_obj}__context__label',
                f'{equiv_obj}__context__uri',
                f'{equiv_obj}__context__meta_json'
            ],
        )
        act_obj = TempItem()
        act_obj.populate_from_context_df_row_cols(
            equiv_row,
            cols=[
                f'{equiv_obj}_id',
                f'{equiv_obj}__item_key',
                f'{equiv_obj}__uri',
                f'{equiv_obj}__slug',
                f'{equiv_obj}__item_type',
                f'{equiv_obj}__data_type',
                f'{equiv_obj}__label',
            ],
        )
        act_obj.context = act_context
        if equiv_obj == 'predicate':
            self.predicate = act_obj
        elif equiv_obj == 'object':
            self.object = act_obj



def make_ld_equivalent_assertions(item_man_obj, assert_qs):
    """Gets an observation of equivalent linked data describing an item

    :param AllManifest item_man_obj: Instance of the AllManifest model that
        we are describing with equivalent linked data.
    :param QuerySet assert_qs: A query set of assertions made on the item
    """
    if not assert_qs:
        return None
    
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

    # Make an index that of assertions that 
    equiv_pred_index = (
        df_context['subject_id'].isin(pred_id_list)
        & df_context['predicate_id'].isin(configs.PREDICATE_LIST_SBJ_EQUIV_OBJ)
    )
    if df_context[equiv_pred_index].empty:
        # There are no linked data equivalences to the predicates
        # in this item.
        return None
    
    equiv_asserts = []

    