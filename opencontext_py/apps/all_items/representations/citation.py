
import datetime



from opencontext_py.apps.all_items import configs
from opencontext_py.apps.all_items.models import (
    AllIdentifier,
)


# ---------------------------------------------------------------------
# NOTE: These functions bring together mainly Dublin Core assertions
# to make citation information that is simple to express in an HTML
# template
# ---------------------------------------------------------------------

def format_citation_person_dict(oc_obj_dict):
    """Formats an OC object dict into a dict suitable for citation

    :param dict oc_obj_dict: An Open Context dict representation
        of an assertion object, as formatted for HTML templating
    """
    # The combined / full name is in the meta_json, but if not,
    # we fall back to the item label.
    combined_name = oc_obj_dict.get(
        'object__meta_json',
        {}
    ).get(
        'combined_name',
        oc_obj_dict.get('label')
    )

    if not combined_name:
        # We don't have a full name in the meta_json, so
        # use the label instead.
        combined_name = oc_obj_dict.get('label')

    surname = oc_obj_dict.get(
        'object__meta_json',
        {}
    ).get(
        'surname',
    )

    given_name = oc_obj_dict.get(
        'object__meta_json',
        {}
    ).get(
        'given_name',
    )

    mid_init = oc_obj_dict.get(
        'object__meta_json',
        {}
    ).get(
        'mid_init',
    )

    if surname and given_name:
        reliable_names = True
    else:
        reliable_names = False

    all_name_parts = combined_name.split(' ')
    if not reliable_names and not surname and len(all_name_parts) > 1:
        surname = all_name_parts[-1]
    if not reliable_names and not given_name and len(all_name_parts) > 1:
        given_name = all_name_parts[0]
    if not reliable_names and not mid_init and len(all_name_parts) == 3:
        mid_init = all_name_parts[1]

    return {
        'combined_name': combined_name,
        'surname': surname,
        'given_name': given_name,
        'mid_init': mid_init,
        'reliable_names': reliable_names,
        'id': oc_obj_dict.get('id'),
        'uuid': str(oc_obj_dict.get('object_id')),
        'slug': oc_obj_dict.get('slug'),
    }


def make_citation_dict(rep_dict):
    """Makes a citation dict from an Open Context rep_dict

    :param dict rep_dict: An Open Context representation dict
        that still lacks JSON-LD
    """

    # NOTE: (TODO) Do we need to fix our citation rules? Is this
    # example, we simply de-dupe based on the "combined_name".

    part_of_list = rep_dict.get('dc-terms:isPartOf', [{}])
    current_date =  datetime.datetime.now().date()


    citation_dict = {
        'title': rep_dict.get('dc-terms:title'),
        'year_published': str(
            rep_dict.get(
                'dc-terms:issued',
                current_date.isoformat(),
            )
        )[:4],
        'date_published': rep_dict.get(
            'dc-terms:issued',
            current_date.isoformat(),
        ),
        'date_modified': rep_dict.get(
            'dc-terms:modified',
            current_date.isoformat(),
        ),
        'publisher': configs.OPEN_CONTEXT_PROJ_LABEL,
        'part_of_label': part_of_list[0].get('label'),
        'part_of_uri': part_of_list[0].get('id'),
        'id': rep_dict.get('id'),
        'ids': {
            'URL': rep_dict.get('id'),
        }
    }

    if citation_dict.get('date_published') == '2007-01-01':
        citation_dict['date_published'] = 'In prep'

    if citation_dict.get('date_published') == current_date.isoformat():
        citation_dict['date_published'] = 'In prep'

    if citation_dict.get('id') and '/projects/' in citation_dict.get('id'):
        # A project does not need to be part of Open Context.
        if citation_dict.get('part_of_label') == configs.OPEN_CONTEXT_PROJ_LABEL:
            citation_dict['part_of_label'] = None

    # Iterate through contributors and creators to add people
    # in these roles to the citation.
    role_keys = [
        ('dc-terms:contributor','contributor'),
        ('dc-terms:creator','creator'),
    ]
    for dc_pred, cite_key in role_keys:
        act_names = []
        citation_dict.setdefault(cite_key, [])
        for oc_obj_dict in rep_dict.get(dc_pred, []):
            p_dict = format_citation_person_dict(oc_obj_dict)
            if p_dict.get('combined_name') in act_names:
                continue
            act_names.append(p_dict.get('combined_name'))
            citation_dict[cite_key].append(p_dict)

    if (not citation_dict.get('contributor')
        and not citation_dict.get('creator')):
        citation_dict['creator'] = [
            {
                'label': f"{configs.OPEN_CONTEXT_PROJ_LABEL} Staff",
                'combined_name': f"{configs.OPEN_CONTEXT_PROJ_LABEL} Staff",
            },
        ]

    if not citation_dict.get('contributor'):
        citation_dict['contributor'] = citation_dict.get('creator').copy()

    citation_dict['authors'] = [
        p.get('combined_name')
        for p in citation_dict.get('contributor', [{}])
    ]
    if citation_dict.get('id') and '/projects/' in citation_dict.get('id'):
        # Don't repeat a person as an editor if they're already a project
        # author.
        citation_dict['editors'] = [
            p.get('combined_name')
            for p in citation_dict.get('creator', [{}])
            if p.get('combined_name') not in citation_dict['authors']
        ]
    else:
        citation_dict['editors'] = [
            p.get('combined_name')
            for p in citation_dict.get('creator', [{}])
        ]
    # Add persistent IDs to the citation dict.
    for scheme_key, scheme_conf in AllIdentifier.SCHEME_CONFIGS.items():
        citation_dict[scheme_key] = None
        url_part = scheme_conf.get('url_root')
        if not url_part:
            continue
        for act_id in rep_dict.get('dc-terms:identifier', []):
            if url_part in act_id:
                citation_dict[scheme_key] = act_id
                citation_dict['ids'][scheme_key.upper()] = act_id
    return citation_dict