



from opencontext_py.apps.all_items import configs
from opencontext_py.apps.all_items import utilities
from opencontext_py.apps.all_items.representations import citation


# ---------------------------------------------------------------------
# NOTE: These functions generate Schema.org JSON-LD metadata for an
# Open Context item
# ---------------------------------------------------------------------
CC_DEFAULT_LICENSE_CC_BY_SCHEMA_DICT  = {
    'id': configs.CC_DEFAULT_LICENSE_CC_BY_URI
}

MAINTAINER_PUBLISHER_DICT = {
    '@id': f'https://{configs.OC_URI_ROOT}',
    'url': f'https://{configs.OC_URI_ROOT}',
    '@type': 'Organization',
    'name': configs.OPEN_CONTEXT_PROJ_LABEL,
    'logo': 'https://opencontext.org/static/oc/images/nav/oc-nav-dai-inst-logo.png',
    'nonprofitStatus': 'Nonprofit501c3',
    'ethicsPolicy': 'https://opencontext.org/about/terms',
    'brand': [
        configs.OPEN_CONTEXT_PROJ_LABEL, 
        'Alexandria Archive Institute'
    ],
}


def make_schema_org_org_person_dict(oc_dict):
    """Makes a Schema.org Organization or Person dict from Open Context dict"""
    schema_dict = {
        '@id': oc_dict.get('id'),
        'identifier': oc_dict.get('id'),
        'name': oc_dict.get('label'),
    }
    if oc_dict.get('type', '').endswith('Person'):
        schema_dict['@type'] = 'Person'
    else:
        schema_dict['@type'] = 'Organization'
    return schema_dict


def get_hero_image_url(rep_dict):
    """Gets the project hero image url if it exists"""
    for key in ['oc-gen:has-files', 'oc_gen__has_files']:
        for item_dict in rep_dict.get(key, []):
            if not item_dict.get('id'):
                continue
            if item_dict.get('type') == 'oc-gen:hero':
                return item_dict.get('id')
    return None


def make_keyword_list(rep_dict):
    """Makes a list of keywords"""
    # Gather keywords from various metadata associated with this item
    keywords = []
    context_keyword = rep_dict.get('oc-gen:has-linked-contexts', [{}])[-1].get('item_class__label')
    if context_keyword:
        keywords.append(context_keyword)
    for context_item in rep_dict.get('oc-gen:has-linked-contexts', []):
        keyword = context_item.get('label')
        if not keyword:
            continue
        if keyword in keywords:
            continue
        keywords.append(keyword)
    for key in ['dc-terms:subject', 'dc-terms:coverage', 'dc-terms:temporal', 'dc-terms:spatial']:
        for item_dict in rep_dict.get(key, []):
            keyword = item_dict.get('label')
            if not keyword:
                continue
            if keyword in keywords:
                continue
            keywords.append(keyword)
    return keywords


def make_image_schema_org_json_ld(
    rep_dict,
    description,
    creators,
    citation_dict,
    citation_txt,
):
    # The about link is the most specific thing (last) in the linked contexts
    about_link = rep_dict.get('oc-gen:has-linked-contexts', [{}])[-1].get('id')

    # Gather keywords from various metadata associated with this item
    keywords = make_keyword_list(rep_dict)

    # Extract the main (full) file representation.
    full_link = rep_dict.get('media_download')
    if not full_link:
        for file_dict in rep_dict.get('oc_gen__has_files', []):
            if file_dict.get('type') != 'oc-gen:fullfile':
                continue
            full_link = file_dict.get('id')

    creator_txt = f"{', '.join(citation_dict.get('authors', []))}"
    schema = {
        '@context': 'http://schema.org/',
        '@type': 'ImageObject',
        '@id': '#schema-org',
        'name': rep_dict.get('dc-terms:title'),
        'caption': description,
        'representativeOfPage': True,
        'creator': creators,
        'datePublished': rep_dict.get('dc-terms:issued'),
        'dateModified': rep_dict.get('dc-terms:modified'),
        'license': rep_dict.get(
            'dc-terms:license', 
            [CC_DEFAULT_LICENSE_CC_BY_SCHEMA_DICT]
        )[0].get('id'),
        'isAccessibleForFree': True,
        'maintainer': MAINTAINER_PUBLISHER_DICT.copy(),
        'publisher': MAINTAINER_PUBLISHER_DICT.copy(),
        'isPartOf': citation_dict.get('part_of_uri'),
        'creditText': citation_txt,
        'acquireLicensePage': f'https://{configs.OC_URI_ROOT}/about/terms',
        'copyrightNotice': f'Copyright owned by the creator(s)/contributors(s): {creator_txt}',
    }
    if about_link:
        schema['about'] = about_link
    if full_link:
        schema['contentUrl'] = full_link
    if keywords:
        schema['keywords'] = keywords
    return schema


def make_schema_org_json_ld(rep_dict):
    """Makes Schema.org JSON-LD from an Open Context rep_dict
    
    :param dict rep_dict: An Open Context representation dict
        that still lacks JSON-LD
    """
    item_type = utilities.get_oc_item_type_from_uri(rep_dict.get('id'))
    if not item_type:
        return None

    identifiers = [rep_dict.get('id')]
    identifiers += [s_dict.get('id') for s_dict in rep_dict.get('owl:sameAs', [])]

    creators = [
        make_schema_org_org_person_dict(p) 
        for p in rep_dict.get('dc-terms:creator', rep_dict.get('dc-terms:contributor', []))
    ]
    if not len(creators):
        creators = MAINTAINER_PUBLISHER_DICT.copy()

    citation_dict = citation.make_citation_dict(rep_dict)

    citation_txt = (
        f"{', '.join(citation_dict.get('authors', []))} "
        f"({citation_dict.get('date_published','')[:4]}) "
        f"\"{citation_dict.get('title','')}\" "
        f"In \"{citation_dict.get('part_of_label','')}\". "
        f"{', '.join(citation_dict.get('editors', []))} (Eds.) . "
        f"Released {citation_dict.get('date_published','')}. "
        f"{configs.OPEN_CONTEXT_PROJ_LABEL}. "
    )
    for scheme_key, id_val in citation_dict.get('ids', {}).items():
        citation_txt += f" {scheme_key}: {id_val}"

    # Add a description about the object.
    description = (
        f'An Open Context "{item_type}" dataset item. '
    )
    item_class_label = rep_dict.get('item_class__label', 'Default')
    item_class_des = 'This record'
    if 'Default' not in item_class_label:
        item_class_des = f'This "{item_class_label}" record'

    if item_type not in ['projects', 'tables']:
        description += (
            'Open Context publishes structured data as granular, URL '
            f'identified Web resources. {item_class_des} is part of the '
            f'"{citation_dict.get("part_of_label", "")}" data publication.'
        )

    for des_dict in rep_dict.get('dc-terms:description', [])[:1]:
        des_txt = des_dict.get('@en')
        if des_txt:
            description += f' Described with: "{des_txt}".'

    if rep_dict.get('item_class__slug') == 'oc-gen-image':
        return make_image_schema_org_json_ld(
            rep_dict=rep_dict,
            description=description,
            creators=creators,
            citation_dict=citation_dict,
            citation_txt=citation_txt,
        )
    
    authors = None
    keywords = None
    hero_image = None
    schema_type = 'Dataset'
    if item_type == 'projects':
        keywords = make_keyword_list(rep_dict)
        schema_type = [
            'Dataset',
            'ScholarlyArticle',
        ]
        authors = creators
        hero_image = get_hero_image_url(rep_dict)

    schema = {
        '@context': 'http://schema.org/',
        '@type':  schema_type,
        '@id': '#schema-org',
        'name': rep_dict.get('dc-terms:title'),
        'description': description,
        'creator': creators,
        'datePublished': rep_dict.get('dc-terms:issued'),
        'dateModified': rep_dict.get('dc-terms:modified'),
        'license': rep_dict.get(
            'dc-terms:license', 
            [CC_DEFAULT_LICENSE_CC_BY_SCHEMA_DICT]
        )[0].get('id'),
        'isAccessibleForFree': True,
        'maintainer': MAINTAINER_PUBLISHER_DICT.copy(),
        'publisher': MAINTAINER_PUBLISHER_DICT.copy(),
        'identifier': identifiers,
        'isPartOf': citation_dict.get('part_of_uri'),
        'citation': citation_txt,
    }
    if keywords:
        schema['keywords'] = keywords
    if authors:
        schema['author'] = authors
    if hero_image:
        schema['image'] = hero_image
    return schema