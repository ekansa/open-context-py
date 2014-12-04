from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.apps.imports.fields.models import ImportField
from opencontext_py.apps.imports.fields.templating import ImportProfile
from opencontext_py.apps.imports.fieldannotations.models import ImportFieldAnnotation
from opencontext_py.apps.imports.records.models import ImportCell
from opencontext_py.apps.imports.records.process import ProcessCells
from opencontext_py.apps.imports.fieldannotations.general import ProcessGeneral
from opencontext_py.apps.imports.fieldannotations.subjects import ProcessSubjects
from opencontext_py.apps.imports.fieldannotations.persons import ProcessPersons
from opencontext_py.apps.imports.fieldannotations.descriptions import ProcessDescriptions
from opencontext_py.apps.imports.fieldannotations.links import ProcessLinks


# Finalizes an import by processing data
class FinalizeImport():

    # list of processes to run, in order, to complete the import of data
    DEFAULT_PROCESSES = ['subjects',
                         'persons',
                         'descriptions',
                         'links']

    def __init__(self, source_id):
        self.source_id = source_id
        pg = ProcessGeneral(source_id)
        pg.get_source()
        self.project_uuid = pg.project_uuid
        self.description_annotations = False
        self.des_rels = False
        self.start_row = 1
        self.last_row = False
        self.batch_size = 250
        self.end_row = self.batch_size
        self.active_process = self.DEFAULT_PROCESSES

    def process_all_batch(self):
        """ Processes the current batch, determined by the row number
            by running the individual import processes in the proper order
        """
        self.end_row = self.start_row + self.batch_size
        outcomes = LastUpdatedOrderedDict()
        outcomes['start'] = self.start_row
        outcomes['end'] = self.end_row
        outcomes['last'] = False
        for act_process in self.active_processes:
            act_outcome = LastUpdatedOrderedDict()
            act_outcome['process'] = act_process
            if act_process == 'subjects':
                ps = ProcessSubjects(self.source_id)
                ps.start_row = self.start_row
                ps.batch_size = self.batch_size
                ps.process_subjects_batch()
                act_outcome['fields'] = ps.count_active_fields

    def process_active_batch(self, act_process):
        """ Processes the current batch, determined by the row number
            by running the individual import processes in the proper order
        """
        act_outcome = LastUpdatedOrderedDict()
        act_outcome['process'] = act_process
        if act_process == 'subjects':
            ps = ProcessSubjects(self.source_id)
            ps.start_row = self.start_row
            ps.batch_size = self.batch_size
            ps.process_subjects_batch()
            act_outcome['fields'] = ps.count_active_fields
        