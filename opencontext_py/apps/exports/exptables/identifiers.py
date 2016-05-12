from django.conf import settings
from opencontext_py.apps.entities.uri.models import URImanagement
from opencontext_py.apps.ocitems.identifiers.models import StableIdentifer


class ExpTableIdentifiers():
    """
    Methods for managing identifiers of tables. This is needed because
    of legacy export tables that have a '/', indicating that they
    are parts of a larger group of exported tables.
    """

    def __init__(self):
        self.table_id = None
        self.public_table_id = None
        self.uri = None

    def make_all_identifiers(self, identifier):
        """ makes all identifiers
            used with an export table, based on a given identifier
            if the given identifier has a '_' or '/' character,
            it is either internal to Open Context ('_') or from
            an expernal URI ('/')
        """
        if '/' in identifier:
            id_ex = identifier.split('/')
            self.table_id = id_ex[1] + '_' + id_ex[0]
            self.public_table_id = identifier
            self.uri = URImanagement.make_oc_uri(self.public_table_id, 'tables')
        elif '_' in identifier:
            id_ex = identifier.split('_')
            self.table_id = identifier
            self.public_table_id = id_ex[1] + '/' + id_ex[0]
            self.uri = URImanagement.make_oc_uri(self.public_table_id, 'tables')
        else:
            self.table_id = identifier
            self.public_table_id = identifier
            self.uri = URImanagement.make_oc_uri(self.public_table_id, 'tables')
