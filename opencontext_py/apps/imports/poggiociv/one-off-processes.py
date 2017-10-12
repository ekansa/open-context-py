"""
One off processing scripts to handle edge cases, cleanup, and straggler data
"""





# import to fix object context associations
# the source database had inconsistent ways context associations got made,
# leading to difference between the way context was shown in open context and in the poggio civitate legacy website
# this fixed MOST such differences, but not all as item identifers in the legacy database were not unique
from opencontext_py.apps.imports.records.models import ImportCell
from opencontext_py.apps.ocitems.assertions.models import Assertion
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.ocitems.subjects.generation import SubjectGeneration
checks = []
uuid_field_num = 2
tb_field_num = 3
locus_field_num = 4
tr_id_field_num = 5
source_id = 'ref:1837878042180'
imp_uuids = ImportCell.objects.filter(source_id=source_id, field_num=uuid_field_num).order_by('row_num')
for imp_uuid in imp_uuids:
    check = {}
    uuid = imp_uuid.record
    check['uuid'] = uuid
    tb_imps = ImportCell.objects.filter(source_id=source_id, field_num=tb_field_num, row_num=imp_uuid.row_num)[:1]
    tb_str = tb_imps[0].record
    try:
        check['tb'] = int(float(tb_str))
    except:
        check['tb'] = -100
    locus_imps = ImportCell.objects.filter(source_id=source_id, field_num=locus_field_num, row_num=imp_uuid.row_num)[:1]
    locus_str = locus_imps[0].record
    try:
        check['locus'] = int(float(locus_str))
    except:
        check['locus'] = 0
    tr_imps = ImportCell.objects.filter(source_id=source_id, field_num=tr_id_field_num, row_num=imp_uuid.row_num)[:1]
    tr_str = tr_imps[0].record
    try:
        check['tr-id'] = int(float(tr_str))
    except:
        check['tr-id']= 0
    checks.append(check)
