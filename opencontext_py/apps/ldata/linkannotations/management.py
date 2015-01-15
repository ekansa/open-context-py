import hashlib
from django.db import models
from django.db.models import Q
from opencontext_py.apps.ldata.linkannotations.models import LinkAnnotation
from opencontext_py.apps.ldata.linkentities.models import LinkEntity
from opencontext_py.apps.ocitems.assertions.models import Assertion
from opencontext_py.apps.entities.uri.models import URImanagement


class LinkAnnoManagement():
    """
        Some useful methods for changing linked data annoations.
    """
    def __init__(self):
        pass

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
