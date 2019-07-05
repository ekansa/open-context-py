from time import sleep
import uuid as GenUUID
from django.conf import settings
from django.db import models
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.ocitems.mediafiles.models import Mediafile
from opencontext_py.apps.imports.fields.models import ImportField
from opencontext_py.apps.imports.fieldannotations.models import ImportFieldAnnotation
from opencontext_py.apps.imports.records.models import ImportCell
from opencontext_py.apps.imports.records.process import ProcessCells
from opencontext_py.apps.imports.fieldannotations.general import ProcessGeneral
from opencontext_py.apps.imports.fieldannotations.metadata import ManifestMetadata
from opencontext_py.apps.imports.sources.unimport import UnImport


# Processes to generate media items for an import
class ProcessMedia():

    def __init__(self, source_id):
        self.source_id = source_id
        pg = ProcessGeneral(source_id)
        pg.get_source()
        self.project_uuid = pg.project_uuid
        # object for associated metadata to new manifest objects
        self.metadata_obj = ManifestMetadata(self.source_id,
                                             self.project_uuid)
        self.media_fields = []
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
            # get rid of "subjects" related assertions made from this source
            unimport = UnImport(self.source_id,
                                self.project_uuid)
            unimport.delete_media_entities()

    def process_media_batch(self):
        """ process media items
        """
        self.clear_source()  # clear prior import for this source
        self.end_row = self.start_row + self.batch_size
        single_media_field = self.process_single_media_label_field()
        if single_media_field is False:
            # only do this if the single media field is False
            self.process_multiple_media_fields()

    def process_multiple_media_fields(self):
        """ processes multiple media fields, if they exist """
        self.get_media_fields()
        self.get_metadata_fields()
        if len(self.media_fields) > 0:
            print('yes we have media')
            for field_obj in self.media_fields:
                pc = ProcessCells(self.source_id,
                                  self.start_row)
                distinct_records = pc.get_field_records(field_obj.field_num,
                                                        False)
                if distinct_records is not False:
                    print('Found Media Records: ' + str(len(distinct_records)))
                    for rec_hash, dist_rec in distinct_records.items():
                        # print('Checking on: ' + dist_rec['imp_cell_obj'].record)
                        cm = CandidateMedia()
                        cm.project_uuid = self.project_uuid
                        cm.source_id = self.source_id
                        cm.class_uri = field_obj.field_value_cat
                        cm.import_rows = dist_rec['rows']  # list of rows where this record value is found
                        cm.metadata_obj = self.metadata_obj
                        cm.reconcile_manifest_item(dist_rec['imp_cell_obj'])
                        if cm.uuid is not False:
                            if cm.new_entity:
                                self.new_entities.append({'id': str(cm.uuid),
                                                          'label': cm.label})
                            else:
                                self.reconciled_entities.append({'id': str(cm.uuid),
                                                                 'label': cm.label})
                            # we have a media item! Now we can add files to it
                            for part_field_obj in field_obj.parts:
                                pc = ProcessCells(self.source_id,
                                                  self.start_row)
                                part_dist_records = pc.get_field_records(part_field_obj.field_num,
                                                                         cm.import_rows)
                                if part_dist_records is not False:
                                    for rec_hash, part_dist_rec in part_dist_records.items():
                                        # distinct records for the media file parts of a media item
                                        cmf = CandidateMediaFile(cm.uuid)
                                        cmf.imp_cell_obj = part_dist_rec['imp_cell_obj']
                                        cmf.project_uuid = self.project_uuid
                                        cmf.source_id = self.source_id
                                        # file type is in the field_value_cat
                                        cmf.file_type = part_field_obj.field_value_cat
                                        file_uri = part_dist_rec['imp_cell_obj'].record
                                        if file_uri[:7] == 'http://' \
                                           or file_uri[:8] == 'https://':
                                            # its a URI part
                                            cmf.reconcile_media_file(file_uri)
                        else:
                            bad_id = str(dist_rec['imp_cell_obj'].field_num)
                            bad_id += '-' + str(dist_rec['imp_cell_obj'].row_num)
                            self.not_reconciled_entities.append({'id': bad_id,
                                                                 'label': dist_rec['imp_cell_obj'].record})

    def process_single_media_label_field(self):
        """Processes only media field, it does not
           create new media, only reconciles existing already imported
           media
        """
        single_media_field = False
        media_fields = ImportField.objects\
                                  .filter(source_id=self.source_id,
                                          field_type='media')
        if len(media_fields) == 1:
            # only for the 1 media field in an import source
            single_media_field = True
            print('yes we have 1 media field')
            field_obj = media_fields[0]
            # make the metadata fields for this one media field
            media_field_nums = [field_obj.field_num]
            self.get_metadata_fields(media_field_nums)
            pc = ProcessCells(self.source_id,
                              self.start_row)
            distinct_records = pc.get_field_records(field_obj.field_num,
                                                    False)
            if distinct_records is not False:
                print('Found Media Records: ' + str(len(distinct_records)))
                for rec_hash, dist_rec in distinct_records.items():
                    # print('Checking on: ' + dist_rec['imp_cell_obj'].record)
                    cm = CandidateMedia()
                    cm.mint_new_entity_ok = False  # DO NOT create new entities!
                    cm.project_uuid = self.project_uuid
                    cm.source_id = self.source_id
                    cm.class_uri = field_obj.field_value_cat
                    cm.import_rows = dist_rec['rows']  # list of rows where this record value is found
                    cm.metadata_obj = self.metadata_obj
                    cm.reconcile_manifest_item(dist_rec['imp_cell_obj'])
                    if cm.uuid is not False:
                        self.reconciled_entities.append({'id': str(cm.uuid),
                                                         'label': cm.label})
        return single_media_field

    def get_media_fields(self):
        """ Makes a list of media fields that have media parts
        """
        part_of = ImportFieldAnnotation.PRED_MEDIA_PART_OF
        media_fields = []
        fields_used_as_parts_of = []
        raw_media_fields = ImportField.objects\
                                      .filter(source_id=self.source_id,
                                              field_type='media')
        for media_field_obj in raw_media_fields:
            part_of_fields = ImportFieldAnnotation.objects\
                                                  .filter(source_id=self.source_id,
                                                          predicate=part_of,
                                                          object_field_num=media_field_obj.field_num)\
                                                  .values_list('field_num', flat=True)
            media_field_obj.part_list = part_of_fields
            if len(part_of_fields) > 0:
                # media field has part of fields
                for part_of_field in part_of_fields:
                    if part_of_field not in fields_used_as_parts_of:
                        fields_used_as_parts_of.append(part_of_field)
        for media_field_obj in raw_media_fields:
            if media_field_obj.field_num not in fields_used_as_parts_of:
                # current media item is not used as part of another
                # it's a field to use for making a manifest item (as a label)
                part_fields = ImportField.objects\
                                         .filter(source_id=self.source_id,
                                                 field_type='media',
                                                 field_num__in=media_field_obj.part_list)
                media_field_obj.parts = part_fields
                media_fields.append(media_field_obj)
        if len(media_fields) > 0:
            self.media_fields = media_fields
        return self.media_fields

    def get_metadata_fields(self, media_field_nums=[]):
        """ finds metadata fields that get added to the the sup_json
            field of new manifest objects
        """
        if len(media_field_nums) < 1 and len(self.media_fields) > 0:
            media_field_nums = []
            for field_obj in self.media_fields:
                media_field_nums.append(field_obj.field_num)
        self.metadata_obj.get_metadata_fields_for_field_list(media_field_nums)

