import datetime
from opencontext_py.libs.rootpath import RootPath

from opencontext_py.apps.all_items import configs
from opencontext_py.apps.all_items.editorial import api as editorial_api

from opencontext_py.apps.all_items.models import (
    AllIdentifier,
)

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
    'CSV',
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

TOS_STATEMENT = (
    '<p><strong>Terms of Use, Intellectual Property, and Ethics</strong></p>'
    '<p>Open Context publishes research materials important to many different communities '
    'all with different histories, cultures, and expectations. We expect uses of these data to '
    'respect civil, legal, and ethical standards. To learn more about these expectations, '
    'please review:</p>'
    '<ul>'
    '<li><a href="https://opencontext.org/about/intellectual-property">Intellectual Property Policies</a></li>'
    '<li><a href="https://opencontext.org/about/terms">Terms of Use</a></li>'
    '<li><a href="https://opencontext.org/about/fair-care">Data Governance Principles</a></li>'
    '</ul>'
)

ZENODO_DOI_DATACITE_PREFIX = '10.5281'


def make_zenodo_doi_url(deposition_id):
    """ makes a Zenodo DOI URL from a deposition ID """
    return f'https://doi.org/{ZENODO_DOI_DATACITE_PREFIX}/zenodo.{deposition_id}'


def make_zenodo_license_abrev_from_uri(lic_uri):
    """ zenodo wants an abbreviated license, not a full URI
        this is annoying, but it is what it wants
    """
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


def make_zenodo_license_abrev(meta_dict):
    """ zenodo wants an abbreviated license, not a full URI
        this is annoying, but it is what it wants
    """
    for lic_obj in meta_dict.get('dc-terms:license', []):
        if not lic_obj.get('id'):
            continue
        lic_uri = lic_obj['id']
        zen_license = make_zenodo_license_abrev_from_uri(lic_uri)
        if zen_license:
            return zen_license
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


def make_zenodo_persistent_id_relation_list(proj_dict, proj_rels):
    """Extracts persistent identifiers from a project and makes a list of
    related identifiers that conform to the Zenodo model.
    """
    zenodo_pid_list = []
    dc_ids = proj_dict.get('dc-terms:identifier', [])
    if not dc_ids:
        return zenodo_list
    for dc_id in dc_ids:
        id, scheme = AllIdentifier().normalize_validate_id_in_scheme(
            dc_id
        )
        if scheme == 'ark':
            id = f'ark:/{id}'
        for proj_rel in proj_rels:
            zenodo_obj = {
                'relation': proj_rel,
                'identifier': id,
                'type': scheme.upper(),
                'scheme': scheme.upper(),
            }
            zenodo_pid_list.append(zenodo_obj)
    return zenodo_pid_list


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
        if obj_dict.get('id', '').endswith(configs.OPEN_CONTEXT_PROJ_UUID):
            # Don't make a relation to the parent project
            continue
        zenodo_obj = {}
        zenodo_obj['relation'] = 'isPartOf'
        zenodo_obj['identifier'] = obj_dict['id']
        zenodo_list.append(zenodo_obj)
    # Now make relations for the persistent identifiers
    # that may be associated with this project
    zenodo_pid_list = make_zenodo_persistent_id_relation_list(
        proj_dict,
        proj_rels
    )
    zenodo_list += zenodo_pid_list
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
            all_order = list_order + (max_count - obj_count )
            obj_w_order = (obj_dict, all_order,)
            objs_w_order.append(obj_w_order)
    ordered_objs = sorted(objs_w_order, key=lambda x: x[1])
    for obj_w_order in ordered_objs:
        obj_dict = obj_w_order[0]
        obj_dict = add_person_names_to_obj(obj_dict)
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
    meta['license'] = make_zenodo_license_abrev_from_uri(dir_dict.get('dc-terms:license', ''))
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
    zip_comment = ''
    zip_name = dir_dict.get('files_in_zip_archive')
    if zip_name:
        zip_comment = (
            f'Because this project includes a large number of files, '
            f'they are archived here in a ZIP file "{zip_name}".'
        )
    meta['description'] = (
        '<p>This archives media files associated with the <em>'
        '<a href="' + proj_dict['id'] + '">' + proj_dict['label'] + '</a></em> project published by '
        '<a href="' + rp.cannonical_host + '">Open Context</a>.</p>'
        '<p>The included JSON file "' + dir_content_file_json + '" describes links between the various files '
        'in this archival deposit and their associated Open Context media resources (identified by URI). '
        'These linked Open Context media resource items provide additional context and descriptive metadata '
        'for the files archived here. ' + zip_comment + '</p>'
        '<br/>'
        '<p><strong>Brief Description of this Project</strong>'
        '<br/>' + project_des + '</p>'
        + TOS_STATEMENT
    )

    return meta


