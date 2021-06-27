
import copy
import hashlib
import uuid as GenUUID

from django.conf import settings
from django.core.cache import caches
from django.db.models import OuterRef, Subquery
from django.utils.http import urlquote, quote_plus, urlquote_plus

from opencontext_py.libs.filemath import FileMath
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.libs.rootpath import RootPath

from opencontext_py.apps.all_items import configs
from opencontext_py.apps.all_items.models import (
    AllManifest,
    AllAssertion,
    AllHistory,
    AllResource,
    AllIdentifier,
    AllSpaceTime,
)
from opencontext_py.apps.all_items import utilities
from opencontext_py.apps.all_items.representations import item
from opencontext_py.apps.all_items.representations import rep_utils

from opencontext_py.apps.all_items.legacy_all import update_old_id



KEY_FIND_REPLACES = [
    ('-', '_',),
    (':', '__',),
    ('#', '',),
    (' ', '_',),
    ('/', '_',),
]

# The key for Geo-overlays in a JSON-LD rep_dict
GEO_OVERLAYS_JSON_LD_KEY = 'oc-pred:oc-gen-has-geo-overlay'
TEMPLATE_GEO_OVERLAY_KEY = 'geo_overlays'
GEO_OVERLAY_OPACITY_DEFAULT = 0.9

SPECIAL_KEYS = [
    'id',
    'uuid',
    'slug',
    'label',
    'category',
    'item_class__label',
    'type',
    'features',
    'oc-gen:has-obs',
    'oc-gen:has-contexts',
    'oc-gen:has-linked-contexts',
    'oc-gen:has-files',
    'dc-terms:abstract',
    'dc-terms:description',
    'schema:text',
    'bibo:content',
    'dc-terms:title',
    'dc-terms:issued',
    'dc-terms:modified',
    'dc-terms:license',
    'dc-terms:isPartOf',
    'dc-terms:hasPart',
    'contexts',
    'for_solr_assert_objs', # used to pass assertion objects to solr
    GEO_OVERLAYS_JSON_LD_KEY,
]

ITEM_METADATA_OBS_ID = '#item-metadata'
ITEM_METADATA_OBS_LABEL = 'Item Metadata'

DEFAULT_ITEM_TYPE_ICONS = {
    'documents': '../../static/oc/icons-v2/noun-document-3183378.svg',
    'persons': '../../static/oc/icons-v2/noun-people-3393687.svg',
    'projects': '../../static/oc/icons-v2/noun-research-project-2341022.svg',
    # 'subjects': '../../static/oc/icons-v2/noun-object-3504999.svg',
    # 'subjects_children': '../../static/oc/icons-v2/noun-object-3504999.svg',
    'subjects': '../../static/oc/icons-v2/object-icon-draft-2.svg',
    'subjects_children': '../../static/oc/icons-v2/object-icon-draft-2.svg',
    'tables': '../../static/oc/icons-v2/noun-table-4305.svg',
}

DEFAULT_LICENSE_ICONS = {
    'creativecommons.org/licenses/by/': '../../static/oc/cc-icons/cc-by.svg',
    'creativecommons.org/licenses/by-nc/': '../../static/oc/cc-icons/cc-by-nc.svg',
    'creativecommons.org/licenses/by-nc-nd/': '../../static/oc/cc-icons/cc-by-nc-nd.svg',
    'creativecommons.org/licenses/by-nc-sa/': '../../static/oc/cc-icons/cc-by-nc-sa.svg',
    'creativecommons.org/licenses/by-nd/': '../../static/oc/cc-icons/by-nd.svg',
    'creativecommons.org/licenses/by-sa/': '../../static/oc/cc-icons/by-sa.svg',
    'creativecommons.org/publicdomain/mark/': '../../static/oc/cc-icons/cc-publicdomain.svg',
    'creativecommons.org/publicdomain/zero/': '../../static/oc/cc-icons/cc-zero.svg',
}


def _make_key_template_ok(key, key_find_replaces=KEY_FIND_REPLACES):
    """Makes a key OK for a template"""
    if not isinstance(key, str):
        return key
    new_key = key.lower()
    for f, r in key_find_replaces:
        new_key = new_key.replace(f, r)
    return new_key


def make_template_ready_dict_obj(dict_obj):
    """Makes a result object ready for use in a template"""
    if not isinstance(dict_obj, dict):
        return dict_obj
    temp_dict = LastUpdatedOrderedDict()
    for key, value in dict_obj.items():
        new_key = _make_key_template_ok(key)
        if isinstance(value, dict):
            value = make_template_ready_dict_obj(value)
        elif isinstance(value, list):
            temp_dict[new_key] = [
                make_template_ready_dict_obj(v)
                for v in value
            ]
            continue
        temp_dict[new_key] = value
    return temp_dict