for check in checks:
    man_obj = Manifest.objects.get(uuid=check['uuid'])
    man_good_unit = None
    tr_id = None
    if check['tr-id'] > 0:
        tr_id = 'ID:' + str(check['tr-id'])
    tb_id_q = '"tb_id":' + str(check['tb'])
    man_docs = Manifest.objects.filter(item_type='documents', sup_json__contains=tb_id_q).order_by('sort')
    tb_link_sort = 500
    for man_doc in man_docs:
        if man_doc.sup_json['tb_id'] == check['tb'] and tr_id is not None:
            tr_unit_mans = Manifest.objects.filter(label__endswith=tr_id, class_uri='oc-gen:cat-exc-unit')[:1]
            if len(tr_unit_mans) > 0:
                tr_unit_man = tr_unit_mans[0]
                su_tr_asses = Assertion.objects.filter(uuid=tr_unit_man.uuid, predicate_uuid='oc-3', object_uuid=man_doc.uuid)
                if len(su_tr_asses) < 1:
                    tb_link_sort += 1
                    print('We need to associate the trench book with a trench unit')
                    new_ass = Assertion()
                    new_ass.uuid = tr_unit_man.uuid
                    new_ass.subject_type = tr_unit_man.item_type
                    new_ass.project_uuid = tr_unit_man.project_uuid
                    new_ass.source_id = 'fix-from-trench-book-id'
                    new_ass.obs_node = '#obs-' + str(1)
                    new_ass.obs_num = 1
                    new_ass.sort = tb_link_sort
                    new_ass.visibility = 1
                    new_ass.predicate_uuid = 'oc-3'
                    new_ass.object_type = man_doc.item_type
                    new_ass.object_uuid = man_doc.uuid
                    new_ass.save()
    exact_match_found = False
    for man_doc in man_docs:
        if man_doc.sup_json['tb_id'] == check['tb'] and exact_match_found is False:
            q_uuids = []
            su_asses = Assertion.objects.filter(subject_type='subjects', predicate_uuid='oc-3', object_uuid=man_doc.uuid)
            for su_ass in su_asses:
                q_uuids.append(su_ass.uuid)
            tr_man_objs = Manifest.objects.filter(uuid__in=q_uuids, class_uri='oc-gen:cat-exc-unit')
            if tr_id is not None:
                for tr_man_obj in tr_man_objs:
                    if tr_id in tr_man_obj.label:
                        man_good_unit = tr_man_obj 
                        exact_match_found = True
                        break
            elif len(man_objs) > 0 and exact_match_found is False:
                man_good_unit = tr_man_objs[0]
            else:
                pass
    if man_good_unit is not None:
        if ',' in man_good_unit.label:
            l_ex = man_good_unit.label.split(',')
            year_str = l_ex[0]
            if year_str in man_obj.label or exact_match_found:
                in_man_obj = man_good_unit
                if check['locus'] != 0:
                    l_label = 'Locus ' + str(check['locus'])
                    ch_asses = Assertion.objects.filter(uuid=man_good_unit.uuid,
                                                        predicate_uuid='oc-gen:contains',
                                                        object_type='subjects')
                    q_uuids = []
                    for ch_ass in ch_asses:
                        q_uuids.append(ch_ass.object_uuid)
                    man_childs = Manifest.objects.filter(uuid__in=q_uuids, label=l_label)[:1]
                    if len(man_childs) > 0:
                        in_man_obj = man_childs[0]
                # delete prior containment relationship
                del_ok = False
                del_objs = Assertion.objects\
                                    .filter(object_uuid=man_obj.uuid,
                                            predicate_uuid='oc-gen:contains')\
                                    .exclude(uuid=in_man_obj.uuid)
                if len(del_objs) > 0:
                    del_ok = True
                    print('Removing old containment relation')
                    for del_obj in del_objs:
                        del_obj.delete()
                if del_ok:
                    if exact_match_found:
                        print('----------------------------------------------------')
                        print('EXACT MATCH ON TB BOOK ID AND TRENCH (Unit Year) ID')
                        print('----------------------------------------------------')
                    print('We have a new good home for ' + man_obj.label + ' ' + man_obj.uuid)
                    new_ass = Assertion()
                    new_ass.uuid = in_man_obj.uuid
                    new_ass.subject_type = 'subjects'
                    new_ass.project_uuid = in_man_obj.project_uuid
                    new_ass.source_id = 'fix-from-trench-book-id'
                    new_ass.obs_node = '#contents-' + str(1)
                    new_ass.obs_num = 1
                    new_ass.sort = 1
                    new_ass.visibility = 1
                    new_ass.predicate_uuid = 'oc-gen:contains'
                    new_ass.object_type = man_obj.item_type
                    new_ass.object_uuid = man_obj.uuid
                    new_ass.save()
                    sg = SubjectGeneration()
                    sg.generate_save_context_path_from_manifest_obj(man_obj)







