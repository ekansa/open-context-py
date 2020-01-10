import json
import copy
import datetime
from random import randint
from geojson import Feature, Point, Polygon, MultiPolygon, GeometryCollection, FeatureCollection
from geojson import MultiPoint, MultiLineString, LineString
from django.conf import settings
from opencontext_py.libs.filemath import FileMath
from opencontext_py.libs.languages import Languages
from django.utils.http import urlquote, quote_plus, urlquote_plus
from opencontext_py.libs.rootpath import RootPath
from opencontext_py.libs.general import LastUpdatedOrderedDict, DCterms
from opencontext_py.libs.globalmaptiles import GlobalMercator
from opencontext_py.apps.entities.uri.models import URImanagement
from opencontext_py.apps.entities.entity.imageproxy import proxy_image_url_if_needed
from opencontext_py.apps.entities.entity.models import Entity
from opencontext_py.apps.contexts.readprojectcontext import ReadProjectContextVocabGraph
from opencontext_py.apps.ocitems.namespaces.models import ItemNamespaces
from opencontext_py.apps.ocitems.ocitem.itemkeys import ItemKeys
from opencontext_py.apps.ocitems.projects.models import Project as ModProject
from opencontext_py.apps.ocitems.projects.permissions import ProjectPermissions
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.ocitems.identifiers.models import StableIdentifer
from opencontext_py.apps.ldata.tdar.api import tdarAPI
from opencontext_py.apps.ldata.orcid.api import orcidAPI
from opencontext_py.apps.ocitems.assertions.models import Assertion
from opencontext_py.apps.searcher.solrsearcher.querymaker import QueryMaker


