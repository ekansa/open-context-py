import copy
import json
from urllib.parse import urlparse, parse_qs
from django.utils.http import urlquote, quote_plus, urlquote_plus
from django.utils.encoding import iri_to_uri

from django.conf import settings

from opencontext_py.libs.memorycache import MemoryCache
from opencontext_py.libs.rootpath import RootPath
from opencontext_py.libs.general import LastUpdatedOrderedDict, DCterms

from opencontext_py.apps.indexer.solrdocumentnew import SolrDocumentNew as SolrDocument

from opencontext_py.apps.searcher.new_solrsearcher import configs
from opencontext_py.apps.searcher.new_solrsearcher import utilities



class SearchFilters():

    def __init__(self, request_dict=None, base_search_url='/search/'):
        rp = RootPath()
        self.base_url = rp.get_baseurl()
        self.base_search_url = base_search_url
        self.request_dict = copy.deepcopy(request_dict)
        self.doc_formats = configs.REQUEST_URL_FORMAT_EXTENTIONS
    
    def add_filters_json(self, request_dict):
        """ adds JSON describing search filters """
        filters = []
        string_fields = []  # so we have an interface for string searches
        i = 0
        m_cache = MemoryCache()
        for param_key, param_vals in request_dict.items():
            if param_vals is None:
                continue
            if param_key in configs.FILTER_IGNORE_PARAMS:
                continue
            act_request_dict = copy.deepcopy(request_dict)
            sl = SearchLinks(
                request_dict=act_request_dict,
                base_search_url=self.base_search_url
            )
            if param_key == 'path':
                i = len(filters) + 1
                entity = m_cache.get_entity_by_context(param_vals)
                label = http.urlunquote_plus(param_vals)
                act_filter = LastUpdatedOrderedDict()
                act_filter['id'] = '#filter-{}'.format(i)
                act_filter['oc-api:filter'] = 'Context'
                act_filter['label'] = label.replace('||', ' OR ')
                if entity:
                    act_filter['rdfs:isDefinedBy'] = entity.uri
                # Generate a request dict without the context filter
                sl.replace_param_value('path', new_value=None)
                urls = sl.make_urls_from_request_dict()
                act_filter['oc-api:remove'] = urls['html']
                act_filter['oc-api:remove-json'] = urls['json']
                filters.append(act_filter)
                continue

            if not isinstance(param_vals, list):
                param_vals = [param_vals]
            for param_val in param_vals:
                i = len(filters) + 1
                remove_geodeep = False
                act_filter = LastUpdatedOrderedDict()
                act_filter['id'] = '#filter-{}'.format(i)
                if configs.REQUEST_PROP_HIERARCHY_DELIM in param_val:
                    all_vals = param_val.split(configs.REQUEST_PROP_HIERARCHY_DELIM)
                else:
                    all_vals = [param_val]
                if param_key == 'proj':
                    # projects, only care about the last item in the parameter value
                    act_filter['oc-api:filter'] = 'Project'
                    label_dict = self.make_filter_label_dict(all_vals[-1])
                    act_filter['label'] = label_dict['label']
                    if len(label_dict['entities']) == 1:
                        act_filter['rdfs:isDefinedBy'] = label_dict['entities'][0].uri
                elif param_key == 'prop':
                    # prop, the first item is the filter-label
                    # the last is the filter
                    act_filter['label'] = False
                    if len(all_vals) < 2:
                        act_filter['oc-api:filter'] = 'Description'
                        act_filter['oc-api:filter-slug'] = all_vals[0]
                    else:
                        filt_dict = self.make_filter_label_dict(all_vals[0])
                        act_filter['oc-api:filter'] = filt_dict['label']
                        if 'slug' in filt_dict:
                            act_filter['oc-api:filter-slug'] = filt_dict['slug']
                        if filt_dict['data-type'] == 'string':
                            act_filter['label'] = 'Search Term: \'' + all_vals[-1] + '\''
                    if act_filter['label'] is False:
                        label_dict = self.make_filter_label_dict(all_vals[-1])
                        act_filter['label'] = label_dict['label']
                elif param_key == 'type':
                    act_filter['oc-api:filter'] = 'Open Context Type'
                    if all_vals[0] in QueryMaker.TYPE_MAPPINGS:
                        type_uri = QueryMaker.TYPE_MAPPINGS[all_vals[0]]
                        label_dict = self.make_filter_label_dict(type_uri)
                        act_filter['label'] = label_dict['label']
                    else:
                        act_filter['label'] = all_vals[0]
                elif param_key == 'q':
                    act_filter['oc-api:filter'] = self.TEXT_SEARCH_TITLE
                    act_filter['label'] = 'Search Term: \'' + all_vals[0] + '\''
                elif param_key == 'id':
                    act_filter['oc-api:filter'] = 'Identifier Lookup'
                    act_filter['label'] = 'Identifier: \'' + all_vals[0] + '\''
                elif param_key == 'form-chronotile':
                    act_filter['oc-api:filter'] = 'Time of formation, use, or life'
                    chrono = ChronoTile()
                    dates = chrono.decode_path_dates(all_vals[0])
                    if isinstance(dates, dict):
                        act_filter['label'] = 'Time range: ' + str(dates['earliest_bce'])
                        act_filter['label'] += ' to ' + str(dates['latest_bce'])
                elif param_key == 'form-start':
                    act_filter['oc-api:filter'] = 'Earliest formation, use, or life date'
                    try:
                        val_date = int(float(all_vals[0]))
                    except:
                        val_date = False
                    if val_date is False:
                        act_filter['label'] = '[Invalid year]'
                    elif val_date < 0:
                        act_filter['label'] = str(val_date * -1) + ' BCE'
                    else:
                        act_filter['label'] = str(val_date) + ' CE'
                elif param_key == 'form-stop':
                    act_filter['oc-api:filter'] = 'Latest formation, use, or life date'
                    try:
                        val_date = int(float(all_vals[0]))
                    except:
                        val_date = False
                    if val_date is False:
                        act_filter['label'] = '[Invalid year]'
                    elif val_date < 0:
                        act_filter['label'] = str(val_date * -1) + ' BCE'
                    else:
                        act_filter['label'] = str(val_date) + ' CE'
                elif param_key == 'disc-geotile':
                    act_filter['oc-api:filter'] = 'Location of discovery or observation'
                    act_filter['label'] = self.make_geotile_filter_label(all_vals[0])
                    remove_geodeep = True
                elif param_key == 'disc-bbox':
                    act_filter['oc-api:filter'] = 'Location of discovery or observation'
                    act_filter['label'] = self.make_bbox_filter_label(all_vals[0])
                    remove_geodeep = True
                elif param_key == 'images':
                    act_filter['oc-api:filter'] = 'Has related media'
                    act_filter['label'] = 'Linked to images'
                elif param_key == 'other-media':
                    act_filter['oc-api:filter'] = 'Has related media'
                    act_filter['label'] = 'Linked to media (other than images)'
                elif param_key == 'documents':
                    act_filter['oc-api:filter'] = 'Has related media'
                    act_filter['label'] = 'Linked to documents'
                elif param_key == 'dc-subject':
                    act_filter['oc-api:filter'] = 'Has subject metadata'
                    label_dict = self.make_filter_label_dict(all_vals[-1])
                    if len(label_dict['label']) > 0:
                        act_filter['label'] = label_dict['label']
                    if 'tdar' == all_vals[-1] or 'tdar*' == all_vals[-1]:
                        act_filter['label'] = 'tDAR defined metadata record(s)'
                    if len(label_dict['entities']) == 1:
                        act_filter['rdfs:isDefinedBy'] = label_dict['entities'][0].uri
                        if label_dict['entities'][0].vocabulary is not False:
                            act_filter['label'] += ' in ' + label_dict['entities'][0].vocabulary
                elif param_key == 'dc-spatial':
                    act_filter['oc-api:filter'] = 'Has spatial metadata'
                    label_dict = self.make_filter_label_dict(all_vals[-1])
                    if len(label_dict['label']) > 0:
                        act_filter['label'] = label_dict['label']
                    if len(label_dict['entities']) == 1:
                        act_filter['rdfs:isDefinedBy'] = label_dict['entities'][0].uri
                        if label_dict['entities'][0].vocabulary is not False:
                            act_filter['label'] += ' in ' + label_dict['entities'][0].vocabulary
                elif param_key == 'dc-coverage':
                    act_filter['oc-api:filter'] = 'Has coverage / period metadata'
                    label_dict = self.make_filter_label_dict(all_vals[-1])
                    if len(label_dict['label']) > 0:
                        act_filter['label'] = label_dict['label']
                    if len(label_dict['entities']) == 1:
                        act_filter['rdfs:isDefinedBy'] = label_dict['entities'][0].uri
                        if label_dict['entities'][0].vocabulary is not False:
                            act_filter['label'] += ' in ' + label_dict['entities'][0].vocabulary
                elif param_key == 'dc-temporal':
                    act_filter['oc-api:filter'] = 'Has temporal coverage'
                    label_dict = self.make_filter_label_dict(all_vals[-1])
                    if len(label_dict['label']) > 0:
                        act_filter['label'] = label_dict['label']
                        if len(label_dict['entities']) == 1: 
                            if label_dict['entities'][0].entity_type == 'vocabulary':
                                act_filter['label'] = 'Concepts defined by: ' + label_dict['label']
                        elif 'periodo' in all_vals[-1]:
                            act_filter['label'] = 'PeriodO defined concepts'
                    if len(label_dict['entities']) == 1:
                        act_filter['rdfs:isDefinedBy'] = label_dict['entities'][0].uri
                        if label_dict['entities'][0].vocabulary is not False\
                            and label_dict['entities'][0].vocabulary != label_dict['label']:
                            act_filter['label'] += ' in ' + label_dict['entities'][0].vocabulary
                elif param_key == 'obj':
                    act_filter['oc-api:filter'] = 'Links (in some manner) to object'
                    label_dict = self.make_filter_label_dict(all_vals[-1])
                    if len(label_dict['label']) > 0:
                        act_filter['label'] = label_dict['label']
                    if len(label_dict['entities']) == 1:
                        act_filter['rdfs:isDefinedBy'] = label_dict['entities'][0].uri
                        if label_dict['entities'][0].vocabulary is not False:
                            act_filter['label'] += ' in ' + label_dict['entities'][0].vocabulary
                elif param_key == 'dc-isReferencedBy':
                    act_filter['oc-api:filter'] = 'Is referenced by'
                    label_dict = self.make_filter_label_dict(all_vals[-1])
                    if len(label_dict['label']) > 0:
                        act_filter['label'] = label_dict['label']
                    if len(label_dict['entities']) == 1:
                        act_filter['rdfs:isDefinedBy'] = label_dict['entities'][0].uri
                        if label_dict['entities'][0].vocabulary is not False\
                            and label_dict['entities'][0].vocab_uri != label_dict['entities'][0].uri:
                            act_filter['label'] += ' in ' + label_dict['entities'][0].vocabulary
                elif param_key == 'linked' and all_vals[-1] == 'dinaa-cross-ref':
                    act_filter['oc-api:filter'] = 'Has cross references'
                    act_filter['label'] = 'Links to, or with, DINAA curated site files'
                else:
                    act_filter = False
                if act_filter is not False:
                    rem_request = fl.make_request_sub(request_dict,
                                                        param_key,
                                                        param_val)
                    if 'geodeep' in rem_request and remove_geodeep:
                        rem_request.pop('geodeep', None)    
                    act_filter['oc-api:remove'] = fl.make_request_url(rem_request)
                    act_filter['oc-api:remove-json'] = fl.make_request_url(rem_request, '.json')
                    filters.append(act_filter)
        return filters