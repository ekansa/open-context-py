
import numpy as np
import pandas as pd

from sklearn.cluster import KMeans, AffinityPropagation, SpectralClustering
from shapely.geometry import mapping, shape


from django.db.models import Q


from opencontext_py.libs.globalmaptiles import GlobalMercator

from opencontext_py.apps.all_items import configs
from opencontext_py.apps.all_items.models import (
    AllManifest,
    AllSpaceTime,
    AllAssertion,
)

from opencontext_py.apps.all_items.geospace import aggregate as geo_agg



def find_outliers_irq(df):
   q1=df.quantile(0.25)
   q3=df.quantile(0.75)
   IQR=q3-q1
   outliers = df[((df<(q1-1.5*IQR)) | (df>(q3+1.5*IQR)))]
   return outliers



def check_points_within_spatial_context(
    parent_man_obj=None,
    parent_uuid=None,
    difference_factor_to_flag=10,
):
    """Checks points contained within an item to find outliers"""
    if not parent_man_obj and parent_uuid:
        parent_man_obj = AllManifest.objects.filter(uuid=parent_uuid).first()
    if not parent_man_obj:
        return None
    space_time_qs = AllSpaceTime.objects.filter(
        item__path__startswith=parent_man_obj.path,
        geometry__isnull=False,
    ).exclude(
        item=parent_man_obj
    )
    df = geo_agg.make_df_from_space_time_qs(space_time_qs, add_item_cols=True)
    dd = df.describe()[['longitude', 'latitude']]
    for c_col in ['longitude', 'latitude']:
        flag_col = f'flag__{c_col }'
        df[flag_col] = False
        mid_val =  dd.loc['50%', c_col]
        # get the maximum range between the middle 50% and the 25% and 75% values
        mid_range = max([abs(mid_val - dd.loc['25%', c_col]), abs(mid_val - dd.loc['75%', c_col])])
        extreme_low_val = mid_val - (mid_range * difference_factor_to_flag)
        extreme_high_val = mid_val + (mid_range * difference_factor_to_flag)
        extreme_index = (
            (df[c_col] <= extreme_low_val)
            | (df[c_col] >= extreme_high_val)
        )
        print(f'Found {len(df[extreme_index])} with extreme {c_col}')
        df.loc[extreme_index, flag_col] = True
    return df
