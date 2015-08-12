from django.conf import settings
from django.db import models
from opencontext_py.apps.entities.uri.models import URImanagement
from opencontext_py.apps.ldata.linkannotations.equivalence import LinkEquivalence
from opencontext_py.apps.ldata.linkentities.models import LinkEntity


class ManifestClasses():
    """
    This class has useful methods for validating class_uris for the manifest
    """

    VALID_OC_CLASS_VOCABS = ['http://opencontext.org/vocabularies/oc-general/']

    def __init__(self):
        self.oc_class_vocabs = '';
        self.allow_blank = True

    def validate_class_uri(self, class_uri):
        """ validates a class_uri as actually
            identifiying a known class. Useful for making sure data
            entry is OK for the manifest table
        """
        output = False
        if len(class_uri) > 0:
            le = LinkEquivalence()
            class_list = le.get_identifier_list_variants(class_uri)
            link_entities = LinkEntity.objects\
                                      .filter(uri__in=class_list,
                                              vocab_uri__in=self.VALID_OC_CLASS_VOCABS)[:1]
            if len(link_entities) > 0:
                # OK! We found it. now make it prefixed for use in the manifest table
                full_class_uri = link_entities[0].uri
                output = URImanagement.prefix_common_uri(full_class_uri)
        else:
            if self.allow_blank:
                # we are allowing blank values for no class_uri to be OK
                output = ''
        return output
