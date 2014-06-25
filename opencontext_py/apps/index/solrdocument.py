import datetime
import json
from opencontext_py.apps.ocitems.ocitem.models import OCitem


class SolrDocument:
    ''' Defines the Solr Document objects that the crawler will crawl. Solr
    fields are stored in the Solr Documents' "fields" property. '''

    def __init__(self, uuid):
        ''' Using our Python JSON-LD and other info provided in OCitem,
        build up dictionary of solr fields to index.'''
        # get ocitem, from which we can also access json_ld
        self.oc_item = OCitem().get_item(uuid)
        self.context_path = self.oc_item.json_ld[
            'oc-gen:has-context-path']['oc-gen:has-path-items']
        self.fields = {}
        self._add_solr_fields()
        self._create_context_path()

    def _convert_slug_to_solr(self, slug):
        return slug.replace('-', '_')

    def _convert_values_to_json(self, key, value):
        json_values = {}
        json_values[key] = value
        return json.dumps(json_values, ensure_ascii=False)

    def _add_solr_fields(self):
        self.fields['uuid'] = self.oc_item.uuid
        self.fields['project_uuid'] = self.oc_item.project_uuid
        self.fields['published'] = self.oc_item.published.strftime(
            '%Y-%m-%dT%H:%M:%SZ'
            )   # verify
        self.fields['updated'] = datetime.datetime.utcnow().strftime(  # verify
            '%Y-%m-%dT%H:%M:%SZ')
        self.fields['image_media_count'] = 0  # fix
        self.fields['other_binary_media_count'] = 0  # fix
        self.fields['sort_score'] = 0  # fix
        self.fields['interest_score'] = 0  # fix
        self.fields['document_count'] = 0  # fix
        self.fields['uuid_label'] = 'test'  # fix

    def _create_context_path(self):
        for index, context in enumerate(self.context_path):
            # treat the root in its own special way
            if index == 0:
                self.fields['root___context_id'] = \
                    self._convert_values_to_json(
                        self.context_path[0]['slug'],
                        self.context_path[0]['label']
                        )
            else:
            # for others, get the parent slug and generate a dynamic field name
                self._solr_field_name = \
                    self.context_path[index - 1]['slug'] + '___context_id'
                # replace dashes with underscores because solr requires it
                self._solr_field_name = self._convert_slug_to_solr(
                    self._solr_field_name
                    )
                # add field name and values
                self.fields[self._solr_field_name] = \
                    self._convert_values_to_json(
                        self.context_path[index]['slug'],
                        self.context_path[index]['label']
                        )
