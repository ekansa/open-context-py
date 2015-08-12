from django.conf import settings
from django.db import models
from django.db.models import Q
from opencontext_py.apps.entities.uri.models import URImanagement
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.apps.ldata.linkentities.models import LinkEntity
from opencontext_py.apps.ldata.linkannotations.models import LinkAnnotation
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.ocitems.identifiers.models import StableIdentifer
from opencontext_py.apps.ocitems.predicates.models import Predicate
from opencontext_py.apps.ocitems.octypes.lookup import TypeLookup
from opencontext_py.apps.ocitems.mediafiles.models import Mediafile
from opencontext_py.apps.ocitems.subjects.models import Subject


# This class is used to dereference URIs or prefixed URIs
# to get useful information about the entity
class Entity():

    def __init__(self):
        self.uri = False
        self.uuid = False
        self.slug = False
        self.label = False
        self.item_type = False
        self.project_uuid = False
        self.class_uri = False
        self.entity_type = False
        self.data_type = False
        self.alt_label = False
        self.vocab_uri = False
        self.vocabulary = False
        self.ld_object_ok = False
        self.content = False
        self.manifest = False
        self.thumbnail_uri = False
        self.comment = False
        self.thumbnail_media = False
        self.get_thumbnail = False
        self.context = False
        self.get_context = False
        self.get_icon = False
        self.icon = False
        self.ids_meta = False

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
                    self.entity_type = ld_entity.ent_type
                    self.vocab_uri = ld_entity.vocab_uri
                    self.ld_object_ok = True
                    try:
                        vocab_entity = LinkEntity.objects.get(uri=self.vocab_uri)
                    except LinkEntity.DoesNotExist:
                        vocab_entity = False
                    if(vocab_entity is not False):
                        self.vocabulary = vocab_entity.label
                    if self.get_icon:
                        prefix_uri = URImanagement.prefix_common_uri(ld_entity.uri)
                        icon_anno = LinkAnnotation.objects\
                                                  .filter(Q(subject=ld_entity.uri)
                                                          | Q(subject=identifier)
                                                          | Q(subject=prefix_uri),
                                                          predicate_uri='oc-gen:hasIcon')[:1]
                        if len(icon_anno) > 0:
                            self.icon = icon_anno[0].object_uri
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
                self.project_uuid = manifest_item.project_uuid
                if(manifest_item.item_type == 'media' and self.get_thumbnail):
                    # a media item. get information about its thumbnail.
                    try:
                        thumb_obj = Mediafile.objects.get(uuid=manifest_item.uuid, file_type='oc-gen:thumbnail')
                    except Mediafile.DoesNotExist:
                        thumb_obj = False
                    if thumb_obj is not False:
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
                elif(manifest_item.item_type == 'subjects' and self.get_context):
                    try:
                        subj = Subject.objects.get(uuid=manifest_item.uuid)
                    except Subject.DoesNotExist:
                        subj = False
                    if subj is not False:
                        self.context = subj.context
        return output

    def context_dereference(self, context):
        """ looks up a context, described as a '/' seperated list of labels """
        output = False
        try:
            subject = Subject.objects.filter(context=context)[:1]
        except Subject.DoesNotExist:
            subject = False
        if subject is not False:
            if len(subject) == 1:
                output = self.dereference(subject[0].uuid)
        return output

    def search(self,
               qstring,
               item_type=False,
               class_uri=False,
               project_uuid=False,
               vocab_uri=False,
               ent_type=False,
               context_uuid=False,
               data_type=False):
        """ Searches for entities limited by query strings
            and optionally other criteria
        """
        ent_equivs = EntityEquivalents()
        uri_alts = ent_equivs.get_identifier_list_variants(qstring);
        entity_list = []
        manifest_list = []
        if ent_type is not False:
            # make ent_type search a list
            ents = [ent_type]
            if ent_type == 'class':
                ents.append('type')
        else:
            ents = False
        if item_type is False and class_uri is False\
           and project_uuid is False and vocab_uri is False:
            """ Search all types of entities, only limit by string matching """
            entity_list = LinkEntity.objects\
                                    .filter(Q(uri__icontains=qstring)\
                                            | Q(uri__in=uri_alts)\
                                            | Q(slug__icontains=qstring)\
                                            | Q(label__icontains=qstring)\
                                            | Q(alt_label__icontains=qstring))[:10]
            manifest_list = Manifest.objects\
                                    .filter(Q(uuid__icontains=qstring)\
                                            | Q(slug__icontains=qstring)\
                                            | Q(label__icontains=qstring))[:10]
        elif item_type == 'uri' and class_uri is False\
                and project_uuid is False and vocab_uri is False:
            """ Search for link entities only limit by string matching """
            if ents is False:
                # don't limit by entity type
                entity_list = LinkEntity.objects\
                                        .filter(Q(uri__icontains=qstring)\
                                                | Q(uri__in=uri_alts)\
                                                | Q(slug__icontains=qstring)\
                                                | Q(label__icontains=qstring)\
                                                | Q(alt_label__icontains=qstring))[:15]
            else:
                # also limit by entity type
                entity_list = LinkEntity.objects\
                                        .filter(ent_type__in=ents)\
                                        .filter(Q(uri__icontains=qstring)\
                                                | Q(uri__in=uri_alts)\
                                                | Q(slug__icontains=qstring)\
                                                | Q(label__icontains=qstring)\
                                                | Q(alt_label__icontains=qstring))[:15]
        elif item_type == 'uri' and class_uri is False\
                and project_uuid is False and vocab_uri is not False:
            """ Search for link entities, limit by vocab_uri """
            vocab_uri = self.make_id_list(vocab_uri)
            if ents is False:
                # don't limit by entity type
                entity_list = LinkEntity.objects\
                                        .filter(vocab_uri__in=vocab_uri)\
                                        .filter(Q(uri__icontains=qstring)\
                                                | Q(uri__in=uri_alts)\
                                                | Q(slug__icontains=qstring)\
                                                | Q(label__icontains=qstring)\
                                                | Q(alt_label__icontains=qstring))[:15]
            else:
                # also limit by entity type
                entity_list = LinkEntity.objects\
                                        .filter(ent_type__in=ents)\
                                        .filter(vocab_uri__in=vocab_uri)\
                                        .filter(Q(uri__icontains=qstring)\
                                                | Q(uri__in=uri_alts)\
                                                | Q(slug__icontains=qstring)\
                                                | Q(label__icontains=qstring)\
                                                | Q(alt_label__icontains=qstring))[:15]
        elif item_type is not False and item_type != 'uri':
            """ Look only for manifest items """
            args = {}
            item_type = self.make_id_list(item_type)
            args['item_type__in'] = item_type
            if class_uri is not False:
                class_uri = self.make_id_list(class_uri)
                args['class_uri__in'] = class_uri
            if project_uuid is not False:
                project_uuid = self.make_id_list(project_uuid)
                args['project_uuid__in'] = project_uuid
            if context_uuid is not False and 'types' in item_type:
                l_tables = 'oc_types'
                filter_types = 'oc_manifest.uuid = oc_types.uuid \
                                AND oc_types.predicate_uuid = \'' + context_uuid + '\' '
                manifest_list = Manifest.objects\
                                        .extra(tables=[l_tables], where=[filter_types])\
                                        .filter(**args)\
                                        .filter(Q(uuid__icontains=qstring)\
                                                | Q(slug__icontains=qstring)\
                                                | Q(label__icontains=qstring))[:15]
            elif data_type is not False and 'predicates' in item_type:
                l_tables = 'oc_predicates'
                filter_types = 'oc_manifest.uuid = oc_predicates.uuid \
                                AND oc_predicates.data_type = \'' + data_type + '\' '
                manifest_list = Manifest.objects\
                                        .extra(tables=[l_tables], where=[filter_types])\
                                        .filter(**args)\
                                        .filter(Q(uuid__icontains=qstring)\
                                                | Q(slug__icontains=qstring)\
                                                | Q(label__icontains=qstring))[:15]
            else:
                manifest_list = Manifest.objects\
                                        .filter(**args)\
                                        .filter(Q(uuid__icontains=qstring)\
                                                | Q(slug__icontains=qstring)\
                                                | Q(label__icontains=qstring))[:15]
        elif item_type is False and project_uuid is not False:
            project_uuid = self.make_id_list(project_uuid)
            manifest_list = Manifest.objects\
                                    .filter(project_uuid__in=project_uuid)\
                                    .filter(Q(uuid__icontains=qstring)\
                                            | Q(slug__icontains=qstring)\
                                            | Q(label__icontains=qstring))[:10]
        self.ids_meta = {}
        output = []
        for link_entity in entity_list:
            item = LastUpdatedOrderedDict()
            item['id'] = link_entity.uri
            item['label'] = link_entity.label
            item['slug'] = link_entity.slug
            item['type'] = 'uri'
            item['class_uri'] = False
            item['ent_type'] = link_entity.ent_type
            item['partOf_id'] = link_entity.vocab_uri
            item['partOf_label'] = self.get_link_entity_label(link_entity.vocab_uri)
            output.append(item)
        for man_entity in manifest_list:
            item = LastUpdatedOrderedDict()
            item['id'] = man_entity.uuid
            item['label'] = man_entity.label
            item['slug'] = man_entity.slug
            item['type'] = man_entity.item_type
            if man_entity.item_type == 'predicates':
                try:
                    pred = Predicate.objects.get(uuid=man_entity.uuid)
                    item['data_type'] = pred.data_type
                except Predicate.DoesNotExist:
                    item['data_type'] = False
            item['class_uri'] = man_entity.class_uri
            item['ent_type'] = False
            item['partOf_id'] = man_entity.project_uuid
            item['partOf_label'] = self.get_manifest_label(man_entity.project_uuid)
            output.append(item)
        return output

    def make_id_list(self, id_string):
        """ Simple method to make an id_string a list of ids """
        if ',' in id_string:
            output_list = id_string.split(",")
        else:
            output_list = [id_string]
        return output_list

    def get_link_entity_label(self, uri):
        """ Gets labels for vocabularies """
        if uri in self.ids_meta:
            output = self.ids_meta[uri]
        else:
            output = False
            try:
                link_entity = LinkEntity.objects.get(uri=uri)
            except LinkEntity.DoesNotExist:
                link_entity = False
            if link_entity is not False:
                output = link_entity.label
            self.ids_meta[uri] = output
        return output

    def get_manifest_label(self, uuid):
        """ Gets labels for items in the manifest """
        if uuid in self.ids_meta:
            output = self.ids_meta[uuid]
        else:
            output = False
            try:
                manifest_item = Manifest.objects.get(uuid=uuid)
            except Manifest.DoesNotExist:
                manifest_item = False
            if manifest_item is not False:
                output = manifest_item.label
            self.ids_meta[uuid] = output
        return output


class EntityEquivalents():
    """ usefult to get alternative ids for entities """

    def __init__(self):
        pass

    def get_identifier_list_variants(self, id_list):
        """ makes different variants of identifiers
            for a list of identifiers
        """
        output_list = []
        if not isinstance(id_list, list):
            id_list = [str(id_list)]
        for identifier in id_list:
            output_list.append(identifier)
            if(identifier[:7] == 'http://' or identifier[:8] == 'https://'):
                oc_uuid = URImanagement.get_uuid_from_oc_uri(identifier)
                if oc_uuid is not False:
                    output_list.append(oc_uuid)
                else:
                    prefix_id = URImanagement.prefix_common_uri(identifier)
                    output_list.append(prefix_id)
            elif ':' in identifier:
                full_uri = URImanagement.convert_prefix_to_full_uri(identifier)
                output_list.append(full_uri)
            else:
                # probably an open context uuid or a slug
                ent = Entity()
                found = ent.dereference(identifier)
                if found:
                    full_uri = ent.uri
                    output_list.append(full_uri)
                    prefix_uri = URImanagement.prefix_common_uri(full_uri)
                    if prefix_uri != full_uri:
                        output_list.append(prefix_uri)
        return output_list
