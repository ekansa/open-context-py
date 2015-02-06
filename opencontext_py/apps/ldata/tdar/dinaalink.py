from opencontext_py.apps.ldata.tdar.api import tdarAPI
from opencontext_py.apps.edit.dinaa.trinomials.models import Trinomial
from opencontext_py.apps.edit.dinaa.trinomials.manage import TrinomialManage
from opencontext_py.apps.entities.entity.models import Entity
from opencontext_py.apps.ldata.linkentities.models import LinkEntity
from opencontext_py.apps.ldata.linkannotations.models import LinkAnnotation


class dinaaLink():
    """ methods to link Smithsonian Trinomials curated by
        DINAA with keywords in tDAR
    """

    def __init__(self):
        self.request_error = False

    def match_dinaa_ids(self):
        """ get a key word for a site """
        tri_man = TrinomialManage()
        tris = Trinomial.objects.filter(trinomial__isnull=False,
                                        trinomial='44PG462')[:25]
        for tri in tris:
            la_check = LinkAnnotation.objects\
                                     .filter(subject=tri.uuid,
                                             predicate_uri='dc-terms:subject',
                                             object_uri__contains=tdarAPI.BASE_URI)[:1]
            if len(la_check) < 1:
                # we don't already have a tDAR id for this item, continue with matches
                request_keywords = [tri.trinomial]
                tri_parts = tri_man.parse_trinomial(tri.trinomial)
                site = tri_parts['site']
                site_part_len = len(site)
                while len(site) < 4:
                    site = '0' + site
                    new_trinomial = tri_parts['state'] + tri_parts['county'] + site
                    request_keywords.append(new_trinomial)
                for keyword in request_keywords:
                    tdar_api = tdarAPI()
                    result = tdar_api.get_site_keyword(keyword)
                    print(str(result))
