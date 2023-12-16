import datetime
from opencontext_py.libs.rootpath import RootPath

from opencontext_py.apps.all_items.editorial import api as editorial_api

PROJECT_BINARY_KEYWORDS = [
    'Open Context',
    'Data Publication',
    'Media Files',
]

PROJECT_KEYWORDS = [
    'Open Context',
    'Data Publication',
    'Structured Data',
    'GeoJSON',
    'JSON-LD',
]

COMMUNITY_IDS = [
    'opencontext',
    'archaeology',
]

DEFAULT_SUBJECTS = [
    {
        'term': 'Archaeology',
        'identifier': 'http://id.loc.gov/authorities/subjects/sh85006507',
    },
]


def make_zenodo_license_abrev(meta_dict):
    """ zenodo wants an abbreviated license, not a full URI
        this is annoying, but it is what it wants
    """
    for lic_obj in meta_dict.get('dc-terms:license', []):
        if not lic_obj.get('id'):
            continue
        lic_uri = lic_obj['id']
        if 'publicdomain' in lic_uri:
            return 'cc-zero'
        if 'licenses/' in lic_uri:
            lic_ex = lic_uri.split('licenses/')
            lic_part = lic_ex[-1]
            if '/' in lic_part:
                lic_part_ex = lic_part.split('/')
                return 'cc-' + lic_part_ex[0]
            else:
                return 'cc-' + lic_part
    return None


def make_zenodo_subjects_list(proj_dict):
    """ makes a list of subjects that conform to the Zenodo model """
    id_list = []
    zenodo_list = []
    for zenodo_obj in DEFAULT_SUBJECTS:
        if zenodo_obj['identifier'] in id_list:
            continue
        id_list.append(zenodo_obj['identifier'])
        zenodo_list.append(zenodo_obj)
    sub_preds = [
        'dc-terms:subject',
        'dc-terms:spatial',
        'dc-terms:temporal',
        'dc-terms:coverage',
    ]
    for sub_pred in sub_preds:
        if not isinstance(proj_dict.get(sub_pred), list):
            continue
        for obj_dict in proj_dict[sub_pred]:
            if obj_dict.get('id') is None or obj_dict.get('id') in id_list:
                continue
            id_list.append(obj_dict['id'])
            zenodo_obj = {}
            zenodo_obj['term'] = obj_dict['label']
            zenodo_obj['identifier'] = obj_dict['id']
            zenodo_list.append(zenodo_obj)
    return zenodo_list


def make_zendo_keywords_for_media_files(dir_dict):
    """ makes a list of keywords based on categories from the dir_dict """
    zenodo_list = []
    for obj_dict in dir_dict.get('category', []):
        identifier = obj_dict.get('id')
        if not identifier:
            continue
        man_obj = editorial_api.get_man_obj_by_any_id(identifier)
        if not man_obj or man_obj.label in zenodo_list:
            continue
        zenodo_list.append(man_obj.label)
    return zenodo_list


def make_zenodo_related_list(proj_dict):
    """ makes a list of related identifiers that
        conform to the Zenodo model.

        These related identifiers describe how a
        deposition relates to Open Context
        and an Open Context project
    """
    rp = RootPath()
    zenodo_list = []
    # make relation to Open Context, the compiler of the deposition
    zenodo_obj = {}
    zenodo_obj['relation'] = 'isCompiledBy'
    zenodo_obj['identifier'] =  rp.cannonical_host
    zenodo_list.append(zenodo_obj)
    # make relation to the Open Context, project
    # this deposition will be part of the project
    # and it will compile the project
    proj_rels = [
        'isPartOf',
        'compiles'
    ]
    for proj_rel in proj_rels:
        zenodo_obj = {}
        zenodo_obj['relation'] = proj_rel
        zenodo_obj['identifier'] =  proj_dict['id']
        zenodo_list.append(zenodo_obj)
        for obj_dict in proj_dict.get('owl:sameAs', []):
            zenodo_obj = {}
            zenodo_obj['relation'] = proj_rel
            zenodo_obj['identifier'] =  obj_dict['id']
            zenodo_list.append(zenodo_obj)
    # make relation to a parent Open Context project, if it applicable
    for obj_dict in proj_dict.get('dc-terms:isPartOf', []):
        zenodo_obj = {}
        zenodo_obj['relation'] = 'isPartOf'
        zenodo_obj['identifier'] = obj_dict['id']
        zenodo_list.append(zenodo_obj)
    return zenodo_list


