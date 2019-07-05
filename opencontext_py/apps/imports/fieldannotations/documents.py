import uuid as GenUUID
from django.conf import settings
from django.db import models
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.ocitems.documents.models import OCdocument
from opencontext_py.apps.imports.fields.models import ImportField
from opencontext_py.apps.imports.fieldannotations.models import ImportFieldAnnotation
from opencontext_py.apps.imports.records.models import ImportCell
from opencontext_py.apps.imports.records.process import ProcessCells
from opencontext_py.apps.imports.fieldannotations.general import ProcessGeneral
from opencontext_py.apps.imports.fieldannotations.metadata import ManifestMetadata
from opencontext_py.apps.imports.sources.unimport import UnImport


# Processes to generate document items for an import
class ProcessDocuments():

    def __init__(self, source_id):
        self.source_id = source_id
        pg = ProcessGeneral(source_id)
        pg.get_source()
        self.project_uuid = pg.project_uuid
        # object for associated metadata to new manifest objects
        self.metadata_obj = ManifestMetadata(self.source_id,
                                             self.project_uuid)
        self.documents_fields = []
        self.start_row = 1
        self.batch_size = settings.IMPORT_BATCH_SIZE
        self.end_row = self.batch_size
        self.count_active_fields = 0
        self.new_entities = []
        self.reconciled_entities = []
        self.not_reconciled_entities = []

    def clear_source(self):
        """ Clears a prior import if the start_row is 1.
            This makes sure new entities and assertions are made for
            this source_id, and we don't duplicate things
        """
        if self.start_row <= 1:
            # get rid of "documents" related assertions made from this source
            unimport = UnImport(self.source_id,
                                self.project_uuid)
            unimport.delete_document_entities()

    def process_documents_batch(self):
        """ processes fields for documents
            entities starting with a given row number.
            This iterates over all containment fields, starting
            with the root subjhect field
        """
        self.clear_source()  # clear prior import for this source
        self.end_row = self.start_row + self.batch_size
        self.get_documents_fields()
        self.get_metadata_fields()
        if len(self.documents_fields) > 0:
            print('Number of Document Fields: ' + str(len(self.documents_fields)))
            for field_obj in self.documents_fields:
                pc = ProcessCells(self.source_id,
                                  self.start_row)
                distinct_records = pc.get_field_records(field_obj.field_num,
                                                        False)
                if distinct_records is not False:
                    print('Distinct document recs: ' + str(len(distinct_records)))
                    for rec_hash, dist_rec in distinct_records.items():
                        content = None
                        if isinstance(field_obj.doc_text_field_num, int):
                            # we have a related document text content field
                            # get the text for the document in the first row
                            doc_text_rows = ImportCell.objects\
                                                      .filter(source_id=self.source_id,
                                                              field_num=field_obj.doc_text_field_num,
                                                              row_num=dist_rec['rows'][0])[:1]
                            if len(doc_text_rows) > 0:
                                # we found text content associated with this set
                                content = doc_text_rows[0].record
                        cd = CandidateDocument()
                        cd.project_uuid = self.project_uuid
                        cd.source_id = self.source_id
                        cd.label = field_obj.field_value_cat
                        if isinstance(content, str):
                            # we found content to add to the document.
                            cd.content = content
                        cd.import_rows = dist_rec['rows']  # list of rows where this record value is found
                        cd.metadata_obj = self.metadata_obj
                        cd.reconcile_item(dist_rec['imp_cell_obj'])
                        if cd.uuid is not False:
                            if cd.new_entity:
                                self.new_entities.append({'id': str(cd.uuid),
                                                          'label': cd.label})
                            else:
                                self.reconciled_entities.append({'id': str(cd.uuid),
                                                                 'label': cd.label})
                        else:
                            bad_id = str(dist_rec['imp_cell_obj'].field_num)
                            bad_id += '-' + str(dist_rec['imp_cell_obj'].row_num)
                            self.not_reconciled_entities.append({'id': str(bad_id),
                                                                 'label': dist_rec['imp_cell_obj'].record})

    def get_documents_fields(self):
        """ Makes a list of document fields
        """
        doc_text = ImportFieldAnnotation.PRED_DOC_Text
        working_doc_fields = []
        fields_used_as_doc_text = []
        raw_documents_fields = ImportField.objects\
                                          .filter(source_id=self.source_id,
                                                  field_type='documents')
        for doc_field_obj in raw_documents_fields:
            doc_text_fields = ImportFieldAnnotation.objects\
                                                   .filter(source_id=self.source_id,
                                                           field_num=doc_field_obj.field_num,
                                                           predicate=doc_text)[:1]
            if len(doc_text_fields) > 0:
                # the document field links to a document text content field
                # add an attribute to the field object to note the relation
                doc_field_obj.doc_text_field_num = doc_text_fields[0].object_field_num
                # make a list of document fields that are text content of other fields
                fields_used_as_doc_text.append(doc_text_fields[0].object_field_num)
            else:
                # this document field does not have a link to a text content field
                doc_field_obj.doc_text_field_num = False
            working_doc_fields.append(doc_field_obj)
        for doc_field_obj in working_doc_fields:
            if doc_field_obj.field_num not in fields_used_as_doc_text:
                # only add document fields not used as text content fields for other doc fields
                self.documents_fields.append(doc_field_obj)
        self.count_active_fields = len(self.documents_fields)
        return self.documents_fields

    def get_metadata_fields(self):
        """ finds metadata fields that get added to the the sup_json
            field of new manifest objects
        """
        # first make a list of subject field numbers
        if len(self.documents_fields) > 0:
            doc_field_nums = []
            for field_obj in self.documents_fields:
                doc_field_nums.append(field_obj.field_num)
            self.metadata_obj.get_metadata_fields_for_field_list(doc_field_nums)

