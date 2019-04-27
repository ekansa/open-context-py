"""
One off processing scripts to handle edge cases, cleanup, and straggler data
"""


from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.imports.records.models import ImportCell
from opencontext_py.apps.ldata.linkentities.models import LinkEntity
from opencontext_py.apps.ldata.linkannotations.models import LinkAnnotation
from opencontext_py.apps.ocitems.identifiers.ezid.ezid import EZID
from opencontext_py.apps.ocitems.strings.manage import StringManagement
from opencontext_py.apps.ocitems.assertions.models import Assertion
ezid = EZID()
# ezid.ark_shoulder = EZID.ARK_TEST_SHOULDER
source_id = 'ref:2348747658045'
pred_uuid = '74b9bacf-e5e8-4f3a-b43d-18bab4b2d635'
project_uuid = '141e814a-ba2d-4560-879f-80f1afb019e9'
pdf_base_link = 'https://archive.org/download/ArchaeologyOfAnImage/Archaeology-of-an-Image.pdf'
pdf_page_offset = 0
page_link_dict = {}
uuid_pages = {}
imp_uuid_cells = ImportCell.objects.filter(source_id=source_id, field_num=5)
for imp_uuid in imp_uuid_cells:
    uuid = imp_uuid.record
    man_objs = Manifest.objects.filter(uuid=uuid)[:1]
    if len(man_objs) > 0:
        man_obj = man_objs[0]
        # get pages
        imp_page_cells = ImportCell.objects.filter(source_id=source_id, field_num=3, row_num=imp_uuid.row_num)[:1]
        imp_link_cells = ImportCell.objects.filter(source_id=source_id, field_num=6, row_num=imp_uuid.row_num)[:1]
        imp_link = imp_link_cells[0]
        page_str = imp_page_cells[0].record
        page_ex = page_str.split(',')
        page_links = []
        for page in page_ex:
            page = page.strip()
            page_num = None
            ark_uri = None
            try:
                page_num = int(float(page))
            except:
                page_num = None
            if len(page) > 0 and isinstance(page_num, int):
                if uuid not in uuid_pages:
                    uuid_pages[uuid] = []
                if page_num not in uuid_pages[uuid]:
                    uuid_pages[uuid].append(page_num)
                pdf_page = pdf_page_offset + page_num
                pdf_link = pdf_base_link + '#page=' + str(pdf_page)
                if  pdf_link not in page_link_dict:
                    page_link_dict[pdf_link] = {
                        'ark_uri': None,
                        'uuids': []
                    }
                    meta = {
                        'erc.who': 'Mark Lehner',
                        'erc.what': 'The Archaeology of an Image: The Great Sphinx of Giza (Page: ' + page  + ')',
                        'erc.when': 1991
                    }
                    url = pdf_link
                    ark_id = ezid.mint_identifier(url, meta, 'ark')
                    if isinstance(ark_id, str):
                        ark_uri = 'https://n2t.net/' + ark_id
                        page_link_dict[pdf_link]['ark_uri'] = ark_uri
                else:
                    ark_uri = page_link_dict[pdf_link]['ark_uri']
                if uuid not in page_link_dict[pdf_link]['uuids']:
                    page_link_dict[pdf_link]['uuids'].append(uuid)
                if isinstance(ark_uri, str):
                    print('Page: ' + page + ' at: ' + ark_uri + ' to: ' + pdf_link)
                    a_link = '<a href="' + ark_uri + '" target="_blank" title="Jump to page ' + page + ' in the dissertation">' + page + '</a>'
                    if a_link not in page_links:
                        page_links.append(a_link)
        all_pages = ', '.join(page_links)
        imp_link.record = all_pages
        imp_link.save()
        imp_link_cells = ImportCell.objects.filter(source_id=source_id, field_num=6, row_num=imp_uuid.row_num)[:1]
        all_pages = imp_link_cells[0].record
        page_notes = '<div><p>Associated pages:</p> <p>' + all_pages + '</p></div>'
        str_m = StringManagement()
        str_m.project_uuid = man_obj.project_uuid
        str_m.source_id = source_id
        str_obj = str_m.get_make_string(page_notes)
        Assertion.objects.filter(uuid=man_obj.uuid, predicate_uuid=pred_uuid).delete()
        new_ass = Assertion()
        new_ass.uuid = man_obj.uuid
        new_ass.subject_type = man_obj.item_type
        new_ass.project_uuid = man_obj.project_uuid
        new_ass.source_id = source_id
        new_ass.obs_node = '#obs-1'
        new_ass.obs_num = 1
        new_ass.sort = 50
        new_ass.visibility = 1
        new_ass.predicate_uuid = pred_uuid # predicate note for about non-specialist
        new_ass.object_type = 'xsd:string'
        new_ass.object_uuid = str_obj.uuid # tb entry
        try:
            new_ass.save()
        except:
            pass
       
        

# Makes a note that a cataloged item was described by a specialist
# Makes cataloging descriptions appear in the 2nd observation tab
from opencontext_py.apps.ocitems.strings.manage import StringManagement
from opencontext_py.apps.ocitems.obsmetadata.models import ObsMetadata
from opencontext_py.apps.ocitems.assertions.models import Assertion
from opencontext_py.apps.entities.entity.models import Entity
has_sp_des_pred = '7c053560-2385-43af-af11-6e58afdbeb10'
sp_note_pred = 'b019efa8-c67a-4641-9340-b667ab73d498'
sp_pred_asses = Assertion.objects.filter(predicate_uuid=has_sp_des_pred)
change_obj_types = [
    "types",
    "xsd:integer",
    "xsd:double",
    "xsd:date",
    "xsd:string",
    "complex-description",
    "xsd:boolean"
]
class_lookups = {
    'oc-gen:cat-human-bone': 'Suellen Gauld (Bioarchaeology / Human Remains)',
    'oc-gen:cat-animal-bone': 'Sarah Whitcher Kansa (Zooarchaeology / Animal Remains)'
}
change_source_ids = []
uuid_entities = {}
for ass in sp_pred_asses:
    uuid = ass.uuid
    if uuid not in uuid_entities:
        uuid_entities[uuid] = []
    entity = Entity()
    found = entity.dereference(ass.object_uuid)
    print('found a ' + entity.class_uri)
    uuid_entities[uuid].append(entity)
for ass in sp_pred_asses:
    uuid = ass.uuid
    print('Update: ' + uuid)
    note = '<div>'
    note += '<p><strong>Catalog Record with Specialist Descriptions</strong></p>'
    note += '<p>This catalog record has additional descriptive information provided by one or more '
    note += 'specialized researchers. Specialist provided descriptions should be regarded as more '
    note += 'authoritative.</p>'
    note += '<br/>'
    note += '<p>Links to Specialist Records:</p>'
    note += '<ul class="list-unstyled">'
    for entity in uuid_entities[uuid]:
        note += '<li>'
        note += '<a target="_blank" href="../../subjects/' + entity.uuid + '">' + entity.label + '</a>'
        note += '; described by '
        note += class_lookups[entity.class_uri]
        note += '</li>'
    note += '</ul>'
    note += '</div>'
    str_m = StringManagement()
    str_m.project_uuid = ass.project_uuid
    str_m.source_id = 'catalog-specialist-note'
    str_obj = str_m.get_make_string(note)
    new_ass = Assertion()
    new_ass.uuid = uuid
    new_ass.subject_type = ass.subject_type
    new_ass.project_uuid = ass.project_uuid
    new_ass.source_id = 'catalog-specialist-note'
    new_ass.obs_node = '#obs-1'
    new_ass.obs_num = 1
    new_ass.sort = 1
    new_ass.visibility = 1
    new_ass.predicate_uuid = sp_note_pred # predicate note for about non-specialist
    new_ass.object_type = 'xsd:string'
    new_ass.object_uuid = str_obj.uuid # tb entry
    try:
        new_ass.save()
    except:
        pass
    change_asses = Assertion.objects\
                            .filter(uuid=uuid,
                                    obs_num=1,
                                    object_type__in=change_obj_types)\
                            .exclude(predicate_uuid=sp_note_pred)\
                            .exclude(source_id__startswith='sec-')\
                            .exclude(source_id='catalog-specialist-note')\
                            .exclude(visibility=0)
    for change_ass in change_asses:
        new_change_ass = change_ass
        change_ass.visibility = 0
        change_ass.save()
        new_change_ass.hash_id = None
        new_change_ass.visibility = 0
        new_source_id = 'sec-' + change_ass.source_id
        new_change_ass.source_id = new_source_id
        new_change_ass.obs_node = '#obs-2'
        new_change_ass.obs_num = 2
        try:
            new_change_ass.save()
        except:
            pass
        if new_source_id not in change_source_ids:
            # make new source metadata
            ometa = ObsMetadata()
            ometa.source_id = new_source_id
            ometa.project_uuid = ass.project_uuid
            ometa.obs_num = 2
            ometa.label = 'Non-Specialist Description'
            ometa.obs_type = 'oc-gen:primary'
            ometa.note = 'From cataloging'
            try:
                ometa.save()
            except:
                pass
            change_source_ids.append(new_source_id)





from opencontext_py.apps.ocitems.assertions.models import Assertion
pred_uuid = '59415979-72f8-4558-9e74-052fae4eed07'
asses = Assertion.objects.filter(predicate_uuid=pred_uuid)
for ass in asses:
    asses_check = Assertion.objects.filter(uuid=ass.uuid,
                                           predicate_uuid=pred_uuid)
    if len(asses_check) > 1:
        all_item_count = 0
        print('Multiple counts for: ' + ass.uuid + ' source: ' + ass.source_id)
        for item_ass in asses_check:
            new_source_id = item_ass.source_id + '-fix'
            try:
                item_count = int(float(item_ass.data_num))
            except:
                item_count = 0
            print('Item count: ' + str(item_count))
            all_item_count  += item_count
        if all_item_count > 0:
            new_ass = asses_check[0]
            new_ass.hash_id = None
            new_source_id = new_ass.source_id + '-fix'
            new_ass.source_id = new_source_id
            new_ass.data_num = all_item_count
            new_ass.save()
            bad_ass = Assertion.objects\
                               .filter(uuid=ass.uuid,
                                       predicate_uuid=pred_uuid)\
                               .exclude(source_id=new_source_id)\
                               .delete()



from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.ldata.linkentities.models import LinkEntity
from opencontext_py.apps.ldata.linkannotations.models import LinkAnnotation
from opencontext_py.apps.ocitems.subjects.models import Subject
ca_subjects = Subject.objects.filter(context__startswith='United States/California',
                                     project_uuid='416A274C-CF88-4471-3E31-93DB825E9E4A')
pred_uri = 'dc-terms:isReferencedBy'
hearst_uri = 'http://hearstmuseum.berkeley.edu'
for ca_subj in ca_subjects:
    ok_mans = Manifest.objects.filter(uuid=ca_subj.uuid,
                                      class_uri='oc-gen:cat-site')[:1]
    annos = LinkAnnotation.objects.filter(subject=ca_subj.uuid,
                                          predicate_uri=pred_uri,
                                          object_uri=hearst_uri)[:1]
    if len(ok_mans) > 0 and len(annos) < 1:
        # we have a site in the manifest that has no links to the hearst
        man_obj = ok_mans[0]
        print('Relate Hearst to site: ' + man_obj.label)
        la = LinkAnnotation()
        la.subject = man_obj.uuid  # the subordinate is the subject
        la.subject_type = man_obj.item_type
        la.project_uuid = man_obj.project_uuid
        la.source_id = 'hearst-link'
        la.predicate_uri = pred_uri
        la.object_uri = hearst_uri
        try:
            la.save()
        except:
            pass



import json
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.ocitems.subjects.models import Subject
from opencontext_py.apps.ocitems.geospace.models import Geospace
from opencontext_py.apps.indexer.reindex import SolrReIndex
from opencontext_py.apps.imports.records.models import ImportCell
from opencontext_py.apps.imports.fieldannotations.models import ImportFieldAnnotation
source_id = 'ref:1990625792930'
project_uuid = '416A274C-CF88-4471-3E31-93DB825E9E4A'
uuids = []
man_objs = Manifest.objects.filter(project_uuid=project_uuid,
                                   class_uri='oc-gen:cat-site')
for man_obj in man_objs:
    geos = Geospace.objects.filter(uuid=man_obj.uuid)[:1]
    if len(geos) < 1:
        # no geospatial data
        label_cells = ImportCell.objects.filter(source_id=source_id,
                                                field_num=1,
                                                record=man_obj.uuid)
        for label_cell in label_cells:
            lat = None
            lon = None
            row_num = label_cell.row_num
            lat_cells = ImportCell.objects.filter(source_id=source_id,
                                                  field_num=11,
                                                  row_num=row_num)[:1]
            lon_cells = ImportCell.objects.filter(source_id=source_id,
                                                  field_num=12,
                                                  row_num=row_num)[:1]
            if len(lat_cells) > 0 and len(lon_cells) >0:
                try:
                    lat = float(lat_cells[0].record)
                except:
                    lat = None
                try:
                    lon = float(lon_cells[0].record)
                except:
                    lon = None
            if isinstance(lat, float) and isinstance(lon, float):
                uuids.append(man_obj.uuid)
                geo = Geospace()
                geo.uuid = man_obj.uuid
                geo.project_uuid = man_obj.project_uuid
                geo.source_id = source_id + '-geofix'
                geo.item_type = man_obj.item_type
                geo.feature_id = 1
                geo.meta_type = ImportFieldAnnotation.PRED_GEO_LOCATION
                geo.ftype = 'Point'
                geo.latitude = lat
                geo.longitude = lon
                geo.specificity = -11
                # dump coordinates as json string in lon - lat (GeoJSON order)
                geo.coordinates = json.dumps([lon, lat],
                                             indent=4,
                                             ensure_ascii=False)
                try:
                    geo.save()
                except:
                    print('Did not like ' + man_obj.label + ' uuid: ' + str(man_obj.uuid))

sri = SolrReIndex()
sri.reindex_uuids(uuids)



from opencontext_py.apps.ocitems.obsmetadata.models import ObsMetadata
from opencontext_py.apps.ocitems.assertions.observations import AssertionObservations
ometa = ObsMetadata()
ometa.source_id = 'ref:1716440680966'
ometa.project_uuid = 'DF043419-F23B-41DA-7E4D-EE52AF22F92F'
ometa.obs_num = 5
ometa.label = 'Grid Coordinates'
ometa.obs_type = 'oc-gen:primary'
ometa.note = 'X, Y, and sometimes Z spatial coordinates'
ometa.save()
class_uri = 'oc-gen:cat-object'
aos = AssertionObservations()
aos.change_obs_num_by_source_id(ometa.obs_num, ometa.source_id, class_uri)
class_uris = [
'oc-gen:cat-object',
'oc-gen:cat-arch-element',
'oc-gen:cat-glass',
'oc-gen:cat-pottery',
'oc-gen:cat-coin']
for class_uri in class_uris:
    aos = AssertionObservations()
    aos.change_obs_num_by_source_id(ometa.obs_num, ometa.source_id, class_uri)
    


from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.apps.ocitems.assertions.models import Assertion
from opencontext_py.apps.ocitems.manifest.models import Manifest
media_uuid = '6c89e96d-d97e-4dba-acbe-e822fc1f87e7'
project_uuid = 'DF043419-F23B-41DA-7E4D-EE52AF22F92F'
media_man = Manifest.objects.get(uuid=media_uuid)
if not isinstance(media_man.sup_json, dict):
    meta = LastUpdatedOrderedDict()
else:
    meta = media_man.sup_json

meta['Leaflet'] = LastUpdatedOrderedDict()
meta['Leaflet']['bounds'] = [[43.153660, 11.402448],[43.152420, 11.400873]]
meta['Leaflet']['label'] = 'Orientalizing, Archaic Features'
media_man.sup_json = meta
media_man.save()

Assertion.objects\
         .filter(uuid=project_uuid,
                 predicate_uuid=Assertion.PREDICATES_GEO_OVERLAY)\
         .delete()

from opencontext_py.apps.ocitems.assertions.models import Assertion
from opencontext_py.apps.ocitems.manifest.models import Manifest
project_uuid = '10aa84ad-c5de-4e79-89ce-d83b75ed72b5'
media_uuid = 'da676164-9829-4798-bb5d-c5b1135daa27'
media_man = Manifest.objects.get(uuid=media_uuid)

ass = Assertion()
ass.uuid = project_uuid
ass.subject_type = 'projects'
ass.project_uuid = project_uuid
ass.source_id = 'heit-el-ghurab-geo-overlay'
ass.obs_node = '#obs-' + str(1)
ass.obs_num =  1
ass.sort = 1
ass.visibility = 1
ass.predicate_uuid = Assertion.PREDICATES_GEO_OVERLAY
ass.object_uuid = media_man.uuid
ass.object_type = media_man.item_type
ass.save()


from opencontext_py.apps.ocitems.identifiers.ezid.manage import EZIDmanage
from opencontext_py.apps.ocitems.manifest.models import Manifest
mans = Manifest.objects.filter(source_id='ref:2181193573133')
ezid_m = EZIDmanage()
for man in mans:
    ezid_m.make_save_ark_by_uuid(man.uuid)

from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.apps.ocitems.assertions.models import Assertion
from opencontext_py.apps.ocitems.manifest.models import Manifest
media_uuid = 'da676164-9829-4798-bb5d-c5b1135daa27'
project_uuid = '5A6DDB94-70BE-43B4-2D5D-35D983B21515'
media_man = Manifest.objects.get(uuid=media_uuid)
if not isinstance(media_man.sup_json, dict):
    meta = LastUpdatedOrderedDict()
