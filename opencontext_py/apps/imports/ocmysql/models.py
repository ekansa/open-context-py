import json
import requests
from django.db.models import Avg, Max, Min
from opencontext_py.apps.ldata.linkannotations.models import LinkAnnotation as LinkAnnotation
from opencontext_py.apps.ldata.linkentities.models import LinkEntity as LinkEntity
from opencontext_py.apps.ocitems.manifest.models import Manifest as Manifest
from opencontext_py.apps.ocitems.mediafiles.models import Mediafile as Mediafile
from opencontext_py.apps.ocitems.persons.models import Person as Person
from opencontext_py.apps.ocitems.projects.models import Project as Project
from opencontext_py.apps.ocitems.documents.models import OCdocument as OCdocument
from opencontext_py.apps.ocitems.strings.models import OCstring as OCstring
from opencontext_py.apps.ocitems.octypes.models import OCtype as OCtype
from opencontext_py.apps.ocitems.predicates.models import Predicate as Predicate
from opencontext_py.apps.ocitems.projects.models import Project as Project
from opencontext_py.apps.ocitems.geospace.models import Geospace
from opencontext_py.apps.ocitems.events.models import Event
from opencontext_py.apps.ocitems.identifiers.models import StableIdentifer
from opencontext_py.apps.ocitems.obsmetadata.models import ObsMetadata

