import copy
import datetime
import json
from django.conf import settings
from django.utils.encoding import force_text
from opencontext_py.libs.isoyears import ISOyears
from opencontext_py.libs.general import LastUpdatedOrderedDict, DCterms
from opencontext_py.libs.chronotiles import ChronoTile
from opencontext_py.libs.globalmaptiles import GlobalMercator

from opencontext_py.apps.all_items.models import (
    AllManifest,
    AllAssertion,
    AllHistory,
    AllResource,
    AllIdentifier,
    AllSpaceTime,
)
from opencontext_py.apps.all_items import configs
from opencontext_py.apps.all_items import hierarchy
from opencontext_py.apps.all_items import labels
from opencontext_py.apps.all_items import utilities
from opencontext_py.apps.all_items.representations import item
from opencontext_py.apps.all_items.representations.template_prep import (
    prepare_for_item_dict_solr_and_html_template,
    prepare_for_item_dict_html_template
)

from opencontext_py.apps.indexer import solr_utils 


# the list below defines predicates used for
# semantic equivalence in indexing
# linked data
LD_EQUIVALENT_PREDICATES = [
    'skos:closeMatch',
    'skos:exactMatch',
    'owl:sameAs',
    'foaf:isPrimaryTopicOf'
]

LD_IDENTIFIER_PREDICATES = [
    'owl:sameAs',
    'foaf:isPrimaryTopicOf'
]

LD_DIRECT_PREDICATES = [
    'http://nomisma.org/ontology#hasTypeSeriesItem',
    'http://erlangen-crm.org/current/P2_has_type',
    'http://www.wikidata.org/wiki/Property:P3328',
    'oc-gen:has-technique',
    'rdfs:range',
    'skos:example',
    'skos:related',
]

PERSISTENT_ID_ROOTS = [
    'https://doi.org',
    'http://doi.org',
    'https://dx.doi.org',
    'http://dx.doi.org',
    'https://n2t.net/ark:/',
    'http://n2t.net/ark:/',
    'https://orcid.org',
    'http://orcid.org'
]

LABELING_PREDICATE_KEYS = [
    'label',
    'skos:altLabel',
    'skos:prefLabel',
    'dc-terms:title',
]

# Don't index descriptive assertions where the
# predicate objects have the following uuids.
NO_INDEX_DESCRIPTION_PREDICATE_UUIDS = [
    configs.PREDICATE_CONTAINS_UUID,
    configs.PREDICATE_CONTAINS_UUID,
    configs.PREDICATE_LINK_UUID,
    configs.PREDICATE_LINKED_FROM_UUID,
]



# Default publication date, if the record does not exist.
# This should ONLY be the case for the very first example
# datasets in Open Context, before we got our metadata
# house in better order.
DEFAULT_PUBLISHED_DATETIME = datetime.date(2007, 1, 1)

# The delimiter for parts of an object value added to a
# solr field.
SOLR_VALUE_DELIM = solr_utils.SOLR_VALUE_DELIM 

FIELD_SUFFIX_CONTEXT = 'context_id'
FIELD_SUFFIX_PREDICATE = 'pred_id'
FIELD_SUFFIX_PROJECT = 'project_id'

ALL_CONTEXT_SOLR = 'obj_all' + SOLR_VALUE_DELIM + FIELD_SUFFIX_CONTEXT
ROOT_CONTEXT_SOLR = 'root' + SOLR_VALUE_DELIM + FIELD_SUFFIX_CONTEXT
ROOT_PREDICATE_SOLR = 'root' + SOLR_VALUE_DELIM + FIELD_SUFFIX_PREDICATE
ROOT_LINK_DATA_SOLR = 'ld' + SOLR_VALUE_DELIM + FIELD_SUFFIX_PREDICATE
ROOT_PROJECT_SOLR = 'root' + SOLR_VALUE_DELIM + FIELD_SUFFIX_PROJECT
ALL_PROJECT_SOLR = 'obj_all' + SOLR_VALUE_DELIM + FIELD_SUFFIX_PROJECT
EQUIV_LD_SOLR = 'skos_closematch' + SOLR_VALUE_DELIM + FIELD_SUFFIX_PREDICATE
JOIN_SOLR = 'join_uuids'
FILE_SIZE_SOLR = 'filesize'
FILE_MIMETYPE_SOLR = 'mimetype' + SOLR_VALUE_DELIM + FIELD_SUFFIX_PREDICATE
RELATED_SOLR_DOC_PREFIX = 'REL_'