# this associated the page numbers associated with a cataloged object with the correct trench book entry
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.ocitems.assertions.models import Assertion
from opencontext_py.apps.imports.records.models import ImportCell
source_id = 'ref:1623762545130'
imp_uuids = ImportCell.objects.filter(source_id=source_id, field_num=2).order_by('row_num')
unit_uuid_tb_objs = {}
for imp_uuid in imp_uuids:
    uuid = imp_uuid.record
    imp_pages = ImportCell.objects.filter(source_id=source_id, field_num=3, row_num=imp_uuid.row_num)[:1]
    pages_str = imp_pages[0].record
    if len(pages_str) > 0:
        unit_uuid = None
        par_asses = Assertion.objects.filter(object_uuid=uuid, predicate_uuid='oc-gen:contains')[:1]
        if len(par_asses) > 0:
            par_man = Manifest.objects.get(uuid=par_asses[0].uuid)
            if par_man.class_uri != 'oc-gen:cat-exc-unit':
                # we have a locus or something so check its parent
                par_asses_b = Assertion.objects.filter(object_uuid=par_asses[0].uuid, predicate_uuid='oc-gen:contains')[:1]
                if len(par_asses_b) > 1:
                    par_man = Manifest.objects.get(uuid=par_asses_b[0].uuid)
                    if par_man.class_uri == 'oc-gen:cat-exc-unit':
                        unit_uuid = par_man.uuid
            else:
                unit_uuid = par_man.uuid
        if unit_uuid is not None:
            # we found a related unit uuid for this object
            if unit_uuid not in unit_uuid_tb_objs:
                unit_uuid_tb_objs[unit_uuid] = []
                tb_asses = Assertion.objects.filter(uuid=unit_uuid, object_type='documents').order_by('sort')
                for tb_ass in tb_asses:
                    try:
                        man_tb = Manifest.objects.get(uuid=tb_ass.object_uuid)
                        man_tb.page_range = []
                        if ':' in man_tb.label:
                            l_ex_a = man_tb.label.split(':')
                            p_part_raw = l_ex_a[1]
                            if ';' in p_part_raw:
                                p_part_raw_ex = p_part_raw.split(';')
                                p_part = p_part_raw_ex[0]
                            else:
                                p_part = p_part_raw
                            if '-' in p_part:
                                p_part_ex = p_part.split('-')
                            else:
                                p_part_ex = [p_part]
                            man_tb.tb_p_range = []
                            for p_str in p_part_ex:
                                try:
                                    tb_page = int(float(p_str))
                                except:
                                    tb_page = None
                                if tb_page is not None:
                                    man_tb.page_range.append(tb_page)
                        unit_uuid_tb_objs[unit_uuid].append(man_tb)
                    except:
                        pass
            if unit_uuid in unit_uuid_tb_objs:
                pages = []
                if ',' in pages_str:
                    pages_str_ex = pages_str.split(',')
                else:
                    pages_str_ex = [pages_str]
                for p_str in pages_str_ex:
                    try:
                        act_p = int(float(p_str))
                    except:
                        act_p = None
                    if act_p is not None:
                        pages.append(act_p)
                if len(pages) > 0:
                    link_sort = 100
                    for man_tb in unit_uuid_tb_objs[unit_uuid]:
                        if len(man_tb.page_range) > 0:
                            link_sort += 0.1
                            for page in pages:
                                if page >= min(man_tb.page_range) and page <= max(man_tb.page_range):
                                    link_sort += 0.001
                                    print('found match with: ' + man_tb.label + ' for pages: ' + pages_str)
                                    new_ass = Assertion()
                                    new_ass.uuid = uuid
                                    new_ass.subject_type = 'subjects'
                                    new_ass.project_uuid = man_tb.project_uuid
                                    new_ass.source_id = source_id + '-code'
                                    new_ass.obs_node = '#obs-1'
                                    new_ass.obs_num = 1
                                    new_ass.sort = link_sort
                                    new_ass.visibility = 1
                                    new_ass.predicate_uuid = 'f20e9e2e-246f-4421-b1dd-e31e8b58805c'
                                    new_ass.object_type = 'documents'
                                    new_ass.object_uuid = man_tb.uuid
                                    try:
                                        new_ass.save()
                                    except:
                                        pass
                                    
    