# Help organize the code, with a class to make templating easier
class HTMLtemplate():
    """ This class makes an object useful for templating, since
    the JSON-LD object can't be read by the django template system """

    FULLIMAGE_MIMETYPES = ['image/png',
                           'image/jpeg',
                           'image/gif']
    
    OPEN_CONTEXT_ICON = '/static/oc/images/index/oc-blue-square-logo.png'
    
    ITEM_TYPE_DESCRIPTIONS = {
        'subjects': 'data record',
        'media': 'media item',
        'documents': 'document (field notes, diaries, narratives)',
        'projects': 'project or collection publication',
        'predicates': 'descriptive attribute or linking relation',
        'types': 'controlled vocabulary (often a typology) concept',
        'persons': 'person or organization record'
    }

    def __init__(self, request=False):
        self.label = False
        self.person = False
        self.uuid = False
        self.project_uuid = False
        self.proj_context_json_ld = False
        self.read_vocab_graph = False
        self.id = False
        self.href = False
        self.slug = False
        self.og_title = False  # open graph title
        self.og_image = False  # open graph image
        self.og_description = False  # open graph description
        self.og_type = 'website'  # open graph type
        self.og_site_name = settings.CANONICAL_SITENAME  # open graph site name
        self.twitter_site = settings.TWITTER_SITE  # twitter site account
        self.item_category_label = False
        self.item_category_uri = False
        self.item_category_icon = False
        self.context = False  # items spatial context
        self.children = False
        self.observations = False
        self.obs_more_tab = 0
        self.class_type_metadata = {}
        self.project = False
        self.citation = False
        self.license = False
        self.geo = False
        self.linked_data = False
        self.content = False
        self.fullimage = False
        self.full_doc_file = False  # a pdf, word, or other file for Javascript preview
        self.fulldownload = False
        self.iiif_json = False
        self.iiif_server = False
        self.x3dom_model = False
        self.x3dom_textures = []
        self.nexus_3d = False
        self.geojson_file = False
        self.nav_items = settings.NAV_ITEMS
        self.act_nav = False
        self.use_accordions = False
        self.item_linked_data = False
        self.item_dc_metadata = False
        self.related_tables = []
        self.request = request
        self.view_permitted = True  # defaults to allow views
        self.edit_permitted = False
        self.check_edit_permitted = False
        self.contents_top = False
        self.project_hero_uri = False  # randomly selects an image for the project
        self.predicate_query_link = False  # link for querying with a predicate
        self.predicate_query_json = False  # link for querying json with a predicate
        self.type_query_link = False  # link for querying with a type
        self.type_query_json = False  # link for querying json with a type
        self.children_query = False  # link for querying children of this
        self.proj_content = False

    def read_jsonld_dict(self, json_ld):
        """ Reads JSON-LD dict object to make a TemplateItem object
        """
        if isinstance(self.proj_context_json_ld, dict):
            self.read_vocab_graph  = ReadProjectContextVocabGraph(self.proj_context_json_ld)
        self.uuid = json_ld['uuid']
        self.label = json_ld['label']
        self.id = json_ld['id']
        ent = Entity()
        found = ent.dereference(self.uuid)
        if found:
            self.act_nav = ent.item_type
            self.href = ent.item_type + '/' + self.uuid
        self.slug = json_ld['slug']
        self.store_class_type_metadata(json_ld)
        self.create_person_data(json_ld)
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
        self.create_query_links(json_ld)
        self.create_project_hero(json_ld)
        self.create_license(json_ld)
        self.check_contents_top()
        self.create_opengraph()

    def create_person_data(self, json_ld):
        """ Creates person names from FOAF properties """
        if 'foaf:name' in json_ld:
            self.person = {}
            self.person['combined_name'] = json_ld['foaf:name']
            if 'foaf:givenName' in json_ld:
                self.person['given_name'] = json_ld['foaf:givenName']
            else:
                self.person['given_name'] = False
            if 'foaf:familyName' in json_ld:
                self.person['surname'] = json_ld['foaf:familyName']
            else:
                self.person['surname'] = False
            if 'foaf:nick' in json_ld:
                self.person['intials'] = json_ld['foaf:nick']
            else:
                self.person['intials'] = False
            if ItemKeys.PREDICATES_FOAF_PRIMARYTOPICOF in json_ld:
                # get the orcid identifier for this person
                orcid_dict = json_ld[ItemKeys.PREDICATES_FOAF_PRIMARYTOPICOF][0]
                orcid_api = orcidAPI()
                orcid_dict['api'] = orcid_api.make_orcid_api_url(orcid_dict['id'])
                self.person['orcid'] = orcid_dict
            else:
                self.person['orcid'] = False

    def create_context(self, json_ld):
        """
        Adds spatial context object if json_ld describes such
        """
        act_context = Context()
        act_context.make_context(json_ld, self.class_type_metadata)
        if act_context.type is not False:
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
            act_obs.read_vocab_graph = self.read_vocab_graph
            act_obs.obs_num = len(self.observations) + 1
            act_obs.make_predicate_obs(json_ld)
            if act_obs.properties is not False:
                self.observations.append(act_obs)
        elif self.act_nav == 'types':
            if self.observations is False:
                self.observations = []
            act_obs = Observation()
            act_obs.read_vocab_graph = self.read_vocab_graph
            act_obs.obs_num = len(self.observations) + 1
            act_obs.make_type_obs(json_ld)
            if act_obs.properties is not False:
                self.observations.append(act_obs)
        if ItemKeys.PREDICATES_OCGEN_HASOBS in json_ld:
            if self.observations is False:
                self.observations = []
            for obs_item in json_ld[ItemKeys.PREDICATES_OCGEN_HASOBS]:
                obs_num = len(self.observations) + 1
                act_obs = Observation()
                act_obs.read_vocab_graph = self.read_vocab_graph
                act_obs.class_type_metadata = self.class_type_metadata
                act_obs.obs_num = obs_num
                act_obs.make_observation(obs_item)
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
                act_obs.read_vocab_graph = self.read_vocab_graph
                act_obs.class_type_metadata = self.class_type_metadata
                act_obs.make_linked_data_obs(self.linked_data.annotations)
                self.observations.append(act_obs)
        if self.item_linked_data is not False:
            # create an observation out of the item annoations
            if self.observations is False:
                self.observations = []
            act_obs = Observation()
            act_obs.read_vocab_graph = self.read_vocab_graph
            act_obs.obs_num = len(self.observations) + 1
            act_obs.make_item_annotation_obs(self.item_linked_data)
            if act_obs.annotations is not False:
                self.observations.append(act_obs)
        if self.item_dc_metadata is not False:
            # create an observation out of the item annoations
            if self.observations is False:
                self.observations = []
            act_obs = Observation()
            act_obs.read_vocab_graph = self.read_vocab_graph
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
        self.project_uuid = proj.uuid

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
        geo.item_type = self.act_nav
        if self.project is not False:
            # add default geozoom to update how mapping happens
            geo.proj_geo_specificity = self.project.proj_geo_specificity
            geo.proj_geo_note = self.project.proj_geo_note
        geo.make_geomap(json_ld)
        self.geo = geo

    def create_linked_data(self, json_ld):
        """ Makes an instance of a GeoMap class, with data from the JSON_LD
        """
        linked_data = LinkedData()
        linked_data.read_vocab_graph = self.read_vocab_graph
        linked_data.project = self.project
        linked_data.make_linked_data(json_ld)
        self.linked_data = linked_data
        self.item_linked_data = linked_data.get_item_annotations(self.act_nav, json_ld)
        self.item_dc_metadata = linked_data.get_item_dc_metadata(self.act_nav, json_ld)
        self.related_tables = linked_data.related_tables

    def create_content(self, json_ld):
        """
        Gets various forms of content for media, documents, projects
        """
        lang_obj = Languages()
        if 'oc-gen:has-files' in json_ld:
            # content for media
            if self.content is False:
                self.content = {}
                self.content['fullfile'] = False
                self.content['full_size'] = 0  # filesize in bytes
                self.content['full_size_human'] = False  # filesize in human readable form
                self.content['preview'] = False
                self.content['thumbnail'] = False
                self.content['x3dom_model'] = False
                self.content['x3dom_textures'] = []
                self.content['nexus_3d'] = False
                self.content['gis_file'] = False
            fmath = FileMath()
            rp = RootPath()
            for file_item in json_ld['oc-gen:has-files']:
                if file_item['type'] == 'oc-gen:fullfile':
                    self.content['fullfile'] = rp.convert_to_https(file_item['id'])
                    self.fulldownload = True
                    if '.nxs' in self.content['fullfile']:
                        if self.content['fullfile'][-4:] == '.nxs':
                            rp = RootPath()
                            target_url = rp.convert_to_https(file_item['id'])
                            self.nexus_3d = self.make_cors_ok_url(target_url)
                            self.content['nexus_3d'] = file_item['id']
                            print('Nexus: ' + self.nexus_3d)
                    if 'dcat:size' in file_item:
                        if float(file_item['dcat:size']) > 0:
                            self.content['full_size'] = float(file_item['dcat:size'])
                            self.content['full_size_human'] = fmath.approximate_size(float(file_item['dcat:size']))
                    if 'dc-terms:hasFormat' in file_item:
                        for mime_type in self.FULLIMAGE_MIMETYPES:
                            if mime_type in file_item['dc-terms:hasFormat']:
                                # the file is an image type that displays in a browser
                                self.fullimage = True
                                break
                        if 'application/pdf' in file_item['dc-terms:hasFormat']:
                            # this is a pdf that can be previewed
                            self.content['preview'] = rp.convert_to_https(file_item['id'])
                            self.item_category_label = 'Acrobat PDF File'
                            rp = RootPath()
                            target_url = rp.convert_to_https(file_item['id'])
                            # if 'https:' in target_url:
                                # target_url = target_url.replace('https:', 'http:')
                            # PDF viewer installed, but only works if PDF at same domain, so make a proxy link
                            self.full_doc_file = self.make_cors_ok_url(target_url)
                            # self.full_doc_file = False  # comment this out when enabling this feature
                        elif 'vnd.geo+json' in file_item['dc-terms:hasFormat']:
                            # this is a geojson file that can be previewed
                            rp = RootPath()
                            target_url = rp.convert_to_https(file_item['id'])
                            self.geojson_file = self.make_cors_ok_url(target_url)
                            self.content['gis_file']  = file_item['id']
                elif file_item['type'] == 'oc-gen:preview':
                    self.content['preview'] = rp.convert_to_https(file_item['id'])
                elif file_item['type'] == 'oc-gen:thumbnail':
                    self.content['thumbnail'] = rp.convert_to_https(file_item['id'])
                elif file_item['type'] == 'oc-gen:iiif':
                    self.iiif_json = rp.convert_to_https(file_item['id'])
                    self.iiif_server = self.iiif_json.replace('/info.json', '')
                elif file_item['type'] == 'oc-gen:x3dom-model':
                    rp = RootPath()
                    target_url = rp.convert_to_https(file_item['id'])
                    self.x3dom_model = self.make_cors_ok_url(target_url)
                    self.content['x3dom_model']  = file_item['id']
                elif file_item['type'] == 'oc-gen:x3dom-texture':
                    rp = RootPath()
                    target_url = rp.convert_to_https(file_item['id'])
                    texture_url = self.make_cors_ok_url(target_url)
                    self.x3dom_textures.append(texture_url)
                    self.content['x3dom_textures'].append(file_item['id'])
            # Proxy broken images in Merritt if needed
            self.content['preview'] = proxy_image_url_if_needed(
                self.content['preview'], 
                primary_url=self.content['fullfile'], 
                width=650
            )
            self.content['thumbnail'] = proxy_image_url_if_needed(
                self.content['thumbnail'], 
                primary_url=self.content['fullfile'], 
                width=150
            )
        if 'rdf:HTML' in json_ld:
            # content for documents
            if self.content is False:
                self.content = {}
            self.content['main_text'] = lang_obj.get_default_value_str(json_ld['rdf:HTML'])
        elif 'dc-terms:abstract' in json_ld:
            # content for project abstracts
            print('here is an abstract')
            if self.content is False:
                self.content = {}
            self.content['main_text'] = lang_obj.get_default_value_str(json_ld['dc-terms:abstract'])
        if 'description' in json_ld:
            # content for project descriptions
            if self.content is False:
                self.content = {}
            self.content['sum_text'] = lang_obj.get_default_value_str(json_ld['description'])
        if self.content is not False \
           and settings.CANONICAL_HOST != settings.DEPLOYED_HOST:
            if 'main_text' in self.content:
                # update links in the text to point to the current host
                rp = RootPath()
                self.content['main_text'] = self.content['main_text']\
                                                .replace(settings.CANONICAL_HOST,
                                                         rp.get_baseurl())

    def store_class_type_metadata(self, json_ld):
        """ Stores information about classes / categories, including labels and icons
            needed for user inferface
        """
        rp = RootPath()
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
                        meta['icon'] = rp.convert_to_https(g_anno['oc-gen:hasIcon'][0]['id'])
                    self.class_type_metadata[identifier] = meta
        if 'category' in json_ld:
            item_cat_labels = []
            for cat in json_ld['category']:
                self.item_category_uri = cat
                if cat in self.class_type_metadata:
                    item_cat_labels.append(self.class_type_metadata[cat]['typelabel'])
                    if 'icon' in self.class_type_metadata[cat]:
                        self.item_category_icon = self.class_type_metadata[cat]['icon'] 
            self.item_category_label = ', '.join(item_cat_labels)
        if self.item_category_label is False:
            # make sure the item has category label, if needed get from settings nav_items
            for nav_item in settings.NAV_ITEMS:
                if nav_item['key'] == self.act_nav:
                    self.item_category_label = nav_item['display']
                    break

    def check_contents_top(self):
        """ checks to see if the
            contents panel is at the top
            of a multi-observation item
        """
        if isinstance(self.observations, list):
            if len(self.observations) > 1:
                has_content = False
                check_obs = self.observations[0]
                if isinstance(check_obs.properties, list):
                    has_content = True
                elif isinstance(check_obs.subjects_links, list):
                    has_content = True
                elif isinstance(check_obs.media_links, list):
                    has_content = True
                elif isinstance(check_obs.documents_links, list):
                    has_content = True
                elif isinstance(check_obs.persons_links, list):
                    has_content = True
                elif isinstance(check_obs.annotations, list):
                    has_content = True
                elif isinstance(check_obs.item_annotations, list):
                    has_content = True
                if has_content is False:
                    # make the contents the top
                    self.contents_top = True

    def create_query_links(self, json_ld):
        """ makes links for querying with the item
        """
        if self.act_nav == 'subjects':
            if isinstance(self.children, list):
                if len(self.children) > 0:
                    self.children_query = '/search/?prop=' + self.slug 
                    if self.project is not False:
                        if self.project.slug is not False:
                            self.children_query += '&proj=' + self.project.slug
                            self.children_query += '&proj=' + self.project.slug
        elif self.act_nav == 'predicates':
            self.predicate_query_link = '/search/?prop=' + self.slug
            self.predicate_query_json = '/search/.json?prop=' + self.slug
            if self.project is not False:
                if self.project.slug is not False:
                    self.predicate_query_link += '&proj=' + self.project.slug
                    self.predicate_query_json += '&proj=' + self.project.slug
        elif self.act_nav == 'types':
            if 'skos:related' in json_ld:
                if isinstance(json_ld['skos:related'], list):
                    if len(json_ld['skos:related']) > 0:
                        pred_slug = json_ld['skos:related'][0]['slug']
                        q_prop = '---'.join([pred_slug, self.slug])
                        self.type_query_link = '/search/?prop=' + q_prop
                        self.type_query_json = '/search/.json?prop=' + q_prop
                        if self.project.slug is not False:
                            self.type_query_link += '&proj=' + self.project.slug
                            self.type_query_json += '&proj=' + self.project.slug

    def create_project_hero(self, json_ld):
        """ creates a link for displaying a hero image
            by randomly selecting through hero images
            associated with the project
        """
        if self.act_nav == 'projects':
            rp = RootPath()
            if 'foaf:depiction' in json_ld:
                # predicate for images
                heros = json_ld['foaf:depiction']
                len_heros = len(heros)
                if len_heros > 0:
                    if len_heros > 1:
                        act_index = randint(0, (len_heros - 1))
                    else:
                        act_index = 0
                    self.project_hero_uri = rp.convert_to_https(heros[act_index]['id'])    

    def create_license(self, json_ld):
        """ creates a license link
            and label
            and type
        """
        if 'dc-terms:license' in json_ld:
            # license information
            self.license = json_ld['dc-terms:license'][0]
            license_uri = self.license['id']
            if license_uri[-1] != '/':
                # add a last character to the string
                # to keep a consistent pattern
                license_uri += '/'
            lic_ex = license_uri.split('/')
            i = len(lic_ex)
            loop = True
            while loop:
                i -= 1
                part = lic_ex[i]
                if len(part) > 0:
                    try:
                        n_p = float(part)
                    except:
                        n_p = False
                    if n_p is False:
                        # we have a string!
                        self.license['type'] = part
                        loop = False
                if i < 2:
                    loop = False

    def create_opengraph(self):
        """ creates opengraph metadata to facilitate snippets for
            social media sites
        """
        rp = RootPath()
        base_url = rp.get_baseurl()
        if isinstance(self.project_hero_uri, str):
            self.og_image = self.project_hero_uri
        else:
            if self.observations is not False:
                for obs in self.observations:
                    if obs.media_link_count >0:
                        for link in obs.media_links:
                            self.og_image = link.media[0].thumbnail
                            break
        if self.content is not False:
            # use a preview or a thumbnail image as the og_image
            # also maybe a short description
            if 'preview' in self.content and self.fullimage:
                if isinstance(self.content['preview'], str):
                    self.og_image = self.content['preview']
            elif 'thumbnail' in self.content:
                if isinstance(self.content['thumbnail'], str):
                    self.og_image = self.content['thumbnail']
            else:
                # don't use any image
                pass
            if 'sum_text' in self.content:
                # we have summary text, so use it
                if len(self.content['sum_text']) > 0:
                    self.og_description = self.content['sum_text']
        if not isinstance(self.og_image, str):
            if isinstance(self.item_category_icon, str):
                # we don't have an og_image yet, but we do have a category icon,
                # so use that
                self.og_image = self.item_category_icon
            else:
                # use the default Open Context icon
                rp = RootPath()
                base_url = rp.get_baseurl()
                self.og_image = base_url + self.OPEN_CONTEXT_ICON
            # do this anyway, since small pictures do not work.
            self.og_image = base_url + self.OPEN_CONTEXT_ICON
        if isinstance(self.og_image, str):
            # if the base URL is not in the sting, we need to use a proxy
            if base_url not in self.og_image:
                proxy_url = base_url + '/entities/proxy/'
                proxy_url += urlquote_plus(self.og_image)
                self.og_image = proxy_url
        self.og_title = self.citation.cite_title
        if not isinstance(self.og_description, str):
            self.og_description = ''
            if isinstance(self.item_category_label, str) and self.act_nav == 'subjects':
                self.og_description += self.item_category_label
            if self.act_nav in self.ITEM_TYPE_DESCRIPTIONS:
                if self.og_description == '':
                    self.og_description = 'A'
                self.og_description += ' ' + self.ITEM_TYPE_DESCRIPTIONS[self.act_nav]
            if self.act_nav != 'projects' and isinstance(self.project.label, str):
                self.og_description += '; part of the ' + self.project.label
                self.og_description += ' data publication.'

    def make_cors_ok_url(self, url):
        """ checks to see if the url is on the CORS ok
            list. If not, make a proxy URL
        """
        make_proxy = True  # default to making a proxy
        for cors_ok_domain in settings.CORS_OK_DOMAINS:
            if cors_ok_domain in url:
                make_proxy = False
                break
        if make_proxy:
            rp = RootPath()
            url = rp.get_baseurl() + '/entities/proxy/' + urlquote(url)
        return url

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
        if 'type' in item:
            if item['type'] in class_type_metadata:
                meta = class_type_metadata[item['type']]
                for key, value in meta.items():
                    item[key] = value
        return item


