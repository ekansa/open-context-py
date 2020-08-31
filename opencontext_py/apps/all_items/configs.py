
from django.conf import settings


# Maximum depth of all Open Context hierarchies
# This is insanely high, but sets a hard-limit against infinite recursion.
MAX_HIERARCHY_DEPTH = 100

# Open Context URI root
OC_URI_ROOT = 'opencontext.org'

# ---------------------------------------------------------------------
# CONFIGS FOR ALL MANIFEST ITEMS
# ---------------------------------------------------------------------

# Item types for the main types of data published by Open Context.
# These are the types of data records that Open Context publishes and
# indexes for search and querying.
OC_ITEM_TYPES = [
    'projects', 
    'tables',
    'subjects',
    'media',
    'documents',
    'predicates',
    'types',
    'persons',
    'tables',
]

# Item type with full URIs as the main identifer. These are for
# supplemental metadata / linked data annotation and description of
# the UUID_ITEM_TYPES above.
URI_CONTEXT_PREFIX_ITEM_TYPES = [
    'languages', # Called as a type to make string modeling easier.
    'class', # A classification type
    'property', # An attribute or linking relation.
    'units', # For a unit of measurement.
    'uri',  # Usually for an instance, but also a file.
    'media-types', # For describing a resource IANA media-type
]

URI_ITEM_TYPES = (
    ['publishers', 'vocabularies'] 
    + URI_CONTEXT_PREFIX_ITEM_TYPES
)

# Item types that are not resolvable on their own (they are nodes
# in some context of another item type). These are organizing
# different parts / nodes / components of UUID_ITEM_TYPES, but
# they are not meant to be "stand-alone" records, individually
# resolvable over the web via an URI.
NODE_ITEM_TYPES = [
    'observations',
    'events',
    'attribute-groups',
]


# All the valid item types for the Manifest model. Note that
# the ording is significant and use for sorting.
ITEM_TYPES = OC_ITEM_TYPES + URI_ITEM_TYPES + NODE_ITEM_TYPES

# The valid data types for Open Context manifest entities. The
# 'id' data_type means that it references an entity in the database.
# All the others are literals.
DATA_TYPES = [
    'id',
    'xsd:boolean',
    'xsd:date',
    'xsd:double',
    'xsd:integer',
    'xsd:string',
]


# Metadata dictionary keys allowed for different item types
MANIFEST_META_JSON_KEYS = {
    # Tuple is as follows:
    # (limit_to_item_type, key, value object type)
    (None, 'skos_alt_label', str,),

    ('vocabularies', 'vocab_file_uri', str,),

    # Projects related metadata keys.
    ('projects', 'short_id', int,),
    ('projects', 'edit_status', int,),
    ('projects', 'view_group_id', int,),
    ('projects', 'edit_group_id', int,),
    ('projects', 'geo_specificity', int,),
    ('projects', 'geo_note', str,),

    ('subjects', 'edit_status', int,),
    ('subjects', 'view_group_id', int,),
    ('subjects', 'edit_group_id', int,),
    ('subjects', 'geo_specificity', int,),
    ('subjects', 'geo_note', str,),

    ('media', 'edit_status', int,),
    ('media', 'view_group_id', int,),
    ('media', 'edit_group_id', int,),
    
    ('documents', 'edit_status', int,),
    ('documents', 'view_group_id', int,),
    ('documents', 'edit_group_id', int,),

    ('tables', 'edit_status', int,),
    ('tables', 'view_group_id', int,),
    ('tables', 'edit_group_id', int,),
    
    # Persons related metadata keys.
    ('persons', 'combined_name', str,),
    ('persons', 'surname', str,),
    ('persons', 'given_name', str,),
    ('persons', 'initials', str,),
    ('persons', 'mid_init', str,),

    # Languages
    ('languages', 'label_localized', str,),
    ('languages', 'script_code', str,),
    ('languages', 'iso_639_3_code', str,),

    # Units
    ('units', 'data_type', str,),
    ('units', 'symbol', str,),

    # Media-types
    ('media-types', 'template', str,),
}

# List of allowed identifer schemes.
IDENTIFIER_SCHEMES = [
    'doi',
    'ark',
    'orcid',
    'oc-old',
]


# ---------------------------------------------------------------------
# CONFIGS FOR DEFAULT PREDICATES USED IN ASSERTIONS
# ---------------------------------------------------------------------

# Standard predicate for project root children; 'oc-gen:contains-root'
PREDICATE_PROJ_ROOT_UUID = '763af21e-dac1-49c0-b121-a420c37eaa0e'

# Standard predicate for spatial containment; 'oc-gen:contains'
PREDICATE_CONTAINS_UUID = 'a07cae41-d615-4ba2-9d81-c60045921b2e'

