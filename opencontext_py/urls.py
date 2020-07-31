from django.conf.urls import include, url
from django.conf import settings
from django.conf.urls.static import static
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


urlpatterns = [
    # Examples:
    # url(r'^$', 'opencontext_py.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),
    # legacy URL for getting atom feed of manifest
    url(r'^manifest/.atom', ManifestViews.index_atom, name='manifest_index_atom'),
    url(r'^manifest.atom', ManifestViews.index_atom, name='manifest_index_ns_atom'),
    # legacy URL for getting atom feed of manifest
    url(r'^all/.atom', ManifestViews.all_atom, name='manifest_all_atom'),
    url(r'^all.atom', ManifestViews.all_atom, name='manifest_all_ns_atom'),
    url(r'^manifest/', ManifestViews.index, name='manifest_index_view'),
    # About pages
    url(r'^about/uses', AboutViews.uses_view, name='about_uses'),
    url(r'^about/publishing', AboutViews.pub_view, name='about_publishing'),
    url(r'^about/estimate', AboutViews.estimate_view, name='about_estimate'),
    url(r'^about/process-estimate', AboutViews.process_estimate, name='process_estimate'),
    url(r'^about/concepts', AboutViews.concepts_view, name='about_concepts'),
    url(r'^about/technology', AboutViews.tech_view, name='about_technology'),
    url(r'^about/recipes', AboutViews.recipes_view, name='about_recipes'),
    url(r'^about/services', AboutViews.services_view, name='about_services'),
    url(r'^about/bibliography', AboutViews.bibliography_view, name='about_bibliography'),
    url(r'^about/intellectual-property', AboutViews.ip_view, name='about_ip'),
    url(r'^about/people', AboutViews.people_view, name='about_people'),
    url(r'^about/sponsors', AboutViews.sponsors_view, name='about_sponsors'),
    url(r'^about/terms', AboutViews.terms_view, name='about_terms'),
    url(r'^about/', AboutViews.index_view, name='about_index'),
    # Contexts for JSON-LD
    url(r'^contexts/item.json', ContextViews.item_view, name='context_item'),
    url(r'^contexts/search.json', ContextViews.search_view, name='context_search'),
    url(r'^contexts/projects/(?P<uuid>\S+)?.json', ContextViews.projects_json, name='context_proj_json'),
    url(r'^contexts/projects/(?P<uuid>\S+)?', ContextViews.projects_json, name='context_proj_gen'),
    url(r'^contexts/project-vocabs/(?P<uuid>\S+)?.jsonld', ContextViews.project_vocabs_jsonld, name='context_proj_vocab_jsonld'),
    url(r'^contexts/project-vocabs/(?P<uuid>\S+)?.json', ContextViews.project_vocabs_json, name='context_proj_vocab_json'),
    # url(r'^contexts/project-vocabs/(?P<uuid>\S+)?.nq', ContextViews.project_vocabs_nquads, name='context_proj_vocab_nquads'),
    url(r'^contexts/project-vocabs/(?P<uuid>\S+)?.nt', ContextViews.project_vocabs_ntrpls, name='context_proj_vocab_ntrpls'),
    url(r'^contexts/project-vocabs/(?P<uuid>\S+)?.rdf', ContextViews.project_vocabs_rdf, name='context_proj_vocab_rdf'),
    url(r'^contexts/project-vocabs/(?P<uuid>\S+)?.ttl', ContextViews.project_vocabs_turtle, name='project_vocabs_turtle'),
    url(r'^contexts/project-vocabs/(?P<uuid>\S+)?', ContextViews.project_vocabs, name='context_proj_vocab_gen'),
    url(r'^contexts', AboutViews.index_view, name='about_index'),
    # Sets views
    url(r'^sets/(?P<spatial_context>\S+)?.json', SearchViews.sets_view, name='sets_json'),
    url(r'^sets/(?P<spatial_context>\S+)?.atom', SearchViews.sets_view, name='sets_atom'),
    url(r'^sets/(?P<spatial_context>\S+)?', SearchViews.sets_view, name='sets_html'),
    # Lightbox views
    url(r'^lightbox/(?P<spatial_context>\S+)?.json', SearchViews.lightbox_view, name='lightbox_json'),
    url(r'^lightbox/(?P<spatial_context>\S+)?.atom', SearchViews.lightbox_view, name='lightbox_atom'),
    url(r'^lightbox/(?P<spatial_context>\S+)?', SearchViews.lightbox_view, name='lightbox_html'),
    # Search views
    url(r'^subjects-search.json?', SearchViews.subjects_json_view, name='subjects_search_json_d'),
    url(r'^subjects-search/(?P<spatial_context>\S+)?.json', SearchViews.subjects_json_view, name='subjects_search_json'),
    url(r'^subjects-search/(?P<spatial_context>\S+)?', SearchViews.subjects_html_view, name='subjects_search_html'),
    url(r'^media-search.json?', SearchViews.media_json_view, name='media_search_json_d'),
    url(r'^media-search/(?P<spatial_context>\S+)?.json', SearchViews.media_json_view, name='media_search_json'),
    url(r'^media-search/(?P<spatial_context>\S+)?', SearchViews.media_html_view, name='media_search_html'),
    url(r'^projects-search.json?', SearchViews.projects_json_view, name='projects_search_json_d'),
    url(r'^projects-search/(?P<spatial_context>\S+)?.json', SearchViews.projects_json_view, name='projects_search_json'),
    url(r'^projects-search/(?P<spatial_context>\S+)?', SearchViews.projects_html_view, name='projects_search_html'),
    
    # New Search (testing) views
    url(r'^query.json?', NewSearchViews.query_json, name='new_search_json_d'),
    url(r'^query/(?P<spatial_context>\S+)?.json', NewSearchViews.query_json, name='new_search_json'),
    url(r'^query/(?P<spatial_context>\S+)?', NewSearchViews.query_html, name='new_search_html'),
    
    url(r'^search.json?', SearchViews.json_view, name='search_json_d'),
    url(r'^search/(?P<spatial_context>\S+)?.json', SearchViews.json_view, name='search_json'),
    url(r'^search/(?P<spatial_context>\S+)?', SearchViews.html_view, name='search_html'),
    # Subjects views for main records (subjects of observations)
    url(r'^database/space.php', SubjectViews.old_redirect_view, name='old_redirect_html'),
    url(r'^subjects/(?P<uuid>\S+)?\.jsonld$', SubjectViews.jsonld_view, name='subjects_jsonld'),
    url(r'^subjects/(?P<uuid>\S+)?\.geojson$', SubjectViews.geojson_view, name='subjects_geojson'),
    url(r'^subjects/(?P<uuid>\S+)?\.json$', SubjectViews.json_view, name='subjects_json'),
    url(r'^subjects/(?P<uuid>\S+)?\.nt$', SubjectViews.ntrpls_view, name='subjects_ntrpls'),
    url(r'^subjects/(?P<uuid>\S+)?\.rdf$', SubjectViews.rdf_view, name='subjects_rdf'),
    url(r'^subjects/(?P<uuid>\S+)?\.ttl$', SubjectViews.turtle_view, name='subjects_turtle'),
    url(r'^subjects/(?P<uuid>\S+)', SubjectViews.html_view, name='subjects_html'),
    url(r'^subjects', SubjectViews.index, name='subjects_index_html_s'),
    # Media views (media resources / metadata + binary files)
    url(r'^media/(?P<uuid>\S+)?\.jsonld$', MediaViews.jsonld_view, name='media_jsonld'),
    url(r'^media/(?P<uuid>\S+)?\.geojson$', MediaViews.geojson_view, name='media_geojson'),
    url(r'^media/(?P<uuid>\S+)?\.json$', MediaViews.json_view, name='media_json'),
    url(r'^media/(?P<uuid>\S+)?\.nt$', MediaViews.ntrpls_view, name='media_ntrpls'),
    url(r'^media/(?P<uuid>\S+)?\.rdf$', MediaViews.rdf_view, name='media_rdf'),
    url(r'^media/(?P<uuid>\S+)?\.ttl$', MediaViews.turtle_view, name='media_turtle'),
    url(r'^media/(?P<uuid>\S+)/full', MediaViews.html_full, name='media_full'),
    url(r'^media/(?P<uuid>\S+)', MediaViews.html_view, name='media_html'),
    url(r'^media', MediaViews.index, name='media_index_html_s'),
    # Document views for HTML document items
    url(r'^documents/(?P<uuid>\S+)?\.jsonld$', DocumentViews.jsonld_view, name='documents_jsonld'),
    url(r'^documents/(?P<uuid>\S+)?\.geojson$', DocumentViews.geojson_view, name='documents_geojson'),
    url(r'^documents/(?P<uuid>\S+)?\.json$', DocumentViews.json_view, name='documents_json'),
    url(r'^documents/(?P<uuid>\S+)?\.nt$', DocumentViews.ntrpls_view, name='documents_ntrpls'),
    url(r'^documents/(?P<uuid>\S+)?\.rdf$', DocumentViews.rdf_view, name='documents_rdf'),
    url(r'^documents/(?P<uuid>\S+)?\.ttl$', DocumentViews.turtle_view, name='documents_turtle'),
    url(r'^documents/(?P<uuid>\S+)', DocumentViews.html_view, name='documents_html'),
    url(r'^documents', DocumentViews.index, name='documents_index'),
    # Person views for Person / organization items
    url(r'^persons/(?P<uuid>\S+)?\.jsonld$', PersonViews.jsonld_view, name='persons_jsonld'),
    url(r'^persons/(?P<uuid>\S+)?\.json$', PersonViews.json_view, name='persons_json'),
    url(r'^persons/(?P<uuid>\S+)?\.nt$', PersonViews.ntrpls_view, name='persons_ntrpls'),
    url(r'^persons/(?P<uuid>\S+)?\.rdf$', PersonViews.rdf_view, name='persons_rdf'),
    url(r'^persons/(?P<uuid>\S+)?\.ttl$', PersonViews.turtle_view, name='persons_turtle'),
    url(r'^persons/(?P<uuid>\S+)', PersonViews.html_view, name='persons_html'),
    url(r'^persons', AboutViews.index_view, name='about_index'),
    # Project views for projects
    url(r'^projects/(?P<uuid>\S+)?\.jsonld$', ProjectViews.jsonld_view, name='projects_jsonld'),
    url(r'^projects/(?P<uuid>\S+)?\.geojson$', ProjectViews.geojson_view, name='projects_geojson'),
    url(r'^projects/(?P<uuid>\S+)?\.json$', ProjectViews.json_view, name='projects_json'),
    url(r'^projects/(?P<uuid>\S+)?\.nt$', ProjectViews.ntrpls_view, name='projects_ntrpls'),
    url(r'^projects/(?P<uuid>\S+)?\.rdf$', ProjectViews.rdf_view, name='projects_rdf'),
    url(r'^projects/(?P<uuid>\S+)?\.ttl$', ProjectViews.turtle_view, name='projects_turtle'),
    url(r'^projects/(?P<uuid>\S+)', ProjectViews.html_view, name='projects_html'),
    url(r'^project-layers/(?P<uuid>\S+)', ProjectViews.layers_view, name='projects_layers'),
    url(r'^projects', ProjectViews.index, name='projects_search_html_s'),
    # Predicates views for descriptive variables and linking relations from OC contributors
    url(r'^predicates/(?P<uuid>\S+)?\.jsonld$', PredicateViews.jsonld_view, name='predicates_jsonld'),
    url(r'^predicates/(?P<uuid>\S+)?\.json$', PredicateViews.json_view, name='predicates_json'),
    url(r'^predicates/(?P<uuid>\S+)?\.nt$', PredicateViews.ntrpls_view, name='predicates_ntrpls'),
    url(r'^predicates/(?P<uuid>\S+)?\.rdf$', PredicateViews.rdf_view, name='predicates_rdf'),
    url(r'^predicates/(?P<uuid>\S+)?\.ttl$', PredicateViews.turtle_view, name='predicates_turtle'),
    url(r'^predicates/(?P<uuid>\S+)', PredicateViews.html_view, name='predicates_html'),
    url(r'^predicates', AboutViews.index_view, name='about_index'),
    # Types views for controlled vocabulary entities from OC contributors
    url(r'^types/(?P<uuid>\S+)?\.jsonld$', OCtypeViews.jsonld_view, name='types_jsonld'),
    url(r'^types/(?P<uuid>\S+)\.json$', OCtypeViews.json_view, name='types_json'),
    url(r'^types/(?P<uuid>\S+)?\.nt$', OCtypeViews.ntrpls_view, name='types_ntrpls'),
    url(r'^types/(?P<uuid>\S+)?\.rdf$', OCtypeViews.rdf_view, name='types_rdf'),
    url(r'^types/(?P<uuid>\S+)?\.ttl$', OCtypeViews.turtle_view, name='types_turtle'),
    url(r'^types/(?P<uuid>\S+)', OCtypeViews.html_view, name='types_html'),
    url(r'^types', OCtypeViews.index, name='types_index'),
    # Table views for controlled downloadable tables
    url(r'^tables/(?P<table_id>\S+)\.json$', OCtableViews.json_view, name='tables_json'),
    url(r'^tables/(?P<table_id>\S+)\.csv$', OCtableViews.csv_view, name='tables_csv'),
    url(r'^tables/(?P<table_id>\S+)', OCtableViews.html_view, name='tables_html'),
    url(r'^tables', OCtableViews.index_view, name='tables_index'),
    # Vocabulary views for viewing controlled vocab + ontology entities
    url(r'^vocabularies/(?P<identifier>\S+).json', vocabViews.json_view, name='vocabularies_json'),
    url(r'^vocabularies/(?P<identifier>\S+)', vocabViews.html_view, name='vocabularies_html'),
    url(r'^vocabularies', vocabViews.index_view, name='vocabularies_index'),
    # --------------------------
    # IMPORTER INTERFACE PAGES
    # --------------------------
    url(r'^imports/projects/(?P<project_uuid>\S+)',  Imp_sources.project,
        name='imp_sources_projects'),
    url(r'^imports/field-types/(?P<source_id>\S+)', Imp_sources.field_types,
        name='field_types'),
    url(r'^imports/field-types-more/(?P<source_id>\S+)', Imp_sources.field_types_more,
        name='field_types_more'),
    url(r'^imports/field-entity-relations/(?P<source_id>\S+)', Imp_sources.field_entity_relations,
        name='field_entity_relations'),
    url(r'^imports/field-complex-desciptions/(?P<source_id>\S+)', Imp_sources.field_complex_descriptions,
        name='field_complex_descriptions'),
    url(r'^imports/field-descriptions/(?P<source_id>\S+)', Imp_sources.field_descriptions,
        name='field_descriptions'),
    url(r'^imports/finalize/(?P<source_id>\S+)', Imp_sources.finalize,
        name='imp_source_finalize'),
    # --------------------------
    # IMPORTER PROJECT POST REQUESTS
    # --------------------------
    url(r'^imports/create-project', Imp_sources.create_project,
        name='imp_sources_create_project'),
    url(r'^imports/edit-project/(?P<project_uuid>\S+)', Imp_sources.edit_project,
        name='imp_sources_edit_project'),
    # --------------------------
    # BELOW ARE URLs FOR IMPORTER AJAX REQUESTS
    # --------------------------
    url(r'^imports/project-import-refine/(?P<project_uuid>\S+)', Imp_sources.project_import_refine,
        name='imp_sources_project_import_refine'),
    url(r'^imports/import-finalize/(?P<source_id>\S+)', Imp_sources.import_finalize,
        name='imp_sources_import_finalize'),
    url(r'^imports/field-classify/(?P<source_id>\S+)', Imp_fields.field_classify,
        name='imp_field_classify'),
    url(r'^imports/field-meta-update/(?P<source_id>\S+)', Imp_fields.field_meta_update,
        name='imp_field_meta_update'),
    url(r'^imports/field-titlecase/(?P<source_id>\S+)', Imp_fields.field_titlecase,
        name='imp_field_titlecase'),
    url(r'^imports/field-list/(?P<source_id>\S+)', Imp_fields.field_list,
        name='imp_field_list'),
    url(r'^imports/field-annotations/(?P<source_id>\S+)', Imp_field_annos.view,
        name='imp_field_annos_view'),
    url(r'^imports/subjects-hierarchy-examples/(?P<source_id>\S+)', Imp_field_annos.subjects_hierarchy_examples,
        name='imp_field_annos_subjects_hierarchy_examples'),
    url(r'^imports/field-described-examples/(?P<source_id>\S+)', Imp_field_annos.described_examples,
        name='imp_field_annos_described_examples'),
    url(r'^imports/field-linked-examples/(?P<source_id>\S+)', Imp_field_annos.linked_examples,
        name='imp_field_annos_linked_examples'),
    url(r'^imports/field-annotation-delete/(?P<source_id>\S+)/(?P<annotation_id>\S+)', Imp_field_annos.delete,
        name='imp_field_annos_delete'),
    url(r'^imports/field-annotation-create/(?P<source_id>\S+)', Imp_field_annos.create,
        name='imp_field_annos_create'),
    # --------------------------
    # BELOW IS THE INDEX PAGE FOR THE IMPORTER
    # --------------------------
    url(r'^imports/', Imp_sources.index,
        name='imp_sources_index'),
    # --------------------------
    # BELOW ARE URLs FOR ENTITY EDITS INTERFACE PAGES
    # --------------------------
    url(r'^edit/items/(?P<uuid>\S+)', EditItemViews.html_view,
        name='edit_item_html_view'),
    # --------------------------
    # BELOW ARE URLs FOR ENTITY EDITS AJAX REQUESTS
    # --------------------------
    url(r'^edit/update-item-basics/(?P<uuid>\S+)', EditItemViews.update_item_basics,
        name='edit_item_basics'),
    url(r'^edit/update-predicate-sort-order/(?P<uuid>\S+)', EditItemViews.update_predicate_sort_order,
        name='update_predicate_sort_order'),
    url(r'^edit/update-project-hero/(?P<uuid>\S+)', EditItemViews.update_project_hero,
        name='edit_update_project_hero'),
    url(r'^edit/update-media-file/(?P<uuid>\S+)', EditItemViews.update_media_file,
        name='edit_update_media_file'),
    url(r'^edit/add-edit-item-containment/(?P<uuid>\S+)', EditItemViews.add_edit_item_containment,
        name='edit_add_edit_item_containment'),
    url(r'^edit/add-edit-item-assertion/(?P<uuid>\S+)', EditItemViews.add_edit_item_assertion,
        name='edit_add_edit_item_assertion'),
    url(r'^edit/add-edit-string-translation/(?P<string_uuid>\S+)',
        EditItemViews.add_edit_string_translation,
        name='edit_add_edit_string_translation'),
    url(r'^edit/sort-item-assertion/(?P<uuid>\S+)', EditItemViews.sort_item_assertion,
        name='edit_sort_item_assertion'),
    url(r'^edit/delete-item-assertion/(?P<uuid>\S+)', EditItemViews.delete_item_assertion,
        name='edit_delete_item_assertion'),
    url(r'^edit/html-validate/', EditItemViews.html_validate,
        name='edit_html_validate'),
    url(r'^edit/add-item-annotation/(?P<uuid>\S+)', EditItemViews.add_item_annotation,
        name='add_item_annotation'),
    url(r'^edit/add-item-stable-id/(?P<uuid>\S+)', EditItemViews.add_item_stable_id,
        name='add_item_stable_id'),
    url(r'^edit/delete-item-stable-id/(?P<uuid>\S+)', EditItemViews.delete_item_stable_id,
        name='delete_item_stable_id'),
    url(r'^edit/edit-annotation/(?P<entity_id>\S+)', EditItemViews.edit_annotation,
        name='edit_annotation'),
    url(r'^edit/delete-annotation/(?P<entity_id>\S+)', EditItemViews.delete_annotation,
        name='delete_annotation'),
    url(r'^edit/create-item-into/(?P<project_uuid>\S+)', EditItemViews.create_item_into,
        name='create_item_into'),
    url(r'^edit/check-delete-item/(?P<uuid>\S+)', EditItemViews.check_delete_item,
        name='check_delete_item'),
    url(r'^edit/delete-item/(?P<uuid>\S+)', EditItemViews.delete_item,
        name='delete_item'),
    url(r'^edit/create-project', EditItemViews.create_project,
        name='create_project'),
    url(r'^edit/add-update-ld-entity', EditItemViews.add_update_ld_entity,
        name='add_update_ld_entity'),
    url(r'^edit/add-update-geo-data/(?P<uuid>\S+)', EditItemViews.add_update_geo_data,
        name='add_update_geo_data'),
    url(r'^edit/add-update-project-geo/(?P<uuid>\S+)', EditItemViews.add_update_project_geo,
        name='add_update_project_geo'),
    url(r'^edit/add-update-date-range/(?P<uuid>\S+)', EditItemViews.add_update_date_range,
        name='add_update_date_range'),
    url(r'^edit/delete-date-range/(?P<uuid>\S+)', EditItemViews.delete_date_range,
        name='delete_date_range'),
    url(r'^edit/projects/(?P<project_uuid>\S+)', EditProjectsViews.status,
        name='edit_projects_status'),
    # --------------------------
    # BELOW ARE URLs FOR INPUT PROFILE RELATED AJAX REQUESTS
    # --------------------------
    url(r'^edit/inputs/profiles/(?P<profile_uuid>\S+).json', InputProfileViews.json_view,
        name='edit_input_profile_json_view'),
    url(r'^edit/inputs/profiles/(?P<profile_uuid>\S+)/edit', InputProfileViews.profile_edit,
        name='edit_input_profile_edit'),
    url(r'^edit/inputs/profiles/(?P<profile_uuid>\S+)/(?P<edit_uuid>\S+)', InputProfileViews.profile_use,
        name='edit_input_profile_use'),
    url(r'^edit/inputs/create-update-profile-item/(?P<profile_uuid>\S+)/(?P<edit_uuid>\S+)',
        InputProfileViews.create_update_profle_item,
        name='edit_input_profile_create_update_profle_item'),
    url(r'^edit/inputs/profile-item-list/(?P<profile_uuid>\S+)', InputProfileViews.profile_item_list,
        name='edit_input_profile_item_list'),
    url(r'^edit/inputs/create-profile/(?P<project_uuid>\S+)', InputProfileViews.create,
        name='edit_input_profile_create'),
    url(r'^edit/inputs/update-profile/(?P<profile_uuid>\S+)', InputProfileViews.update,
        name='edit_input_profile_update'),
    url(r'^edit/inputs/delete-profile/(?P<profile_uuid>\S+)', InputProfileViews.delete,
        name='edit_input_profile_delete'),
    url(r'^edit/inputs/duplicate-profile/(?P<profile_uuid>\S+)', InputProfileViews.duplicate,
        name='edit_input_profile_duplicate'),
    url(r'^edit/inputs/create-field-group/(?P<profile_uuid>\S+)', InputProfileViews.create_field_group,
        name='edit_input_create_field_group'),
    url(r'^edit/inputs/update-field-group/(?P<fgroup_uuid>\S+)', InputProfileViews.update_field_group,
        name='edit_input_update_field_group'),
    url(r'^edit/inputs/delete-field-group/(?P<fgroup_uuid>\S+)', InputProfileViews.delete_field_group,
        name='edit_input_delete_field_group'),
    url(r'^edit/inputs/create-field/(?P<fgroup_uuid>\S+)', InputProfileViews.create_field,
        name='edit_input_create_field'),
    url(r'^edit/inputs/update-field/(?P<field_uuid>\S+)', InputProfileViews.update_field,
        name='edit_input_update_field'),
    url(r'^edit/inputs/delete-field/(?P<field_uuid>\S+)', InputProfileViews.delete_field,
        name='edit_input_delete_field'),
    url(r'^edit/inputs/reorder-item/(?P<uuid>\S+)', InputProfileViews.reorder_item,
        name='edit_input_reorder_item'),
    url(r'^edit/inputs/item-label-check/(?P<project_uuid>\S+)', InputProfileViews.label_check,
        name='edit_input_label_check'),
    url(r'^edit/inputs/(?P<project_uuid>\S+).json', InputProfileViews.index_json,
        name='edit_input_index_json'),
    # --------------------------
    # EDITING ROOT
    # --------------------------
    url(r'^edit/', EditProjectsViews.index,
        name='edit_projects_index'),
    # --------------------------
    # --------------------------
    # BELOW ARE URLs FOR ENTITY LOOKUP AJAX REQUESTS
    # --------------------------
    url(r'^entities/hierarchy-children/(?P<identifier>\S+)', EntityViews.hierarchy_children,
        name='entity_hierarchy_children'),
    url(r'^entities/id-summary/(?P<identifier>\S+)', EntityViews.id_summary,
        name='entity_id_summary'),
    url(r'^entities/look-up/(?P<item_type>\S+)', EntityViews.look_up,
        name='entity_look_up'),
    url(r'^entities/annotations/(?P<subject>\S+)', EntityViews.entity_annotations,
        name='entity_annotations'),
    url(r'^entities/contain-children/(?P<identifier>\S+)', EntityViews.contain_children,
        name='entity_contain_children'),
    url(r'^entities/description-children/(?P<identifier>\S+)', EntityViews.description_hierarchy,
        name='entity_description_hierarchy'),
    url(r'^entities/proxy/(?P<target_url>\S+)', EntityViews.proxy,
        name='entity_proxy'),
    url(r'^entities/proxy-header/(?P<target_url>\S+)', EntityViews.proxy_header,
        name='entity_proxy_header'),
    # testing for new item json generation
    url(r'^items/(?P<identifier>\S+).json', EntityViews.items_json, name='items_json'),
    #----------------------------
    # BELOW ARE OAI REQUESTS (OAIviews)
    #----------------------------
    url(r'^oai/', OAIviews.index, name='oai_index'),
    #----------------------------
    # BELOW ARE PELAGIOS REQUESTS (PelagiosViews)
    #----------------------------
    url(r'^pelagios/void', PelagiosViews.void, name='pelagios_void'),
    url(r'^pelagios/void.ttl', PelagiosViews.void_ttl, name='pelagios_void_ttl'),
    url(r'^pelagios/gazetteer', PelagiosViews.gazetteer, name='pelagios_gaz'),
    url(r'^pelagios/gazetteer.ttl', PelagiosViews.gazetteer_ttl, name='pelagios_gaz_ttl'),
    url(r'^pelagios/data/(?P<identifier>\S+)?.ttl',
        PelagiosViews.project_annotations_ttl,
        name='pelagios_proj_ttl'),
    url(r'^pelagios/data/(?P<identifier>\S+)',
        PelagiosViews.project_annotations,
        name='pelagios_proj'),
    #----------------------------
    # BELOW ARE UTILITIES REQUESTS (UtilitiesViews)
    #----------------------------
    url(r'^utilities/meters-to-lat-lon', UtilitiesViews.meters_to_lat_lon, name='meters_to_lat_lon'),
    url(r'^utilities/lat-lon-to-quadtree', UtilitiesViews.lat_lon_to_quadtree, name='lat_lon_to_quadtree'),
    url(r'^utilities/quadtree-to-lat-lon', UtilitiesViews.quadtree_to_lat_lon, name='quadtree_to_lat_lon'),
    url(r'^utilities/reproject', UtilitiesViews.reproject, name='utilities_reproject'),
    url(r'^utilities/human-remains-ok', UtilitiesViews.human_remains_ok, name='human_remains_ok'),
    #----------------------------
    # BELOW ARE INDEX REQUESTS
    #----------------------------
    # robots.text route
    url(r'^robots.txt', HomeViews.robots, name='home_robots'),
    # Index, home-page route
    url(r'^$', HomeViews.index, name='home_index'),
    # Admin route
    url(r'^admin/', admin.site.urls)]
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
if settings.DEBUG:
    import debug_toolbar
    urlpatterns += [url(r'^__debug__/', include(debug_toolbar.urls))]
