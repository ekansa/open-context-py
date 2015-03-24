import json
import copy
import datetime
from django.conf import settings
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.libs.globalmaptiles import GlobalMercator
from opencontext_py.apps.entities.uri.models import URImanagement
from opencontext_py.apps.entities.entity.models import Entity
from opencontext_py.apps.ocitems.namespaces.models import ItemNamespaces
from opencontext_py.apps.ocitems.ocitem.models import OCitem
from opencontext_py.apps.ocitems.projects.models import Project as ModProject
from opencontext_py.apps.ocitems.projects.permissions import ProjectPermissions
from opencontext_py.apps.ldata.tdar.api import tdarAPI


# Help organize the code, with a class to make templating easier
class TemplateItem():
    """ This class makes an object useful for templating, since
    the JSON-LD object can't be read by the django template system """

    def __init__(self, request=False):
        self.label = False
        self.uuid = False
        self.id = False
        self.item_category_label = False
        self.context = False
        self.children = False
        self.observations = False
        self.obs_more_tab = 0
        self.class_type_metadata = {}
        self.project = False
        self.citation = False
        self.geo = False
        self.linked_data = False
        self.content = False
        self.nav_items = settings.NAV_ITEMS
        self.act_nav = False
        self.use_accordions = False
        self.item_linked_data = False
        self.item_dc_metadata = False
        self.request = request
        self.view_permitted = True  # defaults to allow views
        self.edit_permitted = False
        self.check_edit_permitted = False

    def read_jsonld_dict(self, json_ld):
        """ Reads JSON-LD dict object to make a TemplateItem object
        """
        self.uuid = json_ld['uuid']
        ent = Entity()
        found = ent.dereference(self.uuid)
        if found:
            self.act_nav = ent.item_type
        self.label = json_ld['label']
        self.id = json_ld['id']
        self.store_class_type_metadata(json_ld)
        self.create_project(json_ld)
        self.check_view_permission()
        if self.check_edit_permitted:
            self.check_edit_permission()
        self.create_context(json_ld)
        self.create_children(json_ld)
        self.create_linked_data(json_ld)
        self.create_observations(json_ld)
        self.create_citation(json_ld)
        self.create_geo(json_ld)
        self.create_content(json_ld)

    def create_context(self, json_ld):
        """
        Adds context object if json_ld describes such
        """
        act_context = Context()
        act_context.make_context(json_ld, self.class_type_metadata)
        if(act_context.type is not False):
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
        if self.act_nav == 'predicates':
            if self.observations is False:
                self.observations = []
            act_obs = Observation()
            act_obs.obs_num = len(self.observations) + 1
            act_obs.make_predicate_obs(json_ld)
            if act_obs.properties is not False:
                self.observations.append(act_obs)
        elif self.act_nav == 'types':
            if self.observations is False:
                self.observations = []
            act_obs = Observation()
            act_obs.obs_num = len(self.observations) + 1
            act_obs.make_type_obs(json_ld)
            if act_obs.properties is not False:
                self.observations.append(act_obs)
        if(OCitem.PREDICATES_OCGEN_HASOBS in json_ld):
            context = json_ld['@context'][1]
            if self.observations is False:
                self.observations = []
            for obs_item in json_ld[OCitem.PREDICATES_OCGEN_HASOBS]:
                obs_num = len(self.observations) + 1
                act_obs = Observation()
                act_obs.class_type_metadata = self.class_type_metadata
                act_obs.obs_num = obs_num
                act_obs.make_observation(context, obs_item)
                if act_obs.use_accordions:
                    self.use_accordions = True
                if obs_num == 1 and\
                   self.children is not False and\
                   (act_obs.properties is not False or\
                   act_obs.links is not False):
                    self.use_accordions = True
                if obs_num == 1 and\
                   (self.act_nav == 'media' or
                    self.act_nav == 'documents' or
                   self.act_nav == 'projects'):
                    self.use_accordions = True
                self.observations.append(act_obs)
            if len(self.linked_data.annotations) > 0:
                # make a special observation for linked data annotations
                act_obs = Observation()
                act_obs.class_type_metadata = self.class_type_metadata
                act_obs.make_linked_data_obs(self.linked_data.annotations)
                self.observations.append(act_obs)
        if self.item_linked_data is not False:
            # create an observation out of the item annoations
            if self.observations is False:
                self.observations = []
            act_obs = Observation()
            act_obs.obs_num = len(self.observations) + 1
            act_obs.make_item_annotation_obs(self.item_linked_data)
            if act_obs.annotations is not False:
                self.observations.append(act_obs)
        if self.item_dc_metadata is not False:
            # create an observation out of the item annoations
            if self.observations is False:
                self.observations = []
            act_obs = Observation()
            act_obs.obs_num = len(self.observations) + 1
            act_obs.make_item_dc_metadata_obs(self.item_dc_metadata)
            if act_obs.annotations is not False:
                self.observations.append(act_obs)
        if self.observations is not False:
            # for when to add a 'more' drop down list
            all_labels = ''
            obs_num = 1
            for obs in self.observations:
                # gap at end to approximate spacing between tabs
                all_labels += obs.label + '     '
                if len(all_labels) < 90:
                    self.obs_more_tab = obs_num
                obs_num += 1
            if len(all_labels) < 90:
                self.obs_more_tab += 1

    def create_project(self, json_ld):
        """ Makes an instance of a project class, with data from the JSON_LD
        """
        proj = Project()
        proj.item_type = self.act_nav
        if proj.item_type == 'projects':
            proj.uuid = self.uuid
        proj.make_project(json_ld)
        self.project = proj

    def check_view_permission(self):
        """ Checkes to see if viewing the item is permitted
        """
        if self.project is not False and self.request is not False:
            pp = ProjectPermissions(self.project.uuid)
            self.view_permitted = pp.view_allowed(self.request)

    def check_edit_permission(self):
        """ Checkes to see if editting the item is permitted
        """
        if self.project is not False and self.request is not False:
            pp = ProjectPermissions(self.project.uuid)
            self.edit_permitted = pp.edit_allowed(self.request)

    def create_citation(self, json_ld):
        """ Makes an instance of a citation class, with data from the JSON_LD
        """
        cite = Citation()
        cite.project = self.project
        cite.context = self.context
        cite.make_citation(json_ld)
        self.citation = cite

    def create_geo(self, json_ld):
        """ Makes an instance of a GeoMap class, with data from the JSON_LD
        """
        geo = GeoMap()
        geo.make_geomap(json_ld)
        self.geo = geo

    def create_linked_data(self, json_ld):
        """ Makes an instance of a GeoMap class, with data from the JSON_LD
        """
        linked_data = LinkedData()
        linked_data.project = self.project
        linked_data.make_linked_data(json_ld)
        self.linked_data = linked_data
        self.item_linked_data = linked_data.get_item_annotations(self.act_nav, json_ld)
        self.item_dc_metadata = linked_data.get_item_dc_metadata(self.act_nav, json_ld)

    def create_content(self, json_ld):
        """
        Gets various forms of content for media, documents, projects
        """
        if 'oc-gen:has-files' in json_ld:
            # content for media
            if self.content is False:
                self.content = {}
                self.content['fullfile'] = False
                self.content['preview'] = False
                self.content['thumbnail'] = False
            for file_item in json_ld['oc-gen:has-files']:
                if file_item['type'] == 'oc-gen:fullfile':
                    self.content['fullfile'] = file_item['id']
                elif file_item['type'] == 'oc-gen:preview':
                    self.content['preview'] = file_item['id']
                elif file_item['type'] == 'oc-gen:thumbnail':
                    self.content['thumbnail'] = file_item['id']
        elif 'rdf:HTML' in json_ld:
            # content for documents
            if self.content is False:
                self.content = {}
            self.content['main_text'] = json_ld['rdf:HTML']
        elif 'dc-terms:abstract' in json_ld:
            # content for project abstracts
            if self.content is False:
                self.content = {}
            self.content['main_text'] = json_ld['dc-terms:abstract']
        if 'description' in json_ld:
            # content for project descriptions
            if self.content is False:
                self.content = {}
            self.content['sum_text'] = json_ld['description']

    def store_class_type_metadata(self, json_ld):
        """ Stores information about classes / categories, including labels and icons
            needed for user inferface
        """
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
        if 'category' in json_ld:
            item_cat_labels = []
            for cat in json_ld['category']:
                if cat in self.class_type_metadata:
                    item_cat_labels.append(self.class_type_metadata[cat]['typelabel'])
            self.item_category_label = ', '.join(item_cat_labels)
        if self.item_category_label is False:
            # make sure the item has category label, if needed get from settings nav_items
            for nav_item in settings.NAV_ITEMS:
                if nav_item['key'] == self.act_nav:
                    self.item_category_label = nav_item['display']
                    break


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
        self.type = False
        self.parents = False
        self.parent_labels = []

    def make_context(self, json_ld, class_type_metadata):
        """ makes contexts for use with the template """
        act_context = False
        if(OCitem.PREDICATES_OCGEN_HASCONTEXTPATH in json_ld):
            self.type = 'context'
            act_context = json_ld[OCitem.PREDICATES_OCGEN_HASCONTEXTPATH]
        elif(OCitem.PREDICATES_OCGEN_HASLINKEDCONTEXTPATH in json_ld):
            self.type = 'related'
            act_context = json_ld[OCitem.PREDICATES_OCGEN_HASLINKEDCONTEXTPATH]
        if(act_context is not False):
            self.id = act_context['id']
            self.parents = []
            if(OCitem.PREDICATES_OCGEN_HASPATHITEMS in act_context):
                for parent_item in act_context[OCitem.PREDICATES_OCGEN_HASPATHITEMS]:
                    act_parent = {}
                    act_parent['uri'] = parent_item['id']
                    act_parent['label'] = parent_item['label']
                    act_parent['altlabel'] = None
                    act_parent['linkslug'] = None
                    act_parent['linklabel'] = None
                    act_parent['type'] = ItemMetadata.get_item_type(parent_item)
                    act_parent['uuid'] = URImanagement.get_uuid_from_oc_uri(parent_item['id'])
                    act_parent = ItemMetadata.get_class_meta(act_parent, class_type_metadata)
                    self.parents.append(act_parent)
                    self.parent_labels.append(act_parent['label'])


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
            if OCitem.PREDICATES_OCGEN_CONTAINS in act_children:
                self.id = act_children['id']
                self.children = []
                for child_item in act_children[OCitem.PREDICATES_OCGEN_CONTAINS]:
                    act_child = {}
                    act_child['uri'] = child_item['id']
                    act_child['label'] = child_item['label']
                    act_child['altlabel'] = None
                    act_child['linkslug'] = None
                    act_child['linklabel'] = None
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
        self.obs_num = 0
        self.label = False
        self.source_id = False
        self.obs_status = False
        self.obs_type = False
        self.properties = False
        self.links = False
        self.subjects_links = False
        self.media_links = False
        self.documents_links = False
        self.persons_links = False
        self.subjects_link_count = 0
        self.media_link_count = 0
        self.documents_link_count = 0
        self.persons_link_count = 0
        self.annotations = False
        self.dc_annotations = False
        self.item_annotations = False
        self.class_type_metadata = False
        self.use_accordions = False

    def make_item_dc_metadata_obs(self, item_metadata):
        """ Makes an observation with some metadata
            specifically for display of information related
            to predicates
        """
        self.id = 'item-metadata'
        self.source_id = 'project'
        self.obs_status = 'active'
        self.obs_type = 'contributor'
        self.label = 'Item Metadata'
        self.dc_annotations = True
        for item_anno in item_metadata:
            if self.annotations is False:
                self.annotations = []
            self.annotations.append(item_anno)

    def make_item_annotation_obs(self, item_annotations):
        """ Makes an observation with some metadata
            specifically for display of information related
            to predicates
        """
        self.id = 'item-annotations'
        self.source_id = 'project'
        self.obs_status = 'active'
        self.obs_type = 'contributor'
        self.label = 'Item Annotations'
        for item_anno in item_annotations:
            if self.annotations is False:
                self.annotations = []
            self.annotations.append(item_anno)

    def make_predicate_obs(self, json_ld):
        """ Makes an observation with some metadata
            specifically for display of information related
            to predicates
        """
        self.id = 'predicate-data'
        self.source_id = 'project'
        self.obs_status = 'active'
        self.obs_type = 'contributor'
        self.label = 'Description of this Property / Relation'
        if 'rdfs:range' in json_ld:
            range_values = []
            for rel_item in json_ld['rdfs:range']:
                act_val = PropValue()
                act_val.vartype = 'id'
                act_val.item_type = 'external-resource'
                act_val.uri = URImanagement.convert_prefix_to_full_uri(rel_item['id'])
                act_val.id = URImanagement.convert_prefix_to_full_uri(rel_item['id'])
                act_val.uuid = False
                act_val.val = rel_item['label']
                range_values.append(act_val)
            if self.properties is False:
                self.properties = []
            act_prop = Property()
            act_prop.varlabel = 'Range and type of values'
            act_prop.varuri = False
            act_prop.varslug = False
            act_prop.vartype = False
            act_prop.values = range_values
            self.properties.append(act_prop)

    def make_type_obs(self, json_ld):
        """ Makes an observation with some metadata
            specifically for display of information related
            to types
        """
        self.id = 'type-data'
        self.source_id = 'project'
        self.obs_status = 'active'
        self.obs_type = 'contributor'
        self.label = 'Description of this Category / Type'
        if 'skos:related' in json_ld:
            for rel_item in json_ld['skos:related']:
                if 'oc-pred:' in rel_item['id']:
                    if self.properties is False:
                        self.properties = []
                        act_prop = Property()
                        act_prop.varlabel = 'Related Property'
                        act_prop.varuri = False
                        act_prop.varslug = False
                        act_prop.vartype = False
                        act_prop.values = []
                        act_val = PropValue()
                        act_val.vartype = 'id'
                        act_val.item_type = 'predicates'
                        act_val.uri = rel_item['owl:sameAs']
                        act_val.id = rel_item['owl:sameAs']
                        act_val.uuid = URImanagement.get_uuid_from_oc_uri(rel_item['owl:sameAs'])
                        act_val.val = rel_item['label']
                        act_prop.values.append(act_val)
                        self.properties.append(act_prop)

    def make_linked_data_obs(self, annotations):
        """ Makes an observation with some metadata
            specifically for display of linked data
        """
        self.id = 'linked-data'
        self.source_id = 'oc-editors'
        self.obs_status = 'active'
        self.obs_type = 'annotations'
        self.label = 'Standards Annotations'
        self.annotations = annotations

    def make_observation(self, context, obs_dict):
        """ Makes an observation with some observation metadata
            property list, links to subjects items, links to media items,
            links to persons items, and links to documents
        """
        self.context = context
        self.id = obs_dict['id'].replace('#', '')
        self.source_id = obs_dict[OCitem.PREDICATES_OCGEN_SOURCEID]
        self.obs_status = obs_dict[OCitem.PREDICATES_OCGEN_OBSTATUS]
        self.obs_type = 'contributor'
        if OCitem.PREDICATES_OCGEN_OBSLABEL in obs_dict:
            self.label = obs_dict[OCitem.PREDICATES_OCGEN_OBSLABEL]
        else:
            if self.obs_num < 2:
                self.label = 'Main Observation'
            else:
                self.label = 'Obs (' + str(self.obs_num) + ')'
        if self.source_id == 'http://arachne.dainst.org/data/search':
            self.label = 'Arachne Comparanda'
        self.properties = self.make_properties(obs_dict)
        self.links = self.make_links(obs_dict)
        if self.properties is not False and self.links is not False:
            self.use_accordions = True

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

    def make_links(self, obs_dict):
        """ Makes property objects for an observation
        """
        links = False
        for key, item in obs_dict.items():
            if(key != 'id' and key in self.context):
                if(OCitem.PREDICATES_OCGEN_PREDICATETYPE in self.context[key]):
                    if(self.context[key][OCitem.PREDICATES_OCGEN_PREDICATETYPE] == 'link'):
                        if links is False:
                            links = []
                        act_link = Link()
                        act_link.class_type_metadata = self.class_type_metadata
                        act_link.start_link(self.context[key])
                        act_link.add_link_objects(obs_dict[key])
                        if act_link.subjects is not False:
                            self.subjects_link_count += len(act_link.subjects)
                            if self.subjects_links is False:
                                self.subjects_links = []
                            act_link.nodeid = 'obs-' + str(self.obs_num) + '-subjects-' + act_link.linkslug
                            self.subjects_links.append(act_link)
                        if act_link.media is not False:
                            self.media_link_count += len(act_link.media)
                            if self.media_links is False:
                                self.media_links = []
                            act_link.nodeid = 'obs-' + str(self.obs_num) + '-media-' + act_link.linkslug
                            self.media_links.append(act_link)
                        if act_link.persons is not False:
                            self.persons_link_count += len(act_link.persons)
                            if self.persons_links is False:
                                self.persons_links = []
                            act_link.nodeid = 'obs-' + str(self.obs_num) + '-persons-' + act_link.linkslug
                            self.persons_links.append(act_link)
                        if act_link.documents is not False:
                            self.documents_link_count += len(act_link.documents)
                            if self.documents_links is False:
                                self.documents_links = []
                            act_link.nodeid = 'obs-' + str(self.obs_num) + '-documents-' + act_link.linkslug
                            self.documents_links.append(act_link)
                        links.append(act_link)
        return links


