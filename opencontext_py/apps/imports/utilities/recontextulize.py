from opencontext_py.apps.imports.records.models import ImportCell
from opencontext_py.apps.ocitems.assertions.models import Assertion
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.ocitems.subjects.models import Subject
from opencontext_py.apps.ocitems.subjects.generation import SubjectGeneration


def recontextualize_import(
    project_uuid,
    child_class_uri,
    source_id,
    child_prefix,
    child_field,
    parent_prefix,
    parent_field,
    over_write_existing_context=True):
    """Adds context assertions to existing items in the manifest """ 
    mans = Manifest.objects\
                   .filter(item_type='subjects',
                           class_uri=child_class_uri,
                           source_id=source_id,
                           project_uuid=project_uuid)\
                   .order_by('sort')
    changed_uuids = []
    p_subs = {}
    for man_obj in mans:
        if over_write_existing_context:
            Assertion.objects.filter(predicate_uuid=Assertion.PREDICATES_CONTAINS,
                                     object_uuid=man_obj.uuid).delete()
            cont_asses = []
        else:
            cont_asses = Assertion.objects.filter(predicate_uuid=Assertion.PREDICATES_CONTAINS,
                                                  object_uuid=man_obj.uuid)[:1]
        if len(cont_asses):
            continue
        # need to fix missing context association
        changed_uuids.append(man_obj.uuid)
        act_id = man_obj.label.replace(child_prefix, '')
        ch_cell = ImportCell.objects.filter(source_id=source_id, record=act_id, field_num=child_field)[:1][0]
        par_cell = ImportCell.objects.get(source_id=source_id, field_num=parent_field, row_num=ch_cell.row_num)
        p_context = parent_prefix + par_cell.record
        print('Find Context: {} for {} import row: {}'.format(p_context, man_obj.label, ch_cell.row_num))
        if p_context not in p_subs:
            parent_sub = Subject.objects.get(context__endswith=p_context, project_uuid=project_uuid)
            p_subs[p_context] = parent_sub
        else:
            parent_sub = p_subs[p_context]
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
    return changed_uuids