else:
    meta = media_man.sup_json

meta['Leaflet'] = LastUpdatedOrderedDict()
meta['Leaflet']['bounds'] = [[29.9686630883, 31.1427860408999], [29.9723641789999, 31.1396409363999]]
meta['Leaflet']['label'] = 'Heit el-Ghurab Areas'
media_man.sup_json = meta
media_man.save()

Assertion.objects\
         .filter(uuid=project_uuid,
                 predicate_uuid=Assertion.PREDICATES_GEO_OVERLAY)\
         .delete()

ass = Assertion()
ass.uuid = project_uuid
ass.subject_type = 'projects'
ass.project_uuid = project_uuid
ass.source_id = 'test-geo-overlay'
ass.obs_node = '#obs-' + str(1)
ass.obs_num =  1
ass.sort = 1
ass.visibility = 1
ass.predicate_uuid = Assertion.PREDICATES_GEO_OVERLAY
ass.object_uuid = media_man.uuid
ass.object_type = media_man.item_type
ass.save()


















from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.indexer.reindex import SolrReIndex
uuids = []
items = Manifest.objects.filter(project_uuid='416A274C-CF88-4471-3E31-93DB825E9E4A')
for item in items:
    uuids.append(item.uuid)

print('Items to index: ' + str(len(uuids)))
sri = SolrReIndex()
sri.max_geo_zoom = 11
sri.reindex_uuids(uuids)



from opencontext_py.apps.ocitems.assertions.models import Assertion
from opencontext_py.apps.ocitems.mediafiles.models import Mediafile
from opencontext_py.apps.indexer.reindex import SolrReIndex
project_uuid = 'DF043419-F23B-41DA-7E4D-EE52AF22F92F'
source_id = 'pc-iiif-backfill'

meds = Mediafile.objects.filter(project_uuid=project_uuid,
                                source_id=source_id)

req_types = ['oc-gen:thumbnail', 'oc-gen:preview', 'oc-gen:fullfile']
for media in meds:
    for type in req_types:
        media_ok = Mediafile.objects.filter(uuid=media.uuid, file_type=type)
        if not media_ok:
            print('Missing {} for {}'.format(type, media.uuid))
            ia_fulls = Mediafile.objects.filter(uuid=media.uuid, file_type='oc-gen:ia-fullfile')[:1]
            n_media = ia_fulls[0]
            n_media.hash_id = None
            n_media.source_id = ia_fulls[0].source_id
            n_media.file_type = 'oc-gen:fullfile'
            n_media.file_uri = ia_fulls[0].file_uri
            n_media.save()
        
        
        
        base_uri = media.file_uri.replace('/info.json', '')
        for type in types:
            n_media = media
            n_media.hash_id = None
            n_media.source_id = source_id
            n_media.file_type = type['file_type']
            n_media.file_uri = base_uri + type['suffix']
            n_media.save()


        ia_fulls = Mediafile.objects.filter(uuid=media.uuid, file_type='oc-gen:ia-fullfile')[:1]
        if ia_fulls:
            n_media = media
            n_media.hash_id = None
            n_media.source_id = source_id
            n_media.file_type = 'oc-gen:fullfile'
            n_media.file_uri = ia_fulls[0].file_uri
            n_media.save()

        fixed_media.append(media.uuid)



from opencontext_py.apps.ocitems.assertions.models import Assertion
from opencontext_py.apps.ocitems.mediafiles.models import Mediafile
from opencontext_py.apps.indexer.reindex import SolrReIndex
project_uuid = 'DF043419-F23B-41DA-7E4D-EE52AF22F92F'
source_id = 'pc-iiif-backfill'
fixed_media = []
medias = Mediafile.objects.filter(project_uuid=project_uuid, source_id=source_id)
for media in medias:
    if media.uuid not in fixed_media:
        fixed_media.append(media.uuid)

uuids = fixed_media
ass_o = Assertion.objects.filter(uuid__in=fixed_media, object_type='subjects')
for ass in ass_o:
    if ass.object_uuid not in uuids:
        uuids.append(ass.object_uuid)


ass_s = Assertion.objects.filter(object_uuid__in=fixed_media, subject_type='subjects')
for ass in ass_s:
    if ass.object_uuid not in uuids:
        uuids.append(ass.object_uuid)


print('Items to index: ' + str(len(uuids)))
sri = SolrReIndex()
sri.reindex_uuids(uuids)


from opencontext_py.apps.imports.geojson.geojson import GeoJSONimport
gimp = GeoJSONimport()
gimp.load_into_importer = False
gimp.project_uuid = 'DF043419-F23B-41DA-7E4D-EE52AF22F92F'
gimp.source_id = 'vesco_trenches_2017_4326'
json_obj = gimp.load_json_file('pc-geo', 'vesco_trenches_2017_4326.geojson')
gimp.save_no_coord_file(json_obj, 'pc-geo', 'vesco_trenches_2017_4326.geojson')


from opencontext_py.apps.imports.geojson.geojson import GeoJSONimport
from opencontext_py.apps.ocitems.geospace.models import Geospace
print('Delete old PC geospatial data')
Geospace.objects\
        .filter(project_uuid='DF043419-F23B-41DA-7E4D-EE52AF22F92F',
                ftype__in=['Polygon', 'Multipolygon']).delete()

gimp = GeoJSONimport()
gimp.load_into_importer = False
gimp.project_uuid = 'DF043419-F23B-41DA-7E4D-EE52AF22F92F'
gimp.source_id = 'vesco_trenches_2017_4326'
json_obj = gimp.load_json_file('pc-geo', 'vesco_trenches_2017_4326.geojson')

vdm_props = {
    '1': {'uri': 'https://opencontext.org/subjects/4C242A96-3C0A-4187-48CD-6287241F09CD'}, 
'10': {'uri': 'https://opencontext.org/subjects/F6E97C59-EE6F-4824-863E-6596AA68BE2D'}, 
'11': {'uri': 'https://opencontext.org/subjects/F6E97C59-EE6F-4824-863E-6596AA68BE2D'}, 
'12': {'uri': 'https://opencontext.org/subjects/F6E97C59-EE6F-4824-863E-6596AA68BE2D'}, 
'13': {'uri': 'https://opencontext.org/subjects/F6E97C59-EE6F-4824-863E-6596AA68BE2D'}, 
'14': {'uri': 'https://opencontext.org/subjects/E252E83F-68D7-4671-85E3-70ED3A0A62B3'}, 
'15': {'uri': 'https://opencontext.org/subjects/8D6B6694-6E88-4D3F-9494-A9EE95C78B44'}, 
'16': {'uri': 'https://opencontext.org/subjects/8D6B6694-6E88-4D3F-9494-A9EE95C78B44'}, 
'17': {'uri': 'https://opencontext.org/subjects/6d37f225-f83a-4d6b-8e6a-0b138b29f236'}, 
'18': {'uri': 'https://opencontext.org/subjects/33e3d75f-7ba0-4d64-b36c-96daf288d06e'}, 
'19': {'uri': 'https://opencontext.org/subjects/ce22d11f-721a-4050-9576-f807a25ddefa'}, 
'2': {'uri': 'https://opencontext.org/subjects/25A27283-05AF-42E2-C839-3D8605EEC6BD'}, 
'20': {'uri': 'https://opencontext.org/subjects/c7049909-f2de-4b43-a9b4-d19a5c516532'}, 
'21': {'uri': 'https://opencontext.org/subjects/c7049909-f2de-4b43-a9b4-d19a5c516532'}, 
'22': {'uri': 'https://opencontext.org/subjects/608f3452-daf4-4e93-b953-3adb06c7a0cb'}, 
'23': {'uri': 'https://opencontext.org/subjects/5870f6a9-dbb0-425d-9c8b-2424a9fa060a'}, 
'24': {'uri': 'https://opencontext.org/subjects/bf9a4138-7c96-4c54-8553-004444eec143'}, 
'25': {'uri': 'https://opencontext.org/subjects/ad8357b1-b46c-4bfe-a221-25b403dcef0f'}, 
'26': {'uri': 'https://opencontext.org/subjects/244e8a86-c472-47e2-baaf-fcfe3f67a014'}, 
'27': {'uri': 'https://opencontext.org/subjects/7de5e185-77fb-4ff5-b73b-b47b870acae2'}, 
'28': {'uri': 'https://opencontext.org/subjects/d91c02df-bc3c-476a-a48e-6eb735397692'}, 
'3': {'uri': 'https://opencontext.org/subjects/25A27283-05AF-42E2-C839-3D8605EEC6BD'}, 
'4': {'uri': 'https://opencontext.org/subjects/25A27283-05AF-42E2-C839-3D8605EEC6BD'}, 
'5': {'uri': 'https://opencontext.org/subjects/25A27283-05AF-42E2-C839-3D8605EEC6BD'}, 
'6': {'uri': 'https://opencontext.org/subjects/25A27283-05AF-42E2-C839-3D8605EEC6BD'}, 
'7': {'uri': 'https://opencontext.org/subjects/25A27283-05AF-42E2-C839-3D8605EEC6BD'}, 
'8': {'uri': 'https://opencontext.org/subjects/F6E97C59-EE6F-4824-863E-6596AA68BE2D'}, 
'9': {'uri': 'https://opencontext.org/subjects/F6E97C59-EE6F-4824-863E-6596AA68BE2D'},     
}
id_prop = 'PolygonID'
gimp.save_partial_clean_file(json_obj,
    'pc-geo', 'vesco_trenches_2017_4326.geojson',
    id_prop, ok_ids=False, add_props=vdm_props, combine_json_obj=None)

gimp.load_into_importer = False
gimp.process_features_in_file('pc-geo', 'id-clean-coord-vesco_trenches_2017_4326.geojson')


from opencontext_py.apps.imports.geojson.geojson import GeoJSONimport
gimp = GeoJSONimport()
gimp.load_into_importer = False
gimp.project_uuid = 'DF043419-F23B-41DA-7E4D-EE52AF22F92F'
gimp.source_id = 'pc_trenches_2017_4326'
pc_json_obj = gimp.load_json_file('pc-geo', 'pc_trenches_2017_4326.geojson')

