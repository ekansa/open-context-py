import datetime
import json
from django.conf import settings
from opencontext_py.libs.languages import Languages
from django.utils.encoding import force_text
from opencontext_py.libs.isoyears import ISOyears
from opencontext_py.libs.general import LastUpdatedOrderedDict, DCterms
from opencontext_py.apps.contexts.readprojectcontext import ReadProjectContextVocabGraph as projGraph
from opencontext_py.apps.ocitems.ocitem.generation import OCitem
from opencontext_py.apps.ocitems.ocitem.itemkeys import ItemKeys
from opencontext_py.apps.ldata.linkannotations.recursion import LinkRecursion
from opencontext_py.apps.ldata.linkannotations.equivalence import LinkEquivalence
from opencontext_py.apps.ocitems.projects.metadata import ProjectRels
from opencontext_py.apps.ocitems.queries.geochrono import GeoChronoQueries
from opencontext_py.libs.chronotiles import ChronoTile
from opencontext_py.libs.globalmaptiles import GlobalMercator
from opencontext_py.apps.entities.uri.models import URImanagement





def general_get_jsonldish_entity_parents(identifier, add_original=True):
    """Wrapper for getting parent entities for oc items and parent projects"""
    raw_hiearchy_items = LinkRecursion().get_jsonldish_entity_parents(
        identifier,
        add_original=add_original
    )
    if raw_hiearchy_items:
        return raw_hiearchy_items
    raw_hiearchy_items = ProjectRels().get_jsonldish_parents(
        uuid=identifier,
        add_original=add_original
    )
    return raw_hiearchy_items

def get_id(dict_obj, id_keys=['id', '@id']):
    """Gets an ID from a dictionary object."""
    # NOTE: this uses a ranked ordered list of keys
    for id_key in id_keys:
        if id_key in dict_obj:
            return dict_obj[id_key]
    return None