# imported cleaned HTML text to a set of cached (from the old website) trench book entries                            
from opencontext_py.apps.imports.poggiociv.tbentries import PoggioCivTrenchBookEntries
pctb = PoggioCivTrenchBookEntries()
pctb.pc_directory = 'mag-data'
pctb.pc.pc_directory = 'mag-data'
items = [
{'uuid': '23d75823-b8b3-4c9b-a982-9ef441c15423', 'file': 'viewtrenchbookentry---tbtdid-6146--tbtid-227.html' },
{'uuid': '7f6fb097-eb1d-4059-867f-3e3f5184d293', 'file': 'viewtrenchbookentry---tbtdid-6147--tbtid-227.html' },
{'uuid': '0d8e87d5-1b7a-4d1b-998e-5caac50fed00', 'file': 'viewtrenchbookentry---tbtdid-6149--tbtid-227.html' },
{'uuid': '21a02313-638e-45ae-ba59-072480a1483d', 'file': 'viewtrenchbookentry---tbtdid-6153--tbtid-227.html' },
{'uuid': '4feaba6c-d6fb-4ac2-9cb6-51f122d5094f', 'file': 'viewtrenchbookentry---tbtdid-6158--tbtid-227.html' },
{'uuid': 'e93ef4e1-a381-4251-a9e5-3d651d46c331', 'file': 'viewtrenchbookentry---tbtdid-6159--tbtid-227.html' },
{'uuid': 'e62d379b-20e5-4f70-b60a-2378903278e5', 'file': 'viewtrenchbookentry---tbtdid-6651--tbtid-227.html' },
{'uuid': 'c5918cae-3fd8-43d0-bc96-a6c520a309cf', 'file': 'viewtrenchbookentry---tbtdid-6653--tbtid-227.html' },
{'uuid': '74426cf7-855e-4fd1-a15d-2161576aa9ce', 'file': 'viewtrenchbookentry---tbtdid-6654--tbtid-227.html' },
{'uuid': 'f2fe67cd-70d2-4054-af97-e09d4a337907', 'file': 'viewtrenchbookentry---tbtdid-6732--tbtid-227.html' },
{'uuid': '27f7ea4b-9104-453f-bcf8-a667d6b23dd9', 'file': 'viewtrenchbookentry---tbtdid-6735--tbtid-227.html' },
{'uuid': '057e4c93-4ecc-4a3f-b4dc-67dec3a0d9e8', 'file': 'viewtrenchbookentry---tbtdid-7104--tbtid-227.html' },
{'uuid': '4ef19a87-2114-4e5c-b09c-e036030f3525', 'file': 'viewtrenchbookentry---tbtdid-7106--tbtid-227.html' },
{'uuid': '6f3a653a-65a8-4c5e-bf69-16872c91458d', 'file': 'viewtrenchbookentry---tbtdid-7107--tbtid-227.html' },
{'uuid': '3130cba3-0c2b-427a-a024-72f19229a8fa', 'file': 'viewtrenchbookentry---tbtdid-7108--tbtid-227.html' },
{'uuid': '0d2fd4dc-d3ad-4df1-b6fb-57df385bebb7', 'file': 'viewtrenchbookentry---tbtdid-7109--tbtid-227.html' },
{'uuid': '930ec37e-d8bd-41d8-a252-60231263cd39', 'file': 'viewtrenchbookentry---tbtdid-7110--tbtid-227.html' },
{'uuid': 'a2f32522-ce9e-475e-9bb8-25413e3c3de6', 'file': 'viewtrenchbookentry---tbtdid-7111--tbtid-227.html' }
]
for item in items:
    pctb.clean_file_by_uuid(item['uuid'], item['file'])

