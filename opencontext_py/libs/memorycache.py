from django.conf import settings
import django.utils.http as http
from opencontext_py.libs.rootpath import RootPath
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.apps.entities.entity.models import Entity
from opencontext_py.apps.entities.uri.models import URImanagement
from opencontext_py.apps.indexer.solrdocument import SolrDocument
from opencontext_py.apps.ocitems.assertions.models import Assertion
from opencontext_py.apps.ocitems.mediafiles.models import Mediafile
from opencontext_py.apps.ldata.linkannotations.recursion import LinkRecursion
from opencontext_py.apps.ldata.linkannotations.equivalence import LinkEquivalence


class MemoryCache():
    """ Methods to store entities and data in memory
        to limit database requests
    """

    def __init__(self, request_dict_json=False):
        self.entities = {}
        self.entity_dtypes = {}  # cannonical uri for the item
        self.entity_children = {}
        self.entity_parents = {}
        self.predicates = {}

    def check_entity_found(self, identifier, is_path=False):
        """ true or false if an entity is found """
        entity = self.get_entity(identifier, is_path)
        if entity is False:
            output = False
        else:
            output = True
        return output

    def get_entity(self, identifier, is_path=False):
        """ returns an entity object,
            if it exists looks up an entity
        """
        output = False
        identifier = http.urlunquote_plus(identifier)
        context_id = 'mem-cache-context---' + identifier
        if identifier in self.entities:
            # best case scenario, the entity is already looked up
            output = self.entities[identifier]
        elif context_id in self.entities and is_path:
            output = self.entities[context_id]
        else:
            found = False
            entity = Entity()
            if is_path:
                found = entity.context_dereference(identifier)
            else:
                found = entity.dereference(identifier)
                if found is False:
                    # case of linked data slugs
                    found = entity.dereference(identifier, identifier)
            if found:
                if is_path:
                    self.entities[context_id] = entity
                else:
                    self.entities[identifier] = entity
                if entity.uuid is not False:
                    self.entities[entity.uuid] = entity
                if entity.slug is not False:
                    self.entities[entity.slug] = entity
                output = entity
        return output

    def get_dtypes(self, entity_uri):
        """ returns an entity data type """
        if entity_uri in self.entity_dtypes:
            dtypes = self.entity_dtypes[entity_uri]
        else:
            # haven't found it yet, so look in database
            lequiv = LinkEquivalence()
            lequiv.predicates = self.predicates
            dtypes = lequiv.get_data_types_from_object(entity_uri)
            self.predicates = lequiv.predicates
            self.entity_dtypes[entity_uri] = dtypes
        return dtypes

    def get_entity_children(self, entity_uri):
        """ returns the children of an entity """
        children = []
        if entity_uri in self.entity_children:
            children = self.entity_children[entity_uri]
        else:
            lr = LinkRecursion()
            lr.mem_cache_entities = self.entities
            lr.child_entities = self.entity_children
            children = lr.get_entity_children(entity_uri)
            self.entities = lr.mem_cache_entities
            self.entity_children = lr.child_entities
        return children

    def get_jsonldish_entity_parents(self, entity_uri):
        """ returns the parents of an entity """
        parents = []
        if entity_uri in self.entity_parents:
            parents = self.entity_parents
        else:
            lr = LinkRecursion()
            lr.mem_cache_parents = self.entity_parents
            lr.mem_cache_entities = self.entities
            parents = lr.get_jsonldish_entity_parents(entity_uri)
            # now save the entities that whent into this.
            self.entity_parents = lr.mem_cache_parents
            for key, entity in lr.mem_cache_entities.items():
                if key not in self.entities:
                    self.entities[key] = entity
        return parents
