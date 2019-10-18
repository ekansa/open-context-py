from django.conf import settings
from django.core.cache import cache
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.apps.imports.sources.models import ImportSource
from opencontext_py.apps.imports.fields.models import ImportField
from opencontext_py.apps.imports.fields.templating import ImportProfile
from opencontext_py.apps.imports.fieldannotations.models import ImportFieldAnnotation
from opencontext_py.apps.imports.records.models import ImportCell
from opencontext_py.apps.imports.records.process import ProcessCells
from opencontext_py.apps.imports.fieldannotations.general import ProcessGeneral
from opencontext_py.apps.imports.fieldannotations.subjects import ProcessSubjects
from opencontext_py.apps.imports.fieldannotations.media import ProcessMedia
from opencontext_py.apps.imports.fieldannotations.documents import ProcessDocuments
from opencontext_py.apps.imports.fieldannotations.persons import ProcessPersons
from opencontext_py.apps.imports.fieldannotations.links import ProcessLinks
from opencontext_py.apps.imports.fieldannotations.complexdescriptions import ProcessComplexDescriptions
from opencontext_py.apps.imports.fieldannotations.descriptions import ProcessDescriptions


# Finalizes an import by processing data
class FinalizeImport():

    # list of processes to run, in order, to complete the import of data
    DEFAULT_PROCESS_STAGES = ['subjects',
                              'media',
                              'documents',
                              'persons',
                              'complex-descriptions',
                              'links',
                              'descriptions']
    # prefix to save the state of the import process
    DEFAULT_STAGE_ROW_PREFIX = 'imp-stage-row'
    DEFAULT_DONE_STATUS = 'import-done'

    def __init__(self, source_id, batch_size=settings.IMPORT_BATCH_SIZE):
        self.source_id = source_id
        pg = ProcessGeneral(source_id)
        pg.get_source()
        self.project_uuid = pg.project_uuid
        self.imp_source_obj = False
        self.row_count = False
        self.imp_status = False
        self.start_row = False
        self.batch_size = batch_size
        self.end_row = self.batch_size
        self.act_process_num = False
        self.next_process_num = False
        self.done = False
        self.error = False
        self.ok = True
        self.active_processes = self.DEFAULT_PROCESS_STAGES
        self.get_refine_source_meta()
        self.get_active_stage_row()

    def process_current_batch(self):
        """ Processes the current batch, of a given batch size
            start_row, and stage.
            State determinations (stage, start_row) are made once
            this class is initialized, with get_define_source_meta()
            and get_active_stage_row()
        """
        if self.start_row is not False:
            self.end_row = self.start_row + self.batch_size
            self.save_next_process_state()
            self.ok = True
            p_outome = self.process_active_batch()
            outcomes = self.make_outcomes()
            outcomes['details'] = p_outome
        else:
            self.ok = False
            outcomes = self.make_outcomes()
            outcomes['details'] = False
            outcomes['done'] = True
            if self.imp_status == self.DEFAULT_DONE_STATUS:
                outcomes['error'] = 'Already imported'
            else:
                outcomes['error'] = 'Something else is wrong'
        return outcomes

    def make_outcomes(self):
        """ Makes a dictionary object of process outcomes """
        outcomes = LastUpdatedOrderedDict()
        outcomes['ok'] = self.ok
        outcomes['start'] = self.start_row
        outcomes['end'] = self.end_row
        outcomes['row_count'] = self.row_count
        outcomes['done'] = self.done
        outcomes['done_stage_num'] = self.act_process_num
        outcomes['total_stages'] = len(self.active_processes)
        outcomes['done_stage'] = self.active_processes[self.act_process_num]
        if self.done is False:
            outcomes['next_stage'] = self.active_processes[self.next_process_num]
        else:
            outcomes['done_stage_num'] = outcomes['total_stages']
            outcomes['next_stage'] = 'All completed'
            # now clear the cache a change was made
            cache.clear()
        return outcomes

    def process_active_batch(self):
        """ Processes the current batch, determined by the row number
            by running the individual import processes in the proper order
        """
        p_label = self.active_processes[self.act_process_num]
        p_outcome = LastUpdatedOrderedDict()
        p_outcome['label'] = p_label
        if p_label == 'subjects':
            p_act = ProcessSubjects(self.source_id)
            p_act.start_row = self.start_row
            p_act.batch_size = self.batch_size
            p_act.process_subjects_batch()
            p_outcome['count_active_fields'] = p_act.count_active_fields
            p_outcome['new_entities'] = p_act.new_entities
            p_outcome['reconciled_entities'] = p_act.reconciled_entities
            p_outcome['not_reconciled_entities'] = p_act.not_reconciled_entities
            p_outcome['count_new_assertions'] = 0
        elif p_label == 'media':
            p_act = ProcessMedia(self.source_id)
            p_act.start_row = self.start_row
            p_act.batch_size = self.batch_size
            p_act.process_media_batch()
            p_outcome['count_active_fields'] = p_act.count_active_fields
            p_outcome['new_entities'] = p_act.new_entities
            p_outcome['reconciled_entities'] = p_act.reconciled_entities
            p_outcome['not_reconciled_entities'] = p_act.not_reconciled_entities
            p_outcome['count_new_assertions'] = 0
        elif p_label == 'documents':
            p_act = ProcessDocuments(self.source_id)
            p_act.start_row = self.start_row
            p_act.batch_size = self.batch_size
            p_act.process_documents_batch()
            p_outcome['count_active_fields'] = p_act.count_active_fields
            p_outcome['new_entities'] = p_act.new_entities
            p_outcome['reconciled_entities'] = p_act.reconciled_entities
            p_outcome['not_reconciled_entities'] = p_act.not_reconciled_entities
            p_outcome['count_new_assertions'] = 0
        elif p_label == 'persons':
            p_act = ProcessPersons(self.source_id)
            p_act.start_row = self.start_row
            p_act.batch_size = self.batch_size
            p_act.process_persons_batch()
            p_outcome['count_active_fields'] = p_act.count_active_fields
            p_outcome['new_entities'] = p_act.new_entities
            p_outcome['reconciled_entities'] = p_act.reconciled_entities
            p_outcome['not_reconciled_entities'] = p_act.not_reconciled_entities
            p_outcome['count_new_assertions'] = 0
        elif p_label == 'complex-descriptions':
            p_act = ProcessComplexDescriptions(self.source_id)
            p_act.start_row = self.start_row
            p_act.batch_size = self.batch_size
            p_act.process_complex_batch()
            p_outcome['count_active_fields'] = p_act.count_active_fields
            p_outcome['new_entities'] = []
            p_outcome['reconciled_entities'] = []
            p_outcome['not_reconciled_entities'] = []
            p_outcome['count_new_assertions'] = p_act.count_new_assertions
        elif p_label == 'links':
            p_act = ProcessLinks(self.source_id)
            p_act.start_row = self.start_row
            p_act.batch_size = self.batch_size
            p_act.process_link_batch()
            p_outcome['count_active_fields'] = p_act.count_active_fields
            p_outcome['new_entities'] = []
            p_outcome['reconciled_entities'] = []
            p_outcome['not_reconciled_entities'] = []
            p_outcome['count_new_assertions'] = p_act.count_new_assertions
        elif p_label == 'descriptions':
            p_act = ProcessDescriptions(self.source_id)
            p_act.start_row = self.start_row
            p_act.batch_size = self.batch_size
            p_act.process_description_batch()
            p_outcome['count_active_fields'] = p_act.count_active_fields
            p_outcome['new_entities'] = []
            p_outcome['reconciled_entities'] = []
            p_outcome['not_reconciled_entities'] = []
            p_outcome['count_new_assertions'] = p_act.count_new_assertions
        return p_outcome

    def get_active_stage_row(self):
        """ Gets the active stage + row for the import process from database """
        if self.imp_status is not False:
            if self.imp_status != self.DEFAULT_DONE_STATUS:
                if self.DEFAULT_STAGE_ROW_PREFIX in self.imp_status:
                    status_parts = self.imp_status.split(':')
                    if len(status_parts) == 3:
                        self.act_process_num = int(float(status_parts[1]))
                        self.start_row = int(float(status_parts[2]))
                    print('Current status: ' + self.imp_status)
                else:
                    print('Current status is new')
                    self.act_process_num = 0
                    self.start_row = 1
            else:
                print('Current status is done')
                self.start_row = False
                self.done = True
        else:
            print('Current status is unknown')

    def save_next_process_state(self):
        """ Saves the state of the importer process in the database
            so it can continue at the correct place
        """
        if self.end_row >= self.row_count:
            self.end_row = self.row_count
        self.next_process_num = self.act_process_num + 1
        if self.end_row >= self.row_count and self.next_process_num >= len(self.active_processes):
            # We're in the last row, and have done the last process
            self.done = True
        else:
            # still more to do
            self.done = False
            if self.end_row < self.row_count and self.next_process_num >= len(self.active_processes):
                self.next_process_num = 0
        if self.done is False:
            if self.next_process_num > 0:
                # use the same start row, since we still have to go through
                # more process stages
                next_row = self.start_row
            else:
                # starting at the begining of the process stages, so
                # advance to the next row
                next_row = self.end_row
            next_status = self.DEFAULT_STAGE_ROW_PREFIX + ':'\
                                                        + str(self.next_process_num)\
                                                        + ':'\
                                                        + str(next_row)
        else:
            next_status = self.DEFAULT_DONE_STATUS
        print('Next status: ' + next_status)
        self.imp_source_obj.imp_status = next_status
        self.imp_source_obj.save()

    def reset_state(self):
        """ Resets the state of the import process so we can
            start again from scratch
        """
        self.imp_source_obj.imp_status = 'reset-import'
        self.imp_source_obj.save()
        self.get_refine_source_meta()
        self.get_active_stage_row()

    def get_refine_source_meta(self):
        """ Gets the metadata for a Refine source from the database """
        try:
            self.imp_source_obj = ImportSource.objects.get(source_id=self.source_id)
            self.row_count = self.imp_source_obj.row_count
            self.imp_status = self.imp_source_obj.imp_status
        except ImportSource.DoesNotExist:
            self.imp_source_obj = False
