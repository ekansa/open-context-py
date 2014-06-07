from django.conf import settings
from django.db import models
from django.db.models import Q
from opencontext_py.apps.entities.uri.models import URImanagement
from opencontext_py.apps.ldata.linkentities.models import LinkEntity
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.ocitems.identifiers.models import StableIdentifer
from opencontext_py.apps.ocitems.predicates.models import Predicate
from opencontext_py.apps.ocitems.octypes.models import TypeLookup
from opencontext_py.apps.ocitems.mediafiles.models import Mediafile


# This class is used to dereference URIs or prefixed URIs
# to get useful information about the entity
class Entity():

    def __init__(self):
        self.uri = False
        self.uuid = False
        self.slug = False
        self.label = False
        self.item_type = False
        self.class_uri = False
        self.data_type = False
        self.alt_label = False
        self.vocab_uri = False
        self.vocabulary = False
        self.content = False
        self.manifest = False
        self.thumbnail_uri = False
        self.comment = False
        self.thumbnail_media = False
        self.get_thumbnail = False

    def dereference(self, identifier, link_entity_slug=False):
        """ Dereferences an entity identified by an identifier, checks if a URI,
            if, not a URI, then looks in the OC manifest for the item
        """
        output = False
        try_manifest = True
        identifier = URImanagement.convert_prefix_to_full_uri(identifier)
        if(link_entity_slug or (len(identifier) > 8)):
            if(link_entity_slug or (identifier[:7] == 'http://' or identifier[:8] == 'https://')):
                try:
                    try_manifest = False
                    ld_entity = LinkEntity.objects.get(Q(uri=identifier) | Q(slug=identifier))
                except LinkEntity.DoesNotExist:
                    ld_entity = False
                if(ld_entity is not False):
                    output = True
                    self.uri = ld_entity.uri
                    self.slug = ld_entity.slug
                    self.label = ld_entity.label
                    self.item_type = 'uri'
                    self.alt_label = ld_entity.alt_label
                    self.vocab_uri = ld_entity.vocab_uri
                    try:
                        vocab_entity = LinkEntity.objects.get(uri=self.vocab_uri)
                    except LinkEntity.DoesNotExist:
                        vocab_entity = False
                    if(vocab_entity is not False):
                        self.vocabulary = vocab_entity.label
                else:
                    try_manifest = True
                    # couldn't find the item in the linked entities table
                    identifier = URImanagement.get_uuid_from_oc_uri(identifier)
        if(try_manifest):
            try:
                manifest_item = Manifest.objects.get(Q(uuid=identifier) | Q(slug=identifier))
            except Manifest.DoesNotExist:
                manifest_item = False
            if(manifest_item is not False):
                output = True
                self.uri = URImanagement.make_oc_uri(manifest_item.uuid, manifest_item.item_type)
                self.uuid = manifest_item.uuid
                self.slug = manifest_item.slug
                self.label = manifest_item.label
                self.item_type = manifest_item.item_type
                self.class_uri = manifest_item.class_uri
                if(manifest_item.item_type == 'media' and self.get_thumbnail):
                    # a media item. get information about its thumbnail.
                    try:
                        thumb_obj = Mediafile.objects.get(uuid=manifest_item.uuid, file_type='oc-gen:thumbnail')
                    except Mediafile.DoesNotExist:
                        thumb_obj = False
                    self.thumbnail_media = thumb_obj
                    self.thumbnail_uri = thumb_obj.file_uri
                elif(manifest_item.item_type == 'types'):
                    tl = TypeLookup()
                    tl.get_octype_without_manifest(identifier)
                    self.content = tl.content
                elif(manifest_item.item_type == 'predicates'):
                    try:
                        oc_pred = Predicate.objects.get(uuid=manifest_item.uuid)
                    except Predicate.DoesNotExist:
                        oc_pred = False
                    if(oc_pred is not False):
                        self.data_type = oc_pred.data_type
        return output