pc_props = {
'1': {'uri': 'https://opencontext.org/subjects/17085BC0-4FA1-4236-6426-4861AD48B584'}, 
'10': {'uri': 'https://opencontext.org/subjects/87E9B5C3-0828-4F60-5F9A-DB48CCAB3CCA'}, 
'100': {'uri': 'https://opencontext.org/subjects/A386907E-C61D-4AC4-068D-77F3D2ADFA3E'}, 
'101': {'uri': 'https://opencontext.org/subjects/7E17DFBB-8F0F-4A19-3F74-F9268FBD6813'}, 
'102': {'uri': 'https://opencontext.org/subjects/EF628D6D-2A2D-4E6B-F86A-834A451F8296'}, 
'103': {'uri': 'https://opencontext.org/subjects/4B45D8C9-AF08-4518-1E80-321D2DBDB074'}, 
'104': {'uri': 'https://opencontext.org/subjects/6B8C2C81-B703-4D15-F23E-50A38DD4A387'}, 
'105': {'uri': 'https://opencontext.org/subjects/4BC62D10-69D8-49DB-2CA9-7C3DFD74E0C8'}, 
'106': {'uri': 'https://opencontext.org/subjects/8D224FCC-D368-4993-BC69-A4EDCBCA60D4'}, 
'107': {'uri': 'https://opencontext.org/subjects/AC6DFAF1-8E69-480D-A687-AFDA354FCFF5'}, 
'108': {'uri': 'https://opencontext.org/subjects/11E97C36-9CC5-4616-3C82-771E1EF62BD9'}, 
'109': {'uri': 'https://opencontext.org/subjects/AAB28E39-CEBE-455C-F495-CF7B408971FE'}, 
'11': {'uri': 'https://opencontext.org/subjects/500EC0EE-1078-4BE4-762D-3C66FCF853C2'}, 
'110': {'uri': 'https://opencontext.org/subjects/AAB28E39-CEBE-455C-F495-CF7B408971FE'}, 
'111': {'uri': 'https://opencontext.org/subjects/D68CE259-7E7B-4AE4-590A-4E5EA96265FC'}, 
'112': {'uri': 'https://opencontext.org/subjects/67905CDA-1882-4B23-F0D5-68C45FD0B862'}, 
'113': {'uri': 'https://opencontext.org/subjects/2F24BD3F-2E57-4645-E593-7BA1DB674321'}, 
'114': {'uri': 'https://opencontext.org/subjects/C334AB97-3C6F-4D01-BA1D-C245A73EDE34'}, 
'115': {'uri': 'https://opencontext.org/subjects/658B0F2F-0B65-4013-75E5-0056683D0AC8'}, 
'116': {'uri': 'https://opencontext.org/subjects/5376A5D0-B805-4CEE-490F-78A659777449'}, 
'117': {'uri': 'https://opencontext.org/subjects/C7EAC347-78B3-4FC2-16E2-561ACBA7D836'}, 
'118': {'uri': 'https://opencontext.org/subjects/A63E424C-A2AF-469B-A85D-AC1CC690B2A9'}, 
'119': {'uri': 'https://opencontext.org/subjects/6B98F59B-D05F-4B47-0761-E13EE798C019'}, 
'12': {'uri': 'https://opencontext.org/subjects/A5049327-BCCE-43B2-AA50-2FBEBD620BDF'}, 
'120': {'uri': 'https://opencontext.org/subjects/BF820055-F9BB-4C0B-F214-9495E60B7161'}, 
'121': {'uri': 'https://opencontext.org/subjects/0AC6B338-54BA-41FB-D5D8-59D8227AC31C'}, 
'122': {'uri': 'https://opencontext.org/subjects/30114327-F531-4D7D-2906-A91B80C2A595'}, 
'123': {'uri': 'https://opencontext.org/subjects/E89A8B35-2975-4E7A-4B07-5DC7E17F29E9'}, 
'124': {'uri': 'https://opencontext.org/subjects/DB8A88C9-CA9E-44DD-9E67-ACA26D5AE831'}, 
'125': {'uri': 'https://opencontext.org/subjects/38EB7FE3-D403-4515-D17D-ECCEE1472E3A'}, 
'126': {'uri': 'https://opencontext.org/subjects/14BE93AE-020D-42E2-24AD-604BE3C60F89'}, 
'127': {'uri': 'https://opencontext.org/subjects/9259D8F1-C05C-497F-07C4-E5803BA00709'}, 
'128': {'uri': 'https://opencontext.org/subjects/136A7CDF-13D8-4BAD-4E71-01CB93C4056F'}, 
'129': {'uri': 'https://opencontext.org/subjects/3B24EA00-CA9E-4762-52A2-5A170BCE1402'}, 
'13': {'uri': 'https://opencontext.org/subjects/60F9B8C2-7279-4BF5-9BD1-A0A1C3747017'}, 
'130': {'uri': 'https://opencontext.org/subjects/77830F25-F564-4094-19B9-7DB8ABA08945'}, 
'131': {'uri': 'https://opencontext.org/subjects/3427ED52-FEA9-4E28-E250-4ECF923A116A'}, 
'132': {'uri': 'https://opencontext.org/subjects/3E90BC2C-C826-4A12-6382-131B825BFA27'}, 
'133': {'uri': 'https://opencontext.org/subjects/B0F889B2-6D71-4022-F311-CAA9919A9ECC'}, 
'134': {'uri': 'https://opencontext.org/subjects/BCDC5D9E-BB8B-4159-F6B0-2A9474C123BD'}, 
'135': {'uri': 'https://opencontext.org/subjects/039766CC-521F-46B6-2B98-40210F7DA8F1'}, 
'136': {'uri': 'https://opencontext.org/subjects/56201674-F881-47CC-7000-B2C52FFE9E3A'}, 
'137': {'uri': 'https://opencontext.org/subjects/54252D07-A291-4B75-6C6E-AD4E831F564C'}, 
'138': {'uri': 'https://opencontext.org/subjects/54252D07-A291-4B75-6C6E-AD4E831F564C'}, 
'139': {'uri': 'https://opencontext.org/subjects/6621600B-3B5D-4B99-71F9-E42C18656E59'}, 
'14': {'uri': 'https://opencontext.org/subjects/3C36CD47-17FE-4390-AA8B-0BA9AF8C0A79'}, 
'140': {'uri': 'https://opencontext.org/subjects/4454F19D-C295-4E35-7124-98A6661CFF51'}, 
'141': {'uri': 'https://opencontext.org/subjects/646F3438-9BBF-46F1-71E9-0BEC2E095EA4'}, 
'142': {'uri': 'https://opencontext.org/subjects/847268D2-B10F-4CBB-FFEC-577630572C9C'}, 
'143': {'uri': 'https://opencontext.org/subjects/847268D2-B10F-4CBB-FFEC-577630572C9C'}, 
'144': {'uri': 'https://opencontext.org/subjects/847268D2-B10F-4CBB-FFEC-577630572C9C'}, 
'145': {'uri': 'https://opencontext.org/subjects/99CB9EB0-1EDA-412D-7FBD-04BCD5E44DCF'}, 
'146': {'uri': 'https://opencontext.org/subjects/C7823AAC-4E80-48B0-A6E6-B772C58873A4'}, 
'147': {'uri': 'https://opencontext.org/subjects/7C56C14F-9336-443D-4D1F-602299831244'}, 
'148': {'uri': 'https://opencontext.org/subjects/7C56C14F-9336-443D-4D1F-602299831244'}, 
'149': {'uri': 'https://opencontext.org/subjects/8A9B8A77-37BB-4BF8-DC57-D30EDB73C629'}, 
'15': {'uri': 'https://opencontext.org/subjects/A08A8F9B-DFAC-436C-6D6E-F08EDE4C40DB'}, 
'150': {'uri': 'https://opencontext.org/subjects/2FED46FB-BCF6-439B-B15E-307881DF5011'}, 
'151': {'uri': 'https://opencontext.org/subjects/4C9DE9EB-687B-41CD-E5DC-90CD3B55ADFA'}, 
'152': {'uri': 'https://opencontext.org/subjects/444151E3-24F0-421F-9BD9-6E29DE9F62C7'}, 
'153': {'uri': 'https://opencontext.org/subjects/444151E3-24F0-421F-9BD9-6E29DE9F62C7'}, 
'154': {'uri': 'https://opencontext.org/subjects/4AC3D7E6-8B05-480A-320E-B2AA1266759A'}, 
'155': {'uri': 'https://opencontext.org/subjects/78BB679E-20F6-499C-C274-16BB6A3CD53D'}, 
'156': {'uri': 'https://opencontext.org/subjects/B98E614B-DA64-41BE-1CE8-9E5D3496C96D'}, 
'157': {'uri': 'https://opencontext.org/subjects/A13A7840-04F0-492A-C8E3-C1EA488B006C'}, 
'158': {'uri': 'https://opencontext.org/subjects/F05B2B91-CCD4-4ED0-F2BF-F1E2DBEA354B'}, 
'159': {'uri': 'https://opencontext.org/subjects/F05B2B91-CCD4-4ED0-F2BF-F1E2DBEA354B'}, 
'16': {'uri': 'https://opencontext.org/subjects/BBEF5707-C16F-4BFD-932E-5D9B83F6D9C4'}, 
'160': {'uri': 'https://opencontext.org/subjects/E2E20765-3196-4443-E62C-8C7799708399'}, 
'161': {'uri': 'https://opencontext.org/subjects/04D907B0-A850-4129-03FB-CBABA554171F'}, 
'162': {'uri': 'https://opencontext.org/subjects/BE445D1C-6756-4B3B-4691-5D749A93F7FB'}, 
'163': {'uri': 'https://opencontext.org/subjects/81EDC6F0-153D-4881-3AE7-25E4A8E20806'}, 
'164': {'uri': 'https://opencontext.org/subjects/A3CDCB91-5B30-4305-EFF7-1014AB258A0E'}, 
'165': {'uri': 'https://opencontext.org/subjects/09E36D34-E5DA-432E-9367-057D3ECF26F6'}, 
'166': {'uri': 'https://opencontext.org/subjects/1486CEF9-FB7E-48A5-1468-306C069785BD'}, 
'167': {'uri': 'https://opencontext.org/subjects/4500CA4A-4B5A-41E8-5337-1C77990375AF'}, 
'168': {'uri': 'https://opencontext.org/subjects/A5E7AF56-BB36-4490-2EEB-9F9EA2AE1368'}, 
'169': {'uri': 'https://opencontext.org/subjects/0BD521E1-A442-48DC-C45F-4CA748597550'}, 
'17': {'uri': 'https://opencontext.org/subjects/476CA37D-D70D-443E-45AD-D58B57F9CCEF'}, 
'170': {'uri': 'https://opencontext.org/subjects/E25F27C3-CDFC-4D39-9B9A-A749A8A80F64'}, 
'171': {'uri': 'https://opencontext.org/subjects/E9298DF1-5F47-4BC6-7086-75B9B5E0E880'}, 
'172': {'uri': 'https://opencontext.org/subjects/8EF7AA6F-6CE3-4B45-B488-302E52BB9615'}, 
'173': {'uri': 'https://opencontext.org/subjects/36AA7F2A-F090-43A2-B5C8-A18B16276E6B'}, 
'174': {'uri': 'https://opencontext.org/subjects/9D983826-70DE-48F2-A145-B33A171E8928'}, 
'175': {'uri': 'https://opencontext.org/subjects/5C8BA00A-FD53-4D68-8BA8-8A4A17F4CBD6'}, 
'176': {'uri': 'https://opencontext.org/subjects/66EBB4F3-2E71-49D9-002D-EE6079231F29'}, 
'177': {'uri': 'https://opencontext.org/subjects/6EC9E1CA-1595-4B39-DE94-07669E96D51B'}, 
'178': {'uri': 'https://opencontext.org/subjects/5879C9ED-5FCF-4062-4477-FA5B44250143'}, 
'179': {'uri': 'https://opencontext.org/subjects/373B16B4-8E0F-4008-8D24-43685AA72064'}, 
'18': {'uri': 'https://opencontext.org/subjects/3D84308C-A4D6-4F47-263F-243596729D25'}, 
'180': {'uri': 'https://opencontext.org/subjects/905A30A8-A71D-44DF-3181-437816B64864'}, 
'181': {'uri': 'https://opencontext.org/subjects/09AE421A-F835-4C9B-F74E-45DD9F270E9D'}, 
'182': {'uri': 'https://opencontext.org/subjects/905A30A8-A71D-44DF-3181-437816B64864'}, 
'183': {'uri': 'https://opencontext.org/subjects/F143FA0B-93C8-435F-D34A-BBF4725708AF'}, 
'184': {'uri': 'https://opencontext.org/subjects/8E75346E-ECCB-4BF0-77C1-C33BCB95D18D'}, 
'185': {'uri': 'https://opencontext.org/subjects/CEFDF473-5B63-4B3F-B16F-C4E77E03F2BE'}, 
'186': {'uri': 'https://opencontext.org/subjects/1B0D3E3D-14BE-4951-990B-76835166281C'}, 
'187': {'uri': 'https://opencontext.org/subjects/A0E5EDD4-7388-450B-DF1C-68203EDE247A'}, 
'188': {'uri': 'https://opencontext.org/subjects/AC085185-FEDB-4A4B-D077-FCEAC65730D0'}, 
'189': {'uri': 'https://opencontext.org/subjects/5A9DE9D3-9A86-494F-04C9-487D17FA9D2C'}, 
'19': {'uri': 'https://opencontext.org/subjects/8FAC8645-1EA7-4C7B-60AD-5ECEEB808DC2'}, 
'190': {'uri': 'https://opencontext.org/subjects/E8BDB401-722D-45D4-DC6D-52A041BB1C35'}, 
'191': {'uri': 'https://opencontext.org/subjects/7251FBF7-631D-44C3-C0B6-5753A0E24659'}, 
'192': {'uri': 'https://opencontext.org/subjects/3AA9E720-0371-4443-5A40-5FE6A5E1DCAE'}, 
'193': {'uri': 'https://opencontext.org/subjects/E5E80BD3-81E5-4215-29E8-602D59A2B8D8'}, 
'194': {'uri': 'https://opencontext.org/subjects/51CA7A3E-5D5A-43F6-9B15-937DEC71AB63'}, 
'195': {'uri': 'https://opencontext.org/subjects/BA2D283E-9EC4-47AE-4B5E-3C933662B0FF'}, 
'196': {'uri': 'https://opencontext.org/subjects/041BC004-3A2B-4821-CC1A-F5FFC283E537'}, 
'197': {'uri': 'https://opencontext.org/subjects/6CA4122D-0AF2-4F2B-D8BF-C77584AD386D'}, 
'198': {'uri': 'https://opencontext.org/subjects/9FF8641D-C19B-4DFB-4DE9-65300B0AF24F'}, 
'199': {'uri': 'https://opencontext.org/subjects/EB236367-CCE3-4A53-EB80-351E2E598E90'}, 
'2': {'uri': 'https://opencontext.org/subjects/855F361E-68D8-4BBE-5895-B351F48E8233'}, 
'20': {'uri': 'https://opencontext.org/subjects/DFA0AB59-9398-46B7-3955-5DA0439DFED9'}, 
'200': {'uri': 'https://opencontext.org/subjects/3D75850B-7ECD-4675-B297-3FF2F5106D97'}, 
'201': {'uri': 'https://opencontext.org/subjects/3ECF9E3D-995B-4156-6AB7-87A8BA5BCA99'}, 
'202': {'uri': 'https://opencontext.org/subjects/3ECF9E3D-995B-4156-6AB7-87A8BA5BCA99'}, 
'203': {'uri': 'https://opencontext.org/subjects/AB508F4F-DF85-45D9-C8B1-3147603347E5'}, 
'204': {'uri': 'https://opencontext.org/subjects/AB508F4F-DF85-45D9-C8B1-3147603347E5'}, 
'205': {'uri': 'https://opencontext.org/subjects/171AA8D2-BC5F-4D17-F3B0-5A49DD4E3DB2'}, 
'206': {'uri': 'https://opencontext.org/subjects/0888EE5A-F13A-4E8B-F5FF-959DA485F55B'}, 
'207': {'uri': 'https://opencontext.org/subjects/DE5EFA76-4851-4AFC-DF09-467D249AB1B9'}, 
'208': {'uri': 'https://opencontext.org/subjects/41EC3704-2F60-4CA1-07C3-FBB954170F67'}, 
'209': {'uri': 'https://opencontext.org/subjects/E31ABF39-8A5C-4AC3-C0DE-ACCD8E741502'}, 
'21': {'uri': 'https://opencontext.org/subjects/EC80D676-F07E-4174-E781-8795D4BF599A'}, 
'210': {'uri': 'https://opencontext.org/subjects/42A76947-22B6-4AC1-C96B-46A543A98DFC'}, 
'211': {'uri': 'https://opencontext.org/subjects/8AC933DF-D0C3-479A-9D7F-1BD5854AC9C6'}, 
'212': {'uri': 'https://opencontext.org/subjects/8AC933DF-D0C3-479A-9D7F-1BD5854AC9C6'}, 
'213': {'uri': 'https://opencontext.org/subjects/BFA79728-C24A-431D-94A4-EA96FBCD266A'}, 
'214': {'uri': 'https://opencontext.org/subjects/1F718097-88C2-4292-3396-CDF0C832CDF8'}, 
'215': {'uri': 'https://opencontext.org/subjects/D5F8DC06-7FFD-4309-54BD-A690E1CEC570'}, 
'216': {'uri': 'https://opencontext.org/subjects/B9276437-4E36-4E08-2D09-7FAA0AE7B7D2'}, 
'217': {'uri': 'https://opencontext.org/subjects/B91809DA-A28D-438B-F735-636D941825E1'}, 
'218': {'uri': 'https://opencontext.org/subjects/53EB84D5-7033-4C0A-3473-1703AC111198'}, 
'219': {'uri': 'https://opencontext.org/subjects/F81F3432-2A5C-40E4-CE78-B40E4BE7A3F7'}, 
'22': {'uri': 'https://opencontext.org/subjects/7251FBF7-631D-44C3-C0B6-5753A0E24659'}, 
'220': {'uri': 'https://opencontext.org/subjects/97712850-B663-425C-54BD-914A6AD5AC95'}, 
'221': {'uri': 'https://opencontext.org/subjects/8A817258-0759-47E8-0B1E-FFAC21AD9D3E'}, 
'222': {'uri': 'https://opencontext.org/subjects/1427AB95-F567-4A47-630B-094E82651A49'}, 
'223': {'uri': 'https://opencontext.org/subjects/5E978F37-6FF0-4E05-7D7E-62B5AB2C918F'}, 
'224': {'uri': 'https://opencontext.org/subjects/D0825B7B-9B4F-49F4-A455-88D951C8FADE'}, 
'225': {'uri': 'https://opencontext.org/subjects/E56EEAAE-AE6D-49A5-B2AE-6ED1E4D38655'}, 
'226': {'uri': 'https://opencontext.org/subjects/32B61533-BE8C-481D-CFD9-31C7AA2DB5B0'}, 
'227': {'uri': 'https://opencontext.org/subjects/85401603-A817-48C1-E331-9C63BA143CC9'}, 
'228': {'uri': 'https://opencontext.org/subjects/A7F2CCBF-3A83-4AA0-2BD0-0E2E99900624'}, 
'229': {'uri': 'https://opencontext.org/subjects/19CFB9F3-77F7-4EDF-0B90-E9D6E76BCD77'}, 
'23': {'uri': 'https://opencontext.org/subjects/0F4B79C5-D28E-466D-1B6D-F16B9DDE4F1E'}, 
'230': {'uri': 'https://opencontext.org/subjects/7F063C00-F507-4EB3-A384-B487190459E4'}, 
'231': {'uri': 'https://opencontext.org/subjects/7F063C00-F507-4EB3-A384-B487190459E4'}, 
'232': {'uri': 'https://opencontext.org/subjects/302EA385-93D1-441E-617E-9B5D172EB9EA'}, 
'233': {'uri': 'https://opencontext.org/subjects/E06C5503-D300-4E11-9001-BA93C6F8FDAF'}, 
'234': {'uri': 'https://opencontext.org/subjects/93AB3DC0-E669-45E2-678F-4E41BF0664C4'}, 
'235': {'uri': 'https://opencontext.org/subjects/9736FA6A-3373-4429-50A3-1FB235E00649'}, 
'236': {'uri': 'https://opencontext.org/subjects/C004D54D-C176-4792-BE08-792D9195317A'}, 
'237': {'uri': 'https://opencontext.org/subjects/C004D54D-C176-4792-BE08-792D9195317A'}, 
'238': {'uri': 'https://opencontext.org/subjects/C004D54D-C176-4792-BE08-792D9195317A'}, 
'239': {'uri': 'https://opencontext.org/subjects/B663BA3E-CEF9-40FC-3546-4C5AC7122EFB'}, 
'24': {'uri': 'https://opencontext.org/subjects/6D6DA14B-CDE3-4A36-650D-A80A611C0689'}, 
'240': {'uri': 'https://opencontext.org/subjects/2B395B34-F1D9-4C59-EE39-97E3CE1831A2'}, 
'241': {'uri': 'https://opencontext.org/subjects/0AC6B338-54BA-41FB-D5D8-59D8227AC31C'}, 
'242': {'uri': 'https://opencontext.org/subjects/8161DF34-30A4-4B36-977F-ED68EA59CA5A'}, 
'243': {'uri': 'https://opencontext.org/subjects/6AE46285-0A75-4C91-0C8A-693540D22612'}, 
'244': {'uri': 'https://opencontext.org/subjects/6AE46285-0A75-4C91-0C8A-693540D22612'}, 
'245': {'uri': 'https://opencontext.org/subjects/6AE46285-0A75-4C91-0C8A-693540D22612'}, 
'246': {'uri': 'https://opencontext.org/subjects/1C8A3854-31C8-42DC-D4BB-254ECCE95B62'}, 
'247': {'uri': 'https://opencontext.org/subjects/1C8A3854-31C8-42DC-D4BB-254ECCE95B62'}, 
'248': {'uri': 'https://opencontext.org/subjects/17A80550-E9DA-4D5B-F69B-21A32B3C1458'}, 
'249': {'uri': 'https://opencontext.org/subjects/EF7C1C1F-7CDA-4D22-06D8-E0B6B1C6D9D8'}, 
'25': {'uri': 'https://opencontext.org/subjects/A6B061FA-C808-4282-D03E-8D80A26FF325'}, 
'250': {'uri': 'https://opencontext.org/subjects/E82D1F24-BFAD-49D7-7E19-007759D2E2C8'}, 
'251': {'uri': 'https://opencontext.org/subjects/E82D1F24-BFAD-49D7-7E19-007759D2E2C8'}, 
'252': {'uri': 'https://opencontext.org/subjects/4114E192-9D65-4123-2079-11BD3DD647E3'}, 
'253': {'uri': 'https://opencontext.org/subjects/5C7C5703-C751-4458-9611-3994A62AC974'}, 
'254': {'uri': 'https://opencontext.org/subjects/CCD880A0-1197-4B38-B82F-222C02D10C41'}, 
'255': {'uri': 'https://opencontext.org/subjects/211173B4-BA77-42E7-7A84-AFACA458D082'}, 
'256': {'uri': 'https://opencontext.org/subjects/F1DC6BC7-F794-4429-13FA-65D4D52475C5'}, 
'257': {'uri': 'https://opencontext.org/subjects/1B0D3E3D-14BE-4951-990B-76835166281C'}, 
'258': {'uri': 'https://opencontext.org/subjects/381CAEAA-235F-469D-160E-A03BB9B334F7'}, 
'259': {'uri': 'https://opencontext.org/subjects/18DD4EDD-CF3F-4829-A003-87AFA4ED6742'}, 
'26': {'uri': 'https://opencontext.org/subjects/3F1E1F75-3A5E-4105-1DD2-94C776DE493F'}, 
'260': {'uri': 'https://opencontext.org/subjects/97B3FB48-CF5E-4D97-6FC7-E6213BAE2CE7'}, 
'261': {'uri': 'https://opencontext.org/subjects/02E6EEFA-F1CE-4584-752D-44175C50626C'}, 
'262': {'uri': 'https://opencontext.org/subjects/9B6EB7FC-0506-4F28-22A5-D8C725E7C8A7'}, 
'263': {'uri': 'https://opencontext.org/subjects/4DAF1629-9562-4894-53BE-76AAA63E2BB3'}, 
'264': {'uri': 'https://opencontext.org/subjects/038DC277-D83A-492B-F5CE-AE13DCE3D50B'}, 
'265': {'uri': 'https://opencontext.org/subjects/403CDCF6-C5CF-4FC2-C66C-075F99EA91AD'}, 
'266': {'uri': 'https://opencontext.org/subjects/85BCD16C-705B-4CC5-C88A-52C280711A7B'}, 
'267': {'uri': 'https://opencontext.org/subjects/E651CBEF-B83D-4ED4-21FD-A8A9AE2C18BD'}, 
'268': {'uri': 'https://opencontext.org/subjects/8FD93D1C-264C-40B6-9A72-1F3EAB44C8B6'}, 
'269': {'uri': 'https://opencontext.org/subjects/2A1A12F4-F920-4A59-35C5-70D8D7FEC492'}, 
'27': {'uri': 'https://opencontext.org/subjects/644BB446-6A25-46E8-64C9-E8735E227E72'}, 
'270': {'uri': 'https://opencontext.org/subjects/9673D2A7-4426-412B-CDCB-1D74FAC4BD20'}, 
'271': {'uri': 'https://opencontext.org/subjects/3CD9CA1D-069B-4A65-3DFD-3D170AE8023C'}, 
'272': {'uri': 'https://opencontext.org/subjects/BE44A1B2-774B-4BB0-AFDF-4617996CFF76'}, 
'273': {'uri': 'https://opencontext.org/subjects/05CAB086-0E36-478C-F72C-22A15ABCFB19'}, 
'274': {'uri': 'https://opencontext.org/subjects/321D5BD9-70EE-4095-FD3E-C80B00CDEC78'}, 
'275': {'uri': 'https://opencontext.org/subjects/66213B47-0DE6-450B-10DF-D9143C5C8BC2'}, 
'276': {'uri': 'https://opencontext.org/subjects/034AA229-42A6-4B45-287E-E5C409981CF9'}, 
'277': {'uri': 'https://opencontext.org/subjects/83304A03-52E2-411F-4E36-DBEAC7A441D1'}, 
'278': {'uri': 'https://opencontext.org/subjects/F1360278-6001-43DF-F344-B11A536AF061'}, 
'279': {'uri': 'https://opencontext.org/subjects/E947308A-5F9A-41DD-E98A-D63BEA1CE1D9'}, 
'28': {'uri': 'https://opencontext.org/subjects/3F761187-D0A8-40CD-358E-2F7DB01DBA47'}, 
'280': {'uri': 'https://opencontext.org/subjects/EEB08529-F0BE-4311-53E7-1A4C8BCC200D'}, 
'281': {'uri': 'https://opencontext.org/subjects/938BCA2C-161D-4DC5-130B-C54C98EC8F82'}, 
'282': {'uri': 'https://opencontext.org/subjects/AFCE6C74-53DE-46B2-EF24-F4E1C5DAE3D6'}, 
'283': {'uri': 'https://opencontext.org/subjects/769885E1-C279-470D-5F7C-18AE42CB00AC'}, 
'284': {'uri': 'https://opencontext.org/subjects/C03933DF-64F7-4C78-75A3-980B41CB53D8'}, 
'285': {'uri': 'https://opencontext.org/subjects/7A31B205-C6D1-4D24-EBA4-D93D5732E28A'}, 
'286': {'uri': 'https://opencontext.org/subjects/10BFDD6B-7BD6-4714-F81F-2D7E52D243D6'}, 
'287': {'uri': 'https://opencontext.org/subjects/2042B811-D07C-4665-2CAB-6C9673E54127'}, 
'288': {'uri': 'https://opencontext.org/subjects/BA3576D9-DF16-4AE9-532A-841CCF20DF84'}, 
'289': {'uri': 'https://opencontext.org/subjects/00FABCF8-A821-4934-9A17-0C23DC2106B4'}, 
'29': {'uri': 'https://opencontext.org/subjects/03C05DB2-62DF-43B2-605B-56AEFA277051'}, 
'290': {'uri': 'https://opencontext.org/subjects/1107E1D5-DFAD-4D63-3DD2-1096AE61587D'}, 
'291': {'uri': 'https://opencontext.org/subjects/B19C4F26-ED8C-46BF-0A9A-2565484C9ED6'}, 
'292': {'uri': 'https://opencontext.org/subjects/8C7F1700-D3B1-408F-0BB7-D10B775F2B2E'}, 
'293': {'uri': 'https://opencontext.org/subjects/E84623B7-E3D6-4BC1-C5F7-4AD36E4D6E81'}, 
'294': {'uri': 'https://opencontext.org/subjects/F8D0AFB5-CC02-4756-E6A9-474692BE78C3'}, 
'295': {'uri': 'https://opencontext.org/subjects/F2E38A8D-1156-43CC-8EFC-875820D95FD4'}, 
'296': {'uri': 'https://opencontext.org/subjects/4D825459-8568-47A5-9A85-8510957AABB8'}, 
'297': {'uri': 'https://opencontext.org/subjects/9020295D-29DE-4709-1657-F077C4C2057E'}, 
'298': {'uri': 'https://opencontext.org/subjects/0D9788F5-D6FB-425C-D87E-252D6A1D2F55'}, 
'299': {'uri': 'https://opencontext.org/subjects/8FEC1F08-B91F-4F02-3065-42C80DFA828C'}, 
'3': {'uri': 'https://opencontext.org/subjects/BBDC297E-7AC1-4925-E775-6D1B75CC280C'}, 
'30': {'uri': 'https://opencontext.org/subjects/E2E20765-3196-4443-E62C-8C7799708399'}, 
'300': {'uri': 'https://opencontext.org/subjects/59109ADC-4DDB-4223-0BA1-E0C5593A20F7'}, 
'301': {'uri': 'https://opencontext.org/subjects/FD2FA15C-22AC-4585-360F-8FF50C98791F'}, 
'302': {'uri': 'https://opencontext.org/subjects/865868E6-B3F9-43D4-1EAF-B2FA1008C3A7'}, 
'303': {'uri': 'https://opencontext.org/subjects/FE6761C0-9514-48E9-CEAB-D8D7CD0A44F8'}, 
'304': {'uri': 'https://opencontext.org/subjects/4595251B-B67A-4132-443B-0000E2044C85'}, 
'305': {'uri': 'https://opencontext.org/subjects/FF55F04E-E14E-4230-7155-6DBCDAAFAB19'}, 
'306': {'uri': 'https://opencontext.org/subjects/21EE7A84-703B-49DA-60FB-D7FAFA83FD6E'}, 
'307': {'uri': 'https://opencontext.org/subjects/1F380C32-EDA5-4F74-59CF-05BC44055468'}, 
'308': {'uri': 'https://opencontext.org/subjects/A03E5EA3-CC6F-4BAE-3FA0-D7E8931ADCF5'}, 
'309': {'uri': 'https://opencontext.org/subjects/1E07D087-DE44-4B52-0C69-21481B1E6816'}, 
'31': {'uri': 'https://opencontext.org/subjects/5B5550EC-78D2-4766-2E71-D54E3A4AAC6A'}, 
'310': {'uri': 'https://opencontext.org/subjects/F17D401C-A890-49B3-972F-C516DA9DFC8D'}, 
'311': {'uri': 'https://opencontext.org/subjects/E5E80BD3-81E5-4215-29E8-602D59A2B8D8'}, 
'312': {'uri': 'https://opencontext.org/subjects/6F340337-95B3-48E1-D09B-D5D7FF9700E0'}, 
'313': {'uri': 'https://opencontext.org/subjects/24878B9F-E641-49A6-E7BE-F536303A96BD'}, 
'314': {'uri': 'https://opencontext.org/subjects/BAC52ED6-040A-4E6B-95CF-3FE40592A951'}, 
'315': {'uri': 'https://opencontext.org/subjects/E72D3E97-C3FD-4C21-8B4D-6F153221E59F'}, 
'316': {'uri': 'https://opencontext.org/subjects/9879A755-C08A-498B-3DA2-283E5D8A4346'}, 
'317': {'uri': 'https://opencontext.org/subjects/FDD41CEF-BCE8-4EF1-53AA-A702F71D081E'}, 
'318': {'uri': 'https://opencontext.org/subjects/8B1452F5-ABF0-4F10-9196-9964B1E10C8F'}, 
'319': {'uri': 'https://opencontext.org/subjects/13781DFA-0D2C-41FC-8D12-EF779F960074'}, 
'32': {'uri': 'https://opencontext.org/subjects/7A2631C5-ABBD-46F6-6A6B-0C23EA819370'}, 
'320': {'uri': 'https://opencontext.org/subjects/BA4DD0AC-D9FC-43AE-B343-7A100244FCE0'}, 
'321': {'uri': 'https://opencontext.org/subjects/BA4DD0AC-D9FC-43AE-B343-7A100244FCE0'}, 
'322': {'uri': 'https://opencontext.org/subjects/BA4DD0AC-D9FC-43AE-B343-7A100244FCE0'}, 
'323': {'uri': 'https://opencontext.org/subjects/C1EFFCC9-3FBD-46C0-2160-38A6273DFDEB'}, 
'324': {'uri': 'https://opencontext.org/subjects/D1385646-A2B3-4A24-35A8-E7FE4D2B9E8E'}, 
'325': {'uri': 'https://opencontext.org/subjects/C1769D8F-A55C-4E1A-4398-8CDC1524A589'}, 
'326': {'uri': 'https://opencontext.org/subjects/F1C8EDE7-B1AB-41FE-998F-820C5F85074C'}, 
'327': {'uri': 'https://opencontext.org/subjects/DDF93AE8-2CB7-4FC8-0D49-A204D6D19451'}, 
'328': {'uri': 'https://opencontext.org/subjects/C4E13506-CCFB-4538-8307-412EAB609CAB'}, 
'329': {'uri': 'https://opencontext.org/subjects/AC23FDFA-A661-4EAF-5B68-64409F2DEE3C'}, 
'33': {'uri': 'https://opencontext.org/subjects/3A6C5062-5C6A-4886-87CD-DD15B4636809'}, 
'330': {'uri': 'https://opencontext.org/subjects/1715F935-44F4-46B0-458A-CA73117B66F7'}, 
'331': {'uri': 'https://opencontext.org/subjects/3B1B5BDC-9CEA-4F21-46CF-A1698373CEDE'}, 
'332': {'uri': 'https://opencontext.org/subjects/C6841408-C4D0-4F1F-B163-0F093BD2EC6F'}, 
'333': {'uri': 'https://opencontext.org/subjects/44D03EAE-759A-4C90-0B20-CAB6BC8E010F'}, 
'334': {'uri': 'https://opencontext.org/subjects/44D03EAE-759A-4C90-0B20-CAB6BC8E010F'}, 
'335': {'uri': 'https://opencontext.org/subjects/88085F60-2240-4894-166D-11233971C5CA'}, 
'336': {'uri': 'https://opencontext.org/subjects/88085F60-2240-4894-166D-11233971C5CA'}, 
'337': {'uri': 'https://opencontext.org/subjects/9F5548EF-C05A-471A-2531-99D056C0392E'}, 
'338': {'uri': 'https://opencontext.org/subjects/9F5548EF-C05A-471A-2531-99D056C0392E'}, 
'339': {'uri': 'https://opencontext.org/subjects/8C6D0960-E44D-4C77-EB65-B1BF15B23C1C'}, 
'34': {'uri': 'https://opencontext.org/subjects/E7750CB4-79E0-423C-6F71-4B991EB487DD'}, 
'340': {'uri': 'https://opencontext.org/subjects/CF45634D-C744-4FBE-CB30-DE94362392F5'}, 
'341': {'uri': 'https://opencontext.org/subjects/BB5078E0-E3D7-4876-7115-AB3C1730E483'}, 
'342': {'uri': 'https://opencontext.org/subjects/B79DEFA4-EB3A-4E9D-DB25-711792610C21'}, 
'343': {'uri': 'https://opencontext.org/subjects/1F515D40-4915-4B7C-A644-07ADDD89ACD4'}, 
'344': {'uri': 'https://opencontext.org/subjects/9F5D7919-2266-4617-40B9-45CAFA9B178E'}, 
'345': {'uri': 'https://opencontext.org/subjects/82001ECC-766E-4B9F-2FB0-AF5F30722583'}, 
'346': {'uri': 'https://opencontext.org/subjects/368588E0-9A4F-4E00-2CF8-C4DA561557BF'}, 
'347': {'uri': 'https://opencontext.org/subjects/7C536C68-D9B1-4B34-01E9-B8187E757580'}, 
'348': {'uri': 'https://opencontext.org/subjects/B07D574D-336E-4FC5-B9BE-59136145193D'}, 
'349': {'uri': 'https://opencontext.org/subjects/7DD8061F-FCC1-4E69-C8D6-50FCB1CBF2A0'}, 
'35': {'uri': 'https://opencontext.org/subjects/DA41F536-AD71-413E-048C-C572046069B4'}, 
'350': {'uri': 'https://opencontext.org/subjects/A9F9AD0A-3A54-49D5-21B1-2CB331F82966'}, 
'351': {'uri': 'https://opencontext.org/subjects/BF12F33F-C18C-4F84-0470-B64F86679044'}, 
'352': {'uri': 'https://opencontext.org/subjects/BF12F33F-C18C-4F84-0470-B64F86679044'}, 
'353': {'uri': 'https://opencontext.org/subjects/51EE0E7F-DC67-4911-2E53-57AF8F5068B9'}, 
'354': {'uri': 'https://opencontext.org/subjects/49F45331-EB08-4E19-FA31-4C9AC639C388'}, 
'355': {'uri': 'https://opencontext.org/subjects/8DC1810D-17C9-4064-D1AC-526CE4FB1B69'}, 
'356': {'uri': 'https://opencontext.org/subjects/51811248-1469-45CE-EA1C-33B61A244055'}, 
'357': {'uri': 'https://opencontext.org/subjects/E9425F5E-9AEC-43F0-E0A9-2D64F97F5D2A'}, 
'358': {'uri': 'https://opencontext.org/subjects/122F81BF-29C7-4B62-0E43-E68059D21B8C'}, 
'359': {'uri': 'https://opencontext.org/subjects/171AA8D2-BC5F-4D17-F3B0-5A49DD4E3DB2'}, 
'36': {'uri': 'https://opencontext.org/subjects/0D1E2474-6E46-4348-AD85-800AB9F3D80D'}, 
'360': {'uri': 'https://opencontext.org/subjects/83E9F7D3-4B39-4734-476B-F64E3AB4D584'}, 
'361': {'uri': 'https://opencontext.org/subjects/ED527E93-E63F-4FA6-A9A1-407F9EC2F3C1'}, 
'362': {'uri': 'https://opencontext.org/subjects/68F088F1-A2C1-4072-A9AB-EE6001F30CF8'}, 
'363': {'uri': 'https://opencontext.org/subjects/388BB97A-C9B0-4EBB-FA5D-2A7B57460547'}, 
'364': {'uri': 'https://opencontext.org/subjects/905B4EA0-91A8-4B10-0020-7841C86953B0'}, 
'365': {'uri': 'https://opencontext.org/subjects/4B93CE0F-AD3C-45E2-A260-C52F71792F3A'}, 
'366': {'uri': 'https://opencontext.org/subjects/CA2126B2-51B5-43A6-FBE2-CEAF068934A7'}, 
'367': {'uri': 'https://opencontext.org/subjects/3AFAAAB3-24C6-4F5D-D993-DA4006935924'}, 
'368': {'uri': 'https://opencontext.org/subjects/BA2D283E-9EC4-47AE-4B5E-3C933662B0FF'}, 
'369': {'uri': 'https://opencontext.org/subjects/B1AAE78E-ACD4-4B1F-CA46-EF64F7310195'}, 
'37': {'uri': 'https://opencontext.org/subjects/10AEE2E8-FFB6-4CD7-A7E4-8434BD2A7287'}, 
'370': {'uri': 'https://opencontext.org/subjects/6E9A747F-A5CA-40B6-2E21-61EB5CF4E6CA'}, 
'371': {'uri': 'https://opencontext.org/subjects/f9d2cc31-9892-49d5-a0f8-4e6fb084833e'}, 
'372': {'uri': 'https://opencontext.org/subjects/00E9665A-780D-4390-CFBF-B48A970759CB'}, 
'373': {'uri': 'https://opencontext.org/subjects/2196C174-D15B-428D-BB25-B375B2CE1AA6'}, 
'374': {'uri': 'https://opencontext.org/subjects/0C5F1A52-D6F4-456B-6041-4604F7C54855'}, 
'375': {'uri': 'https://opencontext.org/subjects/cd3e05e0-cd2d-42f4-936b-4399af5c66d2'}, 
'376': {'uri': 'https://opencontext.org/subjects/525E6271-B403-495D-0956-A316F186DC65'}, 
'377': {'uri': 'https://opencontext.org/subjects/ecba8803-74d2-40ac-a63a-54ee3dce5d2c'}, 
'378': {'uri': 'https://opencontext.org/subjects/cf217633-6fba-4002-8dec-472a8416f1dd'}, 
'379': {'uri': 'https://opencontext.org/subjects/45C6D049-10DD-4FFF-78F4-08D6D32642FC'}, 
'38': {'uri': 'https://opencontext.org/subjects/282A6231-1FDA-4DD2-9E9B-BA5F25BC7E37'}, 
'380': {'uri': 'https://opencontext.org/subjects/0C5F1A52-D6F4-456B-6041-4604F7C54855'}, 
'381': {'uri': 'https://opencontext.org/subjects/254dc26d-0431-4e75-8c50-ab6016c0df7e'}, 
'382': {'uri': 'https://opencontext.org/subjects/78ca532e-d943-482a-bb88-3fc43862bdda'}, 
'383': {'uri': 'https://opencontext.org/subjects/5071035d-3771-48d5-89fd-f59c01f96e74'}, 
'384': {'uri': 'https://opencontext.org/subjects/5AD193FF-803A-4D25-273B-F874B29AF6EC'}, 
'385': {'uri': 'https://opencontext.org/subjects/1a6306d7-a0f3-4b45-9667-6854f9e21100'}, 
'386': {'uri': 'https://opencontext.org/subjects/23e7aafa-37d8-4e72-b92e-5e94fedfd207'}, 
'387': {'uri': 'https://opencontext.org/subjects/2f2d6d6e-a85e-4876-af9d-01e83668f5e9'}, 
'388': {'uri': 'https://opencontext.org/subjects/80c59cb5-d6ca-4b88-8e93-cab9c1e3798f'}, 
'389': {'uri': 'https://opencontext.org/subjects/4ba347eb-5401-407a-a65b-7206754259ad'}, 
'39': {'uri': 'https://opencontext.org/subjects/ECCC7A10-11C7-43DA-74E6-726210980A54'}, 
'390': {'uri': 'https://opencontext.org/subjects/4acaaff3-cab7-4391-940b-6f6cb9946186'}, 
'391': {'uri': 'https://opencontext.org/subjects/e7100971-7904-4848-9215-47d12309f089'}, 
'392': {'uri': 'https://opencontext.org/subjects/eccf1e45-88e2-4072-98a5-d04eaa7c3b70'}, 
'393': {'uri': 'https://opencontext.org/subjects/2189b8ab-a4a5-490a-83dd-3b9c2e2385d2'}, 
'394': {'uri': 'https://opencontext.org/subjects/254dc26d-0431-4e75-8c50-ab6016c0df7e'}, 
'395': {'uri': 'https://opencontext.org/subjects/2ab489e7-014b-4437-aeca-c243e019695a'}, 
'396': {'uri': 'https://opencontext.org/subjects/cc79062b-1b2c-417b-9295-299e89d26c97'}, 
'397': {'uri': 'https://opencontext.org/subjects/5071035d-3771-48d5-89fd-f59c01f96e74'}, 
'398': {'uri': 'https://opencontext.org/subjects/17924BE4-6A53-47C1-0E6A-D9C8F840F2D9'}, 
'399': {'uri': 'https://opencontext.org/subjects/61bd5ada-45dd-4cf3-b620-8ba839f85753'}, 
'4': {'uri': 'https://opencontext.org/subjects/D5464A7B-A7B0-4D11-368C-ECF47D1B9389'}, 
'40': {'uri': 'https://opencontext.org/subjects/736422CB-0786-43EC-C243-85E7CB2C7315'}, 
'400': {'uri': 'https://opencontext.org/subjects/61bd5ada-45dd-4cf3-b620-8ba839f85753'}, 
'401': {'uri': 'https://opencontext.org/subjects/61bd5ada-45dd-4cf3-b620-8ba839f85753'}, 
'402': {'uri': 'https://opencontext.org/subjects/9420190e-3d76-44cf-ae0f-279900c4a56c'}, 
'403': {'uri': 'https://opencontext.org/subjects/70a10d8f-5bec-46ab-aa02-6453e66e167e'}, 
'404': {'uri': 'https://opencontext.org/subjects/9420190e-3d76-44cf-ae0f-279900c4a56c'}, 
'405': {'uri': 'https://opencontext.org/subjects/f675c9ad-e4b3-4125-937e-21d64ed8fd30'}, 
'406': {'uri': 'https://opencontext.org/subjects/f675c9ad-e4b3-4125-937e-21d64ed8fd30'}, 
'407': {'uri': 'https://opencontext.org/subjects/bfc2ff8b-1d8a-49ba-bb5e-e64ae799a642'}, 
'408': {'uri': 'https://opencontext.org/subjects/bfc2ff8b-1d8a-49ba-bb5e-e64ae799a642'}, 
'409': {'uri': 'https://opencontext.org/subjects/bfc2ff8b-1d8a-49ba-bb5e-e64ae799a642'}, 
'41': {'uri': 'https://opencontext.org/subjects/67B642B7-C0AC-4ED7-FD60-4DC7E54861C5'}, 
'410': {'uri': 'https://opencontext.org/subjects/1f5549bf-2d1e-4eab-aa1c-a23e76cff1d4'}, 
'411': {'uri': 'https://opencontext.org/subjects/1f5549bf-2d1e-4eab-aa1c-a23e76cff1d4'}, 
'412': {'uri': 'https://opencontext.org/subjects/753ff890-7e5c-4854-93e8-0c1d40e1683a'}, 
'413': {'uri': 'https://opencontext.org/subjects/311c66b1-75d5-49c1-9593-481228048c07'}, 
'414': {'uri': 'https://opencontext.org/subjects/311c66b1-75d5-49c1-9593-481228048c07'}, 
'415': {'uri': 'https://opencontext.org/subjects/6ffcb588-d41e-4749-86db-351bcfba50c4'}, 
'417': {'uri': 'https://opencontext.org/subjects/7b01d4eb-7821-419e-9df4-d72d06513a6d'}, 
'418': {'uri': 'https://opencontext.org/subjects/7b01d4eb-7821-419e-9df4-d72d06513a6d'}, 
'419': {'uri': 'https://opencontext.org/subjects/503bb312-f0cc-4ecf-9443-66a81f9dc683'}, 
'42': {'uri': 'https://opencontext.org/subjects/03C2F519-5258-4880-C762-42673862AD9E'}, 
'420': {'uri': 'https://opencontext.org/subjects/dc245337-3117-4551-837e-42c02d297a2e'}, 
'421': {'uri': 'https://opencontext.org/subjects/dc245337-3117-4551-837e-42c02d297a2e'}, 
'422': {'uri': 'https://opencontext.org/subjects/dc245337-3117-4551-837e-42c02d297a2e'}, 
'423': {'uri': 'https://opencontext.org/subjects/28a6cc00-fbab-40f1-90e6-01c66376926b'}, 
'424': {'uri': 'https://opencontext.org/subjects/28a6cc00-fbab-40f1-90e6-01c66376926b'}, 
'425': {'uri': 'https://opencontext.org/subjects/284a39ef-3e9f-4dac-8dc9-87b94095f382'}, 
'426': {'uri': 'https://opencontext.org/subjects/284a39ef-3e9f-4dac-8dc9-87b94095f382'}, 
'427': {'uri': 'https://opencontext.org/subjects/284a39ef-3e9f-4dac-8dc9-87b94095f382'}, 
'428': {'uri': 'https://opencontext.org/subjects/d0ec09bd-399d-46f0-8ec9-8f5936044f1c'}, 
'429': {'uri': 'https://opencontext.org/subjects/db6cca7f-78cb-4043-adb4-c3de5d791910'}, 
'43': {'uri': 'https://opencontext.org/subjects/751B3F35-088B-46B2-71E7-A555D058491D'}, 
'430': {'uri': 'https://opencontext.org/subjects/a236e90a-f7b6-44b9-af1b-dc259071ab4f'}, 
'431': {'uri': 'https://opencontext.org/subjects/0a00d502-984f-4449-8bdc-8245093690f8'}, 
'432': {'uri': 'https://opencontext.org/subjects/5ccfc2a2-4139-41fd-9961-fdc03420e0bf'}, 
'433': {'uri': 'https://opencontext.org/subjects/3bd49b02-b954-46ad-8cc6-a0fa4ca48906'}, 
'434': {'uri': 'https://opencontext.org/subjects/3bd49b02-b954-46ad-8cc6-a0fa4ca48906'}, 
'435': {'uri': 'https://opencontext.org/subjects/991fd662-e8c0-4dfd-9b1f-d7233429ca3a'}, 
'436': {'uri': 'https://opencontext.org/subjects/ea552ea2-e2aa-4db3-9372-2377958369c4'}, 
'437': {'uri': 'https://opencontext.org/subjects/c8f7fff7-4681-4a40-a049-0f15e1a3602e'}, 
'438': {'uri': 'https://opencontext.org/subjects/7d0c9b3e-1d2a-4c6a-978a-edfa6e40fd2b'}, 
'439': {'uri': 'https://opencontext.org/subjects/7d0c9b3e-1d2a-4c6a-978a-edfa6e40fd2b'}, 
'44': {'uri': 'https://opencontext.org/subjects/5E429FD0-C205-4EB7-7E05-32D4B588E5E1'}, 
'440': {'uri': 'https://opencontext.org/subjects/b8233443-f716-4cfe-9b52-fe46a81eb610'}, 
'441': {'uri': 'https://opencontext.org/subjects/b8233443-f716-4cfe-9b52-fe46a81eb610'}, 
'442': {'uri': 'https://opencontext.org/subjects/ea552ea2-e2aa-4db3-9372-2377958369c4'}, 
'443': {'uri': 'https://opencontext.org/subjects/991fd662-e8c0-4dfd-9b1f-d7233429ca3a'}, 
'444': {'uri': 'https://opencontext.org/subjects/5ccfc2a2-4139-41fd-9961-fdc03420e0bf'}, 
'445': {'uri': 'https://opencontext.org/subjects/5ccfc2a2-4139-41fd-9961-fdc03420e0bf'}, 
'446': {'uri': 'https://opencontext.org/subjects/9420190e-3d76-44cf-ae0f-279900c4a56c'}, 
'447': {'uri': 'https://opencontext.org/subjects/7a32b56f-a7e0-4f0b-87cb-2126ccdee127'}, 
'448': {'uri': 'https://opencontext.org/subjects/910004b2-e13c-4084-9f66-04960123d1fe'}, 
'449': {'uri': 'https://opencontext.org/subjects/45760b29-e1ac-4a1e-9c11-71d071edea48'}, 
'45': {'uri': 'https://opencontext.org/subjects/85C5376B-08B0-429A-F106-D9386FA457B3'}, 
'450': {'uri': 'https://opencontext.org/subjects/45760b29-e1ac-4a1e-9c11-71d071edea48'}, 
'451': {'uri': 'https://opencontext.org/subjects/672bd5a3-ea71-4555-aa78-a7ce17bf51f8'}, 
'452': {'uri': 'https://opencontext.org/subjects/672bd5a3-ea71-4555-aa78-a7ce17bf51f8'}, 
'453': {'uri': 'https://opencontext.org/subjects/c766cfd8-e1b4-4a66-b6b2-08b2030bdcb8'}, 
'454': {'uri': 'https://opencontext.org/subjects/c766cfd8-e1b4-4a66-b6b2-08b2030bdcb8'}, 
'455': {'uri': 'https://opencontext.org/subjects/70a10d8f-5bec-46ab-aa02-6453e66e167e'}, 
'456': {'uri': 'https://opencontext.org/subjects/2d29ce46-1637-4f2e-9841-264d6eb14f9e'}, 
'457': {'uri': 'https://opencontext.org/subjects/511415d9-622c-4958-9445-44d509dacd04'}, 
'458': {'uri': 'https://opencontext.org/subjects/6f59d5c0-fa4f-4adc-a98b-6dca8ccb8d8e'}, 
'459': {'uri': 'https://opencontext.org/subjects/6ec338a9-36a4-4643-9d16-e01fc33c585f'}, 
'46': {'uri': 'https://opencontext.org/subjects/FEB576A3-12DE-4AE2-495D-87E662F23FF5'}, 
'460': {'uri': 'https://opencontext.org/subjects/f2661425-9eb5-45a2-ae01-d7bc63683db6'}, 
'461': {'uri': 'https://opencontext.org/subjects/1341c275-af80-4e8c-a9f4-1682efe5f022'}, 
'462': {'uri': 'https://opencontext.org/subjects/f7b150a8-7650-4d2b-a9b3-91168537a75d'}, 
'463': {'uri': 'https://opencontext.org/subjects/1b6f73ed-6173-4f3f-938e-a5e5b3402fd4'}, 
'464': {'uri': 'https://opencontext.org/subjects/ed8d8636-fd23-408a-86dc-b72ac2da068a'}, 
'465': {'uri': 'https://opencontext.org/subjects/4b503ad5-d1fd-486b-89d0-2b5c0d37e5ff'}, 
'466': {'uri': 'https://opencontext.org/subjects/03C2F519-5258-4880-C762-42673862AD9E'}, 
'467': {'uri': 'https://opencontext.org/subjects/8605e112-6af4-4b29-a50e-4ce4bb45801b'}, 
'468': {'uri': 'https://opencontext.org/subjects/2d73d4bc-bc05-4242-9896-b8cf3ca96346'}, 
'469': {'uri': 'https://opencontext.org/subjects/3f7dc67b-9640-4e09-8c63-42640b4b23c2'}, 
'47': {'uri': 'https://opencontext.org/subjects/5D60BE1B-57A7-4F37-7CA1-11E57A73FB31'}, 
'470': {'uri': 'https://opencontext.org/subjects/e6b4620a-c575-411a-b136-b4110755ac6d'}, 
'471': {'uri': 'https://opencontext.org/subjects/3689eb5d-e9a2-49e4-9be5-c9676080ec2b'}, 
'472': {'uri': 'https://opencontext.org/subjects/221f94cc-1031-400e-a583-2e9b2bb18104'}, 
'473': {'uri': 'https://opencontext.org/subjects/85b795fd-d5ef-406e-bce7-0a695b656fd6'}, 
'48': {'uri': 'https://opencontext.org/subjects/C0C7B0E4-6135-4A2D-5E6B-1285190F271F'}, 
'49': {'uri': 'https://opencontext.org/subjects/78DC8FFD-D170-4FF7-1D02-EA0C85A4539C'}, 
'5': {'uri': 'https://opencontext.org/subjects/9950174E-E880-4BEF-B797-358A82F4A372'}, 
'50': {'uri': 'https://opencontext.org/subjects/D5FF94F3-1D3C-4107-30D5-697C86409234'}, 
'51': {'uri': 'https://opencontext.org/subjects/D5FF94F3-1D3C-4107-30D5-697C86409234'}, 
'52': {'uri': 'https://opencontext.org/subjects/18DD4EDD-CF3F-4829-A003-87AFA4ED6742'}, 
'53': {'uri': 'https://opencontext.org/subjects/692CF461-0052-4019-BB8A-BB26D84E5F24'}, 
'54': {'uri': 'https://opencontext.org/subjects/3AA9E720-0371-4443-5A40-5FE6A5E1DCAE'}, 
'55': {'uri': 'https://opencontext.org/subjects/F5332A70-73BE-4E87-AD91-08F0ABF7BFB1'}, 
'56': {'uri': 'https://opencontext.org/subjects/3E140B66-8309-4931-FEF4-AD2FDF8D6291'}, 
'57': {'uri': 'https://opencontext.org/subjects/E94E6618-A7FC-4AFF-D004-69EEB3E8089A'}, 
'58': {'uri': 'https://opencontext.org/subjects/58FCC816-FF23-4890-06F6-DB80719BFF31'}, 
'59': {'uri': 'https://opencontext.org/subjects/9D2FD065-FA0F-4DA3-21FE-A2D3CA02E320'}, 
'6': {'uri': 'https://opencontext.org/subjects/CFE33CD1-B119-4D65-E2FF-8DAFABEAC941'}, 
'60': {'uri': 'https://opencontext.org/subjects/E405152C-1036-49AE-0A8B-A621B66EC7AB'}, 
'61': {'uri': 'https://opencontext.org/subjects/98BC67D5-770B-4C37-3950-A33170EB3A4F'}, 
'62': {'uri': 'https://opencontext.org/subjects/7CF7D7EB-D71C-45DC-82EA-921CDE5640B1'}, 
'63': {'uri': 'https://opencontext.org/subjects/8EA5B6D8-EC94-4B56-4D7B-440C67EFAFA3'}, 
'64': {'uri': 'https://opencontext.org/subjects/8EA5B6D8-EC94-4B56-4D7B-440C67EFAFA3'}, 
'65': {'uri': 'https://opencontext.org/subjects/8EA5B6D8-EC94-4B56-4D7B-440C67EFAFA3'}, 
'66': {'uri': 'https://opencontext.org/subjects/8EA5B6D8-EC94-4B56-4D7B-440C67EFAFA3'}, 
'67': {'uri': 'https://opencontext.org/subjects/8EA5B6D8-EC94-4B56-4D7B-440C67EFAFA3'}, 
'68': {'uri': 'https://opencontext.org/subjects/8EA5B6D8-EC94-4B56-4D7B-440C67EFAFA3'}, 
'69': {'uri': 'https://opencontext.org/subjects/9B688358-00F8-4091-E5D2-B2E0AB25ADBC'}, 
'7': {'uri': 'https://opencontext.org/subjects/CCAA1707-E736-4CC6-D2F7-F6DE62998FD4'}, 
'70': {'uri': 'https://opencontext.org/subjects/F6B4B592-664A-47A0-A5B8-F77EF4A48149'}, 
'71': {'uri': 'https://opencontext.org/subjects/4B85886B-03E4-48FE-41AB-D55457C5E3A9'}, 
'72': {'uri': 'https://opencontext.org/subjects/4B85886B-03E4-48FE-41AB-D55457C5E3A9'}, 
'73': {'uri': 'https://opencontext.org/subjects/4B85886B-03E4-48FE-41AB-D55457C5E3A9'}, 
'74': {'uri': 'https://opencontext.org/subjects/8F23631E-6201-4092-E5BE-5E7D536E2B35'}, 
'75': {'uri': 'https://opencontext.org/subjects/234F8218-4D67-4887-659E-D14785BC0A20'}, 
'76': {'uri': 'https://opencontext.org/subjects/1CD4609F-F5E5-4C2C-3DF7-CDCB87CB019E'}, 
'77': {'uri': 'https://opencontext.org/subjects/D1359970-4965-4819-DC03-61A7A7E4A850'}, 
'78': {'uri': 'https://opencontext.org/subjects/2680D449-6312-48AE-EF0F-DB25B67F7BFC'}, 
'79': {'uri': 'https://opencontext.org/subjects/C7E131A3-8BE2-40E3-0EF2-C3AB65823B63'}, 
'8': {'uri': 'https://opencontext.org/subjects/7940B16C-1C48-457D-937B-98EBB5CF4980'}, 
'80': {'uri': 'https://opencontext.org/subjects/7655E594-69C9-4438-1BED-5987F671D933'}, 
'81': {'uri': 'https://opencontext.org/subjects/6A9CF999-C6FA-42AA-8F2B-B07442FE2D44'}, 
'82': {'uri': 'https://opencontext.org/subjects/337FE71E-94CD-4FB5-872F-B1678343B812'}, 
'83': {'uri': 'https://opencontext.org/subjects/AB14B22E-C5AC-42E1-2BD3-0D7362D6DC59'}, 
'84': {'uri': 'https://opencontext.org/subjects/04734348-D45B-4957-BA5A-4BB8D9690140'}, 
'85': {'uri': 'https://opencontext.org/subjects/99F94829-B4F3-44CE-8A9B-A8236BECFBB4'}, 
'86': {'uri': 'https://opencontext.org/subjects/34A37E52-6950-4AE8-FCA8-3DE56973B33E'}, 
'87': {'uri': 'https://opencontext.org/subjects/8188FFAA-CFAD-47D6-2A12-23E4FF5DDBFB'}, 
'88': {'uri': 'https://opencontext.org/subjects/A66D8905-2236-4D2A-3151-F0C49F59B660'}, 
'89': {'uri': 'https://opencontext.org/subjects/150BD521-2E06-48C2-DB8A-B4F53AC3D321'}, 
'9': {'uri': 'https://opencontext.org/subjects/C26457DA-4B00-484E-F27E-85F2A2E88314'}, 
'90': {'uri': 'https://opencontext.org/subjects/8E1306DF-0CF7-409F-403A-A7B74C3B6BDE'}, 
'91': {'uri': 'https://opencontext.org/subjects/7BB80569-AEBF-4C8A-6F9F-581BAF999DE0'}, 
'92': {'uri': 'https://opencontext.org/subjects/7FC5291E-A036-4100-981B-3EE7DECCE097'}, 
'93': {'uri': 'https://opencontext.org/subjects/2D8BB7CF-18F6-464B-213A-ADA01818C70D'}, 
'94': {'uri': 'https://opencontext.org/subjects/E7C6B89A-0258-4A50-1487-C55AE8C4ED69'}, 
'95': {'uri': 'https://opencontext.org/subjects/B229A46D-ED3D-41A0-D64F-2E5855703E0B'}, 
'96': {'uri': 'https://opencontext.org/subjects/A35A67AA-2832-415E-F7BE-3B051444E665'}, 
'97': {'uri': 'https://opencontext.org/subjects/9D0D7D58-A751-4CC7-EF3D-5318D9D16E47'}, 
'98': {'uri': 'https://opencontext.org/subjects/20BEF152-BA8B-4A08-57D7-BAADD30A7248'}, 
'99': {'uri': 'https://opencontext.org/subjects/00F368CE-AFF2-43CA-489A-84A0EC2DFF8C'},     
}
id_prop = 'PolygonID'
gimp.save_partial_clean_file(pc_json_obj,
    'pc-geo', 'pc_trenches_2017_4326.geojson',
    id_prop, ok_ids=False, add_props=pc_props, combine_json_obj=None)

