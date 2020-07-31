from django.conf import settings
from opencontext_py.apps.ocitems.namespaces.models import ItemNamespaces


class URImanagement():
    """ Functions for dealing with URIs """
    def convert_prefix_to_full_uri(identifier):
        """ Checks to see if a an identifer is a prefixed URI,
            if so, it will convert to a full uri
        """
        if ':' in identifier:
            if not identifier.startswith('http://') and not identifier.startswith('https://'):
                item_ns = ItemNamespaces()
                identifier_parts = identifier.split(':')
                prefix = identifier_parts[0]
                suffix = identifier_parts[1]
                if prefix in item_ns.namespaces:
                    identifier = str(item_ns.namespaces[prefix]) + str(suffix)
        return identifier

    def prefix_common_uri(identifier):
        """ Converts URIs to a prefixed URI if it is in a
        namespace used by Open Context JSON-LD @context
        """
        if(identifier.startswith('http://') or identifier.startswith('https://')):
            item_ns = ItemNamespaces()
            for prefix, ns_uri in item_ns.namespaces.items():
                if identifier.startswith(ns_uri) and identifier.split(ns_uri)[-1]:
                    identifier = prefix + ':' + identifier.split(ns_uri)[-1]
                    break
        return identifier

    def get_uuid_from_oc_uri(uri, return_type=False):
        """ Gets a UUID and, if wanted item type from an Open Context URI """
        if not isinstance(uri, str):
            return False
        http_start = settings.CANONICAL_HOST.replace('https://', 'http://')
        https_start = settings.CANONICAL_HOST.replace('http://', 'https://')
        if not uri.startswith(http_start) and not uri.startswith(https_start):
            # We're not in the Open context domain. So no UUID to be had.
            return False
        if uri.endswith('/'):
            # Trim off a tailing suffix
            uri = uri[0:-1]
        uri_parts = uri.split('/')
        if len(uri_parts) < 5:
            # Not an Open Context URI. Wrong number of parts.
            return False
        item_type = uri_parts[3]
        if item_type == 'vocabularies' or len(uri_parts) > 5:
            # No UUID for this, it is from an item type that does not
            # have our normal identifier.
            return False
        else:
            uuid = uri_parts[4]
        item_types = [t for t, _ in settings.ITEM_TYPES]
        if item_type not in item_types:
            # This is not an Open Context item type
            return False
            # Checks to make sure the item is an OC item type
        if return_type:
            return {'item_type': item_type, 'uuid': uuid}
        else:
            return uuid

    def make_oc_uri(uuid_or_slug, item_type, do_cannonical=True, do_https=False):
        """
        creates a URI for an item based on its uuid and its item_type
        """
        uri_prefix = 'http://'
        if do_https:
            uri_prefix = 'https://'
        uuid_or_slug = str(uuid_or_slug)
        item_type = str(item_type)
        if do_cannonical:
            uri = settings.CANONICAL_HOST + '/' + item_type + '/' + uuid_or_slug
        else:
            uri = uri_prefix + settings.HOSTNAME + '/' + item_type + '/' + uuid_or_slug
        return uri
