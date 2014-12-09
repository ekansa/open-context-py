import json
import requests
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.apps.imports.fields.models import ImportField
from opencontext_py.apps.imports.records.models import ImportCell


class RefineAPI():
    """ Interacts with Open (Google) Refine for importing and updating data """
    DEFAULT_REFINE_BASE_URL = 'http://127.0.0.1:3333'

    def __init__(self, refine_project=False):
        self.refine_model = False
        self.col_schema = False
        self.json_r = False
        self.refine_base_url = self.DEFAULT_REFINE_BASE_URL
        self.refine_project = str(refine_project)
        self.source_id = self.convert_refine_to_source_id(refine_project)
        self.row_request_limit = 500
        self.data = False

    def convert_refine_to_source_id(self, refine_project):
        """ converts a refine project id to a source_id for opencontext """
        if refine_project is not False:
            source_id = 'ref:' + str(refine_project)
        else:
            source_id = False
        return source_id

    def convert_source_id_to_refine(self, source_id):
        """ converts a refine project id to a source_id for opencontext """
        if 'ref:' in source_id:
            refine_project = source_id.replace('ref:' , '')
        else:
            refine_project = source_id
        return refine_project

    def get_data_batch_to_model(self, start=0):
        """ gets a batch of rows, aligns them to the schema for easy use """
        self.prepare_model()
        if self.col_schema is not False:
            self.data = []
            json_r = self.get_rows(start)
            if 'rows' in json_r:
                num_rows = len(json_r['rows'])
                if num_rows > 0:
                    self.schematize_json_rows(json_r['rows'])
        else:
            print('Don\'t have a schema')

    def get_data_to_model(self, start=0):
        """ gets rows, aligns them to the schema for easy use """
        self.prepare_model()
        if self.col_schema is not False:
            self.data = []
            continue_rows = True
            while continue_rows:
                print('Getting data, starting with: ' + str(start))
                json_r = self.get_rows(start)
                num_rows = 0
                if 'rows' in json_r:
                    num_rows = len(json_r['rows'])
                    if num_rows > 0:
                        self.schematize_json_rows(json_r['rows'])
                else:
                    num_rows = 0
                if num_rows > 0:
                    start += self.row_request_limit
                else:
                    continue_rows = False
        else:
            print('Don\'t have a schema')

    def schematize_json_rows(self, json_rows):
        """ puts json rows into the right order of the schema """
        for row in json_rows:
            row_cell_count = len(row['cells'])
            record = LastUpdatedOrderedDict()
            record['row_num'] = int(float(row['i'])) + 1  # saves the row number (i + 1)
            record['cells'] = LastUpdatedOrderedDict()
            for col_index, col in self.col_schema.items():
                record['cells'][col_index] = ''  # defaults to blank data
                col_cell_index = int(float(col['cellIndex']))
                if col_cell_index < row_cell_count and col_cell_index >= 0:
                    if row['cells'][col_cell_index] is not None:
                        # get the trimmed value for the cell
                        record['cells'][col_index] = str(row['cells'][col_cell_index]['v']).strip()
            self.data.append(record)

    def prepare_model(self):
        """ prepare's the data model / schema for a refine project """
        output = False
        self.get_model()
        if self.refine_model is not False:
            self.col_schema = LastUpdatedOrderedDict()
            field_index = 0
            for col in self.refine_model['columnModel']['columns']:
                field_index += 1
                self.col_schema[field_index] = col
        if self.col_schema is not False:
            output = True
        return output

    def get_size(self):
        """ Makes requests to get the size of the refine dataset """
        output = False
        self.get_model()
        if self.refine_model is not False:
            field_count = len(self.refine_model['columnModel']['columns'])
            json_r = self.get_rows(0, 0)
            if json_r is not False:
                if 'total' in json_r:
                    row_count = int(float(json_r['total']))
                    output = {'field_count': field_count,
                              'row_count': row_count}
        return output

    def get_metadata(self):
        """ simple request to get project metadata """
        payload = {'project': self.refine_project}
        url = self.refine_base_url + '/command/core/get-project-metadata'
        r = requests.get(url, params=payload, timeout=240)
        r.raise_for_status()
        json_r = r.json()
        self.json_r = json_r
        return json_r

    def get_rows(self, start, limit=False):
        """
        gets json data for records of a mysql datatable after a certain time
        """
        if limit is False:
            limit = self.row_request_limit
        payload = {'project': self.refine_project,
                   'start': start,
                   'limit': limit}
        url = self.refine_base_url + '/command/core/get-rows'
        r = requests.get(url, params=payload, timeout=240)
        r.raise_for_status()
        json_r = r.json()
        self.json_r = json_r
        return json_r

    def get_model(self):
        """
        gets json data the schema / model of a refine project
        """
        payload = {'project': self.refine_project}
        url = self.refine_base_url + '/command/core/get-models'
        r = requests.get(url, params=payload, timeout=240)
        r.raise_for_status()
        self.refine_model = r.json()
        return self.refine_model

    def get_projects(self):
        """
        gets project metadata from refine
        """
        url = self.refine_base_url + '/command/core/get-all-project-metadata'
        try:
            r = requests.get(url, timeout=240)
            r.raise_for_status()
            refine_projects = r.json()
        except:
            refine_projects = False
        return refine_projects

    def get_project_base_url(self):
        """
            gets the project base url
        """
        return self.refine_base_url + '/project?project='
