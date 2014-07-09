import json
import copy
from django.conf import settings
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.libs.globalmaptiles import GlobalMercator
from opencontext_py.apps.entities.uri.models import URImanagement
from opencontext_py.apps.entities.entity.models import Entity
from opencontext_py.apps.ocitems.namespaces.models import ItemNamespaces
from opencontext_py.apps.ocitems.ocitem.models import OCitem


# Help organize the code, with a class to make templating easier
class TemplateItem():
    """ This class makes an object useful for templating, since
    the JSON-LD object can't be read by the django template system """

    def __init__(self):
        self.label = False
        self.uuid = False
        self.id = False
        self.context = False
        self.children = False
        self.observations = False
        self.class_type_metadata = {}

    def read_jsonld_dict(self, json_ld):
        """ Reads JSON-LD dict object to make a TemplateItem object
        """
        self.label = json_ld['label']
        self.uuid = json_ld['uuid']
        self.id = json_ld['id']
        self.store_class_type_metadata(json_ld)
        self.create_context(json_ld)
        self.create_children(json_ld)
        self.create_observations(json_ld)

    def create_context(self, json_ld):
        """
        Adds context object if json_ld describes such
        """
        act_context = Context()
        act_context.make_context(json_ld, self.class_type_metadata)
        if(act_context.contype is not False):
            self.context = act_context

    def create_children(self, json_ld):
        """
        Adds children object if json_ld describes such
        """
        act_children = Children()
        act_children.make_children(json_ld, self.class_type_metadata)
        if(act_children.children is not False):
            self.children = act_children

    def create_observations(self, json_ld):
        """
        Adds observation objects if json_ld describes such
        """
        if(OCitem.PREDICATES_OCGEN_HASOBS in json_ld):
            context = json_ld['@context']
            self.observations = []
            for obs_item in json_ld[OCitem.PREDICATES_OCGEN_HASOBS]:
                act_obs = Observation()
                act_obs.make_observation(context, obs_item, self.class_type_metadata)
                self.observations.append(act_obs)

    def store_class_type_metadata(self, json_ld):
        if('@graph' in json_ld):
            for g_anno in json_ld['@graph']:
                identifier = False
                if('@id' in g_anno):
                    identifier = g_anno['@id']
                elif('id' in g_anno):
                    identifier = g_anno['id']
                if('oc-gen:' in identifier):
                    meta = {}
                    if('label' in g_anno):
                        meta['typelabel'] = g_anno['label']
                    if('oc-gen:hasIcon' in g_anno):
                        meta['icon'] = g_anno['oc-gen:hasIcon'][0]['id']
                    self.class_type_metadata[identifier] = meta


class ItemMetadata():
    """ Class has some methods to add metadata to items """
    def get_item_type(item):
        """ Gets the item type from an item, accepts '@type' or 'type' predicates """
        item_type = False
        if('@type' in item):
            item_type = item['@type']
        elif('type' in item):
            item_type = item['type']
        return item_type

    def get_class_meta(item, class_type_metadata):
        item['typelabel'] = False
        item['icon'] = False
        if('type' in item):
            if(item['type'] in class_type_metadata):
                meta = class_type_metadata[item['type']]
                for key, value in meta.items():
                    item[key] = value
        return item


class Context():
    """ This class makes an object useful for templating
    describing context of items"""
    def __init__(self):
        self.id = False
        self.contype = False
        self.parents = False

    def make_context(self, json_ld, class_type_metadata):
        """ makes contexts for use with the template """
        act_context = False
        if(OCitem.PREDICATES_OCGEN_HASCONTEXTPATH in json_ld):
            self.contype = 'Context'
            act_context = json_ld[OCitem.PREDICATES_OCGEN_HASCONTEXTPATH]
        elif(OCitem.PREDICATES_OCGEN_HASLINKEDCONTEXTPATH in json_ld):
            self.contype = 'Context of related item'
            act_context = json_ld[OCitem.PREDICATES_OCGEN_HASLINKEDCONTEXTPATH]
        if(act_context is not False):
            self.id = act_context['id']
            self.parents = []
            if(OCitem.PREDICATES_OCGEN_HASPATHITEMS in act_context):
                for parent_item in act_context[OCitem.PREDICATES_OCGEN_HASPATHITEMS]:
                    act_parent = {}
                    act_parent['uri'] = parent_item['id']
                    act_parent['label'] = parent_item['label']
                    act_parent['type'] = ItemMetadata.get_item_type(parent_item)
                    act_parent['uuid'] = URImanagement.get_uuid_from_oc_uri(parent_item['id'])
                    act_parent = ItemMetadata.get_class_meta(act_parent, class_type_metadata)
                    self.parents.append(act_parent)