class CandidateMedia():

    def __init__(self):
        self.project_uuid = False
        self.source_id = False
        self.class_uri = 'oc-gen:image'  # default to a image
        self.label = False
        self.uuid = False  # final, uuid for the item
        self.imp_cell_obj = False  # ImportCell object
        self.import_rows = False
        self.new_entity = False
        self.mint_new_entity_ok = True
        self.metadata_obj = None

    def reconcile_manifest_item(self, imp_cell_obj):
        """ Checks to see if the item exists in the manifest """
        match_found = None
        self.imp_cell_obj = imp_cell_obj
        if len(imp_cell_obj.record) > 0:
            self.label = imp_cell_obj.record
            
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
            elif self.mint_new_entity_ok:
                print('Create new manifest object {} (media) with pre-specified uuid: {}'.format(
                        self.label,
                        meta_uuid
                    )
                )
                match_found = False
                self.uuid = meta_uuid
                self.new_entity = True
                self.create_media_item(sup_metadata)
                
        elif self.label:
            # Case where we don't have a pre-confiured metadata uuid.
            match_found = self.match_against_manifest(self.label)
            if not match_found and self.mint_new_entity_ok:
                self.new_entity = True
                self.uuid = GenUUID.uuid4()
                self.create_media_item()
        self.update_import_cell_uuid()

    def create_media_item(self, sup_metadata=None):
        """ Create and save a new subject object"""
        new_man = Manifest()
        new_man.uuid = self.uuid
        new_man.project_uuid = self.project_uuid
        new_man.source_id = self.source_id
        new_man.item_type = 'media'
        new_man.repo = ''
        new_man.class_uri = self.class_uri
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

    def match_against_manifest(self, label):
        """ Checks to see if the item exists in the subjects table """
        match_found = False
        media_objs = Manifest.objects\
                             .filter(project_uuid=self.project_uuid,
                                     item_type='media',
                                     label=label)[:1]
        if len(media_objs) > 0:
            match_found = True
            self.uuid = media_objs[0].uuid
        return match_found


