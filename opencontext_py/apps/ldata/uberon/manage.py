from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.apps.entities.entity.models import Entity
from opencontext_py.apps.ldata.uberon.api import uberonAPI
from opencontext_py.apps.ldata.linkentities.models import LinkEntity, LinkEntityGeneration
from opencontext_py.apps.ldata.linkannotations.equivalence import LinkEquivalence
from opencontext_py.apps.ldata.linkannotations.models import LinkAnnotation


class UberonManage():
    """ Methods to clean Uberon references and
        add missing labels
    """
    UBERON_VOCAB_URI = 'http://uberon.org/'
    UBERON_URI_PREFIX = 'http://purl.obolibrary.org/obo/UBERON'

    def __init__(self):
        self.graph = False

    def validate_fix_uberon_objects(self):
        """ Searches for UBERON links in the
            LinkAnnotations table, then fixes
            badly URIs with cruft. Also
            calls the UBERON API to get labels
            for URIs with no record in the LinkEntity
            table.
        """
        checked_uris = []
        uberon_las = LinkAnnotation.objects\
                                   .filter(object_uri__icontains=self.UBERON_URI_PREFIX)
        for uberon_la in uberon_las:
            uberon_uri = uberon_la.object_uri
            le_gen = LinkEntityGeneration()
            uberon_uri = le_gen.make_clean_uri(uberon_uri)  # strip off any cruft in the URI
            if uberon_uri != uberon_la.object_uri:
                print('Has cruft: ' + str(uberon_la.object_uri))
                LinkAnnotation.objects\
                              .filter(hash_id=uberon_la.hash_id)\
                              .delete()  # delete the old
                uberon_la.object_uri = uberon_uri
                uberon_la.save()  # save the cleaned URI
            if uberon_uri not in checked_uris:
                # only check on a given URI once
                checked_uris.append(uberon_uri)
                try:
                    le = LinkEntity.objects.get(uri=uberon_uri)
                except LinkEntity.DoesNotExist:
                    le = False
                if le is False:
                    print('Getting missing data for: ' + uberon_uri)
                    u_api = uberonAPI()
                    label = u_api.get_uri_label_from_graph(uberon_uri)
                    if label is False:
                        print('Failed to read data for : ' + str(uberon_uri))
                    else:
                        print('Saving data for: ' + str(label) + ' (' + uberon_uri + ')')
                        le = LinkEntity()
                        le.uri = uberon_uri
                        le.label = label
                        le.alt_label = label
                        le.ent_type = 'class'
                        le.vocab_uri = self.UBERON_VOCAB_URI
                        le.save()
