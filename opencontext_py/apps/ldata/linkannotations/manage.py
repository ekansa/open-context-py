import hashlib
from django.db import models
from django.db.models import Q
from opencontext_py.apps.ldata.linkannotations.models import LinkAnnotation
from opencontext_py.apps.ldata.linkentities.models import LinkEntity
from opencontext_py.apps.ocitems.assertions.models import Assertion
from opencontext_py.apps.entities.uri.models import URImanagement
from opencontext_py.apps.ocitems.predicates.models import Predicate
from opencontext_py.apps.ldata.linkannotations.recursion import LinkRecursion


class LinkAnnoManagement():
    """
        Some useful methods for changing linked data annoations.
    """

    PRED_SBJ_IS_SUB_OF_OBJ = 'skos:broader'  # default predicate for subject item is subordinate to object item

    def __init__(self):
        self.project_uuid = '0'
        self.source_id = 'manual'

    def add_skos_hierarachy(self, parent_uri, child_uri):
        """ Add a hiearchy assertion for
            linked entities
        """
        try:
            parent = LinkEntity.objects.get(uri=parent_uri)
        except LinkEntity.DoesNotExist:
            parent = False
        try:
            child = LinkEntity.objects.get(uri=child_uri)
        except LinkEntity.DoesNotExist:
            child = False
        if parent is not False and child is not False:
            lr = LinkRecursion()
            exiting_parents = lr.get_entity_parents(child_uri)
            if len(exiting_parents) >= 1:
                print('Child has parents: ' + str(exiting_parents))
            else:
                # child is not already in a hieararchy, ok to put it in one
                la = LinkAnnotation()
                la.subject = child.uri  # the subordinate is the subject
                la.subject_type = 'uri'
                la.project_uuid = self.project_uuid
                la.source_id = self.source_id + '-hierarchy'
                la.predicate_uri = self.PRED_SBJ_IS_SUB_OF_OBJ
                la.object_uri = parent.uri  # the parent is the object
                la.save()
                print('Made: ' + child.uri + ' child of: ' + parent.uri)
        else:
            print('Cannot find parent or child')

    def replace_predicate_uri(self,
                              old_pred_uri,
                              new_pred_uri):
        """ replaces annotations using
        a given old_predicate with a new one
        """
        alt_old_pred = self.make_alt_uri(old_pred_uri)
        la_objs = LinkAnnotation.objects\
                                .filter(Q(predicate_uri=old_pred_uri) |
                                        Q(predicate_uri=alt_old_pred))
        print('Change predicates for annotations: ' + str(len(la_objs)))
        for la_obj in la_objs:
            new_la = la_obj
            new_la.predicate_uri = new_pred_uri
            LinkAnnotation.objects\
                          .filter(hash_id=la_obj.hash_id).delete()
            new_la.save()

    def replace_predicate_uri_narrow(self,
                                     old_pred_uri,
                                     new_pred_uri,
                                     limits_dict):
        """ replaces annotations using
        a given old_predicate with a new one
        """
        if 'object_uri_root' in limits_dict:
            object_uri_root = limits_dict['object_uri_root']
            alt_old_pred = self.make_alt_uri(old_pred_uri)
            la_objs = LinkAnnotation.objects\
                                    .filter(Q(predicate_uri=old_pred_uri) |
                                            Q(predicate_uri=alt_old_pred))\
                                    .filter(object_uri__startswith=object_uri_root)
            print('Change predicates for annotations: ' + str(len(la_objs)))
            for la_obj in la_objs:
                ok_edit = True
                if 'subject_type' in limits_dict:
                    if la_obj.subject_type != limits_dict['subject_type']:
                        ok_edit = False
                if 'data_type' in limits_dict:
                    data_type = limits_dict['data_type']
                    predicate = False
                    try:  # try to find the predicate with a given data_type
                        predicate = Predicate.objects.get(uuid=la_obj.subject)
                    except Predicate.DoesNotExist:
                        print('Cant find predicate: ' + str(la_obj.subject))
                        predicate = False
                    if predicate is False:
                        ok_edit = False
                    else:
                        if predicate.data_type != data_type:
                            print(str(predicate.data_type) + ' wrong data_type in: ' + str(la_obj.subject))
                if ok_edit:
                    print('Editing annotation to subject: ' + str(la_obj.subject))
                    new_la = la_obj
                    new_la.predicate_uri = new_pred_uri
                    LinkAnnotation.objects\
                                  .filter(hash_id=la_obj.hash_id).delete()
                    new_la.save()
                else:
                    print('NO EDIT to subject: ' + str(la_obj.subject))

    def replace_object_uri(self,
                           old_object_uri,
                           new_object_uri):
        """ replaces annotations using
        a given old_object_uri with a new one
        """
        alt_old_obj = self.make_alt_uri(old_object_uri)
        la_objs = LinkAnnotation.objects\
                                .filter(Q(object_uri=old_object_uri) |
                                        Q(object_uri=alt_old_obj))
        print('Change object_uri for annotations: ' + str(len(la_objs)))
        for la_obj in la_objs:
            new_la = la_obj
            new_la.object_uri = new_object_uri
            LinkAnnotation.objects\
                          .filter(hash_id=la_obj.hash_id).delete()
            try:
                new_la.save()
            except Exception as error:
                print("Error: " + str(error))

    def make_alt_uri(self, uri):
        """ makes an alternative URI, changing a prefixed to a full
            uri or a full uri to a prefix
        """
        output = uri
        if(uri[:7] == 'http://' or uri[:8] == 'https://'):
            output = URImanagement.prefix_common_uri(uri)
        else:
            output = URImanagement.convert_prefix_to_full_uri(uri)
        return output
