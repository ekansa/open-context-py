import sys
import csv
from time import sleep
from opencontext_py.apps.entities.uri.models import URImanagement
from opencontext_py.apps.entities.entity.models import Entity
from opencontext_py.apps.ldata.referencedby.api import csvAPI
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.ldata.linkannotations.models import LinkAnnotation
from opencontext_py.apps.ldata.linkannotations.equivalence import LinkEquivalence
from opencontext_py.apps.ldata.linkentities.models import LinkEntity


class ManageReferencesBy():
    """ methods to add referenced by link annotations
        for content referenced by an external source
    """

    DC_TERMS_REFERENCED_BY = 'dc-terms:isReferencedBy'

    def __init__(self):
        self.source_id = 'remote-csv-data'
        self.referrer = Referrer()
        self.new_annotations = 0

    def save_csv_annotations(self, csv_url):
        """ saves annotations for a referrer from a csv source
        """
        # prepare the referrer object, make sure it is valid
        self.referrer.prepare()
        if self.referrer.valid:
            # we have a valid referrer object, we can
            # now make annotations about it referencing OC content
            csv_api = csvAPI()
            csv_data = csv_api.get_read_csv(csv_url)
            if csv_data is not False:
                row_num = 0
                for row in csv_data:
                    row_num += 1
                    print('Reading row: ' + str(row_num))
                    for cell in row:
                        oc_item = self.check_opencontext_uri(cell)
                        if oc_item is not False:
                            self.save_new_ref_by_annotation(oc_item)
            else:
                print('Problem with getting the CSV data')
        else:
            print('Problem with the referrer object')

    def save_new_ref_by_annotation(self, oc_item):
        """ saves a refferenced by annotation if it is new """
        is_new = self.check_new_annotation(oc_item.uuid, self.referrer.uri)
        if is_new:
            self.new_annotations += 1
            la = LinkAnnotation()
            la.subject = oc_item.uuid
            la.subject_type = oc_item.item_type
            la.project_uuid = oc_item.project_uuid
            la.source_id = self.source_id
            la.predicate_uri = self.DC_TERMS_REFERENCED_BY
            la.object_uri = self.referrer.uri
            la.creator_uuid = ''
            la.save()
            print('[' + str(self.new_annotations) + '] annotated: ' + oc_item.uuid)

    def check_opencontext_uri(self, cell):
        """ looks for a valid opencontext uri in a cell """
        oc_item = False
        if 'http://opencontext.' in cell\
           or 'https://opencontext.' in cell:
            uuid = URImanagement.get_uuid_from_oc_uri(cell)
            if isinstance(uuid, str):
                # appears to be an Open Context URI
                # now check we actually have that entity in the database
                try:
                    oc_item = Manifest.objects.get(uuid=uuid)
                except Manifest.DoesNotExist:
                    oc_item = False
        return oc_item

    def check_new_annotation(self, subject, object_uri):
        """ checks to make sure we have a new annotation """
        is_new = False
        # very comprehensive validation for all variants of subject, predicates and object identifiers
        link_equiv = LinkEquivalence()
        subject_list = link_equiv.get_identifier_list_variants(subject)
        predicate_list = link_equiv.get_identifier_list_variants(self.DC_TERMS_REFERENCED_BY)
        object_list = link_equiv.get_identifier_list_variants(object_uri)
        anno_list = LinkAnnotation.objects\
                                  .filter(subject__in=subject_list,
                                          predicate_uri__in=predicate_list,
                                          object_uri__in=object_list)[:1]
        if len(anno_list) < 1:
            is_new = True
        return is_new


class Referrer():
    """ The source of references to data in Open Context
        this is used in cases where the source does not
        have granular URIs to associate specific records
        to records in Open Context
    """

    def __init__(self):
        self.uri = False
        self.label = False
        self.alt_label = ''
        self.vocab_label = False
        self.vocab_alt_label = ''
        self.vocab_uri = False
        self.valid = False

    def prepare(self):
        """ checks to make sure the referrer actually exists
            in the database
        """
        if self.uri is not False:
            ent = Entity()
            found = ent.dereference(self.uri)
            if found:
                self.label = ent.label
                self.alt_label = ent.alt_label
                self.vocab_label = ent.vocabulary
                self.vocab_uri = ent.vocab_uri
                self.valid = True
            else:
                # the referring source is not known in the database
                if self.vocab_uri is not False\
                   and self.vocab_label is not False\
                   and self.label is not False:
                    # we have enough data to save a referrer in the database
                    referrer_ent_type = 'vocabulary'
                    if self.vocab_uri != self.uri:
                        referrer_ent_type = 'class'
                        ent_v = Entity()
                        found_v = ent_v.dereference(self.vocab_uri)
                        if found_v is False:
                            # the referring vocabulary is not known in the database
                            # so we need to create it
                            lev = LinkEntity()
                            lev.uri = self.vocab_uri
                            lev.label = self.vocab_label
                            lev.alt_label = self.vocab_alt_label
                            lev.vocab_uri = self.vocab_uri
                            lev.ent_type = 'vocabulary'
                            lev.save()
                    # now are ready to make a linked entity for the referrer
                    le = LinkEntity()
                    le.uri = self.uri
                    le.label = self.label
                    le.alt_label = self.alt_label
                    le.vocab_uri = self.vocab_uri
                    le.ent_type = referrer_ent_type
                    le.save()
                    self.valid = True
