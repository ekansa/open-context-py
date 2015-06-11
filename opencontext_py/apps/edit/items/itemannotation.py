import time
import uuid as GenUUID
from django.db import models
from django.db.models import Q
from opencontext_py.apps.entities.entity.models import Entity
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.ocitems.projects.permissions import ProjectPermissions
from opencontext_py.apps.ldata.linkannotations.models import LinkAnnotation
from opencontext_py.apps.ldata.linkannotations.equivalence import LinkEquivalence
from opencontext_py.apps.ldata.linkentities.models import LinkEntity
from opencontext_py.apps.ocitems.identifiers.models import StableIdentifer


# Help organize the code, with a class to make editing items easier
class ItemAnnotation():
    """ This class contains methods
        for editing item annotations
    """

    def __init__(self,
                 uuid,
                 request=False):
        self.creator_uuid = False
        self.uuid = uuid
        self.request = request
        self.errors = {'uuid': False,
                       'params': False}
        self.response = {}
        self.orcid_ok = None
        try:
            self.manifest = Manifest.objects.get(uuid=uuid)
        except Manifest.DoesNotExist:
            self.manifest = False
            self.errors['uuid'] = 'Item ' + uuid + ' not in manifest'
        if request is not False and self.manifest is not False:
            # check to make sure edit permissions OK
            pp = ProjectPermissions(self.manifest.project_uuid)
            self.edit_permitted = pp.edit_allowed(request)
        else:
            # default to no editting permissions
            self.edit_permitted = False

    def add_item_annotation(self, post_data):
        """ Adds a linked data annotation to an item
        """
        note = ''
        ok_predicates = ['dc-terms:creator',
                         'dc-terms:contributor']
        ok = True
        predicate_uri = self.request_param_val(post_data,
                                               'predicate_uri')
        object_uri = self.request_param_val(post_data,
                                            'object_uri')
        if predicate_uri is not False \
           and object_uri is not False:
            p_entity = Entity()
            found_p = p_entity.dereference(predicate_uri)
            if found_p is False \
               and predicate_uri in ok_predicates:
                found_p = True
            o_entity = Entity()
            found_o = o_entity.dereference(object_uri)
            if found_p and found_o:
                lequiv = LinkEquivalence()
                pred_list = lequiv.get_identifier_list_variants(predicate_uri)
                obj_list = lequiv.get_identifier_list_variants(object_uri)
                la_exist = LinkAnnotation.objects\
                                         .filter(subject=self.uuid,
                                                 predicate_uri__in=pred_list,
                                                 object_uri__in=obj_list)[:1]
                if len(la_exist) < 1:
                    # we don't have an annotation like this yet
                    object_uri = o_entity.uri
                    new_la = LinkAnnotation()
                    new_la.subject = self.manifest.uuid
                    new_la.subject_type = self.manifest.item_type
                    new_la.project_uuid = self.manifest.project_uuid
                    new_la.source_id = self.request_param_val(post_data,
                                                              'source_id',
                                                              'manual-web-form',
                                                              False)
                    new_la.sort = self.request_param_val(post_data,
                                                        'sort',
                                                        0,
                                                        False)
                    new_la.predicate_uri = predicate_uri
                    new_la.object_uri = object_uri
                    new_la.creator_uuid = self.creator_uuid
                    new_la.save()
                else:
                    ok = False
                    note = 'This annotation already exists.'
            else:
                ok = False
                note = 'Missing a predicate or object entity'
        else:
            note = self.errors['params']
            ok = False
        self.response = {'action': 'add-item-annotation',
                         'ok': ok,
                         'change': {'note': note}}
        return self.response

    def delete_annotation(self, post_data):
        """ Adds a linked data annotation to an item
        """
        note = ''
        if 'hash_id' in post_data:
            hash_id = post_data['hash_id']
            la_exist = LinkAnnotation.objects\
                                     .filter(hash_id=hash_id)\
                                     .delete()
            ok = True
            note = 'annotation deleteted'
        else:
            ok = False
            note = 'Missing a annotation hash-id.'
            self.errors['params'] = note
        self.response = {'action': 'delete-annotation',
                         'ok': ok,
                         'change': {'note': note}}
        return self.response
    
    def check_orcid_ok(self, post_data):
        """ checks to see if it's OK to add ORCID
            stable identifiers
        """
        if self.orcid_ok is None:
            # we haven't checked yet
            orcid_ok = False
            if self.manifest.item_type == 'persons':
                id_type = self.request_param_val(post_data,
                                                 'stable_type')
                if id_type == 'orcid':
                    orcid_ok = True
            self.orcid_ok = orcid_ok
        return self.orcid_ok
    
    def add_item_stable_id(self, post_data):
        """ adds a stable identifier to an item """
        ok = False
        note = ''
        orcid_ok = self.check_orcid_ok(post_data)
        id_type_prefixes = {'ark': 'http://n2t.net/ark:/',
                            'doi': 'http://dx.doi.org/',
                            'orcid': 'http://orcid.org/'}
        stable_id = self.request_param_val(post_data,
                                           'stable_id')
        stable_type = self.request_param_val(post_data,
                                             'stable_type')
        stable_id = stable_id.strip()
        # now update the stable_type based on what's in the stable_id
        stable_type = StableIdentifer().type_uri_check(stable_type,
                                                       stable_id)
        if stable_type == 'orcid' and orcid_ok is not True:
            # problem adding an ORCID to this type of item
            stable_type = False
            note = 'Cannot add an ORCID to this item.'
        if stable_id is not False \
           and stable_type is not False:
            ok = True
            try:
                new_stable = StableIdentifer()
                new_stable.stable_id = stable_id
                new_stable.stable_type = stable_type
                new_stable.uuid = self.manifest.uuid
                new_stable.project_uuid = self.manifest.project_uuid
                new_stable.item_type = self.manifest.item_type
                new_stable.save()
            except:
                ok = False
                note = 'Identifier already in use'
        else:
            note = 'Problems with the ID request'
        self.response = {'action': 'add-item-stable-id',
                         'ok': ok,
                         'change': {'note': note}}
        return self.response
    
    def request_param_val(self,
                          data,
                          param,
                          default=False,
                          note_error=True):
        """ Gets the value for paramater in a dict (data, if parameter
            does not exist, it returns a default value
        """
        if isinstance(data, dict):
            if param in data:
                output = data[param]
            else:
                output = default
                if note_error:
                    if self.error['params'] is False:    
                        self.error['params'] = 'Missing paramater: ' + param
                    else:
                        self.error['params'] += '; Missing paramater: ' + param
        else:
            output = default
        return output