class CandidateMediaFile():

    SLEEP_TIME = .5

    def __init__(self, uuid):
        self.uuid = uuid
        self.project_uuid = False
        self.source_id = False
        self.file_type = False
        self.file_uri = False  
        self.new_entity = False
        self.imp_cell_obj = False  # ImportCell object

    def reconcile_media_file(self, file_uri):
        """ Checks to see if the item exists in the manifest """
        if self.file_type == 'oc-gen:thumbnail':
            # allow thumbnails to repeat
            media_list = Mediafile.objects\
                                  .filter(file_uri=file_uri,
                                          uuid=self.uuid)[:1]
        else:
            # only allow a file uri to be used 1 time
            media_list = Mediafile.objects\
                                  .filter(file_uri=file_uri)[:1]
        if len(media_list) < 1:
            self.file_uri = file_uri
            if self.validate_media_file():
                self.new_entity = True
                self.create_media_file()

    def validate_media_file(self):
        """ validates data for creating a media file """
        is_valid = True
        if not isinstance(self.file_type, str):
            is_valid = False
        if not isinstance(self.file_uri, str):
            is_valid = False
        return is_valid

    def create_media_file(self):
        """ Create and save a new media file object"""
        sleep(.1)
        ok = True
        mf = Mediafile()
        mf.uuid = str(self.uuid)
        mf.project_uuid = self.project_uuid
        mf.source_id = self.source_id
        mf.file_type = self.file_type
        mf.file_uri = self.file_uri
        mf.filesize = 0
        mf.mime_type_uri = ''
        ok = True
        try:
            mf.save()
        except:
            self.new_entity = False
            ok = False
        if ok and mf.filesize == 0:
            # filesize is still zero, meaning URI didn't
            # give an OK response to a HEAD request.
            # try again with a different capitalization
            # of the file extension (.JPG vs .jpg)
            if '.' in self.file_uri:
                f_ex = self.file_uri.split('.')
                f_extension = '.' + f_ex[-1]
                f_ext_upper = f_extension.upper()
                f_ext_lower = f_extension.lower()
                f_alt_exts = []
                f_alt_exts.append(self.file_uri.replace(f_extension,
                                                        f_ext_upper))
                f_alt_exts.append(self.file_uri.replace(f_extension,
                                                        f_ext_lower))
                check_extension = True
                for f_alt_ext in f_alt_exts:
                    # do a loop, since sometimes the user provided data with totally
                    # wrong extention capitalizations
                    if check_extension:
                        print('Pause before checking extension capitalization...')
                        sleep(self.SLEEP_TIME)
                        self.file_uri = f_alt_ext
                        mf.file_uri = self.file_uri
                        mf.save()
                        if mf.filesize > 0 or self.file_uri.endswith('.nxs') or  self.file_uri.endswith('.zip'):
                            print('Corrected extension capitalization: ' + str(self.file_uri))
                            check_extension = False
                            # yeah! We found the correct extention
                            # capitalization
                            # Now, save the corrected file_uri import cell record
                            # So if we have to re-run the import, we don't have to do
                            # multiple checks for capitalization
                            self.imp_cell_obj.record = self.file_uri
                            self.imp_cell_obj.save()
                            print('Saved corrected extension import cell record')
                            break
