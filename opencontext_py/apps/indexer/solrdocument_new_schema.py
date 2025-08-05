import copy
import datetime
from django.core.cache import caches

from django.db.models import Q
from django.db.models.functions import Length

from opencontext_py.libs.utilities import chronotiles
from opencontext_py.libs.globalmaptiles import GlobalMercator

from opencontext_py.apps.all_items.models import (
    AllManifest,
)
from opencontext_py.apps.all_items import configs
from opencontext_py.apps.all_items import hierarchy
from opencontext_py.apps.all_items import sensitive_content
from opencontext_py.apps.all_items.representations import item
from opencontext_py.apps.all_items.representations.template_prep import (
    TEXT_CONTENT_KEYS,
    NO_NODE_KEYS,
    prepare_for_item_dict_solr_and_html_template
)

from opencontext_py.apps.indexer import solr_utils


# A dict for the category, property associated with an Open Context
# category
OC_CATEGORY_PROP_DICT = {
    'uuid': configs.PREDICATE_OC_CATEGORY,
    'project_id': configs.OPEN_CONTEXT_PROJ_UUID,
    'item_class_id': configs.DEFAULT_CLASS_UUID,
    'item_type': 'property',
    'data_type': 'id',
    'slug': 'oc-gen-category',
    'label': 'Category',
    'item_key': 'oc-gen:category',
    'uri': 'opencontext.org/vocabularies/oc-general/category',
    'context_id': configs.OC_GEN_VOCAB_UUID,
}


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
    'dc-terms:identifier',
    'owl:sameAs',
    'foaf:isPrimaryTopicOf'
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
    configs.CSVW_COLUMNS_UUID,
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
ROOT_OC_CATEGORY_SOLR = 'oc_gen_category' + SOLR_VALUE_DELIM + FIELD_SUFFIX_PREDICATE
ROOT_LINK_DATA_SOLR = 'ld' + SOLR_VALUE_DELIM + FIELD_SUFFIX_PREDICATE
ROOT_PROJECT_SOLR = 'root' + SOLR_VALUE_DELIM + FIELD_SUFFIX_PROJECT
ALL_PROJECT_SOLR = 'obj_all' + SOLR_VALUE_DELIM + FIELD_SUFFIX_PROJECT

# General (any event type) space and time solr prefix.
ALL_EVENTS_SOLR = 'all_events'

EQUIV_LD_SOLR = 'skos_closematch' + SOLR_VALUE_DELIM + FIELD_SUFFIX_PREDICATE
JOIN_SOLR = 'join_uuids'
JOIN_PERSON_ORG_SOLR = 'join_person_orgs' + SOLR_VALUE_DELIM + FIELD_SUFFIX_PREDICATE
FILE_SIZE_SOLR = 'filesize'
FILE_MIMETYPE_SOLR = 'mimetype' + SOLR_VALUE_DELIM + FIELD_SUFFIX_PREDICATE

# Configs for related (subjects items) solr fields
RELATED_SOLR_DOC_PREFIX = 'REL_'
ADD_RELATED_LITERAL_FIELDS = False


# Minimum allowed geotile zoom
MIN_GEOTILE_ZOOM = 6
# Maximum depth of geotile zoom
MAX_GEOTILE_ZOOM = 30
# Low resolution geotile string length
LOW_RESOLUTION_GEOTILE_LENGTH = 9
# Drop last chrono-tile characters
LOW_RESOLUTION_CHRONOTILE_DROP_LAST = 10


# Mappings for solr fields and file uris.
FILE_TYPE_SOLR_FIELD_DICT = {
    'oc-gen:thumbnail': 'thumbnail_uri',
    'oc-gen:thumbnail-uri': 'thumbnail_uri',
    'oc-gen:preview': 'preview_uri',
    'oc-gen:preview-uri': 'preview_uri',
    'oc-gen:fullfile': 'full_uri',
    'oc-gen:fullfile-uri': 'full_uri',
    'oc-gen:iiif': 'iiif_json_uri',
    'oc-gen:iiif-uri': 'iiif_json_uri',
}


# The solr document creation calculates an "interest score"
# used to help sort records based on their "interestingness". This is
# calculated as a function of item_type and richness or documentation
# and description. More richly described items will be considered
# more interesting.
DEFAULT_BASE_INTEREST_SCORE = 1
ITEM_TYPE_INTEREST_SCORES = {
    'projects': 500,
    'tables': 250,
    'vocabularies': 100,
    'media': 10,
    'documents': 10,
    'predicates': 3,
    'types': 3,
    'subjects': 2,
    'persons': 1,
}


ALL_ATTRIBUTE_GROUPS_SLUG = 'oc-gen-attribute-groups'

# Projects with more records and more variety of records
# should have a greater information content. For every 500
# records, they should get an extra interest score point.
# This gets
PROJ_ITEM_COUNT_FACTOR = 0.00125
# Projects with more variety will get an extra bonus to the
# raw counts of their items.
PROJ_ITEM_TYPE_ITEM_CLASS_COUNT_VARIETY_BONUS = 0.005

# List of item_class slugs that are OK for project root items
PROJECT_ROOT_SUBJECT_OK_ITEM_CLASS_SLUGS = [
    'oc-gen-cat-region',
    'oc-gen-cat-site',
    'oc-gen-cat-survey-unit',
]


def clear_caches():
    """Clears caches in case we're making DB updates on
       manifest objects used as predicates.
    """
    cache = caches['redis']
    cache.clear()
    cache = caches['default']
    cache.clear()
    cache = caches['memory']
    cache.clear()


