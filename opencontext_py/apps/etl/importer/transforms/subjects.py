import os
import numpy as np
import pandas as pd

from django.db.models import Q

from opencontext_py.apps.all_items import configs
from opencontext_py.apps.all_items.models import (
    AllManifest,
    AllAssertion,
)

from opencontext_py.apps.etl.importer.models import (
    DataSource,
    DataSourceField,
    DataSourceRecord,
    DataSourceAnnotation,
)

# ---------------------------------------------------------------------
# NOTE: These functions manage the transformations of item_type
# subjects items
# ---------------------------------------------------------------------
def get_containment_annotation_qs(ds_source):
    """Gets a queryset for containment annotations for this data source"""
    return DataSourceAnnotation.objects.filter(
        data_source=ds_source,
        subject_field__item_type='subjects',
        predicate_id=configs.PREDICATE_CONTAINS_UUID,
        object_field__item_type='subjects',
    )


def get_subjects_ds_field_containment_root(ds_source):
    """Gets a list of ds_fields in a hierarchy order"""
    contain_qs = get_containment_annotation_qs(ds_source)

    children_field_qs = contain_qs.order_by(
        'object_field'
    ).distinct(
        'object_field'
    ).values_list('object_field', flat=True)
    
    root_contain_anno = contain_qs.exclude(
        # The root is not the object of the another
        # containment annotation so exclude children fields
        # from the subject field.
        subject_field__in=children_field_qs
    ).first()
    return root_contain_anno




