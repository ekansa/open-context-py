import time
from rdflib import Graph, URIRef, Literal, Namespace
from rdflib.namespace import RDF, RDFS, SKOS, OWL
from django.conf import settings
from opencontext_py.libs.languages import Languages
from opencontext_py.apps.entities.uri.models import URImanagement
from opencontext_py.apps.entities.entity.models import Entity
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.ocitems.projects.models import Project
from opencontext_py.apps.ldata.pelagios.graph import PelagiosGraph
from opencontext_py.apps.ocitems.projects.permissions import ProjectPermissions


class PelagiosProjects():
    """ Calls the database to collect data needed
        to make a Pelagios compliant VOID file
        describing datasets in Open Context
        
        Also used to pre-cache database records
        of Pelagios annotations
        
from opencontext_py.apps.ldata.pelagios.projects import PelagiosProjects
p_projs = PelagiosProjects()
p_projs.cache_all_graphs()
p_projs.cache_project_graph('ab9b84d5-ae8a-4d5b-8e45-9f3d260723b1')
    """

    def __init__(self):
        # list of dictionary items that combine project + manifest obj
        self.man_proj_objs = []
        self.request = False
    
    def cache_all_graphs(self, refresh=True):
        """ caches pelagios graph data for all public projects """
        self.get_projects()
        for proj_dict in self.man_proj_objs:
            man = proj_dict['man']
            print('Caching: ' + man.slug)
            self.cache_project_graph(man.uuid, refresh)
       
    def cache_project_graph(self, project_uuid, refresh=True):
        """ caches pelagios graph data for a specific project """
        pelagios = PelagiosGraph()
        pelagios.refresh_cache = refresh
        pelagios.project_uuids = [project_uuid]
        pelagios.get_graph()
     
    def get_projects(self):
        """ gets the manfest and project objects needed to make the void """
        man_objs = Manifest.objects\
                           .filter(item_type='projects')
        for man_obj in man_objs:
            proj_obj = False
            permitted = self.check_view_permission(man_obj.uuid)
            if permitted:
                # only try to get project information if the view is permitted
                try:
                    proj_obj = Project.objects.get(uuid=man_obj.uuid)
                except Project.DoesNotExist:
                    proj_obj = False
            if proj_obj is not False:
                proj_dict = {'man': man_obj,
                             'proj': proj_obj}
                # kludge: check if we have a request object
                if self.request is False:
                    # OK no request object check to see if
                    # the project has a view_group_id > 1, if so
                    # then the project has restricted access for views
                    if proj_obj.view_group_id is not None:
                        if proj_obj.view_group_id > 0:
                            permitted = False
                if permitted:
                    self.man_proj_objs.append(proj_dict)
        return self.man_proj_objs
    
    def check_view_permission(self, project_uuid):
        """ Checkes to see if viewing the item is permitted
        """
        permitted = True # default
        if self.request is not False:
            pp = ProjectPermissions(project_uuid)
            permitted = pp.view_allowed(self.request)
        return permitted

