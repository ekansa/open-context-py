from django.conf import settings
from django.core.cache import caches
from opencontext_py.libs.rootpath import RootPath
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.apps.entities.entity.models import Entity
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.ocitems.projects.permissions import ProjectPermissions
from opencontext_py.apps.ocitems.projects.models import Project
from opencontext_py.apps.ocitems.persons.models import Person
from opencontext_py.apps.ocitems.assertions.models import Assertion
from opencontext_py.apps.ocitems.predicates.models import Predicate
from opencontext_py.apps.ocitems.strings.models import OCstring

class ProjectContext():
    """
    Contexts documenting the predicates, types, and their
    annotations used in a project
    """
    DOI = 'http://dx.doi.org/10.6078/M7P848VC'  # DOI for this

    def __init__(self, uuid=None, request=None):
        self.id_href = True # use the local href as the Context's ID
        self.uuid = uuid
        rp = RootPath()
        self.base_url = rp.get_baseurl()
        self.manifest = False
        self.project_obj = False
        self.edit_status = 0
        self.edit_permitted = False
        self.view_permitted = True
        self.assertion_hashes = False
        self.id = False
        self.href = False
        self.cannonical_href = False
        self.context = False
        self.errors = []
        if uuid is not None:
            self.dereference_uuid(uuid)
            self.set_uri_urls(uuid)
            if request is not None:
                self.check_permissions(request)
    
    def make_context_json_ld(self):
        """ makes the context JSON-LD """
        context = LastUpdatedOrderedDict()
        context['id'] = self.id
        self.context = context
        return self.context
    
    def dereference_uuid(self, uuid):
        """ dereferences the uuid to make sure it is a project """
        man_list = Manifest.objects\
                           .filter(uuid=uuid,
                                   item_type='projects')[:1]
        if len(man_list) > 0:
            self.manifest = man_list[0]
        else:
            self.manifest = False
            self.errors.append('Item ' + uuid + ' not in manifest')
        if self.manifest is not False:
            try:
                self.project_obj = Project.objects.get(uuid=self.manifest.project_uuid)
                self.edit_status = self.project_obj.edit_status
            except Project.DoesNotExist:
                self.project_obj = False
                self.edit_status = 0 
              
    def check_permissions(self, request):
        """ checks permissions """
        if request is not None and self.manifest is not False:
            # check to make sure edit permissions OK
            pp = ProjectPermissions(self.manifest.project_uuid)
            self.edit_permitted = pp.edit_allowed(request)
            self.view_permitted = pp.view_allowed(request)
    
    def set_uri_urls(self, uuid):
        """ sets the uris and urls for this context resource """
        if self.uuid is None:
            self.uuid = uuid
        self.href = self.base_url + '/contexts/projects/' \
                    + str(self.uuid) + '.json'  # URL for this
        self.cannonical_href = settings.CANONICAL_HOST +  '/contexts/projects/' \
                               + str(self.uuid) + '.json'  # URI for main host
        if self.id_href:
            self.id = self.href
        else:
            self.id = self.cannonical_href

