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
