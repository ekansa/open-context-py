import json

from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.libs.memorycache import MemoryCache
from opencontext_py.apps.ocitems.geospace.models import Geospace
from opencontext_py.apps.ocitems.events.models import Event
from opencontext_py.apps.ocitems.projects.models import Project
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.ocitems.assertions.models import Assertion
from opencontext_py.apps.ocitems.mediafiles.models import Mediafile

class ProjectLayers():
    """
    Assemble Geospatial data to augement a view of a project.
    """
    def __init__(self, uuid):
        self.uuid = uuid
        self.all_proj_uuids = []
        self.geo_overlays = []
        self.features = []
    
    def get_geo_overlays(self):
        """Gets geo overlays for an item identified by uuid."""
        m_cache = MemoryCache()
        cache_key = m_cache.make_cache_key('geo-layers',
                                           self.uuid)
        geo_overlays = m_cache.get_cache_object(cache_key)
        if geo_overlays is not None:
            self.geo_overlays = geo_overlays
            return self.geo_overlays
        else:
            geo_overlays = self.get_geo_overlays_db()
            m_cache.save_cache_object(cache_key, geo_overlays)
        return self.geo_overlays
    
    def get_geo_overlays_db(self):
        """Uses the database to get geo overlays for an item identified by uuid."""
        uuids = self._get_make_all_project_list(self.uuid)
        geo_asserts = Assertion.objects.filter(uuid__in=uuids,
                                               predicate_uuid=Assertion.PREDICATES_GEO_OVERLAY)
        for geo_assert in geo_asserts:
            man_objs = Manifest.objects.filter(uuid=geo_assert.object_uuid)[:1]
            if man_objs:
                geo_media = GeoMedia(man_objs[0])
                if geo_media.full_file_obj and geo_media.metadata:
                    self.geo_overlays.append(geo_media)
        return self.geo_overlays
        
    def _get_make_all_project_list(self, uuid):
        """Makes a list of this uuid and parent projects if they exist."""
        if uuid not in self.all_proj_uuids:
            self.all_proj_uuids.append(uuid)
            par_projs = Project.objects.filter(uuid=uuid).exclude(project_uuid=uuid)[:1]
            if par_projs:
                self.all_proj_uuids.append(par_projs[0].project_uuid)
        return self.all_proj_uuids
    
    def json_geo_overlay(self):
        """Output a json string for the geo_overlays."""
        output = LastUpdatedOrderedDict()
        output['overlays'] = []
        for geo_media in self.geo_overlays:
            geo = LastUpdatedOrderedDict()
            geo['url'] = geo_media.full_file_obj.file_uri
            geo['metadata'] = geo_media.metadata
            output['overlays'].append(geo)
        return json.dumps(output,
                          indent=4,
                          ensure_ascii=False)
            

class GeoMedia():
    
    def __init__(self, manifest_obj):
        self.uuid = manifest_obj.uuid
        self.label = manifest_obj.label
        self.metadata = manifest_obj.sup_json
        self.full_file_obj = self.get_full_file(manifest_obj.uuid)
    
    def get_full_file(self, uuid):
        """Gets the full (main) file associated with a media object. """
        medias = Mediafile.objects.filter(uuid=uuid,
                                          file_type='oc-gen:fullfile')[:1]
        if medias:
            return medias[0]
        else:
            return None