gimp.load_into_importer = False
gimp.process_features_in_file('pc-geo', 'labeled-pc-trenches-2017-4326.geojson')


from opencontext_py.apps.ocitems.geospace.models import Geospace
uuid = '59CA9A4E-3D63-4596-0F53-383F286E59FF'
g = Geospace.objects.get(uuid=uuid)
g.latitude = 43.1524182334655
g.longitude = 11.401899321827992
g.coordinates = '[11.401899321827992,43.1524182334655]'
g.save()




from opencontext_py.apps.imports.geojson.geojson import GeoJSONimport
gimp = GeoJSONimport()
gimp.load_into_importer = False
gimp.project_uuid = 'DF043419-F23B-41DA-7E4D-EE52AF22F92F'
gimp.process_features_in_file('pc-geo', 'pc_artifacts_2017_4326.geojson')

from opencontext_py.apps.imports.geojson.geojson import GeoJSONimport
gimp = GeoJSONimport()
gimp.load_into_importer = False
gimp.project_uuid = 'DF043419-F23B-41DA-7E4D-EE52AF22F92F'
gimp.process_features_in_file('pc-geo', 'vesco_artifacts_2017_4326.geojson')





from opencontext_py.apps.imports.geojson.geojson import GeoJSONimport
gimp = GeoJSONimport()
gimp.load_into_importer = False
gimp.project_uuid = 'DF043419-F23B-41DA-7E4D-EE52AF22F92F'
gimp.source_id = 'pc_trenches_2017_4326'
id_prop = 'PolygonID'
ok_ids = False
json_obj = gimp.load_json_file('pc-geo', 'pc_trenches_2017_4326.geojson')
points = gimp.load_json_file('pc-geo', 'pc_artifacts_2017_4326.geojson')
gimp.save_partial_clean_file(json_obj,
    'pc-geo', 'pc_trenches_2017_4326.geojson',
    id_prop, ok_ids, add_props, points)