class Context():
    """ This class makes an object useful for templating
    describing spatial context of items"""
    def __init__(self):
        self.id = False
        self.type = False
        self.parents = False
        self.parent_labels = []

    def make_context(self, json_ld, class_type_metadata):
        """ makes spatial contexts for use with the template """
        act_context = False
        if ItemKeys.PREDICATES_OCGEN_HASCONTEXTPATH in json_ld:
            self.type = 'context'
            act_context = json_ld[ItemSpatialTemporal.PREDICATES_OCGEN_HASCONTEXTPATH]
        elif ItemKeys.PREDICATES_OCGEN_HASLINKEDCONTEXTPATH in json_ld:
            self.type = 'related'
            act_context = json_ld[ItemKeys.PREDICATES_OCGEN_HASLINKEDCONTEXTPATH]
        if act_context is not False:
            self.id = act_context['id']
            self.parents = []
            if ItemKeys.PREDICATES_OCGEN_HASPATHITEMS in act_context:
                for parent_item in act_context[ItemKeys.PREDICATES_OCGEN_HASPATHITEMS]:
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
        if ItemKeys.PREDICATES_OCGEN_HASCONTENTS in json_ld:
            self.contype = 'Context'
            act_children = json_ld[ItemKeys.PREDICATES_OCGEN_HASCONTENTS]
            if ItemKeys.PREDICATES_OCGEN_CONTAINS in act_children:
                self.id = act_children['id']
                self.children = []
                for child_item in act_children[ItemKeys.PREDICATES_OCGEN_CONTAINS]:
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
        self.read_vocab_graph = None
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
        if 'skos:note' in json_ld:
            self.add_skos_note_property(json_ld)
        if 'rdfs:range' in json_ld:
            range_values = []
            for rel_item in json_ld['rdfs:range']:
                act_val = PropValue()
                act_val.vartype = 'id'
                act_val.item_type = 'external-resource'
                act_val.uri = URImanagement.convert_prefix_to_full_uri(rel_item['id'])
                act_val.id = URImanagement.convert_prefix_to_full_uri(rel_item['id'])
                act_val.uuid = False
                if 'label' in rel_item:
                    act_val.val = rel_item['label']
                else:
                    act_val.val = ''
                    if act_val.vartype == 'xsd:boolean':
                        act_val.val = 'Boolean (True/False) Values'
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
        if 'skos:note' in json_ld:
            self.add_skos_note_property(json_ld)
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

    def add_skos_note_property(self, json_ld):
        """adds a skos note property to the properties """
        if 'skos:note' in json_ld:
            act_val = PropValue()
            act_val.vartype = 'xsd:string'
            act_val.set_string_val_and_localizations(json_ld['skos:note'])
            act_prop = Property()
            act_prop.varlabel = 'Definition or Note'
            act_prop.varuri = False
            act_prop.varslug = False
            act_prop.vartype = 'xsd:string'
            act_prop.values = [act_val]
            if not isinstance(self.properties, list):
                self.properties = []
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

    def make_observation(self, obs_dict):
        """ Makes an observation with some observation metadata
            property list, links to subjects items, links to media items,
            links to persons items, and links to documents
        """
        self.id = obs_dict['id'].replace('#', '')
        self.source_id = obs_dict[ItemKeys.PREDICATES_OCGEN_SOURCEID]
        self.obs_status = obs_dict[ItemKeys.PREDICATES_OCGEN_OBSTATUS]
        self.obs_type = 'contributor'
        if ItemKeys.PREDICATES_OCGEN_OBSLABEL in obs_dict:
            self.label = obs_dict[ItemKeys.PREDICATES_OCGEN_OBSLABEL]
        else:
            if self.obs_num < 2:
                self.label = 'Main Observation'
            else:
                self.label = 'Obs (' + str(self.obs_num) + ')'
        if 'arachne.dainst.org/data/search' in self.source_id:
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
            predicate_info = self.read_vocab_graph.lookup_predicate(key)
            if key != 'id' and isinstance(predicate_info, dict):
                if predicate_info['oc-gen:predType'] == 'variable':
                    if not isinstance(properties, list):
                        properties = []
                    act_prop = Property()
                    act_prop.start_property(predicate_info)
                    act_prop.add_property_values(obs_dict[key])
                    properties.append(act_prop)
        return properties

    def make_links(self, obs_dict):
        """ Makes property objects for an observation
        """
        links = False
        for key, item in obs_dict.items():
            predicate_info = self.read_vocab_graph.lookup_predicate(key)
            if key != 'id' and isinstance(predicate_info, dict):
                if predicate_info['oc-gen:predType'] == 'link':
                    if not isinstance(links, list):
                        links = []
                    act_link = Link()
                    act_link.class_type_metadata = self.class_type_metadata
                    act_link.start_link(predicate_info)
                    act_link.add_link_objects(obs_dict[key])
                    if act_link.subjects is not False:
                        self.subjects_link_count += len(act_link.subjects)
                        if not isinstance(self.subjects_links, list):
                            self.subjects_links = []
                            act_link.nodeid = 'obs-' + str(self.obs_num) + '-subjects-' + act_link.linkslug
                            self.subjects_links.append(act_link)
                    if act_link.media is not False:
                        self.media_link_count += len(act_link.media)
                        if not isinstance(self.media_links, list):
                            self.media_links = []
                        act_link.nodeid = 'obs-' + str(self.obs_num) + '-media-' + act_link.linkslug
                        self.media_links.append(act_link)
                    if act_link.persons is not False:
                        self.persons_link_count += len(act_link.persons)
                        if not isinstance(self.persons_links, list):
                            self.persons_links = []
                        act_link.nodeid = 'obs-' + str(self.obs_num) + '-persons-' + act_link.linkslug
                        self.persons_links.append(act_link)
                    if act_link.documents is not False:
                        self.documents_link_count += len(act_link.documents)
                        if not isinstance(self.documents_links, list):
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
        self.vartype = predicate_info['@type']

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
        self.linktype = predicate_info['@type']
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
        self.show_thumb_label = False
        self.oc_item = True
        self.localizations = False

    def make_value(self, val_item):
        if isinstance(val_item, dict):
            if 'id' in val_item:
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
                # convert to HTTPS if needed
                rp = RootPath()
                self.thumbnail = rp.convert_to_https(self.thumbnail)
                self.thumbnail = proxy_image_url_if_needed(
                    self.thumbnail, 
                )
                if self.item_type == 'external-resource':
                    self.item_type = 'media'
                if 'icons/pdf' in self.thumbnail:
                    self.show_thumb_label = self.val
            if 'xsd:string' in val_item:
                self.set_string_val_and_localizations(val_item['xsd:string'])
        else:
            if self.vartype == 'xsd:integer':
                self.val = str(int(float(val_item)))
                self.val = self.val.replace('.0', '')
            elif self.vartype == 'xsd:boolean':
                if val_item == 1:
                    self.val = 'True'
                else:
                    self.val = 'False'
            else:
                self.val = val_item
                
    def set_string_val_and_localizations(self, xsd_string_obj):
        """ sets the string value for the default language
            as well as localized / translated values
        """
        lang_obj = Languages()
        self.val = lang_obj.get_default_value_str(xsd_string_obj)
        self.localizations = lang_obj.get_other_values_dict(xsd_string_obj)

