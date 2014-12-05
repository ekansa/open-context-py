import uuid as GenUUID
from dateutil.parser import parse
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.apps.imports.sources.models import ImportSource
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.ocitems.projects.models import Project
from opencontext_py.apps.entities.entity.models import Entity
from opencontext_py.apps.imports.refine.api import RefineAPI


# Finalizes an import by processing data
class ImportProjects():

    def __init__(self):
        pass

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
            p_sources = ImportSource.objects\
                                    .filter(project_uuid=project_uuid)
            act_item['sources'] = p_sources
            act_item['refines'] = refine_sources
        return act_item

    def relate_refine_local_sources(self):
        """ Relates Refine sources with Sources already loaded from Refine """
        unused_refine_sources = []
        r_sources = self.get_refine_sources()
        if r_sources is not False:
            unused_refine_sources = []
            r_api = RefineAPI()
            for refine_project, ref_meta in r_sources.items():
                source_id = r_api.convert_refine_to_source_id(refine_project)
                ref_created = parse(ref_meta['created'])
                ref_mod_date = parse(ref_meta['modified'])
                try:
                    p_source = ImportSource.objects.get(source_id=source_id)
                except ImportSource.DoesNotExist:
                    p_source = False
                if p_source is not False:
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
                    ref_meta['id'] = refine_project
                    ref_meta['created'] = ref_created
                    ref_meta['modified'] = ref_mod_date
                    unused_refine_sources.append(ref_meta)
        return unused_refine_sources

    def get_refine_sources(self):
        """Get's data from refine"""
        r_api = RefineAPI()
        r_sources = r_api.get_projects()
        if isinstance(r_sources, dict):
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