json_obj = gimp.load_json_file('pc-geo', 'id-clean-coord-pc_trenches_2017_4326.geojson')
gimp.save_no_coord_file(json_obj, 'pc-geo', 'id-clean-coord-pc_trenches_2017_4326.geojson')


from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.imports.geojson.geojson import GeoJSONimport
from opencontext_py.apps.ocitems.geospace.models import Geospace
print('Delete old botany-areas geospatial data')
Geospace.objects\
        .filter(source_id='botany-areas',
                project_uuid='10aa84ad-c5de-4e79-89ce-d83b75ed72b5',
                ftype__in=['Polygon', 'Multipolygon']).delete()
gimp = GeoJSONimport()
gimp.load_into_importer = False
gimp.project_uuid = '10aa84ad-c5de-4e79-89ce-d83b75ed72b5'
gimp.source_id = 'botany-areas'
id_prop = 'LocalArea'
ok_ids = False
projects=['10aa84ad-c5de-4e79-89ce-d83b75ed72b5', '5A6DDB94-70BE-43B4-2D5D-35D983B21515']
json_obj = gimp.load_json_file('giza-areas', 'botany-areas-revised.geojson')
rev_json = LastUpdatedOrderedDict()
rev_json['features'] = []
for feat in json_obj['features']:
    area_name = feat['properties']['LocalArea']
    if area_name == 'KKT-Nohas House':
        area_name = "Noha's"
    elif area_name == 'G1':
        area_name = 'GI'
    man_objs = Manifest.objects.filter(label=area_name, project_uuid__in=projects, class_uri='oc-gen:cat-area')[:1]
    if len(man_objs):
        feat['properties']['uri'] = 'http://opencontext.org/subjects/' + man_objs[0].uuid
        rev_json['features'].append(feat)
    else:
        print('Cannot find: ' + area_name)
        

