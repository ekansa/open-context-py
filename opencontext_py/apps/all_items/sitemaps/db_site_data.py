import datetime
from calendar import c
import copy
import hashlib
import logging

from django.conf import settings

from django.core.cache import caches

from opencontext_py.libs.queue_utilities import (
    wrap_func_for_rq,
)

from django.db.models import Q, Count, OuterRef, Subquery
from django.db.models.functions import Length


from opencontext_py.libs.rootpath import RootPath
from opencontext_py.apps.all_items import configs
from opencontext_py.apps.all_items.models import (
    AllManifest,
    AllAssertion,
    AllResource,
)



BIG_FILE_SAMPLE_SIZE = 100
VERBOSE_TEXT_SAMPLE_SIZE = 15


logger = logging.getLogger("site-map-items")


def db_get_proj_items_unique_by_descriptors(proj_obj):
    """Gets a unique representative sample of items from a project that
    have the full range of descriptive attributes, and associated types
    and persons

    :param AllManifest proj_obj: An AllManifest instance of the project
        for which we want a representative set of

    returns set(AllManifest objects) where the set includes a representative
        associated with each unique predicate, type (controlled vocab concept),
        person.
    """

    # This sub-query returns the number of media resources associated with
    # each subject. It is useful to promote the best image described items
    # that represent each kind of descriptor.
    media_count_qs = AllAssertion.objects.filter(
        subject=OuterRef('subject'),
        object__item_type='media',
        visible=True,
    ).exclude(
        subject__meta_json__has_key='flag_do_not_index',
    ).exclude(
        subject__meta_json__has_key='view_group_id',
    ).annotate(
        media_count=Count('object')
    ).values('media_count')[:1]

    pred_qs = AllAssertion.objects.filter(
        subject__project=proj_obj,
        subject__item_type__in=configs.OC_ITEM_TYPES,
        visible=True,
    ).exclude(
        subject__meta_json__has_key='flag_do_not_index',
    ).exclude(
        subject__meta_json__has_key='view_group_id',
    ).annotate(
        media_count=Subquery(media_count_qs)
    ).select_related(
        'subject'
    ).distinct(
        'predicate',
        'media_count',
    ).order_by(
        '-media_count',
        'predicate',
    )
    unique_by_preds = {act_ass.subject for act_ass in pred_qs}
    # Now items that represent associations with each types and persons item_type
    person_type_qs = AllAssertion.objects.filter(
        subject__project=proj_obj,
        subject__item_type__in=configs.OC_ITEM_TYPES,
        object__item_type__in=['types', 'persons'],
        visible=True,
    ).exclude(
        subject__meta_json__has_key='flag_do_not_index',
    ).exclude(
        subject__meta_json__has_key='view_group_id',
    ).annotate(
        media_count=Subquery(media_count_qs)
    ).select_related(
        'subject'
    ).distinct(
        'object',
        'media_count',
    ).order_by(
        '-media_count',
        'object',
        'subject',
    )
    unique_by_t_p = {act_ass.subject for act_ass in person_type_qs}
    rep_man_objs = unique_by_preds.union(
        unique_by_t_p
    )
    return rep_man_objs


def db_get_proj_items_biggest_files(proj_obj):
    """Gets a unique sample of items associated with a project that have
    the largest file sizes for different media types

    :param AllManifest proj_obj: An AllManifest instance of the project
        for which we want a representative set of

    returns set(AllManifest objects) that have the biggest file sizes for
        different media types
    """
    # Now items that represent each mediatype
    media_type_qs = AllResource.objects.filter(
        item__project=proj_obj,
        resourcetype_id__in=configs.OC_RESOURCE_TYPES_MAIN_UUIDS,
    ).exclude(
        item__meta_json__has_key='flag_do_not_index',
    ).exclude(
        item__meta_json__has_key='view_group_id',
    ).select_related(
        'item'
    ).distinct(
        'mediatype',
    ).order_by(
        'mediatype',
        '-filesize',
    )
    # Now get items with the biggest filesizes associated with each media type
    # in the dataset.
    big_media = set()
    for act_res in media_type_qs:
        big_qs = AllResource.objects.filter(
            item__project=proj_obj,
            resourcetype_id__in=configs.OC_RESOURCE_TYPES_MAIN_UUIDS,
            mediatype=act_res.mediatype,
        ).exclude(
            item__meta_json__has_key='flag_do_not_index',
        ).exclude(
            item__meta_json__has_key='view_group_id',
        ).select_related(
            'item'
        ).order_by(
            '-filesize',
        )[:BIG_FILE_SAMPLE_SIZE]
        act_set = {act_res.item for act_res in big_qs}
        big_media.update(act_set)
    return big_media