def prepare_citation_dict(rep_dict):
    """Prepares a citation dictionary object

    :param dict rep_dict: The item's JSON-LD representation dict
    """
    cite = {
        'title': rep_dict.get('dc-terms:title'),
        'uri': rep_dict.get('id'),
    }
    return cite


def prepare_item_metadata_obs(
    rep_dict,
    obs_id=ITEM_METADATA_OBS_ID,
    obs_label=ITEM_METADATA_OBS_LABEL, 
    skip_keys=SPECIAL_KEYS
):
    """Prepares an observation dict for metadata directly associated to an item

    :param dict rep_dict: The item's JSON-LD representation dict
    :param str obs_label: The label for the observation
    :param list skip_keys: A list of string dictionary keys to skip
        and not allocate to the output meta_obs_dict dict.
    """
    meta_attribute_group_dict = LastUpdatedOrderedDict()
    meta_attribute_group_dict['default'] = True

    meta_count = 0
    for key, vals in rep_dict.items():
        if key in skip_keys:
            # This key is not used for metadata.
            continue
        meta_attribute_group_dict[key] = vals
        meta_count += 1
    if meta_count == 0:
        # We have no linked data predicates / metadata
        # directly associated with this item. Return None.
        return None

    # Bundle the linked data metadata into nested 
    # attribute group, events to make templating more
    # consistent.
    meta_event_dict = LastUpdatedOrderedDict()
    meta_event_dict['default'] = True
    meta_event_dict['oc-gen:has-attribute-groups'] = [
        meta_attribute_group_dict
    ]
    meta_obs_dict = LastUpdatedOrderedDict()
    meta_obs_dict['id'] = obs_id
    meta_obs_dict['label'] = obs_label
    meta_obs_dict['default'] = True
    meta_obs_dict['oc-gen:has-events'] = [
        meta_event_dict
    ]
    return meta_obs_dict


def template_reorganize_attribute_group_dict(old_attrib_grp):
    """Reorganizes assertions in an observation for easier template use

    :param dictold_attrib_grp: An attribute group dict from the item's
        JSON-LD representation dict
    """
    
    # NOTE: To make templating easier, this function groups together
    # assertions by predicate and object item_type. The general structure
    # for the output is like:
    #
    # {
    #   'id': '#-attribute-group'
    #   'label': 'Default',
    #   'type': 'oc-gen:attribute-groups',
    #   'default': True,
    #   'descriptions': {
    #       'oc-pred:24-fabric-category': [
    #        ....lots of dicts of descriptions...
    #       ],
    #       'oc-pred:24-object-type': [
    #           ...lots of dicts of object types ...
    #       ],
    #   },
    #   'relations': {
    #       'subjects': {
    #           'oc-pred:oc_gen_links: [
    #            .... links to different subjects items...
    #           ],
    #       },
    #       'media': {
    #           'oc-pred:oc_gen_links: [
    #            .... links to different media items...
    #           ],
    #       }
    #   },
    # }

    node_keys = ['id', 'label', 'type', 'default']

    new_attrib_group = LastUpdatedOrderedDict()
    for key in node_keys:
        new_attrib_group[key] = old_attrib_grp.get(key)

    new_attrib_group['descriptions'] = LastUpdatedOrderedDict()
    new_attrib_group['relations'] = {}

    for pred_key, vals in old_attrib_grp.items():
        if pred_key in node_keys:
            # We've already copied over the node keys.
            continue
        if not isinstance(vals, list) or not len(vals):
            # This is not a list or it is an empty list.
            continue
        is_relation = (
            str(vals[0].get('predicate__item_class_id')) == configs.CLASS_OC_LINKS_UUID
        )
        if not is_relation:
            # This predicate (pred_key) is not used for a relation,
            # so treat this as a description.
            new_attrib_group['descriptions'][pred_key] = vals
            continue
        
        # Nest relations by the item_type of the object of the
        # assertion, then by the predicate for the assertion.
        for act_val in vals:
            act_item_type = act_val.get('object__item_type')
            if act_item_type not in configs.OC_PRED_LINK_OK_ITEM_TYPES:
                continue
            if act_item_type == 'subjects' and pred_key == 'oc-pred:oc-gen-contains':
                # NOTE: We're treating the (children) subjects of 
                # spatial containment relations somewhat differently in our
                # tempate
                act_item_type = 'subjects_children'
            if pred_key in ['oc-pred:oc-gen-links', 'oc-pred:oc-gen-contains']:
                # The predicate is a default type that does not need to be
                # displayed in the HTML UI.
                act_val['no_display_pred'] = True
            
            # Add a default icon to an item type if missing and default exists.
            if not act_val.get('object_class_icon') and DEFAULT_ITEM_TYPE_ICONS.get(act_item_type):
                act_val['object_class_icon'] = DEFAULT_ITEM_TYPE_ICONS.get(act_item_type)

            new_attrib_group['relations'].setdefault(
                act_item_type,
                LastUpdatedOrderedDict()
            )
            new_attrib_group['relations'][act_item_type].setdefault(
                pred_key,
                []
            )
            new_attrib_group['relations'][act_item_type][pred_key].append(
                act_val
            )

    return new_attrib_group


