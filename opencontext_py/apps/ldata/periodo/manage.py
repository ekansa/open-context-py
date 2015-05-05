from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.apps.ldata.periodo.api import PeriodoAPI
from opencontext_py.apps.entities.entity.models import Entity
from opencontext_py.apps.ldata.linkentities.models import LinkEntity
from opencontext_py.apps.ldata.linkannotations.models import LinkAnnotation


class PeriodoLink():
    """ Relates data originally exported from Open Context
        with PeriodO URIs
    """
    PERIODO_VOCAB_URI = 'http://n2t.net/ark:/99152/p0'
    
    def __init__(self):
        self.periodo_data = False
        self.db_uris = [] # list of entities already in the database

    def get_relate_oc_periods(self):
        """ Gets period-o data, checks for references to open context
            then updates link annotations with references
        """
        self.check_add_periodo_vocab()
        po_api = PeriodoAPI()
        po_api.get_periodo_data()
        oc_refs = po_api.get_oc_periods()
        if isinstance(oc_refs, list):
            for oc_ref in oc_refs:
                # make an annotation if item is in Open Context
                ok = self.add_period_annoation(oc_ref)
                if ok:
                    # create the period collection, if new
                    self.check_add_period_collection(oc_ref)
                    # create the period, if new
                    self.check_add_period(oc_ref)
                
    def add_period_annoation(self, oc_ref):
        """ adds a period annotation """
        entity = Entity()
        found = entity.dereference(oc_ref['oc-uri'])
        if found:
            new_la = LinkAnnotation()
            new_la.subject = entity.uuid
            new_la.subject_type = entity.item_type
            new_la.project_uuid = entity.project_uuid
            new_la.source_id = 'PeriodO'
            new_la.predicate_uri = 'skos:closeMatch'
            new_la.object_uri = oc_ref['period_uri']
            new_la.creator_uuid = ''
            new_la.save()
        return found
    
    
    def check_add_period(self, oc_ref):
        """ Checks to see if a period collection is in
            the database, adds it if needed
        """
        if not oc_ref['period_uri'] in self.db_uris:
            # not in memory for being in the database
            lev = LinkEntity.objects.filter(uri=oc_ref['period_uri'])[:1]
            if len(lev) < 1:
                le = LinkEntity()
                le.uri = oc_ref['period_uri']
                le.label = oc_ref['period_label']
                le.alt_label = oc_ref['period_label']
                le.vocab_uri = oc_ref['collection_uri']
                le.ent_type = 'class'
                le.save()
            self.db_uris.append(oc_ref['period_uri'])
            
    def check_add_period_collection(self, oc_ref):
        """ Checks to see if a period collection is in
            the database, adds it if needed
        """
        if not oc_ref['collection_uri'] in self.db_uris:
            # not in memory for being in the database
            lev = LinkEntity.objects.filter(uri=oc_ref['collection_uri'])[:1]
            if len(lev) < 1:
                le = LinkEntity()
                le.uri = oc_ref['collection_uri']
                le.label = 'PeriodO Collection: ' + oc_ref['collection_label']
                le.alt_label = 'PeriodO (http://perio.do): ' + oc_ref['collection_label']
                le.vocab_uri = self.PERIODO_VOCAB_URI
                le.ent_type = 'vocabulary'
                le.save()
            self.db_uris.append(oc_ref['collection_uri'])
        
    
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