gimp.save_json_file(rev_json, 'giza-areas', 'botany-areas-revised-w-uris.geojson')
gimp.process_features_in_file('giza-areas', 'botany-areas-revised-w-uris.geojson')
gimp.save_no_coord_file(rev_json, 'giza-areas', 'id-clean-coord-botany-areas-revised-w-uris.geojson')




import json
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.apps.ocitems.geospace.models import Geospace, GeospaceGeneration
from opencontext_py.apps.imports.geojson.geojson import GeoJSONimport
from opencontext_py.libs.validategeojson import ValidateGeoJson
from opencontext_py.libs.globalmaptiles import GlobalMercator
from opencontext_py.libs.reprojection import ReprojectUtilities
import pyproj
from pyproj import Proj, transform
import numpy
import geojson

# TRAP Bulgaria
project_uuid = '24e2aa20-59e6-4d66-948b-50ee245a7cfc'
gimp = GeoJSONimport()
gimp.load_into_importer = False
gimp.project_uuid = project_uuid
json_obj = gimp.load_json_file('trap-geo', 'yam-survey-units.geojson')
new_geojson = LastUpdatedOrderedDict()
for key, vals in json_obj.items():
    if key != 'features':
        new_geojson[key] = vals
    else:
        new_geojson[key] = []
        

features = []
bad_features = []
reproj = ReprojectUtilities()
reproj.set_in_out_crs('EPSG:32635', 'EPSG:4326')
for feature in json_obj['features']:
    id = str(feature['properties']['SUID'])
    label = 'Survey Unit ' + id
    print('Find: {}'.format(label))
    try:
        m_obj = Manifest.objects.get(project_uuid=project_uuid, label=label, item_type='subjects')
        uuid = m_obj.uuid
    except:
        uuid = ''
    print('--> {}'.format(uuid))
    feature['properties']['uuid'] = uuid
    if not isinstance(feature['geometry'], dict):
        print(' ---- BAD FEATURE: {}'.format(label))
        bad_features.append(feature)
        continue
    geometry_type = feature['geometry']['type']
    coordinates = feature['geometry']['coordinates']
    new_coordinates = reproj.reproject_multi_or_polygon(coordinates, geometry_type)
    feature['geometry']['coordinates'] = new_coordinates
    coord_str = json.dumps(new_coordinates,
                           indent=4,
                           ensure_ascii=False)
    gg = GeospaceGeneration()
    lon_lat = gg.get_centroid_lonlat_coordinates(coord_str,
                                                 feature['geometry']['type'])
    longitude = float(lon_lat[0])
    latitude = float(lon_lat[1])
    feature['properties']['longitude'] = longitude
    feature['properties']['latitude'] = latitude
    gm = GlobalMercator()
    feature['properties']['geo-tile'] = gm.lat_lon_to_quadtree(latitude, longitude, 20)
    features.append(feature)


new_geojson['features'] = features
new_geojson['bad-features'] = bad_features
gimp.save_json_file(new_geojson, 'trap-geo', 'yam-survey-units-reproj-w-uuids.geojson')











from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.apps.ocitems.assertions.models import Assertion
from opencontext_py.apps.ocitems.manifest.models import Manifest
media_uuid = '6d42ad2a-cbc2-46e2-a72c-907607b6fe3c'
project_uuid = '10aa84ad-c5de-4e79-89ce-d83b75ed72b5'

Assertion.objects\
         .filter(uuid=project_uuid,
                 predicate_uuid=Assertion.PREDICATES_GEO_OVERLAY)\
         .delete()


media_man = Manifest.objects.get(uuid=media_uuid)
if not isinstance(media_man.sup_json, dict):
    meta = LastUpdatedOrderedDict()
else:
    meta = media_man.sup_json

meta['Leaflet'] = LastUpdatedOrderedDict()
meta['Leaflet']['bounds'] = [[31.138088,	29.972094], [31.135083, 29.973761]]
meta['Leaflet']['bounds'] = [[29.972094,	31.138088], [29.973761, 31.135083]]
meta['Leaflet']['label'] = 'Menkaure Valley Temple East Plan'
media_man.sup_json = meta
media_man.save()

Assertion.objects\
         .filter(uuid=project_uuid,
                 predicate_uuid=Assertion.PREDICATES_GEO_OVERLAY)\
         .delete()

ass = Assertion()
ass.uuid = '5A6DDB94-70BE-43B4-2D5D-35D983B21515'
ass.subject_type = 'projects'
ass.project_uuid = '5A6DDB94-70BE-43B4-2D5D-35D983B21515'
ass.source_id = 'test-geo-overlay'
ass.obs_node = '#obs-' + str(1)
ass.obs_num =  1
ass.sort = 1
ass.visibility = 1
ass.predicate_uuid = Assertion.PREDICATES_GEO_OVERLAY
ass.object_uuid = media_man.uuid
ass.object_type = media_man.item_type
ass.save()
ass = Assertion()
ass.uuid = project_uuid
ass.subject_type = 'projects'
ass.project_uuid = project_uuid
ass.source_id = 'test-geo-overlay'
ass.obs_node = '#obs-' + str(1)
ass.obs_num =  1
ass.sort = 1
ass.visibility = 1
ass.predicate_uuid = Assertion.PREDICATES_GEO_OVERLAY
ass.object_uuid = 'da676164-9829-4798-bb5d-c5b1135daa27'
ass.object_type = 'media'
ass.save()






















from opencontext_py.apps.imports.geojson.geojson import GeoJSONimport
gimp = GeoJSONimport()
gimp.load_into_importer = False
gimp.project_uuid = 'DF043419-F23B-41DA-7E4D-EE52AF22F92F'
gimp.source_id = 'pc_trenches_2017_4326'
gimp.process_features_in_file('pc-geo', 'pc_trenches_2017_4326.geojson')








from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.archive.binaries import ArchiveBinaries
arch_bin = ArchiveBinaries()
project_uuid = 'b6de18c6-bba8-4b53-9d9e-3eea4b794268'
arch_bin.save_project_binaries(project_uuid)


from opencontext_py.apps.archive.binaries import ArchiveBinaries
project_uuids = [
    'b6de18c6-bba8-4b53-9d9e-3eea4b794268'
]
for project_uuid in project_uuids:
    arch_bin = ArchiveBinaries()
    arch_bin.save_project_binaries(project_uuid)
    arch_bin.archive_all_project_binaries(project_uuid)


from opencontext_py.apps.archive.binaries import ArchiveBinaries
project_uuids = [
    "DF043419-F23B-41DA-7E4D-EE52AF22F92F"
]
for project_uuid in project_uuids:
    arch_bin = ArchiveBinaries()
    arch_bin.temp_cache_dir = 'temp-cache'
    arch_bin.max_repo_file_count = 2500
    arch_bin.save_project_binaries(project_uuid)
    arch_bin.archive_all_project_binaries(project_uuid)
    

from opencontext_py.apps.archive.binaries import ArchiveBinaries
project_uuid = 'DF043419-F23B-41DA-7E4D-EE52AF22F92F'
archive_dir = 'files-1-by---DF043419-F23B-41DA-7E4D-EE52AF22F92F'
deposition_id = 1251106
arch_bin.archive_dir_project_binaries(project_uuid, archive_dir, deposition_id)


from opencontext_py.apps.archive.binaries import ArchiveBinaries
project_uuid = "3F6DCD13-A476-488E-ED10-47D25513FCB2"
archive_dir = "files-4-by---3F6DCD13-A476-488E-ED10-47D25513FCB2"
deposition_id = 1242673
arch_bin = ArchiveBinaries()
arch_bin.archive_dir_project_binaries(project_uuid, archive_dir, deposition_id)
dirs = [
    "files-5-by---3F6DCD13-A476-488E-ED10-47D25513FCB2",
    "files-6-by---3F6DCD13-A476-488E-ED10-47D25513FCB2"
]
for archive_dir in dirs:
    project_uuid = "3F6DCD13-A476-488E-ED10-47D25513FCB2"
    arch_bin = ArchiveBinaries()
    arch_bin.archive_dir_project_binaries(project_uuid, archive_dir)
    





from opencontext_py.apps.archive.binaries import ArchiveBinaries
project_uuid = "141e814a-ba2d-4560-879f-80f1afb019e9"
archive_dir = "files-4-by---141e814a-ba2d-4560-879f-80f1afb019e9"
deposition_id = 1439449
arch_bin = ArchiveBinaries()
arch_bin.archive_dir_project_binaries(project_uuid, archive_dir, deposition_id)


from opencontext_py.apps.archive.binaries import ArchiveBinaries

dirs = [
    "files-5-by---141e814a-ba2d-4560-879f-80f1afb019e9",
    "files-6-by---141e814a-ba2d-4560-879f-80f1afb019e9",
]
for archive_dir in dirs:
    project_uuid = "141e814a-ba2d-4560-879f-80f1afb019e9"
    arch_bin = ArchiveBinaries()
    arch_bin.archive_dir_project_binaries(project_uuid, archive_dir)


    
    

import shutil
import os
from django.conf import settings
path = settings.STATIC_EXPORTS_ROOT + 'aap-3d/obj-models'
zip_path = settings.STATIC_EXPORTS_ROOT + 'aap-3d/obj-models-zip'
for root, dirs, files in os.walk(path):
    for adir in dirs:
        zip_dir = os.path.join(path, adir)
        zip_file = os.path.join(zip_path, adir)
        print(zip_dir + ' to ' + zip_file)
        shutil.make_archive(zip_file, 'zip', zip_dir)



import pandas as pd
import shutil
import os
import numpy as np

from django.conf import settings

renames = {
    'FORMDATE': 'FORM_DATE',
    'TRINOMIAL': 'SITE_NUM',
    'SITENUM': 'SITE_NUM',
    'TYPE_SITE': 'SITE_TYPE',
    'TYPESITE': 'SITE_TYPE',
    'TYPE_STE': 'SITE_TYPE',
    'SIZESITE': 'SITE_SIZE',
    'SITESIZE': 'SITE_SIZE',
    'SITENAME': 'SITE_NAME',
    'Atlas_Number': 'ATLAS_NUMBER',
    'MAT_COL': 'MATERIAL_COLLECTED',
    'MATERIALS': 'MATERIAL_COLLECTED',
    'ARTIFACTS': 'ARTIFACTS',
    'CULT_DESC': 'TIME_CULTURE_DESC',
    'TIME_DESC': 'TIME_CULTURE_DESC',
    'TIME_OCC': 'TIME_PERIOD',
    'TIME_PER': 'TIME_PERIOD',
    'SING_COM': 'COMPONENT_SINGLE',
    'SINGLE': 'COMPONENT_SINGLE',
    'MULT_COM': 'COMPONENT_MULTI',
    'MULTIPLE': 'COMPONENT_MULTI',
    'COMP_DESC': 'COMPONENT_DESC',
    'BASIS': 'COMPONENT_DESC',
    'COUNTY': 'COUNTY'
}


