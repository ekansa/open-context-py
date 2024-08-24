import json

from django.conf import settings
from django.contrib.humanize.templatetags.humanize import intcomma

from opencontext_py.apps.publish_costs.models import PublishEstimate


EARLY_CAREER_DISCOUNT = 0.5  # 50%
BASE_COST = 300
MAX_COST = 20000
IMAGE_COST = 5
OTHER_COST = 20
DOC_COST = 15
GIS_COST = 25





def float_convert(val):
    """Converts a value to float"""
    if isinstance(val, float):
        return val
    if isinstance(val, str):
        return float(val)
    return 0


def estimate_cost(
    is_early_career=False,
    duration=1,
    count_spec_datasets=1,
    count_tables=0,
    count_images=0,
    count_docs=0,
    count_gis=0,
    count_other=0,
    base_cost=BASE_COST, 
    max_cost=MAX_COST,
):
    """ Estimates the cost, in us dollars """
    
    cost = (base_cost * (float_convert(duration) * .5)) \
        + (base_cost * (float_convert(count_spec_datasets) * .75)) \
        + (base_cost * (float_convert(count_tables) * .5)) \
        + (IMAGE_COST * ((float_convert(count_images) + 10) / 15)) \
        + (DOC_COST * ((float_convert(count_docs) + 10) / 15)) \
        + (GIS_COST * ((float_convert(count_gis) + 5) / 5)) \
        + (OTHER_COST * ((float_convert(count_other) + 10) / 5))
    cost = round((float(cost) * 0.1), 0) * 10
    raw_cost = cost
    if cost < base_cost:
        cost = base_cost
    if is_early_career == '1' or is_early_career == True:
        is_early_career = True
    else:
        is_early_career = False
    if is_early_career:
        cost = cost - (cost * EARLY_CAREER_DISCOUNT)
    max_cost_more = cost > max_cost
    if max_cost_more:
        cost = max_cost
    cost = round((float(cost) * 0.1), 0) * 10
    return cost, raw_cost, max_cost_more


def format_currency(dollars):
    """ Provides a cost estimate in formatted dollars """
    dollars = round(float(dollars), 2)
    return "$%s%s" % (intcomma(int(dollars)), ("%0.2f" % dollars)[-3:])


def estimate_cost_json(session_key, input_json, record_estimate=True):
    if not isinstance(input_json, dict):
        return {
            'estimate_id': '(not recorded)',
            'cost': None,
            'dollar_cost': None,
            'with_discount': None,
        }
    if not session_key:
        session_key = 'no_session_key'
    arg_keys = [
        'is_early_career',
        'duration',
        'count_spec_datasets',
        'count_tables',
        'count_images',
        'count_docs',
        'count_gis',
        'count_other',
    ]
    cost_args = {k: input_json.get(k) for k in arg_keys if input_json.get(k)}
    cost, raw_cost, max_cost_more = estimate_cost(**cost_args)
    with_discount = False
    if cost_args.get('is_early_career') == '1' or cost_args.get('is_early_career') == True:
        with_discount = True
    pub_est = None
    if record_estimate:
        input_json['raw_cost'] = raw_cost
        input_json['max_cost_more'] = max_cost_more
        # Get or create based on the inputs. Ths avoids needing special checks for uniqueness.
        pub_est, _ = PublishEstimate.objects.get_or_create(
            session_id=session_key,
            estimated_cost=cost,
            input_json=input_json,
        )
        
    output = {
        'estimate_id': '(not recorded)',
        'cost': cost,
        'dollar_cost': format_currency(cost),
        'with_discount': with_discount,
    }
    if pub_est:
        output['estimate_id'] = str(pub_est.uuid)
    return output