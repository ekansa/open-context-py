from django.conf.urls import patterns, include, url

from django.contrib import admin
admin.autodiscover()

from opencontext_py.apps.subjects import views as SubjectViews

urlpatterns = patterns('',
                       # Examples:
                       # url(r'^$', 'opencontext_py.views.home', name='home'),
                       # url(r'^blog/', include('blog.urls')),
                       url(r'^subjects/(?P<uuid>\S+).json', SubjectViews.json_view, name='json_view'),
                       url(r'^subjects/(?P<uuid>\S+)', SubjectViews.html_view, name='html_view'),
                       url(r'^subjects', SubjectViews.index, name='index'),
                       url(r'^admin/', include(admin.site.urls)),
                       )
