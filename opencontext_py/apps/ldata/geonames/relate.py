import sys
import json
from time import sleep
from opencontext_py.apps.ldata.geonames.api import GeonamesAPI
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.ocitems.assertions.models import Assertion
from opencontext_py.apps.ocitems.subjects.models import Subject
from opencontext_py.apps.ldata.linkannotations.models import LinkAnnotation
from opencontext_py.apps.ocitems.geospace.models import Geospace
from opencontext_py.apps.ldata.linkentities.models import LinkEntity


class GeoRelate():
    """ methods to add links to Geonames for Open Context subject
        items that are part of project "0" (the Open Context entities)

from opencontext_py.apps.ldata.geonames.relate import GeoRelate
geo_rel = GeoRelate()
geo_rel.find_related_geonames('ekansa')

    """

    FIRST_ADMIN_ROOTS = ['Australia']
    SECOND_ADMIN_ROOTS = ['United States',
                          'Canada',
                          'Mexico']

    def __init__(self):
        self.request_error = False
        self.new_geodata = 0
        self.overwrite = False
        self.specifity = 0

    def find_related_geonames(self, username='demo'):
        """ Adds geonames spatial data for items with geonames annotations """
        man_objs = Manifest.objects\
                           .filter(project_uuid='0',
                                   class_uri='oc-gen:cat-region',
                                   item_type='subjects')
        for man_obj in man_objs:
            print('Checking slug: ' + man_obj.slug)
            subj_obj = Subject.objects.get(uuid=man_obj.uuid)
            context = subj_obj.context
            if '/' in context:
                cont_ex = context.split('/')
                admin_level = len(cont_ex) - 1
                if admin_level < 0:
                    admin_level = 0
            else:
                admin_level = 0
            q_str = context.replace('/', ' ')
            geo_api = GeonamesAPI()
            json_r = geo_api.search_admin_entity(q_str,
                                                 admin_level,
                                                 username)
            if isinstance(json_r, dict):
                # we found a result from GeoNames!
                print('Geonames result found.')
                if 'geonames' in json_r:
                    if len(json_r['geonames']) > 0:
                        # we've got a result
                        geo_id = json_r['geonames'][0]['geonameId']
                        label = json_r['geonames'][0]['name']
                        alt_label = json_r['geonames'][0]['toponymName']
                        geonames_uri = 'http://www.geonames.org/' + str(geo_id)
                        l_ents = LinkEntity.objects\
                                           .filter(uri=geonames_uri)[:1]
                        if len(l_ents) < 1:
                            # we need to create this entity
                            ent = LinkEntity()
                            ent.uri = geonames_uri
                            ent.label = label
                            ent.alt_label = alt_label
                            ent.vocab_uri = GeonamesAPI().VOCAB_URI
                            ent.ent_type = 'class'
                            ent.save()
                        print(geonames_uri)
                        annos = LinkAnnotation.objects\
                                              .filter(subject=man_obj.uuid,
                                                      object_uri=geonames_uri)[:1]
                        if len(annos) < 1:
                            # we need to add the annotation linking this item
                            print('Adding new annotation!')
                            new_la = LinkAnnotation()
                            new_la.subject = man_obj.uuid
                            new_la.subject_type = man_obj.item_type
                            new_la.project_uuid = man_obj.project_uuid
                            new_la.source_id = man_obj.source_id
                            new_la.predicate_uri = 'skos:closeMatch'
                            new_la.object_uri = geonames_uri
                            new_la.creator_uuid = ''
                            new_la.save()
                        else:
                            print('Relation already known.')
        
        
    