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
from opencontext_py.apps.ocitems.octypes.models import OCtype
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

    def get_link_entities_qs(
        self,
        qstring,
        vocab_uri=None,
        ent_type=None,
        label=None,
        qs_limit=10,
    ):
        """Gets a link_entities query set filtered on different args
        
        :param str qstring: A string for partial mating on URIs,
            slugs, labels or alternative labels.
        :param str vocab_uri: A string, with possible delimiter for
            listing multiple vocabulary URIs (namespaces) to search
            within.
        :param str ent_type: A string, with possible delimiter for
            listing multiple entity types to search within.
        :param str label: A string to require an exact match on a
            link_entity label.
        :param int qs_limit: Limit on the length of the query set
            returned. No limit if None.
        """
        # Make URI alternates if the qstring is a uri
        ent_equivs = EntityEquivalents()
        uri_alts = ent_equivs.get_identifier_list_variants(qstring)
        ent_types = []
        if ent_type:
            ent_types.append(ent_type)
        if ent_type == 'class':
            ent_types.append('type')
        
        link_ents_qs = LinkEntity.objects.all()
        if qstring:
            link_ents_qs = link_ents_qs.filter(
                Q(uri__icontains=qstring)
                | Q(uri__in=uri_alts)
                | Q(slug__icontains=qstring)
                | Q(label__icontains=qstring)
                | Q(alt_label__icontains=qstring)
            )
        
        if len(ent_types):
           link_ents_qs = link_ents_qs.filter(ent_type__in=ent_types)

        if vocab_uri:
            vocab_uris = self.make_id_list(vocab_uri)
            link_ents_qs = link_ents_qs.filter(
                vocab_uri__in=vocab_uris
            )
        
        if label:
            # Exact label match required
            link_ents_qs = link_ents_qs.filter(
                label=label
            )
        if qs_limit is not None:
            link_ents_qs = link_ents_qs[:qs_limit]
        return link_ents_qs


    def get_manifest_qs(
        self,
        qstring,
        item_types=[],
        class_uri=None,
        project_uuid=None,
        context_uuid=None,
        data_type=None,
        context=None,
        label=None,
        qs_limit=10,
    ):
        """ Makes a manifest object queryset based on filtered args.

        :param str qstring: A string for partial mating on uuids,
            slugs, or labels.
        :param str item_types: A list of item_types to search 
            (the item_type field in oc_manifest).
        :param str class_uri: A string, with possible delimiter for
            listing multiple class_uris to search within. 
        :param str project_uuid: A string, with possible delimiter for
            listing multiple project_uuids to search within.
        :param str context_uuid: A string to limit searches within a
            parent context entity (either a predicate for a search
            of item_type=='types' or a subjects item for searches
            within a specific spatial context).
        :param str data_type: A string, with possible delimiter for
            listing predicate data-types to search within.
        :param str context: A context path for a spatial (subjects)
            context to search within.
        :param str label: A string to require an exact match on a
            link_entity or manifest label.
        :param int qs_limit: Limit on the length of the query set
            returned. No limit if None.
        """

        manifest_qs = Manifest.objects.all()

        if qstring:
            manifest_qs = manifest_qs.filter(
                Q(uuid__icontains=qstring)
                | Q(slug__icontains=qstring)
                | Q(label__icontains=qstring)
            )

        project_uuids = None
        if project_uuid:
            project_uuids = self.make_id_list(project_uuid)
            manifest_qs = manifest_qs.filter(
                project_uuid__in=project_uuids
            )

        class_uris = []
        if class_uri:
            class_uris = self.make_id_list(class_uri)
            manifest_qs = manifest_qs.filter(
                class_uri__in=class_uris
            )
        
        if label:
            # Exact label match required
            manifest_qs = manifest_qs.filter(
                label=label
            )

        if len(item_types): 
            manifest_qs = manifest_qs.filter(item_type__in=item_types)
        
        # Now get limiting uuid for queries to related tables
        # based on arguments.
        limit_uuids = []
        context_startswith = False
        if not context and context_uuid and 'subjects' in item_types:
            sub = Subject.objects.filter(uuid=context_uuid).first()
            if sub:
                context_startswith = True
                context = sub.context

        if context:
            # Get limit uuids from subject contexts (spatial).
            if context_startswith:
                # Treat the context as the start of a context path
                # so we're searching subcontexts within that path.
                subs_qs = Subject.objects.filter(
                    context__startswith=context
                )
            else:
                subs_qs = Subject.objects.filter(
                    context__icontains=context
                )
            if project_uuids:
                subs_qs = subs_qs.filter(
                    project_uuid__in=project_uuids
                )
            limit_uuids += [s.uuid for s in subs_qs]

        if context_uuid and 'types' in item_types:
            # Get limit uuids from types related to a context_uuid. 
            oc_types_qs = OCtype.objects.filter(
                predicate_uuid=context_uuid
            )
            if project_uuids:
                oc_types_qs = oc_types_qs.filter(
                    project_uuid__in=project_uuids
                )
            limit_uuids += [t.uuid for t in oc_types_qs]

        if data_type and 'predicates' in item_types:
            # Get limit uuids from predicates with a given data_type.
            pred_qs = Predicate.objects.filter(data_type=data_type)
            if project_uuids:
                pred_qs = pred_qs.filter(
                    project_uuid__in=project_uuids
                )
            limit_uuids += [p.uuid for p in pred_qs]
        
        media_uuids = []
        if 'media' in item_types:
            files_qs = Mediafile.objects.filter(
                file_uri__icontains=qstring
            )
            if project_uuids:
                files_qs = files_qs.filter(
                    project_uuid__in=project_uuids
                )
            media_uuids = [f.uuid for f in files_qs]
            limit_uuids += [f.uuid for f in files_qs]

        # Now apply the uuid limit it there are some limit_uuids.
        if len(limit_uuids):
            manifest_qs = manifest_qs.filter(uuid__in=limit_uuids)
        
        # Execute the manifest query now, to see if
        # we need to do a second query for searches of media items.
        if qs_limit is not None:
            manifest_qs = manifest_qs[:qs_limit]
        len_man = len(manifest_qs)
        if len_man == 0 and len(media_uuids):
            # We didn't find any manifest items, but we did find
            # media uuids by matching file uris. So use those
            # to make a new Manifest queryset.
            manifest_qs = Manifest.objects.filter(
                uuid__in=media_uuids,
                item_type='media',
            )
            if class_uris:
                manifest_qs = manifest_qs.filter(
                    class_uri__in=class_uris
                )
            if qs_limit is not None:
                manifest_qs = manifest_qs[:qs_limit]
        return manifest_qs


    def search(
        self,
        qstring,
        item_type=None,
        class_uri=None,
        project_uuid=None,
        vocab_uri=None,
        ent_type=None,
        context_uuid=None,
        data_type=None,
        context=None,
        label=None):
        """ Searches for entities limited by query strings
            and optionally other criteria
        
        :param str qstring: A string for partial mating on URIs,
            slugs, labels or alternative labels.
        :param str item_type: A string, with possible delimiter for
            listing multiple item_types to search (the item_type 
            field in oc_manifest). 'uri' indicates to include link
            entities.
        :param str class_uri: A string, with possible delimiter for
            listing multiple class_uris to search within. 
        :param str project_uuid: A string, with possible delimiter for
            listing multiple project_uuids to search within.
        :param str vocab_uri: A string, with possible delimiter for
            listing multiple vocabulary URIs (namespaces) to search
            within.
        :param str ent_type: A string, with possible delimiter for
            listing multiple entity types to search within.
        :param str context_uuid: A string to limit searches within a
            parent context entity (either a predicate for a search
            of item_type=='types' or a subjects item for searches
            within a specific spatial context).
        :param str data_type: A string, with possible delimiter for
            listing predicate data-types to search within.
        :param str context: A context path for a spatial (subjects)
            context to search within.
        :param str label: A string to require an exact match on a
            link_entity or manifest label.
        """
        
        item_types = []
        if item_type:
            item_types = self.make_id_list(item_type)
        
        if 'uri' in item_types:
            # We have "uri" in our list of requested item_types, 
            # so make a queryset of link_entities.
            link_ents_qs = self.get_link_entities_qs(
                qstring=qstring,
                vocab_uri=vocab_uri,
                ent_type=ent_type,
                label=label,
            )
        else:
            # Make an empty list for link_entities, since uri
            # is not in the list of allowed item_types.
            link_ents_qs = []
        
        if item_types == ['uri']:
            # We're only searching link_entities item_type == 'uri'
            # This means we don't need to bother looking at the 
            # manifest at all, so make an empty list for it.
            manifest_qs = []
        else:
            manifest_qs = self.get_manifest_qs(
                qstring=qstring,
                item_types=item_types,
                class_uri=class_uri,
                project_uuid=project_uuid,
                context_uuid=context_uuid,
                data_type=data_type,
                context=context,
                label=label
            )
        
        # Now make an output list from the query sets.
        self.ids_meta = {}
        output = []
        for link_entity in link_ents_qs:
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
        for man_entity in manifest_qs:
            item = LastUpdatedOrderedDict()
            item['id'] = man_entity.uuid
            item['label'] = man_entity.label
            item['slug'] = man_entity.slug
            item['type'] = man_entity.item_type
            if man_entity.item_type == 'predicates':
                item['data_type'] = False
                pred = Predicate.objects.filter(uuid=man_entity.uuid).first()
                if pred:
                    item['data_type'] = pred.data_type
            if context and man_entity.item_type == 'subjects':
                item['context'] = False
                sub = Subject.objects.filter(uuid=man_entity.uuid).first()
                if sub:
                    item['context'] = sub.context
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
            link_entity = LinkEntity.objects.filter(uri=uri).first()
            if link_entity:
                output = link_entity.label
            self.ids_meta[uri] = output
        return output

    def get_manifest_label(self, uuid):
        """ Gets labels for items in the manifest """
        if uuid in self.ids_meta:
            output = self.ids_meta[uuid]
        else:
            output = False
            manifest_item = Manifest.objects.filter(uuid=uuid).first()
            if manifest_item:
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