class Children():
    """ This class makes an object useful for templating
    describing children of items"""
    def __init__(self):
        self.id = False
        self.children = False

    def make_children(self, json_ld, class_type_metadata):
        """ makes contexts for use with the template """
        act_children = False
        if(OCitem.PREDICATES_OCGEN_HASCONTENTS in json_ld):
            self.contype = 'Context'
            act_children = json_ld[OCitem.PREDICATES_OCGEN_HASCONTENTS]
            self.id = act_children['id']
            self.children = []
            for child_item in act_children[OCitem.PREDICATES_OCGEN_CONTAINS]:
                act_child = {}
                act_child['uri'] = child_item['id']
                act_child['label'] = child_item['label']
                act_child['type'] = ItemMetadata.get_item_type(child_item)
                act_child['uuid'] = URImanagement.get_uuid_from_oc_uri(child_item['id'])
                act_child = ItemMetadata.get_class_meta(act_child, class_type_metadata)
                self.children.append(act_child)


class Observation():
    """ This class makes an object useful for templating
    describing descriptive properties and links for items"""

    def __init__(self):
        self.context = False
        self.id = False
        self.source_id = False
        self.obs_status = False
        self.properties = False
        self.subjects_links = False
        self.media_links = False
        self.persons_links = False
        self.documents_links = False

    def make_observation(self, context, obs_dict, class_type_metadata):
        """ Makes an observation with some observation metadata
            property list, links to subjects items, links to media items,
            links to persons items, and links to documents
        """
        self.context = context
        self.id = obs_dict['id'].replace('#', '')
        self.source_id = obs_dict[OCitem.PREDICATES_OCGEN_SOURCEID]
        self.obs_status = obs_dict[OCitem.PREDICATES_OCGEN_OBSTATUS]
        self.properties = self.make_properties(obs_dict)

    def make_properties(self, obs_dict):
        """ Makes property objects for an observation
        """
        properties = False
        for key, item in obs_dict.items():
            if(key != 'id' and key in self.context):
                if(OCitem.PREDICATES_OCGEN_PREDICATETYPE in self.context[key]):
                    if(self.context[key][OCitem.PREDICATES_OCGEN_PREDICATETYPE] == 'variable'):
                        if(properties is False):
                            properties = []
                        act_prop = Property()
                        act_prop.start_property(self.context[key])
                        act_prop.add_property_values(obs_dict[key])
                        properties.append(act_prop)
        return properties


class Property():
    """ This class makes an object useful for templating
    a property which has a variable predicate with one or more values"""

    def __init__(self):
        self.varlabel = False
        self.varuri = False
        self.varslug = False
        self.values = False

    def start_property(self, predicate_info):
        """ Starts a property with metadata about the variable
        """
        self.varlabel = predicate_info['label']
        self.varuri = predicate_info['owl:sameAs']
        self.varslug = predicate_info['slug']

    def add_property_values(self, prop_vals):
        """ Starts a property with metadata about the variable
        """
        self.values = []
        for val_item in prop_vals:
            act_prop_val = PropValue()
            act_prop_val.make_value(val_item)
            self.values.append(act_prop_val)


class PropValue():
    """ This class makes an object useful for templating
    a property value"""

    def __init__(self):
        self.valtype = False
        self.valuri = False
        self.val = False
        self.valid = False
        self.valuuid = False

    def make_value(self, val_item):
        if isinstance(val_item, dict):
            if('id' in val_item):
                if(val_item['id'][:7] == 'http://' or val_item['id'][:8] == 'https://'):
                    self.valuri = val_item['id']
                    uri_item = URImanagement.get_uuid_from_oc_uri(val_item['id'], True)
                    self.valtype = uri_item['item_type']
                    self.valuuid = uri_item['uuid']
                else:
                    self.valid = val_item['id'].replace('#', '')
            if('label' in val_item):
                self.val = val_item['label']
            if('xsd:string' in val_item):
                self.val = val_item['xsd:string']
        else:
            self.val = val_item
