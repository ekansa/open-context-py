from django.utils.html import strip_tags
from django.conf import settings
from opencontext_py.libs.rootpath import RootPath
from opencontext_py.apps.entities.uri.models import URImanagement
from opencontext_py.apps.searcher.solrsearcher.templating import ResultRecord
from opencontext_py.apps.ocitems.projects.models import Project
from opencontext_py.apps.ldata.linkannotations.models import LinkAnnotation
from opencontext_py.apps.ldata.linkannotations.equivalence import LinkEquivalence
from opencontext_py.apps.entities.entity.models import Entity
from opencontext_py.apps.entities.uri.models import URImanagement


class ProjectAugment():
    """ methods augment the search results
        with some extra data from the database
    """
    
    # metadata for augemented description
    DC_META_PREDS = ['dc-terms:creator',
                     'dc-terms:spatial',
                     'dc-terms:subject',
                     'dc-terms:coverage',
                     'dc-terms:temporal']

    def __init__(self, json_ld):
        rp = RootPath()
        self.base_url = rp.get_baseurl()
        if isinstance(json_ld, dict):
            self.json_ld = json_ld
            self.ok = True
        else:
            self.ok = False
        self.raw_records = []
        self.records = []

    def process_json_ld(self):
        """ processes JSON-LD to make a view """
        if self.ok:
            if 'features' in self.json_ld:
                for feature in self.json_ld['features']:
                    if 'category' in feature:
                        if feature['category'] == 'oc-api:geo-record':
                            geor = ResultRecord()
                            geor.parse_json_record(feature)
                            if geor.uuid is not False:
                                self.raw_records.append(geor)
            if 'oc-api:has-results' in self.json_ld:
                for json_rec in self.json_ld['oc-api:has-results']:
                    rr = ResultRecord()
                    rr.parse_json_record(json_rec)
                    if rr.uuid is not False:
                        self.raw_records.append(rr)
            if len(self.raw_records) > 0:
                self.augment_projects()
    
    def augment_projects(self):
        """ adds some additional informaiton about projects
            to make them easier to display
        """
        uuids = []
        for proj_r in self.raw_records:
            uuids.append(proj_r.uuid)
        # now query the database for all the records with these uuids
        proj_objs = Project.objects\
                           .filter(uuid__in=uuids)
        # now make a dict object to easily get project info by a UUID key
        proj_obj_dict = {}
        for proj_obj in proj_objs:
            proj_obj_dict[proj_obj.uuid] = proj_obj
        # now query the database for all of the dc related predicates
        le = LinkEquivalence()
        subjects = le.get_identifier_list_variants(uuids)
        predicates = le.get_identifier_list_variants(self.DC_META_PREDS)
        dc_annos = LinkAnnotation.objects\
                                 .filter(subject__in=subjects,
                                         predicate_uri__in=predicates)
        # now make a dict object to easily get annotations by UUID key
        dc_anno_dict = {}
        for dc_anno in dc_annos:
            dc_pred = URImanagement.prefix_common_uri(dc_anno.predicate_uri)
            dc_pred = dc_pred.replace('dc-terms:', '')  # remove namespace prefix
            if dc_anno.subject not in dc_anno_dict:
                dc_anno_dict[dc_anno.subject] = {}
            if dc_pred not in dc_anno_dict[dc_anno.subject]:
                dc_anno_dict[dc_anno.subject][dc_pred] = []
            if dc_anno.object_uri not in dc_anno_dict[dc_anno.subject][dc_pred]:
                dc_anno_dict[dc_anno.subject][dc_pred].append(dc_anno.object_uri)
        # now add information we got from queries and organized into dicts
        # to the project response objects
        for proj_r in self.raw_records:
            if proj_r.uuid in proj_obj_dict:
                # add projects objects from the database
                proj_r.extra = proj_obj_dict[proj_r.uuid]
            if proj_r.uuid in dc_anno_dict:
                # add annotations from the database
                proj_r.dc = {'meta': []}
                for pred, object_uris in dc_anno_dict[proj_r.uuid].items():
                    proj_r.dc[pred] = []
                    for object_uri in object_uris:
                        ent = Entity()
                        found = ent.dereference(object_uri)
                        if found:
                            obj_obj = {'id': object_uri,
                                       'label': ent.label}
                            if ent.item_type == 'uri':
                                obj_obj['href'] = ent.uri
                            else:
                                obj_obj['href'] = self.base_url \
                                                  + '/' + ent.item_type \
                                                  + '/' + ent.uuid
                            proj_r.dc[pred].append(obj_obj)
                            if pred != 'creator' and pred != 'temporal':
                                proj_r.dc['meta'].append(obj_obj)
            self.records.append(proj_r)  # now append the augmented record   

