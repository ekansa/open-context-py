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



from opencontext_py.apps.ldata.tdar.api import tdarAPI
keyword_uri = 'http://core.tdar.org/browse/site-name/9694/44ce83'
tdar = tdarAPI()
tdar.search_by_site_keyword_uris(keyword_uri)


from opencontext_py.apps.archive.files import ArchiveFiles
archive = ArchiveFiles()
archive.save_project_data('3')

from opencontext_py.apps.archive.binaries import ArchiveBinaries
arch_bin = ArchiveBinaries()
project_uuid = '141e814a-ba2d-4560-879f-80f1afb019e9'
arch_bin.get_distinct_licenses(project_uuid)

from opencontext_py.apps.archive.binaries import ArchiveBinaries
arch_bin = ArchiveBinaries()
project_uuid = 'cbd24bbb-c6fc-44ed-bd67-6f844f120ad5'
arch_bin.get_distinct_licenses(project_uuid)



from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.archive.binaries import ArchiveBinaries
arch_bin = ArchiveBinaries()
project_uuid = '81d1157d-28f4-46ff-98dd-94899c1688f8'
arch_bin.save_project_binaries(project_uuid)

from opencontext_py.apps.archive.binaries import ArchiveBinaries
project_uuid = '334853c8-320e-4bdc-96b3-f696171b5a58'
arch_bin = ArchiveBinaries()
arch_bin.save_project_binaries(project_uuid)
arch_bin.get_project_binaries_dirs(project_uuid)


from opencontext_py.apps.archive.files import ArchiveFiles
archive = ArchiveFiles()
archive.get_sub_directories([])


from opencontext_py.apps.ocitems.ocitem.generation import OCitem
from opencontext_py.apps.archive.metadata import ArchiveMetadata
arch_meta = ArchiveMetadata()
project_uuid = '81d1157d-28f4-46ff-98dd-94899c1688f8'
oc_item = OCitem(True)
exists = oc_item.check_exists(project_uuid)
oc_item.generate_json_ld()
item_dict = oc_item.json_ld
arch_meta.make_zenodo_creator_list(item_dict)

from opencontext_py.apps.archive.zenodo import ArchiveZenodo
zenodo = ArchiveZenodo(True)
zenodo.create_empty_deposition()



from opencontext_py.apps.archive.binaries import ArchiveBinaries
project_uuid = '334853c8-320e-4bdc-96b3-f696171b5a58'
archive_dir = 'files-1-by---334853c8-320e-4bdc-96b3-f696171b5a58'
arch_bin = ArchiveBinaries(True)
deposition_id = arch_bin.archive_dir_project_binaries(project_uuid, archive_dir)
