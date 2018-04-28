import hashlib
from django.db import models
from django.db.models import Q
from opencontext_py.apps.ldata.linkannotations.models import LinkAnnotation
from opencontext_py.apps.ocitems.assertions.models import Assertion
from opencontext_py.apps.entities.uri.models import URImanagement


class Licensing():
    """
    Looks for dc-terms creator and contributor relations for items,
    checking first for the uuid, then for the project
    """
    URI_LICENSE = 'http://purl.org/dc/terms/license'
    PRF_LICENSE = 'dc-terms:license'
    URI_CC_LICENSE = 'http://creativecommons.org/ns#license'
    PRF_CC_LICENSE = 'cc:license'
    DEFAULT_LICENSE = 'http://creativecommons.org/licenses/by/4.0/'

    def __init__(self):
        self.license = False
        self.proj_default_lic_dict = {}
        self.default_ok = True  # return default license if not specified

    def get_license(self, uuid, project_uuid=False):
        """
        Gets author information associated for an item. If project_uuid is
        not false, look for project author information
        """
        output = False
        output = self.get_license_by_uuid(uuid)
        if output is False and isinstance(project_uuid, str):
            if project_uuid not in self.proj_default_lic_dict:
                # cache this license
                self.proj_default_lic_dict[project_uuid] = self.get_license_by_uuid(project_uuid)
            output = self.proj_default_lic_dict[project_uuid]
        if not isinstance(output, str) and self.default_ok:
            output = self.DEFAULT_LICENSE
        return output

    def get_license_by_uuid(self, uuid):
        """
        Gets licensing information for a uuid
        """
        output = False
        lic = LinkAnnotation.objects\
                            .filter(Q(subject=uuid),
                                    Q(predicate_uri=self.URI_LICENSE)
                                    | Q(predicate_uri=self.PRF_LICENSE))[:1]
        if len(lic) > 0:
            output = lic[0].object_uri
        return output
