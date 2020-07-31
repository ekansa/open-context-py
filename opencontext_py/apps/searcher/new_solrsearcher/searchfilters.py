import copy
import json
from urllib.parse import urlparse, parse_qs
from django.utils.http import (
    urlquote, 
    quote_plus, 
    urlquote_plus, 
    urlunquote_plus,
)
from django.utils.encoding import iri_to_uri

from django.conf import settings

from opencontext_py.libs.memorycache import MemoryCache
from opencontext_py.libs.rootpath import RootPath
from opencontext_py.libs.general import LastUpdatedOrderedDict, DCterms
from opencontext_py.libs.chronotiles import ChronoTile
from opencontext_py.libs.globalmaptiles import GlobalMercator

from opencontext_py.apps.indexer.solrdocumentnew import SolrDocumentNew as SolrDocument

from opencontext_py.apps.searcher.new_solrsearcher import configs
from opencontext_py.apps.searcher.new_solrsearcher import utilities
from opencontext_py.apps.searcher.new_solrsearcher.searchlinks import SearchLinks


def make_geotile_filter_label(raw_geotile):
    """Parses a raw bbox parameter value to make a filter label
    """
    if configs.REQUEST_OR_OPERATOR in raw_geotile:
        tile_list = raw_geotile.split(configs.REQUEST_OR_OPERATOR)
    else:
        tile_list = [raw_geotile]

    output_list = []
    for tile in tile_list:
        geotile = GlobalMercator()
        coordinates = geotile.quadtree_to_lat_lon(tile)
        if not coordinates:
            label = '[Ignored invalid geospatial tile]'
        else:
            round_level = utilities.estimate_good_coordinate_rounding(
                lon_a=coordinates[0], 
                lat_a=coordinates[1], 
                lon_b=coordinates[2], 
                lat_b=coordinates[3],
            )
            label = 'In the region bounded by: {}, {} (SW) and {}, {} (NE)'.format(
                round(coordinates[0], round_level),
                round(coordinates[1], round_level),
                round(coordinates[2], round_level),
                round(coordinates[3], round_level),
            )
        output_list.append(label)
    output = '; or '.join(output_list)
    return output


def make_bbox_filter_label(raw_disc_bbox):
    """Parses a raw bbox parameter value to make a filter label
    """
    if configs.REQUEST_OR_OPERATOR in raw_disc_bbox:
        bbox_list = raw_disc_bbox.split(configs.REQUEST_OR_OPERATOR)
    else:
        bbox_list = [raw_disc_bbox]
    
    output_list = []
    for bbox_str in bbox_list:
        bbox_coors = utilities.return_validated_bbox_coords(
            bbox_str
        )
        if not bbox_coors:
            output_list.append('[Ignored invalid bounding-box]')
            continue
        round_level = utilities.estimate_good_coordinate_rounding(
            lon_a=bbox_coors[0], 
            lat_a=bbox_coors[1], 
            lon_b=bbox_coors[2], 
            lat_b=bbox_coors[3],
        )
        label = 'In the bounding-box of: Latitude {}, Longitude {} (SW)'.format(
            round(bbox_coors[1], round_level),
            round(bbox_coors[0], round_level),
        )
        label += ' and Latitude {}, Longitude {} (NE)'.format(
            round(bbox_coors[3], round_level),
            round(bbox_coors[2], round_level),
        )
        output_list.append(label)

    output = '; or '.join(output_list)
    return output


