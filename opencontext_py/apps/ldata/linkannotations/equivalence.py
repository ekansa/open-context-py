import hashlib
from django.db import models

from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.libs.memorycache import MemoryCache

from opencontext_py.apps.ldata.linkannotations.models import LinkAnnotation
from opencontext_py.apps.ocitems.predicates.models import Predicate
from opencontext_py.apps.entities.uri.models import URImanagement
from opencontext_py.apps.entities.entity.models import Entity


class LinkEquivalence():
    """
    Does lookups on LinkAnnotations to find eqivalences
    """
    def __init__(self):
        self.predicates = {}

    def get_from_object(self, object_uri):
        """
        Gets the subjects equivalent to a given object_uri
        """
        p_for_equiv = self.get_identifier_list_variants(LinkAnnotation.PREDS_SBJ_EQUIV_OBJ)
        object_uris = self.get_identifier_list_variants(object_uri)
        lsubs = LinkAnnotation.objects\
                              .filter(predicate_uri__in=p_for_equiv,
                                      object_uri__in=object_uris)\
                              .values_list('subject', flat=True)\
                              .distinct('subject')
        output = []
        for lsub in lsubs:
            output.append(str(lsub))
        return output

    def get_subject_types_from_object(self, object_uri):
        """
        Gets the types of subjects equivalent to an object_uri
        """
        p_for_equiv = self.get_identifier_list_variants(LinkAnnotation.PREDS_SBJ_EQUIV_OBJ)
        object_uris = self.get_identifier_list_variants(object_uri)
        lsubs = LinkAnnotation.objects\
                              .values_list('subject_type', flat=True)\
                              .filter(predicate_uri__in=p_for_equiv,
                                      object_uri__in=object_uris)
        output = []
        for lsub in lsubs:
            output.append(str(lsub))
        return output

    def get_data_types_from_object(self, object_uri):
        """
        Gets the data types for predicates equivalent to an object_uri
        """
        p_for_equiv = self.get_identifier_list_variants(LinkAnnotation.PREDS_SBJ_EQUIV_OBJ)
        object_uris = self.get_identifier_list_variants(object_uri)
        p_tab = 'oc_predicates'
        filters = 'oc_predicates.uuid=link_annotations.subject'
        dtypes = LinkAnnotation.objects\
                               .values_list('subject', flat=True)\
                               .filter(predicate_uri__in=p_for_equiv,
                                       object_uri__in=object_uris)\
                               .extra(tables=[p_tab], where=[filters])
        output = False
        if len(dtypes) > 0:
            output = []
            predicate_uuids = []
            for uuid in dtypes:
                if uuid not in self.predicates:
                    # only query for un-retrieved predicates
                    predicate_uuids.append(uuid)
            # get unretrieved predicates from the database
            pred_list = Predicate.objects\
                                 .filter(uuid__in=predicate_uuids)
            for pred_obj in pred_list:
                uuid = pred_obj.uuid
                self.predicates[uuid] = pred_obj
            for uuid in dtypes:
                pred_obj = False
                if uuid in self.predicates:
                    pred_obj = self.predicates[uuid]
                if pred_obj is not False:
                    if pred_obj.data_type not in output:
                        output.append(pred_obj.data_type)
        return output

    def get_identifier_list_variants(self, id_list):
        """ makes different variants of identifiers
            for a list of identifiers
        """
        output_list = []
        if not isinstance(id_list, list):
            id_list = [str(id_list)]
        for identifier in id_list:
            output_list.append(identifier)
            if(identifier.startswith('http://') or identifier.startswith('https://')):
                oc_uuid = URImanagement.get_uuid_from_oc_uri(identifier)
                if oc_uuid:
                    output_list.append(oc_uuid)
                prefix_id = URImanagement.prefix_common_uri(identifier)
                if prefix_id:
                    output_list.append(prefix_id)
            elif ':' in identifier:
                full_uri = URImanagement.convert_prefix_to_full_uri(identifier)
                output_list.append(full_uri)
            else:
                # probably an open context uuid or a slug
                m_cache = MemoryCache()
                ent = m_cache.get_entity(identifier)
                if ent:
                    full_uri = ent.uri
                    output_list.append(full_uri)
                    prefix_uri = URImanagement.prefix_common_uri(full_uri)
                    if prefix_uri != full_uri:
                        output_list.append(prefix_uri)
        return output_list