class Project():
    """ This class makes an object useful for templating
    project information"""

    def __init__(self):
        self.uri = False
        self.uuid = False
        self.slug = False
        self.label = False
        self.parent_project_uuid = False
        self.edit_status = False
        self.item_type = False
        self.view_authorized = False
        self.proj_geo_specificity = 0
        self.proj_geo_note = False

    def make_project(self, json_ld):
        if isinstance(json_ld, dict):
            if 'dc-terms:isPartOf' in json_ld:
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
                            self.parent_project_uuid = project.project_uuid
                            self.get_proj_geo_metadata(project)
                        except ModProject.DoesNotExist:
                            project = False
                        break
            if self.item_type == 'projects' and 'bibo:status' in json_ld:
                try:
                    # now get the edit status for the project, not in the JSON-LD
                    # but from the database
                    project = ModProject.objects.get(uuid=self.uuid)
                    self.get_proj_geo_metadata(project) 
                except ModProject.DoesNotExist:
                    pass
                for bibo_status in json_ld['bibo:status']:
                    if 'edit-level' in bibo_status['id']:
                        # get the number at the end of edit-level
                        self.edit_status = float(bibo_status['id'].split('-')[-1])
                        break
        
    def get_proj_geo_metadata(self, project):
        """ gets project geospatial metadata if stored in a project object """
        if isinstance(project.meta_json, dict):
            # the project has some metadata in a dict (stored in db as JSON)
            if ModProject.META_KEY_GEO_SPECIFICITY in project.meta_json:
                # the project has some default geographic specificity noted
                self.proj_geo_specificity = project.meta_json[ModProject.META_KEY_GEO_SPECIFICITY]
            if ModProject.META_KEY_GEO_NOTE in project.meta_json:
                # the project has a note about its geospatial data
                self.proj_geo_note = project.meta_json[ModProject.META_KEY_GEO_NOTE]