path = settings.STATIC_EXPORTS_ROOT + 'texas'
dfs = []
all_cols = []
excel_files = []
for root, dirs, files in os.walk(path):
    for act_file in files:
        if act_file.endswith('.xls'):
            file_num = ''.join(c for c in act_file if c.isdigit())
            excel_files.append((int(file_num), act_file))
            dir_file = os.path.join(path, act_file)
            df = pd.read_excel(dir_file, index_col=None, na_values=['NA'])
            df['filename'] = act_file
            df = df.applymap(lambda x: x.encode('unicode_escape').decode('utf-8') if isinstance(x, str) else x)
            col_names = df.columns.values.tolist()
            print('-'*40)
            print(act_file)
            print(str(col_names))
            """
            for bad_col, good_col in renames.items():
                if bad_col in col_names:
                    df.rename(columns={bad_col: good_col}, inplace=True)
            """
            new_cols = df.columns.values.tolist()
            all_cols = list(set(all_cols + new_cols))
            all_cols.sort()
            print('Total of {} columns for all dataframes'.format(len(all_cols)))
            dfs.append(df)
            
            
excel_files = sorted(excel_files)
print('\n'.join([f[1] for f in excel_files]))


all_df = pd.concat(dfs)
csv_all_dir_file = os.path.join(path, 'all-texas.csv')
print('Save the CSV: ' + csv_all_dir_file)
with open(csv_all_dir_file, 'a' ) as f:
    while True:
        all_df.to_csv(f)



xls_all_dir_file = os.path.join(path, 'all-texas.xlsx')
print('Save the Excel: ' + xls_all_dir_file)
with open(xls_all_dir_file, 'a' ) as f:
    while True:
        all_df.to_excel(f, sheet_name='Sheet1')















from opencontext_py.apps.imports.records.models import ImportCell
from opencontext_py.apps.ocitems.assertions.models import Assertion
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.ocitems.subjects.models import Subject
from opencontext_py.apps.ocitems.geospace.models import Geospace
from opencontext_py.apps.ocitems.subjects.generation import SubjectGeneration
from opencontext_py.apps.edit.items.deletemerge import DeleteMerge
from opencontext_py.libs.solrconnection import SolrConnection
project_uuid = '10aa84ad-c5de-4e79-89ce-d83b75ed72b5'
area_proj_uuid = '5A6DDB94-70BE-43B4-2D5D-35D983B21515'
source_id = 'ref:2289489501377'
area_field = 9
feature_field = 10
specimen_field = 1
man_fixes = Manifest.objects.filter(item_type='subjects', class_uri='oc-gen:cat-plant-remains', project_uuid=project_uuid).order_by('sort')
changed_uuids = []
p_subs = {}
for man_obj in man_fixes:
    cont_asses = Assertion.objects.filter(predicate_uuid=Assertion.PREDICATES_CONTAINS, object_uuid=man_obj.uuid)[:1]
    if len(cont_asses):
        continue
    # need to fix missing context association
    spec_id = man_obj.label.replace('Specimen ', '')
    spec_cell = ImportCell.objects.get(source_id=source_id, record=spec_id, field_num=specimen_field)
    area_cell = ImportCell.objects.get(source_id=source_id, field_num=area_field, row_num=spec_cell.row_num)
    feat_cell = ImportCell.objects.get(source_id=source_id, field_num=feature_field, row_num=spec_cell.row_num)
    l_context = '/{}/Feat. {}'.format(area_cell.record.replace('/', '--'), feat_cell.record)
    if feat_cell.record in ['1031', '1089', '1188'] and 'SSGH' in area_cell.record:
        l_context = '/SSGH (Khentkawes)/Feat. {}'.format(feat_cell.record)
    if l_context == '/KKT-E+/Feat. 33821':
        l_context = '/KKT-E/Feat. 33821'
    if l_context == '/KKT-E+/Feat. 33831':
        l_context = '/KKT-E/Feat. 33831'
    print('Find Context: {} for {} import row: {}'.format(l_context, man_obj.label, spec_cell.row_num))
    if l_context not in p_subs:
        parent_sub = Subject.objects.get(context__endswith=l_context, project_uuid__in=[project_uuid, area_proj_uuid])
        p_subs[l_context] = parent_sub
    else:
        parent_sub = p_subs[l_context]
    new_ass = Assertion()
    new_ass.uuid = parent_sub.uuid
    new_ass.subject_type = 'subjects'
    new_ass.project_uuid = man_obj.project_uuid
    new_ass.source_id = 'ref:1967003269393-fix'
    new_ass.obs_node = '#contents-' + str(1)
    new_ass.obs_num = 1
    new_ass.sort = 1
    new_ass.visibility = 1
    new_ass.predicate_uuid = Assertion.PREDICATES_CONTAINS
    new_ass.object_type = man_obj.item_type
    new_ass.object_uuid = man_obj.uuid
    new_ass.save()
    sg = SubjectGeneration()
    sg.generate_save_context_path_from_uuid(man_obj.uuid)
    
from opencontext_py.apps.ocitems.assertions.models import Assertion

Assertion.objects.filter(predicate_uuid=Assertion.PREDICATES_CONTAINS, object_uuid='2176cb88-bcb4-4ad9-b4aa-e9009b8c4a66').exclude(uuid='FEC673D2-C1F0-4B62-BF66-29127AE2AE11').delete()

from opencontext_py.apps.ocitems.assertions.models import Assertion
from opencontext_py.apps.ocitems.subjects.generation import SubjectGeneration
from opencontext_py.apps.ocitems.subjects.models import Subject
from opencontext_py.apps.ocitems.manifest.models import Manifest
from django.core.cache import caches
cache = caches['redis']
cache.clear()
cache = caches['default']
cache.clear()
cache = caches['memory']
cache.clear()
bad_subs = Subject.objects.filter(context__contains='/Egypt/')
bad_uuids = [bs.uuid for bs in bad_subs]
bad_man_objs = Manifest.objects.filter(uuid__in=bad_uuids, class_uri__in=['oc-gen:cat-feature'])
bad_feats = [bm.uuid for bm in bad_man_objs]
f_subs = Subject.objects.filter(uuid__in=bad_feats)
for bad_sub in bad_subs:
    sg = SubjectGeneration()
    sg.generate_save_context_path_from_uuid(bad_sub.uuid)



from opencontext_py.apps.ocitems.assertions.models import Assertion
keep_proj = '5A6DDB94-70BE-43B4-2D5D-35D983B21515'
keep_p = 'bd0a8c74-c3fe-47bb-bb1a-be067e101069'
keep_p_asses = Assertion.objects.filter(uuid=keep_p, predicate_uuid=Assertion.PREDICATES_CONTAINS)
for keep_p_ch in keep_p_asses:
    ch_uuid = keep_p_ch.object_uuid
    bad_asses = Assertion.objects.filter(predicate_uuid=Assertion.PREDICATES_CONTAINS, object_uuid=ch_uuid).exclude(uuid=keep_p)
    if len(bad_asses):
        print('Remove erroneous parents for :' + ch_uuid)
        bad_asses.delete()
    good_asses = Assertion.objects.filter(uuid=keep_p, predicate_uuid=Assertion.PREDICATES_CONTAINS, object_uuid=ch_uuid)
    if len(good_asses) > 1:
        print('More than 1 parent for :' + ch_uuid)
        redund_ass = Assertion.objects.filter(uuid=keep_p, predicate_uuid=Assertion.PREDICATES_CONTAINS, object_uuid=ch_uuid).exclude(project_uuid=keep_proj)
        if len(redund_ass) < len(good_asses):
            print('Delete redundant for ' + ch_uuid)
            redund_ass.delete()
    
    
    bad_asses = Assertion.objects.filter(predicate_uuid=Assertion.PREDICATES_CONTAINS, object_uuid=ch_uuid).exclude(uuid=mvt)
    if len(bad_asses):
        print('delete wrong for: ' + ch_uuid )
        bad_asses.delete()
    m_asses = Assertion.objects.filter(predicate_uuid=Assertion.PREDICATES_CONTAINS, object_uuid=ch_uuid).exclude(uuid=mvt)




from opencontext_py.apps.imports.records.models import ImportCell
from opencontext_py.apps.ocitems.assertions.models import Assertion
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.ocitems.subjects.models import Subject
from opencontext_py.apps.ocitems.geospace.models import Geospace
from opencontext_py.apps.ocitems.subjects.generation import SubjectGeneration
from opencontext_py.apps.edit.items.deletemerge import DeleteMerge
from opencontext_py.libs.solrconnection import SolrConnection
project_uuid = '10aa84ad-c5de-4e79-89ce-d83b75ed72b5'
area_proj_uuid = '5A6DDB94-70BE-43B4-2D5D-35D983B21515'
source_id = 'ref:1967003269393'
area_field = 20
feature_field = 22
specimen_field = 1
man_fixes = Manifest.objects.filter(item_type='subjects', class_uri='oc-gen:cat-feature', project_uuid=project_uuid).order_by('sort')
changed_uuids = []
p_subs = {}
for man_obj in man_fixes:
    cont_asses = Assertion.objects.filter(predicate_uuid=Assertion.PREDICATES_CONTAINS, object_uuid=man_obj.uuid)[:1]
    if len(cont_asses):
        continue
    # need to fix missing context association
    act_id = man_obj.label.replace('Feat. ', '')
    feat_cell = ImportCell.objects.filter(source_id=source_id, record=act_id, field_num=feature_field)[:1][0]
    area_cell = ImportCell.objects.get(source_id=source_id, field_num=area_field, row_num=feat_cell.row_num)
    l_context = area_cell.record.replace('/', '--')
    l_context = '/' + l_context
    if act_id in ['1031', '1089', '1188'] and 'SSGH' in l_context:
        l_context = '/SSGH (Khentkawes)'
    print('Find Context: {} for {} import row: {}'.format(l_context, man_obj.label, feat_cell.row_num))
    if l_context not in p_subs:
        parent_sub = Subject.objects.get(context__endswith=l_context, project_uuid__in=[project_uuid, area_proj_uuid])
        p_subs[l_context] = parent_sub
    else:
        parent_sub = p_subs[l_context]
    print('Adding Context: {} : {}'.format(parent_sub.uuid, parent_sub.context))
    new_ass = Assertion()
    new_ass.uuid = parent_sub.uuid
    new_ass.subject_type = 'subjects'
    new_ass.project_uuid = man_obj.project_uuid
    new_ass.source_id = source_id + '-fix'
    new_ass.obs_node = '#contents-' + str(1)
    new_ass.obs_num = 1
    new_ass.sort = 1
    new_ass.visibility = 1
    new_ass.predicate_uuid = Assertion.PREDICATES_CONTAINS
    new_ass.object_type = man_obj.item_type
    new_ass.object_uuid = man_obj.uuid
    new_ass.save()
    sg = SubjectGeneration()
    sg.generate_save_context_path_from_uuid(man_obj.uuid)


from opencontext_py.apps.ocitems.assertions.models import Assertion
from opencontext_py.apps.ocitems.manifest.models import Manifest
parent_uuid = '64a12f7b-5ed3-4b1e-beb0-186d5f6c8549'
project_uuid = '10aa84ad-c5de-4e79-89ce-d83b75ed72b5'
area_proj_uuid = '5A6DDB94-70BE-43B4-2D5D-35D983B21515'
child_uuids = []
for child in Assertion.objects.filter(predicate_uuid=Assertion.PREDICATES_CONTAINS, uuid=parent_uuid):
    child_uuids.append(child.object_uuid)

keeps_mans = Manifest.objects.filter(uuid__in=child_uuids, project_uuid=area_proj_uuid)
for keep_man in keeps_mans:
    rem_men = Manifest.objects.filter(label=keep_man.label, uuid__in=child_uuids, project_uuid=project_uuid)[:1]
    if len(rem_men):
        delete_uuid = rem_men[0].uuid
        merge_into_uuid = keep_man.uuid
        print('Remove {} to keep {} with label {}'.format(delete_uuid, merge_into_uuid, keep_man.label))
        dm = DeleteMerge()
        dm.merge_by_uuid(delete_uuid, merge_into_uuid)



from opencontext_py.apps.edit.items.deletemerge import DeleteMerge

delete_uuid = '12b6512b-22bc-4eb7-b23d-868aff7b380a'
merge_into_uuid = '9a567a71-1cc7-4e51-8e8f-79e0a46e0f40'
dm = DeleteMerge()
dm.merge_by_uuid(delete_uuid, merge_into_uuid)


import json
import random
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.libs.validategeojson import ValidateGeoJson
from opencontext_py.libs.clustergeojson import ClusterGeoJson
from opencontext_py.libs.reprojection import ReprojectUtilities
from opencontext_py.apps.imports.geojson.geojson import GeoJSONimport
from opencontext_py.apps.ocitems.geospace.models import Geospace, GeospaceGeneration
gimp = GeoJSONimport()
gimp.load_into_importer = False
gimp.project_uuid = 'DF043419-F23B-41DA-7E4D-EE52AF22F92F'
gimp.source_id = 'vesco_trenches_2017_4326'
geoclust = ClusterGeoJson()
rpu = ReprojectUtilities()
rpu.set_in_out_crs('EPSG:32636', 'EPSG:4326')
geojsons = {}
for file in ['observation_points', 'avkat_dbo_features', 'features_intensive_survey', 'suvey_units']:
    json_obj = gimp.load_json_file('avkat-geo', (file + '.json'))
    geojson = LastUpdatedOrderedDict()
    geojson['type'] = 'FeatureCollection'
    geojson['features'] = []
    samp_geojson = LastUpdatedOrderedDict()
    samp_geojson['type'] = 'FeatureCollection'
    samp_geojson['features'] = []
    i = 0
    for old_f in json_obj['features']:
        # import pdb; pdb.set_trace()
        i += 1
        new_f = LastUpdatedOrderedDict()
        new_f['type'] = 'Feature'
        if 'attributes' in old_f:
            new_f['properties'] = old_f['attributes']
        elif 'properties' in old_f:
            new_f['properties'] = old_f['properties']
        new_f['geometry'] = LastUpdatedOrderedDict()
        if 'rings' in old_f['geometry']:
            new_f['geometry']['type'] = 'Polygon'
            new_f['geometry']['coordinates'] = old_f['geometry']['rings']
            geometry_type = new_f['geometry']['type']
            coordinates = new_f['geometry']['coordinates']
            v_geojson = ValidateGeoJson()
            c_ok = v_geojson.validate_all_geometry_coordinates(geometry_type,
                                                               coordinates)
            if not c_ok:
                print('Fixing coordinates for: {}'.format(i))
                coordinates = v_geojson.fix_geometry_rings_dir(geometry_type, coordinates)
                new_f['geometry']['coordinates'] = coordinates
            coord_str = json.dumps(coordinates, indent=4, ensure_ascii=False)
            gg = GeospaceGeneration()
            lon_lat = gg.get_centroid_lonlat_coordinates(coord_str, geometry_type)
            new_f['properties']['latitude'] = lon_lat[1]
            new_f['properties']['longitude'] = lon_lat[0]
        else:
            if 'x' in old_f['geometry'] and 'y' in old_f['geometry']:
                coords = rpu.reproject_coordinate_pair([ float(old_f['geometry']['x']), float(old_f['geometry']['y'])])
            if ('type' in old_f['geometry'] and
                old_f['geometry']['type'] == 'Point' and
                'coordinates' in old_f['geometry']):
                coords = old_f['geometry']['coordinates']
            if coords is None:
                import pdb; pdb.set_trace()
            new_f['geometry']['type'] = 'Point'
            new_f['geometry']['coordinates'] = coords
            if 'x' in old_f['geometry'] and 'y' in old_f['geometry']:
                new_f['properties']['utm-x'] = old_f['geometry']['x']
                new_f['properties']['utm-y'] = old_f['geometry']['y']
            new_f['properties']['lat'] = coords[1]
            new_f['properties']['lon'] = coords[0]
        geojson['features'].append(new_f)
        r = random.randint(1,11)
        if r > 9:
            samp_geojson['features'].append(new_f)
    
    geojson = geoclust.extact_lon_lat_data_from_geojson(geojson)
    gimp.save_json_file(geojson, 'avkat-geo', (file + '-new.geojson'))
    gimp.save_json_file(samp_geojson, 'avkat-geo', (file + '-new-sampled.geojson'))
    geojsons[file] = geojson


geoclust.cluster_lon_lats()
for file, geojson in geojsons.items():
    geojson = geoclust.add_cluster_property_to_geojson(geojson)
    gimp.save_json_file(geojson, 'avkat-geo', (file + '-new-clustered.geojson'))


all_geojson = geoclust.make_clusters_geojson()
gimp.save_json_file(all_geojson, 'avkat-geo', 'all-clustered-new.geojson')






