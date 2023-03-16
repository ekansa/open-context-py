import copy

from django.conf import settings


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
                'Open Context promotes both the FAIR Data Principles and CARE Principles. While open data '
                'can be a powerful tool to promote scientific collaboration and teaching, they are '
                'not universally appropriate. We promote open data in ethically appropriate '
                'contexts.'
            ),
        },
    },
}

def make_social_media_attributes(url_path, )