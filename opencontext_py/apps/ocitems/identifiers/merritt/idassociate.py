import sys
import csv
import os
import datetime
import time
import re
from time import mktime
from time import sleep
from django.conf import settings
from opencontext_py.apps.entities.uri.models import URImanagement
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.ocitems.identifiers.models import StableIdentifer
from opencontext_py.apps.ocitems.identifiers.merritt.feed import MerrittFeed


class StableIDassociate():
    """ methods associate stable identifiers from Merritt
        with items in Open Context
    """

    def __init__(self):
        self.request_error = False
        self.id_recorded = 0
        self.base_wait = 300
        self.max_wait = self.base_wait * 5
        self.go_backwards = False
        self.url = False
        self.DEFAULT_DIRECTORY = 'exports'

    def associate_ids(self, feed_url=False):
        """ match ids """
        mf = MerrittFeed()
        ids = mf.get_ids_from_merritt_feed(feed_url)
        ids_done = self.add_ids(ids)
        print('Added stable identifiers: ' + str(len(ids)) + ' total added: ' + str(ids_done))
        if mf.next_page is not False and self.go_backwards is False:
            self.url = mf.next_page
            print('Continuing to next batch...')
            self.associate_ids(mf.next_page)
        elif mf.prev_page is not False and self.go_backwards:
            self.url = mf.prev_page
            print('Continuing to next batch (backwards)...')
            self.associate_ids(mf.prev_page)
        else: 
            print('Done for now.')

    def add_ids(self, ids):
        """ Adds ids to the database
        """
        if isinstance(ids, list):
            for id_rec in ids:
                id_and_type = self.parse_stable_id(id_rec['stable_id'])
                manifest = False
                uuid = URImanagement.get_uuid_from_oc_uri(id_rec['id'])
                if uuid is not False and id_and_type is not False:
                    try:
                        manifest = Manifest.objects.get(uuid=uuid)
                    except Manifest.DoesNotExist:
                        manifest = False
                if manifest is not False:
                    # we found the archived item in the manifest
                    # save the stable identifier in the database
                    ok_new = True
                    try:
                        sid = StableIdentifer()
                        sid.stable_id = id_and_type['id']
                        sid.stable_type = id_and_type['type']
                        sid.uuid = manifest.uuid
                        sid.project_uuid = manifest.project_uuid
                        sid.item_type = manifest.item_type
                        sid.save()
                    except:
                        ok_new = False
                    # note when the item was last archived
                    try:
                        manifest.archived = self.validate_date(id_rec['archived'])
                        manifest.archived_save()
                    except:
                        manifest.archived = time.strftime('%Y-%m-%d %H:%M:%S')
                        manifest.archived_save()
                    if ok_new:
                        self.id_recorded += 1
        return self.id_recorded

    def validate_date(self, date_text):
        q_dt_strs = re.findall(r'\d{4}-\d{2}-\d{2}[\s]\d{2}:\d{2}:\d{2}', date_text)
        if len(q_dt_strs) == 1:
            date_text = q_dt_strs[0]
        try:
            output = date_text
            datetime.datetime.strptime(date_text, '%Y-%m-%d %H:%M:%S')
        except ValueError:
            output = time.strftime('%Y-%m-%d %H:%M:%S')
        return output

    def parse_stable_id(self, stable_uri):
        """ Parses a stable ID to into components
            so we can classify ARKs, DOIs, etc.
        """
        output = False
        for type_key, uri_prefix in settings.STABLE_ID_URI_PREFIXES.items():
            if uri_prefix in stable_uri:
                output = {'type': type_key,
                          'id': stable_uri.replace(uri_prefix, '')}
                break
        return output

    def load_csv(self, filename, after=0, add_path=False):
        """ loads CSV dump from Merritt """
        if add_path:
            filename_path = os.path.join(settings.STATIC_ROOT,
                                         self.DEFAULT_DIRECTORY,
                                         filename)
        else:
            filename_path = filename
        data = csv.reader(open(filename_path))
        i = 0
        for row in data:
            manifest = False
            if 'ark:/' in row[0]:
                i += 0
                if i >= after:
                    uuid = URImanagement.get_uuid_from_oc_uri(row[1])
                    if uuid is not False:
                        try:
                            manifest = Manifest.objects.get(uuid=uuid,
                                                            archived__isnull=True)
                        except Manifest.DoesNotExist:
                            manifest = False
                    if manifest is not False:
                        ok_new = True
                        try:
                            sid = StableIdentifer()
                            sid.stable_id = row[0].replace('ark:/', '')
                            sid.stable_type = 'ark'
                            sid.uuid = manifest.uuid
                            sid.project_uuid = manifest.project_uuid
                            sid.item_type = manifest.item_type
                            sid.save()
                        except:
                            ok_new = False
                        # note when the item was last archived
                        try:
                            manifest.archived = self.validate_date(row[3])
                            manifest.archived_save()
                        except:
                            manifest.archived = time.strftime('%Y-%m-%d %H:%M:%S')
                            manifest.archived_save()
                        if ok_new:
                            self.id_recorded += 1
                        print('Saved ids: ' + str(self.id_recorded))