# Predicate for secondary spatial containment, not used in entity
# reconciliation, just for additional navigation between subjects items.
PREDICATE_ALSO_CONTAINS_UUID = '996841cb-7a9b-406f-afb3-65b035ff4294'

# Standard predicate for a generic link; 'oc-gen:links', 'oc-3'
PREDICATE_LINK_UUID = '75427e34-475b-440d-abba-9f0e76100584'

# Standard predicate for a generic note; 'oc-gen:has-note'
PREDICATE_NOTE_UUID = '9dddbdcb-02a3-4703-9fb3-cbdb3ca62e15'

# Standard predicate for a link relation that's from the object
# use this to not make the subject too cluttered with visible links
# this is provisional, I may decide this is stupid beyond hope;
# 'oc-gen:is-linked-from'
PREDICATE_LINKED_FROM_UUID = '8321ce74-0d14-4580-9862-fa0d604cc435'

# Standard predicate for a link between an item and a geospatial bitmap image
# 'oc-gen:has-geo-overlay'
PREDICATE_GEO_OVERLAY_UUID = '8084cd3e-008f-4fee-af32-a58040a5a716'

# OC-General Predicate 'Has icon'
PREDICATE_OC_HAS_ICON_UUID = '00000000-6e24-f67a-9c19-09c9e320443c'
# OC-General Predicate 'Has technique'
PREDICATE_OC_HAS_TECHNIQUE_UUID = '00000000-6e24-7a66-2fff-65ea5fabd642'

# OC-General Resource Classes:
OC_RESOURCE_FULLFILE_UUID = '00000000-6e24-dbd6-3608-9961b99c331b'
OC_RESOURCE_PREVIEW_UUID = '00000000-6e24-ed5a-74cf-4512c48a3877'
OC_RESOURCE_THUMBNAIL_UUID = '00000000-6e24-7e15-b886-83053750960a'
OC_RESOURCE_ICON_UUID = '00000000-6e24-1633-88ea-7dd4f56e3861'
OC_RESOURCE_HERO_UUID = '00000000-6e24-78a8-5818-1f300e0b6593'
OC_RESOURCE_IIIF_UUID = '00000000-6e24-6c5b-fc2a-8f98d8e7da8d'
OC_RESOURCE_ARCHIVE_UUID = '00000000-6e24-5cfe-2037-94227c186a67'
OC_RESOURCE_IA_FULLFILE_UUID = '00000000-6e24-1123-1033-1143412da108'
OC_RESOURCE_X3DOM_MODEL_UUID = '00000000-6e24-2a64-e1cd-25ad672e1109'
OC_RESOURCE_X3DOM_TEXTURE_UUID = '00000000-6e24-7771-1a16-8138bb119c5d'
OC_RESOURCE_NEXUS_3D_UUID = '00000000-6e24-072a-690e-1c0ec00eb451'
OC_RESOURCE_SERVICE_API_UUID = '00000000-6e24-8b22-6ba6-ff76c2bb462c'

# Valid resource type for the Resource Model.
OC_RESOURCE_TYPES_UUIDS = [
    OC_RESOURCE_FULLFILE_UUID,
    OC_RESOURCE_PREVIEW_UUID,
    OC_RESOURCE_THUMBNAIL_UUID,
    OC_RESOURCE_ICON_UUID,
    OC_RESOURCE_HERO_UUID,
    OC_RESOURCE_IIIF_UUID,
    OC_RESOURCE_ARCHIVE_UUID,
    OC_RESOURCE_IA_FULLFILE_UUID,
    OC_RESOURCE_X3DOM_MODEL_UUID,
    OC_RESOURCE_X3DOM_TEXTURE_UUID,
    OC_RESOURCE_NEXUS_3D_UUID,
    OC_RESOURCE_SERVICE_API_UUID,
]

# OC-General default event type. This is essentially a vague
# defined location of discovery/deposition, combined with
# a vaguely specified time span for then something was 
# formed, used, or was alive. More specific even types can be
# modeled, but this default is necessarily unspecific and vague.
OC_EVENT_TYPE_GENERAL_UUID = '00000000-6e24-336d-3531-54f40f2dcce0'
OC_EVENT_TYPE_CURRENT_UUID = '00000000-6e24-eb5e-0cca-1ac8dc56c571'
OC_EVENT_TYPE_ORIGINS_UUID = '00000000-6e24-d923-4de9-195609a19040'
OC_EVENT_TYPE_UUIDS = [
    OC_EVENT_TYPE_GENERAL_UUID,
    OC_EVENT_TYPE_CURRENT_UUID,
    OC_EVENT_TYPE_ORIGINS_UUID,
]

