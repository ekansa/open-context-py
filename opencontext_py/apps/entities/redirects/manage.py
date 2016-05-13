import json
from unidecode import unidecode
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.apps.entities.redirects.models import RedirectMapping
from opencontext_py.apps.exports.exptables.identifiers import ExpTableIdentifiers


# Methods to manage export table fields
class RedirectURL():

    """ Methods to manage the redirection of URLs

from opencontext_py.apps.entities.redirects.manage import RedirectURL
r_url = RedirectURL()
r_url.note = 'Redirect legacy table identifiers from an earlier version of Open Context'


    """

    def __init__(self):
        self.url = None
        self.redirect = None
        self.http_code = None
        self.permanent = True
        self.note = None

    def get_direct_by_type_id(self, item_type, identifier):
        """ gets a redirect if it exists by item_type and identifier """
        found = False
        url = '/' + item_type + '/' + identifier
        re_maps = RedirectMapping.objects\
                                 .filter(url__contains=url)[:1]
        if len(re_maps) > 0:
            # we found some redirection!
            found = True
            self.url = url
            self.redirect = re_maps[0].redirect
            self.http_code = re_maps[0].http_code
            self.permanent = self.set_http_code_perm(re_maps[0].http_code)
        return found

    def set_redirect_for_type_ids(self, item_type, old_id, new_id):
        """ makes a redirect for an item_type with an old id
            to a new id
        """
        if item_type == 'tables':
            ex_id = ExpTableIdentifiers()
            ex_id.make_all_identifiers(old_id)
            old_id = ex_id.public_table_id
        url = '/' + item_type + '/' + old_id
        re_maps = RedirectMapping.objects\
                                 .filter(url=url)[:1]
        if len(re_maps) == 0:
            # we don't already have this, so make the new redirect
            if item_type == 'tables':
                ex_id = ExpTableIdentifiers()
                ex_id.make_all_identifiers(new_id)
                new_id = ex_id.public_table_id
            redirect = '/' + item_type + '/' + new_id
            rmap = RedirectMapping()
            rmap.url = url
            rmap.redirect = redirect
            rmap.note = self.note
            rmap.save()

    def set_http_code_perm(self, http_code):
        """ set the permanent stats for an HTTP code """
        if http_code == 301:
            permanent = True
        elif http_code == 302:
            permanent = False
        else:
            permanent = True
        return permanent