import json
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.libs.validategeojson import ValidateGeoJson
from opencontext_py.libs.clustergeojson import ClusterGeoJson
from opencontext_py.apps.imports.geojson.geojson import GeoJSONimport
from opencontext_py.apps.ocitems.geospace.models import Geospace, GeospaceGeneration
from opencontext_py.apps.imports.fieldannotations.models import ImportFieldAnnotation
gimp = GeoJSONimport()
gimp.load_into_importer = False
project_uuid = '02b55e8c-e9b1-49e5-8edf-0afeea10e2be'
configs = [
    # ('suvey_units', '', 'SU', 'oc-gen:cat-survey-unit'),
    # ('all', 'SU Group ', 'lon-lat-cluster', 'oc-gen:cat-region'),
    ('features_intensive_survey', '', 'f_no', 'oc-gen:cat-feature'),
]
for file, label_prefix, label_prop, class_uri in configs:
    gimp.source_id = file
    geojson = gimp.load_json_file('avkat-geo', (file + '-clustered.geojson'))
    for feat in geojson['features']:
        label = label_prefix + str(feat['properties'][label_prop])
        man_obj = Manifest.objects.get(label=label, project_uuid=project_uuid, class_uri=class_uri)
        props = LastUpdatedOrderedDict()
        props['uri'] = 'https://opencontext.org/subjects/' + man_obj.uuid
        old_props = feat['properties']
        for key, val in old_props.items():
            props[key] = val
        feat['properties'] = props
        geometry_type = feat['geometry']['type']
        coordinates = feat['geometry']['coordinates']
        coord_str = json.dumps(coordinates, indent=4, ensure_ascii=False)
        gg = GeospaceGeneration()
        lon_lat = gg.get_centroid_lonlat_coordinates(coord_str, geometry_type)
        Geospace.objects.filter(uuid=man_obj.uuid).delete()
        geo = Geospace()
        geo.uuid = man_obj.uuid
        geo.project_uuid = man_obj.project_uuid
        geo.source_id = file
        geo.item_type = man_obj.item_type
        geo.feature_id = 1
        geo.meta_type = ImportFieldAnnotation.PRED_GEO_LOCATION
        geo.ftype = geometry_type
        geo.latitude = lon_lat[1]
        geo.longitude = lon_lat[0]
        geo.specificity = 0
        # dump coordinates as json string
        geo.coordinates = coord_str
        try:
            geo.save()
        except:
            print('Problem saving: ' + str(man_obj.uuid))
            quit()
        
    gimp.save_json_file(geojson, 'avkat-geo', (file + '-clustered-uris.geojson'))







from opencontext_py.apps.ocitems.assertions.models import Assertion
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.ocitems.predicates.models import Predicate
project_uuid = '02b55e8c-e9b1-49e5-8edf-0afeea10e2be'
vars = [
    'GIS Feature ID',
    'Survey Unit ID',
    'Transect Type',
    'Survey Bearing',
    'Survey Unit Width',
    'Linear Meters Walked',
    'Shape Length',
    'Shape Area',
    'Weather',
    'Visibility',
    'Ceramics',
    'Land Use',
    'AgType Cereal',
    'AgType Plow',
    'AgType Fruit',
    'AgType Forest',
    'AgType Olive',
    'AgType Vegetable',
    'AgType Vines Grapes',
    'AgType Bee Keeping',
    'AgType Other',
    'AgType Other Description',
    'Description',
]
sort = 9
for vvar in vars:
    sort += 1
    print('Find: ' + vvar)
    vman = Manifest.objects.get(label=vvar, project_uuid=project_uuid, item_type='predicates')
    vpred = Predicate.objects.get(uuid=vman.uuid)
    vpred.sort = sort
    vpred.save()
    Assertion.objects.filter(predicate_uuid=vman.uuid).update(sort=sort)


from opencontext_py.apps.ocitems.assertions.models import Assertion
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.ocitems.predicates.models import Predicate
project_uuid = '02b55e8c-e9b1-49e5-8edf-0afeea10e2be'
vars = [
    "Team member walking the 'A' line",
    "Team member walking the 'B' line",
    "Team member walking the 'C' line",
    "Team member walking the 'D' line",
    "Team member walking the 'E' line",
    "Team member walking the 'F' line",
    "Team member walking the 'G' line",
    "Team member walking the 'H' line",
    "Team Leader",
    "Paper Form Completed by",
]
sort = 99
for vvar in vars:
    sort += 1
    print('Find: ' + vvar)
    vman = Manifest.objects.get(label=vvar, project_uuid=project_uuid, item_type='predicates')
    vpred = Predicate.objects.get(uuid=vman.uuid)
    vpred.sort = sort
    vpred.save()
    Assertion.objects.filter(predicate_uuid=vman.uuid).update(sort=sort)
    
    

import os
from django.conf import settings
from opencontext_py.libs.binaryfiles import BinaryFiles
from opencontext_py.apps.ocitems.mediafiles.models import Mediafile 
path = settings.STATIC_EXPORTS_ROOT + 'iiif'
project_uuid = '141e814a-ba2d-4560-879f-80f1afb019e9'
min_size = 104394357.0
bf = BinaryFiles()
meds = Mediafile.objects.filter(project_uuid=project_uuid, filesize__gte=min_size)\
                        .exclude(mime_type_uri__contains='application/pdf')\
                        .order_by('-filesize')[:100]
for med in meds:
    file_name = med.file_uri.split('/')[-1]
    print('Save ' + file_name)
    bf.get_cache_remote_file_content_http(file_name, med.file_uri, 'iiif')
    
    
from opencontext_py.apps.ocitems.mediafiles.models import Mediafile 
project_uuid = '141e814a-ba2d-4560-879f-80f1afb019e9'
min_size = 104394357.0
imgs = {}
imgs['101-drawing-d-ss-016.tif'] = 'https://free.iiifhosting.com/iiif/291e81f8bc2847aaa5f4c532b4f59e1751aa76ce2e7a7ce8acd459ec0f9b2f30/info.json'
imgs['101-drawing-d-ss-016.tif'] = 'https://free.iiifhosting.com/iiif/291e81f8bc2847aaa5f4c532b4f59e1751aa76ce2e7a7ce8acd459ec0f9b2f30/info.json'
imgs['101-drawing-d-gen-027.tif'] = 'https://free.iiifhosting.com/iiif/a696615ab137c4de2a6c7212651df9467cd04505b21dcbc2602c43eaa2ecaf7a/info.json'
imgs['101-drawing-d-ss-002.tif'] = 'https://free.iiifhosting.com/iiif/69317657a4540d28ce549cb082fed05e821b2a205ba3f69a51539772e94866f5/info.json'
imgs['101-drawing-d-e-047.tif'] = 'https://free.iiifhosting.com/iiif/42e0b97f7b0e46a83828e521c04805e771a8e1dfe24fbada611de9b0726313c3/info.json'
imgs['101-drawing-d-ss-001.tif'] = 'https://free.iiifhosting.com/iiif/840728372ee6b611c3baf631f109b79b3e5657f38e71ff2499b34532f62745fa/info.json'
imgs['101-drawing-d-kvt-006.tif'] = 'https://free.iiifhosting.com/iiif/641ba83302bdb3c1b6d5e9a58a1ce948e6ba0da375ebbc5231df6a4453c5c748/info.json'
imgs['101-drawing-d-gen-007.tif'] = 'https://free.iiifhosting.com/iiif/479f5a37dd2f33d959cf72528ce3978f6ff70788625ab71e028bc1eb360494ad/info.json'
imgs['101-drawing-d-ss-015.tif'] = 'https://free.iiifhosting.com/iiif/9a7393c9278fe60e4ab23d4a2bfd0d7192ab048d132795f337a6b79e89c2f24/info.json'
imgs['101-drawing-d-gen-005.tif'] = 'https://free.iiifhosting.com/iiif/2b85999ad86fa3200a91121912b28e9bae96d55dd554d1d45bd2ac7de003532d/info.json'
imgs['101-drawing-d-ss-004.tif'] = 'https://free.iiifhosting.com/iiif/390df4778e208fd9035c822d161a718414dc56d38b02f6e1dc9c1617d9744cb7/info.json'
imgs['101-drawing-d-ss-005.tif'] = 'https://free.iiifhosting.com/iiif/2851bd2a55ed85cfd1775f9b4b9689b776c1e134e488230e4871736f05972127/info.json'
imgs['101-drawing-d-ss-021.tif'] = 'https://free.iiifhosting.com/iiif/7fd8f19d033a10db04a9960042911223d69468b6df9dfeee1f2c0221d3e29f58/info.json'
imgs['101-drawing-d-ss-003.tif'] = 'https://free.iiifhosting.com/iiif/22443f7c36e4a60e6fb1c8eafdecedd44d55edb16d1ff5da3f7d960f46e9c9ad/info.json'
imgs['101-drawing-d-ss-012.tiff'] = 'https://free.iiifhosting.com/iiif/936ba50885c56f808dd4fc4056f6dd0ae993c084379e2975c5091e6f06e5d9ce/info.json'

meds = Mediafile.objects.filter(project_uuid=project_uuid, filesize__gte=min_size)\
                        .exclude(mime_type_uri__contains='application/pdf')\
                        .order_by('-filesize')[:100]
for med in meds:
    print(med.uuid)





from opencontext_py.apps.imports.records.models import ImportCell
from opencontext_py.apps.ocitems.assertions.models import Assertion
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.ocitems.mediafiles.models import Mediafile
project_uuid = '02b55e8c-e9b1-49e5-8edf-0afeea10e2be'
source_id = 'ref:1669580990802'
sunit_field = 12
feature_field = 11
full_field = 15
med_cells = ImportCell.objects.filter(source_id=source_id, field_num=full_field)
for med_cell in med_cells:
    feat_man = None
    su_man = None
    feat_cell = ImportCell.objects.filter(source_id=source_id, row_num=med_cell.row_num, field_num=feature_field)[:1][0]
    su_cell = ImportCell.objects.filter(source_id=source_id, row_num=med_cell.row_num, field_num=sunit_field)[:1][0]
    try:
        feat_man = Manifest.objects.get(label=feat_cell.record, item_type='subjects', class_uri='oc-gen:cat-feature', project_uuid=project_uuid)
    except:
        pass
    try:
        su_man = Manifest.objects.get(label=su_cell.record, item_type='subjects', class_uri='oc-gen:cat-survey-unit', project_uuid=project_uuid)
    except:
        pass
    full_uri = med_cell.record
    media_f = Mediafile.objects.get(file_uri=full_uri, project_uuid=project_uuid)
    if feat_man:
        print('Adding Feature: {} : {}'.format(feat_man.uuid, media_f.uuid))
        Assertion.objects.filter(uuid=feat_man.uuid, object_uuid=media_f.uuid).delete()
        Assertion.objects.filter(object_uuid=feat_man.uuid, uuid=media_f.uuid).delete()
        new_ass = Assertion()
        new_ass.uuid = feat_man.uuid
        new_ass.subject_type = feat_man.item_type
        new_ass.project_uuid = feat_man.project_uuid
        new_ass.source_id = source_id + '-fix'
        new_ass.obs_node = '#obs-' + str(1)
        new_ass.obs_num = 1
        new_ass.sort = 1
        new_ass.visibility = 1
        new_ass.predicate_uuid = 'oc-3'
        new_ass.object_type = 'media'
        new_ass.object_uuid = media_f.uuid
        new_ass.save()
        new_ass = Assertion()
        new_ass.uuid = media_f.uuid
        new_ass.subject_type = 'media'
        new_ass.project_uuid = project_uuid
        new_ass.source_id = source_id + '-fix'
        new_ass.obs_node = '#obs-' + str(1)
        new_ass.obs_num = 1
        new_ass.sort = 1
        new_ass.visibility = 1
        new_ass.predicate_uuid = 'oc-3'
        new_ass.object_type = feat_man.item_type
        new_ass.object_uuid = feat_man.uuid
        new_ass.save()
    if su_man:
        print('Adding Survey Unit: {} : {}'.format(su_man.uuid, media_f.uuid))
        Assertion.objects.filter(uuid=su_man.uuid, object_uuid=media_f.uuid).delete()
        Assertion.objects.filter(object_uuid=su_man.uuid, uuid=media_f.uuid).delete()
        new_ass = Assertion()
        new_ass.uuid = su_man.uuid
        new_ass.subject_type = su_man.item_type
        new_ass.project_uuid = su_man.project_uuid
        new_ass.source_id = source_id + '-fix'
        new_ass.obs_node = '#obs-' + str(1)
        new_ass.obs_num = 1
        new_ass.sort = 1
        new_ass.visibility = 1
        new_ass.predicate_uuid = 'oc-3'
        new_ass.object_type = 'media'
        new_ass.object_uuid = media_f.uuid
        new_ass.save()
        new_ass = Assertion()
        new_ass.uuid = media_f.uuid
        new_ass.subject_type = 'media'
        new_ass.project_uuid = project_uuid
        new_ass.source_id = source_id + '-fix'
        new_ass.obs_node = '#obs-' + str(1)
        new_ass.obs_num = 1
        new_ass.sort = 1
        new_ass.visibility = 1
        new_ass.predicate_uuid = 'oc-3'
        new_ass.object_type = su_man.item_type
        new_ass.object_uuid = su_man.uuid
        new_ass.save()




from opencontext_py.apps.ocitems.assertions.models import Assertion
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.ocitems.mediafiles.models import Mediafile
project_uuid = '02b55e8c-e9b1-49e5-8edf-0afeea10e2be'
source_id = 'ref:1669580990802'
m_mans = Manifest.objects.filter(project_uuid=project_uuid, source_id=source_id, item_type='media')
for m_man in m_mans:
    a_chk = Assertion.objects.filter(subject_type='subjects', object_uuid=m_man.uuid)[:1]
    if len(a_chk) > 0:
        continue
    if len(a_chk) == 0:
        print('Delete! {} has {} subject links'.format(m_man.uuid, len(a_chk)))
        Mediafile.objects.filter(uuid=m_man.uuid).delete()
        Assertion.objects.filter(uuid=m_man.uuid).delete()
        Assertion.objects.filter(object_uuid=m_man.uuid).delete()
        m_man.delete()
        
        
        



sources = [
    ('trap-geo-yambal',
     'Survey Unit ',
     'SUID',
     'yam-survey-units-reproj-w-uuids-clustered.geojson',
     'yam-survey-units-clustered-w-uris.geojson'),
    ('trap-geo-kazanlak',
     'Survey Unit ',
     'SUID',
     'kaz-survey-units-reproj-w-uuids-best-clustered.geojson',
     'kaz-survey-units-clustered-w-uris.geojson'),
    ('trap-geo-yambal-groups',
     'S.U. Group Y',
     'lon-lat-cluster',
     'yam-clustered.geojson',
     'yam-clustered-w-uris.geojson'),
    ('trap-geo-kazanlak-groups',
     'S.U. Group K',
     'lon-lat-cluster',
     'kaz-clustered.geojson',
     'kaz-clustered-w-uris.geojson')
]

from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.imports.geojson.geojson import GeoJSONimport
from opencontext_py.apps.ocitems.geospace.models import Geospace
project_uuid = '24e2aa20-59e6-4d66-948b-50ee245a7cfc'
sources = [
    ('trap-geo-yambal-groups',
     'S.U. Group Y',
     'lon-lat-cluster',
     'yam-clustered.geojson',
     'yam-clustered-w-uris.geojson'),
    ('trap-geo-kazanlak-groups',
     'S.U. Group K',
     'lon-lat-cluster',
     'kaz-clustered.geojson',
     'kaz-clustered-w-uris.geojson')
]
for source_id, prefix, id_prop, old_file, new_file in sources:
    Geospace.objects\
            .filter(source_id=source_id,
                    project_uuid=project_uuid,
                    ftype__in=['Polygon', 'Multipolygon']).delete()
    gimp = GeoJSONimport()
    gimp.load_into_importer = False
    gimp.project_uuid = project_uuid 
    gimp.source_id = source_id
    json_obj = gimp.load_json_file('trap-geo', old_file)
    rev_json = LastUpdatedOrderedDict()
    rev_json['type'] = 'FeatureCollection'
    rev_json['features'] = []
    for feat in json_obj['features']:
        suid = feat['properties'][id_prop]
        label = prefix + str(suid)
        print('Find {}'.format(label))
        man_obj = Manifest.objects.get(label=label, project_uuid=project_uuid, item_type='subjects')
        feat['properties']['uri'] = 'http://opencontext.org/subjects/' + man_obj.uuid
        if 'uuid' in feat['properties']:
            feat['properties'].pop('uuid')
        rev_json['features'].append(feat)
        print('{} is {}'.format(man_obj.label, man_obj.uuid))
    gimp.save_json_file(rev_json, 'trap-geo', new_file)
    gimp.process_features_in_file('trap-geo', new_file)




from opencontext_py.apps.ocitems.assertions.models import Assertion
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.ocitems.predicates.models import Predicate
project_uuid = 'a52bd40a-9ac8-4160-a9b0-bd2795079203'
pred = Manifest.objects.get(uuid=predicate_uuid)
mans = Manifest.objects.filter(project_uuid=project_uuid, item_type='media')
pers = Manifest.objects.get(uuid='0dcda4ad-812b-484f-ad70-3613d063cf52')  # Kevin
predicate_uuid = 'fc335a0d-42e0-42ae-bb11-0ef46ec048e8'
pm = Predicate.objects.get(uuid=predicate_uuid)
for man_obj in mans:
    Assertion.objects.filter(uuid=man_obj.uuid, object_type='persons').delete()
    new_ass = Assertion()
    new_ass.uuid = man_obj.uuid
    new_ass.subject_type = man_obj.item_type
    new_ass.project_uuid = man_obj.project_uuid
    new_ass.source_id = 'kevin-contributor'
    new_ass.obs_node = '#obs-' + str(1)
    new_ass.obs_num = 1
    new_ass.sort = 1
    new_ass.visibility = 1
    new_ass.predicate_uuid = predicate_uuid
    new_ass.object_type = pers.item_type
    new_ass.object_uuid = pers.uuid
    new_ass.save()
    