# Media-types related publisher, vocabularies, and types
# See: https://www.iana.org/assignments/media-types/
IANA_PUB_UUID = 'd6533f97-aa69-4a85-9c60-bba6a285b2a0'
IANA_MEDIA_TYPE_VOCAB_UUID = '00000000-0ac6-2293-4914-37a37c86f907'

# For the http://vcg.isti.cnr.it/, publisher of the Nexus 3D
# format and libraries
VCG_ISTI_PUB_UUID = 'd9d4b935-06d5-4882-9df3-1bbf75eca9c9'
NEXUS_VCG_VOCAB_UUID = '00000000-1966-0da4-e469-b983bf4b2e74'
MEDIA_NEXUS_3D_NXS_UUID = '00000000-1966-5a64-bd91-c1c84653f19d'
MEDIA_NEXUS_3D_NXZ_UUID = '00000000-1966-d12c-bb2b-05187476019f'


# Just configure the most common media types.
MEDIA_TYPE_CSV_UUID = '00000000-0ac6-a124-3414-8f240c194694'
MEDIA_TYPE_GEO_JSON_UUID = '00000000-0ac6-85d1-eaf2-84b7b625a21f'
MEDIA_TYPE_GIF_UUID = '00000000-0ac6-1ec2-99e3-790cf759d996'
MEDIA_TYPE_JPEG_UUID = '00000000-0ac6-b382-9dd2-f735a38ee3cd'
MEDIA_TYPE_JSON_LD_UUID = '00000000-0ac6-32a2-9605-e49b9c940240'
MEDIA_TYPE_PDF_UUID = '00000000-0ac6-f50e-6b61-c1ab05b95baf'
MEDIA_TYPE_PNG_UUID = '00000000-0ac6-0c36-8f69-c656a6902c5d'
MEDIA_TYPE_TIFF_UUID = '00000000-0ac6-b4a4-7975-f118650d6fff'
MEDIA_TYPE_ZIP_UUID = '00000000-0ac6-2f70-6ab2-dfd44d6cbbc7'


# Widely used SKOS predicates.
PREDICATE_SKOS_EXACT_MATCH_UUID = '00000000-081a-dc93-af22-4cbcca550517'
PREDICATE_SKOS_CLOSE_MATCH_UUID = '00000000-081a-1d47-f617-1699079819cf'
PREDICATE_SKOS_NARROW_MATCH_UUID = '00000000-081a-d48c-4c11-d5b6b186a963'
PREDICATE_SKOS_NARROWER_UUID = '00000000-081a-dc82-b3e0-f36ff7879388'
PREDICATE_SKOS_NARROWER_TRANS_UUID = '00000000-081a-9c99-3914-95d016c9d9d9'
PREDICATE_SKOS_BROADER_UUID = '00000000-081a-0567-dee1-61a8d6e32653'
PREDICATE_SKOS_BROADER_TRANS_UUID = '00000000-081a-315d-f9b8-fcb10149a40d'
PREDICATE_SKOS_BROAD_MATCH_UUID = '00000000-081a-d304-2c93-1a4c0a441d36'
PREDICATE_SKOS_RELATED_UUID = '00000000-081a-3e96-e2a9-3dc15f1afea0'
PREDICATE_SKOS_EXAMPLE_UUID = '00000000-081a-9bb4-e16a-e0f13f82727d'
PREDICATE_SKOS_PREFLABEL_UUID = '00000000-081a-8518-32b5-a719498bd3e4'
PREDICATE_SKOS_ALTLABEL_UUID = '00000000-081a-0f24-0cc6-356c4a6e8723'
PREDICATE_SKOS_DEFINITION_UUID = '00000000-081a-42e7-3baa-ba482b98f4ce'
PREDICATE_SKOS_EDITORIAL_NOTE_UUID = '00000000-081a-fd90-538b-b992eedfa60b'
PREDICATE_SKOS_NOTE_UUID = '00000000-081a-6a8f-98bd-f88056a28922'


# Widely used OWL and RDF, RDFS predicates
PREDICATE_OWL_CLASS_UUID = '00000000-2470-6b19-5699-b23da39d870f'
PREDICATE_OWL_ANNOTATION_PROPERTY_UUID = '00000000-2470-84f0-a196-ae81a75d6b68'
PREDICATE_OWL_OBJECT_PROPERTY_UUID = '00000000-2470-591a-ea4a-72158490922c'
PREDICATE_OWL_SAME_AS_UUID = '00000000-2470-aa02-9342-e9d5b2ed3149'

PREDICATE_RDF_TYPE_UUID = '00000000-7c49-d091-5cb8-c99c6432d046'

