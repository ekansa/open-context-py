from django.db import models
from django.utils.http import urlunquote
from opencontext_py.apps.ldata.linkentities.models import LinkEntity, LinkEntityGeneration
from opencontext_py.apps.ldata.geonames.api import GeonamesAPI
from opencontext_py.apps.ldata.uberon.api import uberonAPI
from opencontext_py.apps.ldata.eol.api import eolAPI
from opencontext_py.apps.ldata.getty.api import gettyAPI
from opencontext_py.apps.ldata.ansochre.api import ANSochreAPI
from opencontext_py.apps.ldata.gbif.manage import (
    GBIF_VOCAB_URI,
    add_get_gbif_link_entity_and_hierarchy
)


# This class has methods to call external Web APIs to add information about linked entities
class WebLinkEntity():
    """
from opencontext_py.apps.ldata.linkentities.web import WebLinkEntity
web_le = WebLinkEntity()
web_le.check_add_link_entity(uri)

    """

    def __init__(self):
        pass

    def check_add_link_entity(self, uri):
        """ Checks to see if an entity exists, if not, it adds
            it if we recognize the URI to be part of a
            known vocabulary
        """
        ent = LinkEntity.objects.filter(uri=uri).first()
        if ent:
            # We found the linked data entity.
            return ent

        label = None
        alt_label = None
        ent_type = 'class'
        vocab_uri = None
        if '.geonames.org' in uri:
            geo_api = GeonamesAPI()
            vocab_uri = GeonamesAPI().VOCAB_URI
            labels = geo_api.get_labels_for_uri(uri)
            if isinstance(labels, dict):
                # got the label!
                label = labels['label']
                alt_label = labels['alt_label']
        elif 'UBERON' in uri:
            uber_api = uberonAPI()
            vocab_uri = uberonAPI().VOCAB_URI
            label = uber_api.get_uri_label_from_graph(uri)
            if label is not False:
                alt_label = label
        elif 'eol.org' in uri:
            eol_api = eolAPI()
            vocab_uri = eolAPI().VOCAB_URI
            labels = eol_api.get_labels_for_uri(uri)
            if isinstance(labels, dict):
                # got the label!
                label = labels['label']
                alt_label = labels['alt_label']
        elif 'wikipedia.org' in uri:
            # page name in the URI of the article
            link_ex = uri.split('/')
            label = urlunquote(link_ex[-1])
            label = label.replace('_', ' ')  # underscores in Wikipedia titles
            alt_label = label
            vocab_uri = 'http://www.wikipedia.org/'
        elif 'vocab.getty.edu/aat' in uri:
            print('Finding: ' + uri)
            getty_api = gettyAPI()
            vocab_uri = gettyAPI().VOCAB_URI
            labels = getty_api.get_labels_for_uri(uri)
            if isinstance(labels, dict):
                # got the label!
                label = labels['label']
                alt_label = labels['alt_label']
        elif 'numismatics.org/ocre/id/' in uri:
            print('Finding: ' + uri)
            ANSochre = ANSochreAPI()
            vocab_uri = ANSochreAPI().VOCAB_URI
            labels = ANSochre.get_labels_for_uri(uri)
            if isinstance(labels, dict):
                # got the label!
                label = labels['label']
                alt_label = labels['alt_label']
        elif 'gbif.org/species/' in uri:
            ent = add_get_gbif_link_entity_and_hierarchy(
                uri
            )
            # This adds the linked entity to the database
            # as well as its hierarchy
            return ent
        if not label or not vocab_uri:
            # Something went wrong. Could not
            # add the item
            return None

        # ok to make an entity then!
        ent = LinkEntity()
        ent.uri = uri
        ent.label = label
        ent.alt_label = alt_label
        ent.vocab_uri = vocab_uri
        ent.ent_type = ent_type
        ent.sort = ''
        ent.save()
        return ent

