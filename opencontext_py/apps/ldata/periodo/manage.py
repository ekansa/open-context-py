import re
from unidecode import unidecode
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.apps.ldata.periodo.api import PeriodoAPI
from opencontext_py.apps.entities.entity.models import Entity
from opencontext_py.apps.ldata.linkentities.models import LinkEntity
from opencontext_py.apps.ldata.linkannotations.equivalence import LinkEquivalence
from opencontext_py.apps.ldata.linkannotations.models import LinkAnnotation
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.ocitems.subjects.models import Subject
from opencontext_py.apps.ocitems.assertions.models import Assertion


class PeriodoLink():
    """ Relates data originally exported from Open Context
        with PeriodO URIs
    """
    PERIODO_VOCAB_URI = 'http://n2t.net/ark:/99152/p0'
    DC_PERIOD_PRED = 'dc-terms:temporal'

    def __init__(self):
        self.periodo_data = False
        self.db_uris = [] # list of entities already in the database
        self.source_id = 'PeriodO'
        self.update_period = False

    def reconcile_oc_subjects_to_periodo(self,
                                         project_uuid,
                                         class_uri,
                                         period_predicate_uuid,
                                         periodo_vocab_uri,
                                         label_mappings=None):
        """ reconciles open context types, used with a
            given 'period_predicate_uuid' for a list
            of subjects (selected by project_uuid and class_uri).
            The first part of the subject item context path is used for
            the geographic scope of the period.
            This adds the periodo annotation directly to the
            subject item, becase a given type (like 'Mesolithic')
            in a given dataset may actually relate to different
            PeriodO periods with different geographic scopes.
            
from opencontext_py.apps.ldata.periodo.manage import PeriodoLink
po_link = PeriodoLink()
project_uuid = '1816A043-92E2-471D-A23D-AAC58695D0D3'
class_uri = 'oc-gen:cat-animal-bone'
period_predicate_uuid = '011b2240-5931-48af-8ef7-adef665266e3'
periodo_vocab_uri = 'http://n2t.net/ark:/99152/p0qhb66'
label_mappings = {
    'Upper Pleistocene - Epigravettian': [
        'Upper Pleistocene',
        'Epigravettian'
    ],
    'Middle Pleistocene, Marine Isotope Stage 9': [
        'Middle Pleistocene'
    ],
    'Middle-Late Neolithic': [
        'Middle Neolithic',
        'Late Neolithic'
    ],
    'Late Bronze-Early Iron Age': [
        'Late Bronze Age',
        'Early Iron Age'
    ],
    'Middle Pleistocene, Marine Isotope Stage 4': [
        'Middle Pleistocene'
    ],
    'Late Mousterian to Aurignacian': [
        'Late Mousterian',
        'Aurignacian',
        'Early Upper Paleolithic'
    ],
    'Middle Pleistocene, Marine Isotope Stage 7': [
        'Middle Pleistocene'
    ],
    'Mesolithic - Pollen Zone VI': [
        'Mesolithic'
    ],
    'Early/Middle Neolithic': [
        'Early Neolithic',
        'Middle Neolithic'
    ],
    'Mesolithic-Neolithic': [
        'Mesolithic',
        'Neolithic'
    ],
    'Neolithic-Chalcolithic': [
        'Neolithic',
        'Chalcolithic'
    ],
    'Chalcolithic-Bronze Age': [
        'Chalcolithic',
        'Bronze Age'
    ],
    'Mesolithic - Pollen Zone V': [
        'Mesolithic'
    ],
    'Bronze Age-Iron Age': [
        'Bronze Age',
        'Iron Age'
    ],
    'Early Neolithic - Pollen Zone VII': [
        'Early Neolithic'    
    ],
    'Early Neolithic - Pollen Zone VIII': [
        'Early Neolithic'    
    ],
    'Mousterian-Late Palaeolithic (C1)': [
        'Mousterian',
        'Late Palaeolithic',
        'Upper Palaeolithic'
    ],
}
po_link.reconcile_oc_subjects_to_periodo(project_uuid,
                                         class_uri,
                                         period_predicate_uuid,
                                         periodo_vocab_uri,
                                         label_mappings)
        """
        # 1st step loads PeriodO collection data
        collection = self.get_periodo_collection(periodo_vocab_uri)
        if isinstance(collection, dict):
            po_api = PeriodoAPI()
            po_api.periodo_data = self.periodo_data
            # Next step makes a list of uuids for each root context
            context_subject_uuids = {}
            man_list = Manifest.objects\
                               .filter(project_uuid=project_uuid,
                                       class_uri=class_uri)
            for man_item in man_list:
                try:
                    sub_item = Subject.objects.get(uuid=man_item.uuid)
                except Subjects.DoesNotExist:
                    sub_item = False
                if sub_item is not False:
                    context_ex = sub_item.context.split('/')
                    root_context = context_ex[0]
                    if root_context not in context_subject_uuids:
                        context_subject_uuids[root_context] = []
                    context_subject_uuids[root_context].append(man_item.uuid)
            for root_context, subject_uuids in context_subject_uuids.items():
                # next step is to query for unique contrutor defined period types used
                # with subjects in a given root context
                context_periods = []
                for p_id_key, period in collection['definitions'].items():
                    period_meta = po_api.get_period_metadata(p_id_key, period)
                    if root_context in period_meta['coverage']:
                        context_periods.append(period_meta)
                ass_per_types = Assertion.objects\
                                         .filter(uuid__in=subject_uuids,
                                                 predicate_uuid=period_predicate_uuid)\
                                         .order_by('object_uuid')\
                                         .distinct('object_uuid')
                for ass_type in ass_per_types:
                    try:
                        man_type = Manifest.objects.get(uuid=ass_type.object_uuid)
                    except Manifest.DoesNotExist:
                        man_type = False
                    if man_type is not False:
                        # strip content in paretheses
                        period_label = re.sub(r'\([^)]*\)', '', man_type.label)
                        period_label = period_label.strip()
                        period_labels = [period_label]
                        if isinstance(label_mappings, dict):
                            if period_label in label_mappings:
                                period_labels == label_mappings[period_label]
                        for check_label in period_labels:
                            print('Checking for: ' + str(unidecode(check_label)))
                            print('[Context: ' + str(unidecode(root_context)) + ']')
                            for period in context_periods:
                                if check_label in period['all_labels']:
                                    print('Match!')

    def add_period_coverage(self, uuid, period_uri):
        """ Adds an periodo uri annotation to an item
        """
        ok = False
        po_api = PeriodoAPI()
        if not isinstance(self.periodo_data, dict):
            self.check_add_period_pred()
            po_api.get_periodo_data()
            self.periodo_data = po_api.periodo_data
        else:
            po_api.periodo_data = self.periodo_data
        if isinstance(po_api.periodo_data, dict):
            
            period = po_api.get_period_by_uri(period_uri)
            if isinstance(period, dict):
                # we found the period, now check the UUID
                # is found
                entity = Entity()
                found = entity.dereference(uuid)
                if found:
                    # save the period collection entity to database, if needed
                    self.check_add_period_collection(period)
                    # save the period entity to the database, if needed
                    self.check_add_period(period)
                    # check to make sure the annotation does not yet exist
                    # do so by checking all possible varients in expressing
                    # this annotation
                    lequiv = LinkEquivalence()
                    subjects = lequiv.get_identifier_list_variants(uuid)
                    predicates = lequiv.get_identifier_list_variants(self.DC_PERIOD_PRED)
                    objects = lequiv.get_identifier_list_variants(period_uri)
                    la_exists = LinkAnnotation.objects\
                                              .filter(subject__in=subjects,
                                                      predicate_uri__in=predicates,
                                                      object_uri__in=objects)[:1]
                    if len(la_exists) < 1:
                        # OK save to make the annotation
                        new_la = LinkAnnotation()
                        new_la.subject = entity.uuid
                        new_la.subject_type = entity.item_type
                        new_la.project_uuid = entity.project_uuid
                        new_la.source_id = self.source_id
                        new_la.predicate_uri = self.DC_PERIOD_PRED
                        new_la.object_uri = period_uri
                        new_la.creator_uuid = ''
                        new_la.save()
                        ok = True
        return ok

    def get_relate_oc_periods(self):
        """ Gets period-o data, checks for references to open context
            then updates link annotations with references
        """
        self.delete_periodo_annotations()
        self.check_add_periodo_vocab()
        po_api = PeriodoAPI()
        po_api.get_periodo_data()
        self.periodo_data = po_api.periodo_data
        oc_refs = po_api.get_oc_periods()
        if isinstance(oc_refs, list):
            for p_ref in oc_refs:
                # make an annotation if item is in Open Context
                ok = self.add_period_annoation(p_ref)
                if ok:
                    # create the period collection, if new
                    self.check_add_period_collection(p_ref)
                    # create the period, if new
                    self.check_add_period(p_ref)

    def add_period_annoation(self, p_ref):
        """ adds a period annotation """
        entity = Entity()
        found = entity.dereference(p_ref['oc-uri'])
        if found:
            new_la = LinkAnnotation()
            new_la.subject = entity.uuid
            new_la.subject_type = entity.item_type
            new_la.project_uuid = entity.project_uuid
            new_la.source_id = self.source_id
            new_la.predicate_uri = 'dc-terms:isReferencedBy'
            new_la.object_uri = p_ref['period-meta']['uri']
            new_la.creator_uuid = ''
            new_la.save()
        return found

    def check_add_period(self, p_ref, vocab_uri):
        """ Checks to see if a period collection is in
            the database, adds it if needed
        """
        if isinstance(p_ref, dict):
            uri = PeriodoAPI.URI_PREFIX + p_ref['id']
            if not uri in self.db_uris:
                # not in memory for being in the database
                lev = LinkEntity.objects.filter(uri=uri)[:1]
                if len(lev) < 1 or self.update_period:
                    le = LinkEntity()
                    le.uri = uri
                    le.label = p_ref['label']
                    le.alt_label = p_ref['alt_label']
                    le.vocab_uri = vocab_uri
                    le.ent_type = 'class'
                    le.save()
                self.db_uris.append(uri)

    def check_add_period_collection(self, p_ref):
        """ Checks to see if a period collection is in
            the database, adds it if needed
        """
        if isinstance(p_ref, dict):
            uri = PeriodoAPI.URI_PREFIX + p_ref['id']
            if not uri in self.db_uris:
                # not in memory for being in the database
                lev = LinkEntity.objects.filter(uri=uri)[:1]
                if len(lev) < 1 or self.update_period:
                    le = LinkEntity()
                    le.uri = uri
                    le.label = 'PeriodO Collection: ' + p_ref['source']['title']
                    le.alt_label = 'PeriodO (http://perio.do): ' + p_ref['source']['title']
                    le.vocab_uri = self.PERIODO_VOCAB_URI
                    le.ent_type = 'vocabulary'
                    le.save()
                self.db_uris.append(uri)

    def check_add_periodo_vocab(self):
        """ Adds the periodo vocabulary if it doesn't exist yet
        """
        lev = LinkEntity.objects.filter(uri=self.PERIODO_VOCAB_URI)[:1]
        if len(lev) < 1:
            le = LinkEntity()
            le.uri = self.PERIODO_VOCAB_URI
            le.label = 'PeriodO'
            le.alt_label = 'PeriodO (http://perio.do)'
            le.vocab_uri = self.PERIODO_VOCAB_URI
            le.ent_type = 'vocabulary'
            le.save()

    def check_add_period_pred(self):
        """ Adds the periodo vocabulary if it doesn't exist yet
        """
        temporal_pred = 'http://purl.org/dc/terms/temporal'
        lev = LinkEntity.objects.filter(uri=temporal_pred)[:1]
        if len(lev) < 1:
            le = LinkEntity()
            le.uri = temporal_pred
            le.label = 'Temporal Coverage'
            le.alt_label = 'Temporal Coverage'
            le.vocab_uri = 'http://purl.org/dc/terms'
            le.ent_type = 'property'
            le.save()

    def get_periodo_collection(self, collection_uri):
        """ gets JSON for a periodO collection
            by loading data from PeriodO
        """
        po_api = PeriodoAPI()
        if not isinstance(self.periodo_data, dict):
            po_api.get_periodo_data()
            self.periodo_data = po_api.periodo_data
        else:
            po_api.periodo_data = self.periodo_data
        collection = po_api.get_period_collection(collection_uri)
        return collection
            
    
    def delete_periodo_annotations(self):
        """ deletes period0 annoations """
        delete = LinkAnnotation.objects\
                               .filter(source_id=self.source_id)\
                               .delete()
        