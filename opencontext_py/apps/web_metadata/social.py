import copy

from django.conf import settings

from opencontext_py.apps.all_items.representations.rep_utils import get_hero_banner_url


DEFAULT_SOCIAL_META_DICT = {
    'title': {
        'property': 'og:title',
        'content': 'Open Context',
    },
    'type': {
        'property': 'og:type',
        'content': 'website',
    },
    'image': {
        'property': 'og:image',
        'content': f'https://{settings.CANONICAL_BASE_URL}/static/oc/images/index/oc-blue-square-logo.png',
    },
    'image_secure_url': {
        'property': 'og:image:secure_url',
        'content': f'https://{settings.CANONICAL_BASE_URL}/static/oc/images/index/oc-blue-square-logo.png',
    },
    'image_alt': {
        'property': 'og:image:alt',
        'content': 'The Open Context logo',
    },
    'url': {
        'property': 'og:url',
        'content': f'https://{settings.CANONICAL_BASE_URL}',
    },
    'description': {
        'property': 'og:description',
        'content': (
            'Open Context publishes archaeological and related research data, '
            'images, maps, field notes, 3D models, and more. This information '
            'richly describes excavations, surveys, and collections from across the '
            'globe and even outer-space.'
        ),
    },
    'site': {
        'property': 'twitter:site',
        'content': 'Open Context: Publishing research data in archaeology and related fields',
    },

}

QUERY_CONFIG = {
    'title': {
        'property': 'og:title',
        'content': 'Open Context: Search (Query) Results',
    },
    'description': {
        'property': 'og:description',
        'content': (
            'Open Context enables you to search within and between archaeological datasets '
            'contributed by researchers working across the world. '
        ),
    },
}

PATH_CONFIGS = {
    '/about/': {
        'title': {
            'property': 'og:title',
            'content': 'About Open Context',
        },
        'description': {
            'property': 'og:description',
            'content': (
                'Watch a quick 1 minute video introduction about how Open Context reviews, '
                'edits, annotates, publishes and archives research data and digital documentation.'
            ),
        },
        'video': {
            'property': 'og:video',
            # Use the Youtube link
            'content': 'https://www.youtube.com/v/qqoPhTZDG04',
        },
    },
    '/about/uses': {
        'title': {
            'property': 'og:title',
            'content': 'Open Context: How You Can Use Open Context Published Data',
        },
        'description': {
            'property': 'og:description',
            'content': (
                'Open Context publishes data you can analyze, media you can reuse, '
                'and field notes you can explore. Learn more about how Open Context published '
                'data can help your research, teaching and enjoyment of the archaeological past.'
            ),
        },
    },
    '/about/publishing': {
        'title': {
            'property': 'og:title',
            'content': 'Open Context: Why Publish Your Research Data?',
        },
        'description': {
            'property': 'og:description',
            'content': (
                'Data can need many steps of cleanup, review, documentation and revision '
                'to be used by different communities. Open Context provides services '
                'to publish and archive data ready for broader reuse and understanding.'
            ),
        },
    },
    '/about/estimate': {
        'title': {
            'property': 'og:title',
            'content': 'Open Context: Estimate Publishing and Archiving Costs',
        },
        'description': {
            'property': 'og:description',
            'content': (
                'While data published by Open Context are free to use, Open Context '
                'charges contributing researchers fees for publishing and archiving services. '
            ),
        },
    },
    '/about/technology': {
        'title': {
            'property': 'og:title',
            'content': 'Open Context: Open Source Software Technologies',
        },
        'description': {
            'property': 'og:description',
            'content': (
                'Open Context integrates several open-source software applications to publish '
                'archaeological data via the Web.'
            ),
        },
    },
    '/about/services': {
        'title': {
            'property': 'og:title',
            'content': 'Open Context: Web Services (APIs)',
        },
        'description': {
            'property': 'og:description',
            'content': (
                'Open Context has a powerful Application Program Interface (API) that enables you '
                'to programmatically: search and browse data; visualize data; link to Open Context '
                'records; interoperate across multiple data sources.'
            ),
        },
    },
    '/about/recipes': {
        'title': {
            'property': 'og:title',
            'content': 'Open Context: Data & API Recipes',
        },
        'description': {
            'property': 'og:description',
            'content': (
                'This page provides a growing list of examples for how to use Open Context data and '
                'APIs in specific tasks and workflows.'
            ),
        },
    },
    '/about/intellectual-property': {
        'title': {
            'property': 'og:title',
            'content': 'Open Context: Intellectual Property Policies',
        },
        'description': {
            'property': 'og:description',
            'content': (
                'Open Context has intellectual property policies shaped to promote both the '
                'FAIR Data Principles and CARE Principles. While open data '
                'can be a powerful tool to promote scientific collaboration and teaching, they are '
                'not universally appropriate. We promote open data in ethically appropriate '
                'contexts.'
            ),
        },
    },
    '/about/fair-care': {
        'title': {
            'property': 'og:title',
            'content': 'Open Context: FAIR + CARE Data Policies',
        },
        'description': {
            'property': 'og:description',
            'content': (
                'Open Context promotes both the FAIR Data Principles and CARE Principles. While open data '
                'can be a powerful tool to promote scientific collaboration and teaching, they are '
                'not universally appropriate. We promote open data in ethically appropriate '
                'contexts.'
            ),
        },
    },
    '/about/people': {
        'title': {
            'property': 'og:title',
            'content': 'Open Context: Meet Our Team',
        },
        'description': {
            'property': 'og:description',
            'content': (
                'Open Context is maintained and administered by the Alexandria Archive Institute, '
                'a not-for-profit organization. Our team includes information scientists, '
                'field researchers, librarians, and other academic professionals'
            ),
        },
    },
    '/about/sponsors': {
        'title': {
            'property': 'og:title',
            'content': 'Open Context: Sponsors and Support',
        },
        'description': {
            'property': 'og:description',
            'content': (
                'Open Context is maintained and administered by a dedicated staff with the '
                'Alexandria Archive Institute, a non-profit organization. The '
                'California Digital Library at the University of California provides data '
                'archiving and preservation services. Open Context development is funded '
                'by foundation grants and charitable donations'
            ),
        },
    },
    '/about/bibliography': {
        'title': {
            'property': 'og:title',
            'content': 'Open Context: Bibliography',
        },
        'description': {
            'property': 'og:description',
            'content': (
                'Developing Open Context requires research and development in a host of issues '
                'relating to informatics, technology, theory, research policy, and research ethics. '
                'This page lists publications that help document our efforts and our research '
                'contributions in these areas of scholarship.'
            ),
        },
    },
    '/about/terms': {
        'title': {
            'property': 'og:title',
            'content': 'Open Context: Terms of Use and Privacy Policies',
        },
        'description': {
            'property': 'og:description',
            'content': (
                'Open Context publishes open research data for different public communities to '
                'access and use. We require civil and respectful use of Open Context and the '
                'content it publishes according to the terms and conditions of service specified here.'
            ),
        },
    },
    '/highlights': {
        'title': {
            'property': 'og:title',
            'content': 'Open Context: Overview and Highlights',
        },
        'description': {
            'property': 'og:description',
            'content': (
                'Open Context publishes a rich array of archaeological data and related digital media. '
                'This page provides an overview and some highlights of these diverse information resources.'
            ),
        },
    },
    '/projects-index': {
        'title': {
            'property': 'og:title',
            'content': 'Open Context: Data Publication Projects',
        },
        'description': {
            'property': 'og:description',
            'content': (
                'Open Context publishes digital datasets — structured (often tabular) data, images, maps, '
                'field notes, 3D models, etc. '
                'This page lists each publication project that will include one or more datasets created '
                'by an individual researcher, a team of researchers, or an organization.'
            ),
        },
    },
}

