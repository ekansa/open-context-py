import copy
import logging
import lxml.html

from django.conf import settings
from django.utils.html import strip_tags

from opencontext_py.libs.isoyears import ISOyears
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.libs.rootpath import RootPath

from opencontext_py.apps.entities.uri.models import URImanagement

from opencontext_py.apps.all_items.models import (
    AllAssertion,
)
from opencontext_py.apps.all_items.icons import configs as icon_configs

from opencontext_py.apps.indexer import solrdocument_new_schema as SolrDoc

from opencontext_py.apps.searcher.new_solrsearcher import configs
from opencontext_py.apps.searcher.new_solrsearcher import db_entities
from opencontext_py.apps.searcher.new_solrsearcher import event_utilities
from opencontext_py.apps.searcher.new_solrsearcher import utilities


logger = logging.getLogger(__name__)


PRED_ID_FIELD_SUFFIX = (
    SolrDoc.SOLR_VALUE_DELIM
    + SolrDoc.FIELD_SUFFIX_PREDICATE
)


def get_record_uuids_from_solr(solr_json):
    """Gets a list of UUIDs from the solr json response"""
    doc_list = utilities.get_dict_path_value(
        configs.RECORD_PATH_KEYS,
        solr_json,
        default=[]
    )
    uuids = [doc.get('uuid') for doc in doc_list if doc.get('uuid')]
    return uuids


def make_url_from_partial_url(
    partial_url,
    base_url=settings.CANONICAL_HOST
):
    for prefix in ['http://', 'https://']:
        if partial_url.startswith(prefix):
            # The partial_url is already a fully defined
            # url, so return it. No need to stick it on a base.
            return partial_url
    return base_url + partial_url


def get_record_uris_from_solr(solr_json):
    """Gets a list of URIs from the solr json response"""
    uri_list = []
    doc_list = utilities.get_dict_path_value(
        configs.RECORD_PATH_KEYS,
        solr_json,
        default=[]
    )
    for doc in doc_list:
        if not doc.get('slug_type_uri_label'):
            continue
        item_dict = utilities.parse_solr_encoded_entity_str(
            doc.get('slug_type_uri_label'),
        )
        uri = make_url_from_partial_url(
            item_dict.get('uri', '')
        )
        uri_list.append(uri)
    return uri_list


def get_simple_hierarchy_items(solr_doc, all_obj_field, solr_slug_format=False):
    """Gets and parses simple (single path) solr entities from an
    'all-objects-field'

    :param dict solr_doc: Solr document dictionary, which is keyed by
        solr fields and has lists of values for the fields.
    :param str all_obj_field: Solr field that will list solr entity
        strings in order from most general to most specific. This
        needs to be a context or a project all object field where
        all the a hierarchy are listed in order.
    """
    hierarchy_items = []
    solr_ent_str_list = solr_doc.get(all_obj_field)
    if not solr_ent_str_list:
        # No hierarchic entities, return an empty list.
        return hierarchy_items
    for solr_ent_str in solr_ent_str_list:
        hierarchy_item = utilities.parse_solr_encoded_entity_str(
            solr_ent_str,
            solr_slug_format=solr_slug_format,
        )
        if not hierarchy_item:
            logger.warn(
                'Cannot parse {} from field {}'.format(
                    solr_ent_str,
                    all_obj_field
                )
            )
            continue
        hierarchy_items.append(hierarchy_item)
    return hierarchy_items


def get_specific_attribute_values(
    solr_doc,
    parent_dict,
    specific_predicate_dict,
    depth=0
):
    """Gets a list of the most specific attributes and values tuples
    starting from a parent_dict.

    :param dict solr_doc: Solr document dictionary, which is keyed by
        solr fields and has lists of values for the fields.
    :param dict parent_dict: A dictionary derived from parsing a solr
        entity string. The slug of the dict will be the solr field
        prefix for the the next level down in the hierarchy.
    :param dict specific_predicate_dict: This dict is derived from
        parsing a solr entity string. It is the most specific
        property / predicate in the hierarchy that we're going down.
        Because it is the most specific property / predicate in this
        hierarchy, it is the "attribute" that will have one or more
        values returned to the client.
    """
    outputs = []
    if depth >= 10:
        return outputs
    slug_prefix = parent_dict['slug'] + SolrDoc.SOLR_VALUE_DELIM
    specific_pred_field_part = (
        SolrDoc.SOLR_VALUE_DELIM
        + specific_predicate_dict['slug']
        + SolrDoc.SOLR_VALUE_DELIM
    )

    # A solr document (solr_doc) is a dict keyed by solr fields
    # for a list of values. The values (solr_vals) can either be
    # literals or solr entity strings. If solr entity strings, these
    # entities may themselves have children deeper in the hierarchy.
    # This recursively gets children entities until there are no more
    # deeper (more specific) children.
    for key, solr_vals in solr_doc.items():
        if not key.startswith(slug_prefix):
            # This is not the key we are looking for.
            continue

        if specific_pred_field_part not in key:
            # The current solr field key does not have the
            # specific pred field part in it, so we're going
            # to make an update so that the new specific
            # predicate dict is the parent dict.
            specific_predicate_dict = parent_dict.copy()

        if not key.endswith(PRED_ID_FIELD_SUFFIX):
            # The values are literals, so return those as a tuple of
            # the predicate for this attribute and the values for this
            # attribute.
            outputs += [(specific_predicate_dict, solr_vals,)]
            continue

        val_dicts = []
        for solr_val in solr_vals:
            val_dict = utilities.parse_solr_encoded_entity_str(
                solr_val,
                solr_slug_format=True,
            )
            if not val_dict:
                # Weird. This is not a valid solr entity string.
                continue
            # The parsed solr entity in val_dict may itself have child
            # entities. Check to see it it does, and add these to the
            # list of outputs.
            deeper_outputs = get_specific_attribute_values(
                solr_doc=solr_doc,
                parent_dict=val_dict,
                specific_predicate_dict=specific_predicate_dict,
                depth=(depth + 1),
            )
            if len(deeper_outputs):
                # We found deeper child attributes, values so
                # add these to the list of outputs.
                outputs += deeper_outputs
                continue
            # There are no deeper outputs for this solr_val
            # which means we're at the bottom of the hierarchy, and
            # we should add this parsed solr entity value dict to the
            # list of values for this specific_predicate_dict.
            val_dicts.append(val_dict)

        if len(val_dicts):
            outputs += [(specific_predicate_dict, val_dicts,)]
    return outputs


