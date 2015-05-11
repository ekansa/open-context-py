from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.apps.ldata.periodo.api import PeriodoAPI
from opencontext_py.apps.entities.entity.models import Entity
from opencontext_py.apps.ldata.linkentities.models import LinkEntity
from opencontext_py.apps.ldata.linkannotations.equivalence import LinkEquivalence
from opencontext_py.apps.ldata.linkannotations.models import LinkAnnotation


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
                    objects = lequiv.get_identifier_list_variants(period['period-meta']['uri'])
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
                        new_la.object_uri = period['period-meta']['uri']
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

    def check_add_period(self, p_ref):
        """ Checks to see if a period collection is in
            the database, adds it if needed
        """
        if not p_ref['period-meta']['uri'] in self.db_uris:
            # not in memory for being in the database
            lev = LinkEntity.objects.filter(uri=p_ref['period-meta']['uri'])[:1]
            if len(lev) < 1:
                le = LinkEntity()
                le.uri = p_ref['period-meta']['uri']
                le.label = p_ref['period-meta']['label'] \
                           + '(' + p_ref['period-meta']['range'] + ')'
                le.alt_label = p_ref['period-meta']['label'] \
                           + '(' + p_ref['period-meta']['range'] + ')'
                le.vocab_uri = p_ref['collection']['uri']
                le.ent_type = 'class'
                le.save()
            self.db_uris.append(p_ref['period-meta']['uri'])

    def check_add_period_collection(self, p_ref):
        """ Checks to see if a period collection is in
            the database, adds it if needed
        """
        if not p_ref['collection']['uri'] in self.db_uris:
            # not in memory for being in the database
            lev = LinkEntity.objects.filter(uri=p_ref['collection']['uri'])[:1]
            if len(lev) < 1:
                le = LinkEntity()
                le.uri = p_ref['collection']['uri']
                le.label = 'PeriodO Collection: ' + p_ref['collection']['label']
                le.alt_label = 'PeriodO (http://perio.do): ' + p_ref['collection']['label']
                le.vocab_uri = self.PERIODO_VOCAB_URI
                le.ent_type = 'vocabulary'
                le.save()
            self.db_uris.append(p_ref['collection']['uri'])

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

    def delete_periodo_annotations(self):
        """ deletes period0 annoations """
        delete = LinkAnnotation.objects\
                               .filter(source_id=self.source_id)\
                               .delete()
        