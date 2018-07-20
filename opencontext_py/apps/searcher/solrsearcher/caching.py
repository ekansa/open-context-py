import hashlib
from django.conf import settings
from django.core.cache import caches
from opencontext_py.libs.general import LastUpdatedOrderedDict, DCterms
from opencontext_py.libs.memorycache import MemoryCache
from opencontext_py.libs.rootpath import RootPath
from opencontext_py.apps.entities.entity.models import Entity
from opencontext_py.apps.entities.uri.models import URImanagement
from opencontext_py.apps.ocitems.assertions.models import Assertion
from opencontext_py.apps.ocitems.mediafiles.models import Mediafile
from opencontext_py.apps.ldata.linkannotations.recursion import LinkRecursion
from opencontext_py.apps.ldata.linkannotations.equivalence import LinkEquivalence


class SearchGenerationCache():
    """
    methods for using the Reddis cache to
    streamline making JSON-LD search results
    """
    
    def __init__(self, cannonical_uris = False):
        self.m_cache = MemoryCache()
    
    def get_dtypes(self, entity_uri):
        """ returns an entity data type """
        cache_key = self.m_cache.make_cache_key('data-types', entity_uri)
        dtypes = self.m_cache.get_cache_object(cache_key)
        if dtypes is None:
            dtypes = self._get_dtypes_db(entity_uri)
            if dtypes:
                self.m_cache.save_cache_object(cache_key, dtypes)
        return dtypes

    def _get_dtypes_db(self, entity_uri):
        """ returns an entity data type """
        # haven't found it yet, so look in database
        lequiv = LinkEquivalence()
        return lequiv.get_data_types_from_object(entity_uri)
