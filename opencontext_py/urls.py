from django.conf.urls import patterns, include, url
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
admin.autodiscover()

from opencontext_py.apps.index import views as HomeViews
from opencontext_py.apps.about import views as AboutViews
from opencontext_py.apps.contexts import views as ContextViews
from opencontext_py.apps.ocitems.subjects import views as SubjectViews
from opencontext_py.apps.ocitems.mediafiles import views as MediaViews
from opencontext_py.apps.ocitems.documents import views as DocumentViews
from opencontext_py.apps.ocitems.persons import views as PersonViews
from opencontext_py.apps.ocitems.projects import views as ProjectViews
from opencontext_py.apps.ocitems.predicates import views as PredicateViews
from opencontext_py.apps.ocitems.octypes import views as OCtypeViews
from opencontext_py.apps.searcher.sets import views as SetsViews
from opencontext_py.apps.entities.entity import views as EntityViews
from opencontext_py.apps.edit.items import views as EditItemViews
from opencontext_py.apps.edit.projects import views as EditProjectsViews
from opencontext_py.apps.edit.inputs import views as InputProfileViews
from opencontext_py.apps.imports.sources import views as Imp_sources
from opencontext_py.apps.imports.fields import views as Imp_fields
from opencontext_py.apps.imports.fieldannotations import views as Imp_field_annos

urlpatterns = patterns('',
                       # Examples:
                       # url(r'^$', 'opencontext_py.views.home', name='home'),
                       # url(r'^blog/', include('blog.urls')),
                       # About pages
                       url(r'^about/uses', AboutViews.uses_view, name='about_uses'),
                       url(r'^about/publishing', AboutViews.pub_view, name='about_publishing'),
                       url(r'^about/estimate', AboutViews.estimate_view, name='about_estimate'),
                       url(r'^about/concepts', AboutViews.concepts_view, name='about_concepts'),
                       url(r'^about/technology', AboutViews.tech_view, name='about_technology'),
                       url(r'^about/recipes', AboutViews.recipes_view, name='about_recipes'),
                       url(r'^about/services', AboutViews.services_view, name='about_services'),
                       url(r'^about/', AboutViews.index_view, name='about_index'),
                       # Contexts for JSON-LD
                       url(r'^contexts/item.json', ContextViews.item_view, name='context_item'),
                       url(r'^contexts/search.json', ContextViews.search_view, name='context_search'),
                       url(r'^contexts', AboutViews.index_view, name='about_index'),
                       # Subjects views for main records (subjects of observations)
                       url(r'^subjects/(?P<uuid>\S+).json', SubjectViews.json_view, name='subjects_json'),
                       url(r'^subjects/(?P<uuid>\S+)', SubjectViews.html_view, name='subjects_html'),
                       # url(r'^subjects', SubjectViews.index, name='subjects_index'),
                       url(r'^subjects', AboutViews.index_view, name='about_index'),
                       # Sets views
                       url(r'^sets/(?P<spatial_context>\S+)?.json', SetsViews.json_view, name='sets_json'),
                       url(r'^sets/(?P<spatial_context>\S+)?', SetsViews.html_view, name='sets_html'),
                       # Media views (media resources / metadata + binary files)
                       url(r'^media/(?P<uuid>\S+).json', MediaViews.json_view, name='media_json'),
                       url(r'^media/(?P<uuid>\S+)/full', MediaViews.html_full, name='media_full'),
                       url(r'^media/(?P<uuid>\S+)', MediaViews.html_view, name='media_html'),
                       # url(r'^media', MediaViews.index, name='media_index'),
                       url(r'^media', AboutViews.index_view, name='about_index'),
                       # Document views for HTML document items
                       url(r'^documents/(?P<uuid>\S+).json', DocumentViews.json_view, name='documents_json'),
                       url(r'^documents/(?P<uuid>\S+)', DocumentViews.html_view, name='documents_html'),
                       # url(r'^documents', DocumentViews.index, name='documents_index'),
                       url(r'^documents', AboutViews.index_view, name='about_index'),
                       # Person views for Person / organization items
                       url(r'^persons/(?P<uuid>\S+).json', PersonViews.json_view, name='persons_json'),
                       url(r'^persons/(?P<uuid>\S+)', PersonViews.html_view, name='persons_html'),
                       # url(r'^persons', PersonViews.index, name='persons_index'),
                       url(r'^persons/(?P<uuid>\S+)', AboutViews.index_view, name='about_index'),
                       url(r'^persons', AboutViews.index_view, name='about_index'),
                       # Project views for projects
                       url(r'^projects/.json', ProjectViews.index_json, name='projects_index_json'),
                       url(r'^projects.json', ProjectViews.index_json, name='projects_index_json'),
                       url(r'^projects/(?P<uuid>\S+).json', ProjectViews.json_view, name='projects_json'),
                       url(r'^projects/(?P<uuid>\S+)', ProjectViews.html_view, name='projects_html'),
                       url(r'^projects', ProjectViews.index, name='projects_index'),
                       # url(r'^projects', AboutViews.index_view, name='about_index'),
                       # Predicates views for descriptive variables and linking relations from OC contributors
                       url(r'^predicates/(?P<uuid>\S+).json', PredicateViews.json_view, name='predicates_json'),
                       url(r'^predicates/(?P<uuid>\S+)', PredicateViews.html_view, name='predicates_html'),
                       # url(r'^predicates', PredicateViews.index, name='predicates_index'),
                       url(r'^predicates', AboutViews.index_view, name='about_index'),
                       # Types views for controlled vocabulary entities from OC contributors
                       url(r'^types/(?P<uuid>\S+).json', OCtypeViews.json_view, name='types_json'),
                       url(r'^types/(?P<uuid>\S+)', OCtypeViews.html_view, name='types_html'),
                       # url(r'^types', OCtypeViews.index, name='types_index'),
                       url(r'^types', AboutViews.index_view, name='about_index'),
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
                       url(r'^edit/create-project', EditItemViews.create_project,
                           name='create_project'),
                       url(r'^edit/add-update-ld-entity', EditItemViews.add_update_ld_entity,
                           name='add_update_ld_entity'),
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
                       url(r'^entities/look-up/(?P<item_type>\S+)', EntityViews.look_up,
                           name='entity_look_up'),
                       url(r'^entities/annotations/(?P<subject>\S+)', EntityViews.entity_annotations,
                           name='entity_annotations'),
                       url(r'^entities/contain-children/(?P<identifier>\S+)', EntityViews.contain_children,
                           name='entity_contain_children'),
                       url(r'^entities/description-children/(?P<identifier>\S+)', EntityViews.description_hierarchy,
                           name='entity_description_hierarchy'),
                       #----------------------------
                       # BELOW ARE INDEX REQUESTS
                       #----------------------------
                       # robots.text route
                       url(r'^robots.txt', HomeViews.robots, name='home_robots'),
                       # Index, home-page route
                       url(r'^$', HomeViews.index, name='home_index'),
                       # Admin route
                       url(r'^admin/', include(admin.site.urls)),
                       ) + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
if settings.DEBUG:
    import debug_toolbar
    urlpatterns += patterns('',
                            url(r'^__debug__/', include(debug_toolbar.urls)),
                            )