def get_item_thumbnail_url(rep_dict):
    """Gets an image thumbnail if present from an item's representative media dict"""
    if not rep_dict:
        return None
    # First check to see if we have a thumbnail image.
    for file_obj in rep_dict.get('oc-gen:has-files', []):
        if file_obj.get('type') == 'oc-gen:thumbnail':
            return file_obj.get('id')
    # OK, not check if we have linked media resources, which may have a thumbnail.
    # import json
    # print(json.dumps(rep_dict, indent=4))
    for obs in rep_dict.get('oc-gen:has-obs', []):
        for event in obs.get('oc-gen:has-events', []):
            for ag in event.get('oc-gen:has-attribute-groups', []):
                for _, media_list in ag.get('relations', {}).get('media', {}).items():
                    if not media_list:
                        continue
                    return media_list[0].get('oc-gen:thumbnail-uri')
    return None


def make_social_media_metadata(url_path=None, canonical_uri=None, man_obj=None, rep_dict=None):
    """Makes social media metadata attributes for a Web page

    :param str url_path: The relative path of the requested page
    :param dict rep_dict: A dictionary for an AllManifest item used for
        templating an HTML view.

    returns dict social_meta
    """
    social_meta = copy.deepcopy(DEFAULT_SOCIAL_META_DICT)
    path_configs = copy.deepcopy(PATH_CONFIGS)
    path_config = None
    if url_path:
        path_config = path_configs.get(url_path)
        if not path_config and url_path.startswith('/query'):
            # Use the query configuration
            path_config = copy.deepcopy(QUERY_CONFIG)
    if path_config:
        for key, val in path_config.items():
            social_meta[key] = val
    if canonical_uri:
        social_meta['url']['content'] = canonical_uri
    if man_obj:
        hero_banner_url = get_hero_banner_url(man_obj)
        if hero_banner_url:
            # The hero_banner_url lacks a prefix
            social_meta['image']['content'] = f'https://{hero_banner_url}'
            social_meta['image_secure_url']['content'] = f'https://{hero_banner_url}'
            social_meta['image_alt']['content'] = f'Banner image for {man_obj.label}'
    if rep_dict:
        if rep_dict.get('id'):
            social_meta['url']['content'] = rep_dict.get('id')
        if rep_dict.get('dc-terms:title'):
            social_meta['title']['content'] = rep_dict.get('dc-terms:title')
        if rep_dict.get('dc-terms:description'):
            act_des = rep_dict.get('dc-terms:description')
            social_meta['description']['content'] = act_des[0].get('@en')
        elif man_obj:
            if man_obj.item_type == 'subjects':
                social_meta['description']['content'] = (
                    f'An Open Context "{rep_dict.get("item_class__label")}" record documented by the '
                    f'project: "{man_obj.project.label}"'
                )
            else:
                social_meta['description']['content'] = (
                    f'An Open Context "{man_obj.item_type}" record documented by the '
                    f'project: "{man_obj.project.label}"'
                )
    thumbnail_url = None
    if man_obj and rep_dict:
        if rep_dict.get('media_preview_image'):
            thumbnail_url = rep_dict.get('media_preview_image')
        elif man_obj.item_type != 'projects':
            thumbnail_url = get_item_thumbnail_url(rep_dict)
    if man_obj and thumbnail_url:
        social_meta['image']['content'] = thumbnail_url
        social_meta['image_secure_url']['content'] = thumbnail_url
        social_meta['image_alt']['content'] = f'Image linked with {man_obj.label}'

    return social_meta