class SolrDocumentNS:
    '''
    Defines the Solr Document objects that the crawler will crawl. Solr
    fields are stored in a Solr Document's "fields" property.
    '''

    def __init__(self, uuid, man_obj=None, rep_dict=None, do_related=False):
        '''
        Using our expanded representation dict to make a solr
        document.
        '''

        # do_related means that we're making solr fields for
        # a related item (a subject linked to a media resource)
        # this makes only some solr fields
        self.do_related = do_related

        # Are we doing a related document? Related documents are
        # made to add extra metadata to a solr document. Typically
        # documents for "media" and "document" item_types lack much
        # description, so we use related documents from "subjects"
        # item_types that are linked to media and document item_types
        # to add more descriptive information.
        # prefix for related solr_documents
        if self.do_related:
            self.solr_doc_prefix = RELATED_SOLR_DOC_PREFIX
        else:
            self.solr_doc_prefix = ''

        # First get core data structures
        if not man_obj or not rep_dict:
            man_obj, rep_dict = item.make_representation_dict(
                subject_id=uuid,
                for_solr=True,
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

        self.flag_do_not_index = None
        if man_obj:
            # Check to see if the item or its project are flagged for not indexing
            self.flag_do_not_index = man_obj.meta_json.get(
                'flag_do_not_index',
                man_obj.project.meta_json.get('flag_do_not_index')
            )

        self.man_obj = man_obj
        self.rep_dict = rep_dict

        self.geo_specified = False
        self.chrono_specified = False
        # Store values here
        self.fields = {}
        self.fields['text'] = ''  # Start of full-text field
        self.fields['keywords'] = []  # Start of keywords field
        self.fields['human_remains'] = False  # Default, item is not about human remains.
        # Default media counts.
        self.fields['image_media_count'] = 0
        self.fields['three_d_media_count'] = 0
        self.fields['gis_media_count'] = 0
        self.fields['other_binary_media_count'] = 0
        self.fields['documents_count'] = 0
        self.fields['subjects_children_count'] = 0
        self.fields['subjects_count'] = 0
        self.fields['persons_count'] = 0
        self.fields['tables_count'] = 0
        # The solr field for joins by uuid.
        self.join_solr_field = 'join' +  SOLR_VALUE_DELIM + 'pred_id'


    # -----------------------------------------------------------------
    # NOTE: This section are for utilities used by multiple methods
    # -----------------------------------------------------------------
    def _add_unique_keyword(self, keyword):
        if not isinstance(keyword, str):
            return None
        if keyword in self.fields['keywords']:
            return None
        self.fields['keywords'].append(keyword)


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


    def _add_solr_fields_for_linked_media_documents(self, item_obj):
        """Adds standard solr fields relating to media and document links."""
        item = solr_utils.solr_convert_man_obj_obj_dict(item_obj)
        if item.get('item_type') == 'media':
            if 'image' in item.get('type', '') or 'image' in item.get('object__item_class__label', ''):
                self.fields['image_media_count'] += 1
            else:
                self.fields['other_binary_media_count'] += 1
        elif item.get('item_type') == 'documents':
            self.fields['documents_count'] += 1
        for key_uri, solr_field in FILE_TYPE_SOLR_FIELD_DICT.items():
            if self.fields.get(solr_field):
                # We already have one of these.
                continue
            if not item.get(key_uri):
                continue
            # This is NOT a multi-valued field
            self.fields[solr_field] = AllManifest().clean_uri(item.get(key_uri))


    def _set_required_solr_fields(self):
        """Sets data for the core solr fields (non-dynamic, required)."""
        self.fields['uuid'] = str(self.man_obj.uuid)
        self.fields['slug_type_uri_label'] = solr_utils.make_solr_entity_str(
            slug=self.man_obj.slug,
            data_type=self.man_obj.data_type,
            uri=self.man_obj.uri,
            label=self.man_obj.label,
        )
        self._add_unique_keyword(self.man_obj.label)
        self.fields['project_uuid'] =  str(self.man_obj.project_id)
        self.fields['project_label'] =  str(self.man_obj.project.label)
        published_datetime = self.man_obj.published
        if not published_datetime:
            published_datetime = self.man_obj.project.published
        if not published_datetime:
            published_datetime = DEFAULT_PUBLISHED_DATETIME
        self.fields['published'] = published_datetime.strftime(
            '%Y-%m-%dT%H:%M:%SZ'
        )
        self.fields['updated'] = datetime.datetime.utcnow().strftime(
            '%Y-%m-%dT%H:%M:%SZ'
        )
        # default, can add as image media links discovered
        self.fields['image_media_count'] = 0
        self.fields['three_d_media_count'] = 0
        self.fields['gis_media_count'] = 0
        # default, can add as other media links discovered
        self.fields['other_binary_media_count'] = 0
        # default, can add as doc links discovered
        self.fields['documents_count'] = 0
        self.fields['subjects_children_count'] = 0
        self.fields['subjects_count'] = 0
        self.fields['persons_count'] = 0
        self.fields['tables_count'] = 0


        self.fields['sort_score'] = float(
            '0.' + self.man_obj.sort.replace('-', '')
        )
        # default, adds to interest score once other fields determined
        self.fields['interest_score'] = 0
        self.fields['item_type'] = self.man_obj.item_type
        self.fields['item_class'] = self.man_obj.item_class.label
        if self.man_obj.meta_json.get('flag_human_remains'):
            # Sensitive data needing to be flagged.
            self.fields['human_remains'] = True


    def _add_string_content_to_text_field(self, text_content_pred_key):
        """Adds multiple language labels and titles to add to text field."""
        text_val_objs = self.rep_dict.get(text_content_pred_key)
        if not text_val_objs:
            return None
        if isinstance(text_val_objs, str):
            text_val_objs = [{'_': text_val_objs}]
        for text_val_obj in text_val_objs:
            for _, text_val in text_val_obj.items():
                text_val = solr_utils.ensure_text_solr_ok(
                    text_val
                )
                if text_val in self.fields['text']:
                    # Don't bloat the index with duplicate text.
                    continue
                self.fields['text'] += text_val +  ' \n'


    def _add_labels_titles_to_text_field(self):
        """Adds multiple language labels and titles to add to text field."""
        for label_pred in LABELING_PREDICATE_KEYS:
            self._add_string_content_to_text_field(label_pred)


    def _add_text_contents(self):
        """Adds multiple language text content to add to text field."""
        for text_pred in TEXT_CONTENT_KEYS:
            self._add_string_content_to_text_field(text_pred)


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


    def _get_parent_and_sibling_projects(self):
        """Gets a project's parent and sibling projects"""
        if self.man_obj.item_type != 'projects':
            return None
        projects = [self.man_obj]
        parent_projects = hierarchy.get_project_hierarchy(self.man_obj)
        for proj_obj in parent_projects:
            if proj_obj not in projects:
                projects.append(proj_obj)
            sub_projects_qs = AllManifest.objects.filter(
                project=proj_obj,
                item_type='projects'
            )
            for sub_proj in sub_projects_qs:
                if sub_proj not in projects:
                    projects.append(sub_proj)
        return projects


    def _get_spatial_context_items_for_collections(self):
        """Gets the spatial context items list for a collection item"""
        if self.man_obj.item_type != 'projects':
            return None
        if self.man_obj.item_class.slug != 'oc-gen-cat-collection':
            return None
        proj_root_man_obj = None
        proj_hierarchy = hierarchy.get_project_hierarchy(self.man_obj)
        all_projs = [self.man_obj, self.man_obj.project] + proj_hierarchy
        for proj in all_projs:
            if not proj.meta_json.get('query_context_path'):
                continue
            proj_root_man_obj = AllManifest.objects.filter(
                item_type='subjects',
                path=proj.meta_json.get('query_context_path')
            ).first()
            if proj_root_man_obj:
                break
        if not proj_root_man_obj:
            return None
        # Sometimes the proj_root_man_obj will be overly specific. The check below will make sure
        # we have a proj_root_man_obj that has an item_class that makes sense to use as a root item.
        check_count = 0
        while (
            check_count < 10
            and not proj_root_man_obj.item_class.slug in PROJECT_ROOT_SUBJECT_OK_ITEM_CLASS_SLUGS):
            # Go up a level until we find an OK item class to use as a root item
            # for the project
            proj_root_man_obj = proj_root_man_obj.context
            check_count += 1
        if check_count > 8:
            return None

        # Add the context to the full text search field. This will make the spatial context
        # searchable with fulltext search
        self.fields['text'] += proj_root_man_obj.path.replace('/', ' ')

        # Get the current root item and all of its parents.
        context_items = item.add_to_parent_context_list(
            manifest_obj=proj_root_man_obj,
            for_solr_or_html=True,
        )
        # the most general (root) items go first.
        context_items.reverse()
        return context_items


    def _get_spatial_context_items_for_project(self):
        """Gets spatial context items list for projects items"""
        if self.man_obj.item_type != 'projects':
            return None
        
        if self.man_obj.item_class.slug == 'oc-gen-cat-collection':
            return self._get_spatial_context_items_for_collections()
        
        sub_projects_qs = AllManifest.objects.filter(
            project=self.man_obj,
            item_type='projects'
        )
        projects = [self.man_obj]
        for proj_obj in sub_projects_qs:
            if proj_obj in projects:
                continue
            projects.append(proj_obj)
        # Now get the root subjects items. These are items
        # in the project (and sub projects) that have contexts in the Open
        # Context project
        root_qs = AllManifest.objects.filter(
            item_type='subjects',
            project__in=projects,
            context__project_id=configs.OPEN_CONTEXT_PROJ_UUID
        )[:500]
        if len(root_qs) < 1:
            # look for root_qs items among items that belong to parents or sibling
            # projects.
            sib_projects = self._get_parent_and_sibling_projects()
            projects += [proj for proj in sib_projects if proj not in projects]

        root_qs = AllManifest.objects.filter(
            item_type='subjects',
            project__in=projects,
            context__project_id=configs.OPEN_CONTEXT_PROJ_UUID
        )[:500]
        if len(root_qs) < 1:
            root_qs = AllManifest.objects.filter(
                item_type='subjects',
                project__in=projects,
            ).order_by(Length('path').asc())[:10]

        if len(root_qs) < 1:
            # We really can't find anything that seems to be a root for this project.
            return None
        # Does this project span multiple world regions? Check
        # the top level paths to see.
        root_paths = {}
        for act_man_obj in root_qs:
            path_ex = act_man_obj.path.split('/')
            for level in range(1, 5):
                act_path = '/'.join(path_ex[0:level])
                if not level in root_paths:
                    root_paths[level] = []
                if act_path in root_paths[level]:
                    continue
                root_paths[level].append(act_path)

        top_paths = None
        if len(root_paths[1]) > 1:
            # we have a project spanning multiple world regions. There's no need to check for a
            # unique context path that goes deeper.
            top_paths = root_paths[1]
        else:
            # check for unique context paths for deeper levels of the
            # spatial hierarchy.
            top_paths = root_paths[1]
            for level in range(1, 5):
                if len(root_paths[level]) > 1:
                    break
                top_paths = root_paths[level]
        # Now finally, determine which manifest "subjects" item is the best one to use
        # as the project root.
        proj_uuids_with_oc = [p.uuid for p in projects] + [configs.OPEN_CONTEXT_PROJ_UUID]
        proj_root_man_obj = None
        root_max_count = 0
        if top_paths:
            # This project spans multiple world regions.
            for top_path in top_paths:
                act_count = AllManifest.objects.filter(
                    item_type='subjects',
                    project__in=projects,
                    path__startswith=top_path
                ).count()
                print(f'Project world region {top_path} is parent of {act_count} items')
                if act_count < root_max_count:
                    continue
                root_max_count = act_count
                proj_root_man_obj = AllManifest.objects.filter(
                    item_type='subjects',
                    path=top_path,
                ).first()
        else:
            for act_man_obj in root_qs:
                act_count = AllManifest.objects.filter(
                    item_type='subjects',
                    project__in=projects,
                    path__startswith=act_man_obj.path
                ).count()
                print(f'Project root {act_man_obj.path} [{act_man_obj.uuid}] is parent of {act_count} items')
                if act_count < root_max_count:
                    continue
                root_max_count = act_count
                proj_root_man_obj = act_man_obj
        if not proj_root_man_obj:
            return None
        # Sometimes the proj_root_man_obj will be overly specific. The check below will make sure
        # we have a proj_root_man_obj that has an item_class that makes sense to use as a root item.
        check_count = 0
        while (
            check_count < 10
            and not proj_root_man_obj.item_class.slug in PROJECT_ROOT_SUBJECT_OK_ITEM_CLASS_SLUGS):
            # Go up a level until we find an OK item class to use as a root item
            # for the project
            proj_root_man_obj = proj_root_man_obj.context
            check_count += 1
        if check_count > 8:
            return None

        # Add the context to the full text search field. This will make the spatial context
        # searchable with fulltext search
        self.fields['text'] += proj_root_man_obj.path.replace('/', ' ')

        # Get the current root item and all of its parents.
        context_items = item.add_to_parent_context_list(
            manifest_obj=proj_root_man_obj,
            for_solr_or_html=True,
        )
        # the most general (root) items go first.
        context_items.reverse()
        return context_items


    def _add_solr_spatial_context(self):
        """Adds spatial context fields to the solr document."""
        context_items = self.rep_dict.get('contexts', [])
        if not context_items and self.man_obj.item_type == 'projects':
            # We have a project item, so do some additional queries to get
            # context items.
            context_items = self._get_spatial_context_items_for_project()
        if not context_items:
            # This item has no spatial context.
            return None
        # Iterate through the spatial context items.
        context_path_labels = []
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
            if not context.get('label'):
                continue
            context_path_labels.append(context.get('label'))
        if len(context_path_labels) < 1:
            return None
        self.fields['context_path'] = '/'.join(context_path_labels)


    def _get_hierarchy_paths_w_alt_labels_by_item_type(self, item_man_obj):
        """Get hierarchy paths list of lists for a manifest object

        :param AllManifest item_man_obj: The item that we want to put
            into a list of hierarchy lists.

        return list of hierarchy lists.
        """
        raw_hierarchy_paths = hierarchy.get_hierarchy_paths_w_alt_labels_by_item_type(item_man_obj)
        # Now get the alternative labels if they exist. This step also
        # converts manifest objects into solr doc creation friendly
        # dictionary objects.
        hierarchy_paths = []
        for raw_hierarchy_path in raw_hierarchy_paths:
            hierarchy_path = []
            for item_obj in raw_hierarchy_path:
                item = solr_utils.solr_convert_man_obj_obj_dict(item_obj)
                self._add_unique_keyword(item_obj.label)
                if getattr(item_obj, 'alt_label', None):
                    item['alt_label'] = item_obj.alt_label
                    self._add_unique_keyword(item_obj.alt_label)
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

                if self._check_meta_json_to_skip_index(item):
                    # item meta_json says don't index this.
                    if False:
                        print(f"No solr indexing of item { item.get('label') } (uuid: {item.get('uuid')}) ")
                    # Index the object URI and label for full text. That's it.
                    self._add_object_uri(item)
                    continue


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
        if str(self.man_obj.item_class.uuid) == configs.DEFAULT_CLASS_UUID:
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
                    solr_field_name = ROOT_OC_CATEGORY_SOLR
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


    def _check_meta_json_to_skip_index(self, item):
        """Checks an item's meta_json (and context meta_json) if item should be skipped

        :param dict item: An item dictionary object with, expected to have
            meta_json and context__meta_json
        """
        keys = [
            'meta_json',
            'context__meta_json',
            'object__meta_json',
            'object__context__meta_json'
        ]
        for key in keys:
            act_meta_json = item.get(key, {})
            if not act_meta_json:
                continue
            if act_meta_json.get('skip_solr_index', False):
                return True
        return False


    def _add_solr_id_field_values(self, solr_field_name, pred_value_objects):
        """Adds non-literal predicate value objects,
           and their hierarchy parents, to the Solr doc
        """
        for item_obj in pred_value_objects:

            item = solr_utils.solr_convert_man_obj_obj_dict(
                item_obj,
                dict_lookup_prefix='object'
            )

            if self._check_meta_json_to_skip_index(item):
                # item meta_json says don't index this.
                if False:
                    print(f"No solr indexing of item { item.get('label') } (uuid: {item.get('uuid')}) ")
                # Index the object URI, that' it.
                self._add_object_uri(item)
                continue

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
            item_man_obj = solr_utils.get_manifest_obj_from_man_obj_dict(
                item_uuid,
                self.rel_man_objs
            )
            if not item_man_obj:
                # This is less idea, because it means hitting the DB
                item_man_obj = AllManifest.objects.filter(uuid=item_uuid).first()
            if not item_man_obj:
                print(f'NO item_man_obj:  {item_uuid}')
                print(f'Problem with:  {solr_field_name}: {item}')
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


    def _clean_add_uri_to_solr_object_uri_field(self, object_uri, clean_first=True):
        """Cleans and adds a uri to the solr object_uri field"""
        if clean_first:
            object_uri = AllManifest().clean_uri(object_uri)
        if 'object_uri' not in self.fields:
            self.fields['object_uri'] = []
        if object_uri not in self.fields['object_uri']:
            self.fields['object_uri'].append(object_uri)


    def _add_object_uri(self, val_obj):
        """Adds a linked data URI of an object for indexing

        :param dict val_obj: An assertion value object
        """
        if not val_obj.get('object__item_type') in configs.URI_CONTEXT_PREFIX_ITEM_TYPES:
            return None
        object_uri = val_obj.get('object__uri')
        if not object_uri:
            return None
        self._clean_add_uri_to_solr_object_uri_field(object_uri)


    def _add_solr_field_values(
            self,
            solr_field_name,
            pred_value_objects,
            enforce_ld_outside_objects=False
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
            if solr_data_type == 'id':
                if (
                    enforce_ld_outside_objects
                    and val_obj.get('predicate__item_type') == 'property'
                    and val_obj.get('object__item_type') == 'types'
                ):
                    # This is a case of a linked data where the object is not
                    # referencig a specific vocabulary, so we should skip it.
                    continue
                # This is the most complicated case where the value
                # objects will be non-literals (entities with outside URIs or URI
                # identified Open Context entities). So we need to add them, and
                # any of their hierarchy parents, to the solr document.
                self._add_solr_id_field_values(
                    solr_field_name,
                    [val_obj]
                )
                self._add_object_uri(val_obj)

            if self.do_related and not ADD_RELATED_LITERAL_FIELDS:
                # This is a related solr doc, and we don't want
                # to add literal fields.
                continue

            if solr_data_type == 'string':
                val_str = val_obj.get('obj_string')
                if not val_str:
                    continue
                val_str = str(solr_utils.ensure_text_solr_ok(val_str))
                self.fields['text'] += val_str + ' \n'
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
            else:
                pass


    def _is_same_actual_versus_expected_meta_json(
        self,
        actual_meta_json,
        expected_meta_json,
        expect_key_only_check=True,
    ):
        """Checks if the actual meta_json object is the same as the expected.

        :param dict actual_meta_json: An items actual meta_json dict.
        :param dict expected_meta_json: Meta_json keys and values expected
            to be present in the predicate item's AllManitest instance.
        :param bool expect_key_only_check: Only check that the expected key
            exists, don't update key values if it does.
        """
        for expected_key, expected_str in expected_meta_json.items():
            if not isinstance(expected_str, str):
                continue
            if expect_key_only_check:
                if not actual_meta_json.get(expected_key):
                    return False
                else:
                    continue
            if expected_str.startswith(RELATED_SOLR_DOC_PREFIX):
                # Strip away any 'REL' prefix, to keep things consistent.
                expected_str = expected_str[len(RELATED_SOLR_DOC_PREFIX):]
            if actual_meta_json.get(expected_key) != expected_str:
                return False
        return True


    def _update_pred_obj_meta_json(
        self,
        expected_meta_json,
        item_obj,
        expect_key_only_check=True,
        clear_caches_on_update=True,
        attrib_group_man_obj=None
    ):
        """Updates a Manifest object meta_json with a solr_field_name if
        it does not already exist.

        :param dict expected_meta_json: Meta_json keys and values expected
            to be present in the predicate item's AllManifest instance.
        :param (dict or AllManifest) item_obj: The AllManifest instance or
            a dict of an AllManifest instance that's used as a predicate.
        :param bool expect_key_only_check: Only check that the expected key
            exists, don't update key values if it does.
        :param bool clear_caches_on_update: Clear the caches on update.
        :param (dict or AllManifest) attrib_group_man_obj: The AllManifest instance or
            a dict of an AllManifest instance that's used as the root attribute group
            object.
        """
        # Make sure we save the solr_field_name in the Manifest meta_json
        # if this doesn't yet exist.
        if not expected_meta_json:
            return None
        is_ok = None
        item_man_obj_to_update = None
        if isinstance(item_obj, dict):
            is_ok = self._is_same_actual_versus_expected_meta_json(
                actual_meta_json=item_obj.get('meta_json', {}),
                expected_meta_json=expected_meta_json,
                expect_key_only_check=expect_key_only_check,
            )
            if not is_ok:
                item_man_obj_to_update = solr_utils.get_manifest_obj_from_man_obj_dict(
                    uuid=item_obj.get('uuid'),
                    man_obj_dict={}
                )

        elif isinstance(item_obj, AllManifest):
            is_ok = self._is_same_actual_versus_expected_meta_json(
                actual_meta_json=item_obj.meta_json,
                expected_meta_json=expected_meta_json,
                expect_key_only_check=expect_key_only_check,
            )
            # Make sure copy the object otherwise we'll run into weird
            # mutation issues.
            if not is_ok:
                item_man_obj_to_update = copy.deepcopy(item_obj)

        if is_ok or not item_man_obj_to_update:
            # We don't need ot update the meta-json
            return None

        update_str = ''
        for expected_key, expected_str in expected_meta_json.items():
            if expected_str.startswith(RELATED_SOLR_DOC_PREFIX):
                # Strip away any 'REL' prefix, to keep things consistent.
                expected_str = expected_str[len(RELATED_SOLR_DOC_PREFIX):]
            if attrib_group_man_obj:
                # Convert the slug for a specific attribute group into the general
                # attribute slug.
                expected_str = solr_utils.replace_slug_in_solr_field(
                    solr_field = expected_str,
                    old_slug=attrib_group_man_obj.slug,
                    new_slug=ALL_ATTRIBUTE_GROUPS_SLUG,
                )
                slugs_key = AllManifest.META_JSON_KEY_ATTRIBUTE_GROUP_SLUGS
                if not item_man_obj_to_update.meta_json.get(slugs_key):
                    item_man_obj_to_update.meta_json[slugs_key] = []
                if not attrib_group_man_obj.slug in item_man_obj_to_update.meta_json[slugs_key]:
                    item_man_obj_to_update.meta_json[slugs_key].append(attrib_group_man_obj.slug)
            update_str += f'{expected_key}:{expected_str}, '
            item_man_obj_to_update.meta_json[expected_key] = expected_str

        print(f'Save {update_str} for {item_man_obj_to_update.label}')

        item_man_obj_to_update.save()
        if clear_caches_on_update:
            solr_utils.clear_man_obj_from_cache(item_man_obj_to_update.uuid)


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

        pred_meta_json = assert_dict.get(
            'predicate__meta_json',
            assert_dict.get('predicate__context__meta_json', {})
        )
        if pred_meta_json.get('skip_solr_index', False):
            if False:
                print(
                    f"No solr indexing of predicate { assert_dict.get('predicate__label') }"
                )
            return None

        # First, check if we already have it from the initial query
        # to the AllAssertions.
        pred_man_obj = solr_utils.get_manifest_obj_from_man_obj_dict(
            pred_uuid,
            self.rel_man_objs
        )
        if not pred_man_obj:
            return None

        if (self.do_related
            and not ADD_RELATED_LITERAL_FIELDS
            and pred_man_obj.data_type != 'id'):
            # We're doing a related solr doc, and this is predicate
            # is for a literal, and we're configured not to add
            # literals to the related fields. So skip out.
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
            attrib_group_man_obj = solr_utils.get_manifest_obj_from_man_obj_dict(
                attribute_group_uuid,
                self.rel_man_objs
            )
        if attrib_group_man_obj:
            # Add the attribute group to the top of the hierarchy paths for this
            # predicate.
            attrib_group_dict = solr_utils.solr_convert_man_obj_obj_dict(attrib_group_man_obj)
            hierarchy_paths = [([attrib_group_dict] + p) for p in hierarchy_paths]

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

        # The last_index_hierarchy_paths is the index number for the last of the
        # hierarchy paths. If we're at the last path of heirarchies, we'll save
        # the solr_field_name and the parent_solr_field_name on the predicate's
        # AllManifest instances meta_json. This should simplify logic on composing
        # facet queries and getting facet fields.
        last_index_hierarchy_paths = len(hierarchy_paths) - 1
        for index_hierarchy_paths, hierarchy_items in enumerate(hierarchy_paths):
            act_solr_field = self._prefix_solr_field(root_solr_field)
            parent_solr_field = self._prefix_solr_field(root_solr_field)
            # Add the root solr field if it does not exist.
            last_item_index = len(hierarchy_items) - 1
            attribute_field_part = ''
            pred_obj_all_field = None
            for index, item_obj in enumerate(hierarchy_items):
                # Make sure this is a dictionary version of this item.
                if False:
                    print(f'act_solr_field: {act_solr_field} [{index}]: {item_obj}')
                item = solr_utils.solr_convert_man_obj_obj_dict(item_obj)

                if self._check_meta_json_to_skip_index(item):
                    # item meta_json says don't index this.
                    if False:
                        print(f"No solr indexing of pred { item.get('label') } (uuid: {item.get('uuid')}) ")
                    break

                # Add the solr field if it does not exist.
                if not self.fields.get(act_solr_field):
                    self.fields[act_solr_field] = []
                if index < last_item_index:
                    # Force parents to be of an id data type.
                    item['data_type'] = 'id'
                    self.fields['text'] += ' ' + item.get('label', '') + ' '

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

                if (
                    index > 0
                    and index < last_item_index
                ):
                    # Save the solr_field_name for items in the
                    # middle of a hierarchy.
                    # We do this only for the last of the hierarchy paths.
                    # So as to limit hits to the DB.
                    expected_meta_json = {
                        'solr_field': solr_utils.convert_slug_to_solr(
                            item_obj.get('slug')
                            + attribute_field_part
                            + SOLR_VALUE_DELIM
                            + FIELD_SUFFIX_PREDICATE
                        ),
                    }
                    if pred_obj_all_field:
                        expected_meta_json['obj_all_solr_field'] = pred_obj_all_field
                    # In cases of multiple hierarchies, this only updates the item_obj meta_json
                    # if we're on the last index of all the hierarchy paths. Otherwise,
                    # we'll only update the item_obj meta_json if it is missing an expected key.
                    self._update_pred_obj_meta_json(
                        expected_meta_json=expected_meta_json,
                        item_obj=copy.deepcopy(item_obj),
                        expect_key_only_check=(index_hierarchy_paths != last_index_hierarchy_paths),
                        attrib_group_man_obj=attrib_group_man_obj,
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
                if index_hierarchy_paths == last_index_hierarchy_paths:
                    # Make sure we save the solr_field_name and
                    # the parent_solr_field_name in the Manifest meta_json.
                    # We do this only for the last of the heirarchy paths.
                    # So as to limit hits to the DB.
                    expected_meta_json = {
                        'solr_field': solr_field_name
                    }
                    if pred_obj_all_field:
                        expected_meta_json['obj_all_solr_field'] = pred_obj_all_field
                    self._update_pred_obj_meta_json(
                        expected_meta_json=expected_meta_json,
                        item_obj=copy.deepcopy(item_obj),
                        expect_key_only_check=False,
                        attrib_group_man_obj=attrib_group_man_obj,
                    )
                # Now finally, add a prefix if this is a related item.
                solr_field_name = self._prefix_solr_field(solr_field_name)

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
            if obs.get('oc-gen:obsStatus', 'active') != 'active':
                # Skip this observation. It's there but has a deprecated
                # status.
                continue
            # Descriptive predicates are down in the events.
            for event_node in obs.get('oc-gen:has-events', []):
                if not event_node.get('has_descriptions'):
                    continue
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
                            pred_value_objects,
                            enforce_ld_outside_objects=True
                        )


    def _add_observations_links(self):
        """Adds linking info from item observations to the Solr doc."""
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
            if obs.get('oc-gen:obsStatus', 'active') != 'active':
                # Skip this observation. It's there but has a deprecated
                # status.
                continue
            # Descriptive predicates are down in the events.
            for event_node in obs.get('oc-gen:has-events', []):
                if not event_node.get('has_relations'):
                    # there are no linking relations in this event node, so skip.
                    continue
                for attrib_group in event_node.get('oc-gen:has-attribute-groups', []):
                    for rel_item_type, pred_value_dicts in attrib_group.get('relations', {}).items():
                        if rel_item_type in ['documents', 'subjects_children', 'subjects', 'persons', 'tables']:
                            solr_field = f'{rel_item_type}_count'
                            for _, pred_value_objects in pred_value_dicts.items():
                                # Add to the count for this item type
                                self.fields[solr_field] += len(pred_value_objects)
                        if rel_item_type == 'persons':
                            # Add uuids for related person and organizations to make it easier to directly query
                            # for items with some direct type of relationship with each person and org.
                            if not JOIN_PERSON_ORG_SOLR in self.fields:
                                self.fields[JOIN_PERSON_ORG_SOLR] = []
                            for _, pred_value_objects in pred_value_dicts.items():
                                for obj_dict in pred_value_objects:
                                    self._add_solr_field_values(
                                        JOIN_PERSON_ORG_SOLR,
                                        [obj_dict]
                                    )
                        if rel_item_type == 'media':
                            for _, pred_value_objects in pred_value_dicts.items():
                                for obj_dict in pred_value_objects:
                                    if obj_dict.get('type') == 'oc-gen:image':
                                        self.fields['image_media_count'] += 1
                                    elif obj_dict.get('type') in ['oc-gen:3d-model']:
                                        self.fields['three_d_media_count'] += 1
                                    elif obj_dict.get('type') in ['oc-gen:geospatial-file', 'oc-gen:gis-vector-file']:
                                        self.fields['gis_media_count'] += 1
                                    else:
                                        self.fields['other_binary_media_count'] += 1
                            for key_uri, solr_field in FILE_TYPE_SOLR_FIELD_DICT.items():
                                if self.fields.get(solr_field):
                                    # We already have one of these.
                                    continue
                                if not obj_dict.get(key_uri):
                                    continue
                                # This is NOT a multi-valued field
                                self.fields[solr_field] = AllManifest().clean_uri(obj_dict.get(key_uri))



    def _add_descriptions_outside_observations(self):
        """Adds descriptions for items that are NOT part of an observation node"""
        for no_node_key in NO_NODE_KEYS:
            if not self.rep_dict.get(no_node_key):
                # This key does not exist in our rep_dict, so skip.
                continue
            if not isinstance(self.rep_dict.get(no_node_key), list):
                # The predicate has a value that needs special treatment,
                # b/c it is NOT a list of dicts, so continue.
                continue
            for pred_value_object in self.rep_dict.get(no_node_key):
                if not isinstance(pred_value_object, dict):
                    # A case like dc-terms:identifier where the objects
                    # are strings.
                    continue
                solr_field_name = self._get_predicate_solr_field_name_in_hierarchy(
                    assert_dict=pred_value_object,
                    is_default_attrib_group=True,
                )
                if not solr_field_name:
                    # We don't have a solr field name, so skip.
                    continue
                self._add_solr_field_values(
                    solr_field_name,
                    [pred_value_object]
                )


    def _add_geo_coordinate_fields(
        self,
        event_class_slug,
        latitude,
        longitude,
        location_precision_factor
    ):
        """Adds solr fields for an event class latitude and longitude

        :param str event_class_slug: An event class slug or
            catch-all ALL_EVENTS_SOLR slug so events of a given
            type are prefixed in solr dynamic geo and chrono
            fields.
        :param float latitude: A float WGS-84 latitude value
        :param float longitude: A float WGS-84 longitude value
        """
        if not latitude or not longitude:
            # Skip out, we lack coordinates.
            return False

        # We're trusting these are valid!

        # Capture the count of the number of geospatial objects associated
        # with this item.
        geo_count_field = event_class_slug + SOLR_VALUE_DELIM + 'geo_count'
        if not self.fields.get(geo_count_field):
            self.fields[geo_count_field] = 0
        self.fields[geo_count_field] += 1

        # NOTE: ___geo_location is a SINGLE value field. Populate it only once for
        # using the first (most important) feature of this event class.
        coords_str = f'{latitude},{longitude}'
        # We'll do the geo_location (a normal location field) and geo_location_rpt,
        # a recursive tree model lots like the geotiles we have implemented, but probably
        # faster and better b/c it is Solr.
        for geo_suffix in ['geo_location',  'geo_location_rpt']:
            solr_geo_location_field = event_class_slug + SOLR_VALUE_DELIM + geo_suffix
            if not self.fields.get(solr_geo_location_field):
                self.fields[solr_geo_location_field] = coords_str


        if  location_precision_factor == 0:
            # Default with no noted reduction in precision is to
            # index geotiles with the maximum zoom level.
            location_precision_factor = MAX_GEOTILE_ZOOM
        if location_precision_factor < MIN_GEOTILE_ZOOM:
            location_precision_factor = MIN_GEOTILE_ZOOM
        if location_precision_factor > MAX_GEOTILE_ZOOM:
            location_precision_factor = MAX_GEOTILE_ZOOM
        gm = GlobalMercator()
        tile = gm.lat_lon_to_quadtree(
            latitude,
            longitude,
            location_precision_factor
        )

        if len(tile) <= (location_precision_factor - 2):
            print(
                f'Problem with location precision {location_precision_factor} '
                f'and tile: {tile}'
            )
            return False

        # NOTE: ___geo_tile is a multi-valued field, so we can add multiple
        # geo-tile values for this event class.
        solr_geo_tile_field = event_class_slug + SOLR_VALUE_DELIM + 'geo_tile'
        if not self.fields.get(solr_geo_tile_field):
            self.fields[solr_geo_tile_field] = []
        if tile not in self.fields[solr_geo_tile_field]:
            self.fields[solr_geo_tile_field].append(tile)

        # NOTE: This is for lower resolution (more general indexing) for
        # better performance when we want "big picture", more general geo-tile
        # facets
        solr_lr_geo_tile_field = event_class_slug + SOLR_VALUE_DELIM + 'lr_geo_tile'
        if not self.fields.get(solr_lr_geo_tile_field):
            self.fields[solr_lr_geo_tile_field] = []
        lr_tile = tile[:LOW_RESOLUTION_GEOTILE_LENGTH]
        if lr_tile not in self.fields[solr_lr_geo_tile_field]:
            self.fields[solr_lr_geo_tile_field].append(lr_tile)
        return True


    def _add_or_widen_chrono_point_range(self, solr_chrono_point_field, date_start, date_stop):
        """Adds or widens a chronological point to a field so as to limit points to only 1 value

        :param str solr_chrono_point_field: The solr field name for the chrono point
        :param int date_start: The start date
        :param int date_stop: The end date
        """
        if not self.fields.get(solr_chrono_point_field):
            self.fields[solr_chrono_point_field] = [
                f'{date_start},{date_stop}'
            ]
            return None
        str_vals =  self.fields[solr_chrono_point_field][0].split(',')
        dates = [int(float(v)) for v in str_vals] + [date_start, date_stop,]
        self.fields[solr_chrono_point_field] = [f'{min(dates)},{max(dates)}']


    def _add_chrono_event(self, feature, event_class_slug):
        """Adds chronology related solr fields given a when dict object

        :param dict feature: A GeoJSON feature with additional keys
            used for solr indexing.
        :param str event_class_slug: An event class slug or
            catch-all ALL_EVENTS_SOLR slug so events of a given
            type are prefixed in solr dynamic geo and chrono
            fields.
        """
        when_dict = feature.get('when')
        if not when_dict:
            return None

        if when_dict.get('reference_type') == 'specified':
            # This item has its own chronological data, not inferred from
            # another source.
            self.chrono_specified = True

        # NOTE: ___chrono_source is a SINGLE value field. Populate it only once for
        # using the first (most important) feature of this event class.
        solr_chrono_source_field = event_class_slug + SOLR_VALUE_DELIM + 'chrono_source'
        if not self.fields.get(solr_chrono_source_field):
            self.fields[solr_chrono_source_field] = solr_utils.make_solr_entity_str(
                slug=when_dict.get('reference_slug'),
                data_type='id',
                uri=when_dict.get('reference_uri'),
                label=when_dict.get('reference_label'),
            )

        # NOTE: ___chrono_tile is a multi-valued field, so we can add multiple
        # chrono-tile values for this event class.
        date_start = when_dict.get('earliest')
        date_stop = when_dict.get('latest')
        if date_start is None and date_stop is None:
            return None
        if date_start is None:
            date_start = date_stop
        if date_stop is None:
            date_stop = date_start

        # Capture the count of the number of chronology time spans associated
        # with this item.
        chrono_count_field = event_class_slug + SOLR_VALUE_DELIM + 'chrono_count'
        if not self.fields.get(chrono_count_field):
            self.fields[chrono_count_field] = 0
        self.fields[chrono_count_field] += 1

        # Try to make a chrono-path. This will error out if the date range
        # exceeds the maximum range allowed.
        try:
            chrono_path = chronotiles.encode_path_from_bce_ce(
                date_start, date_stop, prefix=''
            )
        except:
            chrono_path = None
        if chrono_path:
            # Make the fill resolution chronopath field.
            solr_chrono_tile_field = event_class_slug + SOLR_VALUE_DELIM + 'chrono_tile'
            if not self.fields.get(solr_chrono_tile_field):
                self.fields[solr_chrono_tile_field] = []
            if chrono_path not in self.fields[solr_chrono_tile_field]:
                self.fields[solr_chrono_tile_field].append(chrono_path)
            # Now make the lower resolution chronopath field by dropping the
            # last several characters from the path
            solr_lr_chrono_tile_field = event_class_slug + SOLR_VALUE_DELIM + 'lr_chrono_tile'
            if not self.fields.get(solr_lr_chrono_tile_field):
                self.fields[solr_lr_chrono_tile_field] = []
            lr_chrono_path = chrono_path[0:-LOW_RESOLUTION_CHRONOTILE_DROP_LAST]
            if lr_chrono_path not in self.fields[solr_lr_chrono_tile_field]:
                self.fields[solr_lr_chrono_tile_field].append(lr_chrono_path)

        # Strictly speaking, the point field here is redundant,
        # but I want to experiment with it because it encapsulates
        # start and stop values together (like the chrono_tile).
        # It's useful to see if Solr can aggregate these for useful
        # faceting.
        solr_chrono_point_field = event_class_slug + SOLR_VALUE_DELIM + 'chrono_point'
        self._add_or_widen_chrono_point_range(solr_chrono_point_field, date_start, date_stop)



    def _add_space_time_feature_event(self, feature, event_class_slug):
        """Adds space-time fields from a feature GeoJSON dict

        :param dict feature: A GeoJSON feature with additional keys
            used for solr indexing.
        :param str event_class_slug: An event class slug or
            catch-all ALL_EVENTS_SOLR slug so events of a given
            type are prefixed in solr dynamic geo and chrono
            fields.
        """
        props = feature.get('properties')
        if not props:
            return None
        event_class_slug = solr_utils.convert_slug_to_solr(
            event_class_slug
        )

        # NOTE: Add the geo coordinates.
        coords_ok = self._add_geo_coordinate_fields(
            event_class_slug,
            latitude=props.get('latitude'),
            longitude=props.get('longitude'),
            location_precision_factor=props.get('location_precision_factor', 0),
        )
        if not coords_ok:
            # We don't have ok coordinates, so skip out.
            return None

        # Add the event class slug to the list for this item.
        if not self.fields.get('event_class_slugs'):
            self.fields['event_class_slugs'] = []
        if event_class_slug != ALL_EVENTS_SOLR:
            self.fields['event_class_slugs'].append(event_class_slug)

        # NOTE: ___geo_source is a SINGLE value field. Populate it only once for
        # using the first (most important) feature of this event class.
        solr_geo_source_field = event_class_slug + SOLR_VALUE_DELIM + 'geo_source'
        if not self.fields.get(solr_geo_source_field):
            self.fields[solr_geo_source_field] = solr_utils.make_solr_entity_str(
                slug=props.get('reference_slug'),
                data_type='id',
                uri=props.get('reference_uri'),
                label=props.get('reference_label'),
            )

         # NOTE: ___geo_source is a SINGLE value field. Populate it with the maximum
         # (worst precision) value of all features for this event class.
        solr_geo_precision_factor_field = event_class_slug + SOLR_VALUE_DELIM + 'geo_precision_factor'
        if not self.fields.get(solr_geo_precision_factor_field):
            self.fields[solr_geo_precision_factor_field] = 0
        if props.get('location_precision_factor', 0) > self.fields[solr_geo_precision_factor_field]:
            self.fields[solr_geo_precision_factor_field] = props.get('location_precision_factor')

        # Add chronology related information for this event class, if it exists.
        self._add_chrono_event(feature, event_class_slug)


    def _add_space_time_feature(self, feature):
        """Adds space-time fields from a feature GeoJSON dict

        :param dict feature: A GeoJSON feature with additional keys
            used for solr indexing.
        """
        props = feature.get('properties')
        if not props:
            return None
        if props.get('reference_type') == 'specified':
            # This item has its own geospatial data, not inferred from
            # another source.
            self.geo_specified = True
        act_event_class_slug = props.get('event__item_class__slug')
        if not act_event_class_slug:
            return None
        for event_class_slug in [ALL_EVENTS_SOLR, act_event_class_slug]:
            # Add fields for all event classes, and this specific event
            # class.
            self._add_space_time_feature_event(feature, event_class_slug)


    def _add_space_time_features(self):
        """Adds geospatial and chronology solr field data for
        each class of event.
        """
        if not self.rep_dict.get('features'):
            # NO spacetime information to add.
            return None
        for feature in self.rep_dict.get('features'):
            self._add_space_time_feature(feature)


    def _add_persistent_identifiers(self):
        """Adds persistent identifiers to the solr document"""
        for id_key in LD_IDENTIFIER_PREDICATES:
            if not self.rep_dict.get(id_key):
                continue
            if not self.fields.get('persistent_uri'):
                self.fields['persistent_uri'] = []
            for id_val in self.rep_dict.get(id_key):
                id_val = AllManifest().clean_uri(id_val)
                if id_val in self.fields['persistent_uri']:
                    continue
                self.fields['persistent_uri'].append(id_val)
                self._clean_add_uri_to_solr_object_uri_field(
                    id_val,
                    clean_first=False
                )


    def _add_media_fields(self):
        """Adds media size and type fields to the solr document."""
        if self.man_obj.item_type != 'media':
            return None
        if not self.rep_dict.get('oc-gen:has-files'):
            # Skip this, not a media type item, or missing
            # required data.
            return None
        if not self.fields.get(FILE_SIZE_SOLR):
            self.fields[FILE_SIZE_SOLR] = 0
        # Iterate through the file items.
        for file_item in self.rep_dict.get('oc-gen:has-files'):
            if not 'type' in file_item or not 'dc-terms:hasFormat' in file_item:
                # We're missing key data, so skip.
                continue
            if file_item['type'] in ['oc-gen:archive', 'oc-gen:ia-fullfille', 'oc-gen:fullfile']:
                self.fields[FILE_MIMETYPE_SOLR] = AllManifest().clean_uri(file_item['dc-terms:hasFormat'])

            # Populate the solr field for this file type, if not already populated.
            solr_file_uri_field = FILE_TYPE_SOLR_FIELD_DICT.get(file_item['type'])
            if solr_file_uri_field and not self.fields.get(solr_file_uri_field):
                # Populate solr field with the uri for this file type.
                self.fields[solr_file_uri_field] = AllManifest().clean_uri(file_item['id'])

            if not file_item.get('dcat:size'):
                continue
            size = float(file_item.get('dcat:size'))
            if size > self.fields[FILE_SIZE_SOLR]:
                # The biggest filesize gets indexed.
                self.fields[FILE_SIZE_SOLR] = size


    def _double_check_human_remains(self):
        """Checks if this item has metadata relating to human remains"""
        if self.fields.get('human_remains'):
            # This is already flagged, so no need to do further checks.
            return None

        if self.man_obj.meta_json.get('flag_human_remains'):
            # Sensitive data needing to be flagged.
            self.fields['human_remains'] = True
            return None

        if  self.man_obj.item_class.item_key in sensitive_content.HUMAN_REMAINS_ITEM_CLASS_KEYS:
            # The item class is about human remains.
            self.fields['human_remains'] = True
            return None

        if  self.man_obj.item_class.uri in sensitive_content.HUMAN_REMAINS_ITEM_CLASS_URIS:
            # The item class URI is about human remains.
            self.fields['human_remains'] = True
            return None

        if set(
            sensitive_content.HUMAN_REMAINS_LINKED_DATA_URIS
        ).intersection(set(self.fields.get('object_uri', []))):
            # The item has associated URIs that are about human remains or burials
            self.fields['human_remains'] = True


    def _add_linked_subjects(self):
        """Adds fields from related subject items to the solr document."""

        # NOTE: This essentially denormalizes media and document items.
        # Some of the important descriptive fields of the subjects
        # associated with a given media or document item get added
        # to the solr document. This allows the subject items to
        # provide metadata that further allow searching of media and
        # documents items (that tend not to have great metadata without
        # such associations)

        if not self.man_obj.item_type in ['media', 'documents', ]:
            # This is only done for media and documents items.
            return None
        # Get the list of all the observations made on this item.
        # Each observation is a dictionary with descriptive assertions
        # keyed by a predicate.
        subject_dicts = []
        for obs in self.rep_dict.get('oc-gen:has-obs', []):
             # Get the status of the observation, defaulting to 'active'.
             # We are OK to index observation assertions if the observation is
             # active, otherwise we should skip it to so that the inactive
             # observations do not get indexed.
            if obs.get('oc-gen:obsStatus', 'active') != 'active':
                # Skip this observation. It's there but has a deprecated
                # status.
                continue
            # Descriptive predicates are down in the events.
            for event_node in obs.get('oc-gen:has-events', []):
                if not event_node.get('has_relations'):
                    continue
                for attrib_group in event_node.get('oc-gen:has-attribute-groups', []):
                    for rel_item_type, pred_value_dicts in attrib_group.get('relations', {}).items():
                        if rel_item_type != 'subjects':
                            # We only care about subjects items for related linking.
                            continue
                        for _, pred_value_objects in pred_value_dicts.items():
                            subject_dicts += pred_value_objects

        if self.rep_dict.get('contexts'):
            # Add the last context (the most specific one) from the context items.
            subject_dicts.append(self.rep_dict['contexts'][-1])

        if not JOIN_SOLR in self.fields:
            # We don't have a solr field for joins yet, so
            # make one.
            self.fields[JOIN_SOLR] = []
        for subject_dict in subject_dicts:
            related_object_id = subject_dict.get('object_id')
            if not related_object_id:
                # we don't have a related item.
                continue
            if related_object_id == str(self.man_obj.uuid):
                # The related item is the same as our current item, so skip
                continue
            if related_object_id in self.fields[JOIN_SOLR]:
                # We've already added this.
                continue
            if False:
                print (f'Get related item_type subjects: {related_object_id}')
            rel_sd_obj = SolrDocumentNS(uuid=related_object_id, do_related=True)
            rel_sd_obj.make_related_solr_doc()
            self.fields[JOIN_SOLR].append(related_object_id)
            if rel_sd_obj.fields.get('human_remains'):
                # The related subjects item is about human remains, so
                # flag this for human remains.
                self.fields['human_remains'] = True
            self.fields['text'] += '/n' + rel_sd_obj.fields['text'] + '/n'
            for field_key, vals in rel_sd_obj.fields.items():
                if not field_key.startswith(RELATED_SOLR_DOC_PREFIX):
                    # We only want to add fields from the rel_sd_obj
                    # that start with the RELATED_SOLR_DOC_PREFIX.
                    continue
                if field_key not in self.fields:
                    self.fields[field_key] = []
                # Force the vals of the related solr doc
                # to be a list.
                if not isinstance(vals, list):
                    vals = [vals]
                # Add a list of values.
                for val in vals:
                    if val in self.fields[field_key]:
                        # We already have this value, don't index
                        # the redundant value.
                        continue
                    self.fields[field_key].append(val)


    def _add_table_specifics(self):
        """Adds table specifics"""
        if self.man_obj.item_type != 'tables':
            return None
        for assert_obj in self.assert_objs:
            if str(assert_obj.predicate.uuid) != configs.CSVW_COLUMNS_UUID:
                continue
            self.fields['text'] += ' ' + assert_obj.object.label
            self._clean_add_uri_to_solr_object_uri_field(assert_obj.object.uri)


    def _calculate_interest_for_project(self):
        """Add to the interest score for projects based on scale and diversity"""
        if self.man_obj.item_type != 'projects':
            return 0
        sub_projects_qs = AllManifest.objects.filter(
            project=self.man_obj,
            item_type='projects'
        )
        projects = [self.man_obj]
        for proj_obj in sub_projects_qs:
            if proj_obj in projects:
                continue
            projects.append(proj_obj)
        item_type_class_mq = AllManifest.objects.filter(
            project__in=projects,
            item_type__in=configs.OC_ITEM_TYPES,
        ).distinct(
            'item_type',
            'item_class'
        ).order_by(
            'item_type',
            'item_class'
        ).values_list(
            'item_type',
            'item_class',
        )
        print(f'found {len(item_type_class_mq)} distinct item_types and item_classes')
        item_type_class_counts = []
        for (item_type, item_class) in item_type_class_mq:
            count_item_type_class = AllManifest.objects.filter(
                project__in=projects,
                item_type=item_type,
                item_class=item_class,
            ).count()
            tup = (item_type, item_class, count_item_type_class,)
            item_type_class_counts.append(tup)
        item_type_class_counts.sort(reverse=True, key=lambda a: a[2])
        proj_score = 0
        count_multiplier = PROJ_ITEM_COUNT_FACTOR
        for item_type, _, count_item_type_class in item_type_class_counts:
            media_bonus = 1
            if item_type == 'media':
                media_bonus = 1.5
            proj_score += count_item_type_class * count_multiplier * media_bonus
            print(f'Proj score: {proj_score} += {count_item_type_class} * {count_multiplier} * {media_bonus} [{item_type}]')
            count_multiplier += PROJ_ITEM_TYPE_ITEM_CLASS_COUNT_VARIETY_BONUS
        return proj_score


    def _calculate_interest_score(self):
        """ Calculates the 'interest score' for sorting items with more
        documentation / description to a higher rank.
        """

        # Start the interest score on the base for this item_type.
        score = ITEM_TYPE_INTEREST_SCORES.get(
            self.man_obj.item_type,
            DEFAULT_BASE_INTEREST_SCORE
        )

        rel_solr_field_prefix = solr_utils.convert_slug_to_solr(
            RELATED_SOLR_DOC_PREFIX
        )
        for field_key, value in self.fields.items():
            if (field_key.startswith(rel_solr_field_prefix) and
                '__pred_' in field_key):
                # The more richly related items are described, the
                # more interesting.
                score += 0.1
            elif '__pred_' in field_key:
                score += 1

        score += len(self.fields['text']) / 200
        score += self.fields['image_media_count'] * 4
        score += self.fields['three_d_media_count'] * 10
        score += self.fields['gis_media_count'] * 10
        score += self.fields['other_binary_media_count'] * 5
        score += self.fields['documents_count'] * 4
        score += self.fields['subjects_children_count'] * 0.1
        score += self.fields['subjects_count']
        score += self.fields['persons_count'] * 2
        score += self.fields['tables_count'] * 5
        # Add project scale and diversity score values. Will be
        # zero for non-project item_types
        score += self._calculate_interest_for_project()
        if self.geo_specified:
            # geo data specified, more interesting
            score += 5
        if self.chrono_specified:
            # chrono data specified, more interesting
            score += 5
        # Add to the score based on the file size of a media file.
        score += self.fields.get(FILE_SIZE_SOLR, 0 ) / 50000
        self.fields['interest_score'] = score


    def make_solr_doc(self):
        """Make a solr document """
        if not self.man_obj or not self.rep_dict:
            return None
        # Set the required, universal fields for Solr
        self._set_required_solr_fields()
        # Add labeling text to the general text field
        self._add_labels_titles_to_text_field()
        # Add text content (project abstract, document content, etc.
        # to the text field)
        self._add_text_contents()
        # Add the project hierarchy
        self._set_solr_project_fields()
        # Add the item spatial context hierarchy
        self._add_solr_spatial_context()
        # Add the item_class hierarchies
        self._add_category_hierarchies()
        # Add descriptions from observations
        self._add_observations_descriptions()
        # Add counts for links to different item_types
        self._add_observations_links()
        # Add descriptions that are NOT in observation nodes.
        self._add_descriptions_outside_observations()
        # Add space and time fields
        self._add_space_time_features()
        # Add DOIs, ARKs, ORCID persistent IDs.
        self._add_persistent_identifiers()
        # Add Media file links, size, etc.
        self._add_media_fields()
        # Just to be sure, check metadata about human remains
        # associated metadata in order to flag this item if needed.
        self._double_check_human_remains()
        # Applicable only to media and documents item_types,
        # add fields from related subjects items.
        self._add_linked_subjects()
        # Add table specific indexing information
        self._add_table_specifics()
        # Calculate the interest score for the item
        self._calculate_interest_score()
        return True


    def make_related_solr_doc(self):
        """Make a related solr document """
        if not self.man_obj or not self.rep_dict:
            return None
        self.do_related = True
        self.solr_doc_prefix = RELATED_SOLR_DOC_PREFIX
        # Add the item_class hierarchies
        self._add_category_hierarchies()
        # Add descriptions from observations
        self._add_observations_descriptions()
        # Add descriptions that are NOT in observation nodes.
        self._add_descriptions_outside_observations()
        # Just to be sure, check metadata about human remains
        # associated metadata in order to flag this item if needed.
        self._double_check_human_remains()
        return True