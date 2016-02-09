import json
from django.conf import settings
from django.db import connection
from django.db import models
from opencontext_py.libs.rootpath import RootPath
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.libs.memorycache import MemoryCache
from opencontext_py.apps.searcher.solrsearcher.recordprops import RecordProperties
from opencontext_py.apps.ocitems.assertions.models import Assertion
from opencontext_py.apps.ocitems.mediafiles.models import Mediafile


class SolrUUIDs():
    """ methods to make get UUIDs from a solr
        search result JSON document,

        also makes URIs
    """

    def __init__(self, response_dict_json=False):
        rp = RootPath()
        self.base_url = rp.get_baseurl()
        self.uuids = []
        self.uris = []
        self.mem_cache_obj = MemoryCache()  # memory caching object
        self.response_dict_json = response_dict_json
        self.highlighting = False
        # make values to these fields "flat" not a list
        self.flatten_rec_fields = True
        self.total_found = False
        self.rec_start = False
        self.min_date = False
        self.max_date = False
        # flatten list of an attribute values to single value
        self.flatten_rec_attributes = False
        # A list of (non-standard) attributes to include in a record
        self.rec_attributes = []
        self.do_media_thumbs = True  # get thumbnails for records

    def make_uuids_from_solr(self, solr_json):
        """ makes geojson-ld point records from a solr response """
        #first do lots of checks to make sure the solr-json is OK
        solr_recs = self.extract_solr_recs(solr_json)
        if isinstance(solr_recs, list):
            for solr_rec in solr_recs:
                if 'uuid' in solr_rec:
                    uuid = solr_rec['uuid']
                    self.uuids.append(uuid)
        return self.uuids

    def make_uris_from_solr(self, solr_json, uris_only=True):
        """ processes the solr_json to
             make GeoJSON records
        """
        solr_recs = self.extract_solr_recs(solr_json)
        if isinstance(solr_recs, list):
            if uris_only:
                self.do_media_thumbs = False
            thumbnail_data = self.get_media_thumbs(solr_recs)
            for solr_rec in solr_recs:
                rec_props_obj = RecordProperties(self.response_dict_json)
                rec_props_obj.mem_cache_obj = self.mem_cache_obj
                rec_props_obj.min_date = self.min_date
                rec_props_obj.max_date = self.max_date
                rec_props_obj.highlighting = self.highlighting
                rec_props_obj.flatten_rec_attributes = self.flatten_rec_attributes
                rec_props_obj.rec_attributes = self.rec_attributes
                rec_props_obj.thumbnail_data = thumbnail_data
                item_ok = rec_props_obj.get_item_basics(solr_rec)
                if item_ok:
                    if uris_only:
                        item = rec_props_obj.uri
                    else:
                        rec_props_obj.parse_solr_record(solr_rec)
                        self.mem_cache_obj = rec_props_obj.mem_cache_obj  # add to existing list of entities, reduce lookups
                        item = self.make_item_dict_from_rec_props_obj(rec_props_obj)
                    self.uris.append(item)
        return self.uris

    def make_item_dict_from_rec_props_obj(self, rec_props_obj, cannonical=True):
        """ makes item dictionary object from a record prop obj """
        item = LastUpdatedOrderedDict()
        item['uri'] = rec_props_obj.uri
        if cannonical is False:
            item['href'] = rec_props_obj.href
        item['citation uri'] = rec_props_obj.cite_uri
        item['label'] = rec_props_obj.label
        item['project label'] = rec_props_obj.project_label
        if cannonical:
            item['project uri'] = rec_props_obj.project_uri
        else:
            item['project href'] = rec_props_obj.project_href
        item['context label'] = rec_props_obj.context_label
        if cannonical:
            item['context uri'] = rec_props_obj.context_uri
        else:
            item['context href'] = rec_props_obj.context_href
        item['latitude'] = rec_props_obj.latitude
        item['longitude'] = rec_props_obj.longitude
        item['early bce/ce'] = rec_props_obj.early_date
        item['late bce/ce'] = rec_props_obj.late_date
        item['item category'] = rec_props_obj.category
        if rec_props_obj.snippet is not False:
            item['snippet'] = rec_props_obj.snippet
        item['published'] = rec_props_obj.published
        item['updated'] = rec_props_obj.updated
        if isinstance(rec_props_obj.other_attributes, list):
            for attribute in rec_props_obj.other_attributes:
                prop_key = attribute['property']
                prop_key = rec_props_obj.prevent_attribute_key_collision(item,
                                                                         prop_key)
                if self.flatten_rec_attributes:
                    item[prop_key] = attribute['value']
                else:
                    item[prop_key] = attribute['values_list']
        return item

    def extract_solr_recs(self, solr_json):
        """ extracts solr_recs along with
           some basic metadata from solr_json
        """
        solr_recs = False
        if isinstance(solr_json, dict):
            try:
                self.total_found = solr_json['response']['numFound']
            except KeyError:
                self.total_found = False
            try:
                self.rec_start = solr_json['response']['start']
            except KeyError:
                self.rec_start = False
            try:
                self.highlighting = solr_json['highlighting']
            except KeyError:
                self.highlighting = False
            try:
                solr_recs = solr_json['response']['docs']
            except KeyError:
                solr_recs = False
        return solr_recs

    def get_media_thumbs(self, solr_recs):
        """ gets media thumbnail items """
        thumb_results = {}
        not_media_uuids = []
        media_uuids = []
        rec_props_obj = RecordProperties(self.response_dict_json)
        for solr_rec in solr_recs:
            item = rec_props_obj.get_solr_record_uuid_type(solr_rec)
            if item is not False:
                uuid = item['uuid']
                if item['item_type'] != 'media':
                    not_media_uuids.append(uuid)
                else:
                    media_uuids.append(uuid)
                thumb_results[uuid] = False
        if len(not_media_uuids) > 0:
            if self.do_media_thumbs:
                # only get media_thumbnails if needed
                rows = self.get_thumbs_for_non_media(not_media_uuids)
                for row in rows:
                    uuid = row['uuid']
                    thumb_obj = {}
                    thumb_obj['href'] = self.base_url + '/media/' + row['media_uuid']
                    thumb_obj['uri'] = settings.CANONICAL_HOST + '/media/' + row['media_uuid']
                    thumb_obj['scr'] = row['file_uri']
                    if thumb_results[uuid] is False:
                        thumb_results[uuid] = thumb_obj
        if len(media_uuids) > 0:
            thumbs = Mediafile.objects\
                              .filter(uuid__in=media_uuids,
                                      file_type='oc-gen:thumbnail')
            for thumb in thumbs:
                uuid = thumb.uuid
                thumb_obj = {}
                thumb_obj['href'] = self.base_url + '/media/' + thumb.uuid
                thumb_obj['uri'] = settings.CANONICAL_HOST + '/media/' + thumb.uuid
                thumb_obj['scr'] = thumb.file_uri
                thumb_results[uuid] = thumb_obj
        return thumb_results

    def get_thumbs_for_non_media(self, uuid_list):
        q_uuids = self.make_quey_uuids(uuid_list)
        query = ('SELECT ass.uuid AS uuid, m.file_uri AS file_uri, '
                 'm.uuid AS media_uuid '
                 'FROM oc_assertions AS ass '
                 'JOIN oc_mediafiles AS m ON ass.object_uuid = m.uuid '
                 'AND m.file_type=\'oc-gen:thumbnail\'  '
                 'WHERE ass.uuid IN (' + q_uuids + ') '
                 'GROUP BY ass.uuid,  m.file_uri, m.uuid; ')
        cursor = connection.cursor()
        cursor.execute(query)
        rows = self.dictfetchall(cursor)
        return rows

    def make_quey_uuids(self, uuid_list):
        """ makes a string for uuid list query """
        uuid_q = []
        for uuid in uuid_list:
            uuid = '\'' + uuid + '\''
            uuid_q.append(uuid)
        return ', '.join(uuid_q)

    def dictfetchall(self, cursor):
        """ Return all rows from a cursor as a dict """
        columns = [col[0] for col in cursor.description]
        return [
            dict(zip(columns, row))
            for row in cursor.fetchall()
        ]
