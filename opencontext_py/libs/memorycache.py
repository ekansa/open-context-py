import redis
import pickle
import hashlib
from django.conf import settings
from django.core.cache import caches
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
        self.context_entities = {}  # entities that also have context
        self.entity_dtypes = {}  # cannonical uri for the item
        self.entity_children = {}
        self.entity_parents = {}
        self.predicates = {}
        self.redis_server = False
        self.redis_ok = True

    def ping_redis_server(self):
        """ Checks to make sure that redis is OK """
        # self.redis_server = redis.StrictRedis(host='localhost', port=6379, db=0)
        # self.redis_server.flushall()
        # self.redis_ok = self.redis_server.ping()
        print('Redis status: ' + str(self.redis_ok))

    def check_entity_found(self, identifier, is_path=False):
        """ true or false if an entity is found """
        bad_ids = ['root', False, None]
        if identifier in bad_ids:
            entity = False
        else:
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
            context_cache_id = self.make_memory_cache_key('entities-path', identifier)
            cache_id = self.make_memory_cache_key('entities', identifier)
            item = self.get_cache_object(cache_id)
            if item is not None:
                output = item
                # print('YEAH found entity: ' + cache_id)
            else:
                item = self.get_cache_object(context_cache_id)
                if item is not None:
                    output = item
                    # print('YEAH by context path: ' + context_cache_id)
            if output is False:
                output = self.get_entity_db(identifier, context_id, is_path)
                if output is not False:
                    entity = output
                    if is_path:
                        self.save_cache_object(context_cache_id, entity)
                    else:
                        self.save_cache_object(cache_id, entity)
                        slug_id = self.make_memory_cache_key('entities', entity.slug)
                        if slug_id is not cache_id:
                            self.save_cache_object(slug_id, entity)
        return output

    def get_entity_db(self, identifier, context_id, is_path=False):
        """ returns an entity object
            via database calls
        """
        output = False
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

    def check_con_entity_found(self, identifier):
        """ true or false if an entity is found """
        bad_ids = ['root', False, None]
        if identifier in bad_ids:
            entity = False
        else:
            entity = self.get_con_entity(identifier)
        if entity is False:
            output = False
        else:
            output = True
        return output

    def get_con_entity(self, identifier):
        """ returns an entity object,
            if it exists looks up an entity
        """
        output = False
        identifier = http.urlunquote_plus(identifier)
        if identifier in self.context_entities:
            # best case scenario, the entity is already looked up
            output = self.context_entities[identifier]
        else:
            cache_id = self.make_memory_cache_key('context-entities', identifier)
            item = self.get_cache_object(cache_id)
            if item is not None:
                # print('YEAH found context: ' + cache_id)
                output = item
            else:
                output = self.get_context_entity_db(identifier)
                if output is not False:
                    entity = output
                    self.save_cache_object(cache_id, entity)
                    slug_id = self.make_memory_cache_key('context-entities', entity.slug)
                    if slug_id is not cache_id:
                        self.save_cache_object(slug_id, entity)
        return output

    def get_context_entity_db(self, identifier):
        """ returns an entity object
            via database calls
        """
        output = False
        entity = Entity()
        entity.get_context = True
        found = entity.dereference(identifier)
        if found is False:
            # case of linked data slugs
            found = entity.dereference(identifier, identifier)
        if found:
            self.context_entities[identifier] = entity
            if entity.uuid is not False:
                self.context_entities[entity.uuid] = entity
            if entity.slug is not False:
                self.context_entities[entity.slug] = entity
            output = entity
        return output

    def get_dtypes(self, entity_uri):
        """ returns an entity data type """
        if entity_uri in self.entity_dtypes:
            dtypes = self.entity_dtypes[entity_uri]
        else:
            # haven't found it yet, so look in database
            cache_id = self.make_memory_cache_key('data-types', entity_uri)
            dtypes = self.get_cache_object(cache_id)
            if dtypes is None:
                dtypes = self.get_dtypes_db(entity_uri)
                self.save_cache_object(cache_id, dtypes)
        return dtypes

    def get_dtypes_db(self, entity_uri):
        """ returns an entity data type """
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
            cache_id = self.make_memory_cache_key('entity-children', entity_uri)
            children = self.get_cache_object(cache_id)
            if children is None:
                children = self.get_entity_children_db(entity_uri)
                self.save_cache_object(cache_id, children)
        return children

    def get_entity_children_db(self, entity_uri):
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
            cache_id = self.make_memory_cache_key('entity-jsonldist-parents', entity_uri)
            parents = self.get_cache_object(cache_id)
            if parents is None:
                parents = self.get_jsonldish_entity_parents_db(entity_uri)
                self.save_cache_object(cache_id, parents)
        return parents

    def get_jsonldish_entity_parents_db(self, entity_uri):
        """ returns the parents of an entity """
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

    def make_memory_cache_key(self, prefix, identifier):
        """ makes a valid OK cache key """
        hash_obj = hashlib.sha1()
        concat_string = str(prefix) + " " + str(identifier)
        hash_obj.update(concat_string.encode('utf-8'))
        return hash_obj.hexdigest()

    def get_cache_object(self, key):
        """ gets a cached reddis object """
        if self.redis_ok:
            try:
                cache = caches['redis']
                obj = cache.get(key)
            except:
                obj = None
                self.redis_ok = False
        else:
            obj = None
        return obj

    def save_cache_object(self, key, obj):
        """ saves a cached reddis object """
        if self.redis_ok:
            try:
                cache = caches['redis']
                cache.set(key, obj)
                ok = True
            except:
                self.redis_ok = False
                ok = False
        else:
            ok = False
        return ok

    def get_cache_object_old(self, key):
        """ gets a cached reddis object """
        cache = caches['redis']
        if r.exists(key):
            ob = pickle.loads(r.get(key))
        else:
            unpacked_object = None
        return unpacked_object

    def save_cache_object_old(self, key, obj):
        """ saves a cached reddis object """
        r = self.memcache
        pickled_object = pickle.dumps(obj)
        ok = r.set(key, pickled_object)
        return ok
