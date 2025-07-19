import copy
import datetime
import html
import json
import time

from lxml import etree

from django.db.models import Min
from django.conf import settings
from django.core.cache import caches

from opencontext_py.libs.rootpath import RootPath
from opencontext_py.apps.entities.uri.models import URImanagement

from opencontext_py.apps.all_items.models import (
    AllManifest,
    AllIdentifier,
)
from opencontext_py.apps.all_items.representations import item
from opencontext_py.apps.all_items.editorial.api import get_man_obj_by_any_id

from opencontext_py.apps.searcher.new_solrsearcher import main_search
from opencontext_py.apps.searcher.new_solrsearcher import db_entities


class SolrOAIpmh():
    """
    Open Archives Initiative, Protocol for Metadata
    Harvesting Methods

    Supports OAI-DC and OAI-Datacite and Datacite

    """

    OAI_PMH_NS = 'http://www.openarchives.org/OAI/2.0/'
    XSI_NS = 'http://www.w3.org/2001/XMLSchema-instance'
    SL_NS = 'http://www.openarchives.org/OAI/2.0/ http://www.openarchives.org/OAI/2.0/OAI-PMH.xsd'
    METADATA_FORMATS = [
        {
            "prefix": "oai_dc",
            "schema": "http://www.openarchives.org/OAI/2.0/oai_dc.xsd",
            "ns": "http://www.openarchives.org/OAI/2.0/oai_dc/",
            "schemaLocation": "http://www.openarchives.org/OAI/2.0/oai_dc/ http://www.openarchives.org/OAI/2.0/oai_dc.xsd",
            "label": "OAI Dublin Core",
        },
        {
            "prefix": "oai_datacite",
            "schema": "http://schema.datacite.org/oai/oai-1.0/oai.xsd",
            "ns": "http://schema.datacite.org/oai/oai-1.0/",
            "schemaLocation": "http://schema.datacite.org/oai/oai-1.0/ http://schema.datacite.org/oai/oai-1.0/oai.xsd",
            "label": "OAI DataCite",
        },
        {
            "prefix": "datacite",
            "schema": "http://schema.datacite.org/meta/nonexistant/nonexistant.xsd",
            "ns": "http://datacite.org/schema/nonexistant",
            "schemaLocation": "http://datacite.org/schema/kernel-2.1 http://schema.datacite.org/meta/kernel-2.1/metadata.xsd",
            "label": "DataCite",
        },
    ]
    DATACITE_RESOURCE = {
        'ns': 'http://datacite.org/schema/kernel-2.1',
        'schemaLocation': 'http://datacite.org/schema/kernel-2.1 http://schema.datacite.org/meta/kernel-2.1/metadata.xsd'
    }

    DC_FORMATS = {
        "subjects": [
            "text/html",
            "application/json",
            "application/vnd.geo+json",
            "application/ld+json",
        ],
        "media": [
            "text/html",
            "application/json",
            "application/vnd.geo+json",
            "application/ld+json",
        ],
        "projects": [
            "text/html",
            "application/json",
            "application/vnd.geo+json",
            "application/ld+json",
        ],
        "documents": [
            "text/html",
            "application/json",
            "application/vnd.geo+json",
            "application/ld+json",
        ],
        "other": [
            "text/html", 
            "application/json", 
            "application/ld+json",
        ],
    }

    DATACITE_RESOURCE_TYPES = {
        "subjects": {
            "ResourceTypeGeneral": "InteractiveResource", 
            "oc": "Data Record",
        },
        "media": {
            "ResourceTypeGeneral": "InteractiveResource", 
            "oc": "Media resource",
        },
        "projects": {
            "ResourceTypeGeneral": "Dataset",
            "oc": "Data publication project",
        },
        "documents": {
            "ResourceTypeGeneral": "Text", 
            "oc": "Document, diary, or notes",
        },
        "types": {
            "ResourceTypeGeneral": "InteractiveResource",
            "oc": "Vocabulary category or concept",
        },
        "predicates": {
            "ResourceTypeGeneral": "InteractiveResource",
            "oc": "Predicate, property or relation",
        },
        "other": {
            "ResourceTypeGeneral": "InteractiveResource", 
            "oc": "Resource",
        },
    }

    BASE_SETS = {
        "media": {
            "params": {
                "type": "media",
            }, 
            "label": "Media resources",
        },
        "documents": {
            "params": {
                "type": "documents",
            },
            "label": "Documents, Diaries, and Notes",
        },
        "projects": {
            "params": {
                "type": "projects",
            },
            "label": "Data Publication Projects",
        },
        "tables": {
            "params": {
                "type": "tables",
            },
            "label": "Data tables",
        },
    }

    DEPRECATED_BASE_SETS = {
        "subjects": {
            "params": {
                "type": "subjects"
            }, 
            "label": "Data Records",
        },
        "types": {
            "params": {
                "type": "types",
            },
            "label": "Vocabulary Categories and Concepts",
        },
        "predicates": {
            "params": {
                "type": "predicates",
            },
            "label": "Predicates, Properties and Relations",
        },
    }


    OAI_PMH_VERBS = [
        'Identify',
        'ListMetadataFormats',
        'ListIdentifiers',
        'ListRecords',
        'ListSets',
        'GetRecord',
    ]


    def __init__(self, id_href=True):
        rp = RootPath()
        self.blank_oc_item = None
        self.publisher_name = 'Open Context'
        self.base_url = rp.get_baseurl()
        self.http_resp_code = 200
        self.verb = None
        self.valid_verb = None
        self.metadata_prefix = None
        self.metadata_prefix_valid = None
        self.errors = []
        self.root = None
        self.request_xml = None
        self.resumption_token_dict = None
        self.rows = 100
        self.default_sort = 'published--desc'  # default sort of items (Publication date, descending)
        self.requested_set = None
        self.requested_set_valid = None
        self.identifier = None
        self.from_date = None
        self.until_date = None
        self.from_date_solr = None
        self.until_date_solr = None
        self.earliest_date_cache_key = 'oai-pmh-earliest-date'


    def check_request_param(self, param, request):
        """ Checks to see if a given
            parameter is in the request
            GET or POST
        """
        output = None
        if isinstance(request, dict):
            return request.get(param)
        if request.method == 'GET':
            if param in request.GET:
                output = request.GET[param]
        elif request.method == 'POST':
            if param in request.POST:
                output = request.POST[param]
        return output


    def check_validate_verb(self, request):
        """ Checks and validates the verb in the request """
        self.verb = self.check_request_param(
            'verb',
            request,
        )
        if not self.verb in self.OAI_PMH_VERBS:
            self.valid_verb = False
            self.errors.append('badVerb')
        else:
            self.valid_verb = True
        return self.valid_verb
    

    def get_cache_earliest_date(self):
        """ Gets and caches the earliest date
            as a date_time object!
        """
        cache = caches['redis_search']
        earliest_date = cache.get(self.earliest_date_cache_key)
        if earliest_date:
            return earliest_date
        sum_man = AllManifest.objects.filter(
            published__gt='2001-01-01'
        ).aggregate(
            Min('published')
        )
        earliest_date = sum_man['published__min']
        try:
            cache.set(self.earliest_date_cache_key, earliest_date)
        except:
            pass
        return earliest_date
    

    def add_set_params_to_solr_request(self, request_dict):
        """ adds extra query parameters to the Solr
            request_dict that are needed to filter by
            OAI "set"
        """
        set_params = {}
        if self.requested_set_valid:
            # limit to a valid requested set, using the query
            # params defined for the set
            set_params = self.BASE_SETS[self.requested_set]['params']
        else:
            # request all avalable sets, since there
            # is no requested limit on the set
            item_types = list(self.BASE_SETS.keys())
            set_params['type'] = '||'.join(item_types)
        # now add the set_params to the payload
        for param_key, param_value in set_params.items():
            request_dict[param_key] = param_value
        return request_dict


    def get_item_json_ld(self, item):
        """ gets metadata and uris
        """
        if not item:
            return None
        if isinstance(item, str):
            item_key_dict = db_entities.get_cache_item_key_dict()
            man_obj = get_man_obj_by_any_id(
                identifier=item,
                item_key_dict=item_key_dict,
            )
            if not man_obj:
                return None
            _, rep_dict = item.make_representation_dict(
                subject_id=man_obj.uuid,
                for_solr=False,
            )
            return rep_dict
        if not isinstance(item, dict):
            return None
        item_key_dict = db_entities.get_cache_item_key_dict()
        rep_dict = None
        id_keys = ['uri', 'id', 'uuid', '@id',]
        for id_key in id_keys:
            if rep_dict:
                continue
            act_id = item.get(id_key)
            if not act_id:
                continue
            act_id = item.get(id_key)
            man_obj = get_man_obj_by_any_id(
                identifier=act_id,
                item_key_dict=item_key_dict,
            )
            if not man_obj:
                continue
            _, rep_dict = item.make_representation_dict(
                subject_id=man_obj.uuid,
                for_solr=False,
            )
            break
        return rep_dict


    def get_category_label(self, json_ld):
        """ Gets a label for a category by looking in the
            JSON-LD
        """
        cat = json_ld.get('category')
        if not cat:
            return None
        if isinstance(cat, list):
            cat = cat[0]
        # Use the cache for speed.
        man_obj = db_entities.get_cache_man_obj_by_any_id(
            cat, 
            use_cache=True,
        )
        if not man_obj:
            return None
        return man_obj.label    


    def cache_earliest_time_from_solr(self, solr_json):
        earlest_solr = solr_json.get('oai-pmh:earliestDatestamp')
        if not earlest_solr:
            return None
        from_solr = earlest_solr[:19]
        cache = caches['redis_search']
        dt_earliest = None
        try:
            dt_earliest = datetime.datetime.strptime(from_solr, '%Y-%m-%dT%H:%M:%S')
            cache.set(
                self.earliest_date_cache_key, 
                dt_earliest
            )
        except:
            dt_earliest = None
        return dt_earliest


    def get_general_summary_facets(self):
        """ gets summary information about
            the facets, metadata
        """
        request_dict = {
            'response': 'metadata,facet',
            'oai-pmh': True,
            'cursorMark': '*',
        }
        request_dict = self.add_set_params_to_solr_request(request_dict)
        solr_json = None
        try:
            solr_json = main_search.process_solr_query(request_dict=request_dict)
        except:
            solr_json = None
        if not solr_json:
            error = etree.SubElement(self.root, 'error')
            error.text = 'Internal Server Error: Failed to get collection metadata summary'
            self.http_resp_code = 500
        # Cache the earliest date stamp from solr.
        self.cache_earliest_time_from_solr(solr_json)
        return solr_json


    def check_metadata_prefix(self, request):
        """ Checks to see if a metadata prefix is in a request """
        self.metadata_prefix = self.check_request_param(
            'metadataPrefix',
            request,
        )
        if self.metadata_prefix is not None:
            self.metadata_prefix_valid = False
            for meta_f in self.METADATA_FORMATS:
                if meta_f['prefix'] == self.metadata_prefix:
                    self.metadata_prefix_valid = True
                    break
            if self.metadata_prefix_valid is False:
                self.errors.append('cannotDisseminateFormat')
        return self.metadata_prefix_valid


    def check_validate_set(self, request):
        self.requested_set = self.check_request_param(
            'set',
            request
        )
        if self.requested_set is not None:
            if self.requested_set in self.BASE_SETS:
                self.requested_set_valid = True
            else:
                self.requested_set_valid = False
                self.errors.append('noRecordsMatch')
        return self.requested_set_valid


    def make_resumption_token_xml(
        self,
        resumption_token_dict,
        parent_node_xml,
        api_json_obj,
    ):
        """ makes the XML for a resumption token """
        if not api_json_obj or not isinstance(api_json_obj, dict):
            return None
        now_dt = datetime.datetime.now()
        expiration_dt = now_dt + datetime.timedelta(days=1)
        expiration_date = expiration_dt.strftime('%Y-%m-%dT%H:%M:%SZ')
        start_index = api_json_obj.get('startIndex', 0)
        complete_list_size = api_json_obj.get('totalResults', 0)
        
        if isinstance(resumption_token_dict, dict):
            new_resumption_dict = self.make_update_resumption_object(
                api_json_obj,
                resumption_token_dict,
            )
        else:
            new_resumption_dict = self.make_update_resumption_object(
                api_json_obj,
                {},
            )
        if 'response' in new_resumption_dict:
            # reduce clutter in these tokens, remove uneeded keys
            new_resumption_dict.pop('response', None)
        new_resumption_token_text = json.dumps(
            new_resumption_dict,
            ensure_ascii=False,
        )
        resumption_token = etree.SubElement(
            parent_node_xml,
            'resumptionToken',
            expirationDate=str(expiration_date),
            completeListSize=str(complete_list_size),
            cursor=str(start_index),
        )
        resumption_token.text = new_resumption_token_text


    def check_resumption_token(self, request):
        """ Checks to see if a resumption token is in
            the request, and if it is, validate it
            as a JSON object with the correct keys
        """
        token_str = self.check_request_param(
            'resumptionToken',
            request,
        )
        if not token_str:
            return None
        # OK We have a resumption token string, so check it.
        resumption_token_dict = None
        try:
            resumption_token_dict = json.loads(token_str)
        except:
            resumption_token_dict = None
        if not resumption_token_dict or not isinstance(resumption_token_dict, dict):
            self.errors.append('badResumptionToken')
            self.resumption_token_dict = None
            return None
        # Check required keys for the resumption tocken
        req_keys = [
            'rows',
            'sort',
            'published',
        ]
        valid_token = True
        for key in req_keys:
            if not resumption_token_dict.get(key):
                valid_token = False
                break
        if valid_token:
            # now check to see if we have either the start or the cursorMark parameters
            if not resumption_token_dict.get('start') and not resumption_token_dict.get('cursorMark'):
                # we need to have either a start index or a cursorMark
                valid_token = False
        if valid_token and resumption_token_dict.get('start') and resumption_token_dict.get('cursorMark'):
            # remove the start index param, since we're favoring the cursor mark
            resumption_token_dict.pop('start')
        if not valid_token:
            resumption_token_dict = None
            self.errors.append('badResumptionToken')
        self.resumption_token_dict = resumption_token_dict
        return resumption_token_dict


    def check_identifier(self, request):
        """ Checks and validates the verb in the request """
        identifier = self.check_request_param(
            'identifier',
            request,
        )
        if not identifier:
            return None
        self.identifier = html.escape(identifier)
        return self.identifier


    def make_solr_date(self, date_str):
        """ Converts a date into a valid date for Solr """
        output = None
        if len(date_str) >= 19:
            date_str = date_str[:19]
            try:
                dt = datetime.datetime.strptime(date_str, '%Y-%m-%dT%H:%M:%S')
                output = dt.strftime('%Y-%m-%dT%H:%M:%SZ')
            except:
                output = None
        else:
            date_str = date_str[:10]
            try:
                dt = datetime.datetime.strptime(date_str, '%Y-%m-%d')
                output = dt.strftime('%Y-%m-%dT%H:%M:%SZ')
            except:
                output = None
        return output


    def check_from_date(self, request):
        """ Checks the for a 'from' (date) parameter
        """
        from_date = self.check_request_param(
            'from',
            request,
        )
        if not from_date:
            return None
        from_solr = self.make_solr_date(from_date)
        if from_solr:
            self.from_date = from_date
            self.from_date_solr = from_solr
        else:
            self.from_date = None
            self.errors.append('badArgument')
        return True


    def check_until_date(self, request):
        """ Checks the for a 'until' (date) parameter
        """
        until_date = self.check_request_param(
            'until',
            request,
        )
        if not until_date:
            return None
        until_solr = self.make_solr_date(until_date)
        if until_solr:
            self.until_date = until_date
            self.until_date_solr = until_solr
        else:
            self.until_date = None
            self.errors.append('badArgument')


    def validate_from_until_dates(self):
        """ Checks to make sure the 'from' and
            'until' dates (if they are both requested)
             have the same length (granularity)
        """
        if self.from_date and self.until_date:
            if len(self.from_date) != len(self.until_date):
                self.errors.append('badArgument')
        dt_from = None
        dt_until = None
        if self.from_date_solr:
            from_solr = self.from_date_solr[:19]
            dt_from = datetime.datetime.strptime(from_solr, '%Y-%m-%dT%H:%M:%S')
        if self.until_date_solr:
            until_solr = self.until_date_solr[:19]
            dt_until = datetime.datetime.strptime(until_solr, '%Y-%m-%dT%H:%M:%S')
        if not dt_from and not dt_until:
            return None
        dt_earliest = self.get_cache_earliest_date()
        if dt_from and dt_until:
            if dt_from > dt_until:
                # from date is greater than or equal to the until date
                # or the from date is greater than the earliet date
                # in the manifest
                self.errors.append('badArgument') 
            elif dt_from == dt_until:
                dt_until = dt_from + datetime.timedelta(days=1)
                self.until_date_solr = dt_until.strftime('%Y-%m-%dT%H:%M:%SZ')
        if dt_until and dt_until < dt_earliest:
                # until date is less than the earliest publication date
            # in the manifest
            self.errors.append('noRecordsMatch')


    def get_item_json_ld(self, solr_resp_item):
        """ gets metadata and uris
        """
        if not solr_resp_item:
            return None
        rep_dict = None
        if isinstance(solr_resp_item, str):
            item_key_dict = db_entities.get_cache_item_key_dict()
            man_obj = get_man_obj_by_any_id(
                identifier=solr_resp_item,
                item_key_dict=item_key_dict,
            )
            if not man_obj:
                return None
            _, rep_dict = item.make_representation_dict(
                subject_id=man_obj.uuid,
                for_solr=False,
            )
            return rep_dict
        item_key_dict = db_entities.get_cache_item_key_dict()
        id_keys = ['uri', 'id', 'uuid', '@id',]
        for id_key in id_keys:
            if rep_dict:
                continue
            act_id = solr_resp_item.get(id_key)
            if not act_id:
                continue
            act_id = solr_resp_item.get(id_key)
            man_obj = get_man_obj_by_any_id(
                identifier=act_id,
                item_key_dict=item_key_dict,
            )
            if not man_obj:
                continue
            _, rep_dict = item.make_representation_dict(
                subject_id=man_obj.uuid,
                for_solr=False,
            )
            break
        return rep_dict


    def make_xml_root(self):
        """ makes the Root XML with namespaces for the document """
        if self.root:
            return None
        self.root = etree.Element(
            '{' + self.OAI_PMH_NS + '}OAI-PMH',
            nsmap={None: self.OAI_PMH_NS, 'xsi': self.XSI_NS},
            attrib={'{' + self.XSI_NS + '}schemaLocation': self.SL_NS},
        )


    def make_general_xml(self):
        """ makes general xml used for all responses """
        response_date = etree.SubElement(self.root, 'responseDate')
        response_date.text = time.strftime('%Y-%m-%dT%H:%M:%S') + 'Z'


    def make_request_xml(self):
        """ makes the XML for a verb request """
        if self.valid_verb:
            self.request = etree.SubElement(self.root, 'request', verb=self.verb)
        else:
            self.request = etree.SubElement(self.root, 'request')
        if self.metadata_prefix:
            self.request.attrib['metadataPrefix'] = self.metadata_prefix
        self.request.text = self.base_url + '/oai/'


    def make_error_item_xml(self, code):
        """ makes an XML error message """
        error = etree.SubElement(self.root, 'error', code=code)
        if code == 'badVerb':
            error.text = 'Illegal OAI verb'
        elif code == 'cannotDisseminateFormat':
            pass
        elif code == 'badResumptionToken':
            error.text = 'The value of the resumptionToken argument is invalid or expired'
        elif code == 'noRecordsMatch':
            error.text = (
                'The combination of the values of the from, until, '
                'set, and metadataPrefix arguments results in an empty list.'
            )
        elif code == 'idDoesNotExist':
            error.text = f'"{str(self.identifier)}" is unknown or illegal in Open Context.'
        elif code == 'badArgument':
            error.text = (
                'The request includes illegal arguments, missing required argument(s), '
                'repeated argument(s), or values for arguments have an illegal syntax.'
            )


    def make_error_xml(self):
        """ makes an error message for each error noted """
        if not self.errors or not isinstance(self.errors, list):
            return None
        for error in self.errors:
            self.make_error_item_xml(error)


    def make_identify_xml(self):
        """ Makes the XML for the
            Identify verb
        """
        metadata_facets = self.get_general_summary_facets()
        identify = etree.SubElement(self.root, 'Identify')
        name = etree.SubElement(identify, 'repositoryName')
        name.text = settings.DEPLOYED_SITE_NAME
        base_url = etree.SubElement(identify, 'baseURL')
        base_url.text = self.base_url + '/oai/'
        p_v = etree.SubElement(identify, 'protocolVersion')
        p_v.text = '2.0'
        admin_email = etree.SubElement(identify, 'adminEmail')
        admin_email.text = settings.ADMIN_EMAIL
        if isinstance(metadata_facets, dict):
            if 'oai-pmh:earliestDatestamp' in metadata_facets:
                e_d_t = etree.SubElement(identify, 'earliestDatestamp')
                e_d_t.text = metadata_facets['oai-pmh:earliestDatestamp'][:10]
            else:
                error = etree.SubElement(self.root, 'error')
                error.text = 'Internal Server Error: Failed to get earliest time-stamp'
                self.http_resp_code = 500
        deletions = etree.SubElement(identify, 'deletedRecord')
        deletions.text = 'no'
        granularity = etree.SubElement(identify, 'granularity')
        granularity.text = 'YYYY-MM-DD'


    def make_list_metadata_formats_xml(self):
        """ Makes the XML for the ListMetadataFormats
            verb
        """
        l_m_f = etree.SubElement(self.root, 'ListMetadataFormats')
        for meta_f in self.METADATA_FORMATS:
            meta_xml = etree.SubElement(l_m_f, 'metadataFormat')
            prefix = etree.SubElement(meta_xml, 'metadataPrefix')
            prefix.text = meta_f['prefix']
            schema = etree.SubElement(meta_xml, 'schema')
            schema.text = meta_f['schema']
            meta_ns = etree.SubElement(meta_xml, 'metadataNamespace')
            meta_ns.text = meta_f['ns']


    def make_list_sets_xml(self):
        """ Makes the XML for hte ListSets
            verb
        """
        metadata_facets = self.get_general_summary_facets()
        if not metadata_facets or not isinstance(metadata_facets, dict):
            error = etree.SubElement(self.root, 'error')
            error.text = 'Internal Server Error: Failed to get index of needed to generate sets'
            self.http_resp_code = 500
            return None
        list_sets_xml = etree.SubElement(self.root, 'ListSets')
        for item_type, item_set_des in self.BASE_SETS.items():
            set_xml = etree.SubElement(list_sets_xml, 'set')
            set_spec = etree.SubElement(set_xml, 'setSpec')
            set_spec.text = item_type
            set_name = etree.SubElement(set_xml, 'setName')
            set_name.text = item_set_des['label']

    
    def make_dc_metadata_xml(self, parent_node, json_ld):
        """ makes metadata in the dublin core format """
        act_format = self.get_metadata_format_attributes('oai_dc')
        if not act_format:
            return None

        tcheck = URImanagement.get_uuid_from_oc_uri(json_ld['id'], True)
        if not tcheck:
            item_type = None
        else:
            item_type = tcheck.get('item_type')

        dc = 'http://purl.org/dc/elements/1.1/'
        ns = {
            'dc': dc,
            'oai_dc': act_format['ns'],
            'xsi': self.XSI_NS,
        }
        format_xml = etree.SubElement(
            parent_node,
            '{' + act_format['ns'] + '}dc',
            nsmap=ns,
            attrib={'{' + self.XSI_NS + '}schemaLocation': act_format['schemaLocation']},
        )
        title_xml = etree.SubElement(format_xml, '{' + dc + '}title')
        if 'dc-terms:title' in json_ld:
            title_xml.text = json_ld['dc-terms:title']
        elif 'label' in json_ld:
            title_xml.text = json_ld['label']
        if 'dc-terms:issued' in json_ld:
            dt_date = json_ld['dc-terms:issued']
            date_xml = etree.SubElement(format_xml, '{' + dc + '}date')
            date_xml.text = dt_date
        # Add creators
        for ld_item in json_ld.get('dc-terms:creator', []):
            if not ld_item.get('label'):
                continue
            act_xml = etree.SubElement(format_xml, '{' + dc + '}creator')
            act_xml.text = ld_item.get('label')
        # Add contributors
        for ld_item in json_ld.get('dc-terms:contributor', []):
            if not ld_item.get('label'):
                continue
            act_xml = etree.SubElement(format_xml, '{' + dc + '}contributor')
            act_xml.text = ld_item.get('label')
        # Add identifiers
        for ld_item in json_ld.get('owl:sameAs', []):
            act_xml = etree.SubElement(format_xml, '{' + dc + '}identifier')
            act_xml.text = ld_item['id']
        if json_ld.get('id'):
            act_xml = etree.SubElement(format_xml, '{' + dc + '}identifier')
            act_xml.text = json_ld.get('id')

        if item_type in self.DATACITE_RESOURCE_TYPES:
            act_rt = self.DATACITE_RESOURCE_TYPES[item_type]
        else:
            act_rt = self.DATACITE_RESOURCE_TYPES['other']

        rt_xml = etree.SubElement(format_xml, '{' + dc + '}type')
        rt_xml.text = act_rt['ResourceTypeGeneral']
        publisher = etree.SubElement(format_xml, '{' + dc + '}publisher')
        publisher.text = self.publisher_name

        format_list = self.DC_FORMATS.get(item_type, self.DC_FORMATS.get('other'))
        media_files = json_ld.get('oc-gen:has-files', [])
        if item_type == 'media' and media_files:
            for act_file in media_files:
                if act_file.get('type') != 'oc-gen:fullfile':
                    continue
                mime_type_uri = act_file.get('dc-terms:hasFormat')
                if not mime_type_uri:
                    continue
                mime_type = mime_type_uri.replace(
                    'https://www.iana.org/assignments/media-types/media-types.xhtml#',
                    '',
                )
                mime_type = mime_type.replace(
                    'http://purl.org/NET/mediatypes/',
                    '',
                )
                if mime_type not in format_list:
                    format_list.append(mime_type)
    
        for mime in format_list:
            act_xml = etree.SubElement(format_xml, '{' + dc + '}format')
            act_xml.text = mime
        subjects_list = []
        # Get the category label and add to the subjects list.
        cat_label = self.get_category_label(json_ld)
        if cat_label:
            subjects_list.append(cat_label)
        for subj in json_ld.get('dc-terms:subject', []):
            if not subj.get('label'):
                continue
            subjects_list.append(subj.get('label'))
        for subject in subjects_list:
            act_xml = etree.SubElement(format_xml, '{' + dc + '}subject')
            act_xml.text = subject
        return True



    def make_datacite_metadata_xml(self, parent_node, json_ld):
        """ makes metadata for the datacite specification, which
            is also used in the oai_datacite specification
        """
        tcheck = URImanagement.get_uuid_from_oc_uri(json_ld['id'], True)
        if not tcheck:
            item_type = None
        else:
            item_type = tcheck.get('item_type')
        resource_xml = etree.SubElement(
            parent_node,
            'resoure',
            nsmap={None: self.DATACITE_RESOURCE['ns']},
            attrib={'{' + self.XSI_NS + '}schemaLocation': self.DATACITE_RESOURCE['schemaLocation']}
        )
        pids = json_ld.get('dc-terms:identifier', []) + json_ld.get('owl:sameAs', [])
        if json_ld.get('id'):
            pids.append(json_ld.get('id'))
        for raw_pid in pids:
            id_type = 'URL'
            pid = raw_pid
            if 'doi.org/' in raw_pid:
                id_type = 'DOI'
                pid_ex = raw_pid.split('doi.org/')
                pid = pid_ex[-1]
            if '/ark:' in raw_pid:
                id_type = 'ARK'
                pid_ex = raw_pid.split('/ark:')
                pid = f'ark:{pid_ex[-1]}'
            act_xml = etree.SubElement(
                resource_xml,
                'identifier',
                attrib={'identifierType': id_type}
            )
            act_xml.text = pid

        # Add Titles.
        act_node = etree.SubElement(resource_xml, 'titles')
        if json_ld.get('dc-terms:title'):
            act_xml = etree.SubElement(act_node, 'title')
            act_xml.text = json_ld.get('dc-terms:title')
        if json_ld.get('label') and json_ld.get('dc-terms:title') != json_ld.get('label'):
            act_xml = etree.SubElement(act_node, 'title')
            act_xml.text = json_ld.get('label')

        # Add creators and contributors
        dc_creators = []
        for ld_item in json_ld.get('dc-terms:creator', []):
            if not ld_item.get('label'):
                continue
            dc_creators.append(ld_item.get('label'))
        
        dc_contribs = []
        for ld_item in json_ld.get('dc-terms:contributor', []):
            if not ld_item.get('label'):
                continue
            dc_contribs.append(ld_item.get('label'))

        if dc_creators:
            act_node = etree.SubElement(resource_xml, 'creators')
            for creator in dc_creators:
                act_xml = etree.SubElement(act_node, 'creator')
                act_xml.text = creator
        
        if dc_contribs:
            act_node = etree.SubElement(resource_xml, 'contributors')
            for contributor in dc_contribs:
                act_xml = etree.SubElement(act_node, 'contributor')
                act_xml.text = contributor
        # Add publication and modification dates.
        act_node = etree.SubElement(resource_xml, 'dates')
        create_date = json_ld.get('dc-terms:issued', time.strftime('%Y-%m-%d'))
        date_xml = etree.SubElement(
            act_node,
            'date',
            attrib={'dateType': 'Available'}
        )
        date_xml.text = create_date
        if json_ld.get('dc-terms:modified'):
            date_xml = etree.SubElement(
                act_node,
                'date',
                attrib={'dateType': 'Updated'},
            )
            date_xml.text = json_ld.get('dc-terms:modified')
        # Add publisher informaiton
        act_node = etree.SubElement(resource_xml, 'publisher')
        act_node.text = self.publisher_name
        act_node = etree.SubElement(resource_xml, 'publicationYear')
        act_node.text = create_date[:4]  # the year, first 4 characters
        # now add the Datacite resource type
        act_rt = self.DATACITE_RESOURCE_TYPES.get(
            item_type, 
            self.DATACITE_RESOURCE_TYPES.get('other'),
        )
        rt_xml = etree.SubElement(
            resource_xml,
            'resourceType',
            attrib={'resourceTypeGeneral': act_rt['ResourceTypeGeneral']},
        )
        rt_xml.text = act_rt.get('oc')
        # now gather all the relevant mime-types
        format_list = self.DC_FORMATS.get(item_type, self.DC_FORMATS.get('other'))
        media_files = json_ld.get('oc-gen:has-files', [])
        if item_type == 'media' and media_files:
            for act_file in media_files:
                if act_file.get('type') != 'oc-gen:fullfile':
                    continue
                mime_type_uri = act_file.get('dc-terms:hasFormat')
                if not mime_type_uri:
                    continue
                mime_type = mime_type_uri.replace(
                    'https://www.iana.org/assignments/media-types/media-types.xhtml#',
                    '',
                )
                mime_type = mime_type.replace(
                    'http://purl.org/NET/mediatypes/',
                    '',
                )
                format_list.append(mime_type)
        # add the found mime-types to the xml formats
        act_node = etree.SubElement(resource_xml, 'formats')
        for mime in format_list:
            act_xml = etree.SubElement(act_node, 'format')
            act_xml.text = mime

        # Add subjects lists.
        subjects_list = []
        # Get the category label and add to the subjects list.
        cat_label = self.get_category_label(json_ld)
        if cat_label:
            subjects_list.append(cat_label)
        for subj in json_ld.get('dc-terms:subject', []):
            if not subj.get('label'):
                continue
            subjects_list.append(subj.get('label'))
        if subjects_list:
            act_node = etree.SubElement(resource_xml, 'subjects')
            for subject in subjects_list:
                act_xml = etree.SubElement(act_node, 'subject')
                act_xml.text = subject

        # Add IsPartOf relationships.
        for ld_item in json_ld.get('dc-terms:isPartOf', []):
            rel_uri = ld_item.get('id', ld_item.get('@id'))
            if not rel_uri:
                continue
            act_xml = etree.SubElement(
                resource_xml,
                'RelatedIdentifier',
                attrib={
                    'relatedIdentifierType': 'URL',
                    'relationType': 'IsPartOf'}
                )
            act_xml.text = rel_uri
        return True


    def make_oai_datacite_metadata_xml(self, parent_node, json_ld):
        """ makes metadata in the OAI-datacite specification """
        act_format = self.get_metadata_format_attributes('oai_dc')
        if not act_format:
            return None
        format_xml = etree.SubElement(
            parent_node,
            'oai_datacite',
            nsmap={None: act_format['ns']},
            attrib={'{' + self.XSI_NS + '}schemaLocation': act_format['schemaLocation']}
        )
        payload_xml = etree.SubElement(format_xml, 'payload')
        # now the rest is just the datacite specification
        self.make_datacite_metadata_xml(payload_xml, json_ld)


    def make_record_metadata_xml(self, parent_node, item):
        """ makes metadata about a record """
        json_ld = self.get_item_json_ld(item)
        if not json_ld:
            return None
        metadata_xml = etree.SubElement(parent_node, 'metadata')
        if self.metadata_prefix == 'oai_dc':
            return self.make_dc_metadata_xml(metadata_xml, json_ld)
        elif self.metadata_prefix == 'oai_datacite':
            return self.make_oai_datacite_metadata_xml(metadata_xml, json_ld)
        elif self.metadata_prefix == 'datacite':
            return self.make_datacite_metadata_xml(metadata_xml, json_ld)
        else:
            return None
    
    
    def make_get_record_xml(self):
        """ Makes the XML for the GetRecord
            verb
        """
        # only bother doing this if we don't have any errors
        if len(self.errors) > 0:
            return None
        if self.identifier is None or self.metadata_prefix is None:
            self.errors.append('badArgument')
            return None
        
        metadata_uris = self.get_metadata_uris()
        if not metadata_uris:
            self.errors.append('badArgument')
            return None
        # Get the actual metadata uris.
        uris = metadata_uris.get('oc-api:has-results', [])
        if not uris:
            if self.requested_set is None:
                self.errors.append('idDoesNotExist')
            else:
                self.errors.append('noRecordsMatch')
            return None
        # OK, we're to make an XML response
        list_recs_xml = etree.SubElement(self.root, 'GetRecord')
        item = uris[0]
        rec_xml = etree.SubElement(list_recs_xml, 'record')
        self.make_item_identifier_xml(rec_xml, item)
        self.make_record_metadata_xml(rec_xml, item)
        return True


    def make_list_records_xml(self):
        """ Makes the XML for the ListIdentifiers
            verb
        """
        if len(self.errors) > 0:
            # only bother doing this if we don't have any errors
            return None

        if not self.metadata_prefix and self.resumption_token_dict:
            # default to oai_dc if there's a resumption token but
            # not a metadata_prefix in the request
            self.metadata_prefix = 'oai_dc'
            self.metadata_prefix_valid = True
        
        if not self.metadata_prefix:
            self.errors.append('badArgument')
            return None

        metadata_uris = self.get_metadata_uris()
        if not metadata_uris:
            self.errors.append('badArgument')
            return None
        # Get the actual metadata uris.
        uris = metadata_uris.get('oc-api:has-results', [])
        if not uris:
            self.errors.append('noRecordsMatch')
            return None
        # Make the list of records in XML         
        list_recs_xml = etree.SubElement(self.root, 'ListRecords')
        for item in uris:
            # make an item header XML
            rec_xml = etree.SubElement(list_recs_xml, 'record')
            self.make_item_identifier_xml(rec_xml, item)
            self.make_record_metadata_xml(rec_xml, item)
        # now add the new sumption token
        self.make_resumption_token_xml(
            self.resumption_token_dict,
            list_recs_xml,
            metadata_uris,
        )
        return True


    def make_item_identifier_xml(self, parent_node, item):
        """ Makes XML for an item, in with the "header" element
            and attaches this to a parent node
        """
        header = etree.SubElement(parent_node, 'header')
        identifier = etree.SubElement(header, 'identifier')
        date_stamp = etree.SubElement(header, 'datestamp')
        item_uri = item.get('uri', item.get('id'))
        if item_uri:
            identifier.text = item_uri
            for item_type, _ in self.BASE_SETS.items():
                if not item_type in item_uri:
                    continue
                # found the item type, which defines its set
                set_xml = etree.SubElement(header, 'setSpec')
                set_xml.text = item_type
                break
        if 'published' in item:
            date_stamp.text = item['published'][:10]


    def make_list_identifiers_xml(self):
        """ Makes the XML for the ListIdentifiers
            verb
        """
        if len(self.errors) > 0:
            return None
        # only bother doing this if we don't have any errors
        metadata_uris = self.get_metadata_uris()
        if not metadata_uris or not isinstance(metadata_uris, dict):
            self.errors.append('noRecordsMatch')
            return None
        items = metadata_uris.get('oc-api:has-results',[])
        if not items:
            self.errors.append('noRecordsMatch')
            return None
        list_ids_xml = etree.SubElement(self.root, 'ListIdentifiers')
        for item in items:
            # make an item header XML
            self.make_item_identifier_xml(list_ids_xml, item)
        # now add the new resumption token
        self.make_resumption_token_xml(
            self.resumption_token_dict,
            list_ids_xml,
            metadata_uris,
        )
        return True


    def make_update_resumption_object(
        self,
        api_json_obj=None,
        resumption_token_dict={},
    ):
        """ makes or update a flow control resumption object
            This is a dict object that
            includes query parameters to pass to an API request.
            The parameters restrict by publication date to allow
            consistent pagination,
            even if new material gets published
        """
        if 'cursorMark' not in resumption_token_dict:
            resumption_token_dict['cursorMark'] = '*'
        if False and 'start' not in resumption_token_dict:
            resumption_token_dict['start'] = 0
        if 'rows' not in resumption_token_dict:
            resumption_token_dict['rows'] = self.rows
        if 'sort' not in resumption_token_dict:
            resumption_token_dict['sort'] = self.default_sort
        if isinstance(api_json_obj, dict):
            # this is the first request, without an existing
            # resumption token. So the next one will be for the
            # next page of results
            if 'itemsPerPage' in api_json_obj and \
                'nextCursorMark' in api_json_obj:
                # we have a next cursor mark.
                resumption_token_dict['rows'] = api_json_obj['itemsPerPage']
                resumption_token_dict['cursorMark'] = api_json_obj['nextCursorMark']
            if 'itemsPerPage' in api_json_obj and \
               'startIndex' in api_json_obj:
                # make the 'start' key at the next page
                resumption_token_dict['start'] = api_json_obj['startIndex'] + api_json_obj['itemsPerPage']
                resumption_token_dict['rows'] = api_json_obj['itemsPerPage']
            if 'published' not in resumption_token_dict:
                if 'oai-pmh:earliestDatestamp' in api_json_obj and \
                   'dcmi:created' in api_json_obj:
                    resumption_token_dict['published'] = self.add_from_until_date_limits(
                        api_json_obj['oai-pmh:earliestDatestamp'],
                        api_json_obj['dcmi:created'],
                    )
        else:
            # Add date limits if these are requested
            if self.from_date_solr or self.until_date_solr:
                resumption_token_dict['published'] = self.add_from_until_date_limits(
                    self.from_date_solr,
                    self.until_date_solr,
                )
        return resumption_token_dict


    def add_from_until_date_limits(self, api_earliest, api_latest):
        """ Adds dates limits request by the client
            in the 'from' and 'until' parameters
        """
        use_earliest = api_earliest
        use_latest = api_latest
        if self.from_date_solr:
            use_earliest = self.from_date_solr
        if self.until_date_solr:
            use_latest = self.until_date_solr
        if use_earliest is None:
            use_earliest = '*'
        if use_latest is None:
            use_latest = '*'
        output = '[' + use_earliest + ' TO ' + use_latest + ']'
        return output


    def get_metadata_format_attributes(self, metadata_prefix):
        """ gets attributes about a given metadata format """
        output = None
        for act_format in self.METADATA_FORMATS:
            if act_format['prefix'] != metadata_prefix:
                continue
            output = act_format
            break
        return output


    def get_metadata_uris(self):
        """ gets metadata and uris
        """
        if isinstance(self.resumption_token_dict, dict):
            # pass the validated resumption token provided in request
            resumption_token_dict = self.resumption_token_dict
        else:
            # first request, so we're not passing a resumption object
            # but need to make one
            resumption_token_dict = self.make_update_resumption_object(
                None,
                {}
            )
        
        request_dict = copy.deepcopy(resumption_token_dict)
        request_dict['oai-pmh'] = 1  # So we don't ask for facet counts, which is expensive
        request_dict['response'] = 'metadata,uri-meta'
        request_dict['attributes'] = 'dc-terms-creator,dc-terms-contributor'
        request_dict = self.add_set_params_to_solr_request(request_dict)
        if self.identifier:
            request_dict['id'] = str(self.identifier)
        solr_json = None
        try:
            solr_json = main_search.process_solr_query(request_dict=request_dict)
        except:
            solr_json = None
        if not solr_json:
            error = etree.SubElement(self.root, 'error')
            error.text = 'Internal Server Error: Failed to get collection metadata URIs'
            self.http_resp_code = 500
        return solr_json


    def process_verb(self):
        """ processes the request for a verb """
        if not self.valid_verb:
            return None
        # only do this with valid verbs!
        if self.verb == 'Identify':
            return self.make_identify_xml()
        elif self.verb == 'ListMetadataFormats':
            return self.make_list_metadata_formats_xml()
        elif self.verb == 'ListIdentifiers':
            return self.make_list_identifiers_xml()
        elif self.verb == 'ListRecords':
            return self.make_list_records_xml()
        elif self.verb == 'ListSets':
            return self.make_list_sets_xml()
        elif self.verb == 'GetRecord':
            return self.make_get_record_xml()
        else:
            return None


    def process_request(self, request):
        """ processes a request verb,
            determines the correct
            responses and http response codes
        """
        self.check_validate_verb(request)
        self.check_metadata_prefix(request)
        self.check_resumption_token(request)
        self.check_validate_set(request)
        self.check_identifier(request)
        self.check_from_date(request)
        self.check_until_date(request)
        self.validate_from_until_dates()  # makes sure dates have same granularity
        self.make_xml_root()
        self.make_general_xml()
        self.make_request_xml()
        self.process_verb()
        self.make_error_xml()
        return True


    def output_xml_string(self):
        """ outputs the string of the XML """
        output = etree.tostring(
            self.root,
            xml_declaration=True,
            pretty_print=True,
            encoding='utf-8',
        )
        return output