PREDICATE_RDFS_SUB_CLASS_OF_UUID = '00000000-ec6e-e138-62b0-fdc61986c292'
PREDICATE_RDFS_SUB_PROP_OF_UUID = '00000000-ec6e-7c1e-1083-7166845dd7dd'
PREDICATE_RDFS_IS_DEFINED_BY_UUID = '00000000-ec6e-07f3-f8c4-4a3c85d73e58'
PREDICATE_RDFS_RANGE_UUID = '00000000-ec6e-9b7c-39f3-ccc14d9e4f8f'
PREDICATE_RDFS_DOMAIN_UUID = '00000000-ec6e-297c-21a2-7aa5d634e739'
PREDICATE_RDFS_COMMENT_UUID = '00000000-ec6e-b350-2d80-acfa0013768c'
PREDICATE_RDFS_SEE_ALSO_UUID = '00000000-ec6e-3c6d-b85d-18ec2801c513'

PREDICATE_VOID_DATADUMP_UUID = '00000000-0810-a9db-f11a-7f8304a114fb'





# ---------------------------------------------------------------------
# LINKED DATA CONFIGS
# ---------------------------------------------------------------------
LINKED_DATA_URI_PREFIX_TO_SLUGS = {
    'cidoc-crm.org/rdfs/cidoc-crm': 'crm-rdf',
    'erlangen-crm.org/current': 'cidoc-crm',
    'collection.britishmuseum.org/description/thesauri': 'bm-thes',
    'collection.britishmuseum.org/id/thesauri': 'bm-thes',
    'concordia.atlantides.org': 'concordia',
    'gawd.atlantides.org/terms': 'gawd',
    'purl.org/dc/terms': 'dc-terms',
    'dbpedia.org/resource': 'dbpedia',
    'wikidata.org/wiki': 'wikidata',
    'eol.org/pages': 'eol-p',
    'opencontext.org/vocabularies/dinaa': 'dinaa',
    'opencontext.org/vocabularies/oc-general': 'oc-gen',
    'opencontext.org/vocabularies/open-context-zooarch': 'oc-zoo',
    'orcid.org': 'orcid',
    'pleiades.stoa.org/places': 'pleiades-p',
    'pleiades.stoa.org/vocabularies/time-periods': 'pleiades-tp',
    'purl.obolibrary.org/obo': 'obo',
    'purl.org/NET/biol/ns': 'biol',
    'sw.opencyc.org': 'opencyc',
    'freebase.com/view/en': 'freebase',
    'en.wiktionary.org/wiki': 'wiktionary',
    'geonames.org': 'geonames',
    'w3.org/2000/01/rdf-schema': 'rdfs',
    'w3.org/2003/01/geo/wgs84_pos': 'geo',
    'w3.org/2004/02/skos/core': 'skos',
    'en.wikipedia.org/wiki': 'wiki',
    'id.loc.gov/authorities/subjects': 'loc-sh',
    'core.tdar.org/browse/site-name': 'tdar-kw-site',
    'purl.org/ontology/bibo': 'bibo',
    'creativecommons.org/ns#': 'cc',
    'w3.org/2002/07/owl#': 'owl',
    'creativecommons.org/licenses': 'cc-license',
    'creativecommons.org/publicdomain': 'cc-publicdomain',
    'n2t.net/ark:/99152/p0': 'periodo-p0',
    'vocab.getty.edu/aat': 'getty-aat',
    'nomisma.org/ontology': 'nmo',
    'numismatics.org/ocre/id': 'ocre',
    'portal.vertnet.org': 'vertnet-rec',
    'vocab.getty.edu/tgn': 'getty-tgn',
    'purl.org/heritagedata/schemes/mda_obj/concepts': 'fish',
    'arachne.dainst.org/search': 'arachne-search',
    'arachne.dainst.org/entity/': 'arachne-ent',
    'jstor.org/journal': 'jstor-jrn',
    'jstor.org/stable': 'jstor',
    'scholarworks.sfasu.edu/ita': 'i-texas-a',
    'doi.org': 'doi',
    'gbif.org/species': 'gbif',
    'foodon.org/': 'foodon',
    'purl.obolibrary.org/obo/FOODON_': 'obo-foodon',
}




# ---------------------------------------------------------------------
# CONFIGS FOR FIXTURES OF GENERALLY USED, DEFAULT MANIFEST ITEMS
# ---------------------------------------------------------------------
DEFAULT_SOURCE_ID = 'default-open-context'

