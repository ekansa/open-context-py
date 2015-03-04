import sys
from time import sleep
from opencontext_py.apps.entities.uri.models import URImanagement
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.ocitems.identifiers.models import StableIdentifer
from opencontext_py.apps.ocitems.identifiers.merritt.feed import MerrittFeed


class StableIDmatch():
    """ methods associate stable identifiers from Merritt
        with items in Open Context
    """

    def __init__(self):
        self.request_error = False
        self.error_wait = 0  # wait if problem to send next request
        self.base_wait = 300
        self.max_wait = self.base_wait * 5

    def match_ids(self, feed_url=False):
        """ match ids """
        mf = MerrittFeed()
        ids = mf.get_ids_from_merritt_feed(feed_url)

    def add_ids(self, ids):
        """ Adds ids to the database
        """
        found_matches = 0
        if isinstance(ids, list):
            for id_rec in ids:
                manifest = False
                uuid = URImanagement.get_uuid_from_oc_uri(id_rec['id'])
                if uuid is not False:
                    try:
                        manifest = Manifest.objects.get(uuid=tri.uuid)
                    except Manifest.DoesNotExist:
                        manifest = False
                if manifest is not False:
                    # we found the archived item in the manifest
                    sid = StableIdentifer()
                    sid.stable_id

    def parse_stable_id(self, stable_uri):
        """ Parses a stable ID to into components
            so we can classify ARKs, DOIs, etc.
        """
        if 'http://n2t.net/ark:' in stable_uri:
            pass