def template_reorganize_obs(old_obs_dict):
    """Reorganizes assertions in an observation for easier template use

    :param dict old_obs_dict: An observation dict from the item's
        JSON-LD representation dict
    """
    new_obs_dict = LastUpdatedOrderedDict()
    for key, vals in old_obs_dict.items():
        if key == 'oc-gen:has-events':
            continue
        new_obs_dict[key] = vals
    
    new_obs_dict['oc-gen:has-events'] = []
    for old_event_dict in old_obs_dict.get('oc-gen:has-events', []):
        new_event_dict = LastUpdatedOrderedDict()
        for key, vals in old_event_dict.items():
            if key == 'oc-gen:has-attribute-groups':
                continue
            new_event_dict[key] = vals
        
        new_event_dict['has_descriptions'] = None
        new_event_dict['has_relations'] = None
        new_event_dict['oc-gen:has-attribute-groups'] = []
        for old_attrib_grp in old_event_dict.get('oc-gen:has-attribute-groups', []):
            new_attrib_group = template_reorganize_attribute_group_dict(
                old_attrib_grp
            )
            if len(new_attrib_group.get('descriptions', {})):
                new_event_dict['has_descriptions'] = True
            if len(new_attrib_group.get('relations', {})):
                new_event_dict['has_relations'] = True
            new_event_dict['oc-gen:has-attribute-groups'].append(
                new_attrib_group
            )

        
        new_obs_dict['oc-gen:has-events'].append(new_event_dict)
    return new_obs_dict


def get_units_from_obs(new_obs_dict, units_of_measurement_dict):
    """Extracts units of measurement from assertions in an observation
    
    :param dict new_obs_dict: An observation assertion dict already
        reorganized for templating
    :parma dict unit_of_measurement_dict: A dictionary of unique
        units of measurement in the all observation assertions.
    """

    unit_obj_keys = [
        'id',
        'slug',
        'label',
        'object_id',
        'object__meta_json',
        'object__context__label',
        'object__context__uri'
    ]
    for event_dict in new_obs_dict.get('oc-gen:has-events', []):
        for attrib_group in event_dict.get('oc-gen:has-attribute-groups', []):
            for _, obj_list in attrib_group.get('descriptions', {}).items():
                for obj_dict in obj_list:
                    if obj_dict.get('object__item_type') != 'units':
                        continue
                    units_obj = {k: obj_dict.get(k) for k in unit_obj_keys}
                    units_obj['symbol'] = obj_dict.get(
                        'object__meta_json',
                        {}
                    ).get('symbol')
                    units_of_measurement_dict[units_obj.get('id')] = units_obj
    return units_of_measurement_dict


def template_reorganize_all_obs(rep_dict):
    """Iterates through all observations to make easy to template groups

    :param dict rep_dict: The item's JSON-LD representation dict
    """
    if not rep_dict.get('oc-gen:has-obs'):
        return rep_dict
    
    units_of_measurement_dict = {}
    all_new_obs = []
    for old_obs_dict in rep_dict.get('oc-gen:has-obs'):
        new_obs_dict = template_reorganize_obs(old_obs_dict)
        units_of_measurement_dict = get_units_from_obs(
            new_obs_dict, 
            units_of_measurement_dict
        )
        all_new_obs.append(new_obs_dict)
    
    rep_dict['oc-gen:has-obs'] = all_new_obs
    if units_of_measurement_dict:
        # Make the units of measurement seen in these observation
        # assertions easily accessible for templating.
        rep_dict['units_of_measurement'] = [v for _,v in units_of_measurement_dict.items()]
    return rep_dict