class SolrDocumentNew:
    '''
    Defines the Solr Document objects that the crawler will crawl. Solr
    fields are stored in a Solr Document's "fields" property.

from opencontext_py.apps.indexer.solrdocumentnew import SolrDocumentNew
# Example Bone (subjects)
uuid = '9095FCBB-35A8-452E-64A3-B8D52A0B2DB3'
sd_obj = SolrDocumentNew(uuid)
sd_obj.make_solr_doc()
sd_obj.fields

from opencontext_py.apps.indexer.solrdocumentnew import SolrDocumentNew
# Example with missing predicate
uuid = '775b5d81-81ae-45ee-b622-6f9257c4bedd'
sd_obj = SolrDocumentNew(uuid)
sd_obj.make_solr_doc()
sd_obj.fields

from opencontext_py.apps.indexer.solrdocumentnew import SolrDocumentNew
# Example with missing predicate
uuid = 'EC4E750C-BEF8-46BE-0398-CB4C6464DF71'
sd_obj = SolrDocumentNew(uuid)
sd_obj.make_solr_doc()
sd_obj.fields


# Example coin (subjects)
uuid_a = 'BB35B081-FD20-4339-67F4-00DB99079338'
sd_obj_a = SolrDocumentNew(uuid_a)
sd_obj_a.make_solr_doc()
sd_obj_a.fields

# Example Predicate
uuid_b = '04909421-C28E-46AF-98FA-10F888B64A4D'
sd_obj_b = SolrDocumentNew(uuid_b)
sd_obj_b.make_solr_doc()
sd_obj_b.fields

# Example Media
uuid_c = 'fdbfad01-1a79-4b54-bda0-51b79fcedf76'
sd_obj_c = SolrDocumentNew(uuid_c)
sd_obj_c.make_solr_doc()
sd_obj_c.fields

# Example Media of Human Remains
uuid_d = 'F675E155-81C9-4641-41AA-85A28DC44D90'
sd_obj_d = SolrDocumentNew(uuid_d)
sd_obj_d.make_solr_doc()
sd_obj_d.fields

# Example of Subject of Human Remains
uuid_f = '44f2f90e-3e9b-4bcb-8003-1ad7bddc070d'
sd_obj_fr = SolrDocumentNew(uuid_f)
sd_obj_fr.make_related_solr_doc()
sd_obj_fr.fields

# Example of a Media Image associated with Human Remains
uuid_g = 'e04961ef-5f48-412a-88a7-42c34a1f11e0'
sd_obj_g = SolrDocumentNew(uuid_g)
sd_obj_g.make_solr_doc()
sd_obj_g.fields
sd_obj_g.fields['human_remains']

# Example Document
uuid_h = 'e4676e00-0b9f-40c7-9cb1-606965445056'
sd_obj_h = SolrDocumentNew(uuid_h)
sd_obj_h.make_solr_doc()
sd_obj_h.fields

# Example Project
uuid_i = '3F6DCD13-A476-488E-ED10-47D25513FCB2'
sd_obj_i = SolrDocumentNew(uuid_i)
sd_obj_i.make_solr_doc()
sd_obj_i.fields

# Example Project with Subprojects
uuid_j = '416A274C-CF88-4471-3E31-93DB825E9E4A'
sd_obj_j = SolrDocumentNew(uuid_j)
sd_obj_j.make_solr_doc()
sd_obj_j.fields

# Example Project of a Subproject
uuid_k = '0cea2f4a-84cb-4083-8c66-5191628abe67'
sd_obj_k = SolrDocumentNew(uuid_k)
sd_obj_k.make_solr_doc()
sd_obj_k.fields
    '''

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
    
    LABELING_PREDICATES = [
        'label',
        'skos:altLabel',
        'skos:prefLabel',
        'dc-terms:title',
    ]
    
    CONTEXT_PREDICATES = [
        ItemKeys.PREDICATES_OCGEN_HASCONTEXTPATH,
        ItemKeys.PREDICATES_OCGEN_HASLINKEDCONTEXTPATH,
    ]
    
    # Default publication date, if the record does not exist.
    # This should ONLY be the case for the very first example
    # datasets in Open Context, before we got our metadata
    # house in better order.
    DEFAULT_PUBLISHED_DATETIME = datetime.date(2007, 1, 1)

    ALL_CONTEXT_SOLR = 'obj_all___context_id'
    ROOT_CONTEXT_SOLR = 'root___context_id'
    ROOT_PREDICATE_SOLR = 'root___pred_id'
    ROOT_LINK_DATA_SOLR = 'ld___pred_id'
    ROOT_PROJECT_SOLR = 'root___project_id'
    ALL_PROJECT_SOLR = 'obj_all___project_id'
    EQUIV_LD_SOLR = 'skos_closematch___pred_id'
    FILE_SIZE_SOLR = 'filesize___pred_numeric'
    FILE_MIMETYPE_SOLR = 'mimetype___pred_id'
    RELATED_SOLR_DOC_PREFIX = 'rel--'
    
    MISSING_PREDICATE_TYPES = [
        False,
        None,
        '',
        'None',
        'False'
    ]


    # Maximum depth of geotile zoom
    MAX_GEOTILE_ZOOM = 30
    # Minimum allowed geotile zoom
    MIN_GEOTILE_ZOOM = 6
    
    # Human Remains Field Checks. The following configures how Open Context
    # will flag a solr document as about human remains. Some audiences may
    # want a warning about viewing human remains, so we need reliable methods
    # to catch records of human remains. The 'human_remains' solr field can
    # also be directly set to a positive integer if the below checks don't
    # work.
    HUMAN_REMAINS_FIELD_VALUES = [
        # Classified with Open Context's class-uri of oc-gen:cat-human-bone.
        ('{}obj_all___oc_gen_subjects___pred_id_fq', 'oc-gen-cat-human-bone'),
        
        # Has biological taxonomy of homo sapiens in EOl or GBIF.
        ('{}obj_all___biol_term_hastaxonomy___pred_id_fq', 'eol-p-327955'),
        ('{}obj_all___biol_term_hastaxonomy___pred_id_fq', 'gbif-sp-2436436'),
        
        # Has specific metadata about human remains assigned to the record.
        # Human-remains (archaeology)
        ('{}obj_all___dc_terms_subject___pred_id_fq', 'loc-sh-sh92003545'),
        # Human skeleton
        ('{}obj_all___dc_terms_subject___pred_id_fq', 'loc-sh-sh85062895'),
        # Burial
        ('{}obj_all___dc_terms_subject___pred_id_fq', 'loc-sh-sh85018080'),
    ]
    
    # The delimiter for parts of an object value added to a
    # solr field.
    SOLR_VALUE_DELIM = '___'
    
    def __init__(self, uuid):
        '''
        Using our Python JSON-LD and other info provided in OCitem,
        build up dictionary of solr fields to index.
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
        self.oc_item = None
        self.proj_graph_obj = None
        # First get core data structures
        oc_item = OCitem()
        if oc_item.check_exists(uuid):
            # We found a record for this in the manifest
            oc_item.generate_json_ld()
            self.oc_item = oc_item
            self.proj_graph_obj = projGraph(self.oc_item.proj_context_json_ld)
        self.geo_specified = False
        self.chrono_specified = False
        # Store values here
        self.fields = LastUpdatedOrderedDict()
        self.fields['text'] = ''  # Start of full-text field
        self.fields['human_remains'] = 0  # Default, item is not about human remains.
        # Default media counts.
        self.fields['image_media_count'] = 0
        self.fields['other_binary_media_count'] = 0
        self.fields['document_count'] = 0
        # The solr field for joins by uuid.
        self.join_solr_field = 'join' +  self.SOLR_VALUE_DELIM + 'pred_id'
    
    def ensure_text_ok(self):
        """ Makes sure the text is solr escaped """
        self.fields['text'] = force_text(
            self.fields['text'],
            encoding='utf-8',
            strings_only=False,
            errors='surrogateescape'
        )
    
    def _convert_slug_to_solr(self, slug):
        """Converts a slug to a solr style slug."""
        # slug = self.solr_doc_prefix + slug
        return slug.replace('-', '_')

    def _concat_solr_string_value(self, slug, type, id, label):
        """Make a solr value for an object item."""
        id_part = id
        uri_parsed = URImanagement.get_uuid_from_oc_uri(
            id,
            return_type=True
        )
        if isinstance(uri_parsed, dict):
            id_part = '/' + uri_parsed['item_type'] + '/' + uri_parsed['uuid']
        slug = self.solr_doc_prefix + slug
        return self.SOLR_VALUE_DELIM.join(
            [slug, type, id_part, label]
        )

    def _add_labels_titles_to_text_field(self):
        """Adds multiple language labels and titles to add to text field."""
        lang_obj = Languages()
        for label_pred in self.LABELING_PREDICATES:
            if not label_pred in self.oc_item.json_ld:
                continue
            self.fields['text'] += lang_obj.get_all_value_str(
                self.oc_item.json_ld[label_pred]
            )
            self.fields['text'] += ' \n'
    
    def _add_text_content(self):
        """ Gets text content for indexing
        """
        for pred in settings.TEXT_CONTENT_PREDICATES:
            if not pred in self.oc_item.json_ld:
                continue
            lang_obj = Languages()
            self.fields['text'] += lang_obj.get_all_value_str(
                self.oc_item.json_ld[pred]
            ) + '\n'
    
    def _make_slug_type_uri_label(self):
        """Makes a slug_type_uri_label field for solr """
        parts = [
            self.oc_item.json_ld['slug']
        ]
        if self.oc_item.manifest.item_type == 'predicates':
            if self.oc_item.json_ld['oc-gen:data-type']:
                # Looks up the predicte type mapped to Solr types
                parts.append(
                    self._get_solr_predicate_type_string(
                        self.oc_item.json_ld['oc-gen:data-type']
                    )
                )
            else:
                # Defaults to ID
                parts.append('id')
        else:
            parts.append('id')
        parts.append('/' + self.oc_item.manifest.item_type + '/' + self.oc_item.manifest.uuid)
        parts.append(self.oc_item.json_ld['label'])
        return self.SOLR_VALUE_DELIM.join(parts)

    def _set_required_solr_fields(self):
        """Sets data for the core solr fields (non-dynamic, required)."""
        self.fields['uuid'] = self.oc_item.manifest.uuid
        self.fields['slug_type_uri_label'] = self._make_slug_type_uri_label()
        self.fields['project_uuid'] = self.oc_item.manifest.project_uuid
        if not self.oc_item.manifest.published:
            published_datetime = self.DEFAULT_PUBLISHED_DATETIME
        else:
            published_datetime = self.oc_item.manifest.published
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
            '0.' + self.oc_item.manifest.sort.replace('-', '')
        )
        # default, adds to interest score once other fields determined
        self.fields['interest_score'] = 0
        self.fields['item_type'] = self.oc_item.manifest.item_type

    def _add_id_field_fq_field_values(
            self,
            solr_id_field,
            concat_val,
            slug,
            do_fq_only=False
        ):
        """Adds values for an id field, and the associated slug
           value for the related _fq field
        """
        if (not isinstance(solr_id_field, str) or
            not isinstance(concat_val, str)):
            return None
        # Add the main solr id field if not present,
        # then append the concat_val
        if do_fq_only is False and solr_id_field not in self.fields:
            self.fields[solr_id_field] = []
        if (do_fq_only is False and
            len(concat_val) > 0 and
            concat_val not in self.fields[solr_id_field]):
            # Only add it if we don't already have it
            self.fields[solr_id_field].append(concat_val)
        # Add the solr id field's _fq field if not present.
        solr_id_field_fq = solr_id_field + '_fq'
        if solr_id_field_fq not in self.fields:
            self.fields[solr_id_field_fq] = []
        # Skip th rest of the funciton if slug is not a
        # non-zero length string.
        if not isinstance(slug, str) or len(slug) == 0:
            return None
        # Add the field prefix if needed
        # slug = self.solr_doc_prefix + slug
        if slug not in self.fields[solr_id_field_fq]:
            # only add it if we don't already have it
            self.fields[solr_id_field_fq].append(slug)
    
    def _set_solr_project_fields(self):
        """
        Creates a hierarchy of projects in the same way as a hierarchy of predicates
        """
        solr_field_name = self.ROOT_PROJECT_SOLR
        proj_rel = ProjectRels()
        proj_hierarchy = proj_rel.get_jsonldish_parents(
            self.oc_item.manifest.project_uuid
        )
        for proj in proj_hierarchy:
            # Compose the solr_value for this item in the context
            # hiearchy.
            self.fields['text'] += ' ' + str(proj['label']) + '\n'
            act_solr_value = self._concat_solr_string_value(
                proj['slug'],
                'id',
                get_id(proj),
                proj['label']
            )
            # The self.ALL_PROJECT_SOLR takes values for
            # each project item in project hiearchy, thereby
            # facilitating queries at all levels of the project
            # hierarchy. Without the self.ALL_PROJECT_SOLR, we would need
            # to know the full hiearchy path of project items in order
            # to query for a given project.
            self._add_id_field_fq_field_values(
                self.ALL_PROJECT_SOLR,
                act_solr_value,
                proj['slug'],
                do_fq_only=True
            )
            # Now add the current proj. to the solr field for the current
            # level of the project hiearchy.
            self._add_id_field_fq_field_values(
                solr_field_name,
                act_solr_value,
                proj['slug']
            )
            # Make the new solr_field_name for the next iteration of the loop.
            solr_field_name = (
                self._convert_slug_to_solr(proj['slug']) +
                '___project_id'
            )

    def _get_oc_item_uuid(self, uri, match_type='subjects'):
        """Returns a uuid from an URI referencing an Open Context item,
           of a given type,or None if not the type is not matched.
        """
        uri_parsed = URImanagement.get_uuid_from_oc_uri(
            uri,
            return_type=True
        )
        if not isinstance(uri_parsed, dict):
            return None
        if uri_parsed['item_type'] == match_type:
            return uri_parsed['uuid']
        else:
            return None

    def _get_oc_item_type(self, uri):
        """Returns the Open Context item type from a URI, if an
           Open Context item, otherwise None.
        """
        uri_parsed = URImanagement.get_uuid_from_oc_uri(
            uri,
            return_type=True
        )
        if not isinstance(uri_parsed, dict):
            return None
        return uri_parsed['item_type']

    def _get_context_path_items(self):
        """Gets the context path items from the oc_item.json_ld."""
        for context_key in self.CONTEXT_PREDICATES:
            if not context_key in self.oc_item.json_ld:
                continue
            context = self.oc_item.json_ld[context_key]
            if ItemKeys.PREDICATES_OCGEN_HASPATHITEMS in context:
                return context[ItemKeys.PREDICATES_OCGEN_HASPATHITEMS]
        return None
    
    def _add_solr_spatial_context(self):
        """Adds spatial context fields to the solr document."""
        context_items = self._get_context_path_items()
        if not context_items:
            # This item has no spatial context.
            return None
        # Iterate through the spatial context items.
        for index, context in enumerate(context_items):
            context_uuid = self._get_oc_item_uuid(
                get_id(context),
                match_type='subjects'
            )
            if not context_uuid:
                # Something went wrong, but we're forgiving,
                # so skip.
                continue
            # Compose the solr_value for this item in the context
            # hiearchy.
            act_solr_value = self._concat_solr_string_value(
                context['slug'],
                'id',
                ('/subjects/' + context_uuid),
                context['label']
            )
            # The self.ALL_CONTEXT_SOLR takes values for
            # each context item in spatial context hiearchy, thereby
            # facilitating queries at all levels of the context
            # hierarchy. Without the self.ALL_CONTEXT_SOLR, we would need
            # to know the full hiearchy path of parent items in order
            # to query for a given spatial context.
            self._add_id_field_fq_field_values(
                self.ALL_CONTEXT_SOLR,
                act_solr_value,
                context['slug'],
                do_fq_only=True
            )
            if index == 0:
                # We are at the top of the spatial hiearchy
                # so the solr context field is self.ROOT_CONTEXT_SOLR.
                solr_context_field = self.ROOT_CONTEXT_SOLR
            else:
                # We are at sub-levels in the spatial hiearchy
                # so the solr context field comes from the parent item
                # in the spatial context hierarchy
                solr_context_field = (
                    context_items[index - 1]['slug'] +
                    self.SOLR_VALUE_DELIM + 'context_id'
                )
            self._add_id_field_fq_field_values(
                solr_context_field,
                act_solr_value,
                context['slug']
            )

    def _get_solr_predicate_type_string(self, predicate_type, prefix=''):
        '''
        Defines whether our dynamic solr fields names for
        predicates end with ___pred_id, ___pred_numeric, etc.
        '''
        if predicate_type in ['@id', 'id', 'types', False]:
            return prefix + 'id'
        elif predicate_type in ['xsd:integer', 'xsd:double', 'xsd:boolean']:
            return prefix + 'numeric'
        elif predicate_type == 'xsd:string':
            return prefix + 'string'
        elif predicate_type == 'xsd:date':
            return prefix + 'date'
        elif predicate_type in self.MISSING_PREDICATE_TYPES:
            return prefix + 'string'
        else:
            raise Exception(
                "Unknown predicate type: {}".format(predicate_type)
            )

    def _get_predicate_type_from_dict(self, predicate_dict):
        """Gets data type from a predicate dictionary object. """
        for key in ['type', '@type']:
            if not key in predicate_dict:
                continue
            return predicate_dict[key]
        # Default to a string.
        return 'xsd:string'

    def _get_solr_predicate_type_from_dict(self, predicate_dict, prefix=''):
        """Gets the solr predicate type from a dictionary object. """
        return self._get_solr_predicate_type_string(
            self._get_predicate_type_from_dict(predicate_dict),
            prefix=prefix
        ) 

    def _add_object_value_hiearchy(self, root_solr_field, hiearchy_items):
        """Adds a hiearchy of predicates to the solr doc."""
        # The act_solr_field starts at the solr field that is
        # for the root of the hierarchy, passed as an argument to
        # this function.
        solr_field_prefix = self._convert_slug_to_solr(
            self.solr_doc_prefix
        )
        act_solr_field = solr_field_prefix + root_solr_field
        # The all_obj_solr_field is defined for the solr field
        # at the root of this hiearchy. It will take values for
        # each item in the object value hiearchy, thereby
        # facilitating queries at all levels of the object value
        # hierarchy. Without the all_obj_solr_field, we would need
        # to know the full hiearchy path of parent items in order
        # to query for a given object value.
        all_obj_solr_field = (
            solr_field_prefix +
            'obj_all' +
            self.SOLR_VALUE_DELIM +
            root_solr_field
        )
        
        # Now iterate through the list of hiearchy items of
        # object values.
        for index, item in enumerate(hiearchy_items):
            # Add the label of this item in the hiearchy
            # to the text field. This means key-word searches will
            # be inclusive of all parent items in a hiearchy.
            self.fields['text'] += ' ' + str(item['label']) + ' '
            # Compose the solr value for the current parent item.
            act_solr_value = self._concat_solr_string_value(
                item['slug'],
                self._get_solr_predicate_type_from_dict(item),
                get_id(item),
                item['label']
            )
            # Add to the solr document the object value to the
            # solr field for this level of the hiearchy.
            self._add_id_field_fq_field_values(
                act_solr_field,
                act_solr_value,
                item['slug']
            )
            # Add to the solr document the object value to the
            # all_obj_solr_field , to facilitate queries at ALL
            # levels of the object value hiearchy.
            self._add_id_field_fq_field_values(
                all_obj_solr_field,
                act_solr_value,
                item['slug'],
                do_fq_only=True
            )
            # Make the next act_solr_field for the next
            # iteration through the loop.
            act_solr_field = self._convert_slug_to_solr(
                item['slug']
            ) + self.SOLR_VALUE_DELIM + root_solr_field

    def _add_category(self):
        """Adds category / type data ('class_uri' in the manifest table)
        to the solr document.
        """
        if not 'category' in self.oc_item.json_ld:
            # No category, skip the rest.
            return None
        for category in self.oc_item.json_ld['category']:
            # get the parent entities of the current category
            raw_hiearchy_items = general_get_jsonldish_entity_parents(
                category
            )
            solr_field_name = None
            hiearchy_items = []
            for item in raw_hiearchy_items:
                # We only add the category hierarchy to the solr
                # document once we the poss_item_type has been
                # matched with the the current item's item type.
                # This means that we're NOT indexing the hiearchy
                # above the oc_item.manifest.item_type
                if ((settings.CANONICAL_HOST + '/vocabularies/oc-general/') in
                    item['id']):
                   poss_item_type = item['id'].split('/vocabularies/oc-general/')[-1]
                if (not solr_field_name and
                   poss_item_type == self.oc_item.manifest.item_type):
                    solr_field_name = self._convert_slug_to_solr(
                        item['slug'] +
                        self.SOLR_VALUE_DELIM + 'pred_id'
                    )
                    continue
                if not solr_field_name:
                    continue
                hiearchy_items.append(item)
            # Now add the hiearchy of categories (class_uri) that is under the
            # oc_item.manifest.item_type.
            if solr_field_name:
                self._add_object_value_hiearchy(
                    solr_field_name,
                    hiearchy_items
                )
    
    def _add_joined_subject_uuid(self, val_obj_id):
        """Adds subject uuids to facilitate joins."""
        if not self.oc_item.manifest.item_type in ['media','documents']:
            # This Open Context item type does not record joins.
            return None
        val_obj_subject_uuid = self._get_oc_item_uuid(
            val_obj_id,
            match_type='subjects'
        )
        if not val_obj_subject_uuid:
            # Not a subject, no uuid to join.
            return None
        # We need to facilitate joins to a related
        # Open Context subject item (join by UUID).
        if not self.join_solr_field in self.fields:
            # We don't have a solr field for joins yet, so
            # make one.
            self.fields[self.join_solr_field] = []
        # Append to the solr field for joins
        self.fields[self.join_solr_field].append(val_obj_subject_uuid)

    def _add_solr_fields_for_linked_media_documents(self, val_obj):
        """Adds standard solr fields relating to media and document links."""
        val_obj_oc_type = self._get_oc_item_type(get_id(val_obj))
        if val_obj_oc_type == 'media':
            if 'image' in val_obj['type']:
                self.fields['image_media_count'] += 1
            else:
                self.fields['other_binary_media_count'] += 1
        elif val_obj_oc_type == 'documents':
            self.fields['document_count'] += 1
        if (not 'thumbnail_uri' in self.fields and
            'oc-gen:thumbnail-uri' in val_obj):
            # We store the first thumbnail in the solr document.
            self.fields['thumbnail_uri'] = val_obj['oc-gen:thumbnail-uri']
        if (not 'iiif_json_uri' in self.fields  and
            'oc-gen:iiif-json-uri' in val_obj):
            # We store the first IIIF uri in the solr document.
            self.fields['iiif_json_uri'] = val_obj['oc-gen:iiif-json-uri']

    def _add_solr_id_field_values(self, solr_field_name, pred_value_objects):
        """Adds non-literal predicate value objects,
           and their hiearchy parents, to the Solr doc
        """
        for val_obj in pred_value_objects:
            # Add subject uuid joins, if applicable.
            self._add_joined_subject_uuid(get_id(val_obj))
            # Add standard solr fields that summarize linked media,
            # documents.
            self._add_solr_fields_for_linked_media_documents(val_obj)
            # Now add the val_obj item (and parents) to the
            # solr document.
            hiearchy_items = general_get_jsonldish_entity_parents(
                get_id(val_obj)
            )
            self._add_object_value_hiearchy(solr_field_name, hiearchy_items)
            # A little stying for different value objects in the text field.
            self.fields['text'] += '\n'

    def _add_solr_field_values(
            self,
            solr_field_name,
            solr_pred_type,
            pred_value_objects
        ):
        """Adds predicate value objects, and their hiearchy parents, to the Solr doc."""
        if not isinstance(pred_value_objects, list):
            return None
        if solr_pred_type == 'string':
            # Add string literal values ot the solr_field_name in the
            # solr document. Adds multiple language versions for
            # indexing if multiple langugage versions exist.
            lang_obj = Languages()
            for val_obj in pred_value_objects:
                if isinstance(val_obj, dict) and 'xsd:string' in val_obj:
                    # Add all multi-lingual versions of the text to the text field.
                    act_str = lang_obj.get_all_value_str(val_obj['xsd:string'])
                    self.fields['text'] += str(act_str) + ' \n'
                    act_str = force_text(
                        str(act_str),
                        encoding='utf-8',
                        strings_only=False,
                        errors='surrogateescape'
                    )
                    self.fields[solr_field_name].append(act_str)
                else:
                    self.fields['text'] += str(val_obj) + ' \n'
                    act_str = force_text(
                        str(val_obj),
                        encoding='utf-8',
                        strings_only=False,
                        errors='surrogateescape'
                    )
                    self.fields[solr_field_name].append(str(act_str))
        elif solr_pred_type == 'numeric':
            # Add numeric literal values ot the solr_field_name in the
            # solr document.
            for val_obj in pred_value_objects:
                self.fields['text'] += str(val_obj) + ' \n'
                self.fields[solr_field_name].append(val_obj)
        elif solr_pred_type == 'date':
            # Add date literal values ot the solr_field_name in the
            # solr document.
            for val_obj in pred_value_objects:
                self.fields['text'] += str(val_obj) + ' \n'
                self.fields[solr_field_name].append((val_obj + 'T00:00:00Z'))
        elif solr_pred_type == 'id':
            # This is the most complicated case where the value
            # objects will be non-literals (entities with outside URIs or URI
            # identified Open Context entities). So we need to add them, and
            # any of their hiearchy parents, to the solr document.
            self._add_solr_id_field_values(
                solr_field_name,
                pred_value_objects
            )
        else:
            return None

    def _add_predicate_hiearchy(self, hiearchy_items, root_solr_field):
        """Adds a hiearchy of predicates to the solr doc."""
        last_item_index = len(hiearchy_items) - 1
        for index, item in enumerate(hiearchy_items):
            if item['slug'] == 'link':
                # Skip the standard link, we don't do
                # special processing for standard links.
                continue
            if index < last_item_index:
                # Add the label of the hiearchy item
                # to the text field, to faciliate key-word searches.
                self.fields['text'] += ' ' + str(item['label']) + ' '
            
            # Compose the solr value for the current parent item.
            act_solr_value = self._concat_solr_string_value(
                item['slug'],
                self._get_solr_predicate_type_from_dict(item),
                get_id(item),
                item['label']
            )
            
            # Treat the first parent in a special way
            if index == 0:
                # We're at the highest level of the hiearchy,
                # so solr field name is the root solr field name.
                solr_field_name = root_solr_field
            else:
                # We're at a higher level of the hiearchy, so the
                # solr field name comes from the previous (parent)
                # item in the hiearchy.
                solr_field_name = self._convert_slug_to_solr(
                     hiearchy_items[index - 1]['slug'] +
                     self.SOLR_VALUE_DELIM + 'pred_id'
                )
            # Now add the predicate hiearchy item to the
            # appropriate solr doc fields.
            self._add_id_field_fq_field_values(
                solr_field_name,
                act_solr_value,
                item['slug']
            )

    def _add_predicate_and_object_description(
            self,
            pred_key,
            pred_value_objects
        ):
        """Adds descriptions from a given predicate and object to the Solr doc."""
        # Get needed metadata about the predicate by looking up
        # the pred_key and making a dictionary object of this metadata.
        predicate = self.proj_graph_obj.lookup_predicate(pred_key)
        if not predicate:
            # The predicate does not seem to exist. Skip out.
            return None
        if not 'uuid' in predicate or not predicate.get('slug'):
            print('Wierd predicate: {}'.format(str(predicate)))
            hiearchy_items = []
        else:
            # Get any hiearchy that may exist for the predicate. The
            # current predicate will be the LAST item in this hiearchy.
            hiearchy_items = general_get_jsonldish_entity_parents(
                predicate['uuid']
            )
        # This adds the parents of the predicate to the solr document,
        # starting at the self.ROOT_PREDICATE_SOLR
        self._add_predicate_hiearchy(
            hiearchy_items,
            self.ROOT_PREDICATE_SOLR
        )
        # Set up the solr field name for the predicate.
        solr_field_name = self._convert_slug_to_solr(
            predicate['slug'] +
            self._get_solr_predicate_type_from_dict(
                predicate, prefix=(self.SOLR_VALUE_DELIM + 'pred_')
            )
        )
        # Make sure the solr_field_name is in the solr document's
        # dictionary of fields.
        if solr_field_name not in self.fields:
            self.fields[solr_field_name] = []
        # Add the predicate label to the text string to help
        # make full-text search snippets more meaningful.
        self.fields['text'] += predicate['label'] + ': '
        # Add the predicate's value objects, including hiearchy parents
        # of those value objects, to the solr document.
        self._add_solr_field_values(
            solr_field_name,
            self._get_solr_predicate_type_from_dict(
                predicate, prefix=''
            ),
            pred_value_objects
        )

    def _add_link_object_values(self, pred_value_objects):
        """Adds object values for linked ('oc-pred:link') resources."""
        if self.do_related:
            # We are creating a solr-doc related to media. So
            # skip this step.
            return None
        if not isinstance(pred_value_objects, list):
            return None
        self.fields['text'] += 'Links: '
        for val_obj in pred_value_objects:
            self.fields['text'] += str(val_obj['label']) + ' '
            # Add subject uuid joins, if applicable.
            self._add_joined_subject_uuid(get_id(val_obj))
            # Do updates, specific to the Open Context item_type,
            # to the solr document.
            self._add_solr_fields_for_linked_media_documents(val_obj)
        self.fields['text'] += '\n'
      
    def _add_observations_descriptions(self):
        """Adds descriptions from item observations to the Solr doc."""
        if not ItemKeys.PREDICATES_OCGEN_HASOBS in self.oc_item.json_ld:
            return None
        # Get the list of all the observations made on this item.
        # Each observation is a dictionary with descriptive assertions
        # keyed by a predicate.
        obs_list = self.oc_item.json_ld[ItemKeys.PREDICATES_OCGEN_HASOBS]
        for obs in obs_list:
             # Get the status of the observation, defaulting to 'active'.
             # We are OK to index observation assertions if the observation is
             # active, otherwise we should skip it to so that the inactive
             # observations do not get indexed.
            obs_status = obs.get(ItemKeys.PREDICATES_OCGEN_OBSTATUS, 'active')
            if obs_status != 'active':
                # Skip this observation. It's there but has a deprecated
                # status.
                continue
            for pred_key, pred_value_objects in obs.items():
                if pred_key in projGraph.LINKDATA_OBS_PREDS_SKIP:
                    # Skip, since these are metadata about the observation itself,
                    # and not something we currently index for Solr searches.
                    continue
                if pred_key == 'oc-pred:link':
                    # This 'oc-pred:link' requires special processing.
                    self._add_link_object_values(pred_value_objects)
                    # Now skip the rest below.
                    continue
                # Add the predicate and the object values for this
                # predicate to the Solr document.
                self._add_predicate_and_object_description(
                    pred_key,
                    pred_value_objects
                )

    def _add_object_uri(self, object_uri):
        """ Processes object URIs for inferred linked object entities"""
        # NOTE: It is useful to have a simple field that records all
        # the linked data objects related to a subject (the document
        # indexed by solr).
        if not object_uri or not object_uri.startswith('http'):
            # We don't have an object_uri to add.
            return None
        if 'object_uri' not in self.fields:
            self.fields['object_uri'] = []
        if object_uri not in self.fields['object_uri']:
            self.fields['object_uri'].append(object_uri)

    def _add_infered_descriptions(self):
        """Adds inferred linked data descriptions to the Solr doc."""
        inferred_assertions = self.proj_graph_obj\
                                  .infer_assertions_for_item_json_ld(
                                      self.oc_item.json_ld
                                    )
        if not inferred_assertions:
            # No inferred assertions from liked data, so skip out.
            return None
        for assertion in inferred_assertions:
            # Get any hiearchy that may exist for the predicate. The
            # current predicate will be the LAST item in this hiearchy.
            pred_hiearchy_items = general_get_jsonldish_entity_parents(
                get_id(assertion)
            )
            # This adds the parents of the link data predicate to the solr document,
            # starting at the self.ROOT_LINK_DATA_SOLR
            self._add_predicate_hiearchy(
                pred_hiearchy_items,
                self.ROOT_LINK_DATA_SOLR
            )
            
            # Set up the solr field name for the link data predicate.
            solr_field_name = self._convert_slug_to_solr(
                assertion['slug'] +
                self._get_solr_predicate_type_from_dict(
                    assertion, prefix=(self.SOLR_VALUE_DELIM + 'pred_')
                )
            )
            # Make sure the solr_field_name is in the solr document's
            # dictionary of fields.
            if solr_field_name not in self.fields:
                self.fields[solr_field_name] = []
            
            # Add linked data 
            for _, obj in assertion['ld_objects'].items():
                self._add_object_uri(obj.get('id'))
            
            # Add the dicts of linked data entity objects
            # together with the list of object literal values to make
            # a consoloidated linked data object list.
            ld_object_list = [obj for _, obj in assertion['ld_objects'].items()]
            ld_object_list += [obj for _, obj in assertion['oc_objects'].items()]
            ld_object_list += assertion['literals']
            
            # Add the predicate label to the text string to help
            # make full-text search snippets more meaningful.
            self.fields['text'] += assertion['label'] + ': '
            # Add the predicate's value objects, including hiearchy parents
            # of those value objects, to the solr document.
            self._add_solr_field_values(
                solr_field_name,
                self._get_solr_predicate_type_from_dict(
                    assertion, prefix=''
                ),
                ld_object_list
            )
    
    def _add_equivalent_linked_data(self):
        """ This associates the item getting indexed with an equivalent
        linked data entity and its hierarchy.
        """
        for equiv_uri in self.LD_EQUIVALENT_PREDICATES:
            if equiv_uri not in self.oc_item.json_ld:
                continue
            # We will just "force-fit" all equivalent predicates
            # to be a skos:closeMatch.
            for obj in self.oc_item.json_ld[equiv_uri]:
                # Add linked data object.
                self._add_object_uri(obj.get('id'))
                hiearchy_items = general_get_jsonldish_entity_parents(
                    get_id(obj)
                )
                self._add_object_value_hiearchy(
                    self.EQUIV_LD_SOLR,
                    hiearchy_items
                )
                # A little stying for different value objects in the text field.
                self.fields['text'] += '\n'
    
    def _add_direct_linked_data(self):
        """ Adds linked data directly asserted to an item.
        """
        # Get a list of all the equivalent identifiers (full URIs or
        # namespaced equivalents) of predicates that are directly
        # asserted about different items.
        le = LinkEquivalence()
        direct_preds = le.get_identifier_list_variants(
            self.LD_DIRECT_PREDICATES
        )
        for pred_uri in direct_preds:
            if pred_uri not in self.oc_item.json_ld:
                continue
            # Get any hiearchy that may exist for the predicate. The
            # current predicate will be the LAST item in this hiearchy.
            pred_hiearchy_items = general_get_jsonldish_entity_parents(
                pred_uri
            )
            # This adds the parents of the link data predicate to the solr document,
            # starting at the self.ROOT_LINK_DATA_SOLR
            self._add_predicate_hiearchy(
                pred_hiearchy_items,
                self.ROOT_LINK_DATA_SOLR
            )
            
            # Set up the solr field name for the link data predicate.
            solr_field_name = self._convert_slug_to_solr(
                pred_hiearchy_items[-1]['slug'] +
                self.SOLR_VALUE_DELIM +
                'pred_id'
            )
            
            for obj in self.oc_item.json_ld[pred_uri]:
                # Add linked data object.
                self._add_object_uri(obj.get('id'))
                
                # Get the hierarchy for the objects of this equivalence
                # relationship.
                hiearchy_items = general_get_jsonldish_entity_parents(
                    get_id(obj)
                )
                self._add_object_value_hiearchy(
                    solr_field_name,
                    hiearchy_items
                )
                # A little stying for different value objects in the text field.
                self.fields['text'] += '\n'
           
    def _process_dc_metadata_objects(
        self,
        dc_predicate,
        solr_field_name,
        add_object_uris=False
        ):
        """Processes Dublin Core metadata objects with special handeling."""
        if not dc_predicate in self.oc_item.json_ld:
            # Skip out, this predicate does not exist.
            return None
        index_metas = []
        for meta in self.oc_item.json_ld[dc_predicate]:
            if (not get_id(meta).startswith('http') and
                meta.get('rdfs:isDefinedBy')):
                meta['id'] = meta['rdfs:isDefinedBy']
            if dc_predicate == 'foaf:depection':
                if ('type' in meta and meta['type'] == 'oc-gen:hero' and
                    'thumbnail_uri' not in self.fields):
                    # We only do this once, get the first hero to store as a thumbail in solr
                    self.fields['thumbnail_uri'] = meta['id']
                if ('oc-gen:iiif-json-uri' in meta and
                    'iiif_json_uri' not in self.fields):
                    # We only do this once, get the first iiif-json in solr
                    self.fields['iiif_json_uri'] = meta['oc-gen:iiif-json-uri']
                continue
            if (self.oc_item.manifest.item_type != 'projects' and
                'opencontext.org/tables/' in meta['id']):
                # Skip indexing of related tables.
                continue
            if self.oc_item.manifest.item_type == 'projects' or add_object_uris:
                # We need to add the object_uri for easy indexing.
                self._add_object_uri(get_id(meta))
            # Add to the list of items to actually index
            index_metas.append(meta)
        if not index_metas:
            # Skip the rest, nothing to add.
            return None
        if not solr_field_name in self.fields:
            self.fields[solr_field_name] = []
        # Now add the index_metas to the index.
        self._add_solr_id_field_values(solr_field_name, index_metas)

    def _add_dublin_core(self):
        """Adds Dublin Core metadata"""
        for dc_predicate, solr_field_name in DCterms.DC_META_PREDICATES.items():
            self._process_dc_metadata_objects(
                dc_predicate,
                solr_field_name
            )

    def _add_dublin_core_authors(self):
        """Adds Dublin Core authorship metadata"""
        for dc_predicate, solr_field_name in DCterms.DC_AUTHOR_PREDICATES.items():
            self._process_dc_metadata_objects(
                dc_predicate,
                solr_field_name,
                add_object_uris=True
            )
    
    def _validate_add_geo_point(
            self,
            latitude,
            longitude,
            location_precision
        ):
        """Validates and adds geo point to solr if valid."""
        gm = GlobalMercator()
        lat_ok = gm.validate_geo_coordinate(latitude, 'lat')
        lon_ok = gm.validate_geo_coordinate(longitude, 'lon')
        if not lat_ok or not lon_ok:
            raise ValueError('Coordinate problem: lat {}, lon {}'.format(
                    latitude,
                    longitude
                )
            )
        # The coordinates appear valid, add to the solr doc
        coords_str = '{},{}'.format(latitude, longitude)
        self.fields['discovery_geolocation'] = coords_str
        if not isinstance(location_precision, int):
            raise ValueError(
                'Location precision {} must be an integer.'.format(
                        location_precision
                    )
            )
        if location_precision < self.MIN_GEOTILE_ZOOM:
            location_precision = self.MIN_GEOTILE_ZOOM
        if location_precision > self.MAX_GEOTILE_ZOOM:
            location_precision = self.MAX_GEOTILE_ZOOM
        gm = GlobalMercator()
        tile = gm.lat_lon_to_quadtree(
            latitude,
            longitude,
            location_precision
        )
        if len(tile) <= (location_precision - 2):
            print('Problem with location precision {} and tile: {}'.format(
                    location_precision,
                    tile
                )
            )
            return False
        self.fields['discovery_geotile'] = tile
        return True

    def _add_predicates_types_geo(self):
        """Adds solr geo data for predicates and types"""
        if not self.oc_item.manifest.item_type in ['types', 'predicates']:
            # Skip out, this is for predicates and types.
            return None
        self.geo_specified = False
        gcq = GeoChronoQueries()
        geo_meta = gcq.get_project_geo_meta(
            self.oc_item.manifest.project_uuid
        )
        if not geo_meta:
            # Skip out, no spatial information found.
            return None
        geo = geo_meta[0]
        if not isinstance(geo.specificity, int):
            # Unset geo specificity, so assume it is max precision
            geo.specificity = self.MAX_GEOTILE_ZOOM
        location_precision = abs(geo.specificity)
        valid_geo = self._validate_add_geo_point(
            geo.latitude,
            geo.longitude,
            location_precision=location_precision
        )
        self.geo_specified = valid_geo
    
    def _add_geospatial(self):
        """Adds solr geo spatial data from the feature (GeoJSON) if present."""
        features = self.oc_item.json_ld.get('features')
        if not features:
            # The item does not have geospatial features, so add
            # geo data to the solr doc specific to predicates and types.
            self._add_predicates_types_geo()
            return None
        for feature in features:
            geometry_type = feature['geometry'].get('type')
            loc_type = feature['properties'].get('type')
            ref_type = feature['properties'].get('reference-type')
            contained_in_region = feature['properties'].get('contained-in-region')
            location_precision = feature['properties'].get(
                'location-precision',
                self.MAX_GEOTILE_ZOOM
            )
            if (ref_type == 'specified' and
                geometry_type != 'Point' and
                loc_type in ['oc-gen:discovey-location', 'oc-gen:geo-coverage'] and
                'slug_type_uri_label' in self.fields):
                # The discovery geosource is this item it self.
                self.geo_specified = True
                self.fields['disc_geosource'] = self.fields['slug_type_uri_label']
            elif (contained_in_region and
                  loc_type in ['oc-gen:discovey-location', 'oc-gen:geo-coverage']):
                # The discovery geosource is another (likely parent) item.
                self.geo_specified = False
                ref_label = feature['properties'].get('reference-label')
                ref_uri = feature['properties'].get('reference-uri')
                ref_slug = feature['properties'].get('reference-slug')
                if not ref_label or not ref_uri or not ref_slug:
                    # We're missing data needed for a disc_geosource
                    # value, so skip.
                    continue
                self.fields['disc_geosource'] = self._concat_solr_string_value(
                    ref_slug,
                    'id',
                    ref_uri,
                    ref_label
                )
            if 'discovery_geolocation' in self.fields:
                # Continue the loop, since we already have a disovery
                # location for this item, but still neet to loop
                # through features to populate geosource issues.
                continue
            if (geometry_type == 'Point' and
                loc_type in ['oc-gen:discovey-location', 'oc-gen:geo-coverage']):
                # Get point data to add geoloaction to solr.
                coords = feature['geometry'].get('coordinates')
                if not coords or len(coords) != 2:
                    raise ValueError('No or bad coordinates in feature point geometry.')
                valid_geo = self._validate_add_geo_point(
                    # Note the GeoJSON ordering of coordinates (lon/lat!)
                    latitude=coords[1],
                    longitude=coords[0],
                    location_precision=location_precision
                )
                self.geo_specified = valid_geo          

    def _validate_add_chrono(self, date_start, date_stop):
        """Validates and adds date ranges to Solr"""
        if date_start is None or date_stop is None:
            raise ValueError('Start: {}, stop: {} must be numbers.'.format(
                    date_start,
                    date_stop
                )
            )
        chrono_tile = ChronoTile()
        if 'form_use_life_chrono_tile' not in self.fields:
            self.fields['form_use_life_chrono_tile'] = []
        if 'form_use_life_chrono_earliest' not in self.fields:
                self.fields['form_use_life_chrono_earliest'] = []
        if 'form_use_life_chrono_latest' not in self.fields:
            self.fields['form_use_life_chrono_latest'] = []
        self.fields['form_use_life_chrono_tile'].append(
            chrono_tile.encode_path_from_bce_ce(
                date_start, date_stop, '10M-'
            )
        )
        self.fields['form_use_life_chrono_earliest'].append(
            date_start
        )
        self.fields['form_use_life_chrono_latest'].append(
            date_stop
        )

    def _add_predicates_types_chrono(self):
        """Adds chronological information for predicates or types items"""
        if not self.oc_item.manifest.item_type in ['types', 'predicates']:
            # Skip out, this is for predicates and types.
            return None 
        gcq = GeoChronoQueries()
        if self.oc_item.manifest.item_type  == 'types':
            # Get a date range dict, using a method for types
            date_range = gcq.get_type_date_range(
                self.oc_item.manifest.uuid,
                self.oc_item.manifest.project_uuid
            )
        else:
            # Get a date range dict, using the method for the project
            date_range = gcq.get_project_date_range(
                self.oc_item.manifest.project_uuid
            )
        if not date_range:
            # We don't have chronology information to index, so
            # skip
            return None
        # We have date range information we can index!!
        self.chrono_specified = True
        self._validate_add_chrono(
            date_range['start'],
            date_range['stop']
        )

    def _add_chronological(self):
        """Adds solr chronologica from the feature (GeoJSON) if present."""
        features = self.oc_item.json_ld.get('features')
        if not features:
            # The item does not have geospatial features, so add
            # geo data to the solr doc specific to predicates and types.
            self._add_predicates_types_chrono()
            return None
        for feature in features:
            when_dict = feature.get('when')
            if not when_dict:
                # This feature has no chronology, so continue
                continue
            # Start and stop times are in ISO 8601 time
            iso_start = when_dict.get('start')
            iso_stop = when_dict.get('stop')
            when_type = when_dict.get('type')
            ref_type = when_dict.get('reference-type')
            if (when_type == 'oc-gen:formation-use-life' and
                iso_start is not None and
                iso_stop is not None):
                if when_type == 'specified':
                    self.chrono_specified = True 
                date_start = ISOyears().make_float_from_iso(iso_start)
                date_stop = ISOyears().make_float_from_iso(iso_stop)
                self._validate_add_chrono(
                    date_start,
                    date_stop
                )
    
    def _add_persistent_ids(self):
        """Adds persistent IDs to the solr doc for indexing."""
        for id_pred in self.LD_IDENTIFIER_PREDICATES:
            if not id_pred in self.oc_item.json_ld:
                # This predicate is not in the json_ld, so
                # continue through the loop.
                continue
            for id_obj in self.oc_item.json_ld[id_pred]:
                if isinstance(id_obj, str):
                    id = id_obj
                else:
                    id = projGraph().get_id_from_g_obj(id_obj)
                if not id:
                    # No id found (something weird?)
                    continue
                # Check to see if this is an ID we should index
                # as a general linked data object of this item?
                if (id.startswith('https://') or
                    id.startswith('http://')):
                    # Even if it's not a persistent ID add it.
                    self._add_object_uri(id)
                # Now check to see if the id has the root of one of
                # the persistent ID URIs that we use.
                for act_root in self.PERSISTENT_ID_ROOTS:
                    if not id.startswith(act_root):
                        # The ID does not seem to have 
                        continue
                    if 'persistent_uri' not in self.fields:
                        self.fields['persistent_uri'] = []
                    self.fields['persistent_uri'].append(id)
                    self.fields['text'] += id + '\n'
    
    def _add_media_fields(self):
        """Adds media size and type fields to the solr document."""
        if (self.oc_item.manifest.item_type != 'media' or
           not 'oc-gen:has-files' in self.oc_item.json_ld):
            # Skip this, not a media type item, or missing
            # required data.
            return None
        if not self.FILE_SIZE_SOLR in self.fields:
            self.fields[self.FILE_SIZE_SOLR] = 0
        # Iterate through the file items.
        for file_item in self.oc_item.json_ld['oc-gen:has-files']:
            if not 'type' in file_item or not 'dc-terms:hasFormat' in file_item:
                # We're missing key data, so skip.
                continue
            if file_item['type'] == 'oc-gen:fullfile':
                self.fields[self.FILE_MIMETYPE_SOLR] = file_item['dc-terms:hasFormat']
            elif (file_item['type'] == 'oc-gen:thumbnail' and
                  not 'thumbnail_uri' in self.fields):
                self.fields['thumbnail_uri'] = file_item['id']
            elif (file_item['type'] == 'oc-gen:iiif' and
                  not 'iiif_json_uri' in self.fields):
                self.fields['iiif_json_uri'] = file_item['id']
            if not 'dcat:size' in file_item:
                continue
            size = float(file_item['dcat:size'])
            if size > self.fields[self.FILE_SIZE_SOLR]:
                self.fields[self.FILE_SIZE_SOLR] = size
    
    def _flag_human_remains(self):
        """Flags the solr document for human remains."""
        solr_doc_prefixes = [
            '',
            self.RELATED_SOLR_DOC_PREFIX
        ]
        for solr_doc_prefix in solr_doc_prefixes:
            field_prefix = self._convert_slug_to_solr(solr_doc_prefix)
            for solr_field_tmp, human_val in self.HUMAN_REMAINS_FIELD_VALUES:
                solr_field = (
                    solr_field_tmp.format(field_prefix)
                )
                if (not solr_field in self.fields or
                    human_val not in self.fields[solr_field]):
                    # We don't have this human remains criteria
                    # in our document's solr fields.
                    continue
                # We have matched some criteria indicating a record
                # about human remains.
                self.fields['human_remains'] += 1
    
    def _calculate_interest_score(self):
        """ Calculates the 'interest score' for sorting items with more
        documentation / description to a higher rank.
        """
        score = 0
        type_scores = {
            'subjects': 0,
            'media': 5,
            'documents': 5,
            'persons': 2,
            'types': 2,
            'predicates': 2,
            'projects': 100,
            'vocabularies': 25,
            'tables': 25
        }
        # Add a value for the item_type.
        score += type_scores.get(
            self.oc_item.manifest.item_type,
            0
        )
        rel_solr_field_prefix = self._convert_slug_to_solr(
            self.RELATED_SOLR_DOC_PREFIX
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
        score += self.fields['other_binary_media_count'] * 5
        score += self.fields['document_count'] * 4
        if self.geo_specified:
        # geo data specified, more interesting
            score += 5
        if self.chrono_specified:
        # chrono data specified, more interesting
            score += 5
        # Add to the score based on the file size of a media file.
        score += self.fields.get(self.FILE_SIZE_SOLR, 0 ) / 10000
        self.fields['interest_score'] = score
    
    def _add_linked_subjects(self):
        """Adds fields from related subject items to the solr document."""
        
        # NOTE: This essentially denormalizes media and document items.
        # Some of the important descriptive fields of the subjects
        # associated with a given media or document item get added
        # to the solr document. This allows the subject items to
        # provide metadata that further allow searching of media and
        # documents items (that tend not to have great metadata without
        # such associations)
        
        if not self.oc_item.manifest.item_type in ['media', 'documents']:
            # Not a media or documents item, so skip
            return None
        
        # This is the prefix for solr fields in related solr document
        # objects.
        rel_solr_field_prefix = self._convert_slug_to_solr(
            self.RELATED_SOLR_DOC_PREFIX
        )
        # Get list of related (joined) subject uuids from
        # self.join_solr_field
        rel_subject_uuids = []
        context_list = self._get_context_path_items()
        if context_list:
            subject_uuid = self._get_oc_item_uuid(
                get_id(context_list[-1]),
                match_type='subjects'
            )
            rel_subject_uuids.append(subject_uuid)
        
        # Now add the joined subject IDs (it they exist) that we have
        # already gethered into the self.join_solr_field.
        rel_subject_uuids += self.fields.get(self.join_solr_field, [])
        # Now add the related subjects solr fiels and their data to the
        # current item's solr document.
        for i, subject_uuid in enumerate(rel_subject_uuids):
            if subject_uuid is None:
                # Not a subject_uuid, so skip and continue.
                continue
            # Now create a related solr doc object for the subject_uuid.
            rel_sd_obj = SolrDocumentNew(subject_uuid)
            if (not rel_sd_obj.oc_item or
                rel_sd_obj.oc_item.manifest.item_type != 'subjects'):
                # Not a subject item, so skip and continue.
                continue
            # Make a limited subset of solr fields for the subject_uuid item.
            rel_sd_obj.make_related_solr_doc()
            # Add the related doc's text field to the current item's text field.
            self.fields['text'] += '/n' + rel_sd_obj.fields['text'] + '/n'
            # Iterate through the fields in in the related solr doc, and add
            # them and their values to the current media or documents solr doc.
            for field_key, vals in rel_sd_obj.fields.items():
                if not field_key.startswith(rel_solr_field_prefix):
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
    
    def make_solr_doc(self):
        """Make a solr document """
        if self.oc_item is None:
            return None
        # Set the required, universal fields for Solr
        self._set_required_solr_fields()
        # Add (multilingual) labels and titles to the text field
        self._add_labels_titles_to_text_field()
        # Add the project hiearchy to the solr document
        self._set_solr_project_fields()
        # Add the spatial context hiearchy to the solr document
        self._add_solr_spatial_context()
        # Add the item's category (class_uri) to the solr document
        self._add_category()
        # Add descriptions from the item observations
        self._add_observations_descriptions()
        # Add infered assertions via linked data equivalences to
        # descriptions in the item observations.
        self._add_infered_descriptions()
        # Add equivalences to other linked data
        self._add_equivalent_linked_data()
        # Add linked data made directly on an item
        self._add_direct_linked_data()
        # Add Dublin Core metadata
        self._add_dublin_core()
        # Add Dublin Core Authors
        self._add_dublin_core_authors()
        # Add general text content (esp for projects, documents)
        self._add_text_content()
        # Add geospatial information to the solr doc
        self._add_geospatial()
        # Add chronolgical information to the solr doc
        self._add_chronological()
        # Add persistent identifiers that may be associated to this item.
        self._add_persistent_ids()
        # Add media item specific solr fields.
        self._add_media_fields()
        # Add associated subject information to media and documents.
        self._add_linked_subjects()
        # Check if this solr document is about human remains
        self._flag_human_remains()
        # Make sure the text field is valid for Solr
        self.ensure_text_ok()
        # Calculate the interest score based on richness of description
        self._calculate_interest_score()
    
    def make_related_solr_doc(self):
        """Make a related solr document """
        self.do_related = True
        # Set field prefix to note that data comes from related
        # items, not the self.oc_item itself. 
        self.solr_doc_prefix = self.RELATED_SOLR_DOC_PREFIX
        if self.oc_item is None:
            return None
        # Add related item's category (class_uri) to the solr document
        self._add_category()
        # Add descriptions from the related item observations
        self._add_observations_descriptions()
        # Add infered assertions via linked data equivalences to
        # descriptions in the related item observations.
        self._add_infered_descriptions()
        # Add linked data made directly on the related item
        self._add_direct_linked_data()
        # Add Dublin Core metadata to the related item
        self._add_dublin_core()
        # Make sure the text field is valid for Solr
        self.ensure_text_ok()
        
    