class CandidateDocument():

    DEFAULT_NO_CONTENT = '[No text content yet imported]'
    
    def __init__(self):
        self.project_uuid = False
        self.source_id = False
        self.label = False
        self.content = self.DEFAULT_NO_CONTENT
        self.uuid = False  # final, uuid for the item
        self.imp_cell_obj = False  # ImportCell object
        self.import_rows = False
        self.new_entity = False
        self.metadata_obj = None

    def reconcile_item(self, imp_cell_obj):
        """ Checks to see if the item exists """
        self.imp_cell_obj = imp_cell_obj
        if len(imp_cell_obj.record) > 0:
            self.label = imp_cell_obj.record
        else:
            pg = ProcessGeneral(self.source_id)
            if self.import_rows is not False:
                check_list = self.import_rows
            else:
                check_list = [imp_cell_obj.row_num]
        
        # Set up to check for a preconfigured metadata UUID.
        meta_uuid = None
        sup_metadata = None
        if self.metadata_obj is not None:
            # Get the suplemental metadata that may exist.
            sup_metadata = self.metadata_obj.get_metadata(
                imp_cell_obj.field_num,
                imp_cell_obj.row_num
            )
            meta_uuid = self.metadata_obj.get_uuid_from_metadata_dict(sup_metadata)
            if not isinstance(meta_uuid, str):
                meta_uuid = None
        
        # Handle reconciliation cases where we have a pre-configured UUID to use
        # in the metadata_obj. Only do this if there's actually a label (not a blank).
        if meta_uuid and self.label:
            # Check to see if this already exists.
            man_obj = Manifest.objects.filter(uuid=meta_uuid).first()
            if man_obj:
                print('Found manifest object {} ({}) for pre-specified uuid: {}'.format(
                        man_obj.label,
                        man_obj.item_type,
                        meta_uuid
                    )
                )
                self.uuid = meta_uuid
                self.new_entity = False
                match_found = True
            else:
                print('Create new manifest object {} (documents) with pre-specified uuid: {}'.format(
                        self.label,
                        meta_uuid
                    )
                )
                match_found = False
                self.uuid = meta_uuid
                self.new_entity = True
                self.create_document_item(sup_metadata)
        
        elif self.label:
            match_found = self.match_against_documents(self.label)
            if match_found is False:
                # create new document, manifest objects.
                self.new_entity = True
                self.uuid = GenUUID.uuid4()
                self.create_document_item(None)
        
        if self.uuid:
            act_doc = OCdocument.objects.filter(uuid=self.uuid).first()
            if act_doc is None:
                # We have a manifest record for the document, but no document record,
                # so make one
                act_doc = OCdocument()
                act_doc.uuid = self.uuid  # use the previously assigned temporary UUID
                act_doc.project_uuid = self.project_uuid
                act_doc.source_id = self.source_id
                act_doc.content = self.content
                act_doc.save()

            if act_doc.content != self.content and self.content != self.DEFAULT_NO_CONTENT:
                # update the document content with the latest content
                act_doc.content = self.content
                act_doc.save()
        self.update_import_cell_uuid()

    def create_document_item(self, sup_metadata=None):
        """ Create and save a new subject object"""
        new_doc = OCdocument()
        new_doc.uuid = self.uuid  # use the previously assigned temporary UUID
        new_doc.project_uuid = self.project_uuid
        new_doc.source_id = self.source_id
        new_doc.content = self.content
        new_doc.save()
        new_man = Manifest()
        new_man.uuid = self.uuid
        new_man.project_uuid = self.project_uuid
        new_man.source_id = self.source_id
        new_man.item_type = 'documents'
        new_man.repo = ''
        new_man.class_uri = ''
        new_man.label = self.label
        new_man.des_predicate_uuid = ''
        new_man.views = 0
        if isinstance(sup_metadata, dict):
            new_man.sup_json = sup_metadata
        new_man.save()

    def update_import_cell_uuid(self):
        """ Saves the uuid to the import cell record """
        if self.uuid is not False:
            if self.imp_cell_obj.fl_uuid != self.uuid:
                up_cells = ImportCell.objects\
                                     .filter(source_id=self.source_id,
                                             field_num=self.imp_cell_obj.field_num,
                                             rec_hash=self.imp_cell_obj.rec_hash)
                for up_cell in up_cells:
                    # save each cell with the correct UUID
                    up_cell.fl_uuid = self.uuid
                    up_cell.cell_ok = True
                    up_cell.save()

    def match_against_documents(self, label):
        """ Checks to see if the item exists in the manifest table """
        match_found = False
        man_objs = Manifest.objects\
                           .filter(project_uuid=self.project_uuid,
                                   label=label,
                                   item_type='documents')[:1]
        if len(man_objs) > 0:
            match_found = True
            self.uuid = man_objs[0].uuid
        return match_found
