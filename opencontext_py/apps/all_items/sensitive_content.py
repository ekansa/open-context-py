from django.contrib.auth.models import User, Group

from django.db.models import Q

from opencontext_py.apps.all_items import configs
from opencontext_py.apps.all_items.models import (
    AllManifest,
    AllAssertion,
    AllHistory,
    AllResource,
    AllIdentifier,
    AllSpaceTime,
)

from opencontext_py.apps.all_items.project_contexts import context

"""
import importlib
from opencontext_py.apps.all_items import sensitive_content as sc
importlib.reload(sc)
project_id = 'df043419-f23b-41da-7e4d-ee52af22f92f'
sc.fast_flag_human_remains_items_in_project(project_id)

"""

# ---------------------------------------------------------------------
# NOTE: These functions manage metadata, flagging, and permissions
# associated with sensitive content, especially human remains. 
# Data, media, and documentation of human need special flagging and
# warnings for users
# ---------------------------------------------------------------------
HUMAN_REMAINS_ITEM_CLASS_KEYS = [
    'oc-gen:cat-human-bone'
]

HUMAN_REMAINS_ITEM_CLASS_URIS = [
    'opencontext.org/vocabularies/oc-general/cat-human-bone'
]

HUMAN_REMAINS_LINKED_DATA_URIS = [
    # EOL Human
    'eol.org/pages/327955',
    # GBIF Human
    'gbif.org/species/2436436',
    # LOC 'Human remains (Archaeology)'
    'id.loc.gov/authorities/subjects/sh92003545',
    # LOC 'Human skeleton'
    'id.loc.gov/authorities/subjects/sh85062895',
    # LOC 'Burial'
    'id.loc.gov/authorities/subjects/sh85018080',
    # Add more in the future...
]


def check_man_obj_human_remains(man_obj, df_context=None):
    """Checks a manifest object for human remains
    
    :param AllManifest man_obj: An instance of the AllManifest
        model
    :param DataFrame df_context: A project's context dataframe.
    """
    if man_obj.item_class.uri in HUMAN_REMAINS_ITEM_CLASS_URIS:
        # The item has a human remains related item_class
        return True
    
    # Get all the assertions about the item.
    assert_qs = AllAssertion.objects.filter(
        subject=man_obj,
        visible=True,
    )
    type_id_list = []
    for ass in assert_qs:
        if ass.object.uri in HUMAN_REMAINS_LINKED_DATA_URIS:
            # The item has some direct human remains related metadata
            # asserted about it.
            return True
        if ass.object.item_type != 'types':
            continue
        type_id_list.append(str(ass.object.uuid))

    # Get the project context if we don't already have it.
    if df_context is None:
        df_context = context.get_item_context_df(
            type_id_list, 
            man_obj.project.uuid
        )
    if df_context is None or df_context.empty:
        # The project context is empty so won't have any
        # human remains equivalent liked data.
        return False
    
    # Check if any of the 'types' items used as the objects of 
    # assertions about the man_obj have some sort of equivalence 
    # relationship with human remains related 
    type_pred_equiv_index = (
        df_context['subject_id'].isin(type_id_list)
        & df_context['predicate_id'].isin(
            # Equivalent or sub-class of human remains related
            # linked data uris
            configs.PREDICATE_LIST_SBJ_EQUIV_OBJ
            + configs.PREDICATE_LIST_SBJ_IS_SUBORD_OF_OBJ
        )
        & df_context['object__uri'].isin(
            HUMAN_REMAINS_LINKED_DATA_URIS
        )
    )
    if not df_context[type_pred_equiv_index].empty:
        # There's an equivalence relationship between the 'types'
        # items (used as objects of assertions on the man_obj) and
        # human remains linked data.
        return True
    
    if man_obj.item_type not in ['media', 'documents']:
        # This is not a media or documents item-type, so there's
        # nothing more to check.
        return False
    
    rel_subjects = []
    for ass in assert_qs:
        if ass.object.item_type != 'subjects':
            continue
        rel_subjects.append(ass.object)
    
    rel_subjects += [
        ass.subject for ass in AllAssertion.objects.filter(
            subject__item_type='subjects',
            visible=True,
            object=man_obj
        )
    ]

    for rel_subject in rel_subjects:
        if rel_subject.meta_json.get('flag_human_remains'):
            # An associated subjects object type has human remains
            # flagging
            return True
        human_remains_obj = check_man_obj_human_remains(
            rel_subject, 
            df_context=df_context
        )
        if human_remains_obj:
            # The associated 
            return True
    # Even related / associated item_type = 'subjects' items lack
    # human remains flags.
    return False