# These item types may be in SKOS or OWL hiearchies.
ITEM_TYPES_FOR_CONCEPT_HIERARCHIES = [
    'predicates',
    'types',
    'class',
    'property',
]
# These item types should have their parent vocabulary as their parent.
ITEM_TYPES_FOR_VOCAB_PARENTS = [
    'units',
    'uri',
]

# Maximum depth of geotile zoom
MAX_GEOTILE_ZOOM = 30
# Minimum allowed geotile zoom
MIN_GEOTILE_ZOOM = 6



class SolrDocumentNS:
    '''
    Defines the Solr Document objects that the crawler will crawl. Solr
    fields are stored in a Solr Document's "fields" property.
    '''

    def __init__(self, uuid, man_obj=None, rep_dict=None):
        '''
        Using our expanded representation dict to make a solr
        document.
        '''
    
        # Are we doing a related document? Related documents are
        # made to add extra metadata to a solr document. Typically
        # documents for "media" and "document" item_types lack much
        # description, so we use related documents from "subjects"
        # item_types that are linked to media and document item_types
        # to add more descriptive information.
        # prefix for related solr_documents
        self.solr_doc_prefix = ''
        # do_related means that we're making solr fields for
        # a related item (a subject linked to a media resource)
        # this makes only some solr fields
        self.do_related = False
        # First get core data structures
        if not man_obj or not rep_dict:
            man_obj, rep_dict = item.make_representation_dict(
                subject_id=uuid,
                for_solr_or_html=True,
            )
            rep_dict = prepare_for_item_dict_solr_and_html_template(
                man_obj, 
                rep_dict
            )

        # Make the assertion objects easy to access
        self.assert_objs = rep_dict.get('for_solr_assert_objs', [])
        self.rel_man_objs = solr_utils.make_dict_of_manifest_objs_from_assertion_objs(
            self.assert_objs
        )

        # Make the rep_dict just keep the counts.
        rep_dict['for_solr_assert_objs'] = len(
            rep_dict.get('for_solr_assert_objs', [])
        )
        self.man_obj = man_obj
        self.rep_dict = rep_dict

        self.geo_specified = False
        self.chrono_specified = False
        # Store values here
        self.fields = {}
        self.fields['text'] = ''  # Start of full-text field
        self.fields['human_remains'] = 0  # Default, item is not about human remains.
        # Default media counts.
        self.fields['image_media_count'] = 0
        self.fields['other_binary_media_count'] = 0
        self.fields['document_count'] = 0
        # The solr field for joins by uuid.
        self.join_solr_field = 'join' +  SOLR_VALUE_DELIM + 'pred_id'



    # -----------------------------------------------------------------
    # NOTE: This section are for utilities used by multiple methods
    # -----------------------------------------------------------------
    def _prefix_solr_field(self, solr_field, act_solr_doc_prefix=None):
        """Makes a solr field, with a prefix if needed"""

        if act_solr_doc_prefix is None and not len(self.solr_doc_prefix):
            return solr_utils.convert_slug_to_solr(solr_field)
        
        if act_solr_doc_prefix is None:
            # The act_solr_prefix is not set, so default to the
            # solr_doc_prefix for this class.
            act_solr_doc_prefix = self.solr_doc_prefix

        act_solr_doc_prefix = solr_utils.convert_slug_to_solr(
            act_solr_doc_prefix
        )
        if not solr_field.startswith(act_solr_doc_prefix):
            solr_field = act_solr_doc_prefix + solr_field
        return solr_utils.convert_slug_to_solr(solr_field)


    def _add_id_field_and_value(
            self,
            solr_id_field,
            solr_field_val,
            act_solr_doc_prefix=None,
        ):
        """Adds values for an id field, and the associated slug
           value for the related _fq field
        """
        if (not isinstance(solr_id_field, str) or
            not isinstance(solr_field_val, str)):
            return None
        
        if not solr_field_val:
            return None
        
        if act_solr_doc_prefix is None:
            # The act_solr_prefix is not set, so default to the
            # solr_doc_prefix for this class.
            act_solr_doc_prefix = self.solr_doc_prefix
        

        # Add the main solr id field if not present,
        # then append the concat_val
        
        # A descriptive field (for props), not a context or
        # a project field. So this can take a solr-doc prefix
        # to indicate it is a related property.
        solr_id_field = self._prefix_solr_field(
            solr_id_field,
            # The act_solr_doc_prefix can override the default for the
            # solr_doc_prefix for the whole document object  
            act_solr_doc_prefix=act_solr_doc_prefix
        )
        
        if solr_id_field not in self.fields:
            # Set up the list of values for this solr field.
            self.fields[solr_id_field] = []

        if solr_field_val in self.fields[solr_id_field]:
            # This value already exists, so skip out.
            return None

        # Only add it if we don't already have it
        self.fields[solr_id_field].append(solr_field_val)
        return True
    

    def _add_joined_subject_uuid(self, item_obj):
        """Adds subject uuids to facilitate joins."""
        if not self.man_obj.item_type in ['media','documents']:
            # This Open Context item type does not record joins.
            return None
        # Make sure the item is a dict.
        item = solr_utils.solr_convert_man_obj_obj_dict(item_obj)
        if item.get('item_type') != 'subjects':
            # Not a subject, no uuid to join.
            return None
        
        if not item.get('uuid'):
            return None
        # We need to facilitate joins to a related
        # Open Context subject item (join by UUID).
        if not JOIN_SOLR in self.fields:
            # We don't have a solr field for joins yet, so
            # make one.
            self.fields[JOIN_SOLR] = []
        # Append to the solr field for joins
        self.fields[JOIN_SOLR].append(item.get('uuid'))


    def _add_solr_fields_for_linked_media_documents(self, item_obj):
        """Adds standard solr fields relating to media and document links."""
        item = solr_utils.solr_convert_man_obj_obj_dict(item_obj)
        if item.get('item_type') == 'media':
            if 'image' in item.get('type', '') or 'image' in item.get('object__item_class__label', ''):
                self.fields['image_media_count'] += 1
            else:
                self.fields['other_binary_media_count'] += 1
        elif item.get('item_type') == 'documents':
            self.fields['document_count'] += 1
        
        # Tuples of (solr_field, media item_obj key)
        media_tups = [
            ('thumbnail_uri', 'oc-gen:thumbnail-uri'),
            ('iiif_json_uri', 'oc-gen:iiif-json-uri'),
        ]
        for solr_field, key_uri in media_tups:
            if self.fields.get(solr_field):
                # We already have one of these.
                continue
            if not item.get(key_uri):
                continue
            self.fields[solr_field] = [item.get(key_uri)]


    def _set_required_solr_fields(self):
        """Sets data for the core solr fields (non-dynamic, required)."""
        self.fields['uuid'] = str(self.man_obj.uuid)
        self.fields['slug_type_uri_label'] = solr_utils.make_solr_entity_str(
            slug=self.man_obj.slug,
            data_type=self.man_obj.data_type,
            uri=self.man_obj.uri,
            label=self.man_obj.label,
        )
        self.fields['project_uuid'] =  str(self.man_obj.project_id)
        if not self.man_obj.published:
            published_datetime = DEFAULT_PUBLISHED_DATETIME
        else:
            published_datetime = self.man_obj.published
        self.fields['published'] = published_datetime.strftime(
            '%Y-%m-%dT%H:%M:%SZ'
        )
        self.fields['updated'] = datetime.datetime.utcnow().strftime(
            '%Y-%m-%dT%H:%M:%SZ'
        )
        # default, can add as image media links discovered
        self.fields['image_media_count'] = 0
        # default, can add as other media links discovered
        self.fields['other_binary_media_count'] = 0
        # default, can add as doc links discovered
        self.fields['document_count'] = 0
        self.fields['sort_score'] = float(
            '0.' + self.man_obj.sort.replace('-', '')
        )
        # default, adds to interest score once other fields determined
        self.fields['interest_score'] = 0
        self.fields['item_type'] = self.man_obj.item_type
        self.fields['item_class'] = self.man_obj.item_class.label


    def _add_labels_titles_to_text_field(self):
        """Adds multiple language labels and titles to add to text field."""
        for label_pred in LABELING_PREDICATE_KEYS:
            label_objs = self.rep_dict.get(label_pred)
            if not label_objs:
                continue
            if isinstance(label_objs, str):
                label_objs = [{'_': label_objs}]
            for label_obj in label_objs:
                for _, text_val in label_obj.items():
                    self.fields['text'] += solr_utils.ensure_text_solr_ok(
                        text_val
                    )
                    self.fields['text'] += ' \n'


    def _set_solr_project_fields(self):
        """
        Creates a hierarchy of projects in the same way as a hierarchy of predicates
        """
        solr_field_name = ROOT_PROJECT_SOLR
        proj_hierarchy = hierarchy.get_project_hierarchy(self.man_obj)
        for proj in proj_hierarchy:
            # Add the project label to all text field.
            self.fields['text'] += ' ' + str(proj.label) + '\n'
            # Compose the solr_value for this item in the context
            # hierarchy.
            act_solr_value = solr_utils.make_obj_or_dict_solr_entity_str(
                obj_or_dict=proj,
                act_solr_doc_prefix='', # No prefixing for projects!
            )
            # The self.ALL_PROJECT_SOLR takes values for
            # each project item in project hierarchy, thereby
            # facilitating queries at all levels of the project
            # hierarchy. Without the self.ALL_PROJECT_SOLR, we would need
            # to know the full hierarchy path of project items in order
            # to query for a given project.
            self._add_id_field_and_value(
                ALL_PROJECT_SOLR,
                act_solr_value,
                act_solr_doc_prefix='', # No prefixing for projects!
            )
            # Now add the current proj. to the solr field for the current
            # level of the project hierarchy.
            self._add_id_field_and_value(
                solr_field_name,
                act_solr_value,
                act_solr_doc_prefix='', # No prefixing for projects!
            )
            # Make the new solr_field_name for the next iteration of the loop.
            solr_field_name = (
                solr_utils.convert_slug_to_solr(proj.slug)
                + SOLR_VALUE_DELIM
                + FIELD_SUFFIX_PROJECT
            )


    def _add_solr_spatial_context(self):
        """Adds spatial context fields to the solr document."""
        context_items = self.rep_dict.get('contexts', [])
        if not context_items:
            # This item has no spatial context.
            return None
        # Iterate through the spatial context items.
        for index, context in enumerate(context_items):
            # Compose the solr_value for this item in the context
            # hierarchy.
            act_solr_value = solr_utils.make_obj_or_dict_solr_entity_str(
                obj_or_dict=context,
                act_solr_doc_prefix='', # No prefixing for projects!
            )
            # The self.ALL_CONTEXT_SOLR takes values for
            # each context item in spatial context hierarchy, thereby
            # facilitating queries at all levels of the context
            # hierarchy. Without the self.ALL_CONTEXT_SOLR, we would need
            # to know the full hierarchy path of parent items in order
            # to query for a given spatial context.
            self._add_id_field_and_value(
                ALL_CONTEXT_SOLR,
                act_solr_value,
                act_solr_doc_prefix='', # No prefixing for projects!
            )
            if index == 0:
                # We are at the top of the spatial hierarchy
                # so the solr context field is self.ROOT_CONTEXT_SOLR.
                solr_context_field = ROOT_CONTEXT_SOLR
            else:
                # We are at sub-levels in the spatial hierarchy
                # so the solr context field comes from the parent item
                # in the spatial context hierarchy
                solr_context_field = (
                    context_items[index - 1].get('slug')
                    + SOLR_VALUE_DELIM 
                    + FIELD_SUFFIX_CONTEXT
                )

            self._add_id_field_and_value(
                solr_context_field,
                act_solr_value,
                act_solr_doc_prefix='', # No prefixing for contexts!
            )


    def _add_solr_spatial_context(self):
        """Adds spatial context fields to the solr document."""
        context_items = self.rep_dict.get('contexts', [])
        if not context_items:
            # This item has no spatial context.
            return None
        # Iterate through the spatial context items.
        for index, context in enumerate(context_items):
            # Compose the solr_value for this item in the context
            # hierarchy.
            act_solr_value = solr_utils.make_obj_or_dict_solr_entity_str(
                obj_or_dict=context,
                act_solr_doc_prefix='', # No prefixing for projects!
            )
            # The self.ALL_CONTEXT_SOLR takes values for
            # each context item in spatial context hierarchy, thereby
            # facilitating queries at all levels of the context
            # hierarchy. Without the self.ALL_CONTEXT_SOLR, we would need
            # to know the full hierarchy path of parent items in order
            # to query for a given spatial context.
            self._add_id_field_and_value(
                ALL_CONTEXT_SOLR,
                act_solr_value,
                act_solr_doc_prefix='', # No prefixing for projects!
            )
            if index == 0:
                # We are at the top of the spatial hierarchy
                # so the solr context field is self.ROOT_CONTEXT_SOLR.
                solr_context_field = ROOT_CONTEXT_SOLR
            else:
                # We are at sub-levels in the spatial hierarchy
                # so the solr context field comes from the parent item
                # in the spatial context hierarchy
                solr_context_field = (
                    context_items[index - 1].get('slug')
                    + SOLR_VALUE_DELIM 
                    + FIELD_SUFFIX_CONTEXT
                )

            self._add_id_field_and_value(
                solr_context_field,
                act_solr_value,
                act_solr_doc_prefix='', # No prefixing for contexts!
            )
    

    def _get_hierarchy_paths_w_alt_labels_by_item_type(self, item_man_obj):
        """Get hierarchy paths list of lists for a manifest object

        :param AllManifest item_man_obj: The item that we want to put
            into a list of hierarchy lists.

        return list of hierarchy lists.
        """
        if item_man_obj.item_type in ITEM_TYPES_FOR_CONCEPT_HIERARCHIES:
            raw_hierarchy_paths = hierarchy.get_concept_hierarchy_paths_containing_item(
                item_man_obj
            )
        elif item_man_obj.item_type in ITEM_TYPES_FOR_VOCAB_PARENTS:
            # NOTE TODO: Do we want to suppport recursive look-ups of
            # contexts here?
            if str(item_man_obj.context.uuid) == configs.OPEN_CONTEXT_PROJ_UUID:
                raw_hierarchy_paths = [[item_man_obj]]
            else:
                raw_hierarchy_paths = [[item_man_obj.context, item_man_obj]]
        else:
            raw_hierarchy_paths = [[item_man_obj]]

        # Now get the alternative labels if they exist. This step also
        # converts manifest objects into solr doc creation friendly
        # dictionary objects.
        hierarchy_paths = []
        for raw_hierarchy_path in raw_hierarchy_paths:
            hierarchy_path = []
            for item_obj in raw_hierarchy_path:
                other_labels = labels.get_other_labels(item_obj)
                item = solr_utils.solr_convert_man_obj_obj_dict(item_obj)
                if other_labels:
                    item['alt_label'] = other_labels[0]
                hierarchy_path.append(item)
            hierarchy_paths.append(hierarchy_path)
        return hierarchy_paths


    def _add_object_value_hierarchies(self, root_solr_field, hierarchy_paths):
        """Adds a hierarchy of predicates to the solr doc."""
        
        # The all_obj_solr_field is defined for the solr field
        # at the root of this hierarchy. It will take values for
        # each item in the object value hierarchy, thereby
        # facilitating queries at all levels of the object value
        # hierarchy. Without the all_obj_solr_field, we would need
        # to know the full hierarchy path of parent items in order
        # to query for a given object value.
        all_obj_solr_field = (
            'obj_all'
            + SOLR_VALUE_DELIM
            + root_solr_field
        )
        all_obj_solr_field = self._prefix_solr_field(
            all_obj_solr_field
        )

        # Now iterate through the list of hierarchy items of
        # object values.
        for hierarchy_items in hierarchy_paths:

            # The act_solr_field starts at the solr field that is
            # for the root of the hierarchy, passed as an argument to
            # this function.
            act_solr_field = self._prefix_solr_field(root_solr_field)

            # Add the root solr field if it does not exist.
            if not self.fields.get(act_solr_field):
                self.fields[act_solr_field] = []

            for index, item_obj in enumerate(hierarchy_items):

                # Make sure the item is a dict.
                item = solr_utils.solr_convert_man_obj_obj_dict(item_obj)

                # Add the label of this item in the hierarchy
                # to the text field. This means key-word searches will
                # be inclusive of all parent items in a hierarchy.
                self.fields['text'] += ' ' + item.get('label', '') + ' '
                # Compose the solr value for the current parent item.
                act_solr_value = solr_utils.make_obj_or_dict_solr_entity_str(
                    obj_or_dict=item,
                    act_solr_doc_prefix=self.solr_doc_prefix,
                )
                
                # Add to the solr document the object value to the
                # solr field for this level of the hierarchy.
                self._add_id_field_and_value(
                    act_solr_field,
                    act_solr_value,
                    act_solr_doc_prefix=self.solr_doc_prefix,
                )
                # Add to the solr document the object value to the
                # all_obj_solr_field , to facilitate queries at ALL
                # levels of the object value hierarchy.
                self._add_id_field_and_value(
                    all_obj_solr_field,
                    act_solr_value,
                    act_solr_doc_prefix=self.solr_doc_prefix,
                )
                # Make the next act_solr_field for the next
                # iteration through the loop.
                act_solr_field = solr_utils.convert_slug_to_solr(
                    item.get('slug')
                    + SOLR_VALUE_DELIM
                    + root_solr_field
                )


    def _add_category_hierarchies(self):
        """Adds category / type data ('item_class' in the manifest table)
        to the solr document.
        """
        if not self.man_obj.item_class:
            # No category, skip the rest.
            return None
        if  str(self.man_obj.item_class.uuid) == configs.DEFAULT_CLASS_UUID:
            # Default class, tedious and not worth indexing.
            return None
        
        raw_hierarchy_paths = self._get_hierarchy_paths_w_alt_labels_by_item_type(
            self.man_obj.item_class
        )
        hierarchy_paths = []
        solr_field_name = None
        for raw_path in raw_hierarchy_paths:
            solr_field_name = None
            hierarchy_path = []
            for item in raw_path:
                if solr_field_name:
                    hierarchy_path.append(item)
                    continue
                if item.get('context_id') != configs.OC_GEN_VOCAB_UUID:
                    continue
                if item.get('uri', '').endswith(self.man_obj.item_type):
                    # we've found the parent 
                    solr_field_name = solr_utils.convert_slug_to_solr(
                        item.get('slug')
                        + SOLR_VALUE_DELIM 
                        + 'pred_id'
                    )
            if not hierarchy_path:
                continue
            hierarchy_paths.append(hierarchy_path)
        
        if not solr_field_name:
            # We could NOT find a solr field name meets our 
            # criteria for making hierarchic solr facets. So
            # skip out.
            return None
        
        # Now do the work of adding the hierarchies in solr
        # facet fields.
        self._add_object_value_hierarchies(
            solr_field_name, 
            hierarchy_paths
        )


    def _add_solr_id_field_values(self, solr_field_name, pred_value_objects):
        """Adds non-literal predicate value objects,
           and their hierarchy parents, to the Solr doc
        """
        for item_obj in pred_value_objects:

            item = solr_utils.solr_convert_man_obj_obj_dict(
                item_obj,
                dict_lookup_prefix='object'
            )

            # Add subject uuid joins, if applicable.
            self._add_joined_subject_uuid(item)
            # Add standard solr fields that summarize linked media,
            # documents.
            self._add_solr_fields_for_linked_media_documents(item)
            # Now add the val_obj item (and parents) to the
            # solr document.

            # Try to look up the item's manifest object.
            item_uuid = item.get('uuid')
            if not item_uuid:
                continue
            # First, check if we already have it from the initial query
            # to the AllAssertions.
            item_man_obj = self.rel_man_objs.get(item_uuid)
            if not item_man_obj:
                # This is less idea, because it means hitting the DB
                item_man_obj = AllManifest.objects.filter(uuid=item_uuid).first()
            if not item_man_obj:
                print(f'NO item_man_obj:  {item_uuid}')
                print(f'NO item_man_obj:  {solr_field_name}: {item}')
                continue

            # Put the item in a list of hierarchy lists (parents may not
            # exist, but the data structure will be consistent)
            hierarchy_paths = self._get_hierarchy_paths_w_alt_labels_by_item_type(
                item_man_obj
            )

            # Now do the work of adding the hierarchies in solr
            # facet fields.
            self._add_object_value_hierarchies(
                solr_field_name, 
                hierarchy_paths
            )
            # A little stying for different value objects in the text field.
            self.fields['text'] += '\n'


    def _add_object_uri(self, val_obj):
        """Adds a linked data URI of an object for indexing

        :param dict val_obj: An assertion value object
        """
        if not val_obj.get('object__item_type') in configs.URI_CONTEXT_PREFIX_ITEM_TYPES:
            return None
        object_uri = val_obj.get('object__uri')
        if not object_uri:
            return None
        if 'object_uri' not in self.fields:
            self.fields['object_uri'] = []
        if object_uri not in self.fields['object_uri']:
            self.fields['object_uri'].append(object_uri)


    def _add_solr_field_values(
            self,
            solr_field_name,
            pred_value_objects
        ):
        """Adds predicate value objects, and their hierarchy parents, to the Solr doc."""
        if not isinstance(pred_value_objects, list):
            return None

        if not self.fields.get(solr_field_name):
            self.fields[solr_field_name] = []

        for val_obj in pred_value_objects:
            solr_data_type = solr_utils.get_solr_data_type_from_data_type(
                val_obj.get('predicate__data_type')
            )
            if solr_data_type == 'string':
                val_str = val_obj.get('obj_string')
                if not val_str:
                    continue
                val_str = solr_utils.ensure_text_solr_ok(val_str)
                self.fields['text'] += str(val_str) + ' \n'
                self.fields[solr_field_name].append(val_str)
            elif solr_data_type== 'bool':
                val = val_obj.get('obj_boolean')
                if val is None:
                    continue
                self.fields[solr_field_name].append(val) 
                self.fields['text'] += str(val) + ' \n'
            elif solr_data_type == 'int':
                val = val_obj.get('obj_integer')
                if val is None:
                    continue
                self.fields[solr_field_name].append(val) 
                self.fields['text'] += str(val) + ' \n'
            elif solr_data_type == 'double':
                val = val_obj.get('obj_double')
                if val is None:
                    continue
                self.fields[solr_field_name].append(val) 
                self.fields['text'] += str(val) + ' \n'
            elif solr_data_type == 'date':
                val = val_obj.get('obj_datetime')
                if val is None:
                    continue
                self.fields['text'] += str(val) + ' \n'
                self.fields[solr_field_name].append((val + 'T00:00:00Z'))
            elif solr_data_type == 'id':
                # This is the most complicated case where the value
                # objects will be non-literals (entities with outside URIs or URI
                # identified Open Context entities). So we need to add them, and
                # any of their hierarchy parents, to the solr document.
                self._add_solr_id_field_values(
                    solr_field_name,
                    [val_obj]
                )
                self._add_object_uri(val_obj)
            else:
                pass

    
    def _get_predicate_solr_field_name_in_hierarchy(
        self, 
        assert_dict, 
        is_default_attrib_group=True
    ):
        """Gets a solr field name for a predicate in an appropriate hierarchy

        :param dict assert_dict: A dictionary representation of an assertion
            where assertion predicate attributes are expressed with 
            "predicate_*" keys. This verbose assertion_dictionary gets
            generated when the item.make_representation_dict has 
            a "for_solr=True" argument.
        :param bool is_default_attrib_group: A boolean. If True, the 
            predicate is in a default attribute group, all alone. If False,
            we treat the attribute group as a hierarchy parent for the
            predicate.
        """
        pred_uuid = assert_dict.get('predicate_id')
        if not pred_uuid:
            return None
        
        if pred_uuid in NO_INDEX_DESCRIPTION_PREDICATE_UUIDS:
            # This is not something we want to index.
            return None

        # First, check if we already have it from the initial query
        # to the AllAssertions.
        pred_man_obj = self.rel_man_objs.get(pred_uuid)
        if not pred_man_obj:
            # This is less idea, because it means hitting the DB
            pred_man_obj = AllManifest.objects.filter(uuid=pred_uuid).first()
        if not pred_man_obj:
            return None

        # Put the item in a list of hierarchy lists (parents may not
        # exist, but the data structure will be consistent)
        hierarchy_paths = self._get_hierarchy_paths_w_alt_labels_by_item_type(
            pred_man_obj
        )

        attribute_group_uuid = None
        attrib_group_man_obj = None
        if not is_default_attrib_group:
            attribute_group_uuid = assert_dict.get('attribute_group_id')
        if attribute_group_uuid:
            attrib_group_man_obj = self.rel_man_objs.get(attribute_group_uuid)
        if attrib_group_man_obj:
            # Add the attribute group to the top of the hierarchy paths for this
            # predicate.
            hierarchy_paths = [([attrib_group_man_obj] + [p]) for p in hierarchy_paths]
        
        # NOTE: Add the predicates, inside their hierarchy, 
        # to the solr document.
        if assert_dict.get('predicate__item_type') == 'predicates':
            # This is a project specific predicate.
            root_solr_field = ROOT_PREDICATE_SOLR
        else:
            # This is a linked data predicate.
            root_solr_field = ROOT_LINK_DATA_SOLR
        
        # Add the solr field if it doesn't exist.
        if not self.fields.get(root_solr_field):
            self.fields[root_solr_field] = []
        
        # The default solr_field_name.
        solr_field_name = None

        for hierarchy_items in hierarchy_paths:

            act_solr_field = self._prefix_solr_field(root_solr_field)
            # Add the root solr field if it does not exist.
            last_item_index = len(hierarchy_items) - 1
            attribute_field_part = ''
            pred_obj_all_field = None

            for index, item_obj in enumerate(hierarchy_items):
                # Add the solr field if it does not exist.
                if not self.fields.get(act_solr_field):
                    self.fields[act_solr_field] = []
                if index < last_item_index:
                    # Force parents to be of an id data type.
                    item_obj.data_type = 'id'
                    self.fields['text'] += ' ' + item.label + ' '
                # Make a dictionary version of this item.
                item = solr_utils.solr_convert_man_obj_obj_dict(item_obj)

                # Compose the solr value for the current parent item.
                act_solr_value = solr_utils.make_obj_or_dict_solr_entity_str(
                    item,
                    dict_lookup_prefix='predicate',
                    act_solr_doc_prefix=self.solr_doc_prefix,
                )

                # Treat the first parent in a special way
                if index == 0:
                    # We're at the highest level of the hierarchy,
                    # so solr field name is the root solr field name.
                    solr_field_name = root_solr_field
                else:
                    # We're at a higher level of the hierarchy, so the
                    # solr field name comes from the previous (parent)
                    # item in the hierarchy.
                    solr_field_name = solr_utils.convert_slug_to_solr(
                        hierarchy_items[index - 1].get('slug')
                        + attribute_field_part
                        + SOLR_VALUE_DELIM 
                        + FIELD_SUFFIX_PREDICATE
                    )

                # Add to the solr document the object value to the
                # all_obj_solr_field , to facilitate queries at ALL
                # levels of the object value hierarchy.
                self._add_id_field_and_value(
                    solr_field_name,
                    act_solr_value,
                    act_solr_doc_prefix=self.solr_doc_prefix,
                )

                if attribute_field_part == '' and index > 0:
                    # The attribute field part will be made from the slug
                    # at the top of the hierarchy_items of predicates. 
                    # This makes querying logic easier and more consistent.
                    attribute_field_part = solr_utils.convert_slug_to_solr(
                        SOLR_VALUE_DELIM
                        + hierarchy_items[0].get('slug')
                    )
                
                if not pred_obj_all_field and index > 0:
                    # The obj_all field will be made from the slug at the
                    # top of hierarchy_items of predicates. This makes
                    # querying logic easier and more consistent with
                    # properties and type hierarchies.
                    pred_obj_all_field = self._prefix_solr_field(
                        solr_utils.convert_slug_to_solr(
                            (
                                'obj_all'
                                + SOLR_VALUE_DELIM
                                + hierarchy_items[0].get('slug')
                                + SOLR_VALUE_DELIM
                                + FIELD_SUFFIX_PREDICATE
                            )
                        )
                    )
                    if not pred_obj_all_field in self.fields:
                        self.fields[pred_obj_all_field] = []
                
                if pred_obj_all_field:
                    # Add the act_solr value to the all obj field.
                    self._add_id_field_and_value(
                        pred_obj_all_field,
                        act_solr_value,
                        act_solr_doc_prefix=self.solr_doc_prefix,
                    )
                
                if index != last_item_index:
                    continue

                # The last solr field name is the last item
                # in the hierarchy.
                solr_field_name = solr_utils.convert_slug_to_solr(
                    hierarchy_items[-1].get('slug')
                    + attribute_field_part
                    + SOLR_VALUE_DELIM 
                    + solr_utils.get_solr_data_type_from_data_type(
                        hierarchy_items[-1].get('data_type'), 
                        prefix='pred_'
                    )
                )
    
        return solr_field_name


    def _add_observations_descriptions(self):
        """Adds descriptions from item observations to the Solr doc."""
        if not self.rep_dict.get('oc-gen:has-obs'):
            return None
        # Get the list of all the observations made on this item.
        # Each observation is a dictionary with descriptive assertions
        # keyed by a predicate.
        for obs in self.rep_dict.get('oc-gen:has-obs'):
             # Get the status of the observation, defaulting to 'active'.
             # We are OK to index observation assertions if the observation is
             # active, otherwise we should skip it to so that the inactive
             # observations do not get indexed.
            obs_status = obs.get('oc-gen:obsStatus', 'active')
            if obs_status != 'active':
                # Skip this observation. It's there but has a deprecated
                # status.
                continue
            # Descriptive predicates are down in the events.
            for event_node in obs.get('oc-gen:has-events', []):
                for attrib_group in event_node.get('oc-gen:has-attribute-groups', []):
                    for _, pred_value_objects in attrib_group.get('descriptions', {}).items():
                        # TODO handle predicates, their hierarchy, and add
                        # non-default attribute groups to the top of the predicates
                        # hierarchy.
                        solr_field_name = self._get_predicate_solr_field_name_in_hierarchy(
                            assert_dict=pred_value_objects[0], 
                            is_default_attrib_group=attrib_group.get('default', True),
                        )
                        if not solr_field_name:
                            # We don't have a solr field name, so skip.
                            continue
                        self._add_solr_field_values(
                            solr_field_name,
                            pred_value_objects
                        )


    def make_solr_doc(self):
        """Make a solr document """
        if not self.man_obj or not self.rep_dict:
            return None
        # Set the required, universal fields for Solr
        self._set_required_solr_fields()
        # Add labeling text to the general text field
        self._add_labels_titles_to_text_field()
        # Add the project hierarchy
        self._set_solr_project_fields()
        # Add the item spatial context hierarchy
        self._add_solr_spatial_context()
        # Add the item_class hierarchies
        self._add_category_hierarchies()
        # Add descriptions from observations()
        self._add_observations_descriptions()

    def make_related_solr_doc(self):
        """Make a related solr document """
        self.do_related = True
