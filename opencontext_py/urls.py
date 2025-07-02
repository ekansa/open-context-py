from django.urls import include, re_path, path
from django.conf import settings
from django.contrib import admin
admin.autodiscover()

from opencontext_py.apps.index import views as HomeViews
from opencontext_py.apps.ocitems.manifest import views as ManifestViews
from opencontext_py.apps.about import views as AboutViews
from opencontext_py.apps.contexts import views as ContextViews

from opencontext_py.apps.utilities import views as UtilitiesViews
from opencontext_py.apps.entities.entity import views as EntityViews

# New Open Context highlights page
from opencontext_py.apps.highlights import views as HighlightsViews

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

# Testing new ETL views. These are for GET requests
from opencontext_py.apps.etl.kobo import views as koboViews

# OAI PMH views
from opencontext_py.apps.oai import views as oaiViews

# Site map related
from opencontext_py.apps.all_items.sitemaps import views as oc_sitemap_views
from django.views.decorators.cache import cache_page


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

    # Endpoint for the open archives initiative protocol for metadata harvesting
    re_path(r'^oai/', oaiViews.index, name='oai_pmh_index_view'),

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
    re_path(r'^about/fair-care', AboutViews.fair_care_view, name='about_fair_care'),
    re_path(r'^about/people', AboutViews.people_view, name='about_people'),
    re_path(r'^about/sponsors', AboutViews.sponsors_view, name='about_sponsors'),
    re_path(r'^about/terms', AboutViews.terms_view, name='about_terms'),
    re_path(r'^about/', AboutViews.index_view, name='about_index'),
    # Highlights
    re_path(r'^highlights/', HighlightsViews.index_view, name='highlights_index'),

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
    re_path(r'^map-projects.json', NewSearchViews.projects_geojson, name='map_projects_geojson'),
    re_path(r'^query.json?', NewSearchViews.query_json, name='new_search_json_d'),
    re_path(r'^query/(?P<spatial_context>\S+)?.json', NewSearchViews.query_json, name='new_search_json'),
    re_path(r'^query/(?P<spatial_context>\S+)?', NewSearchViews.query_html, name='new_search_html'),

    # Projects index searches
    re_path(r'^projects-index/(?P<spatial_context>\S+)?.json', NewSearchViews.projects_index_json, name='projects_index_json'),
    re_path(r'^projects-index/(?P<spatial_context>\S+)?', NewSearchViews.projects_index_html, name='projects_index_html'),

    # redirects
    re_path(r'^projects-search/(?P<spatial_context>\S+)?', NewSearchViews.old_projects_search_html, name='old_projects_search_html'),
    re_path(r'^search/(?P<spatial_context>\S+)?', NewSearchViews.old_search_html, name='old_search_html'),
    re_path(r'^subjects-search/(?P<spatial_context>\S+)?', NewSearchViews.old_subjects_search_html, name='old_subjects_search_html'),
    re_path(r'^media-search/(?P<spatial_context>\S+)?', NewSearchViews.old_media_search_html, name='old_media_search_html'),

    # New attribute-group dereference
    re_path(r'^attribute-groups/(?P<uuid>\S+)?\.json$', AllItemsViews.all_items_json, name='attribute_groups_json'),
    re_path(r'^attribute-groups/(?P<uuid>\S+)', AllItemsViews.all_items_html, name='attribute_groups'),

    # Testing for all manifest items
    re_path(r'^all-items/(?P<uuid>\S+)?\.json$', AllItemsViews.all_items_json, name='all_items_json'),
    re_path(r'^all-items/(?P<uuid>\S+)/full', AllItemsViews.all_items_html_full, name='all_items_full'),
    re_path(r'^all-items/(?P<uuid>\S+)', AllItemsViews.all_items_html, name='all_items_html'),
    re_path(r'^all-items-solr/(?P<uuid>\S+)', AllItemsViews.make_solr_doc_in_html, name='all_items_solr_html'),

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
    re_path(r'^editorial/reconcile-term', EditorialViews.reconcile_term_json, name='editorial_reconcile_term'),
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
    re_path(
        r'^editorial/item-reindex',
        EditorialItemViews.reindex_manifest_objs,
        name='editorial_item_reindex'
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
    # Predicates views for descriptive variables and linking relations from OC contributors
    re_path(r'^predicates/(?P<uuid>\S+)?\.jsonld$', AllItemsViews.predicates_json, name='predicates_jsonld'),
    re_path(r'^predicates/(?P<uuid>\S+)?\.json$', AllItemsViews.predicates_json, name='predicates_json'),
    re_path(r'^predicates/(?P<uuid>\S+)', AllItemsViews.predicates_html, name='predicates_html'),
    re_path(r'^predicates', AboutViews.index_view, name='about_index'),
    # Types views for controlled vocabulary entities from OC contributors
    re_path(r'^types/(?P<uuid>\S+)?\.jsonld$',  AllItemsViews.types_json, name='types_jsonld'),
    re_path(r'^types/(?P<uuid>\S+)\.json$', AllItemsViews.types_json, name='types_json'),
    re_path(r'^types/(?P<uuid>\S+)', AllItemsViews.types_html, name='types_html'),
    re_path(r'^types', AboutViews.index_view, name='about_index'),
    # Table views for controlled downloadable tables
    # re_path(r'^tables/(?P<table_id>\S+)\.json$', OCtableViews.json_view, name='tables_json'),
    # re_path(r'^tables/(?P<table_id>\S+)\.csv$', OCtableViews.csv_view, name='tables_csv'),
    # re_path(r'^tables/(?P<table_id>\S+)', OCtableViews.html_view, name='tables_html'),
    # re_path(r'^tables', OCtableViews.index_view, name='tables_index'),
    re_path(r'^tables/(?P<uuid>\S+)?\.jsonld$',  AllItemsViews.tables_json, name='tables_jsonld'),
    re_path(r'^tables/(?P<uuid>\S+)\.json$', AllItemsViews.tables_json, name='tables_json'),
    re_path(r'^tables/(?P<uuid>\S+)\.csv$', AllItemsViews.tables_csv, name='tables_csv'),
    re_path(r'^tables/(?P<uuid>\S+)', AllItemsViews.tables_html, name='tables_html'),
    re_path(r'^types', AboutViews.index_view, name='about_index'),
    # Vocabulary views for viewing controlled vocab + ontology entities
    re_path(r'^vocabularies/(?P<identifier>\S+).json', AllItemsViews.vocabularies_json, name='vocabularies_json'),
    re_path(r'^vocabularies/(?P<identifier>\S+)', AllItemsViews.vocabularies_html, name='vocabularies_html'),

    #----------------------------
    # BELOW ARE UTILITIES REQUESTS (UtilitiesViews)
    #----------------------------
    re_path(r'^utilities/geospace-outliers-within', UtilitiesViews.geospace_outliers_within, name='utilities_geospace_outliers_within'),
    re_path(r'^utilities/check-geospace-contains', UtilitiesViews.check_geospace_contains, name='utilities_check_geospace_contains'),
    re_path(r'^utilities/meters-to-lat-lon', UtilitiesViews.meters_to_lat_lon, name='meters_to_lat_lon'),
    re_path(r'^utilities/lat-lon-to-quadtree', UtilitiesViews.lat_lon_to_quadtree, name='lat_lon_to_quadtree'),
    re_path(r'^utilities/quadtree-to-lat-lon', UtilitiesViews.quadtree_to_lat_lon, name='quadtree_to_lat_lon'),
    re_path(r'^utilities/reproject', UtilitiesViews.reproject, name='utilities_reproject'),
    re_path(r'^utilities/human-remains-ok', UtilitiesViews.human_remains_ok, name='human_remains_ok'),
    re_path(r'^utilities/geonames-geojson/(?P<geonames_uri>\S+)', UtilitiesViews.geonames_geojson, name='geonames_geojson'),
    re_path(r'^utilities/uuid', UtilitiesViews.uuid, name='utilities_uuid'),

    #----------------------------
    # BELOW ARE KOBO Requests
    #----------------------------
    re_path(r'^kobo/submissions', koboViews.submissions_kobo_proxy, name='submissions_kobo_proxy'),

    #----------------------------
    # ENTITIES PROXY views
    #----------------------------
    re_path(r'^entities/proxy/(?P<target_url>\S+)', EntityViews.proxy, name='entities_proxy'),
    re_path(r'^entities/proxy-header/(?P<target_url>\S+)', EntityViews.proxy_header, name='entities_proxy_header'),
    #----------------------------
    # BELOW ARE SITEMAP REQUESTS
    #----------------------------
    re_path(
        r'^sitemap\.xml$',
        oc_sitemap_views.sitemap_index,
        name='sitemapindex'
    ),
    re_path(
        r'^sitemap-(?P<section>.+)\.xml$',
        oc_sitemap_views.project_section_sitemap,
        name='project_section_sitemap'
    ),
    #----------------------------
    # BELOW ARE INDEX REQUESTS
    #----------------------------
    # robots.text route
    re_path(r'^robots.txt', HomeViews.robots, name='home_robots'),
    # Index, home-page route
    re_path(r'^$', HomeViews.index, name='home_index'),
    # Admin route
    # re_path('oc-admin/', admin.site.urls),
    re_path(r'^admin/', admin.site.urls),
]

# how do we fix this?
# urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

if settings.DEBUG:
    import debug_toolbar
    urlpatterns += [path('__debug__/', include(debug_toolbar.urls))]
