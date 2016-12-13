import hashlib
from django.db import models
from django.db.models import Q
from opencontext_py.apps.ldata.linkannotations.models import LinkAnnotation
from opencontext_py.apps.ocitems.assertions.models import Assertion
from opencontext_py.apps.ocitems.projects.models import Project
from opencontext_py.apps.entities.uri.models import URImanagement


class Authorship():
    """
    Looks for dc-terms creator and contributor relations for items,
    checking first for the uuid, then for the project
    """
    URI_DC_CONTRIB = 'http://purl.org/dc/terms/contributor'
    URI_DC_CREATE = 'http://purl.org/dc/terms/creator'
    PRF_DC_CONTRIB = 'dc-terms:contributor'
    PRF_DC_CREATE = 'dc-terms:creator'

    def __init__(self):
        self.creators = []
        self.contributors = []
        self.consolidate_authorship = True

    def get_authors(self, uuid, project_uuid=False):
        """
        Gets author information associated for an item. If project_uuid is
        not false, look for project author information
        """
        output = False
        filter_contribs = 'oc_assertions.predicate_uuid = link_annotations.subject\
                          AND (link_annotations.predicate_uri = \'skos:closeMatch\'\
                          OR link_annotations.predicate_uri = \
                          \'http://www.w3.org/2004/02/skos/core#closeMatch\') \
                          AND (link_annotations.object_uri = \
                               \'' + self.URI_DC_CONTRIB + '\' \
                          OR link_annotations.object_uri = \
                               \'' + self.PRF_DC_CONTRIB + '\')'
        filter_creators = 'oc_assertions.predicate_uuid = link_annotations.subject\
                          AND (link_annotations.predicate_uri = \'skos:closeMatch\'\
                          OR link_annotations.predicate_uri = \
                          \'http://www.w3.org/2004/02/skos/core#closeMatch\') \
                          AND (link_annotations.object_uri = \
                               \'' + self.URI_DC_CREATE + '\' \
                          OR link_annotations.object_uri = \
                               \'' + self.PRF_DC_CREATE + '\' )'
        l_tables = 'link_annotations'
        creator_assertions = Assertion.objects\
                                      .filter(uuid=uuid)\
                                      .extra(tables=[l_tables], where=[filter_creators])\
                                      .order_by('sort')
        for creator in creator_assertions:
            if creator.object_uuid not in self.creators:
                self.creators.append(creator.object_uuid)
        contrib_assertions = Assertion.objects\
                                      .filter(uuid=uuid)\
                                      .extra(tables=[l_tables], where=[filter_contribs])\
                                      .order_by('sort')
        for contrib in contrib_assertions:
            if contrib.object_uuid not in self.contributors:
                if contrib.object_uuid not in self.creators \
                   or self.consolidate_authorship is False:
                    self.contributors.append(contrib.object_uuid)  # add to contrib if not a creator
        if len(self.contributors) > 0 or len(self.creators) > 0:
            output = True
        else:
            if project_uuid is not False:
                output = self.get_project_authors(project_uuid)
        return output

    def get_project_authors(self, project_uuid):
        """ Gets author information for a project """
        output = False
        creator_links = LinkAnnotation.objects\
                                      .filter(Q(subject=project_uuid),
                                              Q(predicate_uri=self.URI_DC_CREATE)
                                              | Q(predicate_uri=self.PRF_DC_CREATE))\
                                      .order_by('sort')
        if len(creator_links) < 1:
            # look for creators from the parent project
            par_proj = Project.objects\
                              .filter(uuid=project_uuid)\
                              .exclude(project_uuid=project_uuid)[:1]
            if len(par_proj) > 0:
                creator_links = LinkAnnotation.objects\
                                              .filter(Q(subject=par_proj[0].project_uuid),
                                                      Q(predicate_uri=self.URI_DC_CREATE)
                                                      | Q(predicate_uri=self.PRF_DC_CREATE))\
                                              .order_by('sort')
        if len(creator_links) > 0:
            for creator in creator_links:
                pid = URImanagement.get_uuid_from_oc_uri(creator.object_uri)
                if pid is False:
                    pid = creator.object_uri
                if pid not in self.creators:
                    self.creators.append(pid)
        contrib_links = LinkAnnotation.objects\
                                      .filter(Q(subject=project_uuid),
                                              Q(predicate_uri=self.URI_DC_CONTRIB)
                                              | Q(predicate_uri=self.PRF_DC_CONTRIB))\
                                      .order_by('sort')
        for contrib in contrib_links:
            pid = URImanagement.get_uuid_from_oc_uri(contrib.object_uri)
            if pid is False:
                pid = contrib.object_uri
            if pid not in self.contributors:
                if pid not in self.creators \
                   or self.consolidate_authorship is False\
                   or contrib.sort > 0:
                    self.contributors.append(pid)  # add to contrib if not a creator    
        if len(self.contributors) > 0 or len(self.creators) > 0:
            output = True
        return output

    def check_authorship_object(self, object_uri):
        """ checks to see if an object_uri is an authorship object """
        auth_objects = [self.URI_DC_CONTRIB,
                        self.URI_DC_CREATE,
                        self.PRF_DC_CONTRIB,
                        self.PRF_DC_CREATE]
        if object_uri in auth_objects:
            output = True
        else:
            output = False
        return output