class Citation():
    """ This class makes an object useful for templating
    ciation information"""

    def __init__(self):
        self.item_authors = []
        self.item_editors = []
        self.raw_doi = False
        self.doi = False
        self.raw_ark = False
        self.ark = False
        self.project = False
        self.context = False
        self.cite_authors = ''
        self.cite_editors = ''
        self.cite_title = ''
        self.cite_year = ''
        self.cite_released = ''
        self.cite_modified = ''
        self.uri = ''
        self.coins = False

    def make_citation(self, json_ld):
        """ Make citation from metadata in the JSON-LD dict """
        if isinstance(json_ld, dict):
            if 'dc-terms:contributor' in json_ld:
                for p_item in json_ld['dc-terms:contributor']:
                    if p_item['label'] not in self.item_authors:
                        self.item_authors.append(p_item['label'])
            if 'dc-terms:creator' in json_ld:
                for p_item in json_ld['dc-terms:creator']:
                    if p_item['label'] not in self.item_editors:
                        self.item_editors.append(p_item['label'])
            if 'owl:sameAs' in json_ld:
                id_prefixes = StableIdentifer.ID_TYPE_PREFIXES
                for s_item in json_ld['owl:sameAs']:
                    if 'doi.org' in s_item['id']:
                        self.raw_doi = s_item['id'].replace('http://dx.doi.org/', '')
                        self.raw_doi = self.raw_doi.replace('https://doi.org/', '')
                        self.raw_doi = self.raw_doi.replace('http://doi.org/', '')
                        self.raw_doi = self.raw_doi.replace('https://doi.org/', '')
                        if id_prefixes['doi'] not in s_item['id']:
                            # replace the DOI with the current best URL from the
                            # StableIdentifer.ID_TYPE_PREFIXES
                            self.doi = id_prefixes['doi'] + self.raw_doi
                        else:
                            self.doi = s_item['id']
                    elif 'n2t.net/ark:' in s_item['id']:
                        self.raw_ark = s_item['id'].replace('http://n2t.net/ark:', '')
                        self.raw_ark = self.raw_ark.replace('https://n2t.net/ark:', '')
                        if id_prefixes['ark'] not in s_item['id']:
                            # replace the DOI with the current best URL from the
                            # StableIdentifer.ID_TYPE_PREFIXES
                            self.ark = id_prefixes['ark'] + self.raw_ark 
                        else:
                            self.ark = s_item['id']
            if len(self.item_authors) < 1:
                self.item_authors = self.item_editors
            if 'dc-terms:issued' in json_ld:
                published = datetime.datetime.strptime(json_ld['dc-terms:issued'], '%Y-%m-%d').date()
            else:
                published = datetime.datetime.now()
            if 'dc-terms:modified' in json_ld:
                self.cite_modified = datetime.datetime.strptime(json_ld['dc-terms:modified'], '%Y-%m-%d').date()
            else:
                self.cite_modified = datetime.datetime.now()
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
            self.cite_modified = self.cite_modified.strftime('%Y-%m-%d')
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
        self.item_type = False
        self.geojson = False
        self.start_lat = 0
        self.start_lon = 0
        self.start_zoom = 7
        self.proj_geo_specificity = 0
        self.proj_geo_note = False

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
                hide_points = False
                if self.item_type == 'projects':
                    # we can hide points from projects with polygons
                    for feature in json_ld['features']:
                        if 'Polygon' in feature['geometry']['type']:
                            hide_points = True
                for feature in json_ld['features']:
                    show_feature = True
                    if 'Polygon' in feature['geometry']['type']:
                        self.start_zoom = 6
                    elif feature['geometry']['type'] == 'Point':
                        lats.append(feature['geometry']['coordinates'][1])
                        lons.append(feature['geometry']['coordinates'][0])
                        if hide_points:
                            show_feature = False # hide this, because we've got a project
                    if 'location-precision-note' in feature['properties']:
                        if 'security' in feature['properties']['location-precision-note'] \
                           and feature['geometry']['type'] == 'Point':
                            show_feature = False
                    if 'reference-type' in feature['properties']:
                        if feature['properties']['reference-type'] == 'inferred':
                            if self.proj_geo_specificity < 0:
                                # we have a case with an inferred location
                                # but a project that generally obscures location
                                # So, make a new polygon feature and hide this point
                                show_feature = False  # don't show the inferred location item, instead show a polygon region for it
                                sec_note = 'All project location data approximated as a security precaution.'
                                geo_props = feature['properties']
                                geo_props['location-precision'] = abs(self.proj_geo_specificity)
                                geo_props['location-precision-note'] = sec_note
                                gmt = GlobalMercator()
                                geotile = gmt.lat_lon_to_quadtree(feature['geometry']['coordinates'][1],
                                                                  feature['geometry']['coordinates'][0],
                                                                  abs(self.proj_geo_specificity))
                                tile_bounds = gmt.quadtree_to_lat_lon(geotile)
                                item_polygon = Polygon([[(tile_bounds[1], tile_bounds[0]),
                                                         (tile_bounds[1], tile_bounds[2]),
                                                         (tile_bounds[3], tile_bounds[2]),
                                                         (tile_bounds[3], tile_bounds[0]),
                                                         (tile_bounds[1], tile_bounds[0])
                                                         ]])
                                item_f_poly = Feature(geometry=item_polygon)
                                item_f_poly.properties.update(geo_props)
                                if 'location-note' in item_f_poly.properties:
                                    if 'no intentional reduction' in item_f_poly.properties['location-note']:
                                        # so we don't confuse messages.
                                        item_f_poly.properties['location-note'] = 'This location information is inferred. ' + sec_note
                                    else:
                                        item_f_poly.properties['location-note'] += ' ' + sec_note
                                if 'location-region-note' in item_f_poly.properties:
                                    if 'center' in  item_f_poly.properties['location-region-note']:
                                        item_f_poly.properties['location-region-note'] = 'This location approximates the '\
                                                                                         'location of the record containing this item.'
                                    item_f_poly.properties['location-region-note'] += ' ' + sec_note
                                use_features.append(item_f_poly)
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

    REL_PREDICATES = ['skos:closeMatch', 'skos:exactMatch']
    REL_MEASUREMENTS = ['cidoc-crm:P67_refers_to',
                        'oc-gen:has-technique',
                        'rdfs:range']
    ITEM_REL_PREDICATES = ['skos:closeMatch',
                           'skos:exactMatch',
                           'owl:sameAs',
                           'skos:related',
                           'skos:broader',
                           'dc-terms:references',
                           'dc-terms:hasVersion',
                           'http://nomisma.org/ontology#hasTypeSeriesItem']
    HIDE_PREDICATES = [
        'foaf:depiction'
    ]

    def __init__(self):
        self.linked_predicates = False
        self.linked_types = False
        self.read_vocab_graph = None
        self.annotations = []  # annotations on entities found in observations
        self.item_annotations = []  # annotations on the main entity of the JSON-LD
        self.item_dc_metadata = []  # dublin-core annotations on the main entity of the JSON-LD
        self.measurement_meta = {}  # measurement metadata for predicates
        self.related_tables = []  # references to related tables
        self.project = False
        dc_terms_obj = DCterms()
        self.ITEM_DC_METADATA_PREDICATES = dc_terms_obj.get_dc_terms_list()
        rp = RootPath()
        self.base_url = rp.get_baseurl()

    def make_linked_data(self, json_ld):
        """ Makes a list of linked data annotations that have unique combinations of predicates and objects
        """
        output = False
        ld_found = self.make_linked_data_lists(json_ld)
        if ld_found and self.linked_predicates is not False:
            # using an ordered dict to make sure we can more easily have unique combos of preds and objects
            temp_annotations = LastUpdatedOrderedDict()
            if ItemKeys.PREDICATES_OCGEN_HASOBS in json_ld:
                for obs_item in json_ld[ItemKeys.PREDICATES_OCGEN_HASOBS]:
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
                                                act_types = self.linked_types[act_type_oc_id]
                                                for act_type in act_types:
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
                            act_obj['query'] = self.make_query_parameter(pred_uri_key, obj_uri_key)
                            objects_list.append(act_obj)
                        act_annotation['objects'] = objects_list
                    if len(act_annotation['oc_objects']) > 0:
                        oc_objects_list = []
                        for obj_uri_key, act_obj in act_annotation['oc_objects'].items():
                            act_obj['query'] = self.make_query_parameter(pred_uri_key, obj_uri_key)
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
                                    link_assertion['slug'] = False
                                    ent = Entity()
                                    found = ent.dereference(link_assertion['id'])
                                    if found:
                                        link_assertion['vocab_uri'] = ent.vocab_uri
                                        link_assertion['vocabulary'] = ent.vocabulary
                                        link_assertion['slug'] = ent.slug
                                        if ent.vocab_uri is False \
                                           and self.project.uuid is not False:
                                            link_assertion['vocab_uri'] = self.base_url \
                                                                          + '/projects/' \
                                                                          + self.project.uuid
                                            link_assertion['vocabulary'] = settings.CANONICAL_SITENAME \
                                                                           + ' :: ' + self.project.label
                                    if subject_type == 'predicates':
                                        linked_predicates.append(link_assertion)
                                    else:
                                        if link_assertion['subject'] in linked_types:
                                            linked_types[link_assertion['subject']].append(link_assertion)
                                        else:
                                            linked_types[link_assertion['subject']] = [link_assertion]
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
                if act_pred in self.HIDE_PREDICATES:
                    # we need to hide this predicate, so skip it.
                    pass
                elif act_pred in json_ld:
                    add_annotation = True
                    p_uri = act_pred
                    p_label = act_pred
                    p_vocab = False
                    p_vocab_uri = False
                    p_slug = False
                    ent = Entity()
                    found = ent.dereference(act_pred)
                    if found:
                        p_uri = ent.uri
                        p_label = ent.label
                        p_vocab = ent.vocabulary
                        p_vocab_uri = ent.vocab_uri
                        p_slug = ent.slug
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
                            # this is a type related to a predicate, don't consider as an annotation
                            add_annotation = False
                        elif 'owl:sameAs' == act_pred and settings.CANONICAL_HOST:
                            # this is same as annotation with something in open context, not to to add
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
                        ld_obj['query'] = False
                        ent = Entity()
                        found = ent.dereference(uri)
                        if found:
                            ld_obj['vocabulary'] = ent.vocabulary
                            ld_obj['vocab_uri'] = ent.vocab_uri
                            if p_slug is not False:
                                # don't make a query for a predicate
                                ld_obj['query'] = self.make_query_parameter(p_slug, ent.slug, item_type)
                            if ent.vocab_uri is False \
                               and self.project.uuid is not False:
                                ld_obj['vocab_uri'] = self.base_url \
                                                      + '/projects/' \
                                                      + self.project.uuid
                                ld_obj['vocabulary'] = settings.CANONICAL_SITENAME \
                                                       + ' :: ' + str(self.project.label)
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
                if act_pred in self.HIDE_PREDICATES:
                    # we need to hide this predicate, so skip it.
                    pass
                elif act_pred in json_ld:
                    add_annotation = True
                    p_uri = act_pred
                    p_label = act_pred
                    p_vocab = False
                    p_vocab_uri = False
                    p_slug = False
                    ent = Entity()
                    found = ent.dereference(act_pred)
                    if found:
                        p_uri = ent.uri
                        p_label = ent.label
                        p_vocab = ent.vocabulary
                        p_vocab_uri = ent.vocab_uri
                        p_slug = ent.slug
                    act_i_ass = {'id': p_uri,
                                 'type': 'Standard',
                                 'label': p_label,
                                 'vocabulary': p_vocab,
                                 'vocab_uri': p_vocab_uri,
                                 'objects': []}
                    for ld_obj in json_ld[act_pred]:
                        uri = ld_obj['id']
                        if not ('http://' in ld_obj['id']\
                           or 'https://' in ld_obj['id'])\
                           and 'rdfs:isDefinedBy' in ld_obj:
                            # special case for inferred relationship
                            uri = ld_obj['rdfs:isDefinedBy']
                            ld_obj['id'] = uri
                        ld_obj['vocabulary'] = False
                        ld_obj['vocab_uri'] = False
                        ld_obj['query'] = False
                        ent = Entity()
                        found = ent.dereference(uri)
                        if found:
                            ld_obj['vocabulary'] = ent.vocabulary
                            ld_obj['vocab_uri'] = ent.vocab_uri
                            if p_slug is not False:
                                ld_obj['query'] = self.make_query_parameter(p_slug, ent.slug)
                            if ent.vocab_uri is False \
                               and self.project.uuid is not False:
                                ld_obj['vocab_uri'] = self.base_url \
                                    + '/projects/' \
                                    + self.project.uuid
                                if isinstance(self.project.label, str):
                                    ld_obj['vocabulary'] = settings.CANONICAL_SITENAME \
                                        + ' :: ' + self.project.label
                                else:
                                    ld_obj['vocabulary'] = settings.CANONICAL_SITENAME
                        if 'opencontext' in ld_obj['id'] and \
                           '/tables/' in ld_obj['id']:
                            # we have an open context table!
                            ld_obj['table_id'] = ld_obj['id'].replace((settings.CANONICAL_HOST + '/tables/'), '')
                            self.related_tables.append(ld_obj)
                        else:
                            # treat as normal linked data
                            act_i_ass['objects'].append(ld_obj)
                    if len(act_i_ass['objects']) < 1:
                        add_annotation = False
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

    def make_query_parameter(self,
                             predicate,
                             obj,
                             item_type=False):
        """ makes a query parameter depending on the value
            of the predicate slug
        """
        if 'http://' in predicate or 'https://' in predicate:
            predicate = urlquote_plus(predicate)
        if 'http://' in obj or 'https://' in obj:
            obj = urlquote_plus(obj)
        dc_terms_obj = DCterms()
        if predicate in dc_terms_obj.DC_SLUG_TO_FIELDS:
            # there's a query parameter for this dc-terms metadata
            query = dc_terms_obj.DC_SLUG_TO_FIELDS[predicate]
            query += '=' + obj
        elif item_type == 'predicates':
            query = 'prop=' + obj
        elif item_type == 'types':
            query = 'obj=' + obj
        else:
            query = 'prop=' + predicate + '---' + obj
        return query
