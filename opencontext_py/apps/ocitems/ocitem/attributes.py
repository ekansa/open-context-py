import time
import json
from collections import OrderedDict
from django.conf import settings
from django.db import models
from django.db.models import Q
from opencontext_py.libs.rootpath import RootPath
from opencontext_py.libs.languages import Languages
from opencontext_py.libs.isoyears import ISOyears
from opencontext_py.libs.general import LastUpdatedOrderedDict, DCterms
from opencontext_py.apps.entities.uri.models import URImanagement
from opencontext_py.apps.ocitems.ocitem.itemkeys import ItemKeys
from opencontext_py.apps.ocitems.ocitem.caching import ItemGenerationCache
from opencontext_py.apps.ocitems.ocitem.partsjsonld import PartsJsonLD
from opencontext_py.apps.ocitems.mediafiles.models import Mediafile
from opencontext_py.apps.ocitems.assertions.models import Assertion
from opencontext_py.apps.ocitems.assertions.containment import Containment
from opencontext_py.apps.ocitems.predicates.models import Predicate
from opencontext_py.apps.ocitems.octypes.models import OCtype
from opencontext_py.apps.ocitems.strings.models import OCstring
from opencontext_py.apps.ocitems.identifiers.models import StableIdentifer
from opencontext_py.apps.ldata.linkannotations.models import LinkAnnotation
from opencontext_py.apps.ldata.linkannotations.equivalence import LinkEquivalence
from opencontext_py.apps.ldata.linkannotations.authorship import Authorship
from opencontext_py.apps.ldata.linkannotations.licensing import Licensing


