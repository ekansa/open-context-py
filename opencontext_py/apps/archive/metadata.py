from django.conf import settings
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.apps.entities.entity.models import Entity
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.ocitems.persons.models import Person
from opencontext_py.apps.ocitems.projects.models import Project


class ArchiveMetadata():
    """
    Methods to make archive metadata objects
    
    """
    
    def __init__(self):
        pass
    
    def make_zenodo_creator_list(self, meta_dict):
        """ makes a list of creators that conform to the Zenodo model """
        zendo_list = []
        id_list = []
        objs_w_order = []
        cite_preds = [
            'dc-terms:contributor',
            'dc-terms:creator',
        ]
        all_order = 0
        list_order = 0
        max_count = 1
        for cite_pred in cite_preds:
            if cite_pred in meta_dict:
                for obj_dict in meta_dict[cite_pred]:
                    if 'count' in obj_dict:
                        if obj_dict['count'] > max_count:
                            max_count = obj_dict['count']
        pred_adder = 0
        for cite_pred in cite_preds:
            pred_adder += max_count
            if cite_pred in meta_dict:
                for obj_dict in meta_dict[cite_pred]:
                    act_id = obj_dict['id']
                    if act_id not in id_list:
                        id_list.append(act_id)
                        list_order = (len(id_list)) + pred_adder
                        if 'count' in obj_dict:
                            # count is useful for bulk uploads of several media items
                            # these may have many creators, so the creaters referenced
                            # the most frequently will appear hgi
                            all_order = list_order + (max_count - obj_dict['count'])
                        else:
                            all_order = list_order
                        obj_w_order = (obj_dict, all_order)
                        objs_w_order.append(obj_w_order)
        ordered_objs = sorted(objs_w_order, key=lambda x: x[1])
        for obj_w_order in ordered_objs:
            obj_dict = obj_w_order[0]
            obj_dict = self.add_person_names_to_obj(obj_dict)
            zenodo_obj = {}
            zenodo_obj['name'] = obj_dict['family_given_name']
            if 'foaf:isPrimaryTopicOf' in obj_dict:
                zenodo_obj['orcid'] = obj_dict['foaf:isPrimaryTopicOf']
            else:
                zenodo_obj['affiliation'] = 'Open Context URI: ' + obj_dict['id']
            zendo_list.append(zenodo_obj)
        return zendo_list
    
    def add_person_names_to_obj(self, obj_dict, default_to_label=True):
        """ adds person names to a JSON-LD object dict """
        obj_dict['family_given_name'] = None
        if 'id' in obj_dict:
            act_id = obj_dict['id']
        elif '@id' in obj_dict:
            act_id = obj_dict['@id']
        else:
            act_id = None
        if default_to_label:
            if 'label' in obj_dict:
                if isinstance(obj_dict['label'], str):
                     obj_dict['family_given_name'] = obj_dict['label']
        if isinstance(act_id, str):
            ent = Entity()
            found = ent.dereference(act_id)
            if found:
                obj_dict['family_given_name'] = ent.label
                if ent.item_type == 'persons':
                    surname = ''
                    given_name = ''
                    try:
                        pers = Person.objects.get(uuid=ent.uuid)
                    except Person.DoesNotExist:
                        pers = None
                    if pers is not None:
                        if isinstance(pers.surname, str):
                            if len(pers.surname.strip()) > 0:
                                surname = pers.surname.strip()
                                if isinstance(pers.given_name, str):
                                    if len(pers.given_name.strip()) > 0:
                                        given_name = pers.given_name.strip()
                                        obj_dict['family_given_name'] = surname + ', ' + given_name
                                        if isinstance(pers.mid_init, str):
                                            if len(pers.mid_init.strip()) > 0:
                                                obj_dict['family_given_name'] += ' ' + pers.mid_init.strip()
        return obj_dict
                    
        