def flag_human_remains_items_in_project(
    project_id, 
    use_cache=True, 
    reset_cache=False
):
    """Gets human remains records from a project
    
    :param str project_id: A project's UUID or string UUID primary key
        identifier
    :param bool use_cache: Boolean flag to use the cache or not
    :param bool reset_cache: Force the cache to be reset.
    """

    count_flagged = 0

    hr_class_uris = [
        AllManifest().clean_uri(uri) 
        for uri in HUMAN_REMAINS_ITEM_CLASS_URIS
    ]
    ld_uris = [
        AllManifest().clean_uri(uri) 
        for uri in HUMAN_REMAINS_LINKED_DATA_URIS
    ]

    # Get the project context, which has equivalence and other
    # linked data relations for all predicates and types used in
    # project.
    print(f'Fetching Project context for {project_id}')
    df_context = context.get_cache_project_context_df(
        str(project_id),
        use_cache=use_cache,
        reset_cache=reset_cache,
    )
    print(f'Project context has {len(df_context.index)} rows.')

    hr_equiv_ids = []
    if set(['predicate_id', 'object__uri']).issubset(set(df_context.columns)):
        hr_equiv_index = (
            df_context['predicate_id'].isin(
                # Equivalent or sub-class of human remains related
                # linked data uris
                configs.PREDICATE_LIST_SBJ_EQUIV_OBJ
                + configs.PREDICATE_LIST_SBJ_IS_SUBORD_OF_OBJ
            )
            & df_context['object__uri'].isin(
                hr_class_uris + ld_uris
            )
        )
        # Get all of the types, etc that have some sort of equivalence or 
        # sub-class relationship to linked data entities about human remains.
        hr_equiv_ids = df_context[hr_equiv_index]['subject_id'].unique().tolist()

    print(f'Project context has: {len(hr_equiv_ids)} human-remains related types.')

    hr_qs = AllManifest.objects.filter(
        project_id=project_id,
        uuid__in=AllAssertion.objects.filter(
            subject__project_id=project_id,
            visible=True,
        ).filter(
            Q(subject__item_class__uri__in=hr_class_uris)
            |Q(object__uri__in=ld_uris)
            |Q(object_id__in=hr_equiv_ids)
        ).distinct(
            'subject'
        ).order_by(
            'subject'
        ).values_list(
            'subject_id', 
            flat=True
        )
    )

    print(f'Manifest items directly needing human remains flags {hr_qs.count()}.')
    human_remains_subjs = []
    for man_obj in hr_qs:
        man_obj.meta_json['flag_human_remains'] = True
        man_obj.save()
        count_flagged += 1
        print(
            f'Added human remains flag to {man_obj.item_type}: {man_obj.label} '
            f'({man_obj.uuid}): {man_obj.uri}'
        )
        if man_obj.item_type == 'subjects':
            # This is a subjects item, so media and documents that reference it
            # should also be flagged.
            human_remains_subjs.append(man_obj)
    
    hr_rel_qs = AllManifest.objects.filter(
        project_id=project_id,
    ).filter(
        # Look up media and documents items that are objects of relationships
        # with human remains flagged items.
        Q(uuid__in=AllAssertion.objects.filter(
                object__item_type__in=['media', 'documents'],
            ).filter(
                Q(subject__in=human_remains_subjs)
                |Q(
                    subject__item_type='subjects',
                    subject__meta_json__flag_human_remains=True
                )
            ).distinct(
                'object'
            ).order_by(
                'object'
            ).values_list('object_id', flat=True)
        )
        |Q(uuid__in=AllAssertion.objects.filter(
                subject__item_type__in=['media', 'documents'],
            ).filter(
                Q(object__in=human_remains_subjs)
                |Q(
                    object__item_type='subjects',
                    object__meta_json__flag_human_remains=True
                )
            ).distinct(
                'subject'
            ).order_by(
                'subject'
            ).values_list('subject_id', flat=True)
        )
    )
    print(f'Manifest media and documents items indirectly needing human remains flags {hr_rel_qs.count()}.')
    human_remains_subjs = []
    for man_obj in hr_rel_qs:
        man_obj.meta_json['flag_human_remains'] = True
        man_obj.save()
        count_flagged += 1
        print(
            f'Added human remains flag to {man_obj.item_type}: {man_obj.label} '
            f'({man_obj.uuid}): {man_obj.uri}'
        )
    return count_flagged