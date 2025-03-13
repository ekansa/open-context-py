
import numpy as np
import pandas as pd


from opencontext_py.apps.all_items import configs
from opencontext_py.apps.all_items.models import (
    AllManifest,
    AllAssertion,
)

from opencontext_py.apps.all_items.editorial.item import edit_configs

# ---------------------------------------------------------------------
# NOTE: These functions provide utilities to support user interface
# functionality for making export data tables. These utilities are not
# needed for command-line invocations to make export tables.
# ---------------------------------------------------------------------

EXPORT_ITEM_TYPE_OPTIONS = [
    {'value': it.get('item_type'), 'text': f"{it.get('item_type_note')} ({it.get('item_type')})",}
    for it in edit_configs.MANIFEST_ADD_EDIT_CONFIGS[0].get('item_types', [])
]

EXPORT_ITEM_TYPE_TEXTS = {
    it.get('item_type'): f"{it.get('item_type_note')} ({it.get('item_type')})"
    for it in edit_configs.MANIFEST_ADD_EDIT_CONFIGS[0].get('item_types', [])
}

EXPORT_QUERY_ATTRIBUTE_CONFIGS = [
    ('subject__item_type__in', 'Item types', 'xsd:string', 'subject__item_type',),
    ('project_id__in', 'Projects', 'id', 'project',),
    ('project_id__label__icontains', 'Projects (label match)', 'xsd:string', None,),
    ('subject__item_class_id__in', 'Classes / categories', 'id', 'subject__item_class',),
    ('subject__item_class__label__icontains', 'Classes / categories (label match)', 'xsd:string', None,),
    ('predicate_id__in', 'Descriptive attribute and relations', 'id', 'predicate',),
    ('predicate__item_class_id__in', 'Attribute or relation types', 'id', 'predicate__item_class',),
    ('observation_id__in', 'Observation', 'id', 'observation',),
    ('subject__path__contains', 'Context path (text match)', 'xsd:string', None,),
    ('source_id__in', 'Data sources', 'xsd:string', 'source_id',),
]

HUMAN_READABLE_ATTRIBUTE_DICT = {
    k:{'label': l, 'data_type': dt,}  
    for k, l, dt, _ in EXPORT_QUERY_ATTRIBUTE_CONFIGS
}


def check_set_project_inventory(filter_args):
    """Checks filter_args to see if we're querying for a project inventory
    updates the filter arg to do so.
    """
    do_project_inventory = False
    if not isinstance(filter_args, dict):
        return filter_args, do_project_inventory    
    if len(filter_args.get('project_id__in', [])) > 0:
        return filter_args, do_project_inventory
    # We're likely doing a project inventory filter
    do_project_inventory = True
    if filter_args.get('project_id__in') == []:
        filter_args.pop('project_id__in')
    if not filter_args.get('subject__item_type__in'):
        filter_args['subject__item_type__in'] = ['projects']
    return filter_args, do_project_inventory



def make_human_readable_query_args(query_arg_dict):
    """Makes a human readable list of args from a query_arg_dict"""
    arg_list = []
    if not query_arg_dict:
        return arg_list
    for attrib_key, q_val in query_arg_dict.items():
        hr_conf = HUMAN_READABLE_ATTRIBUTE_DICT.get(attrib_key, {})
        hr_arg_dict = {
            'arg_param': attrib_key,
            'label': hr_conf.get('label', attrib_key),
        }

        # Deal with the case where the q_val is not a list
        if not isinstance(q_val, list):
            # First we assume a literal.
            hr_arg_dict['values'] = [{'value': q_val, 'text': q_val}]
            if hr_conf.get('data_type') == 'id':
                m = AllManifest.objects.filter(uuid=q_val).first()
                if m:
                    # Update to have the item label in text of the values.
                    hr_arg_dict['values'] = [{'value': str(q_val), 'text': m.label}]
            arg_list.append(hr_arg_dict)
            continue

        # At this point, q_val is a list, so default that it is a list
        # of literal values
        hr_arg_dict['values'] = [
            {'value':v, 'text':v} 
            for v in q_val
        ]

        if hr_conf.get('data_type') == 'id' and attrib_key.endswith('_id__in'):
            # OK, now we can look up a list of entities instead.
            
            mqs = AllManifest.objects.filter(
                uuid__in=q_val,
            )
            if len(mqs):
                # We have dereferenced these items.
                hr_arg_dict['values'] = [
                    {'value': str(m.uuid), 'text':m.label} 
                    for m in mqs
                ]

        arg_list.append(hr_arg_dict)
    return arg_list