def get_uuid_from_entity_dict(
    entity_dict,
    data_type_limit=None,
    item_type_limit=None,
):
    """Gets a uuid from an entity dict meeting optional criteria

    :param dict entity_dict: A dictionary of an entity item derived
        from parsing a solr entity string.
    """
    if (data_type_limit
        and entity_dict.get('data_type') != data_type_limit):
        return None
    uri = entity_dict.get('uri', '')
    if (item_type_limit and
        not uri.startswith('/{}/'.format(item_type_limit))):
        # No uuid for this item, so don't try
        return None
    uuid =  uri.split('/')[-1]
    return uuid


def desolr_attribute_tuples_slugs(attribute_values_tuples):
    """Switch attribute tuples slugs to the normal, not solr version"""
    fixed_tuples = []
    for pred_dict, vals in attribute_values_tuples:
        if not pred_dict.get('slug'):
            # This should not happen, but this check helps
            # filter out bad data.
            continue
        # Replace underscore with a dash
        pred_dict['slug'] = pred_dict['slug'].replace('_', '-')
        fixed_vals = []
        for val in vals:
            if not isinstance(val, dict):
                fixed_vals.append(val)
                continue
            if not val.get('slug'):
                # Again, weird. Should have s slug so remove
                # since it does not.
                continue
            val['slug'] = val['slug'].replace('_', '-')
            fixed_vals.append(val)
        fixed_tuples.append(
            (pred_dict, fixed_vals,)
        )
    return fixed_tuples


def get_attribute_tuples_string_pred_uuids(attribute_values_tuples):
    """Gets a list of string predicate uuids from a list of attribute
    value tuples

    :param list attribute_values_tuples: List of attribute values
        tuples, where the first tuple element is a predicate dict
        derived from a solr entity string.
    """
    string_pred_uuids = []
    for pred_dict, _ in attribute_values_tuples:
        uuid = get_uuid_from_entity_dict(
            pred_dict,
            data_type_limit='string',
            item_type_limit='predicates'
        )
        if not uuid:
            # Not a string predicate uuid, so skip.
            continue
        string_pred_uuids.append(uuid)

    return string_pred_uuids


def get_predicate_attributes(
    solr_doc,
    root_key=SolrDoc.ROOT_PREDICATE_SOLR
):
    """Gets nonstandard predicate attributes from a solr doc

    :param dict solr_doc: Solr document dictionary, which is keyed by
        solr fields and has lists of values for the fields.
    :param str root_key: The dictionary key for the solr field with
        solr entity string values at the start / root of the hierarchy
        to make a list of most specific attribute tuples.
    """
    attribute_values_tuples = []
    root_preds = solr_doc.get(root_key)
    if not root_preds:
        # No root predicates, so return an empty list.
        return attribute_values_tuples
    for pred in root_preds:
        pred_dict = utilities.parse_solr_encoded_entity_str(
            pred,
            solr_slug_format=True,
        )
        attribute_values_tuples += get_specific_attribute_values(
            solr_doc,
            parent_dict=pred_dict.copy(),
            specific_predicate_dict=pred_dict.copy(),
        )
    return attribute_values_tuples


def get_linked_data_attributes(solr_doc):
    """Gets linked data attributes from a solr doc

    :param dict solr_doc: Solr document dictionary, which is keyed by
        solr fields and has lists of values for the fields.
    """
    return get_predicate_attributes(
        solr_doc,
        root_key=SolrDoc.ROOT_LINK_DATA_SOLR
    )


def get_geo_all_event_source_uuid(solr_doc):
    """Gets the uuid for a geo source for un-typed, all_events"""

    # NOTE: An 'all-events geo source' is the item with non-point
    # geo spatial feature data. A give record may have its own
    # geo spatial feature data, or it may be contained within
    # another item that has such data. This method gets the
    # UUID for non-point geospatial feature data that associated
    # with this item or other items that may contain it.

    all_event_source_str = solr_doc.get('all_events___geo_source')
    if not all_event_source_str:
        return None

    all_event_source_dict = utilities.parse_solr_encoded_entity_str(
        all_event_source_str,
        solr_slug_format=False,
    )
    if not all_event_source_dict:
        return None

    uuid = get_uuid_from_entity_dict(
        all_event_source_dict,
        data_type_limit='id',
        item_type_limit='subjects'
    )
    return uuid


class SamplingSite():
    def __init__(self, label, uri):
        self.label = label
        self.uri = uri