def db_get_proj_items_verbose_text(proj_obj):
    """Gets a unique sample of items associated with a project by distinct
    item_type and item_class that have the most verbose text associated

    :param AllManifest proj_obj: An AllManifest instance of the project
        for which we want a representative set of

    returns set(AllManifest objects) that have the biggest file sizes for
        different media types
    """
    # Now get a representative list of each distinct item_type and item_class
    m_qs = AllManifest.objects.filter(
        project=proj_obj,
        item_type__in=configs.OC_ITEM_TYPES,
    ).exclude(
        meta_json__has_key='flag_do_not_index',
    ).exclude(
        meta_json__has_key='view_group_id',
    ).distinct(
        'item_type',
        'item_class'
    ).order_by(
        'item_type',
        'item_class'
    )
    item_type_class = {man_obj for man_obj in m_qs}
    # Now get the most verbosely described items.
    wordy_items = set()
    for man_obj in m_qs:
        wordy_qs = AllAssertion.objects.filter(
            subject__project=proj_obj,
            subject__item_type=man_obj.item_type,
            subject__item_class=man_obj.item_class,
            predicate__data_type='xsd:string',
            visible=True,
        ).exclude(
            subject__meta_json__has_key='flag_do_not_index',
        ).exclude(
            subject__meta_json__has_key='view_group_id',
        ).annotate(
            text_len=Length('obj_string')
        ).distinct(
            'text_len',
            'subject'
        ).order_by(
            '-text_len',
            'subject',
        )[:VERBOSE_TEXT_SAMPLE_SIZE]
        act_set = {act_ass.subject for act_ass in wordy_qs}
        wordy_items.update(act_set)
    # Combine the two sets
    rep_man_objs = item_type_class.union(
        wordy_items
    )
    return rep_man_objs


def db_get_project_representative_sample(proj_obj):
    """Gets a unique representative sample of resources from a project

    :param AllManifest proj_obj: An AllManifest instance of the project
        for which we want a representative set of

    returns set(AllManifest objects) where the set includes a representative
        associated with each unique predicate, type (controlled vocab concept),
        person, item_type, and item_class in the project. This sampling method
        should ensure that search engines have links to a good representation
        of the full diversity of content within a project.
    """
    # NOTE: This seems to work well to greatly reduce the number of links
    # we need to include in a sitemap. For Poggio Civitate, we can make a
    # representative sample of Web resources from only 2% of the total
    # number of records (because so much data is pretty repetitive)
    proj_count = AllManifest.objects.filter(project=proj_obj).count()
    print_prefix = f'{proj_obj.label} ({str(proj_obj.uuid)}) [Total: {proj_count}]'

    unique_by_des = db_get_proj_items_unique_by_descriptors(proj_obj)
    print(f'{print_prefix}; items for distinct descriptors: {len(unique_by_des)}')

    big_files = db_get_proj_items_biggest_files(proj_obj)
    print(f'{print_prefix}; items representing large media: {len(big_files)}')

    wordy_items = db_get_proj_items_verbose_text(proj_obj)
    print(f'{print_prefix}; wordy items for each distinct item_type, item_class: {len(wordy_items)}')

    rep_man_objs = unique_by_des.union(
        big_files
    ).union(
        wordy_items
    )
    rep_len = len(rep_man_objs)
    print(f'{print_prefix}; all representative items: {rep_len}, or {round(((rep_len/proj_count) * 100), 2)} %')
    return rep_man_objs