import re
from django.conf import settings
from django.db import models
from django.db.models import Q
from opencontext_py.apps.entities.uri.models import URImanagement
from opencontext_py.apps.entities.entity.models import Entity
from opencontext_py.apps.ldata.linkentities.models import LinkEntity
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.ocitems.assertions.models import Assertion
from opencontext_py.apps.ocitems.assertions.containment import Containment
from opencontext_py.apps.ldata.linkannotations.models import LinkAnnotation
from opencontext_py.apps.ocitems.subjects.generation import SubjectGeneration
from opencontext_py.apps.ocitems.subjects.models import Subject
from opencontext_py.apps.ocitems.predicates.models import Predicate
from opencontext_py.apps.ocitems.octypes.models import OCtype
from opencontext_py.apps.ocitems.mediafiles.models import Mediafile
from opencontext_py.apps.ocitems.documents.models import OCdocument
from opencontext_py.apps.ocitems.persons.models import Person
from opencontext_py.apps.edit.dinaa.trinomials.models import Trinomial


"""
from opencontext_py.apps.edit.dinaa.trinomials.manage import TrinomialManage
project_uuid = '7f82f3f3-04d2-47c3-b0a9-21aa28294d25'
tri_m = TrinomialManage()
tri_m.remove_prepended_zeros = True
tri_m.make_trinomial_from_site_labels(project_uuid, '')
"""