def add_license_icons_public_domain_flag(rep_dict, icon_dict=DEFAULT_LICENSE_ICONS):
    """Adds licensing icons to license assertions

    :param dict rep_dict: The item's JSON-LD representation dict
    """
    if not rep_dict.get('dc-terms:license'):
        return rep_dict
    
    for lic_dict in rep_dict.get('dc-terms:license'):
        if '/publicdomain/' in lic_dict.get('id', ''):
            lic_dict['is_publicdomain'] = True
        else:
            lic_dict['is_publicdomain'] = False

        if lic_dict.get('object_class_icon'):
            # This license dict already has an icon
            continue
        for uri_key, icon_url in icon_dict.items():
            if not uri_key in lic_dict.get('id', ''):
                # The URI key is not a substring of the license
                # URI (id)
                continue
            lic_dict['object_class_icon'] = icon_url
    return rep_dict


def add_geo_overlay_images(
    rep_dict, 
    geo_over_key=GEO_OVERLAYS_JSON_LD_KEY,
    template_key=TEMPLATE_GEO_OVERLAY_KEY,
    default_opacity=GEO_OVERLAY_OPACITY_DEFAULT
):
    """Adds geo-overlay images formatted for easy use by Leaflet, Vue

    :param dict rep_dict: The item's JSON-LD representation dict
    :param str geo_over_key: The default predicate key for geo
        overlay objects
    :param str template_key: The HTML template key for geo-overlay
        objects.
    :param float default_opacity: The default opacity of an overlay
        image if now configured in meta_json.
    """
    if not rep_dict.get(geo_over_key):
        # There are no geo-overlay images.
        return rep_dict
    
    required_obj_keys = [
        'object__meta_json',
        'object__geo_overlay',
    ]
    required_meta_json_leaflet_keys = [
        'bounds'
    ]
    overlays = []
    for over_dict in rep_dict.get(geo_over_key):
        # Do a little validation to make sure we
        # have the object keys we need.
        keys_ok = True
        for req_key in required_obj_keys:
            if not over_dict.get(req_key):
                keys_ok = False
        if not keys_ok:
            # We're missing some data, so don't
            # include this in the overlays
            continue
        # Make the object_meta_json keys all nice and lower-case for easy handling.
        obj_meta_json = make_template_ready_dict_obj(
            over_dict['object__meta_json']
        )
        if not obj_meta_json.get('leaflet'):
            # We're missing leaflet expected JSON
            continue
        # We'll use the 'leaflet' dict object from the object__meta_json
        # (which ultimately comes from the Manifest object for the 
        # overlay image item-type 'media' meta_json).
        overlay = copy.deepcopy(
            obj_meta_json['leaflet']
        )
        for req_key_leaflet in required_meta_json_leaflet_keys:
            if not overlay.get(req_key_leaflet):
                keys_ok = False
        if not keys_ok:
            # We're missing required leaflet JSON keys
            continue
        # At this point, we've got partially validated overlay
        # data, so we can start making an object ready for the
        # HTML template and leaflet vue.js
        if not overlay.get('label'):
            # Fill in a label from the object label, or use a default
            overlay['label'] = over_dict.get('object__label', 'Map overlay')
        if not overlay.get('opacity'):
            overlay['opacity'] = default_opacity
        if not overlay.get('visible'):
            overlay['visible'] = True
        overlay['id'] = over_dict.get("id")
        overlay['url'] = over_dict.get('object__geo_overlay')
        attribution = (
            f'See: <a href="{over_dict.get("id")}">{over_dict.get("object__label")}</a>'
        )
        overlay['attribution'] = attribution
        overlays.append(overlay)

    # Add these processed overlays to the rep_dict
    rep_dict[template_key] = overlays
    return rep_dict


def check_cors_ok_or_proxy_url(url):
    """Checks if a URL is CORS ok, or proxy a URL"""
    for cors_ok_domain in settings.CORS_OK_DOMAINS:
        if cors_ok_domain in url:
            return url
    # Use our proxy to make this CORS ok.
    rp = RootPath()
    url = rp.get_baseurl() + '/entities/proxy/' + urlquote(url)
    return url


