from django.conf.urls import patterns, include, url
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
admin.autodiscover()

from opencontext_py.apps.ocitems.subjects import views as SubjectViews
from opencontext_py.apps.ocitems.mediafiles import views as MediaViews
from opencontext_py.apps.ocitems.documents import views as DocumentViews
from opencontext_py.apps.ocitems.persons import views as PersonViews
from opencontext_py.apps.ocitems.projects import views as ProjectViews
from opencontext_py.apps.ocitems.predicates import views as PredicateViews
from opencontext_py.apps.ocitems.octypes import views as OCtypeViews
from opencontext_py.apps.searcher.sets import views as SetsViews


urlpatterns = patterns('',
                       # Examples:
                       # url(r'^$', 'opencontext_py.views.home', name='home'),
                       # url(r'^blog/', include('blog.urls')),
                       # Subjects views for main records (subjects of observations)
                       url(r'^subjects/(?P<uuid>\S+).json', SubjectViews.json_view, name='subjects_json'),
                       url(r'^subjects/(?P<uuid>\S+)', SubjectViews.html_view, name='subjects_html'),
                       url(r'^subjects', SubjectViews.index, name='subjects_index'),
                       # Sets views
                       url(r'^sets/(?P<spatial_context>\S+)?.json', SetsViews.json_view, name='sets_json'),
                       url(r'^sets/(?P<spatial_context>\S+)?', SetsViews.html_view, name='sets_html'),
                       # Media views (media resources / metadata + binary files)
                       url(r'^media/(?P<uuid>\S+).json', MediaViews.json_view, name='media_json'),
                       url(r'^media/(?P<uuid>\S+)', MediaViews.html_view, name='media_html'),
                       url(r'^media', MediaViews.index, name='media_index'),
                       # Document views for HTML document items
                       url(r'^documents/(?P<uuid>\S+).json', DocumentViews.json_view, name='documents_json'),
                       url(r'^documents/(?P<uuid>\S+)', DocumentViews.html_view, name='documents_html'),
                       url(r'^documents', DocumentViews.index, name='documents_index'),
                       # Person views for Person / organization items
                       url(r'^persons/(?P<uuid>\S+).json', PersonViews.json_view, name='persons_json'),
                       url(r'^persons/(?P<uuid>\S+)', PersonViews.html_view, name='persons_html'),
                       url(r'^persons', PersonViews.index, name='persons_index'),
                       # Project views for projects
                       url(r'^projects/(?P<uuid>\S+).json', ProjectViews.json_view, name='projects_json'),
                       url(r'^projects/(?P<uuid>\S+)', ProjectViews.html_view, name='projects_html'),
                       url(r'^projects', ProjectViews.index, name='projects_index'),
                       # Predicates views for descriptive variables and linking relations from OC contributors
                       url(r'^predicates/(?P<uuid>\S+).json', PredicateViews.json_view, name='predicates_json'),
                       url(r'^predicates/(?P<uuid>\S+)', PredicateViews.html_view, name='predicates_html'),
                       url(r'^predicates', PredicateViews.index, name='predicates_index'),
                       # Types views for controlled vocabulary entities from OC contributors
                       url(r'^types/(?P<uuid>\S+).json', OCtypeViews.json_view, name='types_json'),
                       url(r'^types/(?P<uuid>\S+)', OCtypeViews.html_view, name='types_html'),
                       url(r'^types', OCtypeViews.index, name='types_index'),
                       # Admin route
                       url(r'^admin/', include(admin.site.urls)),
                       ) + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
if settings.DEBUG:
    import debug_toolbar
    urlpatterns += patterns('',
                            url(r'^__debug__/', include(debug_toolbar.urls)),
                            )