def make_zenodo_structured_data_deposition_title(
    project_dc_title
):
    """Makes a title for a Zenodo deposition of structured data files"""
    return f'{project_dc_title} [Structured Data from Open Context]'


def make_zenodo_proj_stuctured_data_files_metadata(
    proj_dict,
    proj_upload_type = 'publication',
):
    """ makes a zendo metadata object for a deposition
        of structured data files from an Open Context project
    """
    if not isinstance(proj_dict, dict):
        return None
    rp = RootPath()
    meta = {}
    meta['title'] = make_zenodo_structured_data_deposition_title(
        proj_dict.get('dc-terms:title', proj_dict.get('label', ''))
    )
    if 'dc-terms:modified' in proj_dict:
        # date of last modification
        meta['publication_date'] = proj_dict['dc-terms:modified']
    else:
        # default to today
        today = datetime.date.today()
        meta['publication_date'] = today.isoformat()
    meta['license'] = make_zenodo_license_abrev_from_uri(
        proj_dict.get('dc-terms:license', [{}])[0].get('id')
    )
    meta['upload_type'] = proj_upload_type
    meta['creators'] = make_zenodo_creator_list(proj_dict)
    meta['keywords'] = PROJECT_KEYWORDS
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
        '<p>This deposit archives structured-data files associated with the <em>'
        '<a href="' + proj_dict['id'] + '">' + proj_dict['label'] + '</a></em> project published by '
        '<a href="' + rp.cannonical_host + '">Open Context</a>.</p>'
        '<br/>'
        '<p><strong>Brief Description of this Project</strong>'
        '<br/>' + project_des + '</p>'
        '<br/>'
        '<p><strong>Deposition Data File Overview</strong></p>'
        '<p>This archival deposit provides the same information in two formats: </p>'
        '<ol>'
        '<li><strong>CSV</strong>: The ZIP compressed <code>csv_files.zip</code> contains '
        'records related to this project exported from Open Context\'s Postgres relational database. '
        'The records in this CSV files will include records from other projects that are dependencies of this project. '
        '</li>'
        '<li><strong>JSON</strong>: The ZIP compressed <code>json_files.zip</code> contains '
        'records related to this project expressed as JSON-LD. This is a more verbose and semantically expressive format than '
        'the CSV exports. Geo-spatial information is expressed in the GeoJSON format. The JSON-LD files included here are the same '
        'as those that are publicly available via the Open Context API. '
        '</li>'
        '</ol>'
        '<p>Open Context is an open-source Python application built with the Django framework (see '
        '<a href="https://github.com/ekansa/open-context-py" >source code</a> '
        'and <a href="https://github.com/opencontext/oc-docker">Docker deployment code</a>). '
        'To manage a wide variety of archaeological and related data, Open Context organizes information '
        'using a very abstract, graph-based schema. Open Context implements this schema using a Postgres '
        'relational database and the Django "Object Relational Model" (ORM). '
        'The CSV files here provide records relevant to this project and its dependencies '
        'exported from tables in this database.</p>'
        '<p>The CSV expression of this project\'s information is very terse. '
        'To promote interoperability and understanding, The JSON-LD files provide the same information in a more '
        'semantically expressive format. '
        'A considerable amount of application logic '
        'in Open Context generates this more expressive representation of these data. The JSON-LD files included here '
        'result from these "terse" data records (from the Postgres database tables) processed with this application logic. '
        '</p>'
        '<p>The data contained in this project mainly came from one or more tabular data sources provided by '
        'the project contributors and data creators. Open Context editors imported these tabular data sources '
        'via an ETL (Extract, Transform, Load) process after review and editing using '
        '<a href="https://openrefine.org/">Open Refine</a>. '
        'Some data records may have been manually entered or modified within the Open Context database. '
        'The column <code>source_id</code> will indicate the original provenance of the data. Open Context editors work with '
        'contributors to review ETL outcomes, add data documentation, verify attribution and '
        'licensing information, and make other revisions. Because editorial processes may involve data '
        'sensitivity concerns, the history of changes and revisions made prior to publication are <em>not</em> '
        'publicly recorded. </p>'
        + TOS_STATEMENT
    )

    return meta