class Property():
    """ This class makes an object useful for templating
    a property which has a variable predicate with one or more values"""

    def __init__(self):
        self.varlabel = False
        self.varuri = False
        self.varslug = False
        self.vartype = False
        self.values = False

    def start_property(self, predicate_info):
        """ Starts a property with metadata about the variable
        """
        self.varlabel = predicate_info['label']
        self.varuri = predicate_info['owl:sameAs']
        self.varslug = predicate_info['slug']
        self.vartype = predicate_info['type']

    def add_property_values(self, prop_vals):
        """ Adds values to a variable
        """
        self.values = []
        for val_item in prop_vals:
            act_prop_val = PropValue()
            act_prop_val.vartype = self.vartype
            act_prop_val.make_value(val_item)
            self.values.append(act_prop_val)


class Link():

    def __init__(self):
        self.nodeid = False
        self.linklabel = False
        self.linkuri = False
        self.linkslug = False
        self.linktype = False
        self.subjects = False
        self.media = False
        self.documents = False
        self.persons = False
        self.class_type_metadata = False

    def start_link(self, predicate_info):
        """ Starts a link property with metadata about the link
        """
        self.linklabel = predicate_info['label']
        self.linkuri = predicate_info['owl:sameAs']
        self.linkslug = predicate_info['slug']
        self.linktype = predicate_info['type']
        if self.linkslug == 'link':
            self.linklabel = 'Linked / Associated'

    def add_link_objects(self, link_vals):
        """ Adds objects (of different types) to the link
        """
        for val_item in link_vals:
            act_prop_val = PropValue()
            act_prop_val.vartype = self.linktype
            act_prop_val.make_value(val_item)
            if act_prop_val.item_type == 'subjects':
                if self.subjects is False:
                    self.subjects = []
                list_item = {}
                list_item['uri'] = act_prop_val.uri
                list_item['label'] = act_prop_val.val
                list_item['altlabel'] = None
                list_item['linkslug'] = self.linkslug
                list_item['linklabel'] = self.linklabel
                list_item['type'] = act_prop_val.type
                list_item['uuid'] = act_prop_val.uuid
                list_item = ItemMetadata.get_class_meta(list_item,
                                                        self.class_type_metadata)
                self.subjects.append(list_item)
            if act_prop_val.item_type == 'media':
                if self.media is False:
                    self.media = []
                self.media.append(act_prop_val)
            if act_prop_val.item_type == 'documents':
                if self.documents is False:
                    self.documents = []
                self.documents.append(act_prop_val)
            if act_prop_val.item_type == 'persons':
                if self.persons is False:
                    self.persons = []
                self.persons.append(act_prop_val)


