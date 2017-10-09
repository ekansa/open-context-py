import datetime
from django.db import models
from django.db.models import Q, Max
from django.core.cache import cache
from opencontext_py.apps.ocitems.assertions.models import Assertion
from opencontext_py.apps.ocitems.geospace.models import Geospace
from opencontext_py.apps.ocitems.events.models import Event
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.ocitems.subjects.models import Subject
from opencontext_py.apps.ocitems.mediafiles.models import Mediafile
from opencontext_py.apps.ocitems.persons.models import Person
from opencontext_py.apps.ocitems.documents.models import OCdocument
from opencontext_py.apps.ocitems.predicates.models import Predicate
from opencontext_py.apps.ocitems.octypes.models import OCtype
from opencontext_py.apps.ocitems.strings.models import OCstring
from opencontext_py.apps.ocitems.complexdescriptions.models import ComplexDescription
from opencontext_py.apps.imports.fields.templating import ImportProfile
from opencontext_py.apps.imports.fieldannotations.models import ImportFieldAnnotation
from opencontext_py.apps.imports.sources.models import ImportSource


# Removes the import of a from a source_id
class UnImport():

    def __init__(self, source_id, project_uuid):
        self.COMPLEX_DESCRIPTION_SOURCE_SUFFIX = None
        self.source_id = source_id
        self.project_uuid = project_uuid
        self.delete_ok = self.check_unimport_ok()
        # now clear the cache a change was made
        cache.clear()

    def delete_all(self):
        """ deletes all from an import """
        self.delete_containment_assertions()
        self.delete_geospaces()
        self.delete_events()
        self.delete_describe_assertions()
        self.delete_complex_description_assertions()
        self.delete_predicate_vars()
        self.delete_links_assertions()
        self.delete_predicate_links()
        self.delete_subjects_entities()
        self.delete_person_entities()
        self.delete_document_entities()
        self.delete_media_entities()
        self.delete_types_entities()
        self.delete_strings()

    def delete_containment_assertions(self):
        """ Deletes containment assertions for an
            import
        """
        if self.delete_ok:
            rem_assertions = Assertion.objects\
                                      .filter(source_id=self.source_id,
                                              project_uuid=self.project_uuid,
                                              subject_type='subjects',
                                              predicate_uuid=Assertion.PREDICATES_CONTAINS,
                                              object_type='subjects')\
                                      .delete()

    def delete_geospaces(self):
        """ Deletes geolocation data for an
            import
        """
        if self.delete_ok:
            rem_geo = Geospace.objects\
                              .filter(source_id=self.source_id,
                                      project_uuid=self.project_uuid)\
                              .delete()

    def delete_events(self):
        """ Deletes date / event data for an
            import
        """
        if self.delete_ok:
            rem_event = Event.objects\
                             .filter(source_id=self.source_id,
                                     project_uuid=self.project_uuid)\
                             .delete()

    def delete_describe_assertions(self):
        """ Deletes an import of description assertions,
            does not delete assertions that link items to complex-description
            objects.
        """
        if self.delete_ok:
            object_types = ImportProfile.DEFAULT_DESCRIBE_OBJECT_TYPES
            if 'complex-description' in object_types:
                object_types.remove('complex-description')
            if 'xsd:string' not in object_types:
                object_types.append('xsd:string')
            rem_assertions = Assertion.objects\
                                      .filter(source_id=self.source_id,
                                              project_uuid=self.project_uuid,
                                              object_type__in=object_types)\
                                      .exclude(predicate_uuid=Assertion.PREDICATES_CONTAINS)\
                                      .exclude(predicate_uuid=ComplexDescription.PREDICATE_COMPLEX_DES)\
                                      .exclude(object_type='complex-description')\
                                      .delete()
            self.update_complex_description_assertion_source()
        return self.delete_ok
    
    def update_complex_description_assertion_source(self):
        """ updates the source id for assertions made on complex-descriptions
            this is a measure to help make sure assertions about complex-descriptions
            do not get deleted at the start of importing normal descriptive assertions
        """
        if isinstance(self.COMPLEX_DESCRIPTION_SOURCE_SUFFIX, str) and self.delete_ok:
            source_id_w_suffix = self.source_id + self.COMPLEX_DESCRIPTION_SOURCE_SUFFIX
            up_asses = Assertion.objects\
                                .filter(source_id=source_id_w_suffix,
                                        project_uuid=self.project_uuid)
            for up_ass in up_asses:
                up_ass.source_id = self.source_id
                up_ass.save()
    
    def delete_complex_description_assertions(self):
        """ Deletes an import of complex description assertions
        """
        if self.delete_ok:
            rem_assertions = Assertion.objects\
                                      .filter(source_id=self.source_id,
                                              project_uuid=self.project_uuid,
                                              object_type='complex-description')\
                                      .delete()
            rem_assertions = Assertion.objects\
                                      .filter(source_id=self.source_id,
                                              project_uuid=self.project_uuid,
                                              subject_type='complex-description')\
                                      .delete()
        return self.delete_ok

    def delete_predicate_vars(self):
        """ Deletes predicates that are variables
        """
        if self.delete_ok:
            man_pred_vars = Manifest.objects\
                                    .filter(source_id=self.source_id,
                                            project_uuid=self.project_uuid,
                                            item_type='predicates',
                                            class_uri='variable')
            for man_obj in man_pred_vars:
                rem_assertions = Assertion.objects\
                                          .filter(source_id=self.source_id,
                                                  project_uuid=self.project_uuid,
                                                  predicate_uuid=man_obj.uuid)\
                                          .delete()
                rem_pred = Predicate.objects\
                                    .filter(source_id=self.source_id,
                                            project_uuid=self.project_uuid,
                                            uuid=man_obj.uuid)\
                                    .delete()
                man_obj.delete()

    def delete_links_assertions(self):
        """ Deletes assertions usig linking predicates
        """
        if self.delete_ok:
            rem_assertions = Assertion.objects\
                                      .filter(source_id=self.source_id,
                                              project_uuid=self.project_uuid,
                                              subject_type__in=ImportProfile.DEFAULT_SUBJECT_TYPE_FIELDS,
                                              object_type__in=ImportProfile.DEFAULT_SUBJECT_TYPE_FIELDS)\
                                      .exclude(predicate_uuid=Assertion.PREDICATES_CONTAINS)\
                                      .delete()

    def delete_predicate_links(self, delete_custom=True):
        """ Deletes predicates that are links
        """
        if self.delete_ok:
            man_pred_vars = Manifest.objects\
                                    .filter(source_id=self.source_id,
                                            project_uuid=self.project_uuid,
                                            item_type='predicates',
                                            class_uri='link')
            for man_obj in man_pred_vars:
                # delete assertions using linking predicates from this source
                rem_assertions = Assertion.objects\
                                          .filter(source_id=self.source_id,
                                                  project_uuid=self.project_uuid,
                                                  predicate_uuid=man_obj.uuid)\
                                          .delete()
                if delete_custom:
                    ok_pred_delete = True
                else:
                    # Only delete custom, user added linking predicate if it is not
                    # in use for an import
                    impf_use = ImportFieldAnnotation.objects\
                                                    .filter(source_id=self.source_id,
                                                            predicate=man_obj.uuid)[:1]
                    if len(impf_use) < 1:
                        ok_pred_delete = True
                    else:
                        ok_pred_delete = False
                if ok_pred_delete:
                    rem_pred = Predicate.objects\
                                        .filter(source_id=self.source_id,
                                                project_uuid=self.project_uuid,
                                                uuid=man_obj.uuid)\
                                        .delete()
                    man_obj.delete()

    def delete_subjects_entities(self):
        """ Deletes subjects entities
            import
        """
        if self.delete_ok:
            #get rid of "subjects" manifest records from this source
            rem_manifest = Manifest.objects\
                                   .filter(source_id=self.source_id,
                                           project_uuid=self.project_uuid,
                                           item_type='subjects')\
                                   .delete()
            #get rid of subject records from this source
            rem_subject = Subject.objects\
                                 .filter(source_id=self.source_id,
                                         project_uuid=self.project_uuid)\
                                 .delete()

    def delete_person_entities(self):
        """ Deletes person entities
            import
        """
        if self.delete_ok:
            # get rid of "persons" manifest records from this source
            rem_manifest = Manifest.objects\
                                   .filter(source_id=self.source_id,
                                           project_uuid=self.project_uuid,
                                           item_type='persons')\
                                   .delete()
            # get rid of person records from this source
            rem_persons = Person.objects\
                                .filter(source_id=self.source_id,
                                        project_uuid=self.project_uuid)\
                                .delete()

    def delete_document_entities(self):
        """ Deletes document entities
            import
        """
        if self.delete_ok:
            # get rid of "documents" manifest records from this source
            rem_manifest = Manifest.objects\
                                   .filter(source_id=self.source_id,
                                           project_uuid=self.project_uuid,
                                           item_type='documents')\
                                   .delete()
            # get rid of person records from this source
            rem_documents = OCdocument.objects\
                                      .filter(source_id=self.source_id,
                                              project_uuid=self.project_uuid)\
                                      .delete()

    def delete_media_entities(self):
        """ Deletes media entities
            import
        """
        if self.delete_ok:
            # get rid of "persons" manifest records from this source
            rem_manifest = Manifest.objects\
                                   .filter(source_id=self.source_id,
                                           project_uuid=self.project_uuid,
                                           item_type='media')\
                                   .delete()
            # get rid of media records from this source
            rem_media = Mediafile.objects\
                                 .filter(source_id=self.source_id,
                                         project_uuid=self.project_uuid)\
                                 .delete()

    def delete_types_entities(self):
        """ Deletes types entities from an
            import
        """
        if self.delete_ok:
            #get rid of "types" manifest records from this source
            rem_manifest = Manifest.objects\
                                   .filter(source_id=self.source_id,
                                           project_uuid=self.project_uuid,
                                           item_type='types')\
                                   .delete()
           #get rid of types records from this source
            rem_type = OCtype.objects\
                             .filter(source_id=self.source_id,
                                     project_uuid=self.project_uuid)\
                             .delete()

    def delete_strings(self):
        """ Deletes containment assertions for an
            import
        """
        if self.delete_ok:
            rem_string = OCstring.objects\
                                 .filter(source_id=self.source_id,
                                         project_uuid=self.project_uuid)\
                                 .delete()
            self.update_complex_description_strings_source()
    
    def update_complex_description_strings_source(self):
        """ updates the source id for strings used on assertions made on complex-descriptions
            this is a measure to help make sure assertions about complex-descriptions
            do not get deleted at the start of importing normal descriptive assertions
        """
        if isinstance(self.COMPLEX_DESCRIPTION_SOURCE_SUFFIX, str) and self.delete_ok:
            source_id_w_suffix = self.source_id + self.COMPLEX_DESCRIPTION_SOURCE_SUFFIX
            up_strs =  OCstring.objects\
                               .filter(source_id=source_id_w_suffix,
                                       project_uuid=self.project_uuid)
            for up_str in up_strs:
                up_str.source_id = self.source_id
                up_str.save()

    def roubust_check_unimport_ok(self):
        """ Checks to see if it is OK to allow an unimport
        """
        ok = None
        source_last = False
        man_sums = Manifest.objects\
                           .filter(project_uuid=self.project_uuid)\
                           .values('source_id')\
                           .annotate(last=Max('revised'))
        for man_sum in man_sums:
            if man_sum['source_id'] == self.source_id:
                source_last = man_sum['last']
                break
        if source_last is not None and source_last is not False:
            for man_sum in man_sums:
                if source_last < man_sum['last']:
                    ok = False
                    break
            if ok is None:
                ok = True
        else:
            ok = self.check_unimport_ok()
        return ok

    def check_unimport_ok(self):
        """ Checks to see if it is OK to allow an unimport
        """
        ok = None
        p_sources = ImportSource.objects\
                                .filter(project_uuid=self.project_uuid)\
                                .order_by('-updated')
        first = True
        for p_source in p_sources:
            if first:
                first = False
                if p_source.source_id == self.source_id:
                    # the most recent import table is the table in question. OK to delete
                    ok = True
                    break
            else:
                if p_source.source_id != self.source_id and ok is None:
                    # check if the other source has anything in the manifest
                    man_objs = Manifest.objects\
                                       .filter(project_uuid=self.project_uuid,
                                               source_id=p_source.source_id)[:1]
                    if len(man_objs) > 1:
                        # OK. we've got data added after, so it's not OK to delete this source
                        ok = False
                        break
                else:
                    if ok is None:
                        ok = True
                        break
        return ok
