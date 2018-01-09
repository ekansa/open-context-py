import hashlib
from django.conf import settings
from django.db import models
from django.core.cache import caches
from opencontext_py.libs.cacheutilities import CacheUtilities
from opencontext_py.apps.contexts.projectcontext import ProjectContext
from opencontext_py.apps.entities.entity.models import Entity
from opencontext_py.apps.ocitems.assertions.models import Assertion


class ItemGenerationCache():
    """
    methods for using the Reddis cache to
    streamline making item JSON-LD
    """

    def __init__(self):
        self.cache_use = CacheUtilities()
    
    def get_project_context(self,
                            project_uuid,
                            assertion_hashes=False):
        """ gets a project context, which lists all predicates
            and has a graph of linked data annotations to
            predicates and types
            if assertion_hashes is true, then get
            the project context with the hash identifiers
            for the specific linked data assertions. This makes
            it easier to reference specific assertions for edits.
        """
        cache_id = self.cache_use.make_memory_cache_key('proj-context-' + str(assertion_hashes),
                                                        project_uuid)
        item = self.cache_use.get_cache_object(cache_id,
                                               True)
        if item is not None:
            output = item
        else:
            pc = ProjectContext(project_uuid)
            pc.assertion_hashes
            context_json_ld = pc.make_context_json_ld()
            if isinstance(context_json_ld, dict):
                output = context_json_ld
                self.cache_use.save_cache_object(cache_id,
                                                 context_json_ld,
                                                 True)
        return context_json_ld

    def get_entity(self, identifier):
        """ gets an entity either from the cache or from
            database lookups.
        """
        cache_id = self.cache_use.make_memory_cache_key('entities', identifier)
        item = self.cache_use.get_cache_object(cache_id)
        if item is not None:
            output = item
        else:
            entity = Entity()
            entity.get_thumbnail = True
            found = entity.dereference(identifier)
            if found:
                output = entity
                self.cache_use.save_cache_object(cache_id, entity)
            else:
                output = False
        return output
