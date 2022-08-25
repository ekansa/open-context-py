from django.urls import include, re_path, path
from django.conf import settings
from django.contrib import admin
admin.autodiscover()

from opencontext_py.apps.index import views as HomeViews
from opencontext_py.apps.ocitems.manifest import views as ManifestViews
from opencontext_py.apps.about import views as AboutViews
from opencontext_py.apps.contexts import views as ContextViews
from opencontext_py.apps.ocitems.subjects import views as SubjectViews
from opencontext_py.apps.ocitems.mediafiles import views as MediaViews
from opencontext_py.apps.ocitems.documents import views as DocumentViews
from opencontext_py.apps.ocitems.persons import views as PersonViews
from opencontext_py.apps.ocitems.projects import views as ProjectViews
from opencontext_py.apps.ocitems.predicates import views as PredicateViews
from opencontext_py.apps.ocitems.octypes import views as OCtypeViews
from opencontext_py.apps.exports.exptables import views as OCtableViews
from opencontext_py.apps.searcher.search import views as SearchViews
from opencontext_py.apps.entities.entity import views as EntityViews
from opencontext_py.apps.edit.items import views as EditItemViews
from opencontext_py.apps.edit.projects import views as EditProjectsViews
from opencontext_py.apps.edit.inputs import views as InputProfileViews
from opencontext_py.apps.imports.sources import views as Imp_sources
from opencontext_py.apps.imports.fields import views as Imp_fields
from opencontext_py.apps.imports.fieldannotations import views as Imp_field_annos
from opencontext_py.apps.ldata.linkvocabularies import views as vocabViews
from opencontext_py.apps.oai import views as OAIviews
from opencontext_py.apps.utilities import views as UtilitiesViews
from opencontext_py.apps.ldata.pelagios import views as PelagiosViews



# For testing new search
from opencontext_py.apps.searcher.new_solrsearcher import views as NewSearchViews

# Testing views for all items
from opencontext_py.apps.all_items import views as AllItemsViews
from opencontext_py.apps.all_items.editorial import views as EditorialViews
from opencontext_py.apps.all_items.editorial.item import views as EditorialItemViews
# Testing views for making export tables
from opencontext_py.apps.all_items.editorial.tables import views as EditorialExportViews

# Testing new ETL views. These are for GET requests
from opencontext_py.apps.etl.importer import views as etlViews
# Testing new ETL views for POST request endpoints.
from opencontext_py.apps.etl.importer.setup import views as etlSetupViews
# Testing new ETL views for POST request for final transform, load steps.
from opencontext_py.apps.etl.importer.transforms import views as etlTransformsViews


