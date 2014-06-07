from django.conf import settings
from opencontext_py.apps.ocitems.namespaces.models import ItemNamespaces


class URImanagement():
    """ Functions for dealing with URIs """
    def convert_prefix_to_full_uri(identifier):
        """ Checks to see if a an identifer is a prefixed URI,
            if so, it will convert to a full uri 
        """
        if(':' in identifier):
            split_id = True
            if(len(identifier) > 8):
                if(identifier[:7] == 'http://' and identifier[:8] == 'https://'):
                    split_id = False
            if(split_id):
                item_ns = ItemNamespaces()
                identifier_parts = identifier.split(':')
                prefix = identifier_parts[0]
                suffix = identifier_parts[1]
                if(prefix in item_ns.namespaces):
                    identifier = str(item_ns.namespaces[prefix]) + str(suffix)
        return identifier

    def get_uuid_from_oc_uri(uri, return_type=False):
        """ Gets a UUID and, if wanted item type from an Open Context URI """
        output = False
        if(uri.count('/') > 1):
            uri_parts = uri.split('/')
            uuid = uri_parts[(len(uri_parts) - 1)]
            item_type = uri_parts[(len(uri_parts) - 2)]
            if(item_type in (item[0] for item in settings.ITEM_TYPES)):
                # checks to make sure the item is an OC item type
                output = uuid
                if(return_type):
                    output = {'item_type': item_type, 'uuid': uuid}
        return output

    def make_oc_uri(uuid_or_slug, item_type, do_cannonical=True):
        """
        creates a URI for an item based on its uuid and its item_type
        """
        uri = False
        uuid_or_slug = str(uuid_or_slug)
        item_type = str(item_type)
        if(do_cannonical):
            uri = settings.CANONICAL_HOST + "/" + item_type + "/" + uuid_or_slug
        else:
            uri = "http://" + settings.HOSTNAME + "/" + item_type + "/" + uuid_or_slug
        return uri
