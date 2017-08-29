import json
from django.conf import settings
from opencontext_py.libs.solrconnection import SolrConnection
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.apps.indexer.solrdocument import SolrDocument
from opencontext_py.apps.ocitems.projects.models import Project


class ProjectsQuery():

    """ Methods to get projects from solr to see if we need
            to have project facet fields.
            
        If we have 1 project, then we need to show facet fields for project
        specific descriptive properties.
        
    """

    def __init__(self):
        self.solr = False
        self.solr_connect()

    def solr_connect(self):
        """ connects to solr """
        self.solr = SolrConnection(False).connection

    def check_single_project(self, query):
        """ checks to see if the query results only in a single project.
            If it does, then we need to show facet fields for project
            specific descriptive properties
        """
        single_project = False
        projs_query = self.compose_query(query)  # make the stats query
        response = self.solr.search(**projs_query)  # execute solr query
        solr_json = response.raw_content
        if isinstance(solr_json, dict):
            if 'facet_counts' in solr_json:
                if 'facet_fields' in solr_json['facet_counts']:
                    ff_dict = solr_json['facet_counts']['facet_fields']
                    if SolrDocument.ROOT_PROJECT_SOLR in ff_dict:
                        proj_list = ff_dict[SolrDocument.ROOT_PROJECT_SOLR]
                        num_projects = 0
                        last_proj_val = None
                        for proj_val in solr_json['facet_counts']['facet_fields'][SolrDocument.ROOT_PROJECT_SOLR]:
                            if isinstance(proj_val, str):
                                if '___' in proj_val:
                                    last_proj_val = proj_val
                                    num_projects += 1
                        if num_projects == 1:
                            # we have 1 project, check to make sure it's not a parent of a daughter project
                            proj_ex = last_proj_val.split('___')
                            if len(proj_ex) > 3:
                                # get a uuid from 22-kenan-tepe___id___/projects/3DE4CD9C-259E-4C14-9B03-8B10454BA66E___Kenan Tepe
                                p_uuid = proj_ex[2].replace('/projects/', '')
                                ch_projs = Project.objects\
                                                  .filter(project_uuid=p_uuid)\
                                                  .exclude(uuid=p_uuid)[:1]
                                if len(ch_projs) < 1:
                                    # this project does not have child projects, so it is OK to
                                    # consider a single project
                                    single_project = True
        return single_project

    def compose_query(self, old_query):
        """ composes a query to get a summary of
            projects that will be in shown in an old_query
        """
        query = {}
        if 'q' in old_query:
            query['q'] = old_query['q']
        if 'q.op' in old_query:
            query['q.op'] = old_query['q.op']
        if 'fq' in old_query:
            query['fq'] = old_query['fq']
        query['debugQuery'] = 'false'
        query['facet'] = 'true'
        query['facet.mincount'] = 1
        query['rows'] = 0
        query['start'] = 0
        query['facet.field'] = [SolrDocument.ROOT_PROJECT_SOLR]
        return query