class ResultRecord():

    """ Methods to prepare an individual result record """

    def __init__(self,
        solr_doc=None,
    ):
        rp = RootPath()
        self.base_url = rp.get_baseurl()
        self.solr_doc = solr_doc

        # The following are standard attributes for record idems
        self.uuid = None
        self.slug = None
        self.uri = None  # cannonical uri for the item
        self.href = None  # link to the item in the current deployment
        self.cite_uri = None  # stable / persistent uri
        self.label = None
        self.item_type = None
        self.updated = None
        self.published = None
        self.project_href = None  # link to the project in deployment
        self.project_uri = None  # cannonical uri for the project
        self.project_label = None
        self.context_href = None  # link to parent context in deployment
        self.context_uri = None  # link to parent context cannonical uri
        self.context_label = None
        self.category = None
        self.icon = None
        self.latitude = None
        self.longitude = None
        self.geo_feature_type = 'Point'  # Default to point.
        self.geometry_coords = None  # GeoJSON geometry coordinates
        self.early_date = None
        self.late_date = None
        self.thumbnail_href = None
        self.thumbnail_uri = None
        self.thumbnail_src = None
        self.preview_src = None
        self.fullfile_src = None
        self.iiif_json_uri = None
        self.snippet = None
        self.cite_uri = None  # stable identifier as an HTTP uri
        self.descriptiveness = None # maps to interest_score
        self.hero_banner_src = None # hero banner, collected for the project index
        self.description = None # short description of a project.

        # All spatial contexts (dicts derived from solr entity stings)
        self.contexts = None

        # All projects (dicts derived from solr entity stings)
        self.projects = None

        # Linked data attributes
        self.ld_attributes = []
        # Add a column for URIs to linked data attribute values.
        self.add_ld_attrib_values_uris = True
        # Project-specific predicate attributes
        self.pred_attributes = []
        # Add a column for URIs to project specific attribute values.
        self.add_proj_attrib_values_uris = False

        # Flagged as relating to human remains
        self.human_remains_flagged = False

        # flatten list of an attribute values to single value
        self.flatten_attributes = False

        # prepare and format for iSamples
        self.do_isamples = False

        # prepare nested-json objects for attributes
        self.do_nested_json_attributes = False

        # Skip out if we don't have a solr_doc
        if not solr_doc:
            return None

        # Populate some initial metadata on creation
        self.set_record_basic_metadata(solr_doc)
        self.set_record_category(solr_doc)
        self.set_record_icon(solr_doc)
        self.set_record_contexts(solr_doc)
        self.set_record_projects(solr_doc)
        self.set_geo_point_attributes(solr_doc)
        self.set_chrono_ranges(solr_doc)
        self.set_media(solr_doc)


    def set_record_basic_metadata(self, solr_doc):
        """Sets the record's general metadata attributes"""
        self.uuid = solr_doc.get('uuid')
        item_dict = utilities.parse_solr_encoded_entity_str(
            solr_doc.get('slug_type_uri_label', ''),
            solr_slug_format=False,
        )
        if not item_dict:
            return None

        # Add the item local url for this deployment
        self.href = make_url_from_partial_url(
            item_dict.get('uri', ''),
            base_url=self.base_url,
        )
        # Add the item "cannonical" uri
        self.uri = make_url_from_partial_url(
            item_dict.get('uri', ''),
            base_url=settings.CANONICAL_HOST
        )

        cite_uris = solr_doc.get('persistent_uri', [None])
        if cite_uris[0]:
            self.cite_uri = f'https://{cite_uris[0]}'

        self.item_type = solr_doc['item_type']
        self.label = item_dict.get('label')
        self.slug = item_dict.get('slug')
        self.descriptiveness = solr_doc.get('interest_score')
        self.published = solr_doc.get('published')
        self.updated = solr_doc.get('updated')
        self.human_remains_flagged = solr_doc.get('human_remains', False)


    def set_record_category(self, solr_doc):
        """Sets the record category"""
        if not self.item_type:
            item_type_list = solr_doc.get('item_type')
            if not item_type_list:
                logger.warn('Cannot find an item type for this record')
                return None
            self.item_type = item_type_list[0]

        if solr_doc.get('item_class'):
            # The simple case of a category.
            self.category = solr_doc.get('item_class')
        if 'Default (null)' in self.category:
            self.category = self.item_type.title()


    def set_record_icon(self, solr_doc):
        if not self.item_type or not self.category:
            # Make sure we have the item_type and the category set
            self.set_record_category(solr_doc)
        item_type_icon = icon_configs.DEFAULT_ITEM_TYPE_ICONS.get(self.item_type)
        if not item_type_icon:
            # We can't do this, so skip out.
            return None
        class_dict = {}
        solr_class_items = solr_doc.get('obj_all___oc_gen_category___pred_id')
        if solr_class_items:
            solr_class_item = solr_class_items[-1]
            class_dict = utilities.parse_solr_encoded_entity_str(
                solr_class_item,
                solr_slug_format=False,
            )
        class_icon = None
        for class_conf in icon_configs.ITEM_TYPE_CLASS_ICONS_DICT.get(self.item_type, []):
            if not class_conf.get('icon'):
                # No icon configured for this class, so skip
                continue
            class_label = class_conf.get('item_class__label')
            class_slug = class_conf.get('item_class__slug')
            if not class_slug and not class_label:
                continue
            if class_slug == class_dict.get('slug') or class_label == self.category:
                class_icon = class_conf.get('icon')
            if class_icon is not None:
                break
        if class_icon:
            self.icon = class_icon
        else:
            self.icon = item_type_icon
        if self.icon and self.base_url:
            self.icon = self.icon.replace('../..', self.base_url)


    def set_record_contexts(self, solr_doc):
        """Sets the records spatial contexts list"""
        self.contexts = get_simple_hierarchy_items(
            solr_doc,
            SolrDoc.ALL_CONTEXT_SOLR
        )
        if not self.contexts:
            return None

        # Set the local link to the last item in the
        # contexts list
        self.context_href = make_url_from_partial_url(
            self.contexts[-1].get('uri', ''),
            base_url=self.base_url,
        )
        # Set the cannonical link to the last item in the
        # contexts list
        self.context_uri = make_url_from_partial_url(
            self.contexts[-1].get('uri', ''),
            base_url=settings.CANONICAL_HOST,
        )
        if solr_doc.get('context_path'):
            # We have this in the solr doc (a sortable field)
            self.context_label = solr_doc.get('context_path')
        else:
            # Set the context label from all the labels in the
            # context list.
            context_labels = [
                c['label'] for c in self.contexts if c.get('label')
            ]
            self.context_label = '/'.join(context_labels)
        if (
            (self.category == configs.CLASS_OC_SITE_DOCUMENTATION_LABEL)
            or (solr_doc.get('item_class') == configs.CLASS_OC_SITE_DOCUMENTATION_LABEL)
        ):
            self.context_label = '(Open Context Website)'


    def set_record_projects(self, solr_doc):
        """Sets the records projects list"""
        self.projects = get_simple_hierarchy_items(
            solr_doc,
            SolrDoc.ALL_PROJECT_SOLR
        )
        if not self.projects:
            return None

        # Set the local link to the last item in the
        # projects list
        self.project_href = make_url_from_partial_url(
            self.projects[-1].get('uri', ''),
            base_url=self.base_url,
        )
        # Set the cannonical link to the last item in the
        # projects list
        self.project_uri = make_url_from_partial_url(
            self.projects[-1].get('uri', ''),
            base_url=settings.CANONICAL_HOST,
        )
        # Set the context label from the last item in
        # the projects list.
        self.project_label = self.projects[-1].get('label', '')


    def set_geo_point_attributes(self, solr_doc):
        """Sets geospatial point attribute values"""
        disc_geo = solr_doc.get(
            f'{configs.ROOT_EVENT_CLASS}___geo_location'
        )
        if not disc_geo or ',' not in disc_geo:
            # No point found or it is not valid
            self.geo_feature_type = None
            return None

        # The default geospatial feature type
        self.geo_feature_type = 'Point'
        lat_lon = disc_geo.split(',')
        self.latitude = float(lat_lon[0])
        self.longitude = float(lat_lon[1])

        # Now make a point coordinate list in the
        # normal GeoJSON lon/lat order.
        self.geometry_coords = [
            self.longitude,
            self.latitude,
        ]


    def set_chrono_ranges(self, solr_doc):
        """Sets chronology date ranges for the record"""
        dates = []
        for i in [0, 1]:
            date_solr = solr_doc.get(
                f'{configs.ROOT_EVENT_CLASS}___chrono_point_{i}___pdouble',
            )
            if date_solr is None:
                continue
            dates.append(date_solr)

        if not len(dates):
            return None
        self.early_date = min(dates)
        self.late_date = max(dates)


    def set_media(self, solr_doc):
        """Sets media urls for the record"""
        self.thumbnail_src = solr_doc.get('thumbnail_uri')
        self.iiif_json_uri = solr_doc.get('iiif_json_uri')


    def make_snippet_resonable_size(
        self,
        snippet,
        temp_mark_pre,
        temp_mark_post,
        large_limit=480,
    ):
        """Makes the snippet a resonable size, with some smart trimming"""
        if len(snippet) < large_limit:
            return snippet
        term_pos = snippet.find(temp_mark_pre)
        prefix_text_pos = term_pos - 140
        if prefix_text_pos < 0:
            prefix_text_pos = 0
        prefix = snippet[prefix_text_pos:term_pos]
        suffix = snippet[term_pos:]
        # print(f'Prefix: "{prefix}"')
        # print(f'Suffix: "{suffix}"')
        nice_breaks = ['\n', '\t', ' ',]
        for nb in nice_breaks:
            # print(f'Check {nb} in {prefix}')
            nb_pos = prefix.find(nb)
            if nb_pos > 0 and nb_pos < (len(prefix) - 20):
                # print(f'Found {nb} at {nb_pos}')
                break
        if nb_pos > 0:
            prefix = prefix[nb_pos:]
        # Now trim the suffix at a nice place to break
        # after the term mark post tag.
        len_suffix = len(suffix)
        pos_term_mark_post = suffix.find(temp_mark_post)
        pos_last_check = pos_term_mark_post + 150
        if pos_last_check >= len_suffix:
            pos_last_check = len_suffix -1
        # Find any next post term markers within a limited range
        # later in the suffix
        next_pos_term_mark_post = suffix.find(
            temp_mark_post,
            (pos_term_mark_post + 1),
            pos_last_check
        )
        if (next_pos_term_mark_post > pos_term_mark_post):
            pos_term_mark_post = next_pos_term_mark_post
        last_suffix_pos = None
        find_start = pos_term_mark_post + 1
        find_end = find_start + 75
        while last_suffix_pos is None and find_start < len_suffix and find_end < len_suffix:
            if last_suffix_pos and last_suffix_pos > pos_term_mark_post:
                break
            for nb in nice_breaks:
                nb_suffix_pos = suffix.find(nb, find_start, find_end)
                # print(f'nb_suffix_pos: {nb_suffix_pos}, find_start {find_start}')
                if nb_suffix_pos < (pos_term_mark_post + 9):
                    continue
                if nb_suffix_pos > find_start:
                    # We have a nice break 75 characters or more
                    # after the search term post tag.
                    last_suffix_pos = nb_suffix_pos
                    break
            find_start += 10
            find_end = find_start + 75
        # print(f'pos_term_mark_post: {pos_term_mark_post}, last_suffix_pos {last_suffix_pos}')
        if last_suffix_pos and last_suffix_pos > pos_term_mark_post:
            suffix = suffix[:last_suffix_pos]
        snippet = prefix + suffix
        # Remove the line breaks.
        snippet = snippet.replace('\n', ' ')
        snippet = snippet.replace('\t', ' ')
        return snippet


    def add_snippet_content(self, highlight_dict):
        """Add highlighting text for keyword searches """
        record_hl_dict = highlight_dict.get(self.uuid)
        if not record_hl_dict:
            return None

        text_list = record_hl_dict.get('text')
        if not text_list:
            return None

        temp_mark_pre = '[[[[mark]]]]'
        temp_mark_post = '[[[[/mark]]]]'
        snippet = ' '.join(text_list)
        snippet = snippet.strip()
        snippet = snippet.replace(
            configs.QUERY_SNIPPET_HIGHLIGHT_TAG_PRE,
            temp_mark_pre
        )
        snippet = snippet.replace(
            configs.QUERY_SNIPPET_HIGHLIGHT_TAG_POST,
            temp_mark_post,
        )
        try:
            snippet = '<div>' + snippet + '</div>'
            snippet = lxml.html.fromstring(snippet).text_content()
            snippet = strip_tags(snippet)
        except:
            snippet = strip_tags(snippet)

        snippet = self.make_snippet_resonable_size(
            snippet=snippet,
            temp_mark_pre=temp_mark_pre,
            temp_mark_post=temp_mark_post,
        )

        self.snippet = snippet.replace(
            temp_mark_pre,
            configs.RECORD_SNIPPET_HIGHLIGHT_TAG_PRE,
        )
        self.snippet = self.snippet.replace(
            temp_mark_post,
            configs.RECORD_SNIPPET_HIGHLIGHT_TAG_POST,
        )


    def add_string_content(self, uuid_pred_str_dict):
        """Adds string content to the pred_attributes"""
        if not self.pred_attributes:
            # This record has no predicate attributes,
            # meaning it has no project defined attributes.
            return None

        item_preds_vals = uuid_pred_str_dict.get(self.uuid)
        if not item_preds_vals:
            # This record doesn't have any string predicates
            # and values associated with it.
            return None

        updated_pred_attributes = []
        for pred_dict, vals_list in self.pred_attributes:
            # Get a string predicate uuid. This will be None
            # if the pred_dict isn't for a string predicate.
            pred_uuid = get_uuid_from_entity_dict(
                pred_dict,
                data_type_limit='string',
                item_type_limit='predicates',
            )
            if pred_uuid:
                # This is for a string predicate, so add the
                # string content from item_pred_vals for this
                # predicate uuid. The string content will be
                # a list.
                vals_list += item_preds_vals.get(pred_uuid, [])
            # Add to the list of updated pred_attribute tuples.
            updated_pred_attributes.append(
                (pred_dict, vals_list,)
            )

        self.pred_attributes = updated_pred_attributes


    def add_db_string_content(self, db_uuid_pred_str_dict):
        """Adds database fetched string content to the pred_attributes"""
        if not db_uuid_pred_str_dict:
            # There are no db_uuid_pred_str_dict data.
            return None

        item_preds_vals = db_uuid_pred_str_dict.get(self.uuid)
        if not item_preds_vals:
            # This record doesn't have any string predicates
            # and values associated with it.
            return None

        for pred_dict, vals_list in item_preds_vals:
            ok_add = True
            if self.ld_attributes:
                for old_pred_dict, _ in self.ld_attributes:
                    if old_pred_dict.get('slug') == pred_dict.get('slug'):
                        ok_add = False
                        break
            if self.pred_attributes:
                for old_pred_dict, _ in self.pred_attributes:
                    if old_pred_dict.get('slug') == pred_dict.get('slug'):
                        ok_add = False
                        break
            if not ok_add:
                # We already have this predicate from another source.
                continue
            # Go ahead and add our string data
            self.pred_attributes.append(
                (pred_dict, vals_list,)
            )


    def gets_isamples_sampling_site(self):
        """Gets a sampling site for iSamples"""
        if not self.contexts:
            return None
        proj_obj = db_entities.get_cache_man_obj_by_any_id(self.project_uri)
        if proj_obj and proj_obj.meta_json.get('omit_db_sampling_site') and self.context_uri:
            # Omit a database search for a sampling site, and just return the
            # last context.
            sampling_site = SamplingSite(
                label=self.context_label.split('/')[-1],
                uri=self.context_uri,
            )
            return sampling_site
        last_region_obj = None
        for context in self.contexts:
            context_uuid = get_uuid_from_entity_dict(
                context,
                data_type_limit='id',
                item_type_limit='subjects',
            )
            if not context_uuid:
                continue
            man_obj = db_entities.get_cache_man_obj_by_any_id(context_uuid)
            if not man_obj:
                continue
            if man_obj.item_class.slug in configs.ISAMPLES_SAMPLING_SITE_ITEM_CLASS_SLUGS:
                # We found a site, our preferred sampling location.
                return man_obj
            if man_obj.item_class.slug == 'oc-gen-cat-region':
                last_region_obj = man_obj
            if last_region_obj is not None and man_obj.item_class.slug != 'oc-gen-cat-region':
                # We didn't find a site, so return the last region object instead.
                return last_region_obj
        return None


    def prepare_isamples_properties(self, properties):
        """Adds database fetched attributes needed by iSamples"""
        if not self.do_isamples:
            return properties
        sampling_site_obj = self.gets_isamples_sampling_site()
        if sampling_site_obj:
            properties['isam:SamplingSite'] = {
                'label': sampling_site_obj.label,
                'identifier': f'https://{sampling_site_obj.uri}',
                'id': f'https://{sampling_site_obj.uri}',
            }
        return properties


    def add_non_point_geojson_coordinates(self, uuid_geo_dict):
        """Adds non-point geojson coordinates to the result"""
        geo_obj =  uuid_geo_dict.get(self.uuid)
        if not geo_obj:
            return None

        if not geo_obj.geometry:
            return None

        self.geo_feature_type = geo_obj.geometry_type
        self.geometry_coords = geo_obj.geometry.get('coordinates')


    def _make_client_attribute_vals(
        self,
        properties,
        pred_key,
        raw_vals,
        add_uris=False
        ):
        """Makes attribute values for a client"""

        # NOTE: There's some complexity in how we return a record's
        # attribute values to a client. A given attribute can have
        # multiple values, which complicates putting record data into
        # a 'flat' structure like a data table or even a GIS. Therefor,
        # Open Context let's clients request an option to 'flattten'
        # multiple values into a single value, seperated by a
        # delimiter. Also, this logical optionally lets Open Context
        # add an additional attribute to provide the URI to values
        # in cases where the values are URI identified entities.
        vals = []
        val_uris = []
        if self.do_nested_json_attributes:
            # Do this for (say with iSamples outputs) so that label/id objects
            # are returned as nested json objects.
            vals_out = []
            for val in raw_vals:
                if isinstance(val, dict):
                    label = val.get('label')
                    uri = make_url_from_partial_url(val.get('uri'))
                    if label and uri:
                        vals_out.append(
                            {
                                'label': label,
                                'id': uri,
                            }
                        )
                    elif label and not uri:
                        vals_out.append(label)
                    else:
                        continue
                else:
                    vals_out.append(val)
            properties[pred_key] = vals_out
            return properties
        # We do the following if we are NOT doing iSamples.
        if add_uris:
            uri_key = '{} [URI]'.format(pred_key)
        for val in raw_vals:
            if isinstance(val, dict):
                # Pull out the label and the uris.
                vals.append(
                    val.get('label')
                )
                uri = make_url_from_partial_url(val.get('uri'))
                val_uris.append(uri)
                continue
            else:
                # Not a dict, just a simple value.
                vals.append(val)

        if not self.flatten_attributes:
            # Simple case, return the vals as a list of vals.
            properties[pred_key] = vals
            if add_uris and len(val_uris):
                # Add the URI to this property value
                properties[uri_key] = val_uris
            # We're done, skip everything in this function
            # below.
            return properties

        # This is for flattening multiple values for
        # record attributes.
        if len(vals) == 1:
            # Only 1 value, so just use it.
            properties[pred_key] = vals[0]
            if add_uris and len(val_uris):
                # Add the URI to this property value
                properties[uri_key] = val_uris[0]
            # We're done, skip everything in this function
            # below.
            return properties

        # Multiple values, be sure to cast as string before
        # concatenating.
        properties[pred_key] = configs.MULTIVALUE_ATTRIB_RESP_DELIM.join(
            [str(val) for val in vals]
        )
        if add_uris and len(val_uris):
            # Add the URI to this property value
            properties[uri_key] = configs.MULTIVALUE_ATTRIB_RESP_DELIM.join(
                val_uris
            )
        return properties


    def make_client_properties_dict(
        self,
        id_value=None,
        feature_type=None,
        add_lat_lon=False,
        add_descriptiveness=False,
        add_slug=False,
        ):
        """Makes a properties dict to return to a client

        :param str id_value: A string value for an id
            key. This is mainly useful for JSON-LD outputs
            where nodes should have identifiers.
        """
        properties = LastUpdatedOrderedDict()
        if id_value:
            properties['id'] = id_value
        if add_slug:
            properties['slug'] = self.slug
        if feature_type:
            properties['feature-type'] = feature_type

        # Always add these.
        properties['label'] = self.label
        properties['uri'] = self.uri
        properties['href'] = self.href
        properties['citation uri'] = self.cite_uri

        if self.do_nested_json_attributes:
            # Nested versions
            properties['id'] = self.uri
            properties['project'] = {
                'label': self.project_label,
                'id': self.project_uri,
            }
            properties['context'] = {
                'label': self.context_label,
                'id': self.context_uri,
            }
        else:
            # Non nested versions.
            properties['project label'] = self.project_label
            properties['project href'] = self.project_href
            properties['context label'] = self.context_label
            properties['context href'] = self.context_href

        if add_lat_lon:
            properties['latitude'] = self.latitude
            properties['longitude'] = self.longitude
        properties['early bce/ce'] = self.early_date
        properties['late bce/ce'] = self.late_date
        if self.category is not None:
            properties['item category'] = self.category
        if self.icon is not None:
            properties['icon'] = self.icon
        if self.snippet:
            properties['snippet'] = self.snippet
        if self.thumbnail_src:
            properties['thumbnail'] = f'https://{self.thumbnail_src}'
        if self.hero_banner_src:
            properties['hero_banner'] = f'https://{self.hero_banner_src}'
        properties['published'] = self.published
        properties['updated'] = self.updated
        if add_descriptiveness:
            properties['descriptiveness'] = self.descriptiveness
        if self.description:
            properties['description'] = self.description

        # Adds iSamples properties if applicable.
        properties = self.prepare_isamples_properties(properties)

        # Add linked data (standards) attributes if they exist.
        for pred_dict, raw_vals in self.ld_attributes:
            if not pred_dict.get('label') or not pred_dict.get('slug'):
                # Something went wrong, no label or slug
                # for the predicate.
                continue
            pred_key = pred_dict.get('label')
            if pred_key in properties:
                # Safety measure to make sure we have no collisions
                # in attribute names.
                pred_key = '{} [{}]'.format(
                    pred_dict.get('label'),
                    pred_dict.get('slug')
                )
            properties = self._make_client_attribute_vals(
                properties,
                pred_key,
                raw_vals,
                add_uris=self.add_ld_attrib_values_uris,
            )

        # Add project-specific predicate attributes after
        for pred_dict, raw_vals in self.pred_attributes:
            if not pred_dict.get('label') or not pred_dict.get('slug'):
                # Something went wrong, no label or slug
                # for the predicate.
                continue
            pred_key = pred_dict.get('label')
            if pred_key in properties:
                # Safety measure to make sure we have no collisions
                # in attribute names.
                pred_key = '{} [{}]'.format(
                    pred_dict.get('label'),
                    pred_dict.get('slug')
                )
            properties = self._make_client_attribute_vals(
                properties,
                pred_key,
                raw_vals,
                add_uris=self.add_proj_attrib_values_uris,
            )

        return properties


    def make_geojson(self, record_index, total_found):
        """Outputs the record object as GeoJSON"""
        geo_json = LastUpdatedOrderedDict()
        geo_json['id'] = f'#record-{record_index}-of-{total_found}'
        geo_json['label'] = self.label
        geo_json['slug'] = self.slug
        geo_json['rdfs:isDefinedBy'] = self.uri
        geo_json['oc-api:descriptiveness'] = self.descriptiveness
        geo_json['oc-api:human-remains-related'] = self.human_remains_flagged
        geo_json['type'] = 'Feature'
        geo_json['category'] = 'oc-api:geo-record'

        geometry = LastUpdatedOrderedDict()
        geometry['id'] = f'#record-geom-{record_index}-of-{total_found}'
        geometry['type'] = self.geo_feature_type
        geometry['coordinates'] = self.geometry_coords
        geo_json['geometry'] = geometry

        if (self.early_date is not None
            and self.late_date is not None):
            # If we have dates, add them.
            when = LastUpdatedOrderedDict()
            when['id'] = f'#record-event-{record_index}-of-{total_found}'
            when['event_type'] = 'oc-gen:general-time-space'
            if self.early_date == self.late_date:
                when['type'] = 'Instant'
            else:
                when['type'] = 'Interval'
            # convert numeric to GeoJSON-LD ISO 8601
            when['start'] = ISOyears().make_iso_from_float(
                self.early_date
            )
            if self.late_date != self.early_date:
                when['stop'] = ISOyears().make_iso_from_float(
                    self.late_date
                )
            geo_json['when'] = when

        # Now add the properties dict to the GeoJSON
        props_id_value = f'#rec-{record_index}-of-{total_found}'
        geo_json['properties'] = self.make_client_properties_dict(
            id_value=props_id_value,
            feature_type='item record'
        )

        return geo_json

