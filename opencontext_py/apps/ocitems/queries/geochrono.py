from django.conf import settings
from django.db import connection
from django.db import models
from django.db.models import Q, Max, Min, Count, Avg
from django.core.cache import caches
from opencontext_py.libs.memorycache import MemoryCache
from opencontext_py.libs.isoyears import ISOyears
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.apps.ocitems.queries.security import SecurityForQuery
from opencontext_py.apps.ocitems.assertions.models import Assertion
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.ocitems.events.models import Event
from opencontext_py.apps.ocitems.geospace.models import Geospace
from opencontext_py.apps.ocitems.projects.models import Project
from opencontext_py.apps.ocitems.projects.metadata import ProjectRels, ProjectMeta


class GeoChronoQueries():
    """
    This includes queries that use PostgresSQL functions to improve performance
    It represents a bit of a security risk for SQL injection attacks.
    So these methods should not be used unless a passed UUID parameter
    is already known to be safe through use in Django's normal querying model

from opencontext_py.apps.ocitems.queries.geochrono import GeoChronoQueries
gcq = GeoChronoQueries()
project_uuid = '416A274C-CF88-4471-3E31-93DB825E9E4A'
gcq.get_project_date_range(project_uuid)
geos = gcq.get_project_geo_meta(project_uuid)

    """
    def __init__(self):
        self.seems_safe = False
    
    def get_type_date_range(self, type_uuid, project_uuid):
        """ gets a date range for a uuid of item_type 'types' """
        date_range = None
        # check first if this is a type with an associated
        # time range
        t_events = Event.objects\
                        .filter(uuid=type_uuid,
                                item_type='types')[:1]
        if len(t_events) > 0:
            date_range = {
                'start': float(t_events[0].start),
                'stop': float(t_events[0].stop)
            }
        else:
            # get the project date range
            date_range = self.get_project_date_range(project_uuid)
        return date_range

    def get_project_date_range(self, project_uuid):
        """ gets a project date range """
        mem = MemoryCache()
        key = mem.make_cache_key('proj-chrono', project_uuid)
        date_range = mem.get_cache_object(key)
        if not isinstance(date_range, dict):
            date_range = self.get_project_date_range_db(project_uuid)
            mem.save_cache_object(key, date_range)
        return date_range

    def get_project_date_range_db(self, project_uuid):
        """ gets a list of parent items """
        project_uuids = self.add_child_uuids_of_projects(project_uuid)
        date_range = Event.objects\
                          .filter(project_uuid__in=project_uuids)\
                          .aggregate(Min('start'),
                                     Max('stop'),
                                     Count('hash_id'))
        if date_range['start__min'] is None or date_range['stop__max'] is None:
            date_range = None
        else:
            date_range['start'] = float(date_range['start__min'])
            date_range['stop'] = float(date_range['stop__max'])
        return date_range
    
    def get_project_geo_meta(self, project_uuid):
        """ gets a geo_meta object for a project """
        mem = MemoryCache()
        key = mem.make_cache_key('proj-geo', project_uuid)
        geo_meta = mem.get_cache_object(key)
        if geo_meta is None:
            geo_meta = self.get_project_geo_meta_db(project_uuid)
            mem.save_cache_object(key, geo_meta)
        return geo_meta
            
    def get_project_geo_meta_db(self, project_uuid):
        """ gets a geo_meta object for a project """
        pm = ProjectMeta()
        # pm.print_progress = True
        pm.make_geo_meta(project_uuid)
        if pm.geo_objs is not False:
            geo_meta = pm.geo_objs
        else:
            geo_meta = None
        return geo_meta
    
    def add_child_uuids_of_projects(self, project_uuids):
        """ adds any child uuids of a given project(s)
        """
        if not isinstance(project_uuids, list):
            project_uuids = [project_uuids]
        child_projects = Project.objects\
                                .filter(project_uuid__in=project_uuids)\
                                .exclude(uuid__in=project_uuids)
        for child in child_projects:
            project_uuids.append(child.uuid)
        return project_uuids

    def dictfetchall(self, cursor):
        """ Return all rows from a cursor as a dict """
        columns = [col[0] for col in cursor.description]
        return [
            dict(zip(columns, row))
            for row in cursor.fetchall()
        ]