# added some data to the trench book entries
from opencontext_py.apps.ocitems.assertions.models import Assertion
items = [
{'uuid': '23d75823-b8b3-4c9b-a982-9ef441c15423', 'file': 'viewtrenchbookentry---tbtdid-6146--tbtid-227.html' },
{'uuid': '7f6fb097-eb1d-4059-867f-3e3f5184d293', 'file': 'viewtrenchbookentry---tbtdid-6147--tbtid-227.html' },
{'uuid': '0d8e87d5-1b7a-4d1b-998e-5caac50fed00', 'file': 'viewtrenchbookentry---tbtdid-6149--tbtid-227.html' },
{'uuid': '21a02313-638e-45ae-ba59-072480a1483d', 'file': 'viewtrenchbookentry---tbtdid-6153--tbtid-227.html' },
{'uuid': '4feaba6c-d6fb-4ac2-9cb6-51f122d5094f', 'file': 'viewtrenchbookentry---tbtdid-6158--tbtid-227.html' },
{'uuid': 'e93ef4e1-a381-4251-a9e5-3d651d46c331', 'file': 'viewtrenchbookentry---tbtdid-6159--tbtid-227.html' },
{'uuid': 'e62d379b-20e5-4f70-b60a-2378903278e5', 'file': 'viewtrenchbookentry---tbtdid-6651--tbtid-227.html' },
{'uuid': 'c5918cae-3fd8-43d0-bc96-a6c520a309cf', 'file': 'viewtrenchbookentry---tbtdid-6653--tbtid-227.html' },
{'uuid': '74426cf7-855e-4fd1-a15d-2161576aa9ce', 'file': 'viewtrenchbookentry---tbtdid-6654--tbtid-227.html' },
{'uuid': 'f2fe67cd-70d2-4054-af97-e09d4a337907', 'file': 'viewtrenchbookentry---tbtdid-6732--tbtid-227.html' },
{'uuid': '27f7ea4b-9104-453f-bcf8-a667d6b23dd9', 'file': 'viewtrenchbookentry---tbtdid-6735--tbtid-227.html' },
{'uuid': '057e4c93-4ecc-4a3f-b4dc-67dec3a0d9e8', 'file': 'viewtrenchbookentry---tbtdid-7104--tbtid-227.html' },
{'uuid': '4ef19a87-2114-4e5c-b09c-e036030f3525', 'file': 'viewtrenchbookentry---tbtdid-7106--tbtid-227.html' },
{'uuid': '6f3a653a-65a8-4c5e-bf69-16872c91458d', 'file': 'viewtrenchbookentry---tbtdid-7107--tbtid-227.html' },
{'uuid': '3130cba3-0c2b-427a-a024-72f19229a8fa', 'file': 'viewtrenchbookentry---tbtdid-7108--tbtid-227.html' },
{'uuid': '0d2fd4dc-d3ad-4df1-b6fb-57df385bebb7', 'file': 'viewtrenchbookentry---tbtdid-7109--tbtid-227.html' },
{'uuid': '930ec37e-d8bd-41d8-a252-60231263cd39', 'file': 'viewtrenchbookentry---tbtdid-7110--tbtid-227.html' },
{'uuid': 'a2f32522-ce9e-475e-9bb8-25413e3c3de6', 'file': 'viewtrenchbookentry---tbtdid-7111--tbtid-227.html' }
]
prev_uuid = None
project_uuid = 'DF043419-F23B-41DA-7E4D-EE52AF22F92F'
source_id = 'mt-v-linking'
i = 0
for item in items:
    i += .001
    new_ass = Assertion()
    new_ass.uuid = item['uuid']
    new_ass.subject_type = 'documents'
    new_ass.project_uuid = project_uuid
    new_ass.source_id = source_id
    new_ass.obs_node = '#obs-1'
    new_ass.obs_num = 1
    new_ass.sort = 1
    new_ass.visibility = 1
    new_ass.predicate_uuid = 'oc-28' # author
    new_ass.object_type = 'persons'
    new_ass.object_uuid = 'ac410704-d889-433b-9528-d27f8d5c0e27' # tb entry
    new_ass.save()
    
    
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.ocitems.subjects.models import Subject
from opencontext_py.apps.ocitems.assertions.models import Assertion

project_uuid = 'DF043419-F23B-41DA-7E4D-EE52AF22F92F'
class_list = [
    'oc-gen:cat-object',
    'oc-gen:cat-arch-element',
    'oc-gen:cat-glass',
    'oc-gen:cat-pottery',
    'oc-gen:cat-coin'
]
man_list = Manifest.objects\
                   .filter(item_type='subjects',
                           project_uuid=project_uuid,
                           class_uri__in=class_list)
check_uuids = []
for man_obj in man_list:
    year_ok = True
    sub_obj = Subject.objects.get(uuid=man_obj.uuid)
    year_str = man_obj.label.replace('PC', '')
    year_str = year_str.replace('VdM', '')
    year_str = year_str.replace(' ', '')
    year_str = year_str[0:4]
    try:
        year_num = int(float(year_str))
        year_ok = True
    except:
        year_ok = False
    context_path = sub_obj.context.replace('/' + man_obj.label, '')
    if year_ok and year_str not in context_path and 'Unrecorded' not in context_path and 'Not Applicable' not in context_path:
        check_uuids.append(man_obj.uuid)
        print('No ' + year_str + ' in ' +  context_path )



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


