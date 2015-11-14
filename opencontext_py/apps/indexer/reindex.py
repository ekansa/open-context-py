import json
import requests
from django.db import models
from django.conf import settings
from opencontext_py.apps.searcher.solrsearcher.solrdirect import SolrDirect
from opencontext_py.apps.indexer.crawler import Crawler
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.ocitems.assertions.models import Assertion
from opencontext_py.apps.ldata.linkannotations.models import LinkAnnotation
from opencontext_py.apps.ocitems.assertions.containment import Containment


class SolrReIndex():
    """ This class contains methods to make updates to
        the solr index especially after edits

from opencontext_py.apps.indexer.reindex import SolrReIndex
sri = SolrReIndex()
sri.annotated_after = '2015-10-26'
sri.reindex()

    """

    def __init__(self):
        self.uuids = []
        self.list_size = 20
        self.iteration = 0
        self.recursive = True
        # maximum number of times to iterate and make requests
        self.max_iterations = 100
        # if not false, get uuids by directly requsting JSON from solr
        self.solr_direct_url = False
        # if not false, use a request to Open Context to generate a
        # solr request to get UUIDs
        self.oc_url = False
        # if not false, use a dictionary of paramaters with Open Context
        # to generate a solr request to get UUIDs
        self.oc_params = False
        # if not false, use a Postgres SQL query to get a list of
        # UUIDs of items annotated after a certain date
        self.annotated_after = False
        # if not false, then limit to items that have been indexed before
        # this time
        self.skip_indexed_after = False
        # if not True also get uuids for items that have an assertion
        # linking them to annotated items
        self.related_annotations = False
        # if not false, use a Postgres SQL query to get a list of
        # UUIDs from a list of projects
        self.project_uuids = False
        # if not false, use a Postgres SQL query to get a list of
        # UUIDs
        self.sql = False

    def reindex(self):
        """ Reindexes items in Solr,
            with item UUIDs coming from a given source
        """
        self.iteration += 1
        print('Iteration: ' + str(self.iteration))
        if self.iteration <= self.max_iterations:
            uuids = []
            if self.solr_direct_url is not False:
                print('Get uuids from solr: ' + str(self.solr_direct_url))
                uuids = self.get_uuids_solr_direct(self.solr_direct_url)
            elif self.oc_url is not False:
                # now validate to make sure we're asking for uuids
                if 'response=uuid' in self.oc_url \
                   and '.json' in self.oc_url:
                    print('Get uuids from OC-API: ' + str(self.oc_url))
                    uuids = self.get_uuids_oc_url(self.oc_url)
            elif isinstance(self.project_uuids, list) \
                and self.annotated_after is False \
                and self.skip_indexed_after is False:
                # now validate to make sure we're asking for uuids
                print('Getting uuids for: ' + str(len(self.project_uuids)) + ' projects')
                uuids = []
                raw_uuids = Manifest.objects\
                                    .filter(project_uuid__in=self.project_uuids)\
                                    .values_list('uuid', flat=True)
                for raw_uuid in raw_uuids:
                    uuids.append(str(raw_uuid))
            elif isinstance(self.project_uuids, list)\
                 and self.annotated_after is False\
                 and self.skip_indexed_after is not False:
                # index items from projects, but not items indexed after a certain
                # datetime
                uuids = []
                raw_uuids = Manifest.objects\
                                    .filter(project_uuid__in=self.project_uuids)\
                                    .exclude(indexed__gte=self.skip_indexed_after)\
                                    .values_list('uuid', flat=True)
                for raw_uuid in raw_uuids:
                    uuids.append(str(raw_uuid))
            elif self.annotated_after is not False:
                self.max_iterations = 1
                uuids = []
                anno_list = []
                if self.project_uuids is not False:
                    if not isinstance(self.project_uuids, list):
                        project_uuids = [self.project_uuids]
                    else:
                        project_uuids = self.project_uuids
                    anno_list = LinkAnnotation.objects\
                                              .filter(project_uuid__in=project_uuids,
                                                      updated__gte=self.annotated_after)
                else:
                    anno_list = LinkAnnotation.objects\
                                              .filter(updated__gte=self.annotated_after)
                for anno in anno_list:
                    print('Index annotation: ' + anno.subject + ' :: ' + anno.predicate_uri + ' :: ' + anno.object_uri)
                    if(anno.subject_type in (item[0] for item in settings.ITEM_TYPES)):
                        # make sure it's an Open Context item that can get indexed
                        if anno.subject not in uuids:
                            uuids.append(anno.subject)
                    if anno.subject_type == 'types' and self.related_annotations:
                        # get the
                        # subjects item used with this type, we need to do a lookup
                        # on the assertions table
                        assertions = Assertion.objects\
                                              .filter(object_uuid=geo_anno.subject)
                        for ass in assertions:
                            if ass.uuid not in uuids:
                                uuids.append(ass.uuid)
            if isinstance(uuids, list):
                print('Ready to index ' + str(len(uuids)) + ' items')
                crawler = Crawler()
                crawler.index_document_list(uuids, self.list_size)
                self.reindex()
            else:
                print('Problem with: ' + str(uuids))

    def reindex_uuids(self, uuids):
        """ reindexes a list of uuids
        """
        if isinstance(uuids, list):
            crawler = Crawler()
            crawler.index_document_list(uuids, self.list_size)
            return len(uuids)
        else:
            return False

    def reindex_related(self, uuid):
        """ Reindexes an item
            and related items, especially
            child items from containment
        """
        uuids = self.get_related_uuids(uuid)
        return self.reindex_uuids(uuids)

    def reindex_related_to_object_uris(self,
                                       object_uri_list,
                                       indexed_before=False):
        """ reindexes based on associations to object_uris
            in the link_annotations model
        """
        if not isinstance(object_uri_list, list):
            object_uri_list = [object_uri_list]
        # gets predicates related to these object uris
        anno_list = LinkAnnotation.objects\
                                  .filter(object_uri__in=object_uri_list,
                                          subject_type='predicates')
        rel_pred_uuid_list = []
        for anno_obj in anno_list:
            if anno_obj.subject not in rel_pred_uuid_list:
                rel_pred_uuid_list.append(anno_obj.subject)
        print('Got ' + str(len(rel_pred_uuid_list)) + ' now getting manifest items...')
        # now get the uuids to process
        uuids = []
        if indexed_before is False:
            obj_uuids = Assertion.objects\
                                 .filter(predicate_uuid__in=rel_pred_uuid_list)\
                                 .values_list('uuid', flat=True)\
                                 .distinct('uuid')
            for uuid in obj_uuids:
                uuids.append(uuid)
        else:
            a_tab = 'oc_assertions'
            m_tab = '"oc_manifest" AS "m_b"'
            filters = 'oc_assertions.uuid=m_b.uuid \
                      AND ( m_b.indexed < \'' + indexed_before + '\' \
                      OR m_b.indexed is null)'
            obj_uuids = Assertion.objects\
                                 .filter(predicate_uuid__in=rel_pred_uuid_list)\
                                 .extra(tables=[a_tab, m_tab], where=[filters])\
                                 .values_list('uuid', flat=True)\
                                 .distinct('uuid')
            for uuid in obj_uuids:
                uuids.append(uuid)
        print('Found: ' + str(len(uuids)) + ' to index')
        return self.reindex_uuids(uuids)

    def reindex_related_uuid_list(self, rel_uuid_list):
        """ Reindexes an item
            and related items, from a list of uuids

        """
        uuids = []
        if not isinstance(rel_uuid_list, list):
            rel_uuid_list = [rel_uuid_list]
        for rel_uuid in rel_uuid_list:
            act_uuids = self.get_related_uuids(rel_uuid)
            for act_uuid in act_uuids:
                if act_uuid not in uuids:
                    uuids.append(act_uuid)
        print('Working on: ' + str(len(uuids)) + ' related to ' + str(len(rel_uuid_list)) + ' rel uuids...')
        return self.reindex_uuids(uuids)

    def get_related_uuids(self, uuid, inclusive=True):
        """ gets a list of uuids related to a given uuid
            if inclusive, include the UUID passed in the
            output list
        """
        link_item_types = ['subjects',
                           'media',
                           'persons',
                           'documents',
                           'projects']
        uuids = []
        if isinstance(uuid, list):
            start_uuids = uuid
        else:
            start_uuids = [uuid]
        for uuid in start_uuids:
            try:
                m_obj = Manifest.objects.get(uuid=uuid)
            except Manifest.DoesNotExist:
                m_obj = False
            if m_obj is not False:
                if inclusive:
                    uuids.append(m_obj.uuid)
                if m_obj.item_type == 'subjects':
                    act_contain = Containment()
                    # get the contents recusivelhy
                    contents = act_contain.get_children_by_parent_uuid(m_obj.uuid, True)
                    if isinstance(contents, dict):
                        for tree_node, children in contents.items():
                            for child_uuid in children:
                                if child_uuid not in uuids:
                                    uuids.append(child_uuid)
                elif m_obj.item_type == 'predicates':
                    # reindex all of the items described by a given predicate
                    # this can take a while!
                    rel_objs = Assertion.objects\
                                        .filter(predicate_uuid=m_obj.uuid)
                    for rel_item in rel_objs:
                        if rel_item.uuid not in uuids:
                            uuids.append(rel_item.uuid)
                rel_objs = Assertion.objects\
                                    .filter(uuid=m_obj.uuid,
                                            object_type__in=link_item_types)
                for rel_item in rel_objs:
                    if rel_item.object_uuid not in uuids:
                        uuids.append(rel_item.object_uuid)
                rel_subs = Assertion.objects\
                                    .filter(subject_type__in=link_item_types,
                                            object_uuid=m_obj.uuid)
                for rel_item in rel_subs:
                    if rel_item.object_uuid not in uuids:
                        uuids.append(rel_item.object_uuid)
        return uuids

    def get_uuids_solr_direct(self, solr_request_url):
        """ gets uuids from solr by direct request
        """
        solr_d = SolrDirect()
        uuids = solr_d.get_result_uuids(solr_request_url)
        return uuids

    def get_uuids_oc_url(self, oc_url):
        """ gets uuids from the Open Context API
        """
        try:
            r = requests.get(oc_url,
                             timeout=60)
            r.raise_for_status()
            uuids = r.json()
        except:
            uuids = []
        return uuids
