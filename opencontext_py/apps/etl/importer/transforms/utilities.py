import logging

import numpy as np
import pandas as pd


from opencontext_py.apps.all_items import configs
from opencontext_py.apps.all_items.models import (
    AllManifest,
    AllAssertion,
    AllSpaceTime,
    AllResource,
    AllIdentifier,
)

from opencontext_py.apps.etl.importer.models import (
    DataSource,
    DataSourceField,
    DataSourceRecord,
    DataSourceAnnotation,
    get_immediate_context_parent_obj_db,
    get_immediate_context_children_objs_db,
)

from opencontext_py.apps.etl.importer import df as etl_df
from opencontext_py.apps.etl.importer import utilities as etl_utils

from opencontext_py.apps.etl.importer.transforms import assertions
from opencontext_py.apps.etl.importer.transforms import general_named_entities
from opencontext_py.apps.etl.importer.transforms import media_resources
from opencontext_py.apps.etl.importer.transforms import predicates_types_variables
from opencontext_py.apps.etl.importer.transforms import space_time_events
from opencontext_py.apps.etl.importer.transforms import subjects


logger = logging.getLogger("etl-importer-logger")


def bulk_create_assertions(assert_uuids, unsaved_assert_objs, print_errors=True):
    # Delete based on the f
    AllAssertion.objects.filter(
        uuid__in=assert_uuids
    ).delete()
    try:
        AllAssertion.objects.bulk_create(
            unsaved_assert_objs
        )
        ok = True
    except Exception as e:
        ok = False
        if hasattr(e, 'message'):
            error = e.message
        else:
            error = str(e)
        if print_errors:
            print(f'Bulk assertion failed: {error}')

    if ok:
        # We managed to save all, in bulk, without error.
        return unsaved_assert_objs

    # This part iterates through the entire list of unsaved_assert_objs
    # to attempt to save them 1 by 1. It will be lots slower than the
    # bulk create, but we shouldn't be here too much unless something is
    # wrong.
    ok_saved_assert_objs = []
    for assert_obj in unsaved_assert_objs:
        if getattr(assert_obj, 'uuid'):
            # Delete the assertion object that already has this uuid.
            AllAssertion.objects.filter(
                uuid=assert_obj.uuid
            ).delete()
        try:
            assert_obj.save()
            ok = True
        except Exception as e:
            ok = False
            if hasattr(e, 'message'):
                error = e.message
            else:
                error = str(e)
            if print_errors:
                print(f'Single assertion failed: {error}')
        if ok:
            ok_saved_assert_objs.append(assert_obj)
    return ok_saved_assert_objs