# The "core" Open Context identifiers.
OPEN_CONTEXT_PROJ_UUID = '00000000-0000-0000-0000-000000000001'
OPEN_CONTEXT_PUB_UUID = 'aa88bc27-e082-44b5-b51b-73a3f268f939'
OC_GEN_VOCAB_UUID = '00000000-6e24-f5be-ce04-eb2bdd3792f2'
# Additional Open Context vocabularies
DINAA_VOCAB_UUID = '00000000-3e69-33aa-0d04-620ea47df19d'
OCZOO_VOCAB_UUID = '00000000-61ca-2d03-1a84-57bdee155cf5'

# Default for different types of 'nodes' that organize assertions
DEFAULT_CLASS_UUID = '00000000-0000-0000-0000-000000000002'
DEFAULT_OBS_UUID = '00000000-0000-0000-0000-000000000003'
DEFAULT_EVENT_UUID = '00000000-0000-0000-0000-000000000004'
DEFAULT_ATTRIBUTE_GROUP_UUID = '00000000-0000-0000-0000-000000000005'
DEFAULT_NULL_OBJECT_UUID = '00000000-0000-0000-0000-000000000006'
DEFAULT_NULL_STRING_UUID = '00000000-cdd8-bc9b-1985-c3babee8ea6c'

# The root subject item (the World)
DEFAULT_SUBJECTS_ROOT_UUID = 'fc8ff176-beb1-4aaa-896b-d5f49ede58c8'
DEFAULT_SUBJECTS_AFRICA_UUID = '2334627d-5db7-4ff8-b61c-49f51aaaf9f8'
DEFAULT_SUBJECTS_AMERICAS_UUID = '3b59e5d6-e136-407d-9cab-e460f4fbc184'
DEFAULT_SUBJECTS_ASIA_UUID = 'a6c5488c-98de-4e5a-9654-c1a2be698840'
DEFAULT_SUBJECTS_EUROPE_UUID = '6cfc6541-b741-44c4-b9d1-d8d9601c5548'
DEFAULT_SUBJECTS_OCEANIA_UUID = 'ac6ed144-5007-42bc-acee-a42197caa3da'

DEFAULT_PDF_ICON_UUID = '00000000-0000-0000-0000-100000000000'
DEFAULT_3D_ICON_UUID = '00000000-0000-0000-0000-100000000001'
DEFAULT_GIS_ICON_UUID = '00000000-0000-0000-0000-100000000002'
DEFAULT_RASTER_ICON_UUID = '00000000-0000-0000-0000-100000000003'

# --------------------------------------------------------------------
# 
# BELOW MORE Identifiers to core linked data vocabularies.
#
# --------------------------------------------------------------------

# ---------------------------------------------------------------------
# W3C publisher, publisher of web standards.
W3C_PUB_UUID = 'da09c10b-1638-4328-a775-af6671855c04'

# W3C vocabularies.
RDF_VOCAB_UUID = '00000000-7c49-ac9d-21e1-49bbdefe58a2'
RDFS_VOCAB_UUID = '00000000-ec6e-f22b-2e5a-ea6cc9f134c8'
XSD_VOCAB_UUID = '00000000-2783-188b-3bd7-130a8c6aec21'
SKOS_VOCAB_UUID = '00000000-081a-ea72-f98b-2a4f06c92856'
OWL_VOCAB_UUID = '00000000-2470-fcd4-84ce-68d4ca0e3cd5'
DCAT_VOCAB_UUID = '00000000-26f5-50ff-567a-d668b36c9704'
WEB_GEO_VOCAB_UUID = '00000000-31dc-dc7b-1a6c-dbee074608ba'
VOID_VOCAB_UUID = '00000000-0810-ec8a-75fd-32c5e5062520'
# ---------------------------------------------------------------------

# ---------------------------------------------------------------------
# Dublin Core Metadata Initiative, publisher of dublin core
DCMI_PUB_UUID = 'd28ed428-13a0-4b08-bb78-9bd89c6a77b1'

# DCMI vocabularites
DCTERMS_VOCAB_UUID = '00000000-ed50-af60-320b-57c0ffae17f0'
DCMI_VOCAB_UUID = '00000000-2d83-f3b5-efd0-1ca5bc41254e'