def gather_media_links(man_obj, rep_dict):
    """Gathers all media links for images, 3D models, GIS previews and downloads
    
    :param AllManifest man_obj: A instance of the AllManifest model for the
        the item that is getting a representation.
    :param dict rep_dict: The item's JSON-LD representation dict
    """
    if man_obj.item_type != 'media':
        # Not a media item, so this is not relevant.
        return rep_dict
    if not rep_dict.get('oc-gen:has-files'):
        # This media item currently lacks files, so skip out.
        return rep_dict
    for file_dict in rep_dict.get('oc-gen:has-files'):
        format = file_dict.get('dc-terms:hasFormat', '')
        type = file_dict.get('type')
        uri = file_dict.get('id')
        filesize = file_dict.get('dcat:size')
        if type == 'oc-gen:preview':
            if format.endswith('geo+json'):
                # Works for the obsoleted "application/vnd.geo+json"
                # and the current "application/geo+json"
                uri = check_cors_ok_or_proxy_url(uri)
                rep_dict['media_preview_geojson'] = uri
            elif format.endswith('application/pdf') or uri.lower().endswith('.pdf'):
                uri = check_cors_ok_or_proxy_url(uri)
                rep_dict['media_preview_pdf'] = uri
            elif (
                'image' in format 
                or str(man_obj.item_class.uuid) == configs.CLASS_OC_IMAGE_MEDIA
            ):
                if rep_dict.get('media_preview_image'):
                    rep_dict['media_preview_fallback_image'] = uri
                else:
                    rep_dict['media_preview_image'] = uri
            else:
                continue
        elif type == 'oc-gen:iiif':
            rep_dict['media_iiif'] = uri
        elif type == 'oc-gen:nexus-3d':
            rep_dict['media_nexus_3d'] = uri
        elif type == 'oc-gen:x3dom-model':
            rep_dict['media_x3dom_model'] = uri
        elif type == 'oc-gen:x3dom-texture':
            rep_dict['media_x3dom_texture'] = uri
        elif type == 'oc-gen:fullfile':
            # Use the fullfile as the download if the download is
            # not already set.
            if not rep_dict.get('media_download'):
                rep_dict['media_download'] = uri
            if filesize and not rep_dict.get('media_filesize'):
                rep_dict['media_filesize'] = float(filesize)
        elif type == 'oc-gen:ia-fullfille':
            # A more preferred download source.
            rep_dict['media_download'] = uri
            if filesize:
                rep_dict['media_filesize'] = float(filesize)
        elif type == 'oc-gen:archive':
            # A more preferred download source.
            rep_dict['media_download'] = uri
            if filesize:
                rep_dict['media_filesize'] = float(filesize)
        else:
            pass
    if rep_dict.get('media_filesize'):
        fmath = FileMath()
        rep_dict['media_filesize_human'] = fmath.approximate_size(
            rep_dict.get('media_filesize')
        )
    return rep_dict


def prepare_for_item_dict_solr_and_html_template(man_obj, rep_dict):
    """Prepares a representation dict for Solr indexing and HTML templating
    
    :param AllManifest man_obj: A instance of the AllManifest model for the
        the item that is getting a representation.
    :param dict rep_dict: The item's JSON-LD representation dict
    """

    # Consolidate the contexts paths
    rep_dict['contexts'] = (
        rep_dict.get('oc-gen:has-contexts', []) 
        + rep_dict.get('oc-gen:has-linked-contexts', [])
    )

    # Add any metadata about this item.
    meta_obs_dict = prepare_item_metadata_obs(rep_dict)
    if meta_obs_dict:
        rep_dict.setdefault('oc-gen:has-obs', [])
        rep_dict['oc-gen:has-obs'].append(meta_obs_dict)

    # Reorganize the nesting of the assertions to make
    # them more consistent and easier to use in the template
    rep_dict = template_reorganize_all_obs(rep_dict)

    # Add licensing icons to licenses in the rep_dict
    rep_dict = add_license_icons_public_domain_flag(rep_dict)

    # Make any geospatial overlay images more convenient to use
    # in the HTML template with leaflet and vue.js
    rep_dict = add_geo_overlay_images(rep_dict)

    # Gather links for different types of media.
    rep_dict = gather_media_links(man_obj, rep_dict)

    return rep_dict


def prepare_for_item_dict_html_template(man_obj, rep_dict):
    """Prepares a representation dict for HTML templating
    
    :param AllManifest man_obj: A instance of the AllManifest model for the
        the item that is getting a representation.
    :param dict rep_dict: The item's JSON-LD representation dict
    """

    # Convert into a count, because for_solr_assert_objs is not used
    # in HTML templating.
    rep_dict['for_solr_assert_objs'] = len(
        rep_dict.get('for_solr_assert_objs', [])
    )

    # Do the main reorganization to make convenient for HTML templating
    rep_dict = prepare_for_item_dict_solr_and_html_template(
        man_obj, 
        rep_dict
    )

    # Now ensure easy to template characters in the keys
    # in this dict
    item_dict = make_template_ready_dict_obj(rep_dict)

    return item_dict

