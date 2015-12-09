from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.apps.entities.entity.models import Entity
from opencontext_py.apps.ldata.eol.api import eolAPI
from opencontext_py.apps.ldata.linkentities.models import LinkEntity, LinkEntityGeneration
from opencontext_py.apps.ldata.linkannotations.equivalence import LinkEquivalence
from opencontext_py.apps.ldata.linkannotations.models import LinkAnnotation


class EOLmanage():
    """ Methods to clean EOL references and
        add missing labels
    """
    EOL_VOCAB_URI = 'http://eol.org/'
    EOL_URI_PREFIX = 'http://eol.org/pages/'

    def __init__(self):
        self.eol_data = False

    def validate_fix_eol_objects(self):
        """ Searches for EOL links in the
            LinkAnnotations table, then fixes
            badly URIs with cruft. Also
            calls the EOL API to get labels
            for URIs with no record in the LinkEntity
            table.
        """
        checked_uris = []
        eol_las = LinkAnnotation.objects\
                                .filter(object_uri__icontains=self.EOL_URI_PREFIX)
        for eol_la in eol_las:
            eol_uri = eol_la.object_uri
            leg = LinkEntityGeneration()
            le_gen = LinkEntityGeneration()
            eol_uri = le_gen.make_clean_uri(eol_uri)  # strip off any cruft in the URI
            if eol_uri != eol_la.object_uri:
                print('Has cruft: ' + str(eol_la.object_uri))
                LinkAnnotation.objects\
                              .filter(hash_id=eol_la.hash_id)\
                              .delete() # delete the old
                eol_la.object_uri = eol_uri
                eol_la.save()  # save the cleaned URI
            if eol_uri not in checked_uris:
                # only check on a given URI once
                checked_uris.append(eol_uri)
                try:
                    le = LinkEntity.objects.get(uri=eol_uri)
                except LinkEntity.DoesNotExist:
                    le = False
                if le is False:
                    print('Getting missing data for: ' + eol_uri)
                    label = False
                    eol_api = eolAPI()
                    eol_data = eol_api.get_basic_json_for_eol_uri(eol_uri)
                    if isinstance(eol_data, dict):
                        print('Reading data...')
                        if 'scientificName' in eol_data:
                            label = eol_data['scientificName']
                    else:
                        print('Failed to read data: ' + str(eol_data))
                    if label is not False:
                        print('Saving data for: ' + str(label) + ' (' + eol_uri + ')')
                        le = LinkEntity()
                        le.uri = eol_uri
                        le.label = label
                        le.alt_label = label
                        le.ent_type = 'class'
                        le.vocab_uri = self.EOL_VOCAB_URI
                        le.save()