# ---------------------------------------------------------------------
# Methods to generate results records (individual items, not facets)
# ---------------------------------------------------------------------
class ResultRecords():

    """ Methods to prepare result records """

    def __init__(self, request_dict, total_found=0, start=0, proj_index=False):
        rp = RootPath()
        self.request_dict = copy.deepcopy(request_dict)
        self.base_url = rp.get_baseurl()
        self.total_found = total_found
        self.start = start
        self.proj_index = proj_index
        # allow_missing_strings_db_query is for the default case where we
        # allow DB queries to fetch string attribute data, because we don't
        # store string values in solr.
        self.allow_missing_strings_db_query = True
        # do_missing_strings_db_query will be True if we determine we
        # actually need to make a database query for string attribute data
        self.do_missing_strings_db_query = None

        # If we do a DB query for string attributes limit DB queries
        # to only project specific string attribute data.
        # Choices are: None (no limits), 'project' (non-opencontext
        # project attributes only), and 'requested_attrib_slugs'
        # (attributes specified by the requested_attrib_slugs)
        self.db_limit_string_attributes = 'requested_attrib_slugs'

        # prepare and format for iSamples
        self.do_isamples = False
        # prepare nested-json objects for attributes
        self.do_nested_json_attributes = False

        # Flatten attributes into single value strings?
        self.flatten_attributes = False
        rec_flatten_attributes = utilities.get_request_param_value(
            self.request_dict,
            param='flatten-attributes',
            default=False,
            as_list=False,
            solr_escape=False,
        )
        if rec_flatten_attributes:
            self.flatten_attributes = True
        self.multivalue_attrib_resp_delim = configs.MULTIVALUE_ATTRIB_RESP_DELIM


    def _gather_requested_attrib_slugs(self):
        """Make a list of requested attribute slugs"""
        requested_attrib_slugs = []

        # Get all of the prop parameter values requested
        # by the client from the self.request_dict.
        raw_props_paths = utilities.get_request_param_value(
            self.request_dict,
            param='prop',
            default=[],
            as_list=True,
            solr_escape=False,
        )
        for raw_prop_path in raw_props_paths:
            # These can have OR conditions along with hierarchy
            # delimiters, so split these apart to get a list of
            # slugs.
            # print(f'Raw path in filter: {raw_prop_path}')
            paths_as_lists = utilities.infer_multiple_or_hierarchy_paths(
                raw_prop_path,
                hierarchy_delim=configs.REQUEST_PROP_HIERARCHY_DELIM,
                or_delim=configs.REQUEST_OR_OPERATOR
            )
            for path_list in paths_as_lists:
                if not isinstance(path_list, list):
                    path_list = [path_list]
                # print(f'Path list in filter: {path_list}')
                # Add the elements of this list to the list
                # of requested_attrib_slugs. Some of these won't be
                # 'property' (predicate) attributes, but that doesn't
                # matter. It's OK to have some noise in the
                # requested_attrib_slugs.
                requested_attrib_slugs += path_list

        # De-duplicate the slugs in the requested_attrib_slugs.
        requested_attrib_slugs = list(set(requested_attrib_slugs))
        # print(f'Props in filter: {requested_attrib_slugs}')
        raw_attributes = utilities.get_request_param_value(
            self.request_dict,
            param='attributes',
            default=None,
            as_list=False,
            solr_escape=False,
        )
        if not raw_attributes:
            # The client did not request additional attributes.
            return requested_attrib_slugs

        if configs.MULTIVALUE_ATTRIB_CLIENT_DELIM not in raw_attributes:
            attrib_list = [raw_attributes]
        else:
            attrib_list = raw_attributes.split(
                configs.MULTIVALUE_ATTRIB_CLIENT_DELIM
            )

        if configs.REQUEST_NESTED_JSON_ATTRIBUTES in attrib_list:
            # The client wants nested JSON objects for named entities
            # that are in the attribute data.
            self.do_nested_json_attributes = True

        if configs.REQUEST_ISAMPLES_ATTRIBUTES in attrib_list:
            # We need to prepare attribute data to be understood by
            # iSamples
            self.do_isamples = True
            self.do_nested_json_attributes = True
            attrib_list.append(configs.REQUEST_ALL_LD_ATTRIBUTES)

        if self.do_nested_json_attributes:
            # We do not flatten attributes if we have a request for
            # nested JSON attributes.
            self.flatten_attributes = False

        # De-duplicate the slugs in the requested_attrib_slugs.
        requested_attrib_slugs = list(
            set(requested_attrib_slugs + attrib_list)
        )
        return requested_attrib_slugs


    def _limit_attributes_by_request(
        self,
        record_attributes,
        requested_attrib_slugs,
        all_attribute_val=configs.REQUEST_ALL_ATTRIBUTES,
        ):
        """Limit the attributes for the records according to client request"""
        if (set([configs.REQUEST_ALL_ATTRIBUTES, all_attribute_val])
            & set(requested_attrib_slugs)):
            # The client specified that all of the record attributes
            # should be returned.
            return record_attributes

        filtered_record_attributes = []
        for pred_dict, vals in record_attributes:
            if pred_dict.get('slug') not in requested_attrib_slugs:
                # The slug for this predicate is NOT in the list
                # of attributes specified by the client. So
                # skip and don't add it to the new
                # filtered_record_attributes list.
                continue
            filtered_record_attributes.append(
                (pred_dict, vals,)
            )
        return filtered_record_attributes


    def _get_string_attribute_values(self, uuids, string_pred_uuids):
        """Gets string attribute values from the database

        :param list uuids: List of UUIDs for the solr documents in the
            results that may have string attributes.
        :param list string_pred_uuids: List of string predicates from
            solr docs
        """

        if not len(string_pred_uuids):
            # Return an empty dict if there are no string predicates.
            return {}

        # NOTE: We need to query the database to get the string content
        # associated with string attribute predicates, because we do
        # not store this in solr.

        # This queryset will be in a SubQuery to effectively make a
        # join between Assertions and OC strings via the
        # assertion.object_uuid and ocstring.uuid keys.
        ass_qs = AllAssertion.objects.filter(
            subject_id__in=uuids,
            # predicate_id__in=string_pred_uuids,
            predicate__data_type='xsd:string',
            visibility=1,
        ).exclude(
            visibility__lt=1
        ).order_by(
            'subject_id',
            'predicate_id',
            'sort'
        )
        output = {}
        for a in ass_qs:
            subject_id = str(a.subject.uuid)
            predicate_id = str(a.predicate.uuid)
            if not subject_id in output:
                output[subject_id] = {}
            if not predicate_id in output[subject_id]:
                output[subject_id][predicate_id] = []
            output[subject_id][predicate_id].append(
                a.obj_string
            )
        return output


    def _set_strings_db_query_config(self, requested_attrib_slugs):
        """Checks to see if we will do database queries to get
        string attribute data
        """
        if not self.allow_missing_strings_db_query:
            # We're not allowing DB check2s for string attribute data
            self.do_missing_strings_db_query = False
            return None

        raw_download = utilities.get_request_param_value(
            self.request_dict,
            param='download',
            default=None,
            as_list=False,
            solr_escape=False,
        )

        raw_attributes = utilities.get_request_param_value(
            self.request_dict,
            param='attributes',
            default=None,
            as_list=False,
            solr_escape=False,
        )
        if not raw_download and not raw_attributes:
            # We're not making a request for a download, so there's
            # no need to do something expensive like a database
            # fetch of string attribute data.
            self.do_missing_strings_db_query = False
            return None

        if raw_download or raw_attributes:
            # We're doing a download, so get the string attributes
            # that may be present in the raw_attributes.
            self.do_missing_strings_db_query = True

        raw_fulltext_search = utilities.get_request_param_value(
            self.request_dict,
            param='q',
            default=None,
            as_list=False,
            solr_escape=False,
        )
        if raw_fulltext_search:
            # We're doing a full text search, so we should do a
            # query for string attributes.
            self.do_missing_strings_db_query = True
            # No limits on what string attributes get returned.
            self.db_limit_string_attributes = None

        if configs.REQUEST_ALL_ATTRIBUTES in requested_attrib_slugs:
            # If the client made a requires for all attributes, do
            # a DB query for string attributes too
            self.do_missing_strings_db_query = True
            # No limits on what string attributes get returned.
            self.db_limit_string_attributes = None

        if configs.REQUEST_ALL_PROJ_ATTRIBUTES in requested_attrib_slugs:
            # If the client made a requires for all attributes, do
            # a DB query for string attributes too
            self.do_missing_strings_db_query = True
            self.db_limit_string_attributes = 'project'


    def make_db_uuid_pred_str_dict(self, uuids, requested_attrib_slugs):
        """Uses the database to get string attribute data for the list of
        uuids
        """
        if not self.allow_missing_strings_db_query or not self.do_missing_strings_db_query:
            return {}
        return db_entities.get_db_uuid_pred_str_dict(
            uuids=uuids,
            db_limit_string_attributes=self.db_limit_string_attributes,
            requested_attrib_slugs=requested_attrib_slugs
        )


    def make_records_from_solr(self, solr_json):
        """Makes record objects from solr_json"""
        records = []
        doc_list = utilities.get_dict_path_value(
            configs.RECORD_PATH_KEYS,
            solr_json,
            default=[]
        )
        if not len(doc_list):
            return records

        # Gather the slugs for additional descriptive attributes
        # that we will add to the result records.
        requested_attrib_slugs = self._gather_requested_attrib_slugs()

        proj_desc_banner_qs = None
        if self.proj_index:
            proj_desc_banner_qs = db_entities.get_project_desc_banner_qs(
                all_projects=True,
            )

        # Get the keyword search highlighting dict. Default
        # to an empty dict if there's no snippet highlighting.
        highlight_dict = solr_json.get('highlighting', {})

        uuids = []
        geo_uuids = []
        string_pred_uuids = []
        records = []
        for solr_doc in doc_list:
            if not solr_doc.get('uuid'):
                # This shouldn't happen...
                logger.warn('Solr doc without a uuid. How?')
                continue

            # Create a result record object by processing the
            # solr_doc for the result item.
            rr = ResultRecord(solr_doc)
            rr.flatten_attributes = self.flatten_attributes
            rr.do_isamples = self.do_isamples
            rr.do_nested_json_attributes = self.do_nested_json_attributes
            rr.add_snippet_content(highlight_dict)

            uuids.append(rr.uuid)

            geo_uuid = get_geo_all_event_source_uuid(solr_doc)
            if geo_uuid == rr.uuid:
                # We only need to add geospatial feature
                # data if the disc_geosource is actually the
                # same item as the result record. Otherwise,
                # we will simply use the item's point data
                # to locate it.
                geo_uuids.append(geo_uuid)

            # Get all the linked data (standards) attributes
            # for this record.
            rec_ld_attributes = get_linked_data_attributes(
                solr_doc
            )
            # Only add those linked data (standards) attributes
            # that meet our limiting criteria.
            rr.ld_attributes = self._limit_attributes_by_request(
                desolr_attribute_tuples_slugs(rec_ld_attributes),
                requested_attrib_slugs,
                all_attribute_val=configs.REQUEST_ALL_LD_ATTRIBUTES
            )

            # Get all of the project-specific predicate attributes
            # for this result record.
            rec_pred_attributes = get_predicate_attributes(
                solr_doc
            )
            # Only add those project-specific predicate attributes
            # to the result record object that meet our limiting
            # criteria.
            rr.pred_attributes = self._limit_attributes_by_request(
                desolr_attribute_tuples_slugs(rec_pred_attributes),
                requested_attrib_slugs,
                all_attribute_val=configs.REQUEST_ALL_PROJ_ATTRIBUTES
            )

            # Add to the list of string predicate uuids gathered
            # from the attributes describing this record.
            string_pred_uuids += get_attribute_tuples_string_pred_uuids(
                rr.pred_attributes
            )


            if self.proj_index and not rr.geometry_coords:
                # We're doing a project index. Allow the data to be on "null island"
                # so it shows up on the search interface.
                rr.latitude = 0.0000000001
                rr.longitude = 0.0000000001
                rr.geo_feature_type = 'Point'
                rr.geometry_coords = [0.0000000001, 0.0000000001,]

            if proj_desc_banner_qs:
                description, banner_url = db_entities.get_desc_and_banner_url_by_slug(
                    proj_desc_banner_qs,
                    slug=rr.slug
                )
                if description:
                    rr.description = description
                if banner_url:
                    rr.hero_banner_src = banner_url
            # Add the result record object to the list of records.
            records.append(rr)


        # Setup configuration for doing DB queries for string
        # attributes
        self._set_strings_db_query_config(requested_attrib_slugs)

        # Remove the duplicates.
        string_pred_uuids = list(set(string_pred_uuids))

        # Make a query to get a dict associating record uuids, string
        # predicate uuids, and their string content.
        uuid_pred_str_dict = self._get_string_attribute_values(
            uuids,
            string_pred_uuids
        )
        if uuid_pred_str_dict:
            # We already have uuid_pred_str_dict data, so don't
            # get it from the database.
            self.do_missing_strings_db_query = False

        # Make a dict with string attribute data pulled from the database,
        # if required.
        db_uuid_pred_str_dict = self.make_db_uuid_pred_str_dict(
            uuids,
            requested_attrib_slugs,
        )

        # Make a query to get any non-point geospatial feature data
        # associated with these result records.
        uuid_geo_dict = event_utilities.make_cache_spacetime_obj_dict(geo_uuids)

        for rr in records:
            rr.add_string_content(uuid_pred_str_dict)
            rr.add_db_string_content(db_uuid_pred_str_dict)
            rr.add_non_point_geojson_coordinates(uuid_geo_dict)

        return records


    def make_uri_meta_records_from_solr(self, solr_json):
        """Makes uri + metadata records from a solr result"""
        # NOTE: This is basically the properties object of a GeoJSON
        # record, but pulled out of the GeoJSON. It helps get
        records = self.make_records_from_solr(solr_json)
        meta_result_records = []
        for i, rr in enumerate(records, 1):
            properties = rr.make_client_properties_dict(
                add_lat_lon=True,
                add_descriptiveness=self.proj_index,
                add_slug=self.proj_index,
            )
            meta_result_records.append(properties)
        return meta_result_records


    def update_no_geo_record_dict(self, no_geo_dict):
        """Updates a dictionary that looks like a GeoJSON
        result dict to change into a result record that
        is not geospatial
        """
        remove_keys = [
            'geometry',
            'type',
        ]
        for rem_key in remove_keys:
            if no_geo_dict.get(rem_key):
                no_geo_dict.pop(rem_key)
        no_geo_dict['category'] = 'oc-api:no-geo-record'
        return no_geo_dict


    def make_geojson_records_from_solr(self, solr_json):
        """Makes geojson records from a solr result"""
        records = self.make_records_from_solr(solr_json)
        features = []
        non_geo_records = []
        for i, rr in enumerate(records, 1):
            geojson = rr.make_geojson(
                record_index= i + self.start,
                total_found=self.total_found
            )
            if not geojson.get('geometry', {}).get('type'):
                # Missing geometry data, so add to the
                # list of non-geojson records.
                no_geo_dict = self.update_no_geo_record_dict(geojson)
                non_geo_records.append(no_geo_dict)
                continue
            features.append(geojson)
        return features, non_geo_records