# This class is used to manage trinomial identifiers for DINAA.
class TrinomialManage():

    def __init__(self):
        self.remove_prepended_zeros = False
        pass

    def prepend_qualifier_dash(self):
        """ goes through each identifier and prepends a '-' for
           qualifiers
        """
        tris = Trinomial.objects.filter(trinomial__isnull=False)
        for tri in tris:
            tri_parts = self.parse_trinomial(tri.trinomial)
            site_extra = re.sub(r'[0-9]', r'', tri_parts['site'])
            if len(site_extra) > 0:
                # the site part has some extra stuff in it.
                # need to check if it has consistent qualifiers
                i = 0
                ndigit_found = False
                new_site = ''
                p_site = tri_parts['site']
                site_len = len(p_site)
                while i < site_len:
                    if ndigit_found is False:
                        if not p_site[i].isdigit():
                            ndigit_found = True
                            if p_site[i] != '-' and p_site[i] != '/':
                                # prepend a qualifier only if it is not
                                # already present
                                new_site += '-'
                    new_site += p_site[i]
                    i += 1
                if new_site != p_site:
                    print('In ' + tri.trinomial + ' site: ' + p_site + ' now: ' + new_site)
                    tri.trinomial = str(tri_parts['state']) + str(tri_parts['county']) + new_site
                    tri.site = new_site
                    tri.save()

    def parse_trinomial(self, trinomial):
        """ Parses a trinomial into its parts.
            This will need modification + exceptions to handle
            trinomials for other states. See:
            http://en.wikipedia.org/wiki/Smithsonian_trinomial
        """
        non_zero_found = False
        tri_len = len(trinomial)
        act_part = 'state'
        parts = {'state': '',
                 'county': '',
                 'site': ''}
        i = 0
        while i < tri_len:
            act_char = trinomial[i]
            if act_part == 'state':
                if not act_char.isdigit():
                    act_part = 'county'
            if act_part == 'county':
                if act_char.isdigit():
                    act_part = 'site'
            parts[act_part] += act_char
            i += 1
        if self.remove_prepended_zeros:
            int_site = False
            try:
                int_site = int(float(parts['site']))
            except:
                int_site = False
            if int_site is not False:
                parts['site'] = int_site
        return parts

    def fix_missing_county_site(self):
        """ make and save missing trinomial records for Florida """
        missing = Trinomial.objects\
                           .filter(site__isnull=True,
                                   state__isnull=False,
                                   county__isnull=True)
        for mt in missing:
            state = str(int(float(mt.state)))
            county_site_part = mt.trinomial.replace(state, '', 1)
            digit_found = False
            county = ''
            site = ''
            county_site_part_len = len(county_site_part)
            i = 0
            while i < county_site_part_len:
                if digit_found is False \
                   and county_site_part[i].isdigit():
                    digit_found = True
                if digit_found:
                    site += county_site_part[i]
                else:
                    county += county_site_part[i]
                i +=1
            print(mt.trinomial + ' State: ' + state + ' County: ' + county + ' site: ' + site)
            mt.state = state
            mt.county = county
            mt.site = site[:10]
            mt.save()

    def fix_missing_site(self):
        """ make and save missing trinomial records for Florida """
        missing = Trinomial.objects\
                           .filter(site__isnull=True,
                                   state__isnull=False,
                                   county__isnull=False)
        for mt in missing:
            state = str(int(float(mt.state)))
            county = mt.county
            first_part = str(state) + county
            site_part = mt.trinomial.replace(first_part, '')
            non_zero_found = False
            site = ''
            site_part_len = len(site_part)
            i = 0
            while i < site_part_len:
                if non_zero_found is False \
                   and site_part[i] != '0':
                    non_zero_found = True
                if non_zero_found and site_part[i] == '&':
                    site += ','
                elif non_zero_found and site_part[i] != '/':
                    site += site_part[i]
                i +=1
            print(mt.trinomial + ' State: ' + state + ' County: ' + county + ' site: ' + site)
            mt.trinomial = state + county + site
            mt.state = state
            mt.site = site[:6]
            mt.save()

    def fix_long_virginia(self):
        """ make and save missing trinomial records for Florida """
        missing = Trinomial.objects\
                           .filter(label__icontains='-0',
                                   state='44')
        for mt in missing:
            state = str(int(float(mt.state)))
            county = mt.county
            first_part = str(state) + county
            site_part = mt.label.replace(first_part, '')
            non_zero_found = False
            dash_found = False
            site = ''
            site_part_len = len(site_part)
            i = 0
            while i < site_part_len:
                if non_zero_found is False \
                   and site_part[i] != '0':
                    non_zero_found = True
                if non_zero_found and site_part[i] == '-':
                    dash_found = True
                    non_zero_found = False
                    site += '-'
                elif non_zero_found and site_part[i] != '/':
                    site += site_part[i]
                i +=1
            print(mt.label + ' State: ' + state + ' County: ' + county + ' site: ' + site)
            mt.trinomial = state + county + site
            print('Fixed trinomial: ' + mt.trinomial)
            mt.site = site[:10]
            mt.save()

    def make_missing_florida(self):
        """ make and save missing trinomial records for Florida """
        missing = Trinomial.objects\
                           .filter(project_label__icontains='Florida',
                                   trinomial__isnull=True)
        for mt in missing:
            county = re.sub(r'[0-9]', r'', mt.label)
            site_str = re.sub(r'[a-zA-Z]', r'', mt.label)
            site = int(float(site_str))
            mt.trinomial = '8' + county + str(site)
            mt.state = '8'
            mt.county = county
            mt.site = str(site)
            mt.save()
            print('County: ' + county + ' site: ' + str(site))

    def make_missing_scarolina(self):
        """ make and save missing trinomial records for Florida """
        missing = Trinomial.objects\
                           .filter(project_label__icontains='South Carolina',
                                   trinomial__isnull=True)
        for mt in missing:
            if '-' in mt.label:
                labelex = mt.label.split('-')
                label_prefix = labelex[0]
            else:
                label_prefix = mt.label
            county = re.sub(r'[0-9]', r'', label_prefix)
            if county in label_prefix:
                labelex = label_prefix.split(county)
                site_str = labelex[1]
            else:
                site_str = re.sub(r'[a-zA-Z]', r'', label_prefix)
            site = int(float(site_str))
            mt.trinomial = '38' + county + str(site)
            mt.state = '38'
            mt.county = county
            mt.site = str(site)
            mt.save()
            print('County: ' + county + ' site: ' + str(site))

    def fix_indiana_space(self):
        """ make and save missing trinomial records for Florida """
        missing = Trinomial.objects\
                           .filter(project_label__icontains='Indiana',
                                   trinomial__contains=' ')
        for mt in missing:
            first_part = str(mt.state) + mt.county
            site_part = mt.trinomial.replace(first_part, '')
            site_str = re.sub(r'\D', r'', site_part)
            site = int(float(site_str))
            new_trinomial = first_part + str(site)
            suffix = ''
            if ' / ' in mt.trinomial:
                tex = mt.trinomial.split(' / ')
                suffix = tex[1]
            elif 'a and b' in mt.trinomial:
                suffix = 'a,b'
            elif 'east' in mt.trinomial:
                suffix = 'e'
            elif 'west' in mt.trinomial:
                suffix = 'w'
            elif ' ' in mt.trinomial:
                tex = mt.trinomial.split(' ')
                suffix = tex[1]
            new_trinomial += str(suffix)
            print('Old trinimial: ' + mt.trinomial + ' site: ' + str(site) + ' new: ' + new_trinomial)
            mt.trinomial = new_trinomial
            mt.site = str(site) + str(suffix)
            mt.save()

    def make_trinomial_from_site_labels(self,
                                        project_uuid,
                                        state_prefix=''):
        """ makes trinomial identifiers from a site label """
        ent = Entity()
        found = ent.dereference(project_uuid)
        if found:
            proj_label = ent.label
            sites = Manifest.objects\
                            .filter(project_uuid=project_uuid,
                                    class_uri='oc-gen:cat-site')
            for site in sites:
                trinomial = str(state_prefix) + site.label
                if '*' in trinomial:
                    # for North Carolina, only the part before the '*' is a trinomial
                    tr_ex = trinomial.split('*')
                    trinomial = tr_ex[0]
                print('working on (' + site.uuid + '): ' + trinomial)
                parts = self.parse_trinomial(trinomial)
                if 'Tennessee' in proj_label:
                    trinomial = parts['state'] + parts['county'] + str(parts['site'])
                dt = Trinomial()
                dt.uri = URImanagement.make_oc_uri(site.uuid, site.item_type)
                dt.uuid = site.uuid
                dt.label = site.label
                dt.project_label = proj_label
                dt.trinomial = trinomial
                dt.state = parts['state']
                dt.county = parts['county']
                dt.site = parts['site']
                try:
                    dt.save()
                    print('Trinomial: ' + trinomial + ', from: ' + site.label)
                except:
                    print('Trinomial: ' + trinomial + ' not valid as a trinomial')