class ItemAttributes():
    """ Methods for adding descriptive attributes and metadata 
        data to an Open Context Item JSON-LD object
    """
    
    # predicates not for use in observations
    NO_OBS_ASSERTION_PREDS = [
        'skos:note'
    ]
    
    NUMERIC_OBJECT_TYPES = [
        'xsd:integer',
        'xsd:double',
        'xsd:boolean'
    ]

    def __init__(self):
        self.proj_context_json_ld = None
        self.project_uuid = None
        self.manifest = None
        self.assertion_hashes = False
        self.assertions = None
        self.mediafiles = None
        self.link_annotations = None
        self.stable_ids = None
        self.obs_list = []
        self.item_pred_objs = {} # predicate entity objects, with uuid as a key 
        self.string_obj_dict = {}  # OCstring objects, in a dict, with uuid as key
        self.manifest_obj_dict = {}  # manifest objects, in a dict with uuid as key
        self.assertion_author_uuids = {
            # uuids of DC contribuors (persons/orgs) found in item assertions
            ItemKeys.PREDICATES_DCTERMS_CONTRIBUTOR: [],
            # uuids of DC creators (persons/orgs) found in item assertions
            ItemKeys.PREDICATES_DCTERMS_CREATOR: []
        }
        self.dc_assertions = {}  # dublin core assertions. We add these last, just for aesthetics
        self.dc_title = None  # dublin core title attribute, to use if not via default programatic way
        dc_terms_obj = DCterms()
        self.dc_metadata_preds = dc_terms_obj.get_dc_terms_list()
        self.dc_author_preds = dc_terms_obj.get_dc_authors_list()
        self.dc_inherit_preds = [  # these are dc-terms predicates items can inherit from a project
            ItemKeys.PREDICATES_DCTERMS_CONTRIBUTOR,
            ItemKeys.PREDICATES_DCTERMS_CREATOR,
            ItemKeys.PREDICATES_DCTERMS_TEMPORAL,
            ItemKeys.PREDICATES_DCTERMS_LICENSE
        ]
        self.item_gen_cache = ItemGenerationCache()
        rp = RootPath()
        self.base_url = rp.get_baseurl()
        self.class_uri_list = []  # uris of item classes used in this item
        self.parent_context_list = []  # list of parent context labels, used for making a dc-terms:Title

    def get_db_item_attributes(self):
        """ gets item attributes (other than context, space, temporal) that describe
            an item
        """
        self.get_db_mediafile_objs()
        self.get_db_assertions()
        self.get_db_link_anotations()
        self.get_db_stable_ids()

    def add_json_ld_attributes(self, json_ld):
        """ adds attribute information to the JSON-LD """
        json_ld = self.add_json_ld_mediafiles(json_ld)
        json_ld = self.add_json_ld_descriptive_assertions(json_ld)
        json_ld = self.add_json_ld_link_annotations(json_ld)
        json_ld = self.add_json_ld_dc_metadata(json_ld)
        json_ld = self.add_json_ld_stable_ids(json_ld)
        return json_ld
    
    def add_json_ld_mediafiles(self, json_ld):
        """
        adds media files
        """
        if self.mediafiles is not None:
            media_list = []
            thumb_missing = True
            pdf_doc = False
            for media_item in self.mediafiles:
                list_item = LastUpdatedOrderedDict()
                list_item['id'] = media_item.file_uri
                list_item['type'] = media_item.file_type
                if media_item.file_type == 'oc-gen:thumbnail':
                    thumb_missing = False
                list_item['dc-terms:hasFormat'] = media_item.mime_type_uri
                if 'application/pdf' in media_item.mime_type_uri:
                    pdf_doc = True
                list_item['dcat:size'] = float(media_item.filesize)
                if self.assertion_hashes:
                    if hasattr(media_item, 'hash_id'):
                        list_item['hash_id'] = media_item.hash_id
                    else:
                        list_item['hash_id'] = media_item.id
                media_list.append(list_item)
            if thumb_missing and pdf_doc:
                # we have a PDF with a default thumbnail
                list_item = LastUpdatedOrderedDict()
                list_item['id'] = Mediafile.PDF_DEFAULT_THUMBNAIL
                list_item['type'] = 'oc-gen:thumbnail'
                media_list.append(list_item)
            if self.manifest.item_type == 'media':
                json_ld['oc-gen:has-files'] = media_list
            else:
                # Use the depiction predicate, since it depects the item described
                # like project hero images
                json_ld['foaf:depiction'] = media_list
        return json_ld

    def add_json_ld_descriptive_assertions(self, json_ld):
        """
        adds descriptive assertions (descriptive properties, non spatial containment links)
        to items, as parts of Observations
        """
        observations = []
        working_obs = LastUpdatedOrderedDict()
        act_obs = LastUpdatedOrderedDict()
        for assertion in self.assertions:
            act_obs_num = assertion.obs_num
            if assertion.predicate_uuid in self.NO_OBS_ASSERTION_PREDS:
                # we've got a predicate that does not belong in an observation
                json_ld = self.add_json_ld_direct_assertion(json_ld,
                                                            assertion)
            else:    
                if act_obs_num not in working_obs:
                    # we've got a new observation, so make a new observation object for it
                    act_obs = self.make_json_ld_obs_dict_w_metadata(assertion)
                    working_obs[act_obs_num] = act_obs
                else:
                    act_obs = working_obs[act_obs_num]
                act_obs = self.add_json_ld_assertion_predicate_objects(act_obs,
                                                                       assertion)
                working_obs[act_obs_num] = act_obs
        # now that we've gotten observations made,
        # add them to the final list of observations
        for obs_num in self.obs_list:
            if obs_num in working_obs:
                act_obs = working_obs[obs_num]
                observations.append(act_obs)
        if len(observations) > 0:
            json_ld[ItemKeys.PREDICATES_OCGEN_HASOBS] = observations
        return json_ld
    
    def add_json_ld_assertion_predicate_objects(self,
                                                act_obs,
                                                assertion):
        """ adds value objects to for an assertion predicate """
        # we've already looked up objects from the manifest
        parts_json_ld = PartsJsonLD()
        parts_json_ld.proj_context_json_ld = self.proj_context_json_ld
        parts_json_ld.manifest_obj_dict = self.manifest_obj_dict
        if assertion.object_type == 'persons':
            # add a stable ID to person items, but only if they are ORCID IDs
            parts_json_ld.stable_id_predicate = ItemKeys.PREDICATES_FOAF_PRIMARYTOPICOF
            parts_json_ld.stable_id_prefix_limit = StableIdentifer.ID_TYPE_PREFIXES['orcid']
        pred_obj = self.get_pred_obj_by_uuid(parts_json_ld,
                                             assertion.predicate_uuid)
        pred_slug_uri = pred_obj['slug_uri']
        if isinstance(pred_slug_uri, str):
            if pred_slug_uri in act_obs:
                act_obj_list = act_obs[pred_slug_uri]
            else:
                act_obj_list = []
            act_obj = None
            add_literal_object = True
            if assertion.object_type == 'xsd:string':
                # look for the string uuid in the dict of string objects we already
                # got from the database
                if assertion.object_uuid in self.string_obj_dict:
                    act_obj = LastUpdatedOrderedDict()
                    act_obj['id'] = '#string-' + str(assertion.object_uuid)
                    string_obj = self.string_obj_dict[assertion.object_uuid]
                    lang_obj = Languages()
                    act_obj['xsd:string'] = lang_obj.make_json_ld_value_obj(string_obj.content,
                                                                            string_obj.localized_json)
                else:
                    act_obj = 'string content missing'
            elif assertion.object_type == 'xsd:date':
                act_obj = assertion.data_date.date().isoformat()
            elif assertion.object_type == 'xsd:integer':
                try:
                    act_obj = int(float(assertion.data_num))
                except:
                    act_obj = None
            elif assertion.object_type in self.NUMERIC_OBJECT_TYPES:
                act_obj = assertion.data_num
            else:
                # the object of is something identified by a URI, not a literal
                # so we're using function in the parts_json_ld to add the uri identified
                # object as a dict that has some useful information
                # {id, label, slug, sometimes class}
                add_literal_object = False
                # some assertions use predicates equiv. to DC-Terms creators or contributors
                self.add_assertion_dc_authors(pred_obj,
                                              assertion.object_uuid)
                #
                if self.assertion_hashes:
                    # we need to add the assertion hash identifier so as to be able
                    # to identify assertions for editing purposes
                    act_obs = parts_json_ld.addto_predicate_list(act_obs,
                                                                 pred_slug_uri,
                                                                 assertion.object_uuid,
                                                                 assertion.object_type,
                                                                 False,
                                                                 assertion.hash_id)
                else:
                    # normal default assertion creation, without identification of
                    # the assertion's hash ID
                    act_obs = parts_json_ld.addto_predicate_list(act_obs,
                                                                 pred_slug_uri,
                                                                 assertion.object_uuid,
                                                                 assertion.object_type)
            if act_obj is not None and add_literal_object:
                if self.assertion_hashes:
                    # we need to add the assertion hash identifier so as to be able
                    # to identify assertions for editing purposes
                    if not isinstance(act_obj, dict):
                        literal = act_obj
                        act_obj = LastUpdatedOrderedDict()
                        act_obj['literal'] = literal
                    act_obj['hash_id'] = assertion.hash_id
                act_obj_list.append(act_obj)
            if len(act_obj_list) > 0 and add_literal_object:
                # only add a list of literal objects if they are literal objects :)
                act_obs[pred_slug_uri] = act_obj_list
        return act_obs

    def get_pred_obj_by_uuid(self, parts_json_ld, predicate_uuid):
        """ gets a 'pred_obj' which is a dict returned from the
            parts_json_ld method 'get_json_ld_predicate_slug_uri'
        """
        if predicate_uuid in self.item_pred_objs:
            pred_obj = self.item_pred_objs[predicate_uuid]
        else:
            pred_obj = parts_json_ld.get_json_ld_predicate_slug_uri(predicate_uuid,
                                                                    True)
            pred_obj = self.check_pred_dc_author(pred_obj)
            # now cache it in memory so we don't have to go looking to see if this
            # has dublin core equivalence again
            self.item_pred_objs[predicate_uuid] = pred_obj
        return pred_obj

    def check_pred_dc_author(self, pred_obj):
        """ some predicates have equivalence relations with DC-terms:contributor
            or DC-terms:creator properties. This method
            checks to see if a predicate has some sort of equivalence to
            a dublin core contributor or creator URI. If so
        """
        if isinstance(pred_obj, dict):
            pred_obj['dc_contrib'] = False
            pred_obj['dc_creator'] = False
            if 'ent' in pred_obj:
                pred_ent = pred_obj['ent']
                if hasattr(pred_ent, 'item_json_ld'):
                    if isinstance(pred_ent.item_json_ld, dict):
                        pred_json_ld = pred_ent.item_json_ld
                        le = LinkEquivalence()
                        equiv_keys = le.get_identifier_list_variants(LinkAnnotation.PREDS_SBJ_EQUIV_OBJ)
                        dc_contrib_uris = le.get_identifier_list_variants(ItemKeys.PREDICATES_DCTERMS_CONTRIBUTOR)
                        dc_creator_uris = le.get_identifier_list_variants(ItemKeys.PREDICATES_DCTERMS_CREATOR)
                        for equiv_key in equiv_keys:
                            if equiv_key in pred_json_ld :
                                if isinstance(pred_json_ld[equiv_key], list):
                                    for pred_equiv in pred_json_ld[equiv_key]:
                                        uri = None
                                        if 'id' in pred_equiv:
                                            uri = pred_equiv['id']
                                        elif '@id' in pred_equiv:
                                            uri = pred_equiv['@id']
                                        if uri in dc_contrib_uris:
                                            pred_obj['dc_contrib'] = True
                                            break
                                        if uri in dc_creator_uris:
                                            pred_obj['dc_creator'] = True
                                            break
                            if pred_obj['dc_contrib'] or pred_obj['dc_creator']:
                                # no need to keep searching, we found equivalence
                                break
        return pred_obj
                                            
    def add_assertion_dc_authors(self, pred_obj, object_uuid):
        """ adds uuids of author objects if the predicate object says it
            is a dc-terms contributor or a dc-terms creator equivalent
        """
        if isinstance(pred_obj, dict):
            if 'dc_contrib' in pred_obj:
                pred_contrib = ItemKeys.PREDICATES_DCTERMS_CONTRIBUTOR
                if pred_obj['dc_contrib'] and \
                   object_uuid not in self.assertion_author_uuids[pred_contrib]:
                    # uuids of DC contribuors (persons/orgs) found in item assertions
                    self.assertion_author_uuids[pred_contrib].append(object_uuid)
            if 'dc_creator' in pred_obj:
                pred_create = ItemKeys.PREDICATES_DCTERMS_CREATOR
                if pred_obj['dc_creator'] and \
                   object_uuid not in self.assertion_author_uuids[pred_create]:
                    # uuids of DC creators (persons/orgs) found in item assertions
                    self.assertion_author_uuids[pred_create].append(object_uuid)

    def add_json_ld_direct_assertion(self, json_ld, assertion):
        """ adds an JSON-LD for an assertion that is made directly
            to the item, and is not part of an observation
        """
        if assertion.predicate_uuid in self.NO_OBS_ASSERTION_PREDS:
            # these predicates describe the item, but not in an observation
            act_obj = None
            if assertion.object_type == 'xsd:string':
                # look for the string uuid in the dict of string objects we already
                # got from the database
                if assertion.object_uuid in self.string_obj_dict:
                    string_obj = self.string_obj_dict[assertion.object_uuid]
                    lang_obj = Languages()
                    act_obj = lang_obj.make_json_ld_value_obj(string_obj.content,
                                                              string_obj.localized_json)
                else:
                    act_obj = 'string content missing'
            elif assertion.object_type == 'xsd:date':
                act_obj = assertion.data_date.date().isoformat()
            elif assertion.object_type == 'xsd:integer':
                try:
                    act_obj = int(float(assertion.data_num))
                except:
                    act_obj = None
            elif assertion.object_type in self.NUMERIC_OBJECT_TYPES:
                act_obj = assertion.data_num
            else:
                # the object of is something identified by a URI, not a literal
                ent = parts_json_ld.get_new_object_item_entity(
                        assertion.object_uuid,
                        assertion.object_type
                        )
                if ent is not False:
                    act_obj = entity.uri
            if act_obj is not None:
                json_ld[assertion.predicate_uuid] = act_obj
        return json_ld
    
    def make_json_ld_obs_dict_w_metadata(self, assertion):
        """ makes metadata for an observation """
        act_obs = LastUpdatedOrderedDict()
        act_obs['id'] = "#obs-" + str(assertion.obs_num)
        if isinstance(assertion.obs_node, str):
            if len(assertion.obs_node) > 1:
                if assertion.obs_node[:1] == '#':
                    act_obs['id'] = str(assertion.obs_node)
        act_obs[ItemKeys.PREDICATES_OCGEN_SOURCEID] = assertion.source_id
        if assertion.obs_num >= 0 and assertion.obs_num != 100:
            act_obs[ItemKeys.PREDICATES_OCGEN_OBSTATUS] = 'active'
        else:
            act_obs[ItemKeys.PREDICATES_OCGEN_OBSTATUS] = 'deprecated'
        # now go get observation meta
        obs_meta = self.item_gen_cache.get_observation_metadata(assertion.source_id,
                                                                assertion.obs_num)
        if obs_meta is not False:
            act_obs[ItemKeys.PREDICATES_OCGEN_OBSLABEL] = obs_meta.label
            if isinstance(obs_meta.note, str):
                if len(obs_meta.note) > 0:
                    act_obs[ItemKeys.PREDICATES_OCGEN_OBSNOTE] = obs_meta.note
        act_obs['type'] = 'oc-gen:observations'
        return act_obs
    
    def add_json_ld_stable_ids(self, json_ld):
        """
        adds stable identifier information to an item's JSON-LD dictionary object
        """
        if self.stable_ids is not False:
            if len(self.stable_ids) > 0:
                stable_id_list = []
                for stable_id in self.stable_ids:
                    if stable_id.stable_type in settings.STABLE_ID_URI_PREFIXES:
                        uri = settings.STABLE_ID_URI_PREFIXES[stable_id.stable_type]
                        uri += str(stable_id.stable_id)
                        id_dict = {'id': uri}
                        stable_id_list.append(id_dict)
                if self.manifest.item_type == 'persons' and len(stable_id_list) > 0:
                    # persons with ORCID ids use the foaf:primarytopic predicate to link to ORCID
                    primary_topic_list = []
                    same_as_list = []
                    for id_dict in stable_id_list:
                        if 'http://orcid.org' in id_dict['id']:
                            primary_topic_list.append(id_dict)
                        else:
                            same_as_list.append(id_dict)
                    stable_id_list = same_as_list  # other types of identifiers use as owl:sameAs
                    if len(primary_topic_list) > 0:
                        json_ld[ItemKeys.PREDICATES_FOAF_PRIMARYTOPICOF] = primary_topic_list
                if len(stable_id_list) > 0:
                    json_ld['owl:sameAs'] = stable_id_list
        return json_ld

    def add_json_ld_link_annotations(self, json_ld):
        """
        adds linked data annotations (typically referencing URIs from
        outside Open Context)
        """
        if self.link_annotations is not False:
            if len(self.link_annotations) > 0:
                parts_json_ld = PartsJsonLD()
                parts_json_ld.proj_context_json_ld = self.proj_context_json_ld
                parts_json_ld.manifest_obj_dict = self.manifest_obj_dict
                for la in self.link_annotations:
                    tcheck = URImanagement.get_uuid_from_oc_uri(la.object_uri, True)
                    if tcheck is False:
                        # this item is NOT from open context
                        item_type = False
                    else:
                        # an Open Context item
                        item_type = tcheck['item_type']
                    if item_type == 'persons':
                        # add a stable ID to person items, but only if they are ORCID IDs
                        parts_json_ld.stable_id_predicate = ItemKeys.PREDICATES_FOAF_PRIMARYTOPICOF
                        parts_json_ld.stable_id_prefix_limit = StableIdentifer.ID_TYPE_PREFIXES['orcid']
                    # this shortens URIs in item-context declared namespaces
                    # to make a compact URI (prefixed), as the act_pred
                    act_pred = URImanagement.prefix_common_uri(la.predicate_uri)
                    if act_pred not in self.dc_author_preds \
                       and act_pred not in self.dc_inherit_preds \
                       and act_pred not in self.dc_metadata_preds:
                        # the act_prec is not a dublin core predicate, so we're OK to add it
                        # now, not later.
                        json_ld = parts_json_ld.addto_predicate_list(json_ld,
                                                                     act_pred,
                                                                     la.object_uri,
                                                                     item_type)
                    else:
                        # we've got dublin core assertions, cache these in the dict_object
                        # dc_assertions so they get added LAST, after other asserttions
                        self.dc_assertions = parts_json_ld.addto_predicate_list(self.dc_assertions,
                                                                                act_pred,
                                                                                la.object_uri,
                                                                                item_type)
        return json_ld
    
    def add_json_ld_dc_metadata(self, json_ld):
        """ adds dublin core metadata to the json_ld
            does this in a regular, predictable order for
            aethetic reasons
        """
        # start with the dc-terms:title
        json_ld = self.add_json_ld_dc_title(json_ld)
        # now add published and modified DC-terms properties
        if self.manifest.published is not None and self.manifest.published is not False:
            # we have a publication date
            json_ld[ItemKeys.PREDICATES_DCTERMS_PUBLISHED] = self.manifest.published.date().isoformat()
        if self.manifest.revised is not None and self.manifest.revised is not False:
            # the 'revised' attribute is equivalent to the dc-terms:modified property
            json_ld[ItemKeys.PREDICATES_DCTERMS_MODIFIED] = self.manifest.revised.date().isoformat()
        # then add dc-terms:contributors, and creators, from item assertion equivalances to
        # dc-term authors
        json_ld = self.add_json_ld_dc_author_from_item(json_ld)
        # then other dc-terms properties made directly to the item
        # this is done to preserve a consistent order of listing dc-term properties in the JSON-LD
        json_ld = self.add_json_ld_dc_other_from_item(json_ld)
        # now add json_ld that may be interited from the parent project of the item
        json_ld = self.add_json_ld_dc_metadata_inherited(json_ld)
        # now add 'dc-terms:part-of' project information
        json_ld = self.add_json_ld_dc_metadata_partof(json_ld)
        return json_ld
    
    def add_json_ld_dc_title(self, json_ld):
        """ adds the dublin core title to the JSON-LD """
        if not isinstance(self.dc_title, str) and 'label' in json_ld:
            self.dc_title = json_ld['label']
            if len(self.parent_context_list) > 0:
                parents = '/'.join(self.parent_context_list)
                self.dc_title += ' from ' + parents
        if isinstance(self.dc_title, str):
            json_ld[ItemKeys.PREDICATES_DCTERMS_TITLE] = self.dc_title
        return json_ld
    
    def add_json_ld_dc_author_from_item(self, json_ld):
        """ adds dublin core author (contributor, creator) metadata to the JSON-LD
        
            The ORDER of authors is important, because it reflects the relative
            significance of their contribution to a publication.
            
            Author information comes from a variety of sources:
            (1) Linked data annotations directly to an item
            (2) Assertions using predicates that have an equivalence to a
                dublin core contributor or creator property
            (3) Project authoriship (via the self.add_json_ld_dc_metadata_inherited method)
            (4) Parent project authorship (via the self.add_json_ld_dc_metadata_inherited method)
        """
        # we've already looked up objects from the manifest
        parts_json_ld = PartsJsonLD()
        parts_json_ld.proj_context_json_ld = self.proj_context_json_ld
        parts_json_ld.manifest_obj_dict = self.manifest_obj_dict
        # add a stable ID to person items, but only if they are ORCID IDs
        parts_json_ld.stable_id_predicate = ItemKeys.PREDICATES_FOAF_PRIMARYTOPICOF
        parts_json_ld.stable_id_prefix_limit = StableIdentifer.ID_TYPE_PREFIXES['orcid']
        author_preds = [
            ItemKeys.PREDICATES_DCTERMS_CONTRIBUTOR,
            ItemKeys.PREDICATES_DCTERMS_CREATOR
        ]
        for author_pred in author_preds:
            if author_pred in self.dc_assertions:
                # add the 
                json_ld[author_pred] = self.dc_assertions[author_pred]
            if len(self.assertion_author_uuids[author_pred]) > 0:
                # we have contributors noted in contributor equiv preds in the item assertions
                for dc_auth_uuid in self.assertion_author_uuids[author_pred]:
                    json_ld = parts_json_ld.addto_predicate_list(json_ld,
                                                                 author_pred,
                                                                 dc_auth_uuid,
                                                                 'persons')
        return json_ld
    
    def add_json_ld_dc_other_from_item(self, json_ld):
        """ adds other DC-Term metadata annotated directly to the item
            
            To keep the order of predicates consistent, we make a list of
            "dc_item_preds" that lists the dc-terms properties of interest.
            
            Note, because authorship is somewhat more complicated by
            because of the possibility of item assertion predicates with
            equivalences to dc-terms contributors or creators, we skip
            looking at author related dc-terms properties in this method
        """
        dc_item_preds = [
            ItemKeys.PREDICATES_DCTERMS_TEMPORAL,
            ItemKeys.PREDICATES_DCTERMS_LICENSE,
        ]
        for dc_pred in self.dc_metadata_preds:
            if dc_pred not in dc_item_preds:
                dc_item_preds.append(dc_pred)
         # we've already looked up objects from the manifest
        parts_json_ld = PartsJsonLD()
        parts_json_ld.proj_context_json_ld = self.proj_context_json_ld
        parts_json_ld.manifest_obj_dict = self.manifest_obj_dict
        for dc_pred in dc_item_preds:
            if dc_pred in self.dc_assertions:
                # we've got item linked data annotations
                # that include this dc-term property. so add it to the
                # json-ld
                json_ld[dc_pred] = self.dc_assertions[dc_pred]
        return json_ld
    
    def add_json_ld_dc_metadata_inherited(self, json_ld):
        """ adds dublin core metadata inherited from the project to the JSON-LD
        
            Some metadata (dc-terms:contributor, dc-terms:creator,
            dc-terms:license, and dc-terms:temporal) will
            be inherited from the parent project IF
            the item does not yet have those metadata properties.
            
        """
        needed_dc_proj_preds = []
        for check_dc_pred in self.dc_inherit_preds:
            need_proj = True
            if check_dc_pred in json_ld:
                if len(json_ld[check_dc_pred]) > 0:
                    need_proj = False
            if need_proj:
                # we have a dc-terms predicate missing, so look
                # for it as inherited from the project
                 needed_dc_proj_preds.append(check_dc_pred)
        if len(needed_dc_proj_preds) > 0:
            # we need to find some dc-terms metadata in the project
            # so get project level metadata for these
            # we've already looked up objects from the manifest
            parts_json_ld = PartsJsonLD()
            parts_json_ld.proj_context_json_ld = self.proj_context_json_ld
            parts_json_ld.manifest_obj_dict = self.manifest_obj_dict
            # add a stable ID to person items, but only if they are ORCID IDs
            parts_json_ld.stable_id_predicate = ItemKeys.PREDICATES_FOAF_PRIMARYTOPICOF
            parts_json_ld.stable_id_prefix_limit = StableIdentifer.ID_TYPE_PREFIXES['orcid']
            # now get project wide metadata for inherited author assertions
            all_proj_metadata = self.item_gen_cache.get_all_project_metadata(self.manifest.project_uuid)
            if all_proj_metadata is not False:
                proj_meta = all_proj_metadata['project']
                parent_proj_meta = all_proj_metadata['parent-project']
                needed_dc_proj_author_preds = []
                for dc_pred in needed_dc_proj_preds:
                    # get the right type of author annotations
                    proj_dc_pred_annos = proj_meta[dc_pred]
                    if len(proj_dc_pred_annos) < 1 and isinstance(parent_proj_meta, dict):
                        # we don't have project author annotations of this type, so look
                        # for some from the parent project
                        proj_dc_pred_annos += parent_proj_meta[dc_pred]
                    for proj_anno in proj_dc_pred_annos:
                        # proj_anno is a Link Annotation
                        if dc_pred in self.dc_author_preds:
                            # the we're adding author information
                            json_ld = parts_json_ld.addto_predicate_list(json_ld,
                                                                         dc_pred,
                                                                         proj_anno.object_uri,
                                                                         'persons')
                        else:
                            # we're a non-author (person) object to the dc-terms linked data
                             json_ld = parts_json_ld.addto_predicate_list(json_ld,
                                                                         dc_pred,
                                                                         proj_anno.object_uri,
                                                                         False)
        return json_ld
    
    def add_json_ld_dc_metadata_partof(self, json_ld):
        """ adds dublin core partof metadata to the JSON-LD
        
            This property indicates that an item is part of a larger
            body of work (an Open Context "project")
        """
        if self.manifest.uuid != self.manifest.project_uuid:
            # we've already looked up objects from the manifest
            parts_json_ld = PartsJsonLD()
            parts_json_ld.proj_context_json_ld = self.proj_context_json_ld
            parts_json_ld.manifest_obj_dict = self.manifest_obj_dict
            parts_json_ld.stable_id_predicate = ItemKeys.PREDICATES_OWL_SAMEAS
            json_ld = parts_json_ld.addto_predicate_list(json_ld,
                                                         ItemKeys.PREDICATES_DCTERMS_ISPARTOF,
                                                         self.manifest.project_uuid,
                                                         'projects')
        return json_ld
    
    def get_db_assertions(self):
        """ gets assertions that describe an item, except for assertions about spatial containment """
        self.assertions = Assertion.objects.filter(uuid=self.manifest.uuid) \
                                           .exclude(predicate_uuid=Assertion.PREDICATES_CONTAINS)\
                                           .exclude(visibility__lt=1)\
                                           .order_by('obs_num', 'sort')
        # now that we have some assertions, go prepare
        # lists of observations, and get objects of assertions into memory
        self.prep_assertions_lists_and_objects()
    
    def prep_assertions_lists_and_objects(self):
        """ prepares lists and objects from assertions. this is needed
            to organize assertions into observations and get needed
            assertion objects into memory
        """
        string_uuids = []  # list of unique string uuids in these assertions
        manifest_obj_uuids = []  # list of unique manifest object ids (for manifest lookup only)
        if self.assertions is not False:
            if len(self.assertions) > 0:
                for ass in self.assertions:
                    if ass.obs_num not in self.obs_list:
                        self.obs_list.append(ass.obs_num)
                    if ass.object_type == 'xsd:string':
                        if ass.object_uuid not in string_uuids:
                            string_uuids.append(ass.object_uuid)
                    elif ass.object_type in PartsJsonLD.ITEM_TYPE_MANIFEST_LIST:
                        if ass.object_uuid not in manifest_obj_uuids:
                            manifest_obj_uuids.append(ass.object_uuid)
        # now get the string objects that are the objects of some assertions                    
        self.get_db_string_objs(string_uuids)
        # now get manifest objects for objects of assertions
        self.get_db_related_manifest_objs(manifest_obj_uuids)
    
    def get_db_mediafile_objs(self):
        """ gets media file objects associated with the current item """
        if self.manifest.item_type == 'projects':
            # need to get a hero image if it exists
            self.mediafiles = Mediafile.objects\
                                       .filter(uuid=self.manifest.uuid,
                                               file_type='oc-gen:hero')
            if len(self.mediafiles) < 1:
                # check for hero images belonging to the parent project
                self.mediafiles = Mediafile.objects\
                                           .filter(uuid=self.manifest.project_uuid,
                                                   file_type='oc-gen:hero')
        elif self.manifest.item_type == 'media':
            # get the media files associated with this item type
            self.mediafiles = Mediafile.objects\
                                       .filter(uuid=self.manifest.uuid)\
                                       .order_by('-filesize')
        else:
            # not getting media file information
            pass
    
    def get_db_string_objs(self, string_uuids):
        """ gets strings associated with assertions. does it in 1 query to reduce time """
        if len(string_uuids) > 0:
            # we have assertions that reference strings, so now go and
            # retrieve all of these strings
            act_strings = OCstring.objects.filter(uuid__in=string_uuids)
            for act_string in act_strings:
                uuid = act_string.uuid
                self.string_obj_dict[uuid] = act_string
    
    def get_db_related_manifest_objs(self, manifest_obj_uuids):
        """ gets uuids of manifest objects associated with assertions.
            We prepare this list to reduce the number of database queries.
            Only some assertion object_types are OK
            (specified in the PartsJsonLD.ITEM_TYPE_MANIFEST_LIST), because
            other types of items need more queries than a simple manifest lookup.
        """
        if len(manifest_obj_uuids) > 0:
            parts_json_ld = PartsJsonLD()
            # get manifest objects items to use later in making JSON_LD
            parts_json_ld.get_manifest_objects_from_uuids(manifest_obj_uuids)
            self.manifest_obj_dict = parts_json_ld.manifest_obj_dict
    
    def get_db_link_anotations(self):
        """ gets linked data (using standard vocabularies, ontologies) assertions
            that describe an item
        """
        self.link_annotations = LinkAnnotation.objects\
                                              .filter(subject=self.manifest.uuid)\
                                              .order_by('predicate_uri', 'sort')
    
    def get_db_stable_ids(self):
        """ gets stable identifiers (DOIs, ARKs, ORCIDS) """
        self.stable_ids = StableIdentifer.objects.filter(uuid=self.manifest.uuid)
    
    