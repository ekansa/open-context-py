import datetime
import json
from opencontext_py.apps.ocitems.ocitem.models import OCitem
from opencontext_py.apps.ldata.linkannotations.models import LinkRecursion


class SolrDocument:
    '''
    Defines the Solr Document objects that the crawler will crawl. Solr
    fields are stored in the Solr Documents' "fields" property.
    '''

    def __init__(self, uuid):
        '''
        Using our Python JSON-LD and other info provided in OCitem,
        build up dictionary of solr fields to index.
        '''
        # get ocitem, from which we can also access json_ld
        self.oc_item = OCitem().get_item(uuid)
        self.context_path = self._get_context_path()
        self.fields = {}
        self._add_solr_fields()
        self._process_context_path()
        self._process_predicates()

    def _get_solr_field_name_suffix(self, predicate_type):
        '''
        Defines whether our dynamic solr fields names for
        predicates end with ___pred_id, ___pred_numeric, etc.
        '''
        if predicate_type == '@id':
            return '___pred_id'
        elif predicate_type in ['xsd:integer', 'xsd:double', 'xsd:boolean']:
            return '___pred_numeric'
        elif predicate_type == 'xsd:string':
            return '___pred_string'
        elif predicate_type == 'xsd:date':
            return '___pred_date'
        else:
            raise Exception("Error: Unknown predicate type")

    def _get_predicate_values(self, predicate_slug, predicate_type):
        obs_key = 'oc-pred:' + predicate_slug
        for obs_list in self.oc_item.json_ld['oc-gen:has-obs']:
            if obs_key in obs_list:
                if predicate_type == '@id':
                    return self._convert_values_to_json(
                        obs_list[obs_key][0]['slug'],
                        obs_list[obs_key][0]['label']
                        )
                elif predicate_type in [
                    'xsd:integer', 'xsd:double', 'xsd:boolean'
                        ]:
                    if len(obs_list[obs_key]) == 1:
                        return obs_list[obs_key][0]
                    else:
                        return obs_list[obs_key]
                elif predicate_type == 'xsd:date':
                    return obs_list[obs_key][0] + 'T00:00:00Z'
                elif predicate_type == 'xsd:string':
                    return obs_list[obs_key][0]['xsd:string']
                else:
                    raise Exception("Error: Could not get predicate value")

    def _process_predicates(self):
        # Get list of predicates
        predicates = (item for item in self.oc_item.json_ld[
            '@context'].items() if item[0].startswith('oc-pred:'))
        # We need a list for "root___pred_id" because it is multi-valued
        self.fields['root___pred_id'] = []
        for predicate in predicates:
            # We need the predicate's uuid to get its parents
            predicate_uuid = predicate[1]['owl:sameAs'].split('/')[-1]
            predicate_type = predicate[1]['@type']
            parents = LinkRecursion(
                ).get_jsonldish_entity_parents(predicate_uuid)
            # Process parents
            for index, parent in enumerate(parents):
                # Treat the first parent in a special way
                if index == 0:
                    self.fields['root___pred_id'].append(
                        self._convert_values_to_json(
                            parent['slug'],
                            parent['label']
                            )
                        )
                    if len(parents) == 1:
                    # if it's the only item (i.e., no parents),
                        # process the predicate values
                        # First generate the solr field name
                        solr_field_name = self._convert_slug_to_solr(
                            parent['slug'] +
                            self._get_solr_field_name_suffix(
                                predicate_type)
                            )
                        # Then get the predicate values
                        self.fields[solr_field_name] = \
                            self._get_predicate_values(
                                parent['slug'],
                                predicate_type
                            )
                else:
                    # Process additional items
                    # Create solr field name using parent slug
                    solr_field_name = \
                        parents[index - 1]['slug'] + '___pred_id'
                    solr_field_name = self._convert_slug_to_solr(
                        solr_field_name
                        )
                    # Add slug and label as json values
                    self.fields[solr_field_name] = \
                        self._convert_values_to_json(
                            parent['slug'],
                            parent['label']
                            )
                    # If this is the last item, process the predicate values
                    if index == len(parents) - 1:
                        solr_field_name = self._convert_slug_to_solr(
                            parent['slug'] +
                            self._get_solr_field_name_suffix(
                                predicate_type)
                            )
                        self.fields[solr_field_name] = \
                            self._get_predicate_values(
                                parent['slug'],
                                predicate_type
                            )

    def _get_context_path(self):
        if 'oc-gen:has-context-path' in self.oc_item.json_ld:
            try:
                return self.oc_item.json_ld[
                    'oc-gen:has-context-path']['oc-gen:has-path-items']
            except KeyError:
                return None
        elif 'oc-gen:has-linked-context-path' in self.oc_item.json_ld:
            try:
                return self.oc_item.json_ld[
                    'oc-gen:has-linked-context-path']['oc-gen:has-path-items']
            except KeyError:
                return None
        else:
            return None

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
        self.fields['slug_label'] = 'test'  # fix

    def _process_context_path(self):
        if self.context_path is not None:
            for index, context in enumerate(self.context_path):
                # treat the root in its own special way
                if index == 0:
                        self.fields['root___context_id'] = \
                            self._convert_values_to_json(
                                self.context_path[0]['slug'],
                                self.context_path[0]['label']
                                )
                else:
                # for others, get the parent slug and generate a
                # dynamic field name
                    solr_field_name = \
                        self.context_path[index - 1]['slug'] + '___context_id'
                    # replace dashes with underscores because solr requires it
                    solr_field_name = self._convert_slug_to_solr(
                        solr_field_name
                        )
                    # add field name and values as json
                    self.fields[solr_field_name] = \
                        self._convert_values_to_json(
                            self.context_path[index]['slug'],
                            self.context_path[index]['label']
                            )