class PropValue():
    """ This class makes an object useful for templating
    a property value"""

    def __init__(self):
        self.vartype = False
        self.item_type = False
        self.uri = False
        self.val = False
        self.id = False
        self.uuid = False
        self.type = False
        self.thumbnail = False
        self.oc_item = True

    def make_value(self, val_item):
        if isinstance(val_item, dict):
            if('id' in val_item):
                if(val_item['id'][:7] == 'http://' or val_item['id'][:8] == 'https://'):
                    self.uri = val_item['id']
                    uri_item = URImanagement.get_uuid_from_oc_uri(val_item['id'], True)
                    if uri_item is not False:
                        self.item_type = uri_item['item_type']
                        self.uuid = uri_item['uuid']
                    else:
                        self.item_type = 'external-resource'
                        self.uuid = False
                        self.oc_item = False
                else:
                    self.id = val_item['id'].replace('#', '')
            if 'type' in val_item:
                self.type = val_item['type']
            if('label' in val_item):
                self.val = val_item['label']
            if 'oc-gen:thumbnail-uri' in val_item:
                self.thumbnail = val_item['oc-gen:thumbnail-uri']
                if self.item_type == 'external-resource':
                    self.item_type = 'media'
            if('xsd:string' in val_item):
                self.val = val_item['xsd:string']
        else:
            if self.vartype == 'xsd:integer':
                self.val = str(int(float(val_item)))
            else:
                self.val = val_item