# add links to specialist records to pictures if the related catalog
# item has pitures
from opencontext_py.apps.ocitems.assertions.models import Assertion
from opencontext_py.apps.entities.entity.models import Entity
has_sp_des_pred = '7c053560-2385-43af-af11-6e58afdbeb10'
sp_note_pred = 'b019efa8-c67a-4641-9340-b667ab73d498'
sp_pred_asses = Assertion.objects.filter(predicate_uuid=has_sp_des_pred)
source_id = 'catalog-media-copy'
for ass in sp_pred_asses:
    uuid = ass.uuid
    specialist_uuid = ass.object_uuid
    specialist_type = ass.object_type
    media_asses = Assertion.objects\
                           .filter(uuid=uuid,
                                   object_type='media')
    if len(media_asses) > 0:
        print('Has media: ' + str(len(media_asses)))
        for media_ass in media_asses:
            new_ass = Assertion()
            new_ass.uuid = specialist_uuid
            new_ass.subject_type = specialist_type
            new_ass.project_uuid = ass.project_uuid
            new_ass.source_id = source_id
            new_ass.obs_node = '#obs-1'
            new_ass.obs_num = 1
            new_ass.sort = media_ass.sort
            new_ass.visibility = 1
            new_ass.predicate_uuid = 'oc-3' # author
            new_ass.object_type = media_ass.object_type
            new_ass.object_uuid = media_ass.object_uuid
            try:
                new_ass.save()
            except:
                pass



# fix over-escaped appostrophes in document content
from opencontext_py.apps.ocitems.documents.models import OCdocument
oc_docs = OCdocument.objects.all()
for oc_doc in oc_docs:
    content = oc_doc.content
    content = content.replace('\\\'s', '\'s')
    content = content.replace('\\\'s', '\'s')
    content = content.replace('\\\'s', '\'s')
    content = content.replace('\\\'s', '\'s')
    content = content.replace('\\\'s', '\'s')
    content = content.replace('\\\'s', '\'s')
    content = content.replace('\\\'s', '\'s')
    content = content.replace('\\\'s', '\'s')
    oc_doc.content = content
    oc_doc.save()




# fix id prefixes for objects from Vescovado
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.ocitems.subjects.models import Subject
from opencontext_py.apps.ocitems.geospace.models import Geospace

project_uuid = 'DF043419-F23B-41DA-7E4D-EE52AF22F92F'
class_list = [
    'oc-gen:cat-object',
    'oc-gen:cat-arch-element',
    'oc-gen:cat-glass',
    'oc-gen:cat-pottery',
    'oc-gen:cat-coin'
]
man_list = Manifest.objects\
                   .filter(item_type='subjects',
                           project_uuid=project_uuid,
                           class_uri__in=class_list)
check_uuids = []
for man_obj in man_list:
    sub_obj = Subject.objects.get(uuid=man_obj.uuid)
    if 'Vescovado' in sub_obj.context and 'VdM' not in man_obj.label:
        print('Object from Vescovado:' + sub_obj.context)
        id_str = man_obj.label.replace('PC', '')
        id_str = id_str.replace(' ', '')
        new_label = 'VdM ' + id_str
        old_label = man_obj.label
        sub_obj.context = sub_obj.context.replace('/' + old_label, '/' + new_label)
        sub_obj.save()
        man_obj.label = new_label
        man_obj.save()
        
 
# remove erroneous location data for vescovado
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.ocitems.subjects.models import Subject
from opencontext_py.apps.ocitems.geospace.models import Geospace
from opencontext_py.apps.indexer.reindex import SolrReIndex

project_uuid = 'DF043419-F23B-41DA-7E4D-EE52AF22F92F'
class_list = [
    'oc-gen:cat-object',
    'oc-gen:cat-arch-element',
    'oc-gen:cat-glass',
    'oc-gen:cat-pottery',
    'oc-gen:cat-coin'
]
man_list = Manifest.objects\
                   .filter(item_type='subjects',
                           project_uuid=project_uuid,
                           class_uri__in=class_list)
uuids = []
geo_sources = {}
for man_obj in man_list:
    sub_obj = Subject.objects.get(uuid=man_obj.uuid)
    geos = Geospace.objects\
                   .filter(uuid=man_obj.uuid)
    for geo in geos:
        if geo.source_id not in geo_sources:
            geo_sources[geo.source_id] = 0
        geo_sources[geo.source_id] += 1



print('Items to index: ' + str(len(uuids)))
sri = SolrReIndex()
sri.reindex_uuids(uuids)
        

# add millimeters to the units of measurements for zooarch decimal attributes        
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.ldata.linkannotations.models import LinkAnnotation
from opencontext_py.apps.ocitems.predicates.models import Predicate

project_uuid = 'DF043419-F23B-41DA-7E4D-EE52AF22F92F'
preds = Predicate.objects\
                 .filter(project_uuid=project_uuid,
                         data_type='xsd:double')
