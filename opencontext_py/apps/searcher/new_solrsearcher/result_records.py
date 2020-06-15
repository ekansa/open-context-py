import copy
import json
import logging
import lxml.html

from django.conf import settings
from django.db.models import Subquery, Q, OuterRef
from django.utils.html import strip_tags

from opencontext_py.libs.isoyears import ISOyears
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.libs.rootpath import RootPath
from opencontext_py.libs.validategeojson import ValidateGeoJson

from opencontext_py.apps.entities.uri.models import URImanagement

from opencontext_py.apps.ocitems.assertions.models import Assertion
from opencontext_py.apps.ocitems.geospace.models import Geospace
from opencontext_py.apps.ocitems.mediafiles.models import Mediafile
from opencontext_py.apps.ocitems.strings.models import OCstring

from opencontext_py.apps.indexer.solrdocumentnew import SolrDocumentNew as SolrDocument

from opencontext_py.apps.searcher.new_solrsearcher import configs
from opencontext_py.apps.searcher.new_solrsearcher.searchlinks import SearchLinks
from opencontext_py.apps.searcher.new_solrsearcher import utilities


logger = logging.getLogger(__name__)


PRED_ID_FIELD_SUFFIX = (
    SolrDocument.SOLR_VALUE_DELIM 
    + SolrDocument.FIELD_SUFFIX_PREDICATE
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
        # No heirarchic entities, return an empty list.
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
    specific_predicate_dict
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
    slug_prefix = parent_dict['slug'] + SolrDocument.SOLR_VALUE_DELIM
    specific_pred_field_part = (
        SolrDocument.SOLR_VALUE_DELIM
        + specific_predicate_dict['slug']
        + SolrDocument.SOLR_VALUE_DELIM
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
    root_key=SolrDocument.ROOT_PREDICATE_SOLR
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
        root_key=SolrDocument.ROOT_LINK_DATA_SOLR
    )


def get_geo_discovery_source_uuid(solr_doc):
    """Gets the uuid for a discovery geo source item"""

    # NOTE: A 'discovery geo source' is the item with non-point 
    # geo spatial feature data. A give record may have its own
    # geo spatial feature data, or it may be contained within 
    # another item that has such data. This method gets the
    # UUID for non-point geospatial feature data that associated
    # with this item or other items that may contain it.

    disc_source_str = solr_doc.get('disc_geosource')
    if not disc_source_str:
        return None
    
    disc_source_dict = utilities.parse_solr_encoded_entity_str(
        disc_source_str,
        solr_slug_format=False,
    )
    if not disc_source_dict:
        return None
    
    uuid = get_uuid_from_entity_dict(
        disc_source_dict,
        data_type_limit='id',
        item_type_limit='subjects'
    )
    return uuid


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
        self.latitude = None
        self.longitude = None
        self.geo_feature_type = 'Point'  # Default to point.
        self.geometry_coords = None  # GeoJSON geometry coordinates
        self.early_date = None
        self.late_date = None
        self.thumbnail_href = None
        self.thumbnail_uri = None
        self.thumbnail_scr = None
        self.preview_scr = None
        self.fullfile_scr = None
        self.snippet = None
        self.cite_uri = None  # stable identifier as an HTTP uri

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

        # Skip out if we don't have a solr_doc
        if not solr_doc:
            return None

        # Populate some initial metadata on creation
        self.set_record_basic_metadata(solr_doc)
        self.set_record_category(solr_doc)
        self.set_record_contexts(solr_doc)
        self.set_record_projects(solr_doc)
        self.set_geo_point_attributes(solr_doc)
        self.set_chrono_ranges(solr_doc)


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
        item_type_output = URImanagement.get_uuid_from_oc_uri(self.uri, True)
        self.item_type = item_type_output['item_type']
        self.label = item_dict.get('label')
        self.slug = item_dict.get('slug')
    
    def set_record_category(self, solr_doc):
        """Sets the record category"""
        if not self.item_type:
            item_type_list = solr_doc.get('item_type')
            if not item_type_list:
                logger.warn('Cannot find an item type for this record')
                return None
            self.item_type = item_type_list[0]

        root_cat_field = 'obj_all___oc_gen_{}___pred_id'.format(
            self.item_type
        )
        categories = get_simple_hierarchy_items(
            solr_doc,
            root_cat_field
        )
        if not categories:
            return None
        self.category = categories[-1]
    
    def set_record_contexts(self, solr_doc):
        """Sets the records spatial contexts list"""
        self.contexts = get_simple_hierarchy_items(
            solr_doc,
            SolrDocument.ALL_CONTEXT_SOLR
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
        # Set the context label from all the labels in the
        # context list.
        context_labels = [
            c['label'] for c in self.contexts if c.get('label')
        ]
        self.context_label = '/'.join(context_labels)
    
    def set_record_projects(self, solr_doc):
        """Sets the records projects list"""
        self.projects = get_simple_hierarchy_items(
            solr_doc,
            SolrDocument.ALL_PROJECT_SOLR
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
        disc_geo = solr_doc.get('discovery_geolocation')
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
        dates = solr_doc.get('form_use_life_chrono_earliest', [])
        dates += solr_doc.get('form_use_life_chrono_latest', [])
        if not len(dates):
            return None
        self.early_date = min(dates)
        self.late_date = max(dates)
    

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


    def add_non_point_geojson_coordinates(self, uuid_geo_dict):
        """Adds non-point geojson coordinates to the result"""
        geo_obj =  uuid_geo_dict.get(self.uuid)
        if not geo_obj:
            return None

        self.geo_feature_type = geo_obj.ftype
        coord_obj = json.loads(geo_obj.coordinates)
        v_geojson = ValidateGeoJson()
        coord_obj = v_geojson.fix_geometry_rings_dir(
            geo_obj.ftype,
            coord_obj
        )
        self.geometry_coords = coord_obj
    

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
        ):
        """Makes a properties dict to return to a client
        
        :param str id_value: A string value for an id
            key. This is mainly useful for JSON-LD outputs
            where nodes should have identifiers.
        """
        properties = LastUpdatedOrderedDict()
        if id_value:
            properties['id'] = id_value
        if feature_type:
            properties['feature-type'] = feature_type
        properties['uri'] = self.uri
        properties['href'] = self.href
        properties['citation uri'] = self.cite_uri
        properties['label'] = self.label
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
            properties['item category'] = self.category['label']
        if self.snippet:
            properties['snippet'] = self.snippet
        

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
        geo_json['id'] = '#record-{}-of-{}'.format(
            record_index, 
            total_found
        )
        geo_json['label'] = self.label
        geo_json['rdfs:isDefinedBy'] = self.uri
        geo_json['type'] = 'Feature'
        geo_json['category'] = 'oc-api:geo-record'

        geometry = LastUpdatedOrderedDict()
        geometry['id'] = '#record-geom-{}-of-{}'.format(
            record_index, 
            total_found
        )
        geometry['type'] = self.geo_feature_type
        geometry['coordinates'] = self.geometry_coords
        geo_json['geometry'] = geometry

        if (self.early_date is not None 
            and self.late_date is not None):
            # If we have dates, add them.
            when = LastUpdatedOrderedDict()
            when['id'] = '#record-event-{}-of-{}'.format(
                record_index, 
                total_found
            )
            when['type'] = 'oc-gen:formation-use-life'
            # convert numeric to GeoJSON-LD ISO 8601
            when['start'] = ISOyears().make_iso_from_float(
                self.early_date
            )
            when['stop'] = ISOyears().make_iso_from_float(
                self.late_date
            )
            geo_json['when'] = when

        # Now add the properties dict to the GeoJSON
        props_id_value = '#rec-{}-of-{}'.format(
            record_index, 
            total_found
        )
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

    def __init__(self, request_dict, total_found=0, start=0):
        rp = RootPath()
        self.request_dict = copy.deepcopy(request_dict)
        self.base_url = rp.get_baseurl()
        self.total_found = total_found
        self.start = start
        
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
            # delimiters, so split these appart to get a list of
            # slugs.
            paths_as_lists = utilities.infer_multiple_or_hierarchy_paths(
                raw_prop_path,
                hierarchy_delim=configs.REQUEST_PROP_HIERARCHY_DELIM,
                or_delim=configs.REQUEST_OR_OPERATOR
            )
            for path_list in paths_as_lists:
                # Add the elements of this list to the list
                # of requested_attrib_slugs. Some of these won't be
                # 'property' (predicate) attributes, but that doesn't
                # matter. It's OK to have some noise in the
                # requested_attrib_slugs.
                requested_attrib_slugs += path_list
        
        # De-duplicate the slugs in the requested_attrib_slugs.
        requested_attrib_slugs = list(set(requested_attrib_slugs))

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
        str_qs = OCstring.objects.filter(
            uuid=OuterRef('object_uuid')
        ).values('content')

        ass_qs = Assertion.objects.filter(
            uuid__in=uuids,
            predicate_uuid__in=string_pred_uuids,
        ).exclude(
            visibility__lt=1
        ).order_by(
            'uuid', 
            'predicate_uuid', 
            'sort'
        ).annotate(
            str_content=Subquery(
                str_qs
            )
        )
        output = {}
        for a in ass_qs:
            if not a.uuid in output:
                output[a.uuid] = {}
            if not a.predicate_uuid in output[a.uuid]:
                output[a.uuid][a.predicate_uuid] = []
            output[a.uuid][a.predicate_uuid].append(
                a.str_content
            )
        return output
    

    def _get_geo_features_objs(self, uuids):
        """Get non-point geospatial features from the database

        :param list uuids: List of UUIDs for the solr documents in the
            results that may have geospatial features.
        """

        # NOTE: We query the list of multiple uuids in 1 query to
        # limit the number of queries we make on the database.

        uuid_geo_dict = {}
        if not len(uuids):
            return uuid_geo_dict

        geospace_qs = Geospace.objects.filter(
            uuid__in=uuids,
        ).exclude(
            ftype__in=['Point', 'point']
        ).order_by('uuid', '-feature_id')
        for geo_obj in geospace_qs:
            uuid_geo_dict[geo_obj.uuid] = geo_obj

        return uuid_geo_dict


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
            rr.add_snippet_content(highlight_dict)

            uuids.append(rr.uuid)

            geo_uuid = get_geo_discovery_source_uuid(solr_doc)
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

            # Add the result record object to the list of records.
            records.append(rr)

        # Remove the duplicates.
        string_pred_uuids = list(set(string_pred_uuids))
        
        # Make a query to get a dict associating record uuids, string
        # predicate uuids, and their string content. 
        uuid_pred_str_dict = self._get_string_attribute_values(
            uuids, 
            string_pred_uuids
        )

        # Make a query to get any non-point geospatial feature data
        # associated with these result records.
        uuid_geo_dict = self._get_geo_features_objs(geo_uuids)

        for rr in records:
            rr.add_string_content(uuid_pred_str_dict)
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
                add_lat_lon=True
            )
            meta_result_records.append(properties)
        return meta_result_records


    def make_geojson_records_from_solr(self, solr_json):
        """Makes geojson records from a solr result"""
        records = self.make_records_from_solr(solr_json)
        features = []
        for i, rr in enumerate(records, 1):
            geojson = rr.make_geojson(
                record_index= i + self.start, 
                total_found=self.total_found
            )
            features.append(geojson)
        return features
