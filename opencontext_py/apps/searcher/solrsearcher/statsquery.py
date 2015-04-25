import json
from django.conf import settings
from opencontext_py.libs.solrconnection import SolrConnection
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.apps.searcher.solrsearcher.querymaker import QueryMaker


class StatsQuery():

    """ Methods to get stats information
        for 1 or more fields from Solr.

        This is useful in composing queries for
        numeric range facets where we don't know
        the min or max of the filtered set
    """

    def __init__(self):
        self.solr = False
        self.solr_connect()
        self.solr_response = False
        self.stats_fields = []
        self.q = '*:*'  # main solr query
        self.q_op = 'AND'  # default operator for q terms
        self.fq = []  # filter query

    def solr_connect(self):
        """ connects to solr """
        self.solr = SolrConnection(False).connection

    def add_stats_ranges_from_solr(self, query):
        """ gets solr stats by searching solr
            searches solr to get raw solr search results
        """
        stats_query = self.compose_query()  # make the stats query
        response = self.solr.search(**stats_query)  # execute solr query
        solr_json = response.raw_content
        if isinstance(solr_json, dict):
            if 'stats' in solr_json:
                if 'stats_fields' in solr_json['stats']:
                    qm = QueryMaker()
                    groups = qm.histogram_groups
                    for solr_field_key, stats in solr_json['stats']['stats_fields'].items():
                        if stats is not None:
                            if solr_field_key not in query['facet.range']:
                                query['facet.range'].append(solr_field_key)
                            if solr_field_key not in query['stats.field']:
                                query['stats.field'].append(solr_field_key)
                            fstart = 'f.' + solr_field_key + '.facet.range.start'
                            fend = 'f.' + solr_field_key + '.facet.range.end'
                            fgap = 'f.' + solr_field_key + '.facet.range.gap'
                            findex = 'f.' + solr_field_key + '.facet.sort'
                            fother = 'f.' + solr_field_key + '.facet.range.other'
                            finclude = 'f.' + solr_field_key + '.facet.range.include'
                            query[fother] = 'all'
                            query[finclude] = 'all'
                            if 'count' in stats:
                                if (stats['count'] / qm.histogram_groups) < 3:
                                    groups = 4
                            if '___pred_date' in solr_field_key:
                                query[fstart] = qm.convert_date_to_solr_date(stats['min'])
                                query[fend] = qm.convert_date_to_solr_date(stats['max'])
                                query[fgap] = qm.get_date_difference_for_solr(stats['min'], stats['max'], groups)
                                query[findex] = 'index'  # sort by index, not by count
                            else:
                                query[fstart] = stats['min']
                                query[fend] = stats['max']
                                query[fgap] = ((stats['max'] - stats['min']) / groups)
                                if query[fgap] > stats['mean']:
                                    query[fgap] = stats['mean'] / 3;
                                # query[fgap] = ((stats['max'] - stats['min']) / groups) - ((stats['max'] - stats['min']) / groups) * .01
                                query[findex] = 'index'  # sort by index, not by count
        return query

    def compose_query(self):
        """ composes a stats query
            using attributes in this class
        """
        query = {}
        query['debugQuery'] = 'false'
        query['stats'] = 'true'
        query['rows'] = 0
        query['q'] = self.q
        query['fq'] = self.fq
        query['stats.field'] = self.stats_fields
        return query