class Project():
    """ This class makes an object useful for templating
    project information"""

    def __init__(self):
        self.uri = False
        self.uuid = False
        self.slug = False
        self.label = False
        self.edit_status = False
        self.item_type = False
        self.view_authorized = False

    def make_project(self, json_ld):
        if isinstance(json_ld, dict):
            if('dc-terms:isPartOf' in json_ld):
                for proj_item in json_ld['dc-terms:isPartOf']:
                    if 'projects' in proj_item['id']:
                        self.uri = proj_item['id']
                        self.uuid = URImanagement.get_uuid_from_oc_uri(proj_item['id'])
                        self.slug = proj_item['slug']
                        self.label = proj_item['label']
                        try:
                            # now get the edit status for the project, not in the JSON-LD
                            # but from the database
                            project = ModProject.objects.get(uuid=self.uuid)
                            self.edit_status = project.edit_status
                        except ModProject.DoesNotExist:
                            project = False
                        break
            if self.item_type == 'projects' and 'bibo:status' in json_ld:
                for bibo_status in json_ld['bibo:status']:
                    if 'edit-level' in bibo_status['id']:
                        # get the number at the end of edit-level
                        self.edit_status = float(bibo_status['id'].split('-')[-1])
                        break


class Citation():
    """ This class makes an object useful for templating
    ciation information"""

    def __init__(self):
        self.item_authors = []
        self.item_editors = []
        self.doi = False
        self.ark = False
        self.project = False
        self.context = False
        self.cite_authors = ''
        self.cite_editors = ''
        self.cite_title = ''
        self.cite_year = ''
        self.cite_released = ''
        self.uri = ''
        self.coins = False

    def make_citation(self, json_ld):
        """ Make citation from metadata in the JSON-LD dict """
        if isinstance(json_ld, dict):
            if('dc-terms:contributor' in json_ld):
                for p_item in json_ld['dc-terms:contributor']:
                    self.item_authors.append(p_item['label'])
            if('dc-terms:creator' in json_ld):
                for p_item in json_ld['dc-terms:creator']:
                    self.item_editors.append(p_item['label'])
            if('owl:sameAs' in json_ld):
                for s_item in json_ld['owl:sameAs']:
                    if 'dx.doi.org' in s_item['id']:
                        self.doi = s_item['id']
                    elif 'n2t.net/ark:' in s_item['id']:
                        self.ark = s_item['id']
            if len(self.item_authors) < 1:
                self.item_authors = self.item_editors
            if 'dc-terms:published' in json_ld:
                published = datetime.datetime.strptime(json_ld['dc-terms:published'], '%Y-%m-%d')
            else:
                published = datetime.datetime.now()
            if len(self.item_authors) > 0:
                self.cite_authors = ', '.join(self.item_authors)
            else:
                self.cite_authors = 'Open Context Editors'
            if 'dc-terms:title' in json_ld:
                self.cite_title = json_ld['dc-terms:title']
            else:
                self.cite_title = json_ld['label']
            self.cite_year += published.strftime('%Y')
            self.cite_released = published.strftime('%Y-%m-%d')
            self.uri = json_ld['id']
            self.cite_editors = ', '.join(self.item_editors)
            if len(self.item_editors) == 1:
                self.cite_editors += ' (Ed.) '
            elif len(self.item_editors) > 1:
                self.cite_editors += ' (Eds.) '
            else:
                self.cite_editors += ''


