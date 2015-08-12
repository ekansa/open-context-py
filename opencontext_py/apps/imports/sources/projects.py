import time
import uuid as GenUUID
from dateutil.parser import parse
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.apps.imports.sources.models import ImportSource
from opencontext_py.apps.imports.sources.unimport import UnImport
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.ocitems.projects.models import Project
from opencontext_py.apps.entities.entity.models import Entity
from opencontext_py.apps.imports.refine.api import RefineAPI


# Methods for checking on the Edit and Import status of projects
class ImportProjects():

    def __init__(self):
        self.refine_ok = False  # is Refine up and running?
        self.refine_reloadable = {}

    def get_project(self, project_uuid):
        """ Processes the current batch, determined by the row number
            by running the individual import processes in the proper order
        """
        act_item = LastUpdatedOrderedDict()
        try:
            man_proj = Manifest.objects.get(uuid=project_uuid)
        except Manifest.DoesNotExist:
            act_item = False
        if act_item is not False:
            act_item['uuid'] = man_proj.uuid
            act_item['label'] = man_proj.label
            act_item['published'] = man_proj.published
            act_item['revised'] = man_proj.revised
            try:
                pobj = Project.objects.get(uuid=man_proj.uuid)
                act_item['edit_status'] = pobj.edit_status
                act_item['short_des'] = pobj.short_des
            except Project.DoesNotExist:
                act_item['edit_status'] = False
                act_item['short_des'] = ''
            # get sources from refine first, since it lets us know if updated
            refine_sources = self.relate_refine_local_sources()
            raw_p_sources = ImportSource.objects\
                                        .filter(project_uuid=project_uuid)\
                                        .order_by('-updated')
            raw_p_sources = self.note_unimport_ok(raw_p_sources)
            p_sources = self.note_reloadable_sources(raw_p_sources)
            act_item['sources'] = p_sources
            act_item['refines'] = refine_sources
            act_item['ref_baseurl'] = RefineAPI().get_project_base_url()
            act_item['refine_ok'] = self.refine_ok
        return act_item

    def note_reloadable_sources(self, raw_p_sources):
        """ Notes if items in a list of sources
            can be reloaded now from Refine
        """
        p_sources = []
        for p_source in raw_p_sources:
            # checks to see if the source can be reloaded from Refine
            if p_source.source_id in self.refine_reloadable:
                p_source.refine_id = self.refine_reloadable[p_source.source_id]
            else:
                p_source.refine_id = False
            p_sources.append(p_source)
        return p_sources

    def note_unimport_ok(self, raw_p_sources):
        """ Checks to see if it's OK to unimport a given source """
        p_sources = []
        for p_source in raw_p_sources:
            # checks to see if the source can be reloaded from Refine
            unimp = UnImport(p_source.source_id,
                             p_source.project_uuid)
            p_source.undo_ok = unimp.delete_ok
            p_sources.append(p_source)
        return p_sources

    def relate_refine_local_sources(self):
        """ Relates Refine sources with Sources already loaded from Refine """
        unused_refine_sources = []
        r_sources = self.get_refine_sources()
        if r_sources is not False:
            # now sort these in reverse order of last updated
            date_proj_keyed = {}
            date_proj_keys = []
            for refine_project, ref_meta in r_sources.items():
                modified = ref_meta['modified']
                ref_mod_date = parse(ref_meta['modified'])
                unix_mod = time.mktime(ref_mod_date.timetuple())
                # keep the project_id in to insure unique keys
                date_proj = str(unix_mod) + '00' + str(refine_project)
                date_proj = float(date_proj)
                ref_meta['id'] = refine_project
                date_proj_keyed[date_proj] = ref_meta
                date_proj_keys.append(date_proj)
            date_proj_keys.sort(reverse=True)
            print(str(date_proj_keys))
            r_api = RefineAPI()
            for date_proj in date_proj_keys:
                ref_meta = date_proj_keyed[date_proj]
                refine_project = ref_meta['id']
                source_id = r_api.convert_refine_to_source_id(refine_project)
                ref_created = parse(ref_meta['created'])
                ref_mod_date = parse(ref_meta['modified'])
                try:
                    p_source = ImportSource.objects.get(source_id=source_id)
                except ImportSource.DoesNotExist:
                    p_source = False
                if p_source is not False:
                    self.refine_reloadable[source_id] = refine_project
                    if ref_mod_date > p_source.updated:
                        # Refine data updated since the last time the source was updated
                        p_source.is_current = False
                        p_source.save()
                    if p_source.label != ref_meta['name']:
                        # different name, change in our instance
                        p_source.label = ref_meta['name']
                        p_source.save()
                else:
                    # the source_id is not improted yet, so it's still usable
                    # as a new import
                    ref_meta['created'] = ref_created
                    ref_meta['modified'] = ref_mod_date
                    unused_refine_sources.append(ref_meta)
        return unused_refine_sources

    def get_refine_sources(self):
        """Get's data from refine"""
        r_api = RefineAPI()
        r_sources = r_api.get_projects()
        if isinstance(r_sources, dict):
            self.refine_ok = True
            output = r_sources['projects']
        else:
            output = False
        return output

    def get_all_projects(self):
        """ Processes the current batch, determined by the row number
            by running the individual import processes in the proper order
        """
        output = []
        man_projs = Manifest.objects\
                            .filter(item_type='projects')\
                            .order_by('-revised',
                                      '-published',
                                      '-record_updated')
        for man_proj in man_projs:
            act_item = LastUpdatedOrderedDict()
            act_item['uuid'] = man_proj.uuid
            act_item['label'] = man_proj.label
            act_item['published'] = man_proj.published
            act_item['revised'] = man_proj.revised
            try:
                pobj = Project.objects.get(uuid=man_proj.uuid)
                act_item['edit_status'] = pobj.edit_status
                act_item['short_des'] = pobj.short_des
            except Project.DoesNotExist:
                act_item['edit_status'] = False
                act_item['short_des'] = ''
            p_sources = ImportSource.objects\
                                    .filter(project_uuid=man_proj.uuid)
            act_item['count_imp'] = len(p_sources)
            output.append(act_item)
        return output

    def create_project(self, label, short_des):
        """ Creates a new project in the Manifest
            and projects tables
        """
        uuid = GenUUID.uuid4()
        man_proj = Manifest()
        man_proj.uuid = uuid
        man_proj.label = label
        man_proj.source_id = 'manual'
        man_proj.item_type = 'projects'
        man_proj.project_uuid = uuid
        man_proj.des_predicate_uuid = ''
        man_proj.class_uri = ''
        man_proj.views = 0
        man_proj.save()
        pobj = Project()
        pobj.uuid = uuid
        pobj.source_id = 'manual'
        pobj.project_uuid = uuid
        pobj.label = label
        pobj.edit_status = 0
        pobj.short_des = short_des
        pobj.content = ''
        pobj.save()
        return uuid

    def edit_project(self, project_uuid, label, short_des):
        """ Edits basic project metadata,
            name and short description
        """
        ok = True
        try:
            man_proj = Manifest.objects.get(uuid=project_uuid)
            man_proj.label = label
            man_proj.save()
        except Manifest.DoesNotExist:
            ok = False
        if ok:
            try:
                pobj = Project.objects.get(uuid=project_uuid)
                pobj.short_des = short_des
                pobj.save()
            except Project.DoesNotExist:
                ok = False
        return ok
    
    def edit_project_content(self, project_uuid, content):
        """ Edits a project's content
        """
        ok = True
        try:
            man_proj = Manifest.objects.get(uuid=project_uuid)
        except Manifest.DoesNotExist:
            ok = False
        if ok:
            try:
                pobj = Project.objects.get(uuid=project_uuid)
                pobj.content = content
                pobj.save()
            except Project.DoesNotExist:
                ok = False
        return ok
