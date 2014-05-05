from django.conf.urls import patterns, include, url

from django.contrib import admin
admin.autodiscover()

from opencontext_py.apps.subjects import views as subjectViews

urlpatterns = patterns('',
                       # Examples:
                       # url(r'^$', 'opencontext_py.views.home', name='home'),
                       # url(r'^blog/', include('blog.urls')),
                       url(r'^subjects/(?P<uuid>\S+).json', subjectViews.jsonView, name='jsonView'),
                       url(r'^subjects/(?P<uuid>\S+)', subjectViews.htmlView, name='htmlView'),
                       url(r'^subjects', subjectViews.index, name='index'),
                       url(r'^admin/', include(admin.site.urls)),
                       )
