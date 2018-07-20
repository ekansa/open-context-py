from unidecode import unidecode
from django.conf import settings
from django.core.cache import caches
from django.template.defaultfilters import slugify
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.apps.contexts.models import GeneralContext
from opencontext_py.apps.entities.uri.models import URImanagement
from opencontext_py.apps.entities.entity.models import Entity
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.contexts.projectcontext import ProjectContext


class ReferenceContext():
    """
    Methods to reference and use predictates, types, and their
    annotations as defined in the project context

from opencontext_py.apps.contexts.reference import ReferenceContext
rc = ReferenceContext()
rc.get_project_context('3')

    """

    def __init__(self):
        self.project_uuid = None
        self.json_ld = None

    def get_entity_item(self, identifier):
        """ gets context information about an entity
            based on an identifier
        """
        item = None
        # first make a list of variants of the identifier
        if '/' in identifier:
            id_ex = identifier.split('/')
            uuid_or_slug = id_ex[-1]
            uri = identifier
        else:
            uuid_or_slug = identifier
            uri = None
        if isinstance(self.json_ld, dict):
            # first look through the graph to get
            # most information about the item
            if '@graph' in self.json_ld:
                for act_item in self.json_ld['@graph']:
                    if item is None:
                        # first try to match on uuid or slug
                        match = self.check_keys_match(
                            act_item,
                            uuid_or_slug,
                            ['uuid', 'slug'])
                        if match:
                            item = act_item
                        elif uri is not None:
                            match = self.check_keys_match(
                                act_item,
                                uri,
                                ['@id', 'id', 'owl:sameAs'])
                            if match:
                                item = act_item
                        if item is not None:
                            break
            if item is not None and '@context' in self.json_ld:
                if '@id' in item:
                    if 'oc-pred:' in item['@id']:
                        pred_id = item['@id']
                        # we have a predicate item, get more information in the
                        # context
                        if pred_id in self.json_ld['@context']:
                            if 'type' in self.json_ld['@context'][pred_id]:
                                # get the type (data-type) for the item
                                item['type'] = self.json_ld['@context'][pred_id]['type']
        return item

    def check_keys_match(self, act_item, find_val, keys):
        """ checks to see if a key exists, if so,
            does the value match the find string
        """
        output = False
        if not isinstance(keys, list):
            keys = [keys]
        for key in keys:
            if key in act_item:
                if find_val == act_item[key]:
                    output = True
                    break
        return output

    def get_project_context(self, project_identifier):
        """ gets a project context from a project identifier,
            which can be a uuid or a slug or a URI
        """
        output = False
        if '/' in project_identifier:
            pi_ex = project_identifier.split('/')
            uuid_or_slug = pi_ex[-1]
        else:
            uuid_or_slug = project_identifier
        proj_context = ProjectContext()
        proj_context.dereference_uuid_or_slug(uuid_or_slug)
        if isinstance(proj_context.uuid, str):
            cache_key = self.make_cache_key('p-cntxt', proj_context.uuid)
            self.project_uuid = proj_context.uuid
            json_ld = self.get_cache_object(cache_key)
            if json_ld is None:
                json_ld = proj_context.make_context_json_ld()
                self.save_cache_object(cache_key,
                                       json_ld,
                                       None)
                self.json_ld = json_ld
            else:
                self.json_ld = json_ld
            output = True
        else:
            self.project_uuid = False
            self.json_ld = False
        return output

    def make_cache_key(self, prefix, identifier):
        """ makes a valid OK cache key """
        concat_string = str(prefix) + "-" + str(identifier)
        return slugify(unidecode(concat_string))

    def get_cache_object(self, key):
        """ gets a cached reddis object """
        try:
            cache = caches['redis']
            obj = cache.get(key)
        except:
            obj = None
        return obj

    def save_cache_object(self, key, obj, timeout=1200):
        """ saves a cached reddis object """
        try:
            cache = caches['redis']
            cache.set(key, obj, timeout)
            ok = True
        except:
            self.redis_ok = False
            ok = False
        return ok

