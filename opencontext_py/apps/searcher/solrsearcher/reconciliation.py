import re
import datetime
import operator
from django.conf import settings
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.libs.memorycache import MemoryCache
from opencontext_py.apps.entities.entity.models import Entity
from opencontext_py.apps.ldata.linkannotations.equivalence import LinkEquivalence
from opencontext_py.apps.ldata.linkannotations.recursion import LinkRecursion
from opencontext_py.apps.indexer.solrdocument import SolrDocument
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.searcher.solrsearcher.querymaker import QueryMaker

class Reconciliation():
    """ Methods to transform normal JSON results
        into a ranked reconcilation result
    """

    def __init__(self):
        self.geojson_ld = False
        self.raw_related_labels = {}
        self.m_cache = MemoryCache()  # memory caching object

    def process(self, request_dict, geojson_ld):
        """ checks to see if we need to
            convert a geojson_ld object
            into a reconciliation object
        """
        output = geojson_ld
        if 'reconcile' in request_dict \
           and 'q' in request_dict:
            search_term = request_dict['q']
            output = self.make_reconcilation_json(search_term,
                                                  geojson_ld)
        return output

    def make_reconcilation_json(self, search_term, geojson_ld):
        """ takes the geojson_ld and
            makes a reconcilation json
            output
        """
        recon_json = False
        if isinstance(geojson_ld, dict):
            self.geojson_ld = geojson_ld
            recon_json = []
            if 'oc-api:has-facets' in geojson_ld:
                facets = geojson_ld['oc-api:has-facets']
                for facet in facets:
                    if 'oc-api:has-id-options' in facet:
                        max_count = 0
                        for facet_value in facet['oc-api:has-id-options']:
                            if facet_value['count'] > max_count:
                                max_count = facet_value['count']
                        id_ranks = {}
                        for facet_value in facet['oc-api:has-id-options']:
                            id_uri = facet_value['rdfs:isDefinedBy']
                            children = LinkRecursion().get_entity_children(id_uri)
                            if len(children) > 0:
                                levels = len(lr.child_entities) + 1
                            else:
                                levels = 1
                            # calculate a ranking for items, with more specific (fewer children)
                            # categories ranked higher
                            rank = (facet_value['count'] / levels) / max_count
                            match_count = self.count_label_matches(search_term, id_uri)
                            rank = rank + (match_count / levels)
                            id_ranks[id_uri] = rank
                        sorted_ids = sorted(id_ranks.items(), key=operator.itemgetter(1), reverse=True)
                        for id_key, rank in sorted_ids:
                            if len(recon_json) < 5:
                                for facet_value in facet['oc-api:has-id-options']:
                                    if facet_value['rdfs:isDefinedBy'] == id_key:
                                        rank_item =LastUpdatedOrderedDict()
                                        rank_item['id'] = id_key
                                        rank_item['label'] = facet_value['label']
                                        rank_item['rank'] = rank
                                        rank_item['related-labels'] = self.get_related_labels(id_key, True)
                                        recon_json.append(rank_item)
                                        break
                            else:
                                break
        return recon_json
    
    def count_label_matches(self, search_term, uri):
        """ Counts the number of exact search term matches """
        match_count = 0
        lower_s_term = search_term.lower()
        lower_s_term = lower_s_term.strip()
        s_term_len = len(lower_s_term)
        raw_labels = self.get_related_labels(uri)
        for label in raw_labels:
            lower_label = label.lower()
            label_len = len(lower_label)
            if lower_s_term == lower_label:
                match_count += s_term_len
            elif lower_s_term in lower_label:
                match_count += (s_term_len / label_len) * .1  
        return match_count
    
    def get_related_labels(self, uri, unique=False):
        """ gets labels for related URIs """
        if uri not in self.raw_related_labels:
            le = LinkEquivalence()
            equiv_uuids = le.get_from_object(uri)
            self.raw_related_labels[uri] = []
            for uuid in equiv_uuids:
                try:
                    man_obj = Manifest.objects.get(uuid=uuid)
                except Manifest.DoesNotExist:
                    man_obj = False
                if man_obj is not False:
                    self.raw_related_labels[uri].append(man_obj.label)
        output = self.raw_related_labels[uri]
        if unique:
            output = []
            for label in self.raw_related_labels[uri]:
                if label not in output:
                    output.append(label)
        return output