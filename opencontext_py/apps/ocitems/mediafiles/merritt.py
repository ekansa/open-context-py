import csv
import os
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
from opencontext_py.apps.ocitems.mediafiles.models import Mediafile, ManageMediafiles
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.libs.general import LastUpdatedOrderedDict


class MerrittMediaFiles():
    """
    This class has useful methods for updating
    media files, particularly updating links
    to archived versions in the CDL Merrritt repository

from opencontext_py.apps.ocitems.mediafiles.merritt import MerrittMediaFiles
mmf = MerrittMediaFiles()
mmf.update_all_project_media()

from opencontext_py.apps.ocitems.mediafiles.merritt import MerrittMediaFiles
mmf = MerrittMediaFiles()
mmf.process_merritt_dump('cdl', 'arks-files.csv')

    """
    BASE_MERRITT = 'http://merritt.cdlib.org/d/'
    ORE_NAMESPACE = 'http://www.openarchives.org/ore/terms#'
    FILE_TYPE_MAPPINGS = {'oc-gen:thumbnail': '/thumb',
                          'oc-gen:preview': '/preview',
                          'oc-gen:fullfile': '/full'}

    def __init__(self):
        self.root_import_dir = settings.STATIC_IMPORTS_ROOT
        self.abs_path = 'C:\\GitHub\\open-context-py\\static\\imports\\'
        self.updated_uuids = []
        self.updated_file_count = 0

    def update_all_project_media(self):
        """ updates media for all projects
            to use archived files in the
            Merritt repository
        """
        man_projs = Manifest.objects\
                            .filter(item_type='projects')
        for man_proj in man_projs:
            self.update_project_media(man_proj.uuid)

    def update_project_media(self, project_uuid):
        """ updates media items for a project
            to use archived files in the California Digital
            Library Merritt repository
        """
        arks = StableIdentifer.objects\
                              .filter(project_uuid=project_uuid,
                                      item_type='media',
                                      stable_type='ark')
        for id_obj in arks:
            if 'ark:/' not in id_obj.stable_id:
                ark_id = 'ark:/' + id_obj.stable_id
            else:
                ark_id = id_obj.stable_id
            self.update_item_media_files(ark_id,
                                         id_obj.uuid)

    def update_item_media_files(self, ark_id, uuid):
        """ updates media files associated with an item
        """
        old_files = Mediafile.objects.filter(uuid=uuid)
        for old_file in old_files:
            media_files = None
            if self.BASE_MERRITT not in old_file.file_uri:
                # the file_uri is not in Merritt, so do update
                # processes
                if media_files is None:
                    # a file_uri is not in Merritt, so go to
                    # Merritt and get the files for this item
                    media_files = self.get_item_media_files(ark_id,
                                                            uuid)
                if isinstance(media_files, list):
                    # we have a list of media files from Merritt
                    # so now check to update 
                    if old_file.file_type in self.FILE_TYPE_MAPPINGS:
                        type_pattern = urlquote(self.FILE_TYPE_MAPPINGS[old_file.file_type],
                                                safe='')
                        found_file = False
                        for media_file in media_files:
                            if type_pattern in media_file:
                                found_file = media_file
                                break
                        if found_file is not False:
                            if uuid not in self.updated_uuids:
                                self.updated_uuids.append(uuid)
                            self.updated_file_count += 1
                            old_file.file_uri = found_file
                            old_file.save()
                            output = '\n\n'
                            output += 'Saved file: ' + str(self.updated_file_count)
                            output += ' of uuid: ' + str(len(self.updated_uuids))
                            output += '\n'
                            output += found_file
                            print(output)

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
                             (merritt_url + '/0/system%2Fmrt-erc.txt'),
                             (merritt_url + '/0/producer%2Fmrt-erc.txt'),
                             (urlquote(ark_id, safe='') + '/0/system'),
                             (urlquote(ark_id, safe='') + '/0/producer%2Fmrt-erc.txt'),
                             urlquote(('opencontext.org/media/' + uuid), safe='')]
            for obj in objects:
                ok = True
                for avoid in avoid_content:
                    if avoid in obj:
                        # the URI for the object in turtle is a system file
                        # or is related to the media resource description
                        # the URI is NOT a link to the actual binary file
                        ok = False
                if ok and ':' in obj:
                    """
                    We've found the binary file, but now we have to manage some
                    inconsistencies in Merritt's links to these files. To do so,
                    we need to extract the file name part of the URI and compose
                    a new URI that will be a long-term stable URL / URI.

                    If the Merritt link has a port number indicated, then it is NOT
                    stable and we need to make a stable link

                    A port is in the file object URL, so manually compose a better URL
                    """
                    file_splitters = [(urlquote(ark_id, safe='') + '/0/'),
                                      (urlquote(ark_id, safe='') + '/0%2F'),
                                      (urlquote(ark_id, safe='') + '%2F0%2F'),
                                      (urlquote(ark_id, safe='') + '%2F0/')]
                    for splitter in file_splitters:
                        if splitter in obj:
                            obj_ex = obj.split(splitter)
                            # compose a new obj uri based on the canonnical template
                            # for a presistent URI in Merritt
                            obj = merritt_url + '/0/' + obj_ex[1]
                            break
                if ok:
                    # now check that the obj uri actually works
                    mm = ManageMediafiles()
                    head_ok = mm.get_head_info(obj, True)
                    if head_ok:
                        # HTTP head request returned an OK or Redirect found status
                        media_files.append(obj)
                    else:
                        print('Crap failed Header request for ' + obj)
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

    def process_merritt_dump(self, act_dir, filename):
        """ processes a merritt CSV dump listing
            OC media files in the merritt repository

from opencontext_py.apps.ocitems.mediafiles.merritt import MerrittMediaFiles
mmf = MerrittMediaFiles()
mmf.process_merritt_dump('cdl', 'arks-files.csv')

        """
        tab_obj = self.load_csv_file(act_dir, filename)
        if tab_obj is not False:
            print('Found records: ' + str(len(tab_obj)))
            for row in tab_obj:
                self.process_merritt_dump_row(row)

    def process_merritt_dump_row(self, row):
        """ processes a merrit dump row
            to update an item
        """
        raw_ark = row[0]
        ark = raw_ark.replace('ark:/', '')
        uri = row[1] # 2nd column
        merritt_uri = row[2]  # 3rd column
        uri_ex = uri.split('/')
        uuid = uri_ex[-1]
        ark_id_ok = StableIdentifer.objects\
                                   .filter(stable_id=ark,
                                           uuid=uuid)[:1]
        if len(ark_id_ok) > 0:
            # print('Identifers check: ' + ark + ' = ' + uuid)
            old_files = Mediafile.objects.filter(uuid=uuid)
            for old_file in old_files:
                if self.BASE_MERRITT not in old_file.file_uri:
                    # the file_uri is not in Merritt, so do update
                    # processes
                    print('Check: ' + uuid + ': ' + old_file.file_type)
                    if old_file.file_type in self.FILE_TYPE_MAPPINGS:
                        type_pattern = self.FILE_TYPE_MAPPINGS[old_file.file_type]
                        print('Looking for ' + type_pattern + ' in ' + merritt_uri)
                        if type_pattern in merritt_uri:
                            # found a match
                            if uuid not in self.updated_uuids:
                                self.updated_uuids.append(uuid)
                            self.updated_file_count += 1
                            old_file.file_uri = merritt_uri
                            old_file.save()
                            output = '\n\n'
                            output += 'Saved file: ' + str(self.updated_file_count)
                            output += ' of uuid: ' + str(len(self.updated_uuids))
                            output += '\n'
                            output += merritt_uri
                            print(output)

    def set_check_directory(self, act_dir):
        """ Prepares a directory to find import GeoJSON files """
        output = False
        full_dir = self.root_import_dir + act_dir + '/'
        if os.path.exists(full_dir):
            output = full_dir
        if output is False:
            output = self.abs_path + act_dir + '\\'
        return output

    def load_csv_file(self, act_dir, filename):
        """ Loads a file and parse a csv
            file
        """
        tab_obj = False
        dir_file = self.set_check_directory(act_dir) + filename
        if os.path.exists(dir_file):
            with open(dir_file, encoding='utf-8', errors='replace') as csvfile:
                # dialect = csv.Sniffer().sniff(csvfile.read(1024))
                # csvfile.seek(0)
                csv_obj = csv.reader(csvfile)
                tab_obj = []
                for row in csv_obj:
                    row_list = []
                    for cell in row:
                        row_list.append(cell)
                    tab_obj.append(row_list)
        else:
            print('Cannot find: ' + dir_file)
        return tab_obj
