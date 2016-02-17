import hashlib
from django.db import models
from django.db.models import Q
from opencontext_py.apps.ldata.linkannotations.models import LinkAnnotation
from opencontext_py.apps.ldata.linkentities.models import LinkEntity
from opencontext_py.apps.ocitems.assertions.models import Assertion
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.entities.uri.models import URImanagement
from opencontext_py.apps.ocitems.predicates.models import Predicate
from opencontext_py.apps.ldata.linkannotations.recursion import LinkRecursion
from opencontext_py.apps.ldata.linkannotations.equivalence import LinkEquivalence


class LinkAnnoManagement():
    """
        Some useful methods for changing linked data annoations.

from opencontext_py.apps.ldata.linkannotations.manage import LinkAnnoManagement
lam = LinkAnnoManagement()
project_uuid = 'd1c85af4-c870-488a-865b-b3cf784cfc60'
lam.make_von_den_driesch_equiv(project_uuid)

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

    def replace_subject_uri(self,
                            old_subject_uri,
                            new_subject_uri):
        """ replaces annotations using
        a given old_object_uri with a new one
        """
        lequiv = LinkEquivalence()
        old_subj_list = lequiv.get_identifier_list_variants(old_subject_uri)
        la_subjs = LinkAnnotation.objects\
                                 .filter(subject__in=old_subj_list)
        print('Change subjects for annotations: ' + str(len(la_subjs)))
        for la_subj in la_subjs:
            old_hash = la_subj.hash_id
            new_la = la_subj
            new_la.subject = new_subject_uri
            try:
                new_la.save()
                ok = True
            except Exception as error:
                ok = False
                print("Error: " + str(error))
            if ok:
                LinkAnnotation.objects\
                              .filter(hash_id=old_hash).delete()

    def replace_predicate_uri(self,
                              old_pred_uri,
                              new_pred_uri):
        """ replaces annotations using
        a given old_predicate with a new one
        """
        lequiv = LinkEquivalence()
        old_pred_list = lequiv.get_identifier_list_variants(old_pred_uri)
        la_preds = LinkAnnotation.objects\
                                 .filter(predicate_uri__in=old_pred_list)
        print('Change predicates for annotations: ' + str(len(la_preds)))
        for la_pred in la_preds:
            old_hash = la_pred.hash_id
            new_la = la_pred
            new_la.predicate_uri = new_pred_uri
            try:
                new_la.save()
                ok = True
            except Exception as error:
                ok = False
            if ok:
                LinkAnnotation.objects\
                              .filter(hash_id=old_hash).delete()

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
        lequiv = LinkEquivalence()
        old_obj_list = lequiv.get_identifier_list_variants(old_object_uri)
        la_objs = LinkAnnotation.objects\
                                .filter(object_uri__in=old_obj_list)
        print('Change object_uri for annotations: ' + str(len(la_objs)))
        for la_obj in la_objs:
            old_hash = la_obj.hash_id
            new_la = la_obj
            new_la.object_uri = new_object_uri
            try:
                new_la.save()
                ok = True
            except Exception as error:
                ok = False
                print("Error: " + str(error))
            if ok:
                LinkAnnotation.objects\
                              .filter(hash_id=old_hash).delete()

    def make_von_den_driesch_equiv(self,
                                   project_uuid,
                                   equiv_pred='skos:closeMatch'):
        """ makes a skos:closeMatch equivalence relation
            between entities in the zooarch measurement
            ontology and predicates in a project
        """
        preds = Predicate.objects\
                         .filter(project_uuid=project_uuid,
                                 data_type='xsd:double')
        for pred in preds:
            man_obj = False
            try:
                # try to find the manifest item
                man_obj = Manifest.objects.get(uuid=pred.uuid)
            except Manifest.DoesNotExist:
                man_obj = False
            if man_obj is not False:
                l_ents = LinkEntity.objects\
                                   .filter(label=man_obj.label,
                                           vocab_uri='http://opencontext.org/vocabularies/open-context-zooarch/')[:1]
                if len(l_ents) > 0:
                    # a Match! Now let's make a close match assertion
                    uri = l_ents[0].uri
                    print(str(man_obj.label) + ' matches ' + uri)
                    la = LinkAnnotation()
                    la.subject = man_obj.uuid  # the subordinate is the subject
                    la.subject_type = man_obj.item_type
                    la.project_uuid = man_obj.project_uuid
                    la.source_id = 'label-match'
                    la.predicate_uri = equiv_pred
                    la.object_uri = uri
                    la.save()

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