urlpatterns = [
    # Examples:
    # url(r'^$', 'opencontext_py.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),
    # legacy URL for getting atom feed of manifest
    re_path(r'^manifest/.atom', ManifestViews.index_atom, name='manifest_index_atom'),
    re_path(r'^manifest.atom', ManifestViews.index_atom, name='manifest_index_ns_atom'),
    # legacy URL for getting atom feed of manifest
    re_path(r'^all/.atom', ManifestViews.all_atom, name='manifest_all_atom'),
    re_path(r'^all.atom', ManifestViews.all_atom, name='manifest_all_ns_atom'),
    re_path(r'^manifest/', ManifestViews.index, name='manifest_index_view'),
    # About pages
    re_path(r'^about/uses', AboutViews.uses_view, name='about_uses'),
    re_path(r'^about/publishing', AboutViews.pub_view, name='about_publishing'),
    re_path(r'^about/estimate', AboutViews.estimate_view, name='about_estimate'),
    re_path(r'^about/process-estimate', AboutViews.process_estimate, name='process_estimate'),
    re_path(r'^about/concepts', AboutViews.concepts_view, name='about_concepts'),
    re_path(r'^about/technology', AboutViews.tech_view, name='about_technology'),
    re_path(r'^about/recipes', AboutViews.recipes_view, name='about_recipes'),
    re_path(r'^about/services', AboutViews.services_view, name='about_services'),
    re_path(r'^about/bibliography', AboutViews.bibliography_view, name='about_bibliography'),
    re_path(r'^about/intellectual-property', AboutViews.ip_view, name='about_ip'),
    re_path(r'^about/people', AboutViews.people_view, name='about_people'),
    re_path(r'^about/sponsors', AboutViews.sponsors_view, name='about_sponsors'),
    re_path(r'^about/terms', AboutViews.terms_view, name='about_terms'),
    re_path(r'^about/', AboutViews.index_view, name='about_index'),
    # Contexts for JSON-LD
    re_path(r'^contexts/item.json', ContextViews.item_view, name='context_item'),
    re_path(r'^contexts/search.json', ContextViews.search_view, name='context_search'),
    re_path(r'^contexts/projects/(?P<uuid>\S+)?.json', ContextViews.projects_json, name='context_proj_json'),
    re_path(r'^contexts/projects/(?P<uuid>\S+)?', ContextViews.projects_json, name='context_proj_gen'),
    re_path(r'^contexts/project-vocabs/(?P<uuid>\S+)?.jsonld', ContextViews.project_vocabs_jsonld, name='context_proj_vocab_jsonld'),
    re_path(r'^contexts/project-vocabs/(?P<uuid>\S+)?.json', ContextViews.project_vocabs_json, name='context_proj_vocab_json'),
    # re_path(r'^contexts/project-vocabs/(?P<uuid>\S+)?.nq', ContextViews.project_vocabs_nquads, name='context_proj_vocab_nquads'),
    re_path(r'^contexts/project-vocabs/(?P<uuid>\S+)?.nt', ContextViews.project_vocabs_ntrpls, name='context_proj_vocab_ntrpls'),
    re_path(r'^contexts/project-vocabs/(?P<uuid>\S+)?.rdf', ContextViews.project_vocabs_rdf, name='context_proj_vocab_rdf'),
    re_path(r'^contexts/project-vocabs/(?P<uuid>\S+)?.ttl', ContextViews.project_vocabs_turtle, name='project_vocabs_turtle'),
    re_path(r'^contexts/project-vocabs/(?P<uuid>\S+)?', ContextViews.project_vocabs, name='context_proj_vocab_gen'),
    re_path(r'^contexts', AboutViews.index_view, name='about_index'),

    # New Search (testing) views
    re_path(r'^suggest.json?', NewSearchViews.suggest_json, name='new_search_suggest_json'),
    re_path(r'^suggest', NewSearchViews.suggest_json, name='new_search_suggest'),
    re_path(r'^query.json?', NewSearchViews.query_json, name='new_search_json_d'),
    re_path(r'^query/(?P<spatial_context>\S+)?.json', NewSearchViews.query_json, name='new_search_json'),
    re_path(r'^query/(?P<spatial_context>\S+)?', NewSearchViews.query_html, name='new_search_html'),

    # New all_items testing views
    re_path(r'^all-items/(?P<uuid>\S+)?\.json$', AllItemsViews.test_json, name='all_items_json'),
     re_path(r'^all-items/(?P<uuid>\S+)/full', AllItemsViews.test_html_full, name='all_items_full'),
    re_path(r'^all-items/(?P<uuid>\S+)', AllItemsViews.test_html, name='all_items_html'),

    # New add_items administrative (for editing, etl) views
    re_path(
        r'^editorial/item-children/(?P<identifier>\S+)', 
        EditorialViews.item_children_json, 
        name='editorial_item_children'
    ),
    re_path(
        r'^editorial/item-assert-examples/(?P<identifier>\S+)', 
        EditorialViews.item_assert_examples_json,
        name='editorial_item_assert_examples_json'
    ),
    re_path(r'^editorial/item-look-up', EditorialViews.item_look_up_json, name='editorial_item_look_up'),
    re_path(r'^editorial/item-meta-look-up', EditorialViews.item_meta_look_up_json, name='editorial_item_meta_look_up'),
    re_path(r'^editorial/html-validate', EditorialViews.html_validate, name='editorial_html_validate'),
    # New edit_item administrative (for editing) views
    re_path(
        r'^editorial/item-add-configs', 
        EditorialItemViews.item_add_configs_json, 
        name='editorial_item_add_configs_json'
    ),
    re_path(
        r'^editorial/item-edit/(?P<uuid>\S+)', 
        EditorialItemViews.item_edit_interface_html, 
        name='editorial_item_edit_interface_html'
    ),
    re_path(
        r'^editorial/item-history/(?P<uuid>\S+)', 
        EditorialItemViews.item_history_json, 
        name='editorial_item_history_json'
    ),
    re_path(
        r'^editorial/item-manifest/(?P<uuid>\S+)', 
        EditorialItemViews.item_manifest_json, 
        name='editorial_item_manifest_json'
    ),
    re_path(
        r'^editorial/item-manifest-validation', 
        EditorialItemViews.item_manifest_validation, 
        name='editorial_item_manifest_validation_json'
    ),
    re_path(
        r'^editorial/item-update-manifest', 
        EditorialItemViews.update_manifest_objs, 
        name='editorial_update_manifest_objs'
    ),
     re_path(
        r'^editorial/item-add-manifest', 
        EditorialItemViews.add_manifest_objs, 
        name='editorial_add_manifest_objs'
    ),
    re_path(
        r'^editorial/item-delete-manifest', 
        EditorialItemViews.delete_manifest, 
        name='editorial_delete_manifest'
    ),
    re_path(
        r'^editorial/item-merge-manifest', 
        EditorialItemViews.merge_manifest, 
        name='editorial_merge_manifest'
    ),
    # Item assertion editing URLs
    re_path(
        r'^editorial/item-assertions/(?P<uuid>\S+)', 
        EditorialItemViews.item_assertions_json, 
        name='editorial_item_assertions_json'
    ),
    re_path(
        r'^editorial/item-update-assertions', 
        EditorialItemViews.update_assertions_objs, 
        name='editorial_update_assertions_objs'
    ),
    re_path(
        r'^editorial/item-add-assertions', 
        EditorialItemViews.add_assertions, 
        name='editorial_add_assertions'
    ),
    re_path(
        r'^editorial/item-delete-assertions', 
        EditorialItemViews.delete_assertions, 
        name='editorial_delete_assertions'
    ),
    re_path(
        r'^editorial/item-sort-item-assertions', 
        EditorialItemViews.sort_item_assertions, 
        name='editorial_sort_item_assertions'
    ),
    re_path(
        r'^editorial/item-sort-project-assertions', 
        EditorialItemViews.sort_project_assertions, 
        name='editorial_sort_project_assertions'
    ),
    # Item space-time editing URLs
    re_path(
        r'^editorial/item-spacetimes/(?P<uuid>\S+)', 
        EditorialItemViews.item_spacetime_json, 
        name='editorial_item_spacetime_json'
    ),
    re_path(
        r'^editorial/item-update-space-time', 
        EditorialItemViews.update_space_time_objs, 
        name='editorial_update_space_time_objs'
    ),
    re_path(
        r'^editorial/item-add-space-time', 
        EditorialItemViews.add_space_time, 
        name='editorial_add_space_time'
    ),
     re_path(
        r'^editorial/item-add-aggregate-space-time', 
        EditorialItemViews.add_aggregate_space_time, 
        name='editorial_add_aggregate_space_time'
    ),
    re_path(
        r'^editorial/item-delete-space-time', 
        EditorialItemViews.delete_space_time, 
        name='editorial_delete_space_time'
    ),
    # Item space-time editing URLs
    re_path(
        r'^editorial/item-resources/(?P<uuid>\S+)', 
        EditorialItemViews.item_resources_json, 
        name='editorial_item_resources_json'
    ),
    re_path(
        r'^editorial/item-update-resources', 
        EditorialItemViews.update_resource_objs, 
        name='editorial_update_resource_field'
    ),
    re_path(
        r'^editorial/item-add-resources', 
        EditorialItemViews.add_resources, 
        name='editorial_add_resources'
    ),
    re_path(
        r'^editorial/item-delete-resources', 
        EditorialItemViews.delete_resources, 
        name='editorial_delete_resources'
    ),
    # Item identifier editing URLs
    re_path(
        r'^editorial/item-identifiers/(?P<uuid>\S+)', 
        EditorialItemViews.item_identifiers_json, 
        name='editorial_item_identifiers_json'
    ),
    re_path(
        r'^editorial/item-update-identifiers', 
        EditorialItemViews.update_identifier_objs, 
        name='editorial_update_identifier_objs'
    ),
    re_path(
        r'^editorial/item-add-identifiers', 
        EditorialItemViews.add_identifiers, 
        name='editorial_add_identifiers'
    ),
    re_path(
        r'^editorial/item-delete-identifiers', 
        EditorialItemViews.delete_identifiers, 
        name='editorial_delete_identifiers'
    ),
    # Project Human-Remains flagging
    re_path(
        r'^editorial/flag-project-human-remains', 
        EditorialItemViews.flag_project_human_remains, 
        name='editorial_flag_project_human_remains'
    ),

    re_path(
        r'^editorial/proj-descriptions-tree/(?P<identifier>\S+)', 
        EditorialItemViews.project_descriptions_tree_json, 
        name='editorial_project_descriptions_tree_json',
    ),
    re_path(
        r'^editorial/proj-spatial-tree/(?P<identifier>\S+)', 
        EditorialItemViews.project_spatial_tree_json, 
        name='editorial_project_spatial_tree_json',
    ),
    re_path(
        r'^editorial/proj-persons/(?P<identifier>\S+)', 
        EditorialItemViews.project_persons_json, 
        name='editorial_project_persons_json',
    ),
    re_path(
        r'^editorial/proj-data-sources/(?P<identifier>\S+)', 
        EditorialItemViews.project_data_sources_json, 
        name='editorial_project_data_sources_json',
    ),
    # New Export data editorial views
    re_path(
        r'^editorial/export-configs', 
        EditorialExportViews.export_configs,
        name='editorial_export_configs'
    ),
    re_path(
        r'^editorial/export-make', 
        EditorialExportViews.make_export,
        name='editorial_export_make_export'
    ),
    re_path(
        r'^editorial/export-temp-tables/(?P<export_id>\S+)', 
        EditorialExportViews.get_temp_export_table,
        name='editorial_export_get_temp_export_table'
    ),


    # New ETL views
    re_path(r'^etl-importer/prepare/(?P<source_id>\S+)', etlViews.home_html, name='etl_home_html'),
    re_path(r'^etl-importer/source/(?P<source_id>\S+)', etlViews.etl_source, name='etl_source_json'),
    re_path(r'^etl-importer/fields/(?P<source_id>\S+)', etlViews.etl_fields, name='etl_fields_json'),
    re_path(
        r'^etl-importer/field-record-examples/(?P<field_uuid>\S+)', 
        etlViews.etl_field_record_examples, 
        name='etl_field_record_examples_json'
    ),
    re_path(r'^etl-importer/annotations/(?P<source_id>\S+)', etlViews.etl_annotations, name='etl_annotations_json'),
    re_path(
        r'^etl-importer/spatial-contained-examples/(?P<source_id>\S+)', 
        etlViews.etl_spatial_contained_examples, 
        name='etl_spatial_contained_examples_json'
    ),
    re_path(
        r'^etl-importer/linked-examples/(?P<source_id>\S+)', 
        etlViews.etl_link_annotations_examples, 
        name='etl_link_annotations_examples_json'
    ),
    re_path(
        r'^etl-importer/described-by-examples/(?P<source_id>\S+)', 
        etlViews.etl_described_by_examples, 
        name='etl_described_by_examples_json'
    ),
    # New ETL POST request views
    re_path(r'^etl-importer-setup/update-fields', etlSetupViews.etl_update_fields, name='etl_setup_update_fields'),
    re_path(r'^etl-importer-setup/delete-annotations', etlSetupViews.etl_delete_annotations, name='etl_delete_annotations'),
    re_path(r'^etl-importer-setup/add-annotations', etlSetupViews.etl_add_annotations, name='etl_add_annotations'),
    # New ETL POST transform-load views
    re_path(
        r'^etl-importer-transforms/reset-transform-load/(?P<source_id>\S+)', 
        etlTransformsViews.etl_reset_transform_load,
        name='etl_reset_transform_load_json'
    ),
    re_path(
        r'^etl-importer-transforms/transform-load/(?P<source_id>\S+)', 
        etlTransformsViews.etl_transform_load,
        name='etl_transform_load_json'
    ),


    
    re_path(r'^search.json?', SearchViews.json_view, name='search_json_d'),
    re_path(r'^search/(?P<spatial_context>\S+)?.json', SearchViews.json_view, name='search_json'),
    re_path(r'^search/(?P<spatial_context>\S+)?', SearchViews.html_view, name='search_html'),
    # Subjects views for main records (subjects of observations)
    re_path(r'^subjects/(?P<uuid>\S+)?\.jsonld$', AllItemsViews.subjects_json, name='subjects_jsonld'),
    re_path(r'^subjects/(?P<uuid>\S+)?\.geojson$', AllItemsViews.subjects_json, name='subjects_geojson'),
    re_path(r'^subjects/(?P<uuid>\S+)?\.json$', AllItemsViews.subjects_json, name='subjects_json'),
    re_path(r'^subjects/(?P<uuid>\S+)', AllItemsViews.subjects_html, name='subjects_html'),
    # Media views (media resources / metadata + binary files)
    re_path(r'^media/(?P<uuid>\S+)?\.jsonld$', AllItemsViews.media_json, name='media_jsonld'),
    re_path(r'^media/(?P<uuid>\S+)?\.geojson$', AllItemsViews.media_json, name='media_geojson'),
    re_path(r'^media/(?P<uuid>\S+)?\.json$', AllItemsViews.media_json, name='media_json'),
    re_path(r'^media/(?P<uuid>\S+)/full', AllItemsViews.media_full_html, name='media_full'),
    re_path(r'^media/(?P<uuid>\S+)', AllItemsViews.media_html, name='media_html'),
    # Document views for HTML document items
    re_path(r'^documents/(?P<uuid>\S+)?\.jsonld$', AllItemsViews.documents_json, name='documents_jsonld'),
    re_path(r'^documents/(?P<uuid>\S+)?\.geojson$', AllItemsViews.documents_json, name='documents_geojson'),
    re_path(r'^documents/(?P<uuid>\S+)?\.json$', AllItemsViews.documents_json, name='documents_json'),
    re_path(r'^documents/(?P<uuid>\S+)', AllItemsViews.documents_html, name='documents_html'),
    # Person views for Person / organization items
    re_path(r'^persons/(?P<uuid>\S+)?\.jsonld$', AllItemsViews.persons_json, name='persons_jsonld'),
    re_path(r'^persons/(?P<uuid>\S+)?\.json$', AllItemsViews.persons_json, name='persons_json'),
    re_path(r'^persons/(?P<uuid>\S+)', AllItemsViews.persons_html, name='persons_html'),
    re_path(r'^persons', AboutViews.index_view, name='about_index'),
    # Project views for projects
    re_path(r'^projects/(?P<uuid>\S+)?\.jsonld$', AllItemsViews.projects_json, name='projects_jsonld'),
    re_path(r'^projects/(?P<uuid>\S+)?\.geojson$', AllItemsViews.projects_json, name='projects_geojson'),
    re_path(r'^projects/(?P<uuid>\S+)?\.json$', AllItemsViews.projects_json, name='projects_json'),
    re_path(r'^projects/(?P<uuid>\S+)', AllItemsViews.projects_html, name='projects_html'),
    re_path(r'^projects', ProjectViews.index, name='projects_search_html_s'),
    # Predicates views for descriptive variables and linking relations from OC contributors
    re_path(r'^predicates/(?P<uuid>\S+)?\.jsonld$', AllItemsViews.predicates_json, name='predicates_jsonld'),
    re_path(r'^predicates/(?P<uuid>\S+)?\.json$', AllItemsViews.predicates_json, name='predicates_json'),
    re_path(r'^predicates/(?P<uuid>\S+)', AllItemsViews.predicates_html, name='predicates_html'),
    re_path(r'^predicates', AboutViews.index_view, name='about_index'),
    # Types views for controlled vocabulary entities from OC contributors
    re_path(r'^types/(?P<uuid>\S+)?\.jsonld$',  AllItemsViews.types_json, name='types_jsonld'),
    re_path(r'^types/(?P<uuid>\S+)\.json$', AllItemsViews.types_json, name='types_json'),
    re_path(r'^types/(?P<uuid>\S+)', AllItemsViews.types_html, name='types_html'),
    re_path(r'^types', OCtypeViews.index, name='types_index'),
    # Table views for controlled downloadable tables
    re_path(r'^tables/(?P<table_id>\S+)\.json$', OCtableViews.json_view, name='tables_json'),
    re_path(r'^tables/(?P<table_id>\S+)\.csv$', OCtableViews.csv_view, name='tables_csv'),
    re_path(r'^tables/(?P<table_id>\S+)', OCtableViews.html_view, name='tables_html'),
    re_path(r'^tables', OCtableViews.index_view, name='tables_index'),
    # Vocabulary views for viewing controlled vocab + ontology entities
    re_path(r'^vocabularies/(?P<identifier>\S+).json', vocabViews.json_view, name='vocabularies_json'),
    re_path(r'^vocabularies/(?P<identifier>\S+)', vocabViews.html_view, name='vocabularies_html'),
    re_path(r'^vocabularies', vocabViews.index_view, name='vocabularies_index'),
    # --------------------------
    # IMPORTER INTERFACE PAGES
    # --------------------------
    re_path(r'^imports/projects/(?P<project_uuid>\S+)',  Imp_sources.project,
        name='imp_sources_projects'),
    re_path(r'^imports/field-types/(?P<source_id>\S+)', Imp_sources.field_types,
        name='field_types'),
    re_path(r'^imports/field-types-more/(?P<source_id>\S+)', Imp_sources.field_types_more,
        name='field_types_more'),
    re_path(r'^imports/field-entity-relations/(?P<source_id>\S+)', Imp_sources.field_entity_relations,
        name='field_entity_relations'),
    re_path(r'^imports/field-complex-desciptions/(?P<source_id>\S+)', Imp_sources.field_complex_descriptions,
        name='field_complex_descriptions'),
    re_path(r'^imports/field-descriptions/(?P<source_id>\S+)', Imp_sources.field_descriptions,
        name='field_descriptions'),
    re_path(r'^imports/finalize/(?P<source_id>\S+)', Imp_sources.finalize,
        name='imp_source_finalize'),
    # --------------------------
    # IMPORTER PROJECT POST REQUESTS
    # --------------------------
    re_path(r'^imports/create-project', Imp_sources.create_project,
        name='imp_sources_create_project'),
    re_path(r'^imports/edit-project/(?P<project_uuid>\S+)', Imp_sources.edit_project,
        name='imp_sources_edit_project'),
    # --------------------------
    # BELOW ARE URLs FOR IMPORTER AJAX REQUESTS
    # --------------------------
    re_path(r'^imports/project-import-refine/(?P<project_uuid>\S+)', Imp_sources.project_import_refine,
        name='imp_sources_project_import_refine'),
    re_path(r'^imports/import-finalize/(?P<source_id>\S+)', Imp_sources.import_finalize,
        name='imp_sources_import_finalize'),
    re_path(r'^imports/field-classify/(?P<source_id>\S+)', Imp_fields.field_classify,
        name='imp_field_classify'),
    re_path(r'^imports/field-meta-update/(?P<source_id>\S+)', Imp_fields.field_meta_update,
        name='imp_field_meta_update'),
    re_path(r'^imports/field-titlecase/(?P<source_id>\S+)', Imp_fields.field_titlecase,
        name='imp_field_titlecase'),
    re_path(r'^imports/field-list/(?P<source_id>\S+)', Imp_fields.field_list,
        name='imp_field_list'),
    re_path(r'^imports/field-annotations/(?P<source_id>\S+)', Imp_field_annos.view,
        name='imp_field_annos_view'),
    re_path(r'^imports/subjects-hierarchy-examples/(?P<source_id>\S+)', Imp_field_annos.subjects_hierarchy_examples,
        name='imp_field_annos_subjects_hierarchy_examples'),
    re_path(r'^imports/field-described-examples/(?P<source_id>\S+)', Imp_field_annos.described_examples,
        name='imp_field_annos_described_examples'),
    re_path(r'^imports/field-linked-examples/(?P<source_id>\S+)', Imp_field_annos.linked_examples,
        name='imp_field_annos_linked_examples'),
    re_path(r'^imports/field-annotation-delete/(?P<source_id>\S+)/(?P<annotation_id>\S+)', Imp_field_annos.delete,
        name='imp_field_annos_delete'),
    re_path(r'^imports/field-annotation-create/(?P<source_id>\S+)', Imp_field_annos.create,
        name='imp_field_annos_create'),
    # --------------------------
    # BELOW IS THE INDEX PAGE FOR THE IMPORTER
    # --------------------------
    re_path(r'^imports/', Imp_sources.index,
        name='imp_sources_index'),
    # --------------------------
    # BELOW ARE URLs FOR ENTITY EDITS INTERFACE PAGES
    # --------------------------
    re_path(r'^edit/items/(?P<uuid>\S+)', EditItemViews.html_view,
        name='edit_item_html_view'),
    # --------------------------
    # BELOW ARE URLs FOR ENTITY EDITS AJAX REQUESTS
    # --------------------------
    re_path(r'^edit/update-item-basics/(?P<uuid>\S+)', EditItemViews.update_item_basics,
        name='edit_item_basics'),
    re_path(r'^edit/update-predicate-sort-order/(?P<uuid>\S+)', EditItemViews.update_predicate_sort_order,
        name='update_predicate_sort_order'),
    re_path(r'^edit/update-project-hero/(?P<uuid>\S+)', EditItemViews.update_project_hero,
        name='edit_update_project_hero'),
    re_path(r'^edit/update-media-file/(?P<uuid>\S+)', EditItemViews.update_media_file,
        name='edit_update_media_file'),
    re_path(r'^edit/add-edit-item-containment/(?P<uuid>\S+)', EditItemViews.add_edit_item_containment,
        name='edit_add_edit_item_containment'),
    re_path(r'^edit/add-edit-item-assertion/(?P<uuid>\S+)', EditItemViews.add_edit_item_assertion,
        name='edit_add_edit_item_assertion'),
    re_path(r'^edit/add-edit-string-translation/(?P<string_uuid>\S+)',
        EditItemViews.add_edit_string_translation,
        name='edit_add_edit_string_translation'),
    re_path(r'^edit/sort-item-assertion/(?P<uuid>\S+)', EditItemViews.sort_item_assertion,
        name='edit_sort_item_assertion'),
    re_path(r'^edit/delete-item-assertion/(?P<uuid>\S+)', EditItemViews.delete_item_assertion,
        name='edit_delete_item_assertion'),
    re_path(r'^edit/html-validate/', EditItemViews.html_validate,
        name='edit_html_validate'),
    re_path(r'^edit/add-item-annotation/(?P<uuid>\S+)', EditItemViews.add_item_annotation,
        name='add_item_annotation'),
    re_path(r'^edit/add-item-stable-id/(?P<uuid>\S+)', EditItemViews.add_item_stable_id,
        name='add_item_stable_id'),
    re_path(r'^edit/delete-item-stable-id/(?P<uuid>\S+)', EditItemViews.delete_item_stable_id,
        name='delete_item_stable_id'),
    re_path(r'^edit/edit-annotation/(?P<entity_id>\S+)', EditItemViews.edit_annotation,
        name='edit_annotation'),
    re_path(r'^edit/delete-annotation/(?P<entity_id>\S+)', EditItemViews.delete_annotation,
        name='delete_annotation'),
    re_path(r'^edit/create-item-into/(?P<project_uuid>\S+)', EditItemViews.create_item_into,
        name='create_item_into'),
    re_path(r'^edit/check-delete-item/(?P<uuid>\S+)', EditItemViews.check_delete_item,
        name='check_delete_item'),
    re_path(r'^edit/delete-item/(?P<uuid>\S+)', EditItemViews.delete_item,
        name='delete_item'),
    re_path(r'^edit/create-project', EditItemViews.create_project,
        name='create_project'),
    re_path(r'^edit/add-update-ld-entity', EditItemViews.add_update_ld_entity,
        name='add_update_ld_entity'),
    re_path(r'^edit/add-update-geo-data/(?P<uuid>\S+)', EditItemViews.add_update_geo_data,
        name='add_update_geo_data'),
    re_path(r'^edit/add-update-project-geo/(?P<uuid>\S+)', EditItemViews.add_update_project_geo,
        name='add_update_project_geo'),
    re_path(r'^edit/add-update-date-range/(?P<uuid>\S+)', EditItemViews.add_update_date_range,
        name='add_update_date_range'),
    re_path(r'^edit/delete-date-range/(?P<uuid>\S+)', EditItemViews.delete_date_range,
        name='delete_date_range'),
    re_path(r'^edit/projects/(?P<project_uuid>\S+)', EditProjectsViews.status,
        name='edit_projects_status'),
    # --------------------------
    # BELOW ARE URLs FOR INPUT PROFILE RELATED AJAX REQUESTS
    # --------------------------
    re_path(r'^edit/inputs/profiles/(?P<profile_uuid>\S+).json', InputProfileViews.json_view,
        name='edit_input_profile_json_view'),
    re_path(r'^edit/inputs/profiles/(?P<profile_uuid>\S+)/edit', InputProfileViews.profile_edit,
        name='edit_input_profile_edit'),
    re_path(r'^edit/inputs/profiles/(?P<profile_uuid>\S+)/(?P<edit_uuid>\S+)', InputProfileViews.profile_use,
        name='edit_input_profile_use'),
    re_path(r'^edit/inputs/create-update-profile-item/(?P<profile_uuid>\S+)/(?P<edit_uuid>\S+)',
        InputProfileViews.create_update_profle_item,
        name='edit_input_profile_create_update_profle_item'),
    re_path(r'^edit/inputs/profile-item-list/(?P<profile_uuid>\S+)', InputProfileViews.profile_item_list,
        name='edit_input_profile_item_list'),
    re_path(r'^edit/inputs/create-profile/(?P<project_uuid>\S+)', InputProfileViews.create,
        name='edit_input_profile_create'),
    re_path(r'^edit/inputs/update-profile/(?P<profile_uuid>\S+)', InputProfileViews.update,
        name='edit_input_profile_update'),
    re_path(r'^edit/inputs/delete-profile/(?P<profile_uuid>\S+)', InputProfileViews.delete,
        name='edit_input_profile_delete'),
    re_path(r'^edit/inputs/duplicate-profile/(?P<profile_uuid>\S+)', InputProfileViews.duplicate,
        name='edit_input_profile_duplicate'),
    re_path(r'^edit/inputs/create-field-group/(?P<profile_uuid>\S+)', InputProfileViews.create_field_group,
        name='edit_input_create_field_group'),
    re_path(r'^edit/inputs/update-field-group/(?P<fgroup_uuid>\S+)', InputProfileViews.update_field_group,
        name='edit_input_update_field_group'),
    re_path(r'^edit/inputs/delete-field-group/(?P<fgroup_uuid>\S+)', InputProfileViews.delete_field_group,
        name='edit_input_delete_field_group'),
    re_path(r'^edit/inputs/create-field/(?P<fgroup_uuid>\S+)', InputProfileViews.create_field,
        name='edit_input_create_field'),
    re_path(r'^edit/inputs/update-field/(?P<field_uuid>\S+)', InputProfileViews.update_field,
        name='edit_input_update_field'),
    re_path(r'^edit/inputs/delete-field/(?P<field_uuid>\S+)', InputProfileViews.delete_field,
        name='edit_input_delete_field'),
    re_path(r'^edit/inputs/reorder-item/(?P<uuid>\S+)', InputProfileViews.reorder_item,
        name='edit_input_reorder_item'),
    re_path(r'^edit/inputs/item-label-check/(?P<project_uuid>\S+)', InputProfileViews.label_check,
        name='edit_input_label_check'),
    re_path(r'^edit/inputs/(?P<project_uuid>\S+).json', InputProfileViews.index_json,
        name='edit_input_index_json'),
    # --------------------------
    # EDITING ROOT
    # --------------------------
    re_path(r'^edit/', EditProjectsViews.index,
        name='edit_projects_index'),
    # --------------------------
    # --------------------------
    # BELOW ARE URLs FOR ENTITY LOOKUP AJAX REQUESTS
    # --------------------------
    re_path(r'^entities/hierarchy-children/(?P<identifier>\S+)', EntityViews.hierarchy_children,
        name='entity_hierarchy_children'),
    re_path(r'^entities/id-summary/(?P<identifier>\S+)', EntityViews.id_summary,
        name='entity_id_summary'),
    re_path(r'^entities/look-up/(?P<item_type>\S+)', EntityViews.look_up,
        name='entity_look_up'),
    re_path(r'^entities/annotations/(?P<subject>\S+)', EntityViews.entity_annotations,
        name='entity_annotations'),
    re_path(r'^entities/contain-children/(?P<identifier>\S+)', EntityViews.contain_children,
        name='entity_contain_children'),
    re_path(r'^entities/description-children/(?P<identifier>\S+)', EntityViews.description_hierarchy,
        name='entity_description_hierarchy'),
    re_path(r'^entities/proxy/(?P<target_url>\S+)', EntityViews.proxy,
        name='entity_proxy'),
    re_path(r'^entities/proxy-header/(?P<target_url>\S+)', EntityViews.proxy_header,
        name='entity_proxy_header'),
    # testing for new item json generation
    re_path(r'^items/(?P<identifier>\S+).json', EntityViews.items_json, name='items_json'),
    #----------------------------
    # BELOW ARE OAI REQUESTS (OAIviews)
    #----------------------------
    re_path(r'^oai/', OAIviews.index, name='oai_index'),
    #----------------------------
    # BELOW ARE PELAGIOS REQUESTS (PelagiosViews)
    #----------------------------
    re_path(r'^pelagios/void', PelagiosViews.void, name='pelagios_void'),
    re_path(r'^pelagios/void.ttl', PelagiosViews.void_ttl, name='pelagios_void_ttl'),
    re_path(r'^pelagios/gazetteer', PelagiosViews.gazetteer, name='pelagios_gaz'),
    re_path(r'^pelagios/gazetteer.ttl', PelagiosViews.gazetteer_ttl, name='pelagios_gaz_ttl'),
    re_path(r'^pelagios/data/(?P<identifier>\S+)?.ttl',
        PelagiosViews.project_annotations_ttl,
        name='pelagios_proj_ttl'),
    re_path(r'^pelagios/data/(?P<identifier>\S+)',
        PelagiosViews.project_annotations,
        name='pelagios_proj'),
    #----------------------------
    # BELOW ARE UTILITIES REQUESTS (UtilitiesViews)
    #----------------------------
    re_path(r'^utilities/meters-to-lat-lon', UtilitiesViews.meters_to_lat_lon, name='meters_to_lat_lon'),
    re_path(r'^utilities/lat-lon-to-quadtree', UtilitiesViews.lat_lon_to_quadtree, name='lat_lon_to_quadtree'),
    re_path(r'^utilities/quadtree-to-lat-lon', UtilitiesViews.quadtree_to_lat_lon, name='quadtree_to_lat_lon'),
    re_path(r'^utilities/reproject', UtilitiesViews.reproject, name='utilities_reproject'),
    re_path(r'^utilities/human-remains-ok', UtilitiesViews.human_remains_ok, name='human_remains_ok'),
    #----------------------------
    # BELOW ARE INDEX REQUESTS
    #----------------------------
    # robots.text route
    re_path(r'^robots.txt', HomeViews.robots, name='home_robots'),
    # Index, home-page route
    re_path(r'^$', HomeViews.index, name='home_index'),
    # Admin route
    re_path(r'^admin/', admin.site.urls)]

# how do we fix this?
# urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

if settings.DEBUG:
    import debug_toolbar
    urlpatterns += [path('__debug__/', include(debug_toolbar.urls))]