# DCTERMS Predicates -- Literal Values
PREDICATE_DCTERMS_ABSTRACT_UUID = '00000000-ed50-6fc8-2452-121ce56c5b69'
PREDICATE_DCTERMS_BIBLIO_CITE_UUID = '00000000-ed50-b910-a92c-c835d1e3259e'
PREDICATE_DCTERMS_CREATED_UUID = '00000000-ed50-4a27-2b8e-73737faa4251'
PREDICATE_DCTERMS_DATE_UUID = '00000000-ed50-462c-b40f-aff98365e764'
PREDICATE_DCTERMS_DESCRIPTION_UUID = '00000000-ed50-6ec3-85ce-edf9d92ffa15'
PREDICATE_DCTERMS_IDENTIFIER_UUID = '00000000-ed50-926e-2f58-d7c0b082bbf1'
PREDICATE_DCTERMS_ISSUED_UUID = '00000000-ed50-5bfe-bbf3-3f9bca5ae9be'
PREDICATE_DCTERMS_MODIFIED_UUID = '00000000-ed50-12a5-ef07-d501c10648eb'
PREDICATE_DCTERMS_PROVENANCE_UUID = '00000000-ed50-bdb1-d364-9223dceca6a5'
PREDICATE_DCTERMS_TITLE_UUID = '00000000-ed50-7943-c53e-3b9732d08b96'

# DCTERMS Predicates -- People
PREDICATE_DCTERMS_CONTRIBUTOR_UUID = '00000000-ed50-8ee5-c7a2-21a012593f25'
PREDICATE_DCTERMS_CREATOR_UUID = '00000000-ed50-3cf1-c266-683c89afdac4'

# DCTERMS Predicates -- URIs
PREDICATE_DCTERMS_COVERAGE_UUID = '00000000-ed50-381e-dac2-33364bc86adb'
PREDICATE_DCTERMS_FORMAT_UUID = '00000000-ed50-ac14-88a4-8926d9708f30'
PREDICATE_DCTERMS_HAS_FORMAT_UUID = '00000000-ed50-2144-20b7-65df351650c6'
PREDICATE_DCTERMS_HAS_PART_UUID = '00000000-ed50-cea8-c286-a93aacaa8fbe'
PREDICATE_DCTERMS_HAS_VERSION_UUID = '00000000-ed50-5262-82fe-72e1bc17afd9'
PREDICATE_DCTERMS_IS_PART_OF_UUID = '00000000-ed50-114e-bf8a-c76a6e1a2f2c'
PREDICATE_DCTERMS_IS_REFERENCED_BY_UUID = '00000000-ed50-d201-4202-eeff1dfffc9c'
PREDICATE_DCTERMS_IS_REPLACED_BY_UUID = '00000000-ed50-d8e6-b43a-29f1d3931cc1'
PREDICATE_DCTERMS_IS_VERSION_OF_UUID = '00000000-ed50-3edf-fd84-62bd9b706f52'
PREDICATE_DCTERMS_LANGUAGE_UUID = '00000000-ed50-32dc-679b-89daab7801be'
PREDICATE_DCTERMS_LICENSE_UUID = '00000000-ed50-8d06-7d04-87a1f1e084c4'
PREDICATE_DCTERMS_PUBLISHER_UUID = '00000000-ed50-9a66-9bb4-3805c41a9d44'
PREDICATE_DCTERMS_REFERENCES_UUID = '00000000-ed50-8c59-369e-f5e97260005a'
PREDICATE_DCTERMS_RELATION_UUID = '00000000-ed50-fc9e-a7b3-f3314689db63'
PREDICATE_DCTERMS_REPLACES_UUID = '00000000-ed50-ee5f-f083-c275beaa11cf'
PREDICATE_DCTERMS_SOURCE_UUID = '00000000-ed50-a947-e471-df79e64e5236'
PREDICATE_DCTERMS_SPATIAL_UUID = '00000000-ed50-e685-f3da-d9f7135a4f24'
PREDICATE_DCTERMS_SUBJECT_UUID = '00000000-ed50-5006-1991-3afe609b3089'
PREDICATE_DCTERMS_TEMPORAL_UUID = '00000000-ed50-4d17-4574-2f0d30c17ef8'
# ---------------------------------------------------------------------

# ---------------------------------------------------------------------
# Creative Commons
CC_PUB_UUID = '0175b7e1-b91e-455c-af65-ad4eaedb49ad'
# Creative Commons license vocabulary
CC_LICENSE_VOCAB_UUID = '00000000-25ef-fb4e-d901-9b9276b89b86'
CC_PUBLIC_DOMAIN_VOCAB_UUID = '00000000-c973-13ad-bf66-b41772ad85b0'
# CC Default License (cc-by)
CC_DEFAULT_LICENSE_CC_BY_UUID = '00000000-25ef-426d-ea02-1804e08f2e87'

# ---------------------------------------------------------------------