def make_zenodo_table_stuctured_data_files_metadata(
    rep_dict,
    upload_type = 'publication',
):
    """ makes a zendo metadata object for a deposition
        of structured data files from an Open Context project
    """
    if not isinstance(rep_dict, dict):
        return None
    rp = RootPath()
    meta = {}
    meta['title'] = make_zenodo_structured_data_deposition_title(
        rep_dict.get('dc-terms:title', rep_dict.get('label', ''))
    )
    if 'dc-terms:modified' in rep_dict:
        # date of last modification
        meta['publication_date'] = rep_dict['dc-terms:modified']
    else:
        # default to today
        today = datetime.date.today()
        meta['publication_date'] = today.isoformat()
    meta['license'] = make_zenodo_license_abrev_from_uri(
        rep_dict.get('dc-terms:license', [{}])[0].get('id')
    )
    meta['upload_type'] = upload_type
    meta['creators'] = make_zenodo_creator_list(rep_dict)
    meta['keywords'] = PROJECT_KEYWORDS
    meta['subjects'] = make_zenodo_subjects_list(rep_dict)
    meta['related_identifiers'] = make_zenodo_related_list(rep_dict)
    description = ''
    des_sep = ''
    for desc_obj in rep_dict.get('dc-terms:description', []):
        for _, val in desc_obj.items():
            description +=  des_sep + val
            des_sep = ' '
    if len(description) > 2:
        description = (
            '<p><strong>Brief Description of this Project</strong></p>'
            '<p>' + description + '</p>'
            '<br/>'
        )
    meta['communities'] = [{'identifier': com_id,} for com_id in COMMUNITY_IDS]
    meta['description'] = (
        '<p>This deposit archives structured-data files associated with <em>'
        '<a href="' + rep_dict['id'] + '">' + rep_dict['label'] + '</a></em>, a Data Table resource published by '
        '<a href="' + rp.cannonical_host + '">Open Context</a>.</p>'
        '<p>In general, Open Context is a dynamic and frequently updated database that integrates '
        'research data from a growing number of sources. However, Open Context also stores some static '
        'and unchanging, externally stored "Data Table" files. Unless otherwise indicated, the content of '
        'Data Table files (such as the resource deposited here) will not change even after updates to '
        'the Open Context database.'
        '<br/>' + description + '<br/>'
        '<p><strong>Deposition File Overview</strong></p>'
        '<p>This archival deposit includes two files, in two formats: </p>'
        '<ol>'
        '<li><strong>CSV</strong>: The <code>' + rep_dict['slug'] + '.csv</code> contains '
        'the tabular data content for this resource in a CSV format. '
        '</li>'
        '<li><strong>JSON</strong>: The <code>' + rep_dict['slug'] + '.json</code> provides '
        'additional metadata about the tabular data content for this resource in a JSON-LD format. '
        '</li>'
        '</ol>'
        '<p>Open Context is an open-source Python application built with the Django framework (see '
        '<a href="https://github.com/ekansa/open-context-py" >source code</a> '
        'and <a href="https://github.com/opencontext/oc-docker">Docker deployment code</a>). '
        'To manage a wide variety of archaeological and related data, Open Context organizes information '
        'using a very abstract, graph-based schema. Open Context implements this schema using a Postgres '
        'relational database and the Django "Object Relational Model" (ORM). </p>'
        '<p>Because Open Context internally maintains data using a very abstract schema, data dumps directly from '
        'this schema would be difficult to understand and use. Therefore, Open Context makes select datasets (like this) '
        'available in more easily understood tabular expressions. A considerable amount of application logic '
        'in Open Context generated the more expressive tabular representation of data. This tabular data '
        'output from Open Context is meant to be considered as a static and unchanging "snapshot" of data selected '
        'for output at a specific time. </p>'
        + TOS_STATEMENT
    )

    return meta