class GeoMap():
    def __init__(self):
        self.geojson = False
        self.start_lat = 0
        self.start_lon = 0
        self.start_zoom = 7

    def make_geomap(self, json_ld):
        """ Makes an ordered dict for saving geojson data as json
            embedded in the HTML of an item, for easy use by
            leaflet
        """
        if isinstance(json_ld, dict):
            if 'features' in json_ld:
                lats = []
                lons = []
                use_features = []
                for feature in json_ld['features']:
                    show_feature = True
                    if 'Polygon' in feature['geometry']['type']:
                        self.start_zoom = 6
                    elif feature['geometry']['type'] == 'Point':
                        lats.append(feature['geometry']['coordinates'][1])
                        lons.append(feature['geometry']['coordinates'][0])
                    if 'location-precision-note' in feature['properties']:
                        if 'security' in feature['properties']['location-precision-note'] \
                           and feature['geometry']['type'] == 'Point':
                            show_feature = False
                    if show_feature:
                        use_features.append(feature)
                self.start_lat = sum(lats) / float(len(lats))
                self.start_lon = sum(lons) / float(len(lons))
                geojson = LastUpdatedOrderedDict()
                geojson['type'] = 'FeatureCollection'
                geojson['features'] = use_features
                self.geojson = json.dumps(geojson,
                                          indent=4,
                                          ensure_ascii=False)


