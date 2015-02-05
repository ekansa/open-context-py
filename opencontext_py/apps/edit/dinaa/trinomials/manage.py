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


# This class is used to manage trinomial identifiers for DINAA.
class TrinomialManage():

    def __init__(self):
        pass

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
