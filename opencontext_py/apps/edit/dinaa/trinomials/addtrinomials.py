from opencontext_py.apps.entities.entity.models import Entity
from opencontext_py.apps.edit.dinaa.trinomials.models import Trinomial
from opencontext_py.apps.edit.dinaa.trinomials.manage import TrinomialManage
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.ocitems.projects.models import Project
from opencontext_py.apps.ocitems.obsmetadata.models import ObsMetadata
from opencontext_py.apps.ocitems.predicates.manage import PredicateManagement
from opencontext_py.apps.ocitems.strings.manage import StringManagement
from opencontext_py.apps.ocitems.assertions.models import Assertion


class AddTrinomials():
    """ methods to add trinomials,
        in different varients
        to DINAA site records

from opencontext_py.apps.edit.dinaa.trinomials.addtrinomials import AddTrinomials
add_tris = AddTrinomials()
add_tris.dinaa_projs = ['7f82f3f3-04d2-47c3-b0a9-21aa28294d25']
add_tris.add_trinomials_to_items()
    """

    DINAA_PROJ_UUID = '416A274C-CF88-4471-3E31-93DB825E9E4A'

    def __init__(self):
        self.dinaa_proj_uuid = self.DINAA_PROJ_UUID
        self.dinaa_projs = self.get_dinaa_projects()
        self.obs_meta_label = 'Trinomial ID'
        self.source_id = 'trinomials'
        self.source_ids = {}
        self.obs_num = 2
        self.initial_sort = 201
        self.primary_label = 'Smithsonian Trinomial Identifier'
        self.sort_label = 'Sortable Trinomial'
        self.aux_label = 'Variant Trinomial Expression(s)'

    def add_trinomials_to_items(self):
        """ adds trinomial identifiers to every item
            with a trinomial added in the temporary
            trinomial table
        """
        proj_labels = {}
        proj_uuids = self.dinaa_projs
        projects = Project.objects.filter(uuid__in=proj_uuids)
        source_index = 0
        for project in projects:
            project_uuid = project.uuid
            proj_labels[project_uuid] = project.label
            source_index = project.short_id
            # check to see if the project already has a source_id for
            # trinomial observation assertions
            proj_source_id = self.check_project_source_id(project_uuid)
            if proj_source_id is False:
                # make a new source_id for this project
                proj_source_id = self.source_id + '-' + str(source_index)
                self.source_ids[project_uuid] = proj_source_id
                self.create_obsmetadata(project_uuid)
            else:
                # use the existing source_id for this project
                self.source_ids[project_uuid] = proj_source_id
            print('Project uuid: ' + project_uuid + ' source: ' + proj_source_id)
        pm = PredicateManagement()
        pm.project_uuid = self.dinaa_proj_uuid
        pm.source_id = self.source_id
        main_pred = pm.get_make_predicate(self.primary_label,
                                          'variable')
        pm = PredicateManagement()
        pm.project_uuid = self.dinaa_proj_uuid
        pm.source_id = self.source_id
        sort_pred = pm.get_make_predicate(self.sort_label,
                                          'variable')
        pm = PredicateManagement()
        pm.project_uuid = self.dinaa_proj_uuid
        pm.source_id = self.source_id
        aux_pred = pm.get_make_predicate(self.aux_label,
                                         'variable')
        for project_uuid, proj_label in proj_labels.items():
            print('Adding trinomials for: ' + proj_label)
            tris = Trinomial.objects.filter(trinomial__isnull=False,
                                            project_label=proj_label)
            for tri in tris:
                # first check a manifest item exists for this item
                manifest = False
                try:
                    manifest = Manifest.objects.get(uuid=tri.uuid)
                except Manifest.DoesNotExist:
                    manifest = False
                if manifest is not False:
                    # OK we know this exists, so now make the assertion
                    # to add a trinomial
                    sorting = self.initial_sort
                    # add the cannonical trinomial first
                    ok = self.add_trinomial_to_item(main_pred,
                                                    sorting,
                                                    manifest,
                                                    tri.trinomial,
                                                    False)
                    if ok:
                        print('Added: ' + tri.trinomial + ' to: ' + tri.uri)
                        sorting += 1
                        # add the sorting trinomial
                        sort_trinomial = self.make_sort_trinomial(tri.trinomial)
                        ok = self.add_trinomial_to_item(sort_pred,
                                                        sorting,
                                                        manifest,
                                                        sort_trinomial,
                                                        False)
                        # add a list of alternate versions
                        aux_list = self.make_aux_trinomial_list(tri.trinomial)
                        allow_multiple = False
                        for aux_trinomial in aux_list:
                            sorting += 1
                            # if successful in creation, then allow_multiple is true
                            allow_multiple = self.add_trinomial_to_item(aux_pred,
                                                                        sorting,
                                                                        manifest,
                                                                        aux_trinomial,
                                                                        allow_multiple)
                else:
                    print('Bad news! Missing Manifest obj for: ' + str(tri))

    def add_trinomial_to_item(self,
                              predicate,
                              sort,
                              manifest,
                              trinomial,
                              allow_multiple=False):
        """ Adds trinomials to an item """
        output = False
        ok_to_create = False
        if allow_multiple is False:
            # first check to make sure the item doesn't have
            # a predicate for a trinomial, if multiple are not allowed
            t_ass = Assertion.objects\
                             .filter(uuid=manifest.uuid,
                                     predicate_uuid=predicate.uuid)[:1]
            if len(t_ass) < 1:
                ok_to_create = True
        else:
            ok_to_create = True
        if manifest.project_uuid in self.source_ids:
            source_id = self.source_ids[manifest.project_uuid]
        if ok_to_create:
            # first make a string object
            sm = StringManagement()
            sm.project_uuid = self.dinaa_proj_uuid
            sm.source_id = self.source_id
            oc_string = sm.get_make_string(trinomial)
            # now make the assertion for the trinomial
            ass = Assertion()
            ass.uuid = manifest.uuid
            ass.subject_type = manifest.item_type
            ass.project_uuid = manifest.project_uuid
            ass.source_id = source_id
            ass.obs_node = '#obs-' + str(self.obs_num)
            ass.obs_num = self.obs_num
            ass.sort = sort
            ass.visibility = 1
            ass.predicate_uuid = predicate.uuid
            ass.object_uuid = oc_string.uuid
            ass.object_type = 'xsd:string'
            ass.save()
            output = True
        return output

    def check_project_source_id(self, project_uuid):
        """ Checks for the project's source_id for trinomial observtions """
        source_id = False
        obsmeta = ObsMetadata.objects\
                             .filter(project_uuid=project_uuid,
                                     source_id__contains='trinomial',
                                     obs_num=self.obs_num)[:1]
        if len(obsmeta) > 0:
            source_id = obsmeta[0].source_id
        return source_id

    def create_obsmetadata(self, project_uuid):
        """ create metadata for trinomial observations """
        if project_uuid in self.source_ids:
            source_id = self.source_ids[project_uuid]
            obsmeta = ObsMetadata.objects\
                                 .filter(source_id=source_id,
                                         project_uuid=project_uuid,
                                         obs_num=self.obs_num)[:1]
            if len(obsmeta) < 1:
                obsmeta = ObsMetadata()
                obsmeta.source_id = source_id
                obsmeta.project_uuid = project_uuid
                obsmeta.obs_num = self.obs_num
                obsmeta.label = self.obs_meta_label
                obsmeta.obs_type = 'oc-gen:primary'
                obsmeta.note = 'Smithsonian Trinomial Identifier'
                obsmeta.save()

    def get_dinaa_projects(self):
        """gets a list of projects that are part of DINAA """
        uuids = []
        projs = Project.objects\
                       .filter(project_uuid=self.dinaa_proj_uuid)\
                       .exclude(uuid=self.dinaa_proj_uuid)
        for proj in projs:
            uuids.append(proj.uuid)
        return uuids

    def make_sort_trinomial(self, trinomial):
        """ make a sortable trinomial """
        tri_man = TrinomialManage()
        tri_parts = tri_man.parse_trinomial(trinomial)
        prepended_site = self.prepend_site_zeros(tri_parts['site'], 5)
        return str(tri_parts['state']) + str(tri_parts['county']) + prepended_site

    def make_aux_trinomial_list(self, trinomial):
        """ makes a list of auxiliary, non standard
            trinomials
        """
        aux_tris = []
        # get a dictionary for the different parts of the trinomial
        tri_man = TrinomialManage()
        tri_parts = tri_man.parse_trinomial(trinomial)
        #add a - seperator between parts
        aux_tris.append(self.join_parts('-', tri_parts))
        p_tri_parts = tri_parts
        p_tri_parts['site'] = self.prepend_site_zeros(p_tri_parts['site'], 5)
        aux_tris.append(self.join_parts('-', p_tri_parts))
        return aux_tris

    def prepend_site_zeros(self, site, total_len):
        """ prepends zeros for a site
            with a total digit length
        """
        while(self.get_site_id_len(site) < total_len):
            site = '0' + site
        return site

    def get_site_id_len(self, site):
        """ gets the length of a site id
            before any non-numeric stuff
            that may be appended at the end
        """
        numeric_len = 0
        non_digit_found = False
        i = 0
        while i < len(site):
            if non_digit_found is False:
                if site[i].isdigit():
                    numeric_len += 1
                else:
                    non_digit_found = True
                    break
            i += 1
        return numeric_len

    def join_parts(self, delim, tri_parts):
        """ makes a string with a deliminator
            of the various parts
        """
        output = str(tri_parts['state']) + delim
        output += str(tri_parts['county']) + delim
        output += str(tri_parts['site'])
        return output