def give_arg_config_and_options(qs, arg_param, arg_label, data_type, attrib_to_count, max_opt_count=20):
    """Makes a UI config and options for an export filter or exclude argument

    :param QuerySet qs: An AllAssertion queryset that may be limited by filters and
        excludes
    :param str arg_param: A potential filter or exclude argument parameter that we
        will return a config and options for
    :param str arg_label: A human readable label describing this filter/exclude 
        argument parameter.
    :param str data_type: The data type for this particular arg parameter.
    :param str attrib_to_count: The actual attribute that we will be counting
        distinct values of in the qs
    :param int max_opt_count: The maximum number of options for this param argument
        that we will return
    """
    output = {
        'arg_param': arg_param,
        'label': arg_label,
        'data_type': data_type,
        'do_text_input': (not arg_param.endswith('__in')),
        'count': None,
        'options': None,
    }

    if qs is None or attrib_to_count is None:
        if attrib_to_count == 'subject__item_type':
            # We have no queryset yet to count, so return the default
            # set of item type options.
            output['count'] = len(EXPORT_ITEM_TYPE_OPTIONS)
            output['options'] = EXPORT_ITEM_TYPE_OPTIONS
        # Skip out of the function
        return output
    
    count = qs.values(
        attrib_to_count,
    ).distinct().order_by().count()
    if count == 0 or count > max_opt_count:
        return output
    
    if attrib_to_count == 'source_id':
        value_key = attrib_to_count
        text_key = attrib_to_count
        options_qs = qs.values(
            attrib_to_count
        ).distinct().order_by()
    elif attrib_to_count == 'subject__item_type':
        value_key = attrib_to_count
        text_key = attrib_to_count
        options_qs = qs.select_related(
            'subject'
        ).values(
            attrib_to_count
        ).distinct().order_by()
    else:
        value_key = f'{attrib_to_count}_id'
        text_key = f'{attrib_to_count}__label'
        options_qs = qs.select_related(
            attrib_to_count
        ).values(
            value_key,
            text_key,
        ).distinct().order_by(
            text_key,
            value_key,
        )

    # Return a list of options in that are dicts keyed
    # by 'value' and 'text' so as to be easy to use with
    # a Bootstrap Vue front end.
    options = []
    for opt in options_qs:
        value = opt.get(value_key)
        if not value:
            # We don't want a "None" option
            continue
        if str(value) == configs.DEFAULT_CLASS_UUID:
            # We don't want a default class option
            continue
        text = opt.get(text_key)
        if attrib_to_count == 'subject__item_type':
             # Special case to look up explanatory text for item_type values
            if not EXPORT_ITEM_TYPE_TEXTS.get(text):
                # Not an item_type configured for export, so skip it.
                continue
            text = EXPORT_ITEM_TYPE_TEXTS.get(text)
        option_dict = {
            'value': str(value),
            'text': text,
        }
        options.append(option_dict)
    
    # Add the options list to the output.
    output['count'] = len(options)
    output['options'] = options
    return output
    


def make_export_config_dict(
    filter_args=None, 
    exclude_args=None,
    ui_configs=EXPORT_QUERY_ATTRIBUTE_CONFIGS,
):
    """Makes an export configuration dictionary that provides
    counts of different unique attributes

    :param dict filter_args: Arguments for filtering an
        AllAssertion model queryset.
    :param dict exclude_args: Arguments for making exclusions in
        an AllAssertion model queryset.
    :param list ui_configs: List of config tuples that give options
        and some description to filter and exclude options
    """
    qs = None
    filter_hr_list = make_human_readable_query_args(filter_args)
    exclude_hr_list = make_human_readable_query_args(exclude_args)
    if filter_args or exclude_args:
        qs = AllAssertion.objects.all()
        # Update the filter_args in case we're doing a project inventory
        filter_args, _ = check_set_project_inventory(filter_args)

        if filter_args:
            qs = qs.filter(
                **filter_args
            )
        if exclude_args:
            qs = qs.exclude(
                **exclude_args
            )
        # Always exclude containment assertions, as we
        # don't expose these for export.
        qs = qs.exclude(
            predicate_id=configs.PREDICATE_CONTAINS_UUID,
        )

    # Get the total count of subjects of exported description
    if qs is not None:
        total_count = qs.values('subject').distinct().order_by().count()
    else:
        total_count = None

    act_configs = []
    for arg_param, arg_label, data_type, attrib_to_count in ui_configs:
        act_config = give_arg_config_and_options(
            qs, 
            arg_param, 
            arg_label,
            data_type,
            attrib_to_count,
        )
        if not act_config.get('options') and not act_config.get('do_text_input'):
            # No option
            continue
        act_configs.append(act_config)
    return {
        'total_count': total_count,
        'exist_filters': filter_hr_list,
        'exist_excludes': exclude_hr_list,
        'act_configs': act_configs,
    }