# ---------------------------------------------------------------------
# FOAF publisher and vocabulary
FOAF_PUB_UUID = '956c311f-28b3-4066-b64c-216f514283e9'
FOAF_VOCAB_UUID = '00000000-546a-21f2-78cd-efb0bfe17e7e'
CLASS_FOAF_AGENT_UUID = '00000000-546a-ae25-327a-95ddc172b07b'
CLASS_FOAF_GROUP_UUID = '00000000-546a-20f0-eda7-13f7bbf7b5fa'
CLASS_FOAF_PERSON_UUID = '00000000-546a-e6c7-7c0a-2909e60e7c81'
CLASS_FOAF_ORGANIZATION_UUID = '00000000-546a-df1c-0e55-4f27d6cbe824'
CLASS_FOAF_IMAGE_UUID = '00000000-546a-a07b-f674-1cc297404007'
PREDICATE_FOAF_IMG_UUID = '00000000-546a-1309-223b-9c6a196b2da5'
PREDICATE_FOAF_PRIMARY_TOPIC_OF_UUID = '00000000-546a-9655-f041-cc3f7f3257d3'
# ---------------------------------------------------------------------


# ---------------------------------------------------------------------
# DBpedia
DBPEDIA_PUB_UUID = 'ba21b1a1-cfeb-45e0-9e34-0bde43c764a7'
DBPEDIA_VOCAB_UUID = '00000000-3e39-16a5-d7dd-2278fbf57897'
# ---------------------------------------------------------------------

# ---------------------------------------------------------------------
# ORCID
ORCID_PUB_UUID = 'ac39a0a1-74ce-4f4f-8257-8bbe89abb9cc'
ORCID_VOCAB_UUID = '00000000-7b24-5ac2-6dc9-9be294ae9bba'
# ---------------------------------------------------------------------

# BIBO Bibliographic ontology
BIBO_PUB_UUID = 'fc7cda7c-da33-4a3c-bea6-8e309b79b533'
BIBO_VOCAB_UUID = '00000000-11fc-1f89-4d9a-943fa4a4c7da'
PREDICATE_BIBO_CONTENT_UUID = '00000000-11fc-e567-6593-b2cf0210a1e4'

# CIDOC-CRM Ontonlogy
CIDOC_PUB_UUID = 'ab03a6b8-f87b-4cfa-8b08-7a68be7b61ef'
CIDOC_VOCAB_UUID =  '00000000-798b-aa74-20d9-96d2bba09865'
PREDICATE_CIDOC_CONSISTS_OF_UUID = '00000000-798b-ac05-70c4-1762c7ad066e'
PREDICATE_CIDOC_HAS_TYPE_UUID = '00000000-798b-37da-99aa-704b3f50c62f'
PREDICATE_CIDOC_HAS_UNIT_UUID = '00000000-798b-85cc-1bc4-172732da72bf'
# CRM-EH (English Heritage CIDOC CRM Extentions)
EH_PUB_UUID = '00462c87-720e-474b-9218-60fc11568513'
CRMEH_VOCAB_UUID = '00000000-a352-78cb-4e05-e9f7138a1493'
CLASS_CRMEH_AREA_OF_INVEST_UUID = '00000000-a352-82b6-15ec-78c4ad0924c4'

# GeoJSON
GEOJSON_PUB_UUID = '8b217b00-c204-4b00-af05-acb6d62691dd'
GEOJSON_VOCAB_UUID = '00000000-3d2f-f57e-4f60-9ecdbc53e535'

# Library of Congress
LOC_PUB_UUID = '0c1d63ae-5b0c-480b-9cf5-617269c3f8cd'
LOC_SUBJ_HEAD_VOCAB_UUID = '00000000-8dad-ba96-6125-887aa30dbfda'
LOC_PERIODO_VOCAB_UUID = '00000000-7bc4-40c8-1466-37a5d076c902'

# Getty
GETTY_PUB_UUID = 'bd1a0bf8-3b4b-488a-b9ac-b3814dc36798'
GETTY_AAT_VOCAB_UUID = '00000000-53ae-3cda-d835-ec8864e26956'



# --------------------------------------------------------------------
# Wikipedia publisher and vocabularies
WIKIPEDIA_PUB_UUID = '978f0a01-dce5-4d90-a40d-959471039876'
WIKIPEDIA_VOCAB_UUID = '00000000-b1b7-38dd-dbb4-4e742a1770ec'
WIKIDATA_VOCAB_UUID = '00000000-75e9-fdf2-40db-0fd1ddcc8997'
WIKTIONARY_VOCAB_UUID = '00000000-459a-0cee-ae90-4e783860ca74'
# ---------------------------------------------------------------------