# OCmysql requests JSON-data from the MySQL datastore.
# This is useful for synching the postgres and mysql databases as a temporary measure
class OCmysql():
    LAST_UPDATE_URL = "http://oc2/export/last-updates"
    TABLE_RECORD_COUNTS_URL = "http://oc2/export/table-records-count"
    TABLE_RECORDS_URL = "http://oc2/export/table-records-mapped"
    TABLES = ['link_annotations']
    mysql_last_updates = []
    DEFAULT_EARLY = '1970-01-01'

    def get_last_updates(self):
        """
        gets json data for last update of all mysql data tables
        """
        r = requests.get(self.LAST_UPDATE_URL, timeout=240)
        json_r = r.json()
        self.mysql_last_updates = json_r['result']
        return self.mysql_last_updates

    def get_table_records(self, act_table, after, start):
        """
        gets json data for records of a mysql datatable after a certain time
        """
        payload = {'table': act_table, 'after': after, 'start': start}
        r = requests.get(self.TABLE_RECORDS_URL, params=payload, timeout=240)
        json_r = r.json()
        return json_r['result']

    def store_records(self, act_table, recs):
        """
        stores records retrieved for a given table
        """
        for rkey, record in recs.items():
            if(act_table == 'link_annotations'):
                newr = LinkAnnotation(**record)
                newr.save()
            elif(act_table == 'link_entities'):
                newr = LinkEntity(**record)
                newr.save()
            elif(act_table == 'link_hierarchies'):
                newr = LinkHierarchy(**record)
                newr.save()
            elif(act_table == 'oc_chronology'):
                newr = Chronology(**record)
                newr.save()
            elif(act_table == 'oc_geodata'):
                newr = Geodata(**record)
                newr.save()
            elif(act_table == 'oc_mediafiles'):
                newr = Mediafile(**record)
                newr.save()
            elif(act_table == 'oc_documents'):
                newr = OCdocument(**record)
                newr.save()
            elif(act_table == 'oc_persons'):
                newr = Person(**record)
                newr.save()
            elif(act_table == 'oc_projects'):
                newr = Project(**record)
                newr.save()
            elif(act_table == 'oc_strings'):
                newr = OCstring(**record)
                newr.save()
            elif(act_table == 'oc_types'):
                newr = OCtype(**record)
                newr.save()
            elif(act_table == 'oc_events'):
                newr = Event(**record)
                newr.save()
            elif(act_table == 'oc_predicates'):
                newr = Predicate(**record)
                newr.save()
            elif(act_table == 'oc_identifiers'):
                newr = StableIdentifer(**record)
                newr.save()
            elif(act_table == 'oc_obsmetadata'):
                newr = ObsMetadata(**record)
                newr.save()

    def process_table(self, act_table, after):
        """
        iterates through a data table to get records after a certain time
        """
        start = 0
        loop_ok = True
        while loop_ok:
            recs = self.get_table_records(act_table, after, start)
            if recs is not False:
                self.store_records(act_table, recs)
                count_recs = len(recs)
                start = start + count_recs
            else:
                loop_ok = False
        return start

    def add_predicates_manifest(self):
        """
        adds predicate items to the manifest
        """
        predicates = Predicate.objects.all()
        for predicate in predicates:
            record = {'uuid': predicate.uuid,
                      'project_uuid': predicate.project_uuid,
                      'source_id': predicate.source_id,
                      'item_type': 'predicates',
                      'repo': '',
                      'class_uri': predicate.archaeoml_type,
                      'label': predicate.label,
                      'des_predicate_uuid': '',
                      'views': 0,
                      'published': predicate.created,
                      'revised': predicate.updated}
            newr = Manifest(**record)
            newr.save()
        return len(predicates)

    def add_octypes_manifest(self):
        """
        adds octype items to the manifest
        """
        octypes = OCtype.objects.all()
        proj_dates = self.get_manifest_project_dates()
        for octype in octypes:
            record = {'uuid': octype.uuid,
                      'project_uuid': octype.project_uuid,
                      'source_id': octype.source_id,
                      'item_type': 'types',
                      'repo': '',
                      'class_uri': '',
                      'label': octype.label,
                      'des_predicate_uuid': '',
                      'views': 0,
                      'published': proj_dates[octype.project_uuid]['earliest'],
                      'revised': octype.updated}
            newr = Manifest(**record)
            newr.save()
        return len(octypes)

    def add_ocprojects_manifest(self):
        """
        adds ocproject items to the manifest
        """
        ocprojects = Project.objects.all()
        proj_dates = self.get_manifest_project_dates()
        for ocproj in ocprojects:
            record = {'uuid': ocproj.uuid,
                      'project_uuid': ocproj.project_uuid,
                      'source_id': ocproj.source_id,
                      'item_type': 'projects',
                      'repo': '',
                      'class_uri': '',
                      'label': ocproj.label,
                      'des_predicate_uuid': '',
                      'views': 0,
                      'published': proj_dates[ocproj.project_uuid]['earliest'],
                      'revised': ocproj.updated}
            newr = Manifest(**record)
            newr.save()
        return len(ocprojects)

    def add_ocpersons_manifest(self):
        """
        adds ocproject items to the manifest
        """
        ocpersons = Person.objects.all()
        proj_dates = self.get_manifest_project_dates()
        for ocper in ocpersons:
            record = {'uuid': ocper.uuid,
                      'project_uuid': ocper.project_uuid,
                      'source_id': ocper.source_id,
                      'item_type': 'persons',
                      'repo': '',
                      'class_uri': '',
                      'label': ocper.combined_name,
                      'des_predicate_uuid': '',
                      'views': 0,
                      'published': proj_dates[ocper.project_uuid]['earliest'],
                      'revised': ocper.updated}
            newr = Manifest(**record)
            newr.save()
        return len(ocpersons)

    def get_manifest_project_dates(self):
        """
        gets initial publication date for items in the manifest
        """
        projs = Manifest.objects.values_list('project_uuid').distinct()
        proj_dates = {}
        from django.utils import timezone
        start_date = timezone.now()
        for proj in projs:
            early_date = Manifest.objects.filter(project_uuid=proj[0],
                                                 published__isnull=False,
                                                 published__lte=start_date).aggregate(earliest=Min('published'),
                                                                                      last=Max('published'))
            proj_dates[proj[0]] = early_date
        return proj_dates

    def update_geo_chrono(self):
        """
        geos = Geospaceold.objects.all()
        for geo in geos:
            record = {'uuid': geo.uuid,
                      'project_uuid': geo.project_uuid,
                      'source_id': 'ArchaeoML doc',
                      'item_type': 'subjects',
                      'feature_id': geo.fid,
                      'meta_type': geo.meta_type,
                      'ftype': geo.ftype,
                      'latitude': geo.latitude,
                      'longitude': geo.longitude,
                      'specificity': geo.specificity,
                      'coordinates': geo.coordinates,
                      'note': geo.note}
            newr = Geospace(**record)
            newr.save()
        geo_count = len(geos)
        geos = []
        geo_count = 0
        chronos = Eventold.objects.all()
        for chrono in chronos:
            record = {'uuid': chrono.uuid,
                      'item_type': chrono.item_type,
                      'project_uuid': chrono.project_uuid,
                      'source_id': chrono.source_id,
                      'event_id': chrono.event_id,
                      'meta_type': chrono.meta_type,
                      'when_type': chrono.when_type,
                      'feature_id': chrono.feature_id,
                      'earliest': chrono.earliest,
                      'start': chrono.start,
                      'stop': chrono.stop,
                      'latest': chrono.latest,
                      'note': chrono.note}
            newr = Event(**record)
            newr.save()
        chrono_count = len(chronos)
        return 'Geospace records: ' + geo_count + ', event records: ' + chrono_count
        """