class LinkedData():

    REL_PREDICATES = ['skos:closeMatch']
    REL_MEASUREMENTS = ['cidoc-crm:P67_refers_to',
                        'oc-gen:has-technique',
                        'rdfs:range']
    ITEM_REL_PREDICATES = ['skos:closeMatch',
                           'owl:sameAs',
                           'skos:related',
                           'skos:broader']
    ITEM_DC_METADATA_PREDICATES = ['dc-terms:subject',
                                   'dc-terms:spatial',
                                   'dc-terms:coverage']

    def __init__(self):
        self.linked_predicates = False
        self.linked_types = False
        self.annotations = []  # annotations on entities found in observations
        self.item_annotations = []  # annotations on the main entity of the JSON-LD
        self.item_dc_metadata = []  # dublin-core annotations on the main entity of the JSON-LD
        self.measurement_meta = {}  # measurement metadata for predicates
        self.project = False

    def make_linked_data(self, json_ld):
        """ Makes a list of linked data annotations that have unique combinations of predicates and objects
        """
        output = False
        ld_found = self.make_linked_data_lists(json_ld)
        if ld_found:
            # using an ordered dict to make sure we can more easily have unique combos of preds and objects
            temp_annotations = LastUpdatedOrderedDict()
            if(OCitem.PREDICATES_OCGEN_HASOBS in json_ld):
                for obs_item in json_ld[OCitem.PREDICATES_OCGEN_HASOBS]:
                    for link_pred in self.linked_predicates:
                        if link_pred['subject'] in obs_item:
                            if link_pred['id'] not in temp_annotations:
                                act_annotation = link_pred
                                act_annotation['subjects'] = []
                                act_annotation['objects'] = LastUpdatedOrderedDict()
                                act_annotation['oc_objects'] = LastUpdatedOrderedDict()
                                act_annotation['literals'] = []
                            else:
                                act_annotation = temp_annotations[link_pred['id']]
                            if link_pred['subject'] not in act_annotation['subjects']:
                                act_annotation['subjects'].append(link_pred['subject'])
                            for act_val in obs_item[link_pred['subject']]:
                                if isinstance(act_val, dict):
                                    if 'xsd:string' in act_val:
                                        if act_val['xsd:string'] not in act_annotation['literals']:
                                            # makes sure we've got unique string literals
                                            act_annotation['literals'].append(act_val['xsd:string'])
                                    else:
                                        if 'id' in act_val:
                                            act_type_oc_id = act_val['id']
                                            if act_type_oc_id in self.linked_types:
                                                act_type = self.linked_types[act_type_oc_id]
                                                if act_type['id'] not in act_annotation['objects']:
                                                    # makes sure we've got unique objects
                                                    act_annotation['objects'][act_type['id']] = act_type
                                            else:
                                                act_type = act_val
                                                if self.project.label is False:
                                                    act_type['vocab_uri'] = settings.CANONICAL_HOST
                                                    act_type['vocabulary'] = settings.CANONICAL_SITENAME
                                                else:
                                                    act_type['vocab_uri'] = self.project.uri
                                                    act_type['vocabulary'] = settings.CANONICAL_SITENAME + ' :: ' + self.project.label
                                                if act_type['id'] not in act_annotation['oc_objects']:
                                                    # makes sure we've got unique objects
                                                    act_annotation['oc_objects'][act_type['id']] = act_type
                                else:
                                    if act_val not in act_annotation['literals']:
                                        # makes sure we've got unique value literals
                                        act_annotation['literals'].append(act_val)
                            temp_annotations[link_pred['id']] = act_annotation
            if len(temp_annotations) > 0:
                output = True
                for pred_uri_key, act_annotation in temp_annotations.items():
                    if len(act_annotation['literals']) < 1:
                        act_annotation['literals'] = None
                    if len(act_annotation['objects']) > 0:
                        objects_list = []
                        for obj_uri_key, act_obj in act_annotation['objects'].items():
                            objects_list.append(act_obj)
                        act_annotation['objects'] = objects_list
                    if len(act_annotation['oc_objects']) > 0:
                        oc_objects_list = []
                        for obj_uri_key, act_obj in act_annotation['oc_objects'].items():
                            oc_objects_list.append(act_obj)
                        act_annotation['oc_objects'] = oc_objects_list
                    if len(act_annotation['objects']) < 1:
                        if len(act_annotation['oc_objects']) < 1:
                            act_annotation['objects'] = None
                            act_annotation['oc_objects'] = None
                        else:
                            act_annotation['objects'] = act_annotation['oc_objects']
                    act_annotation['type'] = 'Standard'
                    self.annotations.append(act_annotation)
        return output

    def make_linked_data_lists(self, json_ld):
        """ Makes lists of linked predicates and types by
            reading the @graph section of the JSON-LD
        """
        output = False
        if isinstance(json_ld, dict):
            if '@graph' in json_ld:
                linked_predicates = []
                linked_types = LastUpdatedOrderedDict()
                for ld_item in json_ld['@graph']:
                    subject_type = False
                    if '@id' in ld_item:
                        subject_id = ld_item['@id']
                    elif 'id' in ld_item:
                        subject_id = ld_item['id']
                    else:
                        subject_id = False
                    if subject_id is not False:
                        if 'oc-pred:' in subject_id:
                            subject_type = 'predicates'
                        elif (settings.CANONICAL_HOST + '/predicates/') in subject_id:
                            subject_type = 'predicates'
                        elif 'oc-types:' in subject_id:
                            subject_type = 'types'
                        elif (settings.CANONICAL_HOST + '/types/') in subject_id:
                            subject_type = 'types'
                        else:
                            subject_type = False
                    if subject_type is not False:
                        for rel_predicate in self.REL_PREDICATES:
                            # find equivalence standards annotations
                            if rel_predicate in ld_item:
                                for link_assertion in ld_item[rel_predicate]:
                                    link_assertion['subject'] = subject_id
                                    link_assertion['vocab_uri'] = False
                                    link_assertion['vocabulary'] = False
                                    ent = Entity()
                                    found = ent.dereference(link_assertion['id'])
                                    if found:
                                        link_assertion['vocab_uri'] = ent.vocab_uri
                                        link_assertion['vocabulary'] = ent.vocabulary
                                    if subject_type == 'predicates':
                                        linked_predicates.append(link_assertion)
                                    else:
                                        linked_types[link_assertion['subject']] = link_assertion
                if len(linked_predicates) > 0:
                    self.linked_predicates = linked_predicates
                    self.linked_types = {}
                    output = True
                if len(linked_types) > 0:
                    self.linked_types = linked_types
                    output = True
        return output

    def get_item_annotations(self, item_type, json_ld):
        """ Gets annotations made on this specific item """
        self.item_assertions = []
        if isinstance(json_ld, dict):
            preds = self.ITEM_REL_PREDICATES + self.REL_MEASUREMENTS
            for act_pred in preds:
                if act_pred in json_ld:
                    add_annotation = True
                    p_uri = act_pred
                    p_label = act_pred
                    p_vocab = False
                    p_vocab_uri = False
                    ent = Entity()
                    found = ent.dereference(act_pred)
                    if found:
                        p_uri = ent.uri
                        p_label = ent.label
                        p_vocab = ent.vocabulary
                        p_vocab_uri = ent.vocab_uri
                    act_i_ass = {'id': p_uri,
                                 'type': 'Standard',
                                 'label': p_label,
                                 'vocabulary': p_vocab,
                                 'vocab_uri': p_vocab_uri,
                                 'objects': []}
                    for ld_obj in json_ld[act_pred]:
                        uri = ld_obj['id']
                        if item_type == 'types'\
                           and act_pred == 'skos:related'\
                           and ('/predicates/' in uri or 'oc-pred' in uri):
                            # this is a type related to a predicate, don't consider as an annotaiton
                            add_annotation = False
                        elif item_type == 'predicates' and act_pred == 'rdfs:range':
                             # this is a range for a predicate, don't consider as an annotaiton
                            add_annotation = False
                        elif 'dx.doi.org' in uri and 'owl:sameAs' == act_pred:
                            add_annotation = False
                        elif 'n2t.net' in uri and 'owl:sameAs' == act_pred:
                            add_annotation = False
                        ld_obj['vocabulary'] = False
                        ld_obj['vocab_uri'] = False
                        ent = Entity()
                        found = ent.dereference(uri)
                        if found:
                            ld_obj['vocabulary'] = ent.vocabulary
                            ld_obj['vocab_uri'] = ent.vocab_uri
                        act_i_ass['objects'].append(ld_obj)
                    if add_annotation:
                        self.item_assertions.append(act_i_ass)
        if len(self.item_assertions) > 0:
            output = self.item_assertions
        else:
            output = False
        return output

    def get_item_dc_metadata(self, item_type, json_ld):
        """ Gets dublin core annotations made on this specific item """
        self.item_dc_metadata = []
        if isinstance(json_ld, dict):
            for act_pred in self.ITEM_DC_METADATA_PREDICATES:
                # print(act_pred)
                if act_pred in json_ld:
                    add_annotation = True
                    p_uri = act_pred
                    p_label = act_pred
                    p_vocab = False
                    p_vocab_uri = False
                    ent = Entity()
                    found = ent.dereference(act_pred)
                    if found:
                        p_uri = ent.uri
                        p_label = ent.label
                        p_vocab = ent.vocabulary
                        p_vocab_uri = ent.vocab_uri
                    act_i_ass = {'id': p_uri,
                                 'type': 'Standard',
                                 'label': p_label,
                                 'vocabulary': p_vocab,
                                 'vocab_uri': p_vocab_uri,
                                 'objects': []}
                    for ld_obj in json_ld[act_pred]:
                        uri = ld_obj['id']
                        ld_obj['vocabulary'] = False
                        ld_obj['vocab_uri'] = False
                        ent = Entity()
                        found = ent.dereference(uri)
                        if found:
                            ld_obj['vocabulary'] = ent.vocabulary
                            ld_obj['vocab_uri'] = ent.vocab_uri
                        act_i_ass['objects'].append(ld_obj)
                    if add_annotation:
                        self.item_dc_metadata.append(act_i_ass)
                    if 'subject' in act_i_ass['id'] \
                       and len(act_i_ass['objects']) > 0:
                        tdar = tdarAPI()
                        tdar_items = tdar.get_tdar_items_by_site_keyword_objs(act_i_ass['objects'])
                        if isinstance(tdar_items, list):
                            if len(tdar_items) > 0:
                                act_i_ass = {'id': 'http://www.w3.org/2000/01/rdf-schema#seeAlso',
                                             'type': 'Source, Current Feed',
                                             'label': 'See also, Related Content',
                                             'vocabulary': 'Digital Antiquity, tDAR',
                                             'vocab_uri': tdar.html_url,
                                             'objects': tdar_items}
                                self.item_dc_metadata.append(act_i_ass)
        if len(self.item_dc_metadata) > 0:
            output = self.item_dc_metadata
        else:
            output = False
        return output
