from django.conf import settings
from django.db import models
from django.db.models import Q, Count
from opencontext_py.apps.entities.uri.models import URImanagement
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.apps.ldata.linkentities.models import LinkEntity
from opencontext_py.apps.ldata.linkannotations.models import LinkAnnotation
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.ocitems.projects.models import Project
from opencontext_py.apps.ocitems.identifiers.models import StableIdentifer
from opencontext_py.apps.ocitems.predicates.models import Predicate
from opencontext_py.apps.ocitems.octypes.lookup import TypeLookup
from opencontext_py.apps.ocitems.mediafiles.models import Mediafile
from opencontext_py.apps.ocitems.subjects.models import Subject
from opencontext_py.apps.ocitems.identifiers.models import StableIdentifer


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
        self.parent_project_uuid = False
        self.par_proj_man_obj = False
        self.class_uri = False
        self.entity_type = False
        self.data_type = False
        self.sort = False
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
        self.stable_id_uris = False
        self.get_stable_ids = False
        self.context = False
        self.get_context = False
        self.get_icon = False
        self.get_ld_data_type = True
        self.icon = False
        self.ids_meta = False
        self.slug_uri = False

    def get_linked_entity_data_type(self, ld_entity, db_save=True):
        """Get the data type for a linked data property."""
        if ld_entity.ent_type != 'property':
            return False
        # First find the predicates associated with this linked_entity. 
        rel_preds = LinkAnnotation.objects.filter(
            subject_type='predicates',
            object_uri=ld_entity.uri
        )
        rel_pred_uuids = [la.subject for la in rel_preds]
        data_type_dict = Predicate.objects.filter(
            uuid__in=rel_pred_uuids
        ).values('data_type').annotate(
            total=Count('data_type')
        ).order_by('-total').first()
        if not data_type_dict:
            return False
        data_type = data_type_dict['data_type']
        if db_save:
            if not isinstance(ld_entity.localized_json, dict):
                ld_entity.localized_json = {}    
            ld_entity.localized_json['data_type'] = data_type
            ld_entity.save()
        return data_type

    def dereference_linked_data(self, identifier, link_entity_slug=None):
        """Dereferences a linked data entity (not part of an OC project)"""
        uris = []
        if ((len(identifier) > 8)
            and (identifier[:7] == 'http://' or identifier[:8] == 'https://')):
            ent_equivs = EntityEquivalents()
            uris = ent_equivs.make_uri_variants(identifier)
        if not uris and not link_entity_slug:
            return None
        ld_entity = LinkEntity.objects.filter(Q(uri__in=uris) | Q(slug=identifier)).first()
        if not ld_entity:
            return None
        self.uri = ld_entity.uri
        self.slug = ld_entity.slug
        self.label = ld_entity.label
        self.item_type = 'uri'
        self.alt_label = ld_entity.alt_label
        self.entity_type = ld_entity.ent_type
        self.vocab_uri = ld_entity.vocab_uri
        self.ld_object_ok = True
        if isinstance(ld_entity.localized_json, dict):
            self.data_type = ld_entity.localized_json.get(
                'data_type', False
            )

        # Now get the vocabulary item.
        vocab_uris = [ld_entity.vocab_uri]
        vocab_uris.append(ld_entity.vocab_uri.replace('https://', 'http://'))
        vocab_uris.append(ld_entity.vocab_uri.replace('http://', 'https://'))
        vocab_entity = LinkEntity.objects.filter(uri__in=vocab_uris).first()
        if vocab_entity:
            self.vocabulary = vocab_entity.label
        
        if (not self.data_type 
            and self.get_ld_data_type 
            and ld_entity.ent_type == 'property'):
            # Get the data_type for the link entity via looking at the
            # most common data_type for associated predicate items.
            self.data_type = self.get_linked_entity_data_type(ld_entity)

        if not self.get_icon:
            # Do not bother adding an icon.
            return True
        
        # Add an icon link if true
        prefix_uri = URImanagement.prefix_common_uri(ld_entity.uri)
        icon_ids = uris + [ld_entity.uri, identifier, prefix_uri]
        icon_anno = LinkAnnotation.objects.filter(
            subject__in=icon_ids,
            predicate_uri='oc-gen:hasIcon'
        ).first()
        if icon_anno:
            self.icon = icon_anno.object_uri
        return True
        

    def dereference_manifest_item(self, identifier):
        """Dereferences a manifest item (something part of an OC project)"""
        manifest_item = Manifest.objects.filter(
            Q(uuid=identifier) | Q(slug=identifier)
        ).first()
        if not manifest_item:
            return None
        
        # We found the item, now get the data out.
        self.uri = URImanagement.make_oc_uri(manifest_item.uuid, manifest_item.item_type)
        self.uuid = manifest_item.uuid
        self.slug = manifest_item.slug
        self.label = manifest_item.label
        self.item_type = manifest_item.item_type
        self.class_uri = manifest_item.class_uri
        self.project_uuid = manifest_item.project_uuid
        if manifest_item.item_type == 'media' and self.get_thumbnail:
            # a media item. get information about its thumbnail.
            thumb_obj = Mediafile.objects.filter(
                uuid=manifest_item.uuid,
                file_type='oc-gen:thumbnail'
            ).first()
            if thumb_obj:
                self.thumbnail_media = thumb_obj
                self.thumbnail_uri = thumb_obj.file_uri
        elif manifest_item.item_type in ['persons', 'projects', 'tables'] \
             or self.get_stable_ids:
            # get stable identifiers for persons or projects by default
            stable_ids = StableIdentifer.objects.filter(uuid=manifest_item.uuid)
            if len(stable_ids) > 0:
                self.stable_id_uris = []
                doi_uris = []
                orcid_uris = []
                other_uris = []
                for stable_id in stable_ids:
                    if stable_id.stable_type in StableIdentifer.ID_TYPE_PREFIXES:
                        prefix = StableIdentifer.ID_TYPE_PREFIXES[stable_id.stable_type]
                    else:
                        prefix = ''
                    stable_uri = prefix + stable_id.stable_id
                    if stable_id.stable_type == 'orcid':
                        orcid_uris.append(stable_uri)
                    elif stable_id.stable_type == 'doi':
                        doi_uris.append(stable_uri)
                    else:
                        other_uris.append(stable_uri)
                # now list URIs in order of importance, with ORCIDs and DOIs
                # first, followed by other stable URI types (Arks or something else)
                self.stable_id_uris = orcid_uris + doi_uris + other_uris
        elif manifest_item.item_type == 'types':
            tl = TypeLookup()
            tl.get_octype_without_manifest(identifier)
            self.content = tl.content
        elif manifest_item.item_type == 'predicates':
            oc_pred = Predicate.objects.filter(uuid=manifest_item.uuid).first()
            if oc_pred:
                self.data_type = oc_pred.data_type
                self.sort = oc_pred.sort
                self.slug_uri = 'oc-pred:' + str(self.slug)
        elif manifest_item.item_type == 'projects':
            # get a manifest object for the parent of a project, if it exists
            ch_tab = '"oc_projects" AS "child"'
            filters = 'child.project_uuid=oc_manifest.uuid '\
                      ' AND child.uuid=\'' + self.uuid + '\' ' \
                      ' AND child.project_uuid != \'' + self.uuid + '\' '
            par_rows = Manifest.objects\
                               .filter(item_type='projects')\
                               .exclude(uuid=self.uuid)\
                               .extra(tables=[ch_tab], where=[filters])[:1]
            if len(par_rows) > 0:
                self.par_proj_man_obj = par_rows[0]
        elif (manifest_item.item_type == 'subjects'
              and self.get_context
              and not self.context):
            subj = Subject.objects.filter(uuid=manifest_item.uuid).first()
            if subj:
                self.context = subj.context
        return True


    def dereference(self, identifier, link_entity_slug=False):
        """ Dereferences an entity identified by an identifier, checks if a URI,
            if, not a URI, then looks in the OC manifest for the item
        """
        output = False
        # Only try to dereference if the identifier is a string.
        if not isinstance(identifier, str):
            return output
        identifier = URImanagement.convert_prefix_to_full_uri(identifier)
        oc_uuid = URImanagement.get_uuid_from_oc_uri(identifier)
        if not oc_uuid and (settings.CANONICAL_HOST + '/tables/') in identifier:
            # Special case for probable open context table item.
            oc_uuid = identifier.replace(
                (settings.CANONICAL_HOST + '/tables/'), ''
            )
        
        if not oc_uuid:
            # We don't have an Open Context UUID, so look up a linked
            # data entity.
            link_entity_found = self.dereference_linked_data(
                identifier,
                link_entity_slug=link_entity_slug
            )
            if link_entity_found:
                # Found what we want, so skip the rest and return True.
                return True
        # If we haven't found a link_entity, check for manifest items.
        if oc_uuid:
            # We found an Open Context uuid by parsing a URI. So that
            # should be the identifier to lookup.
            identifier = oc_uuid
        manifest_item_found = self.dereference_manifest_item(identifier)
        if manifest_item_found:
            return True
        return output
 
    def context_dereference(self, context):
        """ looks up a context, described as a '/' seperated list of labels """
        output = False
        subject = Subject.objects.filter(context=context).first()
        if not subject:
            return output
        self.context = subject.context
        output = self.dereference(subject.uuid)
        return output

    def search(self,
               qstring,
               item_type=False,
               class_uri=False,
               project_uuid=False,
               vocab_uri=False,
               ent_type=False,
               context_uuid=False,
               data_type=False,
               context=False):
        """ Searches for entities limited by query strings
            and optionally other criteria
        """
        ent_equivs = EntityEquivalents()
        uri_alts = ent_equivs.get_identifier_list_variants(qstring);
        entity_list = []
        manifest_list = [] 
        subjects_obj = None
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
            last_args = {}
            search_sub_uuids = []
            if context:
                # limit by context path
                c_args = {'context__icontains': context}
                if project_uuid:
                    project_uuid = self.make_id_list(project_uuid)
                    c_args['project_uuid__in'] = project_uuid
                subs = Subject.objects.filter(**c_args)
                for sub in subs:
                    search_sub_uuids.append(sub.uuid)
                args['uuid__in'] = search_sub_uuids
                last_args['uuid__in'] = search_sub_uuids
                # print('Limit to contexts: ' + str(search_sub_uuids))
            item_type = self.make_id_list(item_type)
            args['item_type__in'] = item_type
            last_args['item_type__in'] = item_type
            if class_uri is not False:
                class_uri = self.make_id_list(class_uri)
                args['class_uri__in'] = class_uri
            if project_uuid is not False:
                project_uuid = self.make_id_list(project_uuid)
                args['project_uuid__in'] = project_uuid
                last_args['project_uuid__in'] = project_uuid
            # print('args are here: ' + str(args))
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
            if len(manifest_list) < 1:
                # now just search for a uuid, since we may have a search just for UUIDs
                manifest_list = Manifest.objects\
                                        .filter(**last_args)\
                                        .filter(Q(uuid=qstring) | Q(slug=qstring))[:1]
        elif item_type is False and project_uuid is not False:
            project_uuid = self.make_id_list(project_uuid)
            manifest_list = Manifest.objects\
                                    .filter(project_uuid__in=project_uuid)\
                                    .filter(Q(uuid__icontains=qstring)\
                                            | Q(slug__icontains=qstring)\
                                            | Q(label__icontains=qstring))[:10]
            if len(manifest_list) < 1:
                # now just search for a uuid, since we may have a search just for UUIDs
                manifest_list = Manifest.objects\
                                        .filter(Q(uuid=qstring) | Q(slug=qstring))[:1]
        if len(manifest_list) < 1 and 'media' in item_type:
            # we're searching for a media item. check to see if we have a file name
            # print('check for file: ' + qstring)
            med_files = Mediafile.objects\
                                 .filter(file_uri__icontains=qstring)[:1]
            if len(med_files) > 0:
                manifest_list = Manifest.objects\
                                        .filter(uuid=med_files[0].uuid)[:1]
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
            if context and man_entity.item_type == 'subjects':
                try:
                    sub = Subject.objects.get(uuid=man_entity.uuid)
                    item['context'] = sub.context
                except Subject.DoesNotExist:
                    item['context'] = False
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
        elif not isinstance(id_string, list):
            output_list = [id_string]
        else:
            output_list = id_string
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
                if isinstance(oc_uuid, str):
                    output_list.append(oc_uuid)
                else:
                    prefix_id = URImanagement.prefix_common_uri(identifier)
                    output_list.append(prefix_id)
                    variant_uris = self.make_uri_variants(identifier)
                    for variant_uri in variant_uris:
                        if variant_uri not in output_list:
                            output_list.append(variant_uri)
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
    
    def make_uri_variants(self, uri):
        """ makes alternative uri varients """
        space_opts = [
            ' ',
            '%20',
            '+'
        ]
        variants = [uri]
        if isinstance(uri, str):
            if len(uri) > 8:
                if uri[:7] == 'http://':
                    variants.append('https://' + uri[7:])
                elif uri[:8] == 'https://':
                    variants.append('http://' + uri[8:])
                space_variants = []
                for variant in variants:
                    for space_opt in space_opts:
                        if space_opt in variant:
                            for o_opt in space_opts:
                                new_variant = variant.replace(space_opt, o_opt)
                                if new_variant not in space_variants:
                                    space_variants.append(new_variant)
                for space_variant in space_variants:
                    if space_variant not in variants:
                        variants.append(space_variant)
        return variants
