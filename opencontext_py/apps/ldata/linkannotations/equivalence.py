import hashlib
from django.db import models
from opencontext_py.apps.ldata.linkannotations.models import LinkAnnotation
from opencontext_py.apps.entities.uri.models import URImanagement
from opencontext_py.apps.entities.entity.models import Entity
from opencontext_py.libs.general import LastUpdatedOrderedDict


class LinkEquivalence():
    """
    Does lookups on LinkAnnotations to find eqivalences
    """
    def __init__(self):
        pass

    def get_from_object(self, object_uri):
        """
        The subjects equivalent to a given object_uri
        """
        p_for_equiv = self.get_identifier_list_variants(LinkAnnotation.PREDS_SBJ_EQUIV_OBJ)
        object_uris = self.get_identifier_list_variants(object_uri)
        lsubs = LinkAnnotation.objects\
                              .filter(predicate_uri__in=p_for_equiv,
                                      object_uri__in=object_uris)\
                              .value_list('subject', flat=True)\
                              .distinct()
        output = []
        for lsub in lsubs:
            output.append(str(lsub))
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
            if(identifier[:7] == 'http://' or identifier[:8] == 'https://'):
                oc_uuid = URImanagement.get_uuid_from_oc_uri(identifier)
                if oc_uuid is not False:
                    output_list.append(oc_uuid)
                else:
                    prefix_id = URImanagement.prefix_common_uri(identifier)
                    output_list.append(prefix_id)
            elif ':' in identifier:
                full_uri = URImanagement.convert_prefix_to_full_uri(identifier)
                output_list.append(full_uri)
        return output_list
