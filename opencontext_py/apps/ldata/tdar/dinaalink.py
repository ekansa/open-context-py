import sys
from time import sleep
from opencontext_py.apps.ldata.tdar.api import tdarAPI
from opencontext_py.apps.edit.dinaa.trinomials.models import Trinomial
from opencontext_py.apps.edit.dinaa.trinomials.manage import TrinomialManage
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.ldata.linkentities.models import LinkEntity
from opencontext_py.apps.ldata.linkannotations.models import LinkAnnotation
from opencontext_py.apps.ocitems.subjects.models import Subject
from opencontext_py.apps.ocitems.ocitem.generation import OCitem


class dinaaLink():
    """ methods to link Smithsonian Trinomials curated by
        DINAA with keywords in tDAR
        
from opencontext_py.apps.ldata.tdar.dinaalink import dinaaLink
dl = dinaaLink()
dl.match_dinaa_ids('Tennessee')


    """
    DC_TERMS_SUBJECT = 'dc-terms:subject'
    TDAR_VOCAB = 'http://core.tdar.org/browse/site-name/'

    def __init__(self):
        self.request_error = False
        self.lead_zero_check = True
        self.max_results = 3
        self.error_wait = 0  # wait if problem to send next request
        self.base_wait = 300
        self.max_wait = self.base_wait * 5

    def match_dinaa_ids(self, proj_limit, limit=False):
        """ get a key word for a site """
        found_matches = 0
        if limit is not False:
            tris = Trinomial.objects.filter(trinomial__isnull=False,
                                            project_label__contains=proj_limit,
                                            tdar_checked__isnull=True)[:limit]
        else:
            tris = Trinomial.objects.filter(trinomial__isnull=False,
                                            project_label__contains=proj_limit,
                                            tdar_checked__isnull=True)
        len_tris = len(tris)
        i = 1
        for tri in tris:
            found_matches += self.match_trinomial_obj(tri)
            if self.request_error is False:
                tri.tdar_checked_save()
                print('Total tDAR matches: ' + str(found_matches) + ', Checked item: ' + str(i) + ' of ' + str(len_tris))
            i += 1
        return found_matches

    def match_trinomial_obj(self, tri):
        """ Attempts to match a trinomial object 'tri'
            against tDAR, if it hasn't yet been matched
        """
        found_matches = 0
        manifest = False
        try:
            manifest = Manifest.objects.get(uuid=tri.uuid)
        except Manifest.DoesNotExist:
            manifest = False
        la_check = LinkAnnotation.objects\
                                 .filter(subject=tri.uuid,
                                         predicate_uri='dc-terms:subject',
                                         object_uri__contains=self.TDAR_VOCAB)[:1]
        if len(la_check) < 1 and manifest is not False:
            # we don't already have a tDAR id for this item, continue with matches
            tri_man = TrinomialManage()
            request_keywords = [tri.trinomial]
            if self.lead_zero_check:
                # check multiple leading zeros
                tri_parts = tri_man.parse_trinomial(tri.trinomial)
                site = tri_parts['site']
                site_part_len = len(site)
                while len(site) < 4:
                    site = '0' + site
                    new_trinomial = tri_parts['state'] + tri_parts['county'] + site
                    request_keywords.append(new_trinomial)
            for keyword in request_keywords:
                tdar_api = tdarAPI()
                results = tdar_api.get_site_keyword(keyword)
                if isinstance(results, list):
                    for result in results[:self.max_results]:
                        # assume it is a spurious match
                        match_real = False
                        if result['label'] == tri.trinomial:
                            # the trinomial and the tDAR result exactly match
                            match_real = True
                        else:
                            # check if the only difference is in leading zeros
                            tri_parts = tri_man.parse_trinomial(tri.trinomial)
                            site = tri_parts['site']
                            site_part_len = len(site)
                            while len(site) < 5:
                                site = '0' + site
                                new_trinomial = tri_parts['state'] + tri_parts['county'] + site
                                if new_trinomial == result['label']:
                                    # A good match, the tDAR result and the trinomial
                                    # match (but with different leading zeros)
                                    match_real = True
                        if match_real:
                            found_matches += 1
                            # OK! Found a match, first save the linked entity in the link entity table
                            le_check = False
                            try:
                                le_check = LinkEntity.objects.get(uri=result['id'])
                            except LinkEntity.DoesNotExist:
                                le_check = False
                            if le_check is False:
                                le = LinkEntity()
                                le.uri = result['id']
                                le.label = result['label']
                                le.alt_label = result['label']
                                le.vocab_uri = self.TDAR_VOCAB
                                le.ent_type = 'type'
                                le.save()
                            # Now save the link annotation
                            la = LinkAnnotation()
                            la.subject = tri.uuid
                            la.subject_type = manifest.item_type
                            la.project_uuid = manifest.project_uuid
                            la.source_id = 'tdar-api-lookup'
                            la.predicate_uri = self.DC_TERMS_SUBJECT
                            la.object_uri = result['id']
                            la.save()
                        else:
                            print('Almost! ' + result['label'] + ' is not exactly: ' + tri.trinomial)
                if tdar_api.request_error:
                    self.request_error = True
                    print('HTTP request to tDAR failed!')
                    self.error_wait += self.base_wait
                    if self.error_wait > self.max_wait:
                        print('Too many failures, quiting...')
                        sys.exit('Quitting process')
                    else:
                        # sleep some minutes before trying again
                        print('Will try again in ' + str(self.error_wait) + ' seconds...')
                        sleep(self.error_wait)
                else:
                    self.request_error = False
                    if self.error_wait >= self.base_wait:
                        print('HTTP requests resumed OK, will continue.')
                        self.error_wait = 0
        return found_matches


    def match_california_sites(self):
        """ Attempts to match California site name with a tDAR
            site key word
        """
        found_matches = 0
        ca_subjects = Subject.objects.filter(context__startswith='United States/California')
        for ca_subj in ca_subjects:
            ok_mans = Manifest.objects.filter(uuid=ca_subj.uuid,
                                              class_uri='oc-gen:cat-site')[:1]
            if len(ok_mans) > 0:
                # we have a site in the manifest!
                print('Check site: ' + ok_mans[0].label + '; Matches found: ' + str(found_matches))
                found_matches += self.match_california_site(ca_subj.uuid)
        
    def match_california_site(self, site_uuid):
        """ Attempts to match California site name with a tDAR
            site key word
        """
        found_matches = 0
        oc_item = OCitem()
        exists = oc_item.check_exists(site_uuid)
        if exists:
            la_check = LinkAnnotation.objects\
                                     .filter(subject=site_uuid,
                                             predicate_uri='dc-terms:subject',
                                             object_uri__contains=self.TDAR_VOCAB)[:1]
        if exists and len(la_check) < 1:
            # we don't already have a tDAR id for this item, continue with matches
            # first, generate the item's JSON-LD
            oc_item.generate_json_ld()
            request_keywords = []
            if 'oc-gen:has-obs' in oc_item.json_ld:
                if isinstance(oc_item.json_ld['oc-gen:has-obs'], list):
                    for obs in oc_item.json_ld['oc-gen:has-obs']:
                        if 'oc-pred:52-alternate-site-or-place-name' in obs:
                            if isinstance(obs['oc-pred:52-alternate-site-or-place-name'], list): 
                                for name_obj in obs['oc-pred:52-alternate-site-or-place-name']:
                                    if 'xsd:string' in name_obj:
                                        if isinstance(name_obj['xsd:string'], str):
                                            name_str = name_obj['xsd:string']
                                            request_keywords.append(name_str)
            print('Checking names in tDAR: ' + '; '.join(request_keywords))
            for keyword in request_keywords:
                tdar_api = tdarAPI()
                results = tdar_api.get_site_keyword(keyword)
                if isinstance(results, list):
                    for result in results[:self.max_results]:
                        # assume it is a spurious match
                        match_real = False
                        lw_result = result['label'].lower()
                        lw_keyword = keyword.lower()
                        if lw_result == lw_keyword:
                            # the trinomial and the tDAR result exactly match
                            match_real = True
                        if match_real:
                            print('FOUND ' + result['label'])
                            found_matches += 1
                            # OK! Found a match, first save the linked entity in the link entity table
                            le_check = False
                            try:
                                le_check = LinkEntity.objects.get(uri=result['id'])
                            except LinkEntity.DoesNotExist:
                                le_check = False
                            if le_check is False:
                                le = LinkEntity()
                                le.uri = result['id']
                                le.label = result['label']
                                le.alt_label = result['label']
                                le.vocab_uri = self.TDAR_VOCAB
                                le.ent_type = 'type'
                                le.save()
                            # Now save the link annotation
                            la = LinkAnnotation()
                            la.subject = oc_item.manifest.uuid
                            la.subject_type = oc_item.manifest.item_type
                            la.project_uuid = oc_item.manifest.project_uuid
                            la.source_id = 'tdar-api-lookup'
                            la.predicate_uri = self.DC_TERMS_SUBJECT
                            la.object_uri = result['id']
                            la.save()
                        else:
                            print('Almost! ' + result['label'] + ' is not exactly: ' + keyword)
                if tdar_api.request_error:
                    self.request_error = True
                    print('HTTP request to tDAR failed!')
                    self.error_wait += self.base_wait
                    if self.error_wait > self.max_wait:
                        print('Too many failures, quiting...')
                        sys.exit('Quitting process')
                    else:
                        # sleep some minutes before trying again
                        print('Will try again in ' + str(self.error_wait) + ' seconds...')
                        sleep(self.error_wait)
                else:
                    self.request_error = False
                    if self.error_wait >= self.base_wait:
                        print('HTTP requests resumed OK, will continue.')
                        self.error_wait = 0
        return found_matches


    def cache_db_tdar_refs(self, overwrite=True):
        """ caches in the database items in tDAR that cross-reference
            with Open Context plances.
            
            Calls the tDAR API to do so
        """
        if overwrite:
            tdar_annos = LinkAnnotation.objects\
                                       .filter(subject_type='subjects',
                                               object_uri__contains=tdarAPI.BASE_URI)
        else:
            tdar_annos = LinkAnnotation.objects\
                                       .filter(subject_type='subjects',
                                               object_uri__contains=tdarAPI.BASE_URI,
                                               obj_extra=None)
        for tdar_anno in tdar_annos:
            print('Checking: ' + str(tdar_anno.object_uri))
            tdar = tdarAPI()
            tdar.pause_request()
            tdar_items = tdar.search_by_site_keyword_uris(tdar_anno.object_uri)
            if isinstance(tdar_items, list):
                print('Found: ' + str(len(tdar_items)) + ' items')
                tdar_anno.obj_extra = {'dc-terms:isReferencedBy': tdar_items}
                tdar_anno.save()