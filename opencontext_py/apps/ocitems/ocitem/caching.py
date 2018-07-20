import hashlib
from django.conf import settings
from django.db import models
from django.core.cache import caches
from opencontext_py.libs.general import LastUpdatedOrderedDict, DCterms
from opencontext_py.libs.rootpath import RootPath
from opencontext_py.libs.cacheutilities import CacheUtilities
from opencontext_py.libs.memorycache import MemoryCache
from opencontext_py.apps.contexts.projectcontext import ProjectContext
from opencontext_py.apps.entities.entity.models import Entity
from opencontext_py.apps.ocitems.ocitem.itemkeys import ItemKeys
from opencontext_py.apps.ocitems.assertions.models import Assertion
from opencontext_py.apps.ocitems.obsmetadata.models import ObsMetadata
from opencontext_py.apps.ocitems.projects.models import Project
from opencontext_py.apps.ocitems.projects.metadata import ProjectRels
from opencontext_py.apps.ldata.linkannotations.models import LinkAnnotation
from opencontext_py.apps.ldata.linkannotations.equivalence import LinkEquivalence


class ItemGenerationCache():
    """
    methods for using the Reddis cache to
    streamline making item JSON-LD
    """
    
    def __init__(self, cannonical_uris = False):
        self.cannonical_uris = cannonical_uris
        self.cache_use = CacheUtilities()
        dc_terms_obj = DCterms()
        self.dc_metadata_preds = dc_terms_obj.get_dc_terms_list()
        rp = RootPath()
        if self.cannonical_uris:
            self.base_url = rp.cannonical_host
        else:
            self.base_url = rp.get_baseurl()

    def get_project_context(self,
                            project_uuid,
                            assertion_hashes=False):
        """ gets a project context, which lists all predicates
            and has a graph of linked data annotations to
            predicates and types
            if assertion_hashes is true, then get
            the project context with the hash identifiers
            for the specific linked data assertions. This makes
            it easier to reference specific assertions for edits.
        """
        cache_id = self.cache_use.make_cache_key('proj-context-' + str(assertion_hashes),
                                                 project_uuid)
        item = self.cache_use.get_cache_object(cache_id,
                                               True)
        if item is not None:
            output = item
        else:
            pc = ProjectContext(project_uuid)
            if self.cannonical_uris:
                pc.id_href = False  # use the cannonical href as the Context's ID
            else:
                pc.id_href = True  # use the local href as the Context's ID
            pc.base_url = self.base_url
            pc.assertion_hashes = assertion_hashes
            context_json_ld = pc.make_context_and_vocab_json_ld()
            if isinstance(context_json_ld, dict):
                output = context_json_ld
                self.cache_use.save_cache_object(cache_id,
                                                 context_json_ld,
                                                 True)
        return output

    def get_entity(self, identifier):
        """ gets an entity either from the cache or from
            database lookups.
        """
        m_cache = MemoryCache()
        return m_cache.get_entity(identifier)
    
    def get_observation_metadata(self, source_id, obs_num):
        """ gets a metadata object for an observation node, that
            provides some context on assertions made in an observation
        """
        cache_id = self.cache_use.make_cache_key('obs-meta',
                                                 (source_id + '-' + str(obs_num)))
        obs_meta = self.cache_use.get_cache_object(cache_id)
        if obs_meta is None:
            obs_meta = False
            obs_metas = ObsMetadata.objects.filter(source_id=source_id,
                                                   obs_num=obs_num)[:1]
            if len(obs_metas) > 0:
                obs_meta = obs_metas[0]
            else:
                obs_meta = False
            # cache the result, even if is False ad there is no metadata
            self.cache_use.save_cache_object(cache_id, obs_meta)
        return obs_meta
    
    def get_all_project_metadata(self, project_uuid):
        """ gets dc-metadata information for a project,
            and its parent project (if applicable) from the cache.
            If not cached, it queries the database.
            These metadata are inherited by all items in the project
            (author, and temporal)
        """
        cache_id = self.cache_use.make_cache_key('proj-metadata',
                                                 project_uuid)
        all_proj_metadata = self.cache_use.get_cache_object(cache_id)
        if all_proj_metadata is None:
            all_proj_metadata = self.get_db_all_project_metadata(project_uuid)
            if all_proj_metadata is not False:
                self.cache_use.save_cache_object(cache_id,
                                                 all_proj_metadata)
        return all_proj_metadata
    
    def get_project_model_object(self, project_uuid):
        """ gets a project model object from the cache, or database if needed """
        project = None
        all_proj_metadata = self.get_all_project_metadata(project_uuid)
        if isinstance(all_proj_metadata, dict):
            if 'project' in all_proj_metadata:
                if 'project_obj' in all_proj_metadata['project']:
                    if isinstance(all_proj_metadata['project']['project_obj'], Project):
                        project = all_proj_metadata['project']['project_obj']
        return project
    
    def get_project_subprojects(self, project_uuid):
        """ gets a project model object from the cache, or database if needed """
        sub_projects = False
        all_proj_metadata = self.get_all_project_metadata(project_uuid)
        if isinstance(all_proj_metadata, dict):
            if 'project' in all_proj_metadata:
                if 'sub_projects' in all_proj_metadata['project']:
                    if all_proj_metadata['project']['sub_projects'] is not False:
                        sub_projects = all_proj_metadata['project']['sub_projects'] 
        return sub_projects
    
    def get_db_all_project_metadata(self, project_uuid):
        """ Gets author information for a project
            AND its parent project, if it exists     
            from the database
        """
        all_proj_meta = False
        project_entity = self.get_entity(project_uuid)
        if project_entity is not False:
            all_proj_meta = {}
            all_proj_meta['project'] = self.get_db_project_dc_metadata(project_uuid)
            # get the parent project (if it exists author annotations)
            par_proj = Project.objects\
                              .filter(uuid=project_uuid)\
                              .exclude(project_uuid=project_uuid)\
                              .exclude(project_uuid='0')[:1]
            if len(par_proj) > 0:
                # the current project is part of a parent project
                parent_uuid = par_proj[0].project_uuid
                all_proj_meta['parent-project'] = self.get_db_project_dc_metadata(parent_uuid)
            else:
                all_proj_meta['parent-project'] = False
        return all_proj_meta

    def get_db_project_dc_metadata(self, project_uuid):
        """ Gets dc-metadata information for a project from the database
            these metadata are inherited by all items in the project (author, and temporal)
        """
        pr = ProjectRels()
        le = LinkEquivalence()
        dc_contrib_uris = le.get_identifier_list_variants(ItemKeys.PREDICATES_DCTERMS_CONTRIBUTOR)
        dc_creator_uris = le.get_identifier_list_variants(ItemKeys.PREDICATES_DCTERMS_CREATOR)
        dc_temporal_uris = le.get_identifier_list_variants(ItemKeys.PREDICATES_DCTERMS_TEMPORAL)
        dc_license_uris = le.get_identifier_list_variants(ItemKeys.PREDICATES_DCTERMS_LICENSE)
        dc_meta_uris = dc_contrib_uris + dc_creator_uris + dc_temporal_uris + dc_license_uris
        proj_dc_meta = False
        project_entity = self.get_entity(project_uuid)
        try:
            project = Project.objects.get(uuid=project_uuid)
        except Project.DoesNotExist:
            project = None
        if project_entity is not False:
            proj_dc_meta = {
                'entity': project_entity,
                'project_obj': project,
                'sub_projects': pr.get_sub_projects(project_uuid),
                ItemKeys.PREDICATES_DCTERMS_CONTRIBUTOR: [],
                ItemKeys.PREDICATES_DCTERMS_CREATOR: [],
                ItemKeys.PREDICATES_DCTERMS_TEMPORAL: [],
                ItemKeys.PREDICATES_DCTERMS_LICENSE: []
            }
            # get the project dc-metadata annotations (interitable only)
            proj_meta_annos = LinkAnnotation.objects\
                                            .filter(subject=project_uuid,
                                                    predicate_uri__in=dc_meta_uris)\
                                            .order_by('predicate_uri', 'sort')
            for anno in proj_meta_annos:
                if anno.predicate_uri in dc_contrib_uris:
                    # we've got a contributor annotation
                    if anno.object_uri not in proj_dc_meta[ItemKeys.PREDICATES_DCTERMS_CONTRIBUTOR]:
                        proj_dc_meta[ItemKeys.PREDICATES_DCTERMS_CONTRIBUTOR]\
                           .append(anno)
                elif anno.predicate_uri in dc_creator_uris:
                    # we've got creator annotation
                    if anno.object_uri not in proj_dc_meta[ItemKeys.PREDICATES_DCTERMS_CREATOR]:
                        proj_dc_meta[ItemKeys.PREDICATES_DCTERMS_CREATOR]\
                           .append(anno)
                elif anno.predicate_uri in dc_temporal_uris:
                    # we've got temporal annotation
                    if anno.object_uri not in proj_dc_meta[ItemKeys.PREDICATES_DCTERMS_TEMPORAL]:
                        proj_dc_meta[ItemKeys.PREDICATES_DCTERMS_TEMPORAL]\
                           .append(anno)
                elif anno.predicate_uri in dc_license_uris:
                    # we've got a license annotation
                    if anno.object_uri not in proj_dc_meta[ItemKeys.PREDICATES_DCTERMS_LICENSE]:
                        proj_dc_meta[ItemKeys.PREDICATES_DCTERMS_LICENSE]\
                           .append(anno)
        else:
            # there's no project entity
            proj_dc_meta = False
        return proj_dc_meta