def add_person_names_to_obj(obj_dict, default_to_label=True):
    """ adds person names to a JSON-LD object dict """
    obj_dict['family_given_name'] = None
    if default_to_label and isinstance(obj_dict.get('label'), str):
        obj_dict['family_given_name'] = obj_dict['label']
        return obj_dict
    identifier = obj_dict.get('id', obj_dict.get('@id'))
    if not identifier:
        return obj_dict
    man_obj = editorial_api.get_man_obj_by_any_id(identifier)
    if not man_obj:
        return obj_dict
    obj_dict['family_given_name'] = man_obj.label
    surname = man_obj.meta_json.get('surname', '').strip()
    given_name = man_obj.meta_json.get('given_name', '').strip()
    mid_init = man_obj.meta_json.get('mid_init', '').strip()
    if len(surname) > 0 and len(given_name) > 0:
        obj_dict['family_given_name'] = surname + ', ' + given_name
        if len(mid_init) > 0:
            obj_dict['family_given_name'] += ' ' + mid_init
    return obj_dict


def make_zenodo_creator_list(meta_dict):
    """ makes a list of creators that conform to the Zenodo model """
    zenodo_list = []
    objs_w_order = []
    cite_preds = [
        'dc-terms:contributor',
        'dc-terms:creator',
    ]
    all_order = 0
    list_order = 0
    max_count = 1
    for cite_pred in cite_preds:
        for obj_dict in meta_dict.get(cite_pred, []):
            obj_count = obj_dict.get('count', 1)
            if obj_count > max_count:
                max_count = obj_count
    pred_adder = 0
    for cite_pred in cite_preds:
        pred_adder += 1
        for obj_dict in meta_dict.get(cite_pred, []):
            identifier = obj_dict.get('id', obj_dict.get('@id'))
            if not identifier:
                continue
            obj_count = obj_dict.get('count', 1)
            all_order = list_order + (max_count - obj_dict['count'])
            obj_w_order = (obj_dict, all_order,)
            objs_w_order.append(obj_w_order)
    ordered_objs = sorted(objs_w_order, key=lambda x: x[1])
    for obj_w_order in ordered_objs:
        obj_dict = obj_w_order[0]
        obj_dict = self.add_person_names_to_obj(obj_dict)
        zenodo_obj = {}
        zenodo_obj['name'] = obj_dict['family_given_name']
        orcid_url = obj_dict.get('dc-terms:identifier', '')
        if 'orcid.org' in orcid_url:
            id_ex = orcid_url.split('/')
            zenodo_obj['orcid'] = id_ex[-1]
        zenodo_list.append(zenodo_obj)
    return zenodo_list


def make_zenodo_proj_media_files_metadata(
    proj_dict,
    dir_dict,
    dir_content_file_json,
    proj_upload_type = 'publication',
    proj_pub_type = 'other',
    proj_binary_upload_type = 'publication',
    proj_binary_pub_type = 'other',
    access_right = 'open',
):
    """ makes a zendo metadata object for a deposition
        of media files from an Open Context project
    """
    if not isinstance(proj_dict, dict) or not isinstance(dir_dict, dict):
        return None

    rp = RootPath()
    meta = {}
    meta['title'] = (
        proj_dict['dc-terms:title'] + ' '
        '[Aggregated Media Files (' +  str( dir_dict['partition-number'] ) + ') from Open Context]'
    )
    if 'dc-terms:modified' in proj_dict:
        # date of last modification
        meta['publication_date'] = proj_dict['dc-terms:modified']
    else:
        # default to today
        today = datetime.date.today()
        meta['publication_date'] = today.isoformat()
    meta['license'] = make_zenodo_license_abrev(dir_dict)
    meta['upload_type'] = proj_upload_type
    if meta['upload_type'] == 'publication':
        meta['publication_type'] = proj_binary_pub_type
    meta['creators'] = make_zenodo_creator_list(dir_dict)
    meta['keywords'] = (
        PROJECT_BINARY_KEYWORDS
        + make_zendo_keywords_for_media_files(dir_dict)
    )
    meta['subjects'] = make_zenodo_subjects_list(proj_dict)
    meta['related_identifiers'] = make_zenodo_related_list(proj_dict)
    project_des = ''
    proj_des_sep = ''
    for desc_obj in proj_dict.get('dc-terms:description', []):
        for _, val in desc_obj.items():
            project_des += proj_des_sep + val
            proj_des_sep = ' '
    if not project_des:
        project_des = '[No additional description provided]'
    meta['communities'] = [{'identifier': com_id,} for com_id in COMMUNITY_IDS]
    meta['description'] = (
        '<p>This archives media files associated with the <em>'
        '<a href="' + proj_dict['id'] + '">' + proj_dict['label'] + '</a></em> project published by '
        '<a href="' + rp.cannonical_host + '">Open Context</a>.</p>'
        '<p>The included JSON file "' + dir_content_file_json + '" describes links between the various files '
        'in this archival deposit and their associated Open Context media resources (identified by URI). '
        'These linked Open Context media resource items provide additional context and descriptive metadata '
        'for the files archived here.</p>'
        '<br/>'
        '<p><strong>Brief Description of this Project</strong>'
        '<br/>' + project_des + '</p>'
    )
    return meta
