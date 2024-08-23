import json

from django.conf import settings
from django.contrib.humanize.templatetags.humanize import intcomma


EARLY_CAREER_DISCOUNT = 0.5  # 50%
BASE_COST = 300
MAX_COST = 20000
IMAGE_COST = 5
OTHER_COST = 20
DOC_COST = 15
GIS_COST = 25


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
    cost = (base_cost * (duration * .5)) \
        + (base_cost * (count_spec_datasets * .75)) \
        + (base_cost * (count_tables * .5)) \
        + (IMAGE_COST * ((count_images + 10) / 15)) \
        + (DOC_COST * ((count_docs + 10) / 15)) \
        + (GIS_COST * ((count_gis + 5) / 5)) \
        + (OTHER_COST * ((count_other + 10) / 5))
    if cost < base_cost:
        cost = base_cost
    if is_early_career:
        cost = cost - (cost * EARLY_CAREER_DISCOUNT)
    raw_cost = round(float(cost), 2)
    max_cost_more = cost > max_cost
    if max_cost_more:
        cost = max_cost
    return cost, raw_cost, max_cost_more


def format_currency(dollars):
    """ Provides a cost estimate in formatted dollars """
    dollars = round(float(dollars), 2)
    return "$%s%s" % (intcomma(int(dollars)), ("%0.2f" % dollars)[-3:])


def estimate_cost_json(input_json):
    if not isinstance(input_json, dict):
        return None
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
    return format_currency(cost)