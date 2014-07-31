import numpy as np
from numpy import vstack, array
from scipy.cluster.vq import kmeans,vq
from django.db import models
from django.db.models import Avg, Max, Min
from opencontext_py.apps.ocitems.geospace.models import Geospace
from opencontext_py.apps.ocitems.events.models import Event
from opencontext_py.apps.ocitems.projects.models import Project
from opencontext_py.libs.chronotiles import ChronoTile
from opencontext_py.libs.globalmaptiles import GlobalMercator


class ProjectRels():
    """
    Checks on project relationships with subprojects
    """

    def __init__(self):
        self.sub_projects = False

    def get_sub_projects(self, uuid):
        """
        Gets (child) sub-projects from the current project uuid
        """
        sub_projs = Project.objects.filter(project_uuid=uuid).exclude(uuid=uuid)
        if(len(sub_projs) > 0):
            self.sub_projects = sub_projs
        else:
            self.sub_projects = False
        return self.sub_projects


class ProjectMeta():
    """
    Generates geospatial and chronological summaries for project metadata
    """

    MAX_CLUSTERS = 15
    MIN_CLUSTER_SIZE = .05

    def __init__(self):
        self.geo_ents = False
        self.event_ents = False
        self.geo_range = False

    def make_uuids_list(self, uuids):
        """ Makes a list of UUIDS if only passed a string """
        if uuids is not list:
            uuids = [uuids]  # make a list
        return uuids

    def cluster_geo(self, uuids):
        """ Puts geo points into clusters """
        dist_geo = self.get_distinct_geo(uuids)
        lon_lats = []
        for geo in dist_geo:
            # using geojson order of lon / lat
            lon_lat = [geo['longitude'], geo['latitude']]
            # makes it a numpy float
            dpoint = np.fromiter(lon_lat, np.dtype('float'))
            lon_lats.append(dpoint)
        # create a numpy array object from my list of float coordinates
        data = array(lon_lats)
        resonable_clusters = False
        number_clusters = self.MAX_CLUSTERS
        while resonable_clusters is False:
            centroids, _ = kmeans(data, number_clusters)
            idx, _ = vq(data, centroids)
            resonable_clusters = True
        return centroids

    def get_distinct_geo(self, uuids):
        """ Gets distinct geo lat/lons """
        uuids = self.make_uuids_list(uuids)
        dist_geo = Geospace.objects.filter(project_uuid__in=uuids)\
                           .exclude(latitude=0, longitude=0)\
                           .values('latitude', 'longitude')\
                           .distinct()
        return dist_geo

    def get_geo_range(self, uuids):
        """
        Gets summary geospatial information for a string or a list
        of project uuids. Accepts a list to get sub-projects
        """
        uuids = self.make_uuids_list(uuids)
        proj_geo = Geospace.objects.filter(project_uuid__in=uuids)\
                           .exclude(latitude=0, longitude=0)\
                           .aggregate(Max('latitude'),
                                      Max('longitude'),
                                      Min('latitude'),
                                      Min('longitude'))
        if(proj_geo['latitude__max'] is not None):
            """
            self.max_lat = proj_geo['latitude__max']
            self.min_lat = proj_geo['latitude__min']
            self.max_lon = proj_geo['longitude__max']
            self.min_lon = proj_geo['longitude__min']
            """
            self.geo_range = proj_geo

