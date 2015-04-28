import requests
from rdflib import Graph, URIRef, Literal
from rdflib.namespace import SKOS, RDFS, OWL
from django.conf import settings
from django.utils.http import urlquote, quote_plus, urlquote_plus
from opencontext_py.libs.generalapi import GeneralAPI
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.apps.entities.uri.models import URImanagement
from opencontext_py.apps.entities.entity.models import Entity
from opencontext_py.apps.ocitems.identifiers.models import StableIdentifer
from opencontext_py.apps.ocitems.mediafiles.models import Mediafile
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.libs.general import LastUpdatedOrderedDict


class ManageMediaFiles():
    """
    This class has useful methods for updating
    media files, particularly updating links
    to archived versions in the CDL Merrritt repository
    """
    BASE_MERRITT = 'http://merritt.cdlib.org/d/'
    ORE_NAMESPACE = 'http://www.openarchives.org/ore/terms#'
    FILE_TYPE_MAPPINGS = {'oc-gen:thumbnail': '/thumb',
                          'oc-gen:preview': '/preview',
                          'oc-gen:fullfile': '/full'}
    
    def __init__(self):
        self.updated_uuid_count = 0
        self.updated_file_count = 0
    
    
    def update_project_media(self, project_uuid):
        """ updates media items for a project
            to use archived files in the California Digital
            Library Merritt repository
        """
        arks = StableIdentifer.objects\
                              .filter(project_uuid=project_uuid,
                                      item_type='media',
                                      stable_type='ark')[:5]
        for id_obj in arks:
            if 'ark:/' not in id_obj.stable_id:
                ark_id = 'ark:/' + id_obj.stable_id
            else:
                ark_id = id_obj.stable_id
            media_files = self.get_item_media_files(ark_id,
                                                    id_obj.uuid)
            self.update_item_media_files(id_obj.uuid,
                                         media_files)
    
    def update_item_media_files(self, uuid, media_files):
        """ updates media files associated with an item
        """
        uuid_add = 0
        if isinstance(media_files, list):
            old_files = Mediafile.objects.filter(uuid=uuid)
            for old_file in old_files:
                if old_file.file_type in self.FILE_TYPE_MAPPINGS:
                    type_pattern = urlquote(self.FILE_TYPE_MAPPINGS[old_file.file_type],
                                            safe='')
                    found_file = False
                    for media_file in media_files:
                        if type_pattern in media_file:
                            found_file = media_file
                            break
                    if found_file is not False:
                        uuid_add = 1
                        self.updated_file_count += 1
                        print('Found ' + old_file.file_type + ' in ' + found_file)
        self.updated_uuid_count += uuid_add
        
    def get_item_media_files(self, ark_id, uuid):
        """ Gets item resources from Merritt
            based on an ARK id
        """
        media_files = False
        merritt_url = self.BASE_MERRITT + urlquote(ark_id, safe='')
        turtle_uri = merritt_url + '/1/system%2Fmrt-object-map.ttl'
        objects = self.get_item_resources(turtle_uri)
        if isinstance(objects, list):
            media_files = []
            avoid_content = [(merritt_url + '/0/system'),
                             (merritt_url + '/0/producer%2Fmrt-erc.txt'),
                             urlquote(('opencontext.org/media/' + uuid), safe='')]
            for obj in objects:
                ok = True
                for avoid in avoid_content:
                    if avoid in obj:
                        ok = False
                if ok:
                    media_files.append(obj)
        else:
            print('No resources for item')
        return media_files 
    
    def get_item_resources(self, turtle_uri):
        """ Gets and parses turtle,
            then finds the resources
            that are aggregated as part of
            the archived media resource
        """
        objects = False
        graph = self.load_parse_turtle_text(turtle_uri)
        if graph is not False:
            objects = []
            ore_pred = URIRef(self.ORE_NAMESPACE + 'aggregates')
            for s, p, o in graph.triples( (None, ore_pred, None) ):
                objects.append(o.__str__())
        return objects

    def load_parse_graph(self, uri, fformat='text/turtle'):
        """
        Loads and parses a graph with media resources
        For some reason this does not appear to work
        """
        graph = Graph()
        try:
            if(fformat is not False):
                graph.parse(uri, format=fformat)
            else:
                graph.parse(uri)
        except:
            print('Failed to load the graph.')
            graph = False
        return graph
    
    def load_parse_turtle_text(self, url):
        """ gets the turle text from
            Merritt, attemps to parse it
        """
        graph = False
        turtle = self.get_turtle_text(url)
        if turtle is not False:
            graph = Graph()
            try:
                graph.parse(data=turtle, format='turtle')
            except:
                print('Failed to load the graph.')
                graph = False
        return graph
    
    def get_turtle_text(self, url):
        """ gets the turtle manifest as
            a string
        """
        try:
            gapi = GeneralAPI()
            r = requests.get(url,
                             timeout=240,
                             headers=gapi.client_headers)
            r.raise_for_status()
            turtle = r.text
        except:
            print('Failed to get ' + url)
            turtle = False
        return turtle