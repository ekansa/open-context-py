import json
from django.conf import settings
from django.http import HttpResponse, Http404
from django.shortcuts import redirect

from django.template import loader

from django.template.response import TemplateResponse
from django.contrib.sitemaps import Sitemap

from opencontext_py.apps.all_items.sitemaps import site_data

from django.views.decorators.cache import never_cache


from opencontext_py.libs.rootpath import RootPath
from opencontext_py.apps.all_items.sitemaps import site_data


if settings.DEBUG:
    SITEMAP_XML_DOC_CACHE_TIMEOUT = 0 # don't cache
else:
    SITEMAP_XML_DOC_CACHE_TIMEOUT = 60 * 60 * 48 # Two days


@never_cache
def sitemap_index(request):
    """A sitemap index listing sitemaps for each public, indexed project"""
    rp = RootPath()
    base_url = rp.get_baseurl()
    sitemaps = []
    project_slug_counts, max_count = site_data.get_cache_solr_indexed_project_slugs(
        reset_cache=request.GET.get('reset', False)
    )
    for proj_slug, proj_count in project_slug_counts:
        proj_obj = site_data.get_index_sitemap_item_for_proj_slug(
            proj_slug=proj_slug,
            proj_count=proj_count,
            max_count=max_count,
        )
        if not proj_obj:
            continue
        site = f'{base_url}/sitemap-{proj_obj.slug}.xml'
        sitemaps.append(site)
    return TemplateResponse(
        request,
        'sitemap_index.xml',
        {"sitemaps": sitemaps},
        content_type='application/xml',
        headers=None,
    )


@never_cache
def project_section_sitemap(request, section):
    """A sitemap for a specific project"""
    proj_slug = None
    proj_count = None
    project_slug_counts, max_count = site_data.get_cache_solr_indexed_project_slugs(
        reset_cache=request.GET.get('reset', False)
    )
    for act_proj_slug, act_proj_count in project_slug_counts:
        if act_proj_slug == section:
            proj_slug = act_proj_slug
            proj_count = act_proj_count
            break
    if not proj_slug:
        raise Http404
    rep_man_objs = site_data.get_sitemap_items_for_proj_slug(
        proj_slug=proj_slug,
        proj_count=proj_count,
        max_count=max_count,
        reset_proj_item_index=request.GET.get('reset', False),
    )
    rp = RootPath()
    base_url = rp.get_baseurl()
    urlset = []
    for man_obj in rep_man_objs:
        url = {
            'location': f'{base_url}{man_obj.url}',
            'lastmod':  man_obj.updated,
            'priority': man_obj.sitemap_priority,
        }
        urlset.append(url)
    return TemplateResponse(
        request,
        'sitemap.xml',
        {"urlset": urlset},
        content_type='application/xml',
        headers=None,
    )