class SearchFilters():

    def __init__(
        self, 
        request_dict=None, 
        current_filters_url=None, 
        base_search_url='/search/'
    ):
        rp = RootPath()
        self.base_url = rp.get_baseurl()
        self.base_search_url = base_search_url
        self.request_dict = copy.deepcopy(request_dict)
        self.current_filters_url = current_filters_url
        self.doc_formats = configs.REQUEST_URL_FORMAT_EXTENTIONS


    def add_links_to_act_filter(
        self,
        param_key, 
        match_old_value,
        new_value,
        act_filter, 
        request_dict,
        make_text_template=False,
    ):
        """Adds links to an active filter"""
        act_request_dict = copy.deepcopy(request_dict)

        sl = SearchLinks(
            request_dict=act_request_dict,
            base_search_url=self.base_search_url
        )

        # Remove non search related params.
        sl.remove_non_query_params()
        
        sl.replace_param_value(
            param_key,
            match_old_value=match_old_value,
            new_value=new_value,
        ) 
        urls = sl.make_urls_from_request_dict()
        if make_text_template:
            # Make template for a text search
            act_filter['oc-api:template'] = urls['html']
            act_filter['oc-api:template-json'] = urls['json']
            return act_filter
        if urls['html'] == self.current_filters_url:
            # The urls don't actually change state, so don't
            # add new remove or broaden links, and skip out.
            return act_filter
        if new_value is None:
            # If the new_value is None, then we're completely
            # removing the search filter.
            act_filter['oc-api:remove'] = urls['html']
            act_filter['oc-api:remove-json'] = urls['json']
        else:
            # Make links to broaden a filter to a higher
            # point in a given filter's hierarchy
            act_filter['oc-api:broaden'] = urls['html']
            act_filter['oc-api:broaden-json'] = urls['json']
        return act_filter


    def add_non_hierarchy_filter_json(
        self,
        param_key,
        act_val,
        act_filter,
        param_config, 
        request_dict,
    ):
        """Adds JSON for non-hierarchy filters.
        
        :param str param_key: Client request query parameter
        :param str act_val: URL unquoted client request 
            search value
        :param dict act_filter: Dictionary describing the
            search filter associated with the param_key 
            and act_val.
        :param dict param_config: Configuration dictionary 
            for translating the param_key and act_val into
            an act_filter.
        :param dict request_dict: Dictionary object of the GET
            request from the client. 
        """

        if param_config.get('label'):
            act_filter['label'] = param_config['label']
        elif param_config.get('label-template'):
            act_filter['label'] = param_config['label-template'].format(
                act_val=act_val    
            )
        
        if param_key in ['form-start', 'form-stop']:
            # Case for filters on years.
            act_date = utilities.string_to_int(act_val)
            if act_date is None:
                act_filter['label'] = 'Invalid year. Must be integer value'
            elif act_date < 0:
                act_filter['label'] = '{} BCE'.format(act_date)
            else:
                act_filter['label'] = '{} CE'.format(act_date) 
       
        elif param_key == 'form-chronotile':
            chrono = ChronoTile()
            dates = chrono.decode_path_dates(act_val)
            if isinstance(dates, dict):
                act_filter['label'] = 'Time range: {} to {}'.format(
                    dates['earliest_bce'],
                    dates['latest_bce'],
                )
            else:
                act_filter['label'] = 'Invalid chronology encoding'

        elif param_key == 'disc-geotile':
            act_filter['label'] = make_geotile_filter_label(
                act_val
            )
        
        elif param_key == 'disc-bbox':
            act_filter['label'] = make_bbox_filter_label(
                act_val
            )

        # Add the removal links.
        act_filter = self.add_links_to_act_filter(
            param_key, 
            match_old_value=None,
            new_value=None,
            act_filter=act_filter, 
            request_dict=request_dict,
        )
        return act_filter


    def add_entity_item_to_act_filter(
            self, 
            lookup_val, 
            act_filter, 
            is_spatial_context=False,
            look_up_mapping_dict=None,
        ):
        """Looks up a entity item to add to an act_filter"""
        lookup_val = str(lookup_val)
    
        if lookup_val.startswith(configs.RELATED_ENTITY_ID_PREFIX):
            # Strip off the related property prefix. Note that this
            # is a related property.
            lookup_val = lookup_val[len(configs.RELATED_ENTITY_ID_PREFIX):]
            act_filter['oc-api:related-property'] = True

        # Map the lookup_val to a mapping dict
        if look_up_mapping_dict:
            lookup_val = look_up_mapping_dict.get(
                lookup_val, 
                lookup_val
            )

        m_cache = MemoryCache()
        items = []
        if configs.REQUEST_OR_OPERATOR in lookup_val:
            lookup_list = lookup_val.split(
                configs.REQUEST_OR_OPERATOR
            )
        else:
            lookup_list = [lookup_val]
        
        for act_val in lookup_list:
            if is_spatial_context:
                item = m_cache.get_entity_by_context(act_val)
            else:
                item = m_cache.get_entity(act_val)
            if not item:
                continue
            items.append(item)
        
        if not len(items):
            # We didn't find any item entities, so return
            # the lookup list as the label.
            act_filter['label'] = ' OR '.join(lookup_list)
            return act_filter, None
        
        # Use all the item labels to make a label.
        item_labels = [item.label for item in items]   
        act_filter['label'] = ' OR '.join(item_labels)

        if len(items) == 1:
            # We only have 1 item, so define it with a
            # URI and slug.
            act_filter['rdfs:isDefinedBy'] = items[0].uri
            act_filter['oc-api:filter-slug'] = items[0].slug
        
        return act_filter, item

    
    def add_filters_json(self, request_dict):
        """Adds JSON describing active search filters.
        
        :param dict request_dict: Dictionary object of the GET
            request from the client.
        """

        # NOTE: This function creates a list of the filters that
        # the client requested in their search / query.
        # Each of the listed filters has some metadata and
        # links to remove the filter or broaden the filter,
        # in case there are multiple levels of hierarchy in a
        # given filter.

        filters = []
        string_fields = []  # so we have an interface for string searches

        for param_key, param_vals in request_dict.items():
            if param_vals is None:
                continue
            if param_key in configs.FILTER_IGNORE_PARAMS:
                continue
            
            # Normalize the values of this parameter into a
            # list to make processing easier
            if not isinstance(param_vals, list):
                param_vals = [param_vals]

            # Get the configuration for this specific request
            # parameter.
            param_config = configs.FILTER_PARAM_CONFIGS.get(
                param_key
            )
            if not param_config:
                # No configuration for this request parameter
                continue

            # Get the hierarchy delimiter configured 
            # for values used by this param_key.
            hierarchy_delim = param_config.get('hierarchy_delim')
            
            for param_val in param_vals:
                
                if (hierarchy_delim and hierarchy_delim in param_val):
                    # NOTE: Sometimes we may get a param_val that
                    # has a trailing hierarchy delim. This will result in weird
                    # behavior. So we make a splitting_param_val that trims
                    # off any trailing delimiter.
                    splitting_param_val = param_val.lstrip(hierarchy_delim)
                    splitting_param_val = splitting_param_val.rstrip(hierarchy_delim)
                    hierarchy_vals = splitting_param_val.split(hierarchy_delim)
                else:
                    hierarchy_vals = [param_val]
                
                parent_path_vals = []
                
                # This gets set in the event that we have a
                # property with a string data type. It is used to make
                # a search template for that string.
                text_template_value = None

                for act_val in hierarchy_vals:
                    act_val = urlunquote_plus(act_val)
                    parent_path_vals.append(act_val)
                    if hierarchy_delim:
                        act_full_path = hierarchy_delim.join(
                            parent_path_vals
                        )
                    else:
                        act_full_path = act_val
                    
                    # Count the existing filters to make the 
                    # index of the next one.
                    i = len(filters) + 1

                    act_filter = LastUpdatedOrderedDict()
                    act_filter['id'] = '#filter-{}'.format(i)
                    act_filter['oc-api:filter'] = param_config['oc-api:filter']
                    
                    if hierarchy_delim is None:
                        # Do one of the many special case non-hierarchic
                        # filter parameters.
                        act_filter = self.add_non_hierarchy_filter_json(
                            param_key,
                            act_val,
                            act_filter,
                            param_config, 
                            request_dict,
                        )
                        filters.append(act_filter)
                        # Skip everything in this loop below, because
                        # below we're doing things related to entities that
                        # may be in a hierarchy.
                        continue


                    # The filter-group helps to group together all of the
                    # levels of the hierarchy_vals.
                    act_filter['oc-api:filter-group'] = param_val
                    
                    if param_key == "path":
                        # Look up item entity for spatial context
                        # path items by the current path, which will
                        # include the hierarchy of parent items.
                        item_lookup_val = act_full_path
                    else:
                        # Look up the item entity simply by using
                        # the current act_val.
                        item_lookup_val = act_val
                    
                    if text_template_value is None:
                        # Do not do this for the string value of a string
                        # type property
                        act_filter, item = self.add_entity_item_to_act_filter(
                            item_lookup_val,
                            act_filter,
                            is_spatial_context=param_config.get(
                                'is_spatial_context', 
                                False
                            ),
                            look_up_mapping_dict=param_config.get(
                                'look_up_mapping_dict'
                            ),
                        )
                        if item and getattr(item, 'data_type') == 'xsd:string':
                            act_search_term = None
                            text_template_value = (
                                act_full_path 
                                + hierarchy_delim 
                                + configs.URL_TEXT_QUERY_TEMPLATE
                            )
                    else:
                        # This is the a case of a search term, which is the child
                        # of a descriptive property of data_type xsd:string.
                        act_search_term = item_lookup_val
                        act_filter['label'] = item_lookup_val
                        if param_config.get('label-prop-template'):
                            # Use a configured tem
                            act_filter['label'] = param_config['label-prop-template'].format(
                                act_val=item_lookup_val
                            )

                    # Add text field templates
                    if text_template_value is not None:
                        # Add some special keys and values relating to text
                        # searches.
                        act_filter["oc-api:search-term"] = act_search_term
                        act_filter = self.add_links_to_act_filter(
                            param_key, 
                            match_old_value=param_val,
                            new_value=text_template_value,
                            act_filter=act_filter, 
                            request_dict=request_dict,
                            make_text_template=True,
                        )

                    # Add the totally remove filter links
                    act_filter = self.add_links_to_act_filter(
                        param_key, 
                        match_old_value=param_val,
                        new_value=None,
                        act_filter=act_filter, 
                        request_dict=request_dict,
                    )

                    if len(parent_path_vals) < len(hierarchy_vals):
                        # We can add links to broaden this current
                        # filter to a higher level in the hierarchy.
                        act_filter = self.add_links_to_act_filter(
                            param_key, 
                            match_old_value=param_val,
                            new_value=act_full_path,
                            act_filter=act_filter, 
                            request_dict=request_dict,
                        )

                    filters.append(act_filter)
                    
        return filters
