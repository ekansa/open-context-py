import json
from django.conf import settings
from opencontext_py.apps.entities.uri.models import URImanagement
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.libs.filemath import FileMath
from opencontext_py.apps.exports.expfields.models import ExpField
from opencontext_py.apps.exports.exprecords.models import ExpCell
from opencontext_py.apps.exports.exptables.models import ExpTable


class ExpTableTemplating():
    """
    Methods for making metadata templates for a table
    """

    def __init__(self, table_id):
        if '/' in table_id:
            id_ex = table_id.split('/')
            table_id = id_ex[1] + '_' + id_ex[0]
        self.public_table_id = table_id
        self.table_id = table_id
        self.exp_tab = self.get_exp_table_obj(table_id)
        self.uuid = table_id  # for template
        self.project_uuid = table_id  # for template
        self.view_permitted = True
        self.csv_url = False
        self.csv_size_human = False
        self.old_csv_files = []
        self.field_list = []

    def get_exp_table_obj(self, table_id):
        """ gets an export table model object
            or returns false if it does not exist
        """
        try:
            exp_tab = ExpTable.objects.get(table_id=table_id)
        except ExpTable.DoesNotExist:
            exp_tab = False
        return exp_tab

    def prep_html(self):
        """ preps HTML data """
        if self.exp_tab is not False:
            json_ld = self.make_json_ld()
            self.get_csv_url(json_ld)

    def prep_csv(self):
        """ preps CSV data """
        if self.exp_tab is not False:
            json_ld = self.make_json_ld()
            self.get_csv_url(json_ld)

    def make_json_ld(self):
        """ makes a JSON-LD object for the table metadata

            Need oc-table namespace
            need to include the cc-rel namespace

            need to add this name space
            http://www.w3.org/2003/01/geo/ as geo:lat, geo:lon
        """
        json_ld = LastUpdatedOrderedDict()
        if self.exp_tab is not False:
            json_ld['id'] = URImanagement.make_oc_uri(self.public_table_id, 'tables')
            json_ld['label'] = self.exp_tab.label
            json_ld['fields'] = self.exp_tab.field_count
            json_ld['rows'] = self.exp_tab.row_count
            json_ld['field_list'] = self.get_field_list()
            for key, objects in self.exp_tab.meta_json.items():
                json_ld[key] = objects
        return json_ld

    def get_field_list(self):
        """ gets a list of fields used with the current table """
        field_list = []
        ex_fields = ExpField.objects\
                            .filter(table_id=self.table_id)\
                            .order_by('field_num')
        for ex_field in ex_fields:
            field = LastUpdatedOrderedDict()
            field['id'] = '#field-' + str(ex_field.field_num)
            field['label'] = ex_field.label
            for key, objects in ex_field.rel_ids.items():
                field[key] = objects
            field_list.append(field)
        self.field_list = field_list
        return self.field_list

    def get_csv_url(self, json_ld):
        """ gets the csv link from the json-ld """
        if ExpTable.PREDICATE_DUMP in json_ld:
            for item in json_ld[ExpTable.PREDICATE_DUMP]:
                if 'text/csv' in item['dc-terms:hasFormat'] and \
                   'dc-terms:isReplacedBy' not in item:
                    # this is the current item, since it does not
                    # have a "replaced-by" predicate
                    self.csv_url = item['id']
                    fmath = FileMath()
                    self.csv_size_human = fmath.approximate_size(float(item['dcat:size']))
                    break
        return self.csv_url

    def get_old_csv_files(self, json_ld):
        """ gets the url for an old versions of CSV dumps of the data """
        if ExpTable.PREDICATE_DUMP in json_ld:
            for item in json_ld[ExpTable.PREDICATE_DUMP]:
                if 'text/csv' in item['dc-terms:hasFormat'] and \
                   'dc-terms:isReplacedBy' in item:
                    # this is an old item, since it has
                    # a "replaced-by" predicate
                    fmath = FileMath()
                    item['size-human'] = fmath.approximate_size(float(item['dcat:size']))
                    self.old_csv_files.append(item)
