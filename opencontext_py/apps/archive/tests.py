import os
import json
import codecs
import requests
from django.db import models
from django.db import transaction
from django.conf import settings
from django.test import TestCase
from django.test.client import Client
from rdflib.plugin import register, Parser
from rdflib import Graph, URIRef, Literal
from rdflib.graph import ConjunctiveGraph
from rdflib.namespace import SKOS
from opencontext_py.libs.generalapi import GeneralAPI


class TestJSONld(TestCase):

    """
from opencontext_py.apps.contexts.tests import TestJSONld
t_json_ld = TestJSONld()
t_json_ld.setUp()

    """

    def setUp(self):
        register('json-ld',
                 Parser,
                 'rdflib_jsonld.parser',
                 'JsonLDParser')
        # self.graph = Graph()
        # self.proj_context_uri = 'http://127.0.0.1:8000/contexts/projects/3FAAA477-5572-4B05-8DC1-CA264FE1FC10.json'
        self.proj_context_uri = '/contexts/projects/3FAAA477-5572-4B05-8DC1-CA264FE1FC10.json'
        self.context_file = settings.STATIC_IMPORTS_ROOT + '3-context.json'
        self.data_file = settings.STATIC_IMPORTS_ROOT + 'dt-bone.json'
        #self.context_str = self.request_json_str(self.proj_context_uri)
        client = Client()
        response = client.get(self.proj_context_uri, follow=True)
        assert response.status_code in [200,301]
        self.context_str = response.content
        self.data_str = self.load_json_file_str(self.data_file)
        g_context = ConjunctiveGraph(identifier=self.proj_context_uri)
        g_context.parse(data=self.context_str, format='json-ld')
        proj_graph_obj = URIRef(self.proj_context_uri)
        print('N3: ' + str(g_context.__str__()))
        for c in g_context.contexts():
            print(str(c))
        print('-------Triples for context-graph------')
        self.test_type_linking(g_context)
        g_data = ConjunctiveGraph().parse(data=self.data_str, format='json-ld')
        print('-------Triples for data-record--------')
        self.test_type_linking(g_data)

    def test_type_linking(self, graph):
        test_type = URIRef('http://opencontext.org/types/13_56_DT_VarVal')
        for s,p,o in  graph.triples( (test_type,  None, None) ):
            # gets all the triples replating to the test type. If all is
            # well, we will have triples from the context and from the data
            print('P: ' + str(p) + ' ---> O: ' + str(o))
    
    
    def request_json_str(self, url):
        """requests JSON as a string from a URl """
        json_output = None
        try:
            gapi = GeneralAPI()
            r = requests.get(url,
                             timeout=240,
                             headers=gapi.client_headers)
            r.raise_for_status()
            json_obj = r.json()
        except:
            json_obj = False
        if isinstance(json_obj, dict):
            json_output = json.dumps(json_obj,
                                    indent=4,
                                    ensure_ascii=False)
        return json_output
        
    def load_json_file_str(self, dir_file):
        """ loads a json file, checks to make sure it is
            valid json, then dumps it as a string again
        """
        json_output = None
        json_obj = self.load_json_file(dir_file)
        if json_obj is not False:
            json_output = json.dumps(json_obj,
                                     indent=4,
                                     ensure_ascii=False)
        return json_output
    
    def load_json_file(self, dir_file):
        """ Loads a file and parse it into a
            json object
        """
        json_obj = False
        if os.path.exists(dir_file):
            try:
                json_obj = json.load(codecs.open(dir_file,
                                                 'r',
                                                 'utf-8-sig'))
            except:
                print('Cannot parse as JSON: ' + dir_file)
                json_obj = False
        return json_obj
    
