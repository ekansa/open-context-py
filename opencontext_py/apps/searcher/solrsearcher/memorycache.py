from django.conf import settings
import django.utils.http as http
from opencontext_py.libs.rootpath import RootPath
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.apps.entities.entity.models import Entity
from opencontext_py.apps.entities.uri.models import URImanagement
from opencontext_py.apps.indexer.solrdocument import SolrDocument
from opencontext_py.apps.ocitems.assertions.models import Assertion
from opencontext_py.apps.ocitems.mediafiles.models import Mediafile
from opencontext_py.apps.searcher.solrsearcher.querymaker import QueryMaker
from opencontext_py.apps.ldata.linkannotations.recursion import LinkRecursion
from opencontext_py.apps.ldata.linkannotations.equivalence import LinkEquivalence


class MemoryCache():
    """ Methods to store entities and data in memory
        to limit database requests
    """

    def __init__(self, request_dict_json=False):
        self.entities = {}
        self.entity_dtypes = {}  # cannonical uri for the item

    def check_entity_found(self, identifier, is_path=False):
        """ true or false if an entity is found """
        entity = self.get_entity(identifier, is_path=False)
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
        if identifier in self.entities:
            # best case scenario, the entity is already looked up
            output = self.entities[identifier]
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
                output = entity
        return output

    def get_dtypes(self, entity_uri):
        """ returns an entity data type """
        if entity_uri in self.entity_dtypes:
            dtypes = self.entity_dtypes[entity_uri]
        else:
            # haven't found it yet, so look in database
            lequiv = LinkEquivalence()
            dtypes = lequiv.get_data_types_from_object(entity_uri)
            self.entity_dtypes[entity_uri] = dtypes
        return dtypes

