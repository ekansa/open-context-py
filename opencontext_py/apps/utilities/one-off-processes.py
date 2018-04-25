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
pred_uuid = '71440c6e-f996-4ac4-a6a1-a47f9ef605a7'
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