for pred in preds:
    man_obj = False
    man_obj = Manifest.objects.get(uuid=pred.uuid)
    if man_obj.source_id == 'ref:1770225443483' or man_obj.source_id == 'ref:1667718581590':
        # save also that the unit of measurement is in MM
        la = LinkAnnotation()
        la.subject = man_obj.uuid  # the subordinate is the subject
        la.subject_type = man_obj.item_type
        la.project_uuid = man_obj.project_uuid
        la.source_id = 'label-match'
        la.predicate_uri = 'http://www.w3.org/2000/01/rdf-schema#range'
        la.object_uri = 'http://www.wikidata.org/wiki/Q174789'
        try:
            la.save()
        except:
            pass


# url search and replace
from opencontext_py.apps.ocitems.strings.models import OCstring
bad_url = 'http://poggiocivitate.classics.umass.edu'
good_url = 'http://www.poggiocivitate.org'
b_strs = OCstring.objects.filter(content__contains=bad_url)
for b_str in b_strs:
    b_str.content = b_str.content.replace(bad_url, good_url)
    b_str.save()




# add images to internet archive for IIIF serving
from opencontext_py.apps.ocitems.mediafiles.models import Mediafile
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.ocitems.mediafiles.internetarchive import InternetArchiveMedia
ia_m = InternetArchiveMedia()
ia_m.noindex = False
ia_m.save_db = True
ia_m.remote_uri_sub = 'https://artiraq.org/static/opencontext/seyitomer-hoyuk/'
ia_m.local_uri_sub = 'http://127.0.0.1:8000/static/exports/seyitomer-hoyuk/'
ia_m.project_uuids.append('347286db-b6c6-4fd2-b3bd-b50316b0cb9f')
ia_m.delay_before_request = .25
ia_m.archive_image_media_items()
ia_m.errors












# reindex
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.indexer.reindex import SolrReIndex
project_uuid = '347286db-b6c6-4fd2-b3bd-b50316b0cb9f'
uuids = []
items = Manifest.objects.filter(project_uuid=project_uuid).order_by('sort')
for item in items:
    uuids.append(item.uuid)

print('Items to index: ' + str(len(uuids)))
sri = SolrReIndex()
sri.reindex_uuids(uuids)



from opencontext_py.libs.filecache import FileCacheJSON
from opencontext_py.libs.waybackup import WaybackUp
from opencontext_py.apps.imports.poggiociv.tbentries import PoggioCivTrenchBookEntries
pctb = PoggioCivTrenchBookEntries()
wb = WaybackUp()
wb.filecache = FileCacheJSON()
wb.cache_filekey = 'poggio-civitate-crawl'
wb.delay_before_request = .5
wb.do_img_src = True
wb.transform_href_obj = pctb
path = ['poggiocivitate.org']  # only follow links in these paths
url = 'http://www.poggiocivitate.org/catalog/trenchbooks/'
wb.scrape_urls(url, path, 10)  # archive pages discovered from the url, going 6 steps away
wb.urls = wb.failed_urls
# archive the previous failures
wb.archive_urls()


from opencontext_py.libs.filecache import FileCacheJSON
from opencontext_py.libs.waybackup import WaybackUp
wb = WaybackUp()
wb.filecache = FileCacheJSON()
wb.cache_filekey = 'ascsa-crawl'
wb.delay_before_request = 1
wb.do_img_src = True
path = ['ascsa.net/']  # only follow links in these paths
url = 'http://ascsa.net/research?v=default'
wb.scrape_urls(url, path, 10)  # archive pages discovered from the url, going 6 steps away
wb.urls = wb.failed_urls
# archive the previous failures
wb.archive_urls()





# poggio civitate assertion sorting
from opencontext_py.apps.ocitems.assertions.sorting import AssertionSorting
asor = AssertionSorting()
asor.sort_ranked_manifest_for_project('DF043419-F23B-41DA-7E4D-EE52AF22F92F')