# LANGUAGES (Use Wikidata for URIs to languages)
# NOTE - Expand on these as needed. This is currently pretty comprehensive
# for Open Context's current coverage.
LANG_AR_UUID = '00000000-75e9-0c86-2ceb-f176f1a75050'  # Arabic
LANG_DE_UUID = '00000000-75e9-5e18-f221-4e41746744ca'  # German
LANG_EL_UUID = '00000000-75e9-737b-3ab1-2992e9e8529f'  # Greek
LANG_EN_UUID = '00000000-75e9-d759-8d1d-eaa07c1c03dc'  # English
LANG_ES_UUID = '00000000-75e9-edd7-9197-973e7c649ed2'  # Spanish
LANG_FA_UUID = '00000000-75e9-b11a-277f-ca8960d463c8'  # Persian
LANG_FR_UUID = '00000000-75e9-2ae0-1d06-eaa65fa767bf'  # French
LANG_HE_UUID = '00000000-75e9-a959-ba14-3c0c421ad1c2'  # Hebrew
LANG_IT_UUID = '00000000-75e9-d58e-86ac-d02839ce4bc8'  # Italian
LANG_TR_UUID = '00000000-75e9-9f79-0dec-b1c4e2511942'  # Turkish
LANG_ZH_UUID = '00000000-75e9-6824-9448-fee92cff43b9'  # Chinese

# Default language to be English, overwrite this to change.
DEFAULT_LANG_UUID = LANG_EN_UUID

# Units of Measurement (Use Wikidata for URIs for Units of Measurement)
# NOTE - Expand on these as needed. 
UNITS_CENTIMETER_UUID = '00000000-75e9-092a-9afa-b9d6227ea8ea'
UNITS_COUNTING_MEASURE_UUID = '00000000-75e9-0f41-d9ef-29a517f44b06'
UNITS_DEGREE_UUID = '00000000-75e9-a86f-981d-73f03c797b21'
UNITS_FOOT_UUID = '00000000-75e9-2995-79d7-995113a4dc8e'
UNITS_GRAM_UUID = '00000000-75e9-b5a4-0273-adfe75dacd0c'
UNITS_HECTARE_UUID = '00000000-75e9-9348-46a3-ce508a6b1dc6'
UNITS_KILOGRAM_UUID = '00000000-75e9-a03d-3e8c-4d27830f7b11'
UNITS_KILOMETER_UUID = '00000000-75e9-6e82-d4b3-cd85c42f97f5'
UNITS_LITER_UUID = '00000000-75e9-bf7b-5ae0-d6b021365b43'
UNITS_METER_UUID = '00000000-75e9-0e4b-1650-809b6a9d5294'
UNITS_METRIC_TON_UUID = '00000000-75e9-b158-42cf-069ce8d5c638'
UNITS_MICROGRAM_UUID ='00000000-75e9-51f3-29b8-86cf873bc790'
UNITS_MILLIGRAM_UUID = '00000000-75e9-63c7-ee9f-3526f846159c'
UNITS_MILLILITER_UUID = '00000000-75e9-e55c-6b90-f7630eb8fb11'
UNITS_MILLIMETER_UUID = '00000000-75e9-5503-d05c-c90f3da8f4b5'
UNITS_SQUAREMETER_UUID = '00000000-75e9-c8ae-b57c-0ab952428987'


# List of predicate uuids where the subject is roughly equivalent to the object
PREDICATE_LIST_DBJ_EQUIV_OBJ = [
    PREDICATE_OWL_SAME_AS_UUID,
    PREDICATE_SKOS_EXACT_MATCH_UUID,
    PREDICATE_SKOS_CLOSE_MATCH_UUID,
]

# List of predicate uuids where the subject is a child (subordinate)
# of a parent (broader) object item.
PREDICATE_LIST_SBJ_IS_SUBORD_OF_OBJ = [
    PREDICATE_SKOS_BROADER_UUID,
    PREDICATE_SKOS_BROADER_TRANS_UUID,
    PREDICATE_SKOS_BROAD_MATCH_UUID,
    PREDICATE_RDFS_SUB_CLASS_OF_UUID,
    PREDICATE_RDFS_SUB_PROP_OF_UUID,
    PREDICATE_DCTERMS_IS_PART_OF_UUID,
]

# List of predicate uuids where the subject is a broader parent of
# of a subordinate, child object item.
PREDICATE_LIST_SBJ_IS_SUPER_OF_OBJ = [
    PREDICATE_SKOS_NARROWER_UUID,
    PREDICATE_SKOS_NARROWER_TRANS_UUID,
    PREDICATE_SKOS_NARROW_MATCH_UUID,
    PREDICATE_DCTERMS_HAS_PART_UUID,
]

# List of predicate uuids specific for spatial hierarchies where
# the subject item is broader and contains the subordinate child
# object item.
PREDICTATE_LIST_CONTEXT_SBJ_IS_SUPER_OF_OBJ = [
    PREDICATE_CONTAINS_UUID,
    PREDICATE_ALSO_CONTAINS_UUID,
]