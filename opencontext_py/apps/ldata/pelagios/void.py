import time
from rdflib import Graph, URIRef, Literal, Namespace
from rdflib.namespace import RDF, RDFS, SKOS, OWL
from django.conf import settings
from opencontext_py.libs.languages import Languages
from opencontext_py.apps.entities.uri.models import URImanagement
from opencontext_py.apps.ldata.pelagios.projects import PelagiosProjects


class PelagiosVoid():
    """ Calls the database to collect data needed
        to make a Pelagios compliant VOID file
        describing datasets in Open Context
    """

    NAMESPACES = {
        'void': 'http://rdfs.org/ns/void#',
        'dcterms': 'http://purl.org/dc/terms/',
        'foaf': 'http://xmlns.com/foaf/0.1/',
        # 'xsd': 'http://www.w3.org/2001/XMLSchema',
        'oc-gen': 'http://opencontext.org/vocabularies/oc-general/'
    }
    
    # license or open annotation assertions
    OA_LICENSE = 'http://creativecommons.org/publicdomain/zero/1.0/'

    WEB_DESCRIPTION = 'This dataset relates archaeological site records published '\
        'by Open Context to content published elsewhere on the Web. '\
        'In some cases, Open Context contributors and/or editors manually identified '\
        'these relationships. In other cases, software processes followed by editorial '\
        'checks identified linkages expressed in this dataset.'

    def __init__(self):
        # list of dictionary items that combine project + manifest obj
        self.man_proj_objs = []
        self.g = None
        self.prep_graph()
        self.request = False
        self.base_uri = settings.CANONICAL_HOST + '/pelagios/data/'
        self.latest_revised = None
        # add a file extension to the data dump, make it easier for Pelagios to injest
        self.data_dump_extension = '.ttl'
        
    def prep_graph(self):
        """ prepares a graph for Pelagios """
        self.g = Graph()
        for prefix, ns_uri in self.NAMESPACES.items():
            ns = Namespace(ns_uri)
            self.g.bind(prefix, ns)
    
    def make_graph(self):
        """ makes a graph of assertions for the void file """
        lang_obj = Languages()
        # get a list of project manifest + projects objects
        # these are filtered for publicly available projects only
        pprojs = PelagiosProjects()
        pprojs.request = self.request
        self.man_proj_objs = pprojs.get_projects()
        # first make assertions about Open Context
        oc_projs_uri = settings.CANONICAL_HOST + '/projects/'
        self.make_add_triple(oc_projs_uri,
                             RDF.type,
                             self.make_full_uri('void', 'Dataset'))
        self.make_add_triple(oc_projs_uri,
                             self.make_full_uri('dcterms', 'title'),
                             None,
                             settings.CANONICAL_SITENAME)
        self.make_add_triple(oc_projs_uri,
                             self.make_full_uri('dcterms', 'description'),
                             None,
                             settings.HOST_TAGLINE)
        self.make_add_triple(oc_projs_uri,
                             self.make_full_uri('foaf', 'homepage'),
                             settings.CANONICAL_HOST)
        # now add assertions about Web data and Open Context
        self.make_add_web_dataset_assertions()
        # now add the projects as subsets of data
        for proj_dict in self.man_proj_objs:
            man = proj_dict['man']
            uri = URImanagement.make_oc_uri(man.uuid,
                                            man.item_type)
            self.make_add_triple(oc_projs_uri,
                                 self.make_full_uri('void', 'subset'),
                                 uri)
        # now add assertions about each project, esp. datadump uri
        for proj_dict in self.man_proj_objs:
            man = proj_dict['man']
            proj = proj_dict['proj']
            uri = URImanagement.make_oc_uri(man.uuid,
                                            man.item_type)
            data_uri = self.base_uri + man.uuid + self.data_dump_extension
            self.make_add_triple(uri,
                                 RDF.type,
                                 self.make_full_uri('void', 'Dataset'))
            self.make_add_triple(uri,
                                 self.make_full_uri('void', 'dataDump'),
                                 data_uri)
            """
            self.make_add_triple(uri,
                                 self.make_full_uri('foaf', 'homepage'),
                                 uri)
            """
            self.make_add_triple(uri,
                                 self.make_full_uri('dcterms', 'publisher'),
                                 None,
                                 settings.CANONICAL_SITENAME)
            self.make_add_triple(data_uri,
                                 self.make_full_uri('dcterms', 'license'),
                                 self.OA_LICENSE)
            self.make_add_triple(uri,
                                 self.make_full_uri('dcterms', 'title'),
                                 None,
                                 man.label)
            self.make_add_triple(uri,
                                 self.make_full_uri('dcterms', 'description'),
                                 None,
                                 proj.short_des)
            if man.published is not None:
                self.make_add_triple(uri,
                                     self.make_full_uri('dcterms', 'issued'),
                                     None,
                                     man.published.date().isoformat())
            if man.revised is not None:
                self.make_add_triple(uri,
                                     self.make_full_uri('dcterms', 'modified'),
                                     None,
                                     man.revised.date().isoformat())
    
    def make_add_web_dataset_assertions(self):
        """ makes and adds assertions about the 'web' dataset,
            which relate Open Context gazetteer records to other
            data on the Web
        """
        uri = settings.CANONICAL_HOST + '/about/'
        described_uri = settings.CANONICAL_HOST + '/about/recipes'
        data_uri = self.base_uri + 'web' + self.data_dump_extension
        self.make_add_triple(uri,
                             RDF.type,
                             self.make_full_uri('void', 'Dataset'))
        self.make_add_triple(uri,
                             self.make_full_uri('void', 'dataDump'),
                             data_uri)
        self.make_add_triple(uri,
                             self.make_full_uri('foaf', 'homepage'),
                             described_uri)
        self.make_add_triple(uri,
                             self.make_full_uri('dcterms', 'publisher'),
                             None,
                             settings.CANONICAL_SITENAME)
        self.make_add_triple(data_uri,
                             self.make_full_uri('dcterms', 'license'),
                             self.OA_LICENSE)
        self.make_add_triple(uri,
                             self.make_full_uri('dcterms', 'title'),
                             None,
                             'Web Resources Related to Open Context Published Places')
        self.make_add_triple(uri,
                             self.make_full_uri('dcterms', 'description'),
                             None,
                             self.WEB_DESCRIPTION)
        if self.latest_revised is not None:
            self.make_add_triple(uri,
                                 self.make_full_uri('dcterms', 'modified'),
                                 None,
                                 self.latest_revised.date().isoformat())
            
    def make_add_triple(self, sub_uri, pred_uri, obj_uri=None, obj_literal=None):
        """ makes a triple and adds it to the graph """
        act_s = URIRef(sub_uri)
        act_p = URIRef(pred_uri)
        if obj_literal is not None:
            act_o = Literal(obj_literal)
        else:
            act_o = URIRef(obj_uri)
        self.g.add((act_s, act_p, act_o))
    
    def make_full_uri(self, prefix, value):
        """ makes a full uri for a prefix and value """
        if prefix in self.NAMESPACES:
            output = self.NAMESPACES[prefix] + value
        else:
            output = prefix + ':' + value
        return output
    
    def get_projects(self):
        """ gets the manfest and project objects needed to make the void """
        man_objs = Manifest.objects\
                           .filter(item_type='projects')
        for man_obj in man_objs:
            if self.latest_revised is None:
                self.latest_revised = man_obj.revised
            proj_obj = False
            permitted = self.check_view_permission(man_obj.uuid)
            if permitted:
                # only try to get project information if the view is permitted
                try:
                    proj_obj = Project.objects.get(uuid=man_obj.uuid)
                except Project.DoesNotExist:
                    proj_obj = False
            if proj_obj is not False:
                if man_obj.revised > self.latest_revised:
                    self.latest_revised = man_obj.revised
                proj_dict = {'man': man_obj,
                             'proj': proj_obj}
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