from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.ocitems.assertions.models import Assertion
from opencontext_py.apps.ocitems.geospace.models import Geospace
from opencontext_py.apps.ocitems.subjects.models import Subject
project_uuid = '766698E3-2E79-4A78-B0BC-245FF435BBBD'
class_uri = 'oc-gen:cat-site'
bad_source_id = "z_13_41b22b176"
good_source_id = "ref:2215904997131"
del_uuids = []
bad_mans = Manifest.objects.filter(project_uuid=project_uuid,
                                   class_uri=class_uri,
                                   source_id=bad_source_id)
for bad_man in bad_mans:
    new_asses = Assertion.objects\
                         .filter(uuid=bad_man.uuid,
                                 source_id=good_source_id)
    if len(new_asses) < 1:
        # item doesn't have a new description, so it is to be removed
        del_uuids.append(bad_man.uuid)


for del_uuid in del_uuids:
    Assertion.objects.filter(uuid=del_uuid).delete()
    Assertion.objects.filter(object_uuid=del_uuid).delete()
    Subject.objects.filter(uuid=del_uuid).delete()
    Geospace.objects.filter(uuid=del_uuid).delete()
    Manifest.objects.filter(uuid=del_uuid).delete()


from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.ocitems.assertions.models import Assertion
from opencontext_py.apps.ocitems.geospace.models import Geospace
from opencontext_py.apps.ocitems.subjects.models import Subject
project_uuid = 'EDDA846F-7225-495E-AB77-7314C256449A'
class_uri = 'oc-gen:cat-site'
bad_source_id = "z_12_d23b6cd17"
good_source_id = "ref:2505863900014"
del_uuids = []
bad_mans = Manifest.objects.filter(project_uuid=project_uuid,
                                   class_uri=class_uri,
                                   source_id=bad_source_id)
for bad_man in bad_mans:
    new_asses = Assertion.objects\
                         .filter(uuid=bad_man.uuid,
                                 source_id=good_source_id)
    if len(new_asses) < 1:
        # item doesn't have a new description, so it is to be removed
        del_uuids.append(bad_man.uuid)


for del_uuid in del_uuids:
    Assertion.objects.filter(uuid=del_uuid).delete()
    Assertion.objects.filter(object_uuid=del_uuid).delete()
    Subject.objects.filter(uuid=del_uuid).delete()
    Geospace.objects.filter(uuid=del_uuid).delete()
    Manifest.objects.filter(uuid=del_uuid).delete()



# reindex
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.indexer.reindex import SolrReIndex
project_uuids = [
    'EDDA846F-7225-495E-AB77-7314C256449A',
    '766698E3-2E79-4A78-B0BC-245FF435BBBD',
    'DF043419-F23B-41DA-7E4D-EE52AF22F92F'
]
uuids = []
items = Manifest.objects.filter(project_uuid__in=project_uuids).exclude(indexed__gt='2018-10-03').order_by('sort')
for item in items:
    uuids.append(item.uuid)

print('Items to index: ' + str(len(uuids)))
sri = SolrReIndex()
sri.reindex_uuids(uuids)


from opencontext_py.apps.ocitems.assertions.models import Assertion

type_uuid = 'a2879621-39eb-49b5-be7b-a4c5a5604dc8'
uuids = [
    type_uuid
]
l_asses = Assertion.objects.filter(object_uuid=type_uuid)
for l_ass in l_asses:
    if l_ass.uuid not in uuids:
        uuids.append(l_ass.uuid)




from opencontext_py.libs.solrconnection import SolrConnection
solr = SolrConnection().connection
# Open Context (Google) Solr Delete
project_uuids = [
    'EDDA846F-7225-495E-AB77-7314C256449A',
    '766698E3-2E79-4A78-B0BC-245FF435BBBD',
    'DF043419-F23B-41DA-7E4D-EE52AF22F92F'
]
for project_uuid in project_uuids:
    q = 'project_uuid:' + project_uuid
    solr.delete_by_query(q)



from opencontext_py.apps.ocitems.projects.permissions import ProjectPermissions
project_uuids = [
    'EDDA846F-7225-495E-AB77-7314C256449A',
    '766698E3-2E79-4A78-B0BC-245FF435BBBD'
]
for project_uuid in project_uuids:
    pp = ProjectPermissions()
    pp.publish_project(project_uuid)
