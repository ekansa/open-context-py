from django.conf.urls import patterns, include, url

from django.contrib import admin
admin.autodiscover()

from opencontext_py.apps.ocitems.subjects import views as SubjectViews
from opencontext_py.apps.ocitems.mediafiles import views as MediaViews
from opencontext_py.apps.ocitems.documents import views as DocumentViews
from opencontext_py.apps.ocitems.predicates import views as PredicateViews
from opencontext_py.apps.ocitems.octypes import views as OCtypeViews

urlpatterns = patterns('',
                       # Examples:
                       # url(r'^$', 'opencontext_py.views.home', name='home'),
                       # url(r'^blog/', include('blog.urls')),
                       # Subjects views for main records (subjects of observations)
                       url(r'^subjects/(?P<uuid>\S+).json', SubjectViews.json_view, name='json_view'),
                       url(r'^subjects/(?P<uuid>\S+)', SubjectViews.html_view, name='html_view'),
                       url(r'^subjects', SubjectViews.index, name='index'),
                       # Media views (media resources / metadata + binary files)
                       url(r'^media/(?P<uuid>\S+).json', MediaViews.json_view, name='json_view'),
                       url(r'^media/(?P<uuid>\S+)', MediaViews.html_view, name='html_view'),
                       url(r'^media', MediaViews.index, name='index'),
                       # Document views for HTML document items
                       url(r'^documents/(?P<uuid>\S+).json', DocumentViews.json_view, name='json_view'),
                       url(r'^documents/(?P<uuid>\S+)', DocumentViews.html_view, name='html_view'),
                       url(r'^documents', DocumentViews.index, name='index'),
                       # Predicates views for descriptive variables and linking relations from OC contributors
                       url(r'^predicates/(?P<uuid>\S+).json', PredicateViews.json_view, name='json_view'),
                       url(r'^predicates/(?P<uuid>\S+)', PredicateViews.html_view, name='html_view'),
                       url(r'^predicates', PredicateViews.index, name='index'),
                       # Types views for controlled vocabulary entities from OC contributors
                       url(r'^types/(?P<uuid>\S+).json', OCtypeViews.json_view, name='json_view'),
                       url(r'^types/(?P<uuid>\S+)', OCtypeViews.html_view, name='html_view'),
                       url(r'^types', OCtypeViews.index, name='index'),
                       # Admin route
                       url(r'^admin/', include(